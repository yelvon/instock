# -*- coding: utf-8 -*-
"""单股/批量前复权派生。"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from instock.core.adjustment.apply_qfq import apply_qfq_to_ohlc
from instock.core.adjustment.corporate_action_store import (
    get_stored_factor_version,
    ingest_gbbq_to_db,
    load_xdxr_for_code,
    qfq_table_has_rows,
    update_watermark,
)
from instock.core.adjustment.factor_chain import build_qfq_factor_series
from instock.core.adjustment.gbbq_reader import gbbq_factor_version
from instock.core.adjustment.schema import ensure_qfq_tables
from instock.core.canonical.qfq_writer import QfqBarWriter
from instock.core.canonical.reader import load_canonical_bars
from instock.core.canonical.sync_plan import plan_qfq_derive
from instock.core.mootdx_universe import load_universe_codes

_log = logging.getLogger(__name__)
LogFn = Optional[Callable[[str], None]]


def _log(fn: LogFn, msg: str) -> None:
    if fn:
        fn(msg)
    else:
        _log.info(msg)


def derive_one_code(
    code: str,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    factor_version: str = "",
    log: LogFn = None,
    limit_write_scope: bool = False,
) -> Dict[str, Any]:
    """
    date_from/date_to：缺口检测与写入范围。
    limit_write_scope=True 时仍用全历史 raw 计算复权因子，但只写入区间内 qfq 行。
    """
    code = str(code).zfill(6)[:6]
    write_from = date_from
    write_to = date_to
    if limit_write_scope:
        from instock.core.canonical.sync_plan import _code_bar_bounds

        raw_min, _ = _code_bar_bounds(code, "raw")
        load_from = raw_min.isoformat() if raw_min else "19900101"
        raw = load_canonical_bars(code, load_from, None, adjust_type="raw")
    else:
        raw = load_canonical_bars(code, date_from or "19900101", date_to, adjust_type="raw")
    if raw is None or raw.empty:
        return {"ok": True, "skipped": True, "code": code, "reason": "raw 无数据"}

    xdxr = load_xdxr_for_code(code)
    factor = build_qfq_factor_series(raw, xdxr)
    qfq_df = apply_qfq_to_ohlc(raw, factor)

    if write_from:
        d0 = pd.to_datetime(write_from)
        qfq_df = qfq_df[pd.to_datetime(qfq_df["date"]) >= d0]
    if write_to:
        d1 = pd.to_datetime(write_to)
        qfq_df = qfq_df[pd.to_datetime(qfq_df["date"]) <= d1]

    fv = factor_version or get_stored_factor_version() or gbbq_factor_version()
    writer = QfqBarWriter(factor_version=fv)
    writer.write_factor_rows(code, factor, fv)
    stats = writer.write_dataframe(code, qfq_df)

    last_date = None
    if not raw.empty and "date" in raw.columns:
        last_date = str(raw["date"].iloc[-1])[:10]
    update_watermark(code, last_date, fv)

    return {
        "ok": True,
        "code": code,
        "rows": len(qfq_df),
        "upserted": stats.upserted,
        "errors": stats.errors,
    }


def run_derive(
    *,
    mode: str = "incremental",
    codes: Optional[List[str]] = None,
    date_from: str = "",
    date_to: str = "",
    skip_ingest: bool = False,
    limit: int = 0,
    log: LogFn = None,
    limit_sync_scope: bool = False,
) -> Dict[str, Any]:
    ensure_qfq_tables()
    mode = (mode or "incremental").strip().lower()

    if not skip_ingest:
        cur_ver = gbbq_factor_version()
        stored = get_stored_factor_version()
        if cur_ver and cur_ver != stored:
            _log(log, f"gbbq 版本变化 {stored} -> {cur_ver}，重新 ingest")
            ingest_gbbq_to_db()
            mode = "full"

    if mode == "incremental" and not qfq_table_has_rows():
        if limit_sync_scope and (date_from or date_to):
            _log(log, "qfq 表为空且限定区间，自动切换为全历史首次派生")
            limit_sync_scope = False
            mode = "full"
        else:
            _log(log, "qfq 表为空，请使用 --mode full 手动全量派生")
            return {"ok": False, "error": "QFQ_TABLE_EMPTY", "hint": "derive_qfq_from_tdx_job --mode full"}

    scope_from = (date_from or "").strip()
    scope_to = (date_to or "").strip()
    if limit_sync_scope and scope_from:
        _log(log, f"qfq 派生区间与 raw 补数一致: {scope_from} ~ {scope_to or '最新'}")

    universe = codes or load_universe_codes()
    if limit > 0:
        universe = universe[:limit]

    skip_n = 0
    ok_n = 0
    fail_n = 0
    fv = get_stored_factor_version() or gbbq_factor_version()
    plan_from = scope_from if limit_sync_scope else (date_from or "")
    plan_to = scope_to if limit_sync_scope else (date_to or "")
    write_scope = limit_sync_scope and bool(scope_from)

    for i, code in enumerate(universe, 1):
        if mode == "incremental":
            plan = plan_qfq_derive(
                code,
                date_from=plan_from,
                date_to=plan_to,
                factor_version=fv,
            )
            if plan.get("skip"):
                skip_n += 1
                _log(log, f"[{i}/{len(universe)}] skip qfq {code} ({plan.get('reason')})")
                continue
            miss = plan.get("missing_dates") or []
            if miss:
                _log(
                    log,
                    f"[{i}/{len(universe)}] derive qfq {code} 补 {len(miss)} 日 "
                    f"({plan.get('date_from')}~{plan.get('date_to')})",
                )
            else:
                _log(log, f"[{i}/{len(universe)}] derive qfq {code} ({plan.get('reason')})")
        elif write_scope:
            _log(
                log,
                f"[{i}/{len(universe)}] derive qfq {code} [full 区间 {plan_from}~{plan_to or '最新'}]",
            )
        else:
            _log(log, f"[{i}/{len(universe)}] derive qfq {code} [full]")

        try:
            r = derive_one_code(
                code,
                date_from=plan_from or None,
                date_to=plan_to or None,
                factor_version=fv,
                log=log,
                limit_write_scope=write_scope,
            )
            if r.get("skipped"):
                skip_n += 1
                _log(log, f"  [SKIP] {code} {r.get('reason')}")
            elif r.get("ok"):
                ok_n += 1
            else:
                fail_n += 1
                _log(log, f"  [FAIL] {code} {r.get('error')}")
        except Exception as e:
            fail_n += 1
            _log(log, f"  [FAIL] {code} {e}")

    return {
        "ok": fail_n == 0,
        "success": ok_n,
        "skipped": skip_n,
        "failed": fail_n,
        "total": len(universe),
    }
