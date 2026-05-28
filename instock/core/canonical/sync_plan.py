# -*- coding: utf-8 -*-
"""补数/派生前按库内覆盖与缺口决定跳过或仅写缺失日。"""

from __future__ import annotations

import datetime
import os
from typing import Any, Dict, List, Optional, Tuple

import instock.lib.database as mdb
from instock.core.pipeline import gaps


def sync_skip_complete_enabled() -> bool:
    return os.environ.get("INSTOCK_SYNC_SKIP_COMPLETE", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _parse_date(s: Optional[str]) -> Optional[datetime.date]:
    if not s or not str(s).strip():
        return None
    t = str(s).strip().replace("/", "-")
    if len(t) == 8 and t.isdigit():
        t = f"{t[:4]}-{t[4:6]}-{t[6:8]}"
    return datetime.datetime.strptime(t[:10], "%Y-%m-%d").date()


def resolve_sync_range(
    date_from: str,
    date_to: str,
) -> Tuple[datetime.date, datetime.date]:
    d0 = _parse_date(date_from)
    if d0 is None:
        import instock.lib.trade_time as trd

        today = datetime.date.today().isoformat()
        ds, _ = trd.get_trade_hist_interval(today)
        d0 = _parse_date(ds) or datetime.date.today()
    d1 = _parse_date(date_to) or datetime.date.today()
    if d0 > d1:
        d0, d1 = d1, d0
    return d0, d1


def _code_bar_bounds(code: str, adjust_type: str) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
    from instock.core.canonical.bar_tables import bar_table_has_adjust_column, resolve_bar_table

    table = resolve_bar_table(adjust_type)
    if not mdb.checkTableIsExist(table):
        return None, None
    c = str(code).zfill(6)[:6]
    if bar_table_has_adjust_column(adjust_type):
        rows = mdb.executeSqlFetch(
            f"SELECT MIN(`date`), MAX(`date`) FROM `{table}` "
            "WHERE code=%s AND adjust_type=%s",
            (c, adjust_type),
        )
    else:
        rows = mdb.executeSqlFetch(
            f"SELECT MIN(`date`), MAX(`date`) FROM `{table}` WHERE code=%s",
            (c,),
        )
    if not rows or not rows[0][0]:
        return None, None
    a, b = rows[0][0], rows[0][1]
    if isinstance(a, datetime.datetime):
        a = a.date()
    if isinstance(b, datetime.datetime):
        b = b.date()
    return a, b


def plan_canonical_sync(
    code: str,
    date_from: str,
    date_to: str,
    *,
    adjust_type: str = "raw",
) -> Dict[str, Any]:
    """
    返回是否可跳过拉取、缺失交易日列表。
    skip=True 表示区间内标准表已覆盖全部期望交易日。
    """
    d0, d1 = resolve_sync_range(date_from, date_to)
    code = str(code).zfill(6)[:6]
    expected = gaps._expected_trade_dates(d0, d1)
    _, _, per_code = gaps.detect_canonical_daily_bar_gaps(
        d0, d1, adjust_type=adjust_type, codes=[code]
    )
    missing = list(per_code.get(code) or [])
    skip = len(missing) == 0 and len(expected) > 0
    return {
        "code": code,
        "adjust_type": adjust_type,
        "date_from": d0.isoformat(),
        "date_to": d1.isoformat(),
        "expected_days": len(expected),
        "missing_dates": missing,
        "skip": skip,
    }


def filter_bars_to_missing_dates(df, missing_iso_dates: List[str]):
    """仅保留待补日期行，减少 merge 写入量。"""
    if df is None or df.empty or not missing_iso_dates:
        return df
    import pandas as pd

    miss = set(missing_iso_dates)
    work = df.copy()
    if "date" not in work.columns:
        if isinstance(work.index, pd.DatetimeIndex):
            work = work.reset_index()
            if work.columns[0] != "date":
                work = work.rename(columns={work.columns[0]: "date"})
        elif work.index.name in ("date", "datetime", None):
            work = work.reset_index()
            first = work.columns[0]
            if first != "date":
                work = work.rename(columns={first: "date"})
        else:
            return work
    work["_d"] = pd.to_datetime(work["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out = work[work["_d"].isin(miss)].drop(columns=["_d"], errors="ignore")
    return out


def get_code_watermark(code: str) -> Dict[str, str]:
    from instock.core.adjustment.corporate_action_store import get_stored_factor_version
    from instock.core.adjustment.schema import ensure_qfq_tables

    ensure_qfq_tables()
    c = str(code).zfill(6)[:6]
    out = {
        "last_raw_date": "",
        "last_factor_version": "",
        "stored_global_factor_version": get_stored_factor_version(),
    }
    if not mdb.checkTableIsExist("cn_stock_qfq_watermark"):
        return out
    rows = mdb.executeSqlFetch(
        "SELECT last_raw_date, last_factor_version FROM cn_stock_qfq_watermark WHERE code=%s",
        (c,),
    )
    if rows and rows[0]:
        if rows[0][0]:
            out["last_raw_date"] = str(rows[0][0])[:10]
        if rows[0][1]:
            out["last_factor_version"] = str(rows[0][1])
    return out


def plan_qfq_derive(
    code: str,
    date_from: str = "",
    date_to: str = "",
    *,
    factor_version: str = "",
) -> Dict[str, Any]:
    """
    判断单股是否需派生 qfq。
    skip=True：区间内 qfq 无缺口且 raw 未超出已派生水位、因子版本一致。
    """
    from instock.core.adjustment.gbbq_reader import gbbq_factor_version

    code = str(code).zfill(6)[:6]
    cur_fv = factor_version or gbbq_factor_version()
    wm = get_code_watermark(code)
    raw_min, raw_max = _code_bar_bounds(code, "raw")
    qfq_min, qfq_max = _code_bar_bounds(code, "qfq")

    if raw_max is None:
        return {
            "code": code,
            "skip": True,
            "reason": "no_raw",
            "missing_dates": [],
        }

    if date_from or date_to:
        d0, d1 = resolve_sync_range(
            date_from or (raw_min.isoformat() if raw_min else "1990-01-01"),
            date_to or datetime.date.today().isoformat(),
        )
    else:
        d0 = raw_min or datetime.date(1990, 1, 1)
        d1 = max(raw_max, datetime.date.today())

    _, _, per_code = gaps.detect_canonical_daily_bar_gaps(
        d0, d1, adjust_type="qfq", codes=[code]
    )
    missing = list(per_code.get(code) or [])

    reasons: List[str] = []
    if missing:
        reasons.append(f"qfq_missing:{len(missing)}")

    wm_raw = _parse_date(wm.get("last_raw_date"))
    if raw_max and (wm_raw is None or raw_max > wm_raw):
        reasons.append("raw_ahead_of_watermark")

    if cur_fv and wm.get("last_factor_version") and cur_fv != wm["last_factor_version"]:
        reasons.append("factor_version_changed")

    if qfq_max is None and raw_max is not None:
        reasons.append("qfq_empty")

    skip = len(reasons) == 0
    return {
        "code": code,
        "skip": skip,
        "reason": "ok" if skip else ",".join(reasons),
        "missing_dates": missing,
        "date_from": d0.isoformat(),
        "date_to": d1.isoformat(),
        "raw_max": raw_max.isoformat() if raw_max else "",
        "qfq_max": qfq_max.isoformat() if qfq_max else "",
        "factor_version": cur_fv,
    }
