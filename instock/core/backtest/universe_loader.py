# -*- coding: utf-8 -*-
"""回测股票池：手工 codes / 选股表 / 策略信号表。"""

from __future__ import annotations

import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple

import instock.lib.database as mdb
import pymysql


def _tbs():
    import instock.core.tablestructure as tbs

    return tbs


def _strategy_tables() -> Set[str]:
    tbs = _tbs()
    return {item["name"] for item in tbs.TABLE_CN_STOCK_STRATEGIES}


def _allowed_selection_tables() -> Set[str]:
    tbs = _tbs()
    return {tbs.TABLE_CN_STOCK_SELECTION["name"]}


def _zcode(v: Any) -> str:
    return str(v).strip().zfill(6)[:6]


def universe_type(payload: Dict[str, Any]) -> str:
    uni = payload.get("universe") or {}
    if isinstance(uni, dict):
        t = str(uni.get("type") or "codes").strip().lower()
        return t or "codes"
    return "codes"


def max_universe_size(payload: Dict[str, Any]) -> int:
    uni = payload.get("universe") or {}
    if isinstance(uni, dict) and uni.get("maxUniverseSize"):
        return max(1, int(uni["maxUniverseSize"]))
    import os

    return int(os.environ.get("INSTOCK_BACKTEST_MAX_UNIVERSE", "500"))


def _table_meta(table: str) -> Tuple[str, str]:
    table = str(table or "").strip()
    if table in _strategy_tables():
        return table, "date"
    if table in _allowed_selection_tables():
        return table, "date"
    raise ValueError(f"不支持的 universe 表: {table}")


def _build_filter_sql(
    table: str, filters: Optional[Dict[str, Any]]
) -> Tuple[str, List[Any]]:
    if not filters:
        return "", []
    cols = set()
    tbs = _tbs()
    if table == tbs.TABLE_CN_STOCK_SELECTION["name"]:
        cols = set(tbs.TABLE_CN_STOCK_SELECTION["columns"].keys())
    elif table in _strategy_tables():
        cols = set(tbs.TABLE_CN_STOCK_FOREIGN_KEY["columns"].keys())
    parts: List[str] = []
    args: List[Any] = []
    for k, v in (filters or {}).items():
        if k not in cols:
            continue
        parts.append(f"`{k}`=%s")
        args.append(v)
    if not parts:
        return "", []
    return " AND " + " AND ".join(parts), args


@lru_cache(maxsize=4096)
def _load_daily_codes_cached(table: str, date_str: str, filter_key: str) -> Tuple[str, ...]:
    del filter_key  # filter_key encodes filters for cache key only
    date_field, _ = _table_meta(table)
    sql = f"SELECT DISTINCT `code` FROM `{table}` WHERE `{date_field}`=%s ORDER BY `code`"
    rows = mdb.executeSqlFetch(sql, (date_str,))
    return tuple(_zcode(r[0]) for r in rows if r and r[0])


def load_daily_codes(
    table: str,
    date_str: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
) -> List[str]:
    table, date_field = _table_meta(table)
    filter_sql, filter_args = _build_filter_sql(table, filters)
    if not filter_sql:
        return list(_load_daily_codes_cached(table, date_str, ""))
    sql = f"SELECT DISTINCT `code` FROM `{table}` WHERE `{date_field}`=%s{filter_sql} ORDER BY `code`"
    rows = mdb.executeSqlFetch(sql, (date_str, *filter_args))
    return [_zcode(r[0]) for r in rows if r and r[0]]


def load_daily_rows(
    table: str,
    date_str: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    table, date_field = _table_meta(table)
    filter_sql, filter_args = _build_filter_sql(table, filters)
    sql = f"SELECT * FROM `{table}` WHERE `{date_field}`=%s{filter_sql}"
    with mdb.connection_ctx() as conn:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, (date_str, *filter_args))
            rows = cur.fetchall()
    return list(rows or [])


def load_codes_for_range(
    table: str,
    date_from: str,
    date_to: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 500,
) -> List[str]:
    """回测区间内出现过的全部 code（去重）。"""
    table, date_field = _table_meta(table)
    filter_sql, filter_args = _build_filter_sql(table, filters)
    sql = (
        f"SELECT DISTINCT `code` FROM `{table}` WHERE `{date_field}`>=%s AND `{date_field}`<=%s"
        f"{filter_sql} ORDER BY `code` LIMIT %s"
    )
    rows = mdb.executeSqlFetch(sql, (date_from, date_to, *filter_args, int(limit)))
    return [_zcode(r[0]) for r in rows if r and r[0]]


def resolve_universe_codes(payload: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
    """解析 payload.universe，返回 (codes, universe_meta)。"""
    uni = payload.get("universe") or {}
    if not isinstance(uni, dict):
        uni = {}
    ut = str(uni.get("type") or "codes").strip().lower() or "codes"
    date_from, date_to = payload.get("_date_from"), payload.get("_date_to")
    if ut == "codes":
        codes = uni.get("codes") or []
        if isinstance(codes, str):
            codes = [x.strip() for x in codes.replace("\n", ",").split(",")]
        out = [_zcode(c) for c in codes if str(c).strip()]
        return (out[:30] or ["600000"], {"type": "codes", "codes": out[:30] or ["600000"]})
    if ut in ("selection_table", "strategy_table"):
        table = str(uni.get("table") or "").strip()
        if ut == "selection_table" and not table:
            tbs = _tbs()
            table = tbs.TABLE_CN_STOCK_SELECTION["name"]
        if ut == "strategy_table" and not table:
            table = "cn_stock_strategy_enter"
        filters = uni.get("filter") if isinstance(uni.get("filter"), dict) else None
        if not date_from or not date_to:
            raise ValueError("表驱动股票池需要 dateFrom/dateTo")
        codes = load_codes_for_range(
            table,
            str(date_from),
            str(date_to),
            filters=filters,
            limit=max_universe_size(payload),
        )
        if not codes:
            raise ValueError(f"表 {table} 在 {date_from}~{date_to} 无候选股票")
        meta = {
            "type": ut,
            "table": table,
            "filters": filters or {},
            "codes": codes,
        }
        return codes, meta
    raise ValueError(f"未知 universe.type: {ut}")


def check_table_universe_coverage(
    table: str,
    date_from: datetime.date,
    date_to: datetime.date,
    trade_dates: List[datetime.date],
) -> Tuple[List[str], int]:
    """返回缺失交易日与区间内总行数。"""
    table, date_field = _table_meta(table)
    sql = (
        f"SELECT `{date_field}`, COUNT(*) FROM `{table}` "
        f"WHERE `{date_field}`>=%s AND `{date_field}`<=%s GROUP BY `{date_field}`"
    )
    rows = mdb.executeSqlFetch(sql, (date_from.isoformat(), date_to.isoformat()))
    present = {str(r[0])[:10] for r in rows if r}
    missing = [d.isoformat() for d in trade_dates if d.isoformat() not in present]
    total = sum(int(r[1]) for r in rows if r and len(r) > 1)
    return missing, total
