# -*- coding: utf-8 -*-
"""标准日线完整度与来源质量分。"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Set

import pandas as pd

# 核心 OHLCV 齐全视为 complete
CORE_FIELDS = ("open", "close", "high", "low", "volume")
OPTIONAL_FIELDS = ("amount", "amplitude", "quote_change", "ups_downs", "turnover")

PROVIDER_QUALITY: Dict[str, int] = {
    "mootdx_local": 100,
    "tushare": 90,
    "akshare": 85,
    "mootdx_online": 80,
    "eastmoney": 75,
    "legacy_cache": 70,
}

# 相对收盘价冲突阈值
PRICE_CONFLICT_REL = 0.015


def provider_quality(provider_id: str) -> int:
    return int(PROVIDER_QUALITY.get(provider_id, 60))


def row_hash(row: Dict[str, Any]) -> str:
    payload = {k: row.get(k) for k in sorted(CORE_FIELDS + OPTIONAL_FIELDS) if k in row}
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _is_empty(val: Any) -> bool:
    if val is None:
        return True
    try:
        return bool(pd.isna(val))
    except Exception:
        return False


def completeness_score(row: Dict[str, Any]) -> int:
    core_ok = sum(1 for f in CORE_FIELDS if not _is_empty(row.get(f)))
    opt_ok = sum(1 for f in OPTIONAL_FIELDS if not _is_empty(row.get(f)))
    return min(100, int(core_ok / len(CORE_FIELDS) * 80 + opt_ok / len(OPTIONAL_FIELDS) * 20))


def quality_status_from_score(score: int, is_conflict: bool = False) -> str:
    if is_conflict:
        return "suspect"
    if score >= 80:
        return "complete"
    return "partial"


def fields_present(row: Dict[str, Any]) -> List[str]:
    return [f for f in CORE_FIELDS + OPTIONAL_FIELDS if not _is_empty(row.get(f))]


def fields_missing(row: Dict[str, Any]) -> List[str]:
    return [f for f in CORE_FIELDS + OPTIONAL_FIELDS if _is_empty(row.get(f))]


def price_conflict(existing: Dict[str, Any], incoming: Dict[str, Any]) -> bool:
    ec = existing.get("close")
    ic = incoming.get("close")
    if _is_empty(ec) or _is_empty(ic):
        return False
    try:
        ec_f, ic_f = float(ec), float(ic)
        if ec_f <= 0:
            return False
        return abs(ec_f - ic_f) / ec_f > PRICE_CONFLICT_REL
    except (TypeError, ValueError):
        return False


def merge_masks(existing_mask: Optional[Any], provider_id: str) -> List[str]:
    if existing_mask is None:
        out: Set[str] = set()
    elif isinstance(existing_mask, str):
        try:
            out = set(json.loads(existing_mask))
        except Exception:
            out = set()
    elif isinstance(existing_mask, (list, tuple)):
        out = set(str(x) for x in existing_mask)
    else:
        out = set()
    out.add(provider_id)
    return sorted(out)
