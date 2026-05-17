# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime
from typing import Optional

import pandas as pd

from instock.core.data.provider import FetchResult


class BaseProvider:
    provider_id: str = "base"

    def capabilities(self) -> set:
        return set()

    def healthcheck(self) -> bool:
        return True

    def fetch_spot(self, trade_date: datetime.date, **kwargs) -> FetchResult:
        return FetchResult(
            ok=False,
            error="fetch_spot 未实现",
            provider_id=self.provider_id,
        )

    def fetch_bars(
        self,
        code: str,
        date_from: str,
        date_to: Optional[str] = None,
        *,
        adjust: str = "raw",
        **kwargs,
    ) -> FetchResult:
        return FetchResult(
            ok=False,
            error="fetch_bars 未实现",
            provider_id=self.provider_id,
        )

    def enrich_spot(
        self,
        df: pd.DataFrame,
        trade_date: datetime.date,
        *,
        mode: str = "valuation_only",
        **kwargs,
    ) -> FetchResult:
        return FetchResult(
            ok=False,
            error="enrich_spot 未实现",
            provider_id=self.provider_id,
            data=df,
        )
