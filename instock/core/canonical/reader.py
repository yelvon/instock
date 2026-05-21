# -*- coding: utf-8 -*-
"""回测与业务从标准日线表读取。"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd
import pymysql

import instock.lib.database as mdb
from instock.core.canonical.writer import TABLE_BAR, ensure_canonical_tables

HIST_COLS = [
    "date",
    "open",
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "amplitude",
    "quote_change",
    "ups_downs",
    "turnover",
]


def canonical_read_enabled() -> bool:
    return os.environ.get("INSTOCK_BACKTEST_USE_CANONICAL", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def load_canonical_bars(
    code: str,
    date_start: str,
    date_end: Optional[str] = None,
    adjust_type: str = "raw",
) -> pd.DataFrame:
    """从 cn_stock_daily_bar 读取，列与 CN_STOCK_HIST_DATA 对齐。"""
    ensure_canonical_tables()
    code = str(code).zfill(6)[:6]
    ds = str(date_start).replace("-", "")[:8]
    ds_fmt = f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}" if len(ds) == 8 else date_start
    de_fmt = None
    if date_end:
        de = str(date_end).replace("-", "")[:8]
        de_fmt = f"{de[:4]}-{de[4:6]}-{de[6:8]}" if len(de) == 8 else date_end

    sql = (
        f"SELECT {','.join(HIST_COLS)} FROM `{TABLE_BAR}` "
        "WHERE code=%s AND adjust_type=%s AND date>=%s"
    )
    params: list = [code, adjust_type, ds_fmt]
    if de_fmt:
        sql += " AND date<=%s"
        params.append(de_fmt)
    sql += " ORDER BY date ASC"

    with pymysql.connect(**mdb.MYSQL_CONN_DBAPI) as conn:
        df = pd.read_sql(sql, conn, params=params)
    if df is None or df.empty:
        return pd.DataFrame(columns=HIST_COLS)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df
