# -*- coding: utf-8 -*-
"""标准行情库治理：覆盖率、冲突、来源贡献。"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import instock.lib.database as mdb
from instock.core.canonical.writer import TABLE_BAR, TABLE_CONTRIB, ensure_canonical_tables
BAR_SYNC_SOURCES = [
    "mootdx",
    "tushare",
    "akshare",
    "eastmoney",
]


def _rows_to_dicts(rows, columns: List[str]) -> List[Dict[str, Any]]:
    out = []
    for row in rows or []:
        if isinstance(row, dict):
            out.append(row)
        else:
            out.append({columns[i]: row[i] for i in range(min(len(columns), len(row)))})
    return out


_SUMMARY_CACHE_TTL_SEC = 60
_summary_cache_lock = Lock()
_summary_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def invalidate_canonical_summary_cache() -> None:
    with _summary_cache_lock:
        _summary_cache.clear()


def _aggregate_core_stats() -> Dict[str, int]:
    """单次表扫描汇总行数、股票数与质量分布（替代多次 COUNT/GROUP BY）。"""
    row = (mdb.executeSqlFetch(
        f"SELECT COUNT(*) AS total, COUNT(DISTINCT code) AS codes, "
        f"SUM(quality_status = 'complete') AS complete, "
        f"SUM(quality_status = 'partial') AS partial, "
        f"SUM(quality_status = 'suspect') AS suspect "
        f"FROM `{TABLE_BAR}`"
    ) or [(0, 0, 0, 0, 0)])[0]
    return {
        "total_bars": int(row[0] or 0),
        "codes": int(row[1] or 0),
        "complete": int(row[2] or 0),
        "partial": int(row[3] or 0),
        "suspect": int(row[4] or 0),
    }


def _build_canonical_summary(*, light: bool) -> Dict[str, Any]:
    ensure_canonical_tables()
    if not mdb.checkTableIsExist(TABLE_BAR):
        return {
            "ready": False,
            "total_bars": 0,
            "codes": 0,
            "suspect": 0,
            "partial": 0,
            "complete": 0,
            "bar_sync_sources": BAR_SYNC_SOURCES,
        }
    core = _aggregate_core_stats()
    out: Dict[str, Any] = {
        "ready": True,
        "bar_sync_sources": BAR_SYNC_SOURCES,
        **core,
    }
    from instock.core.canonical.bar_tables import TABLE_BAR_QFQ
    from instock.core.adjustment.schema import ensure_qfq_tables

    ensure_qfq_tables()
    if mdb.checkTableIsExist(TABLE_BAR_QFQ):
        qrow = (mdb.executeSqlFetch(
            f"SELECT COUNT(*), COUNT(DISTINCT code) FROM `{TABLE_BAR_QFQ}`"
        ) or [(0, 0)])[0]
        out["qfq_total_bars"] = int(qrow[0] or 0)
        out["qfq_codes"] = int(qrow[1] or 0)
    else:
        out["qfq_total_bars"] = 0
        out["qfq_codes"] = 0
    if light:
        return out
    by_source_raw = mdb.executeSqlFetch(
        f"SELECT primary_source, COUNT(*) FROM `{TABLE_BAR}` "
        "WHERE primary_source IS NOT NULL GROUP BY primary_source ORDER BY 2 DESC LIMIT 20"
    )
    recent_raw = []
    if mdb.checkTableIsExist(TABLE_CONTRIB):
        recent_raw = mdb.executeSqlFetch(
            f"SELECT source_provider, merge_action, COUNT(*) FROM `{TABLE_CONTRIB}` "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
            "GROUP BY source_provider, merge_action ORDER BY 3 DESC LIMIT 50"
        ) or []
    out["by_primary_source"] = _rows_to_dicts(by_source_raw, ["primary_source", "c"])
    out["recent_contributions"] = _rows_to_dicts(
        recent_raw, ["source_provider", "merge_action", "c"]
    )
    return out


def get_canonical_summary(*, light: bool = False, refresh: bool = False) -> Dict[str, Any]:
    cache_key = "light" if light else "full"
    now = time.time()
    if not refresh:
        with _summary_cache_lock:
            hit = _summary_cache.get(cache_key)
            if hit and now - hit[0] < _SUMMARY_CACHE_TTL_SEC:
                return dict(hit[1])
    data = _build_canonical_summary(light=light)
    with _summary_cache_lock:
        _summary_cache[cache_key] = (now, data)
    return data


def get_code_coverage(code: str, adjust_type: str = "raw") -> Dict[str, Any]:
    from instock.core.canonical.bar_tables import bar_table_has_adjust_column, resolve_bar_table

    ensure_canonical_tables()
    code = str(code).zfill(6)[:6]
    table = resolve_bar_table(adjust_type)
    if bar_table_has_adjust_column(adjust_type):
        rows = mdb.executeSqlFetch(
            f"SELECT MIN(date), MAX(date), COUNT(*) FROM `{table}` "
            "WHERE code=%s AND adjust_type=%s",
            (code, adjust_type),
        )
    else:
        rows = mdb.executeSqlFetch(
            f"SELECT MIN(date), MAX(date), COUNT(*) FROM `{table}` WHERE code=%s",
            (code,),
        )
    r = (rows or [(None, None, 0)])[0]
    contrib_raw = []
    if mdb.checkTableIsExist(TABLE_CONTRIB):
        contrib_raw = mdb.executeSqlFetch(
            f"SELECT source_provider, merge_action, COUNT(*) FROM `{TABLE_CONTRIB}` "
            "WHERE code=%s AND adjust_type=%s GROUP BY source_provider, merge_action",
            (code, adjust_type),
        ) or []
    return {
        "code": code,
        "date_min": str(r[0] or ""),
        "date_max": str(r[1] or ""),
        "bar_count": int(r[2] or 0),
        "contributions": _rows_to_dicts(
            contrib_raw, ["source_provider", "merge_action", "c"]
        ),
    }
