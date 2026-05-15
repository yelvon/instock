# -*- coding: utf-8 -*-
"""股票/ETF 日线快照数据源：东财、Baostock、或东财优先自动回补（与 Web/环境变量一致）。"""

from __future__ import annotations

import os
from typing import Optional

# 与前端、子进程 INSTOCK_SPOT_DATA_SOURCE 使用同一套取值
SPOT_SOURCE_EASTMONEY = "eastmoney"
SPOT_SOURCE_BAOSTOCK = "baostock"
SPOT_SOURCE_AUTO = "auto"

_VALID = frozenset({SPOT_SOURCE_EASTMONEY, SPOT_SOURCE_BAOSTOCK, SPOT_SOURCE_AUTO})


def normalize_spot_source(raw: Optional[str]) -> str:
    """将用户输入规范为 eastmoney / baostock / auto；无法识别时默认东财。"""
    if raw is None:
        return SPOT_SOURCE_EASTMONEY
    s = str(raw).strip().lower()
    if not s:
        return SPOT_SOURCE_EASTMONEY
    if s in ("eastmoney", "em", "dfc", "东财"):
        return SPOT_SOURCE_EASTMONEY
    if s in ("baostock", "bs", "bao", "宝上"):
        return SPOT_SOURCE_BAOSTOCK
    if s in ("auto", "fallback", "both", "东财优先", "优先东财"):
        return SPOT_SOURCE_AUTO
    if s in _VALID:
        return s
    return SPOT_SOURCE_EASTMONEY


def effective_spot_source(override: Optional[str] = None) -> str:
    """
    解析最终数据源。
    ``override`` 非空时优先；否则读环境变量 ``INSTOCK_SPOT_DATA_SOURCE``（默认东财）。
    """
    if override is not None and str(override).strip():
        return normalize_spot_source(override)
    return normalize_spot_source(os.environ.get("INSTOCK_SPOT_DATA_SOURCE", ""))
