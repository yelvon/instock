# -*- coding: utf-8 -*-
"""Domain Provider 契约与统一抓取结果。"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import pandas as pd


@dataclass
class FetchResult:
    data: Optional[pd.DataFrame] = None
    provider_id: str = ""
    domain_id: str = ""
    trade_date: Optional[datetime.date] = None
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    scope_type: str = ""
    scope_key: str = ""
    fields_provided: List[str] = field(default_factory=list)
    is_partial: bool = False
    mixed_source: bool = False
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    error: Optional[str] = None

    @property
    def row_count(self) -> int:
        if self.data is None or self.data.empty:
            return 0
        return int(len(self.data))


@runtime_checkable
class DomainProvider(Protocol):
    provider_id: str

    def capabilities(self) -> set:
        ...

    def healthcheck(self) -> bool:
        ...

    def fetch_spot(self, trade_date: datetime.date, **kwargs) -> FetchResult:
        ...

    def fetch_bars(
        self,
        code: str,
        date_from: str,
        date_to: Optional[str] = None,
        *,
        adjust: str = "raw",
        **kwargs,
    ) -> FetchResult:
        ...

    def enrich_spot(
        self,
        df: pd.DataFrame,
        trade_date: datetime.date,
        *,
        mode: str = "valuation_only",
        **kwargs,
    ) -> FetchResult:
        ...
