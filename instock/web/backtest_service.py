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

from instock.core.backtest.engine import run_moving_average_backtest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STORE_DIR = _REPO_ROOT / "instock" / "log" / "backtest_runs"
_LOCK = threading.Lock()
_RUNS: Dict[str, Dict[str, Any]] = {}


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
    uni = payload.get("universe") or {}
    codes = uni.get("codes") if isinstance(uni, dict) else []
    if isinstance(codes, str):
        codes = [x.strip() for x in codes.replace("\n", ",").split(",")]
    out = [str(c).strip().zfill(6) for c in (codes or []) if str(c).strip()]
    return out[:30] or ["600000"]


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


def _load_bars(code: str, date_from: str, date_to: str, allow_sample: bool) -> pd.DataFrame:
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
        codes = _codes_from_payload(payload)
        strategy = payload.get("strategy") or {}
        params = strategy.get("params") or {}
        broker = payload.get("broker") or {}
        risk = payload.get("risk") or {}
        data_opts = payload.get("data") or {}
        allow_sample = not bool(data_opts.get("requirePrerequisites", True))
        bars = {code: _load_bars(code, date_from, date_to, allow_sample=allow_sample) for code in codes}
        result = run_moving_average_backtest(
            run_id=run_id,
            title=str(payload.get("title") or "回测"),
            bars_by_code=bars,
            initial_cash=float(broker.get("initialCash") or 1000000),
            fast=int(params.get("fast") or 5),
            slow=int(params.get("slow") or 20),
            commission_rate=float(broker.get("commissionRate") or 0.0003),
            min_commission=float(broker.get("minCommission") or 5),
            stamp_tax_rate=float(broker.get("stampTaxRate") or 0.001),
            max_weight_per_symbol=float(risk.get("maxWeightPerSymbol") or 0.1),
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
        result["universe"] = {"type": "codes", "codes": codes}
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
    data_opts = payload.get("data") or {}
    if bool(data_opts.get("requirePrerequisites", True)):
        try:
            from instock.core.pipeline.backtest_data_prerequisites import check_backtest_data

            date_from, date_to = _date_range(payload)
            report = check_backtest_data(
                pd.to_datetime(date_from).date(),
                pd.to_datetime(date_to).date(),
            ).to_dict()
            if not report.get("ok"):
                raise BacktestDataGapError(report)
        except BacktestDataGapError:
            raise
        except Exception as e:
            raise ValueError(f"回测前置数据检查失败：{e}") from e
    run_id = str(uuid.uuid4())
    date_from, date_to = _date_range(payload)
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
        "universe": {"type": "codes", "codes": _codes_from_payload(payload)},
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
    with _LOCK:
        _RUNS.clear()
    if _STORE_DIR.exists():
        for path in _STORE_DIR.glob("*.json"):
            try:
                path.unlink()
            except OSError:
                pass
