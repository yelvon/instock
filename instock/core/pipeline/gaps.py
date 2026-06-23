# -*- coding: utf-8 -*-
"""主数据断档检测（规划 data.md §3）：交易日 vs cn_stock_spot 有数据的日期。"""

from __future__ import annotations

import datetime
import logging
from typing import List, Set, Tuple

import instock.core.pipeline.trade_calendar as tcal
import instock.lib.database as mdb


def _dates_in_spot_between(date_from: datetime.date, date_to: datetime.date) -> Set[datetime.date]:
    import instock.core.tablestructure as tbs

    table = tbs.TABLE_CN_STOCK_SPOT["name"]
    if not mdb.checkTableIsExist(table):
        return set()
    sql = (
        f"SELECT DISTINCT `date` FROM `{table}` "
        f"WHERE `date` >= %s AND `date` <= %s ORDER BY `date`"
    )
    rows = mdb.executeSqlFetch(sql, (date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")))
    if not rows:
        return set()
    out: Set[datetime.date] = set()
    for r in rows:
        v = r[0]
        if isinstance(v, datetime.datetime):
            out.add(v.date())
        else:
            out.add(v)
    return out


def _expected_trade_dates(
    date_from: datetime.date, date_to: datetime.date
) -> List[datetime.date]:
    """优先 trade_calendar；若为空则回退到网络交易日集合。"""
    tcal.ensure_table()
    if tcal.table_row_count() > 0:
        return tcal.load_open_dates_between(date_from, date_to)
    from instock.core.pipeline.data_source import get_default_market_data_source

    src = get_default_market_data_source()
    td = src.fetch_trade_dates()
    if not td:
        logging.warning("gaps: trade_calendar 为空且无法拉取交易日历")
        return []
    return sorted(d for d in td if date_from <= d <= date_to)


def expected_trade_dates_in_range(
    date_from: datetime.date, date_to: datetime.date
) -> List[datetime.date]:
    """区间内应为交易日的日期列表（与断档检测同源）。"""
    return _expected_trade_dates(date_from, date_to)


def detect_stock_spot_gaps(
    date_from: datetime.date, date_to: datetime.date
) -> Tuple[List[datetime.date], List[datetime.date]]:
    """
    返回 (缺失交易日列表, 有数据但非交易日的日期列表第二项可选简化).

    第二项：若 trade_calendar 有数据，找出 DB 中有行但不在日历的 date（通常为空）。
    """
    expected = _expected_trade_dates(date_from, date_to)
    actual = _dates_in_spot_between(date_from, date_to)
    exp_set = set(expected)
    missing = sorted(exp_set - actual)
    extra = sorted(actual - exp_set) if exp_set else []
    return missing, extra


def _dates_in_table_between(
    table: str, date_from: datetime.date, date_to: datetime.date, date_col: str = "date"
) -> Set[datetime.date]:
    if not mdb.checkTableIsExist(table):
        return set()
    sql = (
        f"SELECT DISTINCT `{date_col}` FROM `{table}` "
        f"WHERE `{date_col}` >= %s AND `{date_col}` <= %s ORDER BY `{date_col}`"
    )
    rows = mdb.executeSqlFetch(sql, (date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")))
    if not rows:
        return set()
    out: Set[datetime.date] = set()
    for r in rows:
        v = r[0]
        if isinstance(v, datetime.datetime):
            out.add(v.date())
        else:
            out.add(v)
    return out


def detect_trade_calendar_gaps(
    date_from: datetime.date, date_to: datetime.date
) -> Tuple[List[datetime.date], List[datetime.date]]:
    """trade_calendar 相对网络/回退交易日集的缺失日。"""
    tcal.ensure_table()
    expected = _expected_trade_dates(date_from, date_to)
    if not mdb.checkTableIsExist(tcal.TABLE_NAME):
        return list(expected), []
    sql = (
        f"SELECT `cal_date` FROM `{tcal.TABLE_NAME}` "
        f"WHERE `is_open` = 1 AND `cal_date` >= %s AND `cal_date` <= %s"
    )
    rows = mdb.executeSqlFetch(sql, (date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")))
    actual: Set[datetime.date] = set()
    for r in rows or []:
        v = r[0]
        actual.add(v.date() if isinstance(v, datetime.datetime) else v)
    exp_set = set(expected)
    missing = sorted(exp_set - actual)
    extra = sorted(actual - exp_set) if exp_set else []
    return missing, extra


def detect_table_date_gaps(
    table: str,
    date_from: datetime.date,
    date_to: datetime.date,
    *,
    date_col: str = "date",
) -> Tuple[List[datetime.date], List[datetime.date]]:
    """通用衍生表：相对期望交易日的缺日。"""
    expected = _expected_trade_dates(date_from, date_to)
    actual = _dates_in_table_between(table, date_from, date_to, date_col=date_col)
    exp_set = set(expected)
    missing = sorted(exp_set - actual)
    extra = sorted(actual - exp_set) if exp_set else []
    return missing, extra


def _dates_in_canonical_bar_for_code(
    code: str,
    date_from: datetime.date,
    date_to: datetime.date,
    adjust_type: str = "raw",
) -> Set[datetime.date]:
    from instock.core.canonical.bar_tables import bar_table_has_adjust_column, resolve_bar_table

    table = resolve_bar_table(adjust_type)
    if not mdb.checkTableIsExist(table):
        return set()
    c = str(code).zfill(6)[:6]
    if bar_table_has_adjust_column(adjust_type):
        sql = (
            f"SELECT DISTINCT `date` FROM `{table}` "
            "WHERE `code` = %s AND `adjust_type` = %s "
            "AND `date` >= %s AND `date` <= %s ORDER BY `date`"
        )
        params = (c, adjust_type, date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"))
    else:
        sql = (
            f"SELECT DISTINCT `date` FROM `{table}` "
            "WHERE `code` = %s AND `date` >= %s AND `date` <= %s ORDER BY `date`"
        )
        params = (c, date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"))
    rows = mdb.executeSqlFetch(sql, params)
    if not rows:
        return set()
    out: Set[datetime.date] = set()
    for r in rows:
        v = r[0]
        out.add(v.date() if isinstance(v, datetime.datetime) else v)
    return out


def batch_canonical_dates_by_code(
    codes: list,
    date_from: datetime.date,
    date_to: datetime.date,
    adjust_type: str = "raw",
) -> dict:
    """批量查询各 code 在区间内的已有 date，返回 {code: set(date)}。"""
    from instock.core.canonical.bar_tables import bar_table_has_adjust_column, resolve_bar_table

    norm = [str(c).zfill(6)[:6] for c in (codes or []) if str(c).strip()]
    out: dict = {c: set() for c in norm}
    if not norm:
        return out
    table = resolve_bar_table(adjust_type)
    if not mdb.checkTableIsExist(table):
        return out
    chunk = 400
    d0 = date_from.strftime("%Y-%m-%d")
    d1 = date_to.strftime("%Y-%m-%d")
    for i in range(0, len(norm), chunk):
        part = norm[i : i + chunk]
        placeholders = ",".join(["%s"] * len(part))
        if bar_table_has_adjust_column(adjust_type):
            sql = (
                f"SELECT `code`, `date` FROM `{table}` "
                f"WHERE `code` IN ({placeholders}) AND `adjust_type`=%s "
                "AND `date` >= %s AND `date` <= %s"
            )
            params = tuple(part) + (adjust_type, d0, d1)
        else:
            sql = (
                f"SELECT `code`, `date` FROM `{table}` "
                f"WHERE `code` IN ({placeholders}) AND `date` >= %s AND `date` <= %s"
            )
            params = tuple(part) + (d0, d1)
        rows = mdb.executeSqlFetch(sql, params)
        for r in rows or []:
            c = str(r[0]).zfill(6)[:6]
            v = r[1]
            if isinstance(v, datetime.datetime):
                v = v.date()
            if c in out:
                out[c].add(v)
    return out


def detect_canonical_daily_bar_gaps(
    date_from: datetime.date,
    date_to: datetime.date,
    *,
    adjust_type: str = "raw",
    codes=None,
) -> Tuple[List[datetime.date], List[datetime.date], dict]:
    """
    标准日线缺日检测。
    返回 (全市场缺日, extra, per_code_missing) 其中 per_code_missing 为 {code: [iso dates]}。
    """
    expected = _expected_trade_dates(date_from, date_to)
    exp_set = set(expected)
    from instock.core.canonical.bar_tables import bar_table_has_adjust_column, resolve_bar_table

    table = resolve_bar_table(adjust_type)
    per_code: dict = {}

    norm_codes = [str(c).zfill(6)[:6] for c in (codes or []) if str(c).strip()]
    if norm_codes:
        union_missing: Set[datetime.date] = set()
        for code in norm_codes:
            actual = _dates_in_canonical_bar_for_code(code, date_from, date_to, adjust_type)
            missing = sorted(exp_set - actual)
            if missing:
                per_code[code] = [d.isoformat() for d in missing]
                union_missing.update(missing)
        return sorted(union_missing), [], per_code

    if not mdb.checkTableIsExist(table):
        return list(expected), [], per_code

    if bar_table_has_adjust_column(adjust_type):
        sql = (
            f"SELECT DISTINCT `date` FROM `{table}` "
            "WHERE `adjust_type` = %s AND `date` >= %s AND `date` <= %s ORDER BY `date`"
        )
        params = (adjust_type, date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"))
    else:
        sql = (
            f"SELECT DISTINCT `date` FROM `{table}` "
            "WHERE `date` >= %s AND `date` <= %s ORDER BY `date`"
        )
        params = (date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"))
    rows = mdb.executeSqlFetch(sql, params)
    actual: Set[datetime.date] = set()
    for r in rows or []:
        v = r[0]
        actual.add(v.date() if isinstance(v, datetime.datetime) else v)
    missing = sorted(exp_set - actual)
    extra = sorted(actual - exp_set) if exp_set else []
    return missing, extra, per_code


def detect_canonical_quality_issues(
    date_from: datetime.date,
    date_to: datetime.date,
    *,
    adjust_type: str = "raw",
    codes=None,
    min_completeness_score: int = 80,
) -> dict:
    """统计回测区间内标准日线质量问题。"""
    from instock.core.canonical.bar_tables import resolve_bar_table

    table = resolve_bar_table(adjust_type)
    out = {"suspect": 0, "partial": 0, "low_score": 0}
    if not mdb.checkTableIsExist(table):
        return out

    clauses = ["`date` >= %s", "`date` <= %s"]
    params: list = [date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")]
    norm_codes = [str(c).zfill(6)[:6] for c in (codes or []) if str(c).strip()]
    if norm_codes:
        placeholders = ",".join(["%s"] * len(norm_codes))
        clauses.append(f"`code` IN ({placeholders})")
        params.extend(norm_codes)
    where = " AND ".join(clauses)
    sql = (
        "SELECT "
        "SUM(CASE WHEN `quality_status`='suspect' THEN 1 ELSE 0 END) AS suspect, "
        "SUM(CASE WHEN `quality_status`='partial' THEN 1 ELSE 0 END) AS partial, "
        "SUM(CASE WHEN `completeness_score` < %s THEN 1 ELSE 0 END) AS low_score "
        f"FROM `{table}` WHERE {where}"
    )
    rows = mdb.executeSqlFetch(sql, tuple([min_completeness_score] + params)) or []
    if not rows:
        return out
    row = rows[0]
    return {
        "suspect": int(row[0] or 0),
        "partial": int(row[1] or 0),
        "low_score": int(row[2] or 0),
    }
