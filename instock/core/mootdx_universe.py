#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mootdx 全市场证券列表：在线 stocks + 本地 vipdoc 扫描。"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional

import pandas as pd

import instock.core.stockfetch as stf
import instock.lib.database as mdb
import instock.core.tablestructure as tbs

_log = logging.getLogger(__name__)

TABLE_NAME = "cn_stock_universe"
LogFn = Optional[Callable[[str], None]]


def _log(log: LogFn, msg: str) -> None:
    if log:
        log(msg)
    else:
        _log.info(msg)


def ensure_cn_stock_universe_table() -> None:
    if mdb.checkTableIsExist(TABLE_NAME):
        return
    tdef = tbs.TABLE_CN_STOCK_UNIVERSE
    empty = pd.DataFrame({k: [] for k in tdef["columns"].keys()})
    ct = tbs.get_field_types(tdef["columns"])
    mdb.insert_db_from_df(empty, TABLE_NAME, ct, False, "`code`")


def fetch_universe_mootdx_online(log: LogFn = None) -> pd.DataFrame:
    """从 mootdx 在线行情拉沪/深证券列表，过滤为 A 股。"""
    from instock.core.data.providers.mootdx_online import _quotes

    c = _quotes()
    frames: List[pd.DataFrame] = []
    for market_id, label in ((0, "SH"), (1, "SZ")):
        _log(log, f"mootdx stocks(market={market_id}/{label}) …")
        raw = c.stocks(market_id)
        if raw is None or raw.empty:
            _log(log, f"  {label} 返回空")
            continue
        part = raw.copy()
        if "code" not in part.columns:
            _log(log, f"  {label} 无 code 列")
            continue
        part["code"] = part["code"].astype(str).str.zfill(6)
        part["name"] = part["name"].astype(str) if "name" in part.columns else ""
        part["market"] = label
        frames.append(part[["code", "name", "market"]])
        _log(log, f"  {label} 原始 {len(raw)} 条")
    if not frames:
        return pd.DataFrame(columns=["code", "name", "market", "source_provider", "updated_at"])
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["code"], keep="first")
    before = len(out)
    out = out.loc[out["code"].apply(stf.is_a_stock)]
    before2 = len(out)
    out = out.loc[
        out.apply(
            lambda r: stf.is_tradeable_a_share(r["code"], r.get("name", "")),
            axis=1,
        )
    ]
    _log(log, f"A 股过滤：{before} → {before2} 条；剔除指数/债基：{before2} → {len(out)} 条")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out["source_provider"] = "mootdx_online"
    out["updated_at"] = now
    return out


def fetch_universe_from_tdx_dir(tdx_dir: str, log: LogFn = None) -> pd.DataFrame:
    """从本地通达信 vipdoc 目录扫描 .day 文件名作为代码表（仅代码+市场）。"""
    root = Path(tdx_dir)
    rows: List[dict] = []
    for sub, mkt in (("sh/lday", "SH"), ("sz/lday", "SZ")):
        d = root / "vipdoc" / sub
        if not d.is_dir():
            _log(log, f"跳过不存在目录 {d}")
            continue
        n = 0
        for p in d.glob("*.day"):
            code = p.stem
            if len(code) >= 6:
                code = code[-6:]
            code = str(code).zfill(6)
            if stf.is_a_stock(code):
                rows.append({"code": code, "name": "", "market": mkt})
                n += 1
        _log(log, f"扫描 {d}：{n} 个 A 股日线文件")
    if not rows:
        return pd.DataFrame(columns=["code", "name", "market", "source_provider", "updated_at"])
    out = pd.DataFrame(rows).drop_duplicates(subset=["code"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out["source_provider"] = "mootdx_local"
    out["updated_at"] = now
    return out


def upsert_universe_df(df: pd.DataFrame) -> int:
    ensure_cn_stock_universe_table()
    if df is None or df.empty:
        return 0
    tdef = tbs.TABLE_CN_STOCK_UNIVERSE
    cols = list(tdef["columns"].keys())
    data = df[cols].copy()
    ct = tbs.get_field_types(tdef["columns"])
    # 全量替换：简单可靠
    mdb.executeSql(f"DELETE FROM `{TABLE_NAME}`")
    mdb.insert_db_from_df(data, TABLE_NAME, ct, False, "`code`")
    return len(data)


def load_universe_codes(limit: Optional[int] = None) -> List[str]:
    ensure_cn_stock_universe_table()
    if not mdb.checkTableIsExist(TABLE_NAME):
        return []
    sql = f"SELECT `code` FROM `{TABLE_NAME}` ORDER BY `code`"
    if limit and limit > 0:
        sql += f" LIMIT {int(limit)}"
    rows = mdb.executeSqlFetch(sql)
    if not rows:
        return []
    return [str(r[0]).zfill(6) for r in rows]


def count_universe() -> int:
    ensure_cn_stock_universe_table()
    if not mdb.checkTableIsExist(TABLE_NAME):
        return 0
    rows = mdb.executeSqlFetch(f"SELECT COUNT(*) FROM `{TABLE_NAME}`")
    return int(rows[0][0]) if rows else 0
