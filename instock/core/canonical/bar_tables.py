# -*- coding: utf-8 -*-
"""标准日线物理表路由：raw 与 qfq 分表。"""

from __future__ import annotations

TABLE_BAR_RAW = "cn_stock_daily_bar"
TABLE_BAR_QFQ = "cn_stock_daily_bar_qfq"
PROVIDER_QFQ_DERIVED = "tdx_qfq_derived"


def normalize_adjust_type(adjust_type: str) -> str:
    a = (adjust_type or "raw").strip().lower()
    if a in ("qfq", "01", "forward"):
        return "qfq"
    if a in ("hfq", "02", "backward"):
        return "hfq"
    return "raw"


def resolve_bar_table(adjust_type: str) -> str:
    if normalize_adjust_type(adjust_type) == "qfq":
        return TABLE_BAR_QFQ
    return TABLE_BAR_RAW


def bar_table_has_adjust_column(adjust_type: str) -> bool:
    return resolve_bar_table(adjust_type) == TABLE_BAR_RAW
