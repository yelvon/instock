# -*- coding: utf-8 -*-
"""主数据断档检测（规划 data.md §3）：交易日 vs cn_stock_spot 有数据的日期。"""

from __future__ import annotations

import datetime
import logging
from typing import List, Set, Tuple

import instock.core.tablestructure as tbs
import instock.core.pipeline.trade_calendar as tcal
import instock.lib.database as mdb
from instock.core.pipeline.data_source import get_default_market_data_source


def _dates_in_spot_between(date_from: datetime.date, date_to: datetime.date) -> Set[datetime.date]:
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
