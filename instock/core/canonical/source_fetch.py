# -*- coding: utf-8 -*-
"""按单一数据源拉取日线（不走路由 chain 回退）。"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from instock.core.data.registry import get_registry

_HC_CACHE: dict[str, bool] = {}

# 作业 --source 别名 → provider_id
SOURCE_ALIASES = {
    "mootdx": ["mootdx_local", "mootdx_online"],
    "mootdx_local": ["mootdx_local"],
    "mootdx_online": ["mootdx_online"],
    "tushare": ["tushare"],
    "akshare": ["akshare"],
    "eastmoney": ["eastmoney"],
}


def resolve_provider_chain(source: str) -> list[str]:
    s = str(source or "").strip().lower()
    return SOURCE_ALIASES.get(s, [s] if s else [])


def fetch_bars_single_source(
    source: str,
    code: str,
    date_from: str,
    date_to: Optional[str] = None,
    *,
    adjust: str = "raw",
) -> tuple[Optional[pd.DataFrame], str, Optional[str]]:
    """
    返回 (dataframe, provider_id_used, error)。
    mootdx 会按 local → online 顺序尝试。
    """
    reg = get_registry()
    chain = resolve_provider_chain(source)
    if not chain:
        return None, "", f"未知数据源: {source}"
    last_err = None
    for pid in chain:
        try:
            prov = reg.get_provider(pid)
            if pid not in _HC_CACHE:
                _HC_CACHE[pid] = bool(prov.healthcheck())
            if not _HC_CACHE[pid]:
                last_err = f"{pid} healthcheck failed"
                continue
            res = prov.fetch_bars(code, date_from, date_to, adjust=adjust)
            if res.ok and res.data is not None and not res.data.empty:
                return res.data, pid, None
            last_err = res.error or f"{pid} empty"
        except Exception as e:
            last_err = str(e)[:200]
    return None, chain[-1] if chain else "", last_err
