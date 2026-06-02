# -*- coding: utf-8 -*-
"""回测基准指数曲线与超额指标。"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from instock.core.backtest.result import _f, annual_return, max_drawdown, pct, sharpe

BENCHMARK_PRESETS: Dict[str, str] = {
    "000300": "沪深300",
    "000905": "中证500",
    "399006": "创业板指",
}


def normalize_benchmark_spec(spec: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    if not spec or not isinstance(spec, dict):
        return None
    code = str(spec.get("code") or "").strip().zfill(6)[:6]
    if not code:
        return None
    name = str(spec.get("name") or BENCHMARK_PRESETS.get(code) or code)
    return {"code": code, "name": name}


def load_benchmark_bars(
    code: str,
    date_from: str,
    date_to: str,
    *,
    adjust_type: str = "raw",
) -> pd.DataFrame:
    """加载指数日线，复用 canonical / legacy 读取。"""
    import os

    import instock.core.stockfetch as stf
    from instock.core.canonical.reader import canonical_read_enabled, load_canonical_bars

    if canonical_read_enabled():
        df = load_canonical_bars(code, date_from, date_to, adjust_type=adjust_type)
        if df is not None and not df.empty:
            return df
    if os.environ.get("INSTOCK_BACKTEST_ALLOW_LEGACY_CACHE", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    ):
        df = stf.stock_hist_cache(
            code,
            date_from.replace("-", ""),
            date_end=date_to.replace("-", ""),
            is_cache=True,
            adjust="",
        )
        if df is not None and not df.empty:
            return df
    raise ValueError(f"基准 {code} 缺少 {date_from} ~ {date_to} 日线数据")


def build_benchmark_curve(
    equity_times: List[str],
    bars: pd.DataFrame,
    *,
    name: str,
) -> Dict[str, Any]:
    if not equity_times or bars is None or bars.empty:
        return {"name": name or "无基准", "time": [], "value": [], "dailyReturn": []}
    df = bars.copy()
    if "date" not in df.columns:
        df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["date", "close"]).sort_values("date")
    close_map = {str(r["date"]): _f(r["close"]) for _, r in df.iterrows()}
    values: List[float] = []
    daily_returns: List[float] = []
    base = None
    prev = None
    for d in equity_times:
        c = close_map.get(d)
        if c is None or c <= 0:
            if values:
                values.append(values[-1])
                daily_returns.append(0.0)
            else:
                values.append(1.0)
                daily_returns.append(0.0)
            continue
        if base is None:
            base = c
        eq = c / base if base else 1.0
        dr = 0.0 if prev is None or prev <= 0 else c / prev - 1.0
        prev = c
        values.append(pct(eq))
        daily_returns.append(pct(dr))
    return {
        "name": name,
        "time": list(equity_times),
        "value": values,
        "dailyReturn": daily_returns,
    }


def compute_relative_metrics(
    strategy_returns: List[float],
    benchmark_returns: List[float],
    *,
    strategy_total_return: float,
    benchmark_total_return: float,
    strategy_mdd: float,
    strategy_annual: float,
) -> Dict[str, float]:
    n = min(len(strategy_returns), len(benchmark_returns))
    if n < 2:
        return {
            "benchmarkReturn": pct(benchmark_total_return),
            "excessReturn": pct(strategy_total_return - benchmark_total_return),
            "alpha": 0.0,
            "beta": 0.0,
            "informationRatio": 0.0,
            "calmar": 0.0,
        }
    sr = strategy_returns[:n]
    br = benchmark_returns[:n]
    mean_s = sum(sr) / n
    mean_b = sum(br) / n
    var_b = sum((x - mean_b) ** 2 for x in br) / (n - 1)
    cov = sum((sr[i] - mean_s) * (br[i] - mean_b) for i in range(n)) / (n - 1)
    beta = cov / var_b if var_b > 0 else 0.0
    alpha_daily = mean_s - beta * mean_b
    alpha = alpha_daily * 252
    active = [sr[i] - br[i] for i in range(n)]
    mean_a = sum(active) / n
    var_a = sum((x - mean_a) ** 2 for x in active) / (n - 1)
    std_a = math.sqrt(var_a) if var_a > 0 else 0.0
    ir = mean_a / std_a * math.sqrt(252) if std_a > 0 else 0.0
    calmar = strategy_annual / abs(strategy_mdd) if strategy_mdd < 0 else 0.0
    return {
        "benchmarkReturn": pct(benchmark_total_return),
        "excessReturn": pct(strategy_total_return - benchmark_total_return),
        "alpha": pct(alpha),
        "beta": pct(beta),
        "informationRatio": pct(ir),
        "calmar": pct(calmar),
    }


def enrich_result_with_benchmark(
    result: Dict[str, Any],
    benchmark_spec: Optional[Dict[str, Any]],
    *,
    date_from: str,
    date_to: str,
    adjust_type: str = "raw",
) -> Dict[str, Any]:
    spec = normalize_benchmark_spec(benchmark_spec)
    equity_times = (result.get("equity") or {}).get("time") or []
    if not spec:
        result["benchmark"] = {"name": "无基准", "time": [], "value": []}
        return result
    try:
        bars = load_benchmark_bars(spec["code"], date_from, date_to, adjust_type=adjust_type)
    except Exception:
        result["benchmark"] = {"name": spec["name"], "time": [], "value": []}
        return result
    bench = build_benchmark_curve(equity_times, bars, name=spec["name"])
    result["benchmark"] = {"name": bench["name"], "time": bench["time"], "value": bench["value"]}
    if not bench["value"]:
        return result
    strat_returns = (result.get("equity") or {}).get("dailyReturn") or []
    bench_returns = bench.get("dailyReturn") or []
    strat_total = (result.get("equity") or {}).get("value") or [1.0]
    bench_total = bench["value"][-1] - 1.0 if bench["value"] else 0.0
    strat_total_ret = strat_total[-1] - 1.0 if strat_total else 0.0
    metrics = result.get("metrics") or {}
    rel = compute_relative_metrics(
        strat_returns,
        bench_returns,
        strategy_total_return=strat_total_ret,
        benchmark_total_return=bench_total,
        strategy_mdd=_f(metrics.get("maxDrawdown")),
        strategy_annual=_f(metrics.get("annualReturn")),
    )
    metrics.update(rel)
    result["metrics"] = metrics
    return result
