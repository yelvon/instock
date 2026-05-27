# -*- coding: utf-8 -*-
"""读取通达信 T0002/hq_cache/gbbq（依赖 pytdx.GbbqReader）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd

from instock.core.data.profile import tdx_dir

GBBQ_CANDIDATES = (
    "T0002/hq_cache/gbbq",
    "T0002/hq_cache/gbbq.dat",
    "hq_cache/gbbq",
)


def find_gbbq_path(tdx_root: Optional[str] = None) -> Optional[Path]:
    root = Path(tdx_root or tdx_dir() or "")
    if not root.is_dir():
        return None
    for rel in GBBQ_CANDIDATES:
        p = root / rel
        if p.is_file():
            return p
    cache = root / "T0002" / "hq_cache"
    if cache.is_dir():
        for name in ("gbbq", "gbbq.dat"):
            p = cache / name
            if p.is_file():
                return p
    return None


def gbbq_factor_version(tdx_root: Optional[str] = None) -> str:
    p = find_gbbq_path(tdx_root)
    if not p:
        return ""
    st = p.stat()
    return f"mtime:{int(st.st_mtime)}:{st.st_size}"


def read_gbbq_dataframe(tdx_root: Optional[str] = None) -> pd.DataFrame:
    """返回全市场 gbbq 记录；列含 market,code,datetime,category,..."""
    path = find_gbbq_path(tdx_root)
    if not path:
        raise FileNotFoundError(
            "未找到 gbbq 文件，请同步 T0002/hq_cache/gbbq 并设置 INSTOCK_TDX_DIR"
        )
    try:
        from pytdx.reader import GbbqReader
    except ImportError as e:
        raise ImportError("解析 gbbq 需要 pytdx，请 pip install pytdx") from e

    df = GbbqReader().get_df(str(path))
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    out["code"] = out["code"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(6).str[-6:]
    if "datetime" in out.columns:
        out["ex_date"] = pd.to_datetime(out["datetime"], errors="coerce").dt.normalize()
    return out


def events_for_code(gbbq: pd.DataFrame, code: str, *, category: int = 1) -> pd.DataFrame:
    """单只股票除权事件（category=1 为 A 股除权除息）。"""
    if gbbq is None or gbbq.empty:
        return pd.DataFrame()
    c = str(code).zfill(6)[:6]
    sub = gbbq[(gbbq["code"] == c) & (gbbq["category"] == category)].copy()
    if sub.empty:
        return sub
    sub = sub.sort_values("ex_date")
    sub["fenhong"] = pd.to_numeric(
        sub.get("hongli_panqianliutong", 0), errors="coerce"
    ).fillna(0)
    sub["songzhuangu"] = pd.to_numeric(
        sub.get("songgu_qianzongguben", 0), errors="coerce"
    ).fillna(0)
    sub["peigujia"] = pd.to_numeric(
        sub.get("peigujia_qianzongguben", 0), errors="coerce"
    ).fillna(0)
    sub["peigu"] = pd.to_numeric(sub.get("peigu_houzongguben", 0), errors="coerce").fillna(0)
    return sub
