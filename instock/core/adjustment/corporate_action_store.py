# -*- coding: utf-8 -*-
"""除权事件入库与读取。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import pymysql

import instock.lib.database as mdb
from instock.core.adjustment.gbbq_reader import events_for_code, read_gbbq_dataframe
from instock.core.adjustment.schema import ensure_qfq_tables

GLOBAL_WATERMARK_CODE = "__global__"


def get_stored_factor_version() -> str:
    ensure_qfq_tables()
    if not mdb.checkTableIsExist("cn_stock_qfq_watermark"):
        return ""
    rows = mdb.executeSqlFetch(
        "SELECT last_factor_version FROM cn_stock_qfq_watermark WHERE code=%s",
        (GLOBAL_WATERMARK_CODE,),
    )
    if not rows or not rows[0][0]:
        return ""
    return str(rows[0][0])


def set_global_factor_version(version: str) -> None:
    ensure_qfq_tables()
    sql = """
    INSERT INTO cn_stock_qfq_watermark (code, last_factor_version, last_derived_at)
    VALUES (%s, %s, NOW())
    ON DUPLICATE KEY UPDATE last_factor_version=VALUES(last_factor_version)
    """
    mdb.executeSql(sql, (GLOBAL_WATERMARK_CODE, version))


def ingest_gbbq_to_db(tdx_root: Optional[str] = None) -> Dict[str, Any]:
    from instock.core.adjustment.gbbq_reader import gbbq_factor_version

    ensure_qfq_tables()
    gbbq = read_gbbq_dataframe(tdx_root)
    version = gbbq_factor_version(tdx_root)
    if gbbq.empty:
        return {"ok": False, "error": "gbbq 为空", "factor_version": version}

    sub = gbbq[gbbq["category"] == 1].copy()
    conn = pymysql.connect(**mdb.MYSQL_CONN_DBAPI)
    n = 0
    try:
        with conn.cursor() as cur:
            for _, row in sub.iterrows():
                ex = row.get("ex_date")
                if pd.isna(ex):
                    continue
                cur.execute(
                    """
                    INSERT INTO cn_stock_corporate_action
                    (code, ex_date, event_type, category, cash_div, stock_div,
                     rights_ratio, rights_price, source, factor_version)
                    VALUES (%s,%s,'xdxr',%s,%s,%s,%s,%s,'tdx_gbbq',%s)
                    ON DUPLICATE KEY UPDATE
                      cash_div=VALUES(cash_div), stock_div=VALUES(stock_div),
                      rights_ratio=VALUES(rights_ratio), rights_price=VALUES(rights_price),
                      factor_version=VALUES(factor_version), ingested_at=CURRENT_TIMESTAMP
                    """,
                    (
                        str(row["code"]).zfill(6)[:6],
                        pd.Timestamp(ex).strftime("%Y-%m-%d"),
                        int(row.get("category") or 1),
                        float(row.get("hongli_panqianliutong") or 0),
                        float(row.get("songgu_qianzongguben") or 0),
                        float(row.get("peigu_houzongguben") or 0),
                        float(row.get("peigujia_qianzongguben") or 0),
                        version,
                    ),
                )
                n += 1
        conn.commit()
    finally:
        conn.close()
    set_global_factor_version(version)
    return {"ok": True, "rows": n, "factor_version": version}


def load_xdxr_for_code(code: str) -> pd.DataFrame:
    """从 DB 或 gbbq 文件加载单股 xdxr 事件。"""
    c = str(code).zfill(6)[:6]
    if mdb.checkTableIsExist("cn_stock_corporate_action"):
        rows = mdb.executeSqlFetch(
            """
            SELECT ex_date, cash_div, stock_div, rights_ratio, rights_price
            FROM cn_stock_corporate_action
            WHERE code=%s AND source='tdx_gbbq' ORDER BY ex_date
            """,
            (c,),
        )
        if rows:
            data = []
            for r in rows:
                data.append(
                    {
                        "ex_date": pd.to_datetime(r[0]),
                        "fenhong": float(r[1] or 0),
                        "songzhuangu": float(r[2] or 0),
                        "peigu": float(r[3] or 0),
                        "peigujia": float(r[4] or 0),
                    }
                )
            df = pd.DataFrame(data).set_index("ex_date")
            return df
    try:
        gbbq = read_gbbq_dataframe()
        ev = events_for_code(gbbq, c)
        if ev.empty:
            return pd.DataFrame()
        return ev.set_index("ex_date")[["fenhong", "peigu", "peigujia", "songzhuangu"]]
    except Exception:
        return pd.DataFrame()


def qfq_table_has_rows() -> bool:
    ensure_qfq_tables()
    from instock.core.canonical.bar_tables import TABLE_BAR_QFQ

    if not mdb.checkTableIsExist(TABLE_BAR_QFQ):
        return False
    rows = mdb.executeSqlFetch(f"SELECT 1 FROM `{TABLE_BAR_QFQ}` LIMIT 1")
    return bool(rows)


def update_watermark(code: str, last_raw_date: Optional[str], factor_version: str) -> None:
    ensure_qfq_tables()
    c = str(code).zfill(6)[:6]
    mdb.executeSql(
        """
        INSERT INTO cn_stock_qfq_watermark (code, last_raw_date, last_factor_version, last_derived_at)
        VALUES (%s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
          last_raw_date=VALUES(last_raw_date),
          last_factor_version=VALUES(last_factor_version),
          last_derived_at=NOW()
        """,
        (c, last_raw_date, factor_version),
    )
