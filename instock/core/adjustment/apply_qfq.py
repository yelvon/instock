# -*- coding: utf-8 -*-
"""前复权价格变换（对齐通达信 baoli_qfq 思路）。"""

from __future__ import annotations

import pandas as pd


def apply_baoli_qfq(df: pd.DataFrame, xdxr: pd.DataFrame) -> pd.DataFrame:
    """
    对 index=date 的 OHLC 做前复权；xdxr 含 fenhong/peigu/peigujia/songzhuangu，index 为 ex_date。
    算法来源：mootdx.tools.reversion.baoli_qfq
    """
    if df is None or df.empty or xdxr is None or xdxr.empty:
        return df
    out = df.copy()
    peigu = xdxr["peigu"].astype(float)
    fenhong = xdxr["fenhong"].astype(float)
    peigujia = xdxr["peigujia"].astype(float)
    songzhuangu = xdxr["songzhuangu"].astype(float)

    for i in range(len(xdxr)):
        fh = float(fenhong.iloc[i])
        pg = float(peigu.iloc[i])
        pgj = float(peigujia.iloc[i])
        szg = float(songzhuangu.iloc[i])
        date = xdxr.index[i]
        denom = 10.0 + pg + szg
        if denom <= 0:
            continue
        mask = out.index < date
        for col in ("open", "high", "low", "close"):
            if col in out.columns:
                out.loc[mask, col] = (
                    out.loc[mask, col].astype(float) * 10.0 - fh + pg * pgj
                ) / denom
    return out


def apply_qfq_to_ohlc(raw_bars: pd.DataFrame, factor: pd.Series) -> pd.DataFrame:
    """用因子序列缩放 OHLC；volume 保持不变。"""
    if raw_bars is None or raw_bars.empty:
        return raw_bars
    out = raw_bars.copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.set_index("date")
    out = out.sort_index()
    f = factor.reindex(out.index).fillna(1.0).astype(float)
    for col in ("open", "high", "low", "close"):
        if col in out.columns:
            out[col] = out[col].astype(float) * f
    if "amount" in out.columns:
        out["amount"] = out["amount"].astype(float) * f
    out = out.reset_index()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out
