# -*- coding: utf-8 -*-
"""各 Provider 字段映射到 tablestructure 列名。"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

# mootdx Reader.daily 常见列名 -> CN_STOCK_HIST_DATA
MOOTDX_BAR_MAP = {
    "date": "date",
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "vol": "volume",
    "volume": "volume",
    "amount": "amount",
}

TENCENT_SPOT_MAP = {
    "pe_ttm": "pe9",
    "pb": "pbnewmrq",
    "turnover_pct": "turnoverrate",
    "mcap_yi": "total_market_cap",
    "float_mcap_yi": "free_cap",
    "pe_static": "dtsyl",
}


AKSHARE_BAR_MAP = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "quote_change",
    "涨跌额": "ups_downs",
    "换手率": "turnover",
}


def _ensure_hist_columns(df: pd.DataFrame, volume_hands_to_shares: bool) -> pd.DataFrame:
    hist_cols = list(
        __import__("instock.core.tablestructure", fromlist=["CN_STOCK_HIST_DATA"]).CN_STOCK_HIST_DATA[
            "columns"
        ].keys()
    )
    for c in hist_cols:
        if c not in df.columns:
            df[c] = None
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if volume_hands_to_shares and "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce") * 100
    keep = [c for c in hist_cols if c in df.columns]
    return df[keep]


def normalize_akshare_bars(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    rename = {k: v for k, v in AKSHARE_BAR_MAP.items() if k in out.columns}
    out = out.rename(columns=rename)
    return _ensure_hist_columns(out, volume_hands_to_shares=True)


def normalize_provider_bars(df: pd.DataFrame, provider_id: str) -> pd.DataFrame:
    pid = str(provider_id or "").lower()
    if pid in ("mootdx_local", "mootdx_online", "mootdx"):
        return normalize_mootdx_bars(df)
    if pid == "akshare":
        return normalize_akshare_bars(df)
    if pid == "tushare":
        from instock.core.data.providers.tushare import normalize_tushare_bars

        return normalize_tushare_bars(df)
    if pid in ("eastmoney", "legacy_cache"):
        out = df.copy()
        if "date" in out.columns:
            out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        return _ensure_hist_columns(out, volume_hands_to_shares=False)
    return normalize_mootdx_bars(df)


def normalize_mootdx_bars(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    if "datetime" in out.columns and "date" not in out.columns:
        out["date"] = pd.to_datetime(out["datetime"]).dt.strftime("%Y-%m-%d")
    # online bars 可能同时有 vol 与 volume，避免 rename 后出现重复列名
    if "vol" in out.columns and "volume" in out.columns:
        out = out.drop(columns=["volume"])
    rename = {k: v for k, v in MOOTDX_BAR_MAP.items() if k in out.columns and k != v}
    out = out.rename(columns=rename)
    return _ensure_hist_columns(out, volume_hands_to_shares=True)


def merge_tencent_valuation(spot_df: pd.DataFrame, tencent_by_code: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    """仅填空/NaN 列，不覆盖东财已有值。"""
    if spot_df is None or spot_df.empty:
        return spot_df
    out = spot_df.copy()
    if "code" not in out.columns:
        return out
    for idx, row in out.iterrows():
        code = str(row["code"]).zfill(6)[:6]
        tv = tencent_by_code.get(code)
        if not tv:
            continue
        for src, dst in TENCENT_SPOT_MAP.items():
            if dst not in out.columns:
                continue
            cur = out.at[idx, dst]
            if cur is None or (isinstance(cur, float) and pd.isna(cur)) or cur == "":
                val = tv.get(src)
                if val is not None and val != "":
                    out.at[idx, dst] = val
    return out
