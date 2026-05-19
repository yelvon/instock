# -*- coding: utf-8 -*-
"""INSTOCK_DATA_PROFILE / BAR_MODE 等环境解析。"""

from __future__ import annotations

import os
from typing import Optional

PROFILE_LIVE = "live"
PROFILE_BACKTEST = "backtest"
BAR_MODE_RAW = "raw"
BAR_MODE_ADJUSTED = "adjusted"
BAR_SOURCE_AUTO = "auto"
BAR_SOURCE_MOOTDX = "mootdx"
BAR_SOURCE_TUSHARE = "tushare"
BAR_SOURCE_EASTMONEY = "eastmoney"


def effective_data_profile(override: Optional[str] = None) -> str:
    raw = override if override is not None and str(override).strip() else os.environ.get(
        "INSTOCK_DATA_PROFILE", PROFILE_LIVE
    )
    s = str(raw).strip().lower()
    if s in (PROFILE_BACKTEST, "bt", "strict"):
        return PROFILE_BACKTEST
    return PROFILE_LIVE


def effective_bar_mode(override: Optional[str] = None) -> str:
    raw = override if override is not None and str(override).strip() else os.environ.get(
        "INSTOCK_BAR_MODE", BAR_MODE_RAW
    )
    s = str(raw).strip().lower()
    if s in (BAR_MODE_ADJUSTED, "qfq", "hfq", "adjusted"):
        return BAR_MODE_ADJUSTED
    return BAR_MODE_RAW


def tencent_enrich_enabled(profile: Optional[str] = None) -> bool:
    p = effective_data_profile(profile)
    env = os.environ.get("INSTOCK_TENCENT_ENRICH", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if env in ("0", "false", "no", "off"):
        return False
    return p == PROFILE_LIVE


def tdx_dir() -> Optional[str]:
    p = os.environ.get("INSTOCK_TDX_DIR", "").strip()
    return p or None


def bars_mootdx_only() -> bool:
    """为 true 时 K 线只走 mootdx，不回退东财（避免 push2 82 阻塞遍历作业）。"""
    return os.environ.get("INSTOCK_BARS_MOOTDX_ONLY", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def normalize_bar_data_source(raw: Optional[str]) -> str:
    s = str(raw or "").strip().lower()
    if not s or s in ("auto", "registry", "chain", "default"):
        return BAR_SOURCE_AUTO
    if s in ("mootdx", "tdx", "通达信"):
        return BAR_SOURCE_MOOTDX
    if s in ("tushare", "ts"):
        return BAR_SOURCE_TUSHARE
    if s in ("eastmoney", "em", "东财"):
        return BAR_SOURCE_EASTMONEY
    return BAR_SOURCE_AUTO


def effective_bar_data_source(override: Optional[str] = None) -> str:
    raw = override if override is not None and str(override).strip() else os.environ.get(
        "INSTOCK_BAR_DATA_SOURCE", BAR_SOURCE_AUTO
    )
    return normalize_bar_data_source(raw)
