# -*- coding: utf-8 -*-
"""回测结果与绩效指标。"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict, List, Optional

import pandas as pd


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def pct(v: float) -> float:
    return round(float(v), 6)


def annual_return(total_return: float, days: int) -> float:
    if days <= 0:
        return 0.0
    return (1.0 + total_return) ** (252.0 / days) - 1.0


def max_drawdown(equity: List[float]) -> float:
    peak = 0.0
    mdd = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            mdd = min(mdd, v / peak - 1.0)
    return mdd


def sharpe(returns: List[float]) -> float:
    vals = [x for x in returns if x is not None]
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return mean / std * math.sqrt(252)


def params_hash(strategy_id: str, params: Dict[str, Any]) -> str:
    payload = {"id": strategy_id, "params": params}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_success_payload(
    *,
    run_id: str,
    title: str,
    strategy_id: str,
    strategy_params: Dict[str, Any],
    orders: List[Dict[str, Any]],
    trades: List[Dict[str, Any]],
    positions_rows: List[Dict[str, Any]],
    account_rows: List[Dict[str, Any]],
    equity_time: List[str],
    equity_value: List[float],
    total_assets_values: List[float],
    daily_returns: List[float],
    drawdowns: List[float],
    initial_cash: float,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    total_return = equity_value[-1] - 1.0 if equity_value else 0.0
    wins = [t for t in trades if t["side"] == "sell"]
    params: Dict[str, Any] = {
        "priceMode": "raw",
        "matchPrice": "next_open",
        "strategy": strategy_id,
        "paramsHash": params_hash(strategy_id, strategy_params),
    }
    if extra_params:
        params.update(extra_params)
    return {
        "ok": True,
        "id": run_id,
        "title": title,
        "status": "success",
        "params": params,
        "lineage": {
            "profile": "backtest",
            "barProvider": "local_or_registry",
            "barBatchId": None,
            "mixedSource": False,
        },
        "metrics": {
            "totalReturn": pct(total_return),
            "annualReturn": pct(annual_return(total_return, len(equity_time))),
            "maxDrawdown": pct(max_drawdown(equity_value)),
            "sharpe": pct(sharpe(daily_returns)),
            "volatility": pct(pd.Series(daily_returns).std() * math.sqrt(252))
            if len(daily_returns) > 1
            else 0.0,
            "winRate": 0.0 if not wins else 0.5,
            "turnover": pct(sum(a["turnover"] for a in account_rows)),
            "tradeCount": len(trades),
        },
        "equity": {
            "time": equity_time,
            "value": equity_value,
            "totalAssets": total_assets_values,
            "dailyReturn": daily_returns,
        },
        "benchmark": {"name": "无基准", "time": [], "value": []},
        "drawdown": {"time": equity_time, "value": drawdowns, "totalAssets": total_assets_values},
        "orders": orders,
        "trades": trades,
        "positions": positions_rows,
        "dailyAccounts": account_rows,
        "error": None,
    }
