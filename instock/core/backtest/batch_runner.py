# -*- coding: utf-8 -*-
"""回测批量任务：参数网格与 walk-forward。"""

from __future__ import annotations

import copy
import itertools
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple


def _set_nested(d: Dict[str, Any], path: List[str], value: Any) -> None:
    cur = d
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value


def expand_param_grid(base: Dict[str, Any], grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    if not grid:
        return [copy.deepcopy(base)]
    keys = sorted(grid.keys())
    combos = []
    for values in itertools.product(*[grid[k] for k in keys]):
        payload = copy.deepcopy(base)
        for k, v in zip(keys, values):
            if "." in k:
                _set_nested(payload, k.split("."), v)
                continue
            if k in ("fast", "slow", "period", "top_n", "rebalance_days") and isinstance(
                payload.get("strategy"), dict
            ):
                sp = payload.setdefault("strategy", {}).setdefault("params", {})
                if isinstance(sp, dict):
                    sp[k] = v
                    continue
            payload[k] = v
        combos.append(payload)
    return combos


def walk_forward_windows(
    date_from: str,
    date_to: str,
    *,
    train_days: int,
    test_days: int,
    step_days: int,
    trade_dates: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    if trade_dates:
        dates = list(trade_dates)
    else:
        import pandas as pd

        dates = [
            d.strftime("%Y-%m-%d")
            for d in pd.bdate_range(start=date_from, end=date_to)
        ]
    windows: List[Dict[str, str]] = []
    i = 0
    while i + train_days + test_days <= len(dates):
        train_start = dates[i]
        train_end = dates[i + train_days - 1]
        test_start = dates[i + train_days]
        test_end = dates[i + train_days + test_days - 1]
        windows.append(
            {
                "trainFrom": train_start,
                "trainTo": train_end,
                "testFrom": test_start,
                "testTo": test_end,
            }
        )
        i += max(1, step_days)
    return windows


def build_walk_forward_payloads(
    base_payload: Dict[str, Any],
    *,
    train_days: int,
    test_days: int,
    step_days: int,
) -> List[Tuple[str, Dict[str, Any]]]:
    date_from = str(base_payload.get("dateFrom") or "")
    date_to = str(base_payload.get("dateTo") or "")
    windows = walk_forward_windows(
        date_from,
        date_to,
        train_days=train_days,
        test_days=test_days,
        step_days=step_days,
    )
    out: List[Tuple[str, Dict[str, Any]]] = []
    for idx, w in enumerate(windows):
        payload = copy.deepcopy(base_payload)
        payload["dateFrom"] = w["testFrom"]
        payload["dateTo"] = w["testTo"]
        payload["title"] = f"{payload.get('title') or '回测'}-OOS-{idx + 1}"
        payload["_walkForward"] = w
        out.append((f"fold-{idx + 1}", payload))
    return out


def summarize_batch_runs(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    ok = [r for r in runs if r.get("status") == "success"]
    if not ok:
        return {"count": len(runs), "success": 0, "avgTotalReturn": 0.0, "avgSharpe": 0.0}
    rets = [float((r.get("metrics") or {}).get("totalReturn") or 0) for r in ok]
    sharpes = [float((r.get("metrics") or {}).get("sharpe") or 0) for r in ok]
    return {
        "count": len(runs),
        "success": len(ok),
        "avgTotalReturn": round(sum(rets) / len(rets), 6) if rets else 0.0,
        "avgSharpe": round(sum(sharpes) / len(sharpes), 6) if sharpes else 0.0,
    }
