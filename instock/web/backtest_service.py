# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime as _dt
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from instock.core.backtest.registry import (
    ensure_registry,
    list_strategies,
    reset_registry_for_tests,
    run_backtest,
    validate_params,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STORE_DIR = _REPO_ROOT / "instock" / "log" / "backtest_runs"
_BATCH_DIR = _REPO_ROOT / "instock" / "log" / "backtest_batches"
_LOCK = threading.Lock()
_RUNS: Dict[str, Dict[str, Any]] = {}
_BATCHES: Dict[str, Dict[str, Any]] = {}


class BacktestDataGapError(ValueError):
    def __init__(self, report: Dict[str, Any]):
        super().__init__("回测主数据缺失")
        self.report = report


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _ensure_store() -> None:
    _STORE_DIR.mkdir(parents=True, exist_ok=True)


def _persist(run: Dict[str, Any]) -> None:
    _ensure_store()
    path = _STORE_DIR / f"{run['id']}.json"
    path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_history() -> None:
    _ensure_store()
    with _LOCK:
        if _RUNS:
            return
        for path in sorted(_STORE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("id"):
                    _RUNS[data["id"]] = data
            except Exception:
                continue


def _codes_from_payload(payload: Dict[str, Any]) -> List[str]:
    from instock.core.backtest.universe_loader import resolve_universe_codes

    date_from, date_to = _date_range(payload)
    payload_copy = dict(payload)
    payload_copy["_date_from"] = date_from
    payload_copy["_date_to"] = date_to
    codes, _ = resolve_universe_codes(payload_copy)
    return codes


def _resolve_universe(payload: Dict[str, Any]) -> tuple[List[str], Dict[str, Any]]:
    from instock.core.backtest.universe_loader import resolve_universe_codes

    date_from, date_to = _date_range(payload)
    payload_copy = dict(payload)
    payload_copy["_date_from"] = date_from
    payload_copy["_date_to"] = date_to
    return resolve_universe_codes(payload_copy)


def _universe_table(payload: Dict[str, Any]) -> Optional[str]:
    uni = payload.get("universe") or {}
    if not isinstance(uni, dict):
        return None
    ut = str(uni.get("type") or "codes").strip().lower()
    if ut in ("selection_table", "strategy_table"):
        return str(uni.get("table") or "").strip() or None
    return None


def _date_range(payload: Dict[str, Any]) -> tuple[str, str]:
    today = _dt.date.today()
    date_to = str(payload.get("dateTo") or today.isoformat())
    date_from = str(payload.get("dateFrom") or (today - _dt.timedelta(days=180)).isoformat())
    return date_from, date_to


def _sample_bars(date_from: str, date_to: str) -> pd.DataFrame:
    start = pd.to_datetime(date_from)
    end = pd.to_datetime(date_to)
    days = pd.bdate_range(start=start, end=end)
    if len(days) < 6:
        days = pd.bdate_range(start=start, periods=30)
    rows = []
    price = 10.0
    for i, d in enumerate(days):
        if i < len(days) / 2:
            price += 0.18
        else:
            price -= 0.12
        open_price = price - 0.05
        close = price
        rows.append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "open": round(open_price, 2),
                "high": round(max(open_price, close) + 0.08, 2),
                "low": round(min(open_price, close) - 0.08, 2),
                "close": round(close, 2),
                "volume": 1000000 + i * 10000,
            }
        )
    return pd.DataFrame(rows)


def _normalize_price_mode(value: object) -> str:
    mode = str(value or "raw").strip().lower() or "raw"
    return mode if mode in ("raw", "qfq") else "raw"


def _load_bars(
    code: str,
    date_from: str,
    date_to: str,
    allow_sample: bool,
    *,
    adjust_type: str = "raw",
) -> pd.DataFrame:
    adjust_type = _normalize_price_mode(adjust_type)
    try:
        from instock.core.canonical.reader import canonical_read_enabled, load_canonical_bars

        if canonical_read_enabled():
            df = load_canonical_bars(code, date_from, date_to, adjust_type=adjust_type)
            if df is not None and not df.empty:
                return df
    except Exception:
        pass
    if os.environ.get("INSTOCK_BACKTEST_ALLOW_LEGACY_CACHE", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    ):
        try:
            import instock.core.stockfetch as stf

            df = stf.stock_hist_cache(
                code,
                date_from.replace("-", ""),
                date_end=date_to.replace("-", ""),
                is_cache=True,
                adjust="",
            )
            if df is not None and not df.empty:
                return df
        except Exception:
            pass
    if allow_sample:
        return _sample_bars(date_from, date_to)
    raise ValueError(f"{code} 缺少 {date_from} ~ {date_to} 日线数据")


def _ensure_batch_store() -> None:
    _BATCH_DIR.mkdir(parents=True, exist_ok=True)


def _persist_batch(batch: Dict[str, Any]) -> None:
    _ensure_batch_store()
    path = _BATCH_DIR / f"{batch['id']}.json"
    path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_batch_history() -> None:
    _ensure_batch_store()
    with _LOCK:
        if _BATCHES:
            return
        for path in sorted(_BATCH_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("id"):
                    _BATCHES[data["id"]] = data
            except Exception:
                continue


def _worker_count() -> int:
    try:
        return max(1, int(os.environ.get("INSTOCK_BACKTEST_WORKERS", "2")))
    except ValueError:
        return 2


def _execute(run_id: str, payload: Dict[str, Any]) -> None:
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return
        if run.get("status") == "cancelled":
            return
        run["status"] = "running"
        run["startedAt"] = _now()
        run["progress"] = {"processedDays": 0, "totalDays": 0, "message": "加载数据"}
        _persist(run)
    try:
        date_from, date_to = _date_range(payload)
        codes, universe_meta = _resolve_universe(payload)
        strategy = payload.get("strategy") or {}
        strategy_id = (strategy.get("id") or "moving_average_cross").strip()
        params = strategy.get("params") or {}
        broker = payload.get("broker") or {}
        risk = payload.get("risk") or {}
        data_opts = payload.get("data") or {}
        allow_sample = not bool(data_opts.get("requirePrerequisites", True))
        price_mode = _normalize_price_mode(data_opts.get("priceMode"))
        slippage_bps = float(broker.get("slippageBps") or 0)
        match_price = str(broker.get("matchPrice") or "next_open")
        bars = {
            code: _load_bars(
                code, date_from, date_to, allow_sample=allow_sample, adjust_type=price_mode
            )
            for code in codes
        }
        ensure_registry()
        result = run_backtest(
            run_id=run_id,
            title=str(payload.get("title") or "回测"),
            strategy_id=strategy_id,
            strategy_params=params if isinstance(params, dict) else {},
            bars_by_code=bars,
            initial_cash=float(broker.get("initialCash") or 1000000),
            commission_rate=float(broker.get("commissionRate") or 0.0003),
            min_commission=float(broker.get("minCommission") or 5),
            stamp_tax_rate=float(broker.get("stampTaxRate") or 0.001),
            transfer_fee_rate=float(broker.get("transferFeeRate") or 0.00002),
            max_weight_per_symbol=float(risk.get("maxWeightPerSymbol") or 0.1),
            slippage_bps=slippage_bps,
            match_price=match_price,
        )
        if isinstance(result.get("params"), dict):
            result["params"]["priceMode"] = price_mode
            result["params"]["slippageBps"] = slippage_bps
            result["params"]["matchPrice"] = match_price
        benchmark_spec = payload.get("benchmark")
        if benchmark_spec:
            from instock.core.backtest.benchmark import enrich_result_with_benchmark

            enrich_result_with_benchmark(
                result,
                benchmark_spec if isinstance(benchmark_spec, dict) else None,
                date_from=date_from,
                date_to=date_to,
                adjust_type=price_mode,
            )
        with _LOCK:
            current = _RUNS.get(run_id)
            if current is None:
                return
            result["createdAt"] = current.get("createdAt")
            result["startedAt"] = current.get("startedAt")
        result["finishedAt"] = _now()
        result["dateFrom"] = date_from
        result["dateTo"] = date_to
        result["universe"] = universe_meta
        result["benchmarkSpec"] = payload.get("benchmark")
        result["progress"] = {
            "processedDays": len(result["equity"]["time"]),
            "totalDays": len(result["equity"]["time"]),
            "message": "完成",
        }
        with _LOCK:
            if _RUNS.get(run_id, {}).get("status") == "cancelled":
                _persist(_RUNS[run_id])
                return
            _RUNS[run_id] = result
            _persist(result)
    except Exception as e:
        with _LOCK:
            run = _RUNS.get(run_id)
            if run is None:
                return
            if run.get("status") == "cancelled":
                _persist(run)
                return
            run["status"] = "failed"
            run["finishedAt"] = _now()
            run["error"] = {"code": "BACKTEST_RUN_FAILED", "message": str(e)}
            run["progress"] = {"message": "失败"}
            _persist(run)


def start_run(payload: Dict[str, Any], *, run_inline: bool = False) -> Dict[str, Any]:
    _load_history()
    ensure_registry()
    strategy = payload.get("strategy") or {}
    strategy_id = (strategy.get("id") or "moving_average_cross").strip()
    raw_params = strategy.get("params") or {}
    if not isinstance(raw_params, dict):
        raise ValueError("strategy.params 必须为对象")
    validate_params(strategy_id, raw_params)

    data_opts = payload.get("data") or {}
    if bool(data_opts.get("requirePrerequisites", True)):
        try:
            from instock.core.pipeline.backtest_data_prerequisites import check_backtest_data

            date_from, date_to = _date_range(payload)
            profile = str(data_opts.get("profile") or "backtest")
            price_mode = _normalize_price_mode(data_opts.get("priceMode"))
            report = check_backtest_data(
                pd.to_datetime(date_from).date(),
                pd.to_datetime(date_to).date(),
                profile=profile,
                codes=_codes_from_payload(payload),
                adjust_type=price_mode,
                universe_table=_universe_table(payload),
            ).to_dict()
            if not report.get("ok"):
                raise BacktestDataGapError(report)
        except BacktestDataGapError:
            raise
        except Exception as e:
            raise ValueError(f"回测前置数据检查失败：{e}") from e
    run_id = str(uuid.uuid4())
    date_from, date_to = _date_range(payload)
    _, universe_meta = _resolve_universe(payload)
    run = {
        "ok": True,
        "id": run_id,
        "title": str(payload.get("title") or "回测"),
        "status": "queued",
        "createdAt": _now(),
        "startedAt": None,
        "finishedAt": None,
        "dateFrom": date_from,
        "dateTo": date_to,
        "strategy": (payload.get("strategy") or {}).get("id") or "moving_average_cross",
        "universe": universe_meta,
        "progress": {"message": "排队中"},
        "summary": {},
    }
    with _LOCK:
        _RUNS[run_id] = run
        _persist(run)
    if run_inline:
        _execute(run_id, payload)
    else:
        t = threading.Thread(target=_execute, args=(run_id, payload), daemon=True)
        t.start()
    return get_run(run_id) or run


def list_runs(limit: int = 80) -> List[Dict[str, Any]]:
    _load_history()
    with _LOCK:
        rows = sorted(_RUNS.values(), key=lambda x: x.get("createdAt") or "", reverse=True)
    items = []
    for r in rows[:limit]:
        metrics = r.get("metrics") or {}
        items.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "status": r.get("status"),
                "createdAt": r.get("createdAt"),
                "startedAt": r.get("startedAt"),
                "finishedAt": r.get("finishedAt"),
                "dateFrom": r.get("dateFrom"),
                "dateTo": r.get("dateTo"),
                "universe": r.get("universe"),
                "strategy": (r.get("params") or {}).get("strategy") or r.get("strategy"),
                "progress": r.get("progress") or {},
                "summary": {
                    "totalReturn": metrics.get("totalReturn"),
                    "annualReturn": metrics.get("annualReturn"),
                    "maxDrawdown": metrics.get("maxDrawdown"),
                    "sharpe": metrics.get("sharpe"),
                    "tradeCount": metrics.get("tradeCount"),
                },
                "error": r.get("error"),
            }
        )
    return items


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    _load_history()
    with _LOCK:
        row = _RUNS.get(run_id)
        return json.loads(json.dumps(row, ensure_ascii=False)) if row else None


def get_run_kline_chart(
    run_id: str,
    code: str,
    period: str = "daily",
) -> Dict[str, Any]:
    """回测区间内单股 K 线 + 成交买卖点（用于前端 candlestick）。"""
    from instock.core.canonical.kline_payload import build_canonical_kline_payload

    run = get_run(run_id)
    if not run:
        raise ValueError("回测任务不存在")
    code = str(code).strip().zfill(6)[:6]
    date_from = str(run.get("dateFrom") or "")
    date_to = str(run.get("dateTo") or "")
    if not date_from or not date_to:
        raise ValueError("回测任务缺少日期区间")
    params = run.get("params") or {}
    adjust_type = str(params.get("priceMode") or "raw").strip() or "raw"
    marks = _marks_for_code(run, code)

    payload = build_canonical_kline_payload(
        code,
        date_from,
        date_to,
        adjust_type=adjust_type,
        period=period,
        marks=marks,
        empty_hint=f"{code} 在 {date_from} ~ {date_to} 无标准日线，请先在回测数据管理补数",
    )
    if payload.get("empty"):
        return payload

    return payload


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _marks_for_code(run: Dict[str, Any], code: str) -> List[Dict[str, Any]]:
    marks: List[Dict[str, Any]] = []
    for t in run.get("trades") or []:
        if str(t.get("code") or "").zfill(6)[:6] != code:
            continue
        side = str(t.get("side") or "").lower()
        if side not in ("buy", "sell"):
            continue
        raw_dt = str(t.get("date") or "").replace("/", "-")[:10]
        if len(raw_dt) >= 10:
            dt = raw_dt[:10]
        else:
            dt = raw_dt
        price = _f(t.get("price"))
        if not dt or len(dt) < 10 or price <= 0:
            continue
        qty = int(_f(t.get("qty")))
        marks.append(
            {
                "date": dt,
                "side": side,
                "price": round(price, 4),
                "qty": qty,
                "label": "买" if side == "buy" else "卖",
            }
        )
    marks.sort(key=lambda x: x["date"])
    return marks


def cancel_run(run_id: str) -> Dict[str, Any]:
    _load_history()
    with _LOCK:
        run = _RUNS.get(run_id)
        if not run:
            raise ValueError("回测任务不存在")
        if run.get("status") not in ("queued", "running"):
            raise ValueError("已完成任务不可取消")
        run["status"] = "cancelled"
        run["finishedAt"] = _now()
        run["progress"] = {"message": "已取消"}
        _persist(run)
        return run


def delete_run(run_id: str) -> Dict[str, Any]:
    _load_history()
    with _LOCK:
        _RUNS.pop(run_id, None)
    path = _STORE_DIR / f"{run_id}.json"
    bytes_freed = path.stat().st_size if path.exists() else 0
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    return {"id": run_id, "deletedBytes": bytes_freed}


def reset_for_tests() -> None:
    reset_registry_for_tests()
    with _LOCK:
        _RUNS.clear()
        _BATCHES.clear()
    if _STORE_DIR.exists():
        for path in _STORE_DIR.glob("*.json"):
            try:
                path.unlink()
            except OSError:
                pass
    if _BATCH_DIR.exists():
        for path in _BATCH_DIR.glob("*.json"):
            try:
                path.unlink()
            except OSError:
                pass


def _run_batch_jobs(batch_id: str, jobs: List[tuple[str, Dict[str, Any]]]) -> None:
    from instock.core.backtest.batch_runner import summarize_batch_runs

    completed: List[str] = []
    for label, payload in jobs:
        with _LOCK:
            batch = _BATCHES.get(batch_id)
            if batch is None or batch.get("status") == "cancelled":
                return
            batch["status"] = "running"
            batch["progress"] = {"done": len(completed), "total": len(jobs), "current": label}
            _persist_batch(batch)
        run = start_run(payload, run_inline=True)
        completed.append(run["id"])
        with _LOCK:
            batch = _BATCHES.get(batch_id)
            if batch is None:
                return
            batch.setdefault("runIds", []).append(run["id"])
            batch["items"] = batch.get("items") or []
            batch["items"].append({"label": label, "runId": run["id"], "status": run.get("status")})
            _persist_batch(batch)
    runs = [get_run(rid) for rid in completed]
    runs = [r for r in runs if r]
    summary = summarize_batch_runs(runs)
    with _LOCK:
        batch = _BATCHES.get(batch_id)
        if batch is None:
            return
        batch["status"] = "success"
        batch["finishedAt"] = _now()
        batch["summary"] = summary
        batch["progress"] = {"done": len(jobs), "total": len(jobs), "message": "完成"}
        _persist_batch(batch)


def start_grid_batch(body: Dict[str, Any]) -> Dict[str, Any]:
    from instock.core.backtest.batch_runner import expand_param_grid

    _load_batch_history()
    base = body.get("basePayload") or body.get("payload") or {}
    grid = body.get("grid") or {}
    if not isinstance(base, dict):
        raise ValueError("basePayload 必须为对象")
    if not isinstance(grid, dict) or not grid:
        raise ValueError("grid 不能为空")
    payloads = expand_param_grid(base, grid)
    batch_id = str(uuid.uuid4())
    jobs = [(f"grid-{i + 1}", p) for i, p in enumerate(payloads)]
    batch = {
        "id": batch_id,
        "type": "grid",
        "status": "queued",
        "createdAt": _now(),
        "runIds": [],
        "items": [],
        "grid": grid,
        "summary": {},
        "progress": {"done": 0, "total": len(jobs)},
    }
    with _LOCK:
        _BATCHES[batch_id] = batch
        _persist_batch(batch)
    t = threading.Thread(target=_run_batch_jobs, args=(batch_id, jobs), daemon=True)
    t.start()
    return get_batch(batch_id) or batch


def start_walkforward_batch(body: Dict[str, Any]) -> Dict[str, Any]:
    from instock.core.backtest.batch_runner import build_walk_forward_payloads

    _load_batch_history()
    base = body.get("basePayload") or body.get("payload") or {}
    if not isinstance(base, dict):
        raise ValueError("basePayload 必须为对象")
    train_days = int(body.get("trainDays") or 60)
    test_days = int(body.get("testDays") or 20)
    step_days = int(body.get("stepDays") or test_days)
    jobs = build_walk_forward_payloads(
        base, train_days=train_days, test_days=test_days, step_days=step_days
    )
    if not jobs:
        raise ValueError("walk-forward 窗口为空，请扩大 dateFrom/dateTo 或减小 train/test 天数")
    batch_id = str(uuid.uuid4())
    batch = {
        "id": batch_id,
        "type": "walkforward",
        "status": "queued",
        "createdAt": _now(),
        "runIds": [],
        "items": [],
        "trainDays": train_days,
        "testDays": test_days,
        "stepDays": step_days,
        "summary": {},
        "progress": {"done": 0, "total": len(jobs)},
    }
    with _LOCK:
        _BATCHES[batch_id] = batch
        _persist_batch(batch)
    t = threading.Thread(target=_run_batch_jobs, args=(batch_id, jobs), daemon=True)
    t.start()
    return get_batch(batch_id) or batch


def get_batch(batch_id: str) -> Optional[Dict[str, Any]]:
    _load_batch_history()
    with _LOCK:
        row = _BATCHES.get(batch_id)
        return json.loads(json.dumps(row, ensure_ascii=False)) if row else None


def compare_runs(run_ids: List[str]) -> Dict[str, Any]:
    items = []
    for rid in run_ids:
        run = get_run(rid)
        if not run:
            continue
        items.append(
            {
                "id": rid,
                "title": run.get("title"),
                "status": run.get("status"),
                "dateFrom": run.get("dateFrom"),
                "dateTo": run.get("dateTo"),
                "metrics": run.get("metrics") or {},
                "equity": {
                    "time": (run.get("equity") or {}).get("time") or [],
                    "value": (run.get("equity") or {}).get("value") or [],
                },
                "benchmark": run.get("benchmark") or {},
            }
        )
    return {"ok": True, "items": items}


def export_run_csv(run_id: str) -> str:
    run = get_run(run_id)
    if not run:
        raise ValueError("回测任务不存在")
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["section", "key", "value"])
    metrics = run.get("metrics") or {}
    for k, v in metrics.items():
        w.writerow(["metric", k, v])
    equity = run.get("equity") or {}
    for i, dt in enumerate(equity.get("time") or []):
        w.writerow(["equity", dt, (equity.get("value") or [None])[i]])
    for t in run.get("trades") or []:
        w.writerow(
            [
                "trade",
                t.get("date"),
                f"{t.get('side')} {t.get('code')} qty={t.get('qty')} price={t.get('price')}",
            ]
        )
    return buf.getvalue()
