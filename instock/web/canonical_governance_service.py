# -*- coding: utf-8 -*-
"""标准行情库治理：覆盖率、冲突、来源贡献。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

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


def get_canonical_summary() -> Dict[str, Any]:
    ensure_canonical_tables()
    if not mdb.checkTableIsExist(TABLE_BAR):
        return {"ready": False, "total_bars": 0, "codes": 0, "suspect": 0, "partial": 0}
    total = mdb.executeSqlCount(f"SELECT COUNT(*) FROM `{TABLE_BAR}`")
    codes = mdb.executeSqlCount(f"SELECT COUNT(DISTINCT code) FROM `{TABLE_BAR}`")
    by_status_raw = mdb.executeSqlFetch(
        f"SELECT quality_status, COUNT(*) FROM `{TABLE_BAR}` GROUP BY quality_status"
    )
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
    by_status = _rows_to_dicts(by_status_raw, ["quality_status", "c"])
    status_map = {r["quality_status"]: int(r["c"]) for r in by_status if r.get("quality_status")}
    by_source = _rows_to_dicts(by_source_raw, ["primary_source", "c"])
    recent = _rows_to_dicts(recent_raw, ["source_provider", "merge_action", "c"])
    return {
        "ready": True,
        "total_bars": total,
        "codes": codes,
        "suspect": status_map.get("suspect", 0),
        "partial": status_map.get("partial", 0),
        "complete": status_map.get("complete", 0),
        "by_primary_source": by_source,
        "recent_contributions": recent,
        "bar_sync_sources": BAR_SYNC_SOURCES,
    }


def get_code_coverage(code: str, adjust_type: str = "raw") -> Dict[str, Any]:
    ensure_canonical_tables()
    code = str(code).zfill(6)[:6]
    rows = mdb.executeSqlFetch(
        f"SELECT MIN(date), MAX(date), COUNT(*) FROM `{TABLE_BAR}` "
        "WHERE code=%s AND adjust_type=%s",
        (code, adjust_type),
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
