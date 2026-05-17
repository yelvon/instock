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
    hist_cols = list(
        __import__("instock.core.tablestructure", fromlist=["CN_STOCK_HIST_DATA"]).CN_STOCK_HIST_DATA[
            "columns"
        ].keys()
    )
    for c in hist_cols:
        if c not in out.columns:
            out[c] = None
    keep = [c for c in hist_cols if c in out.columns]
    out = out[keep]
    if "volume" in out.columns:
        # mootdx 日线成交量多为手，与 stockfetch 东财路径一致转为股
        out["volume"] = pd.to_numeric(out["volume"], errors="coerce") * 100
    return out


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
