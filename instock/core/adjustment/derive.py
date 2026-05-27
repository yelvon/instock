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
) -> Dict[str, Any]:
    code = str(code).zfill(6)[:6]
    raw = load_canonical_bars(code, date_from or "19900101", date_to, adjust_type="raw")
    if raw is None or raw.empty:
        return {"ok": False, "code": code, "error": "raw 无数据"}

    xdxr = load_xdxr_for_code(code)
    factor = build_qfq_factor_series(raw, xdxr)
    qfq_df = apply_qfq_to_ohlc(raw, factor)

    if date_from:
        d0 = pd.to_datetime(date_from)
        qfq_df = qfq_df[pd.to_datetime(qfq_df["date"]) >= d0]
    if date_to:
        d1 = pd.to_datetime(date_to)
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
        _log(log, "qfq 表为空，请使用 --mode full 手动全量派生")
        return {"ok": False, "error": "QFQ_TABLE_EMPTY", "hint": "derive_qfq_from_tdx_job --mode full"}

    universe = codes or load_universe_codes()
    if limit > 0:
        universe = universe[:limit]

    ok_n = 0
    fail_n = 0
    for i, code in enumerate(universe, 1):
        _log(log, f"[{i}/{len(universe)}] derive qfq {code}")
        try:
            r = derive_one_code(
                code,
                date_from=date_from if mode == "full" else date_from,
                date_to=date_to or None,
                log=log,
            )
            if r.get("ok"):
                ok_n += 1
            else:
                fail_n += 1
                _log(log, f"  [FAIL] {code} {r.get('error')}")
        except Exception as e:
            fail_n += 1
            _log(log, f"  [FAIL] {code} {e}")

    return {"ok": fail_n == 0, "success": ok_n, "failed": fail_n, "total": len(universe)}
