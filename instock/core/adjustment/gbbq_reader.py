# -*- coding: utf-8 -*-
"""读取通达信 T0002/hq_cache/gbbq（依赖 pytdx.GbbqReader）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from instock.core.data.profile import tdx_dir

GBBQ_CANDIDATES = (
    "T0002/hq_cache/gbbq",
    "T0002/hq_cache/gbbq.dat",
    "hq_cache/gbbq",
    "T0002/gbbq",
)


def _hq_cache_dir(root: Path) -> Path:
    return root / "T0002" / "hq_cache"


def list_hq_cache_names(tdx_root: Optional[str] = None, *, limit: int = 40) -> List[str]:
    """列出 hq_cache 下文件名（诊断用）。"""
    root = Path(tdx_root or tdx_dir() or "")
    cache = _hq_cache_dir(root)
    if not cache.is_dir():
        return []
    names = sorted(p.name for p in cache.iterdir() if p.is_file())
    return names[:limit]


def find_gbbq_path(tdx_root: Optional[str] = None) -> Optional[Path]:
    root = Path(tdx_root or tdx_dir() or "")
    if not root.is_dir():
        return None
    for rel in GBBQ_CANDIDATES:
        p = root / rel
        if p.is_file():
            return p
    cache = _hq_cache_dir(root)
    if cache.is_dir():
        for name in ("gbbq", "gbbq.dat"):
            p = cache / name
            if p.is_file():
                return p
        # 部分版本无扩展名、大小写不同
        for p in cache.iterdir():
            if p.is_file() and p.name.lower() in ("gbbq", "gbbq.dat"):
                return p
        # 浅层递归 T0002（个别安装路径不同）
        t2 = root / "T0002"
        if t2.is_dir():
            for p in t2.rglob("gbbq"):
                if p.is_file() and p.stat().st_size > 1024:
                    return p
            for p in t2.rglob("gbbq.dat"):
                if p.is_file() and p.stat().st_size > 1024:
                    return p
    return None


def diagnose_gbbq(tdx_root: Optional[str] = None) -> Tuple[Optional[Path], str]:
    """
    返回 (path, message)。无 gbbq 时 message 含 hq_cache 摘要，便于对照资源管理器。
    """
    root = Path(tdx_root or tdx_dir() or "")
    p = find_gbbq_path(tdx_root)
    if p:
        return p, f"OK: {p} ({p.stat().st_size} bytes)"
    cache = _hq_cache_dir(root)
    if not root.is_dir():
        return None, f"INSTOCK_TDX_DIR 不存在: {root}"
    if not cache.is_dir():
        return (
            None,
            f"无目录 {cache}（日常同步只拷了 vipdoc，需同步 T0002/hq_cache 或整目录）",
        )
    names = list_hq_cache_names(tdx_root, limit=30)
    has_map = any(n.lower() == "gbbq.map" for n in names)
    hint = "请在 Windows 通达信保持联网运行，待生成 gbbq 后再同步（菜单：系统→专业下载→沪深京日线/品种，或盘后数据下载）。"
    if has_map and not any(n.lower() in ("gbbq", "gbbq.dat") for n in names):
        hint = "已有 gbbq.map 但无 gbbq 主文件，请在通达信内执行「下载沪深京品种/权息」或完整盘后下载后重启通达信。"
    sample = ", ".join(names[:12]) + ("…" if len(names) > 12 else "")
    return None, f"hq_cache 中未找到 gbbq；当前文件示例: {sample or '(空)'}。{hint}"


def parse_gbbq_datetime(series: pd.Series) -> pd.Series:
    """
    通达信 gbbq 的 datetime 列为 YYYYMMDD 整数（如 19900301），
    不可用 pd.to_datetime(int) 直接解析（会变成 1970 纳秒偏移）。
    """
    raw = series.astype(str).str.replace(r"\D", "", regex=True)
    raw = raw.where(raw.str.len() >= 8, other=pd.NA)
    return pd.to_datetime(raw, format="%Y%m%d", errors="coerce").dt.normalize()


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
        _, msg = diagnose_gbbq(tdx_root)
        raise FileNotFoundError(msg)
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
        out["ex_date"] = parse_gbbq_datetime(out["datetime"])
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
