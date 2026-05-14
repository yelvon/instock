# -*- coding: utf-8 -*-
"""交易日历表 trade_calendar：本地对齐交易日轴，供断档检测与 H6 校验。"""

from __future__ import annotations

import datetime
import logging
from typing import Iterable, List, Optional, Set

import instock.lib.database as mdb

TABLE_NAME = "trade_calendar"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS `{TABLE_NAME}` (
  `cal_date` date NOT NULL,
  `is_open` tinyint NOT NULL DEFAULT 1,
  `synced_at` datetime DEFAULT NULL,
  PRIMARY KEY (`cal_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
"""

_UPSERT_SQL = f"""
INSERT INTO `{TABLE_NAME}` (`cal_date`, `is_open`, `synced_at`)
VALUES (%s, 1, NOW())
ON DUPLICATE KEY UPDATE `is_open` = VALUES(`is_open`), `synced_at` = VALUES(`synced_at`);
"""


def ensure_table() -> None:
    """若表不存在则创建（幂等）。"""
    mdb.executeSql(_CREATE_SQL)


def upsert_open_dates(dates: Iterable[datetime.date]) -> int:
    """将给定日期标记为交易日（is_open=1）。返回 executemany 批次数。"""
    uniq = sorted(set(dates))
    if not uniq:
        return 0
    conn = mdb.get_connection()
    if conn is None:
        logging.error("trade_calendar.upsert_open_dates: 数据库连接失败")
        return 0
    batch = [(d,) for d in uniq]
    try:
        with conn.cursor() as cur:
            cur.executemany(_UPSERT_SQL, batch)
        return len(batch)
    finally:
        conn.close()


def sync_from_trade_date_set(trade_dates: Optional[Set[datetime.date]]) -> int:
    """从外部提供的交易日集合同步到 trade_calendar。"""
    if not trade_dates:
        logging.warning("trade_calendar.sync_from_trade_date_set: 无交易日数据，跳过")
        return 0
    ensure_table()
    return upsert_open_dates(trade_dates)


def load_open_dates_between(
    date_from: datetime.date, date_to: datetime.date
) -> List[datetime.date]:
    """读取区间内标记为交易日的日期（有序）。"""
    ensure_table()
    conn = mdb.get_connection()
    if conn is None:
        return []
    sql = (
        f"SELECT `cal_date` FROM `{TABLE_NAME}` "
        f"WHERE `is_open` = 1 AND `cal_date` >= %s AND `cal_date` <= %s ORDER BY `cal_date`"
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (date_from, date_to))
            rows = cur.fetchall()
    finally:
        conn.close()
    if not rows:
        return []
    out: List[datetime.date] = []
    for r in rows:
        v = r[0]
        if isinstance(v, datetime.datetime):
            out.append(v.date())
        else:
            out.append(v)
    return out


def table_row_count() -> int:
    ensure_table()
    conn = mdb.get_connection()
    if conn is None:
        return 0
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM `{TABLE_NAME}`")
            r = cur.fetchone()
            return int(r[0]) if r else 0
    finally:
        conn.close()


def sync_from_network() -> int:
    """从默认数据源拉取交易日历并写入 trade_calendar。"""
    from instock.core.pipeline.data_source import get_default_market_data_source

    dates = get_default_market_data_source().fetch_trade_dates()
    return sync_from_trade_date_set(dates)
