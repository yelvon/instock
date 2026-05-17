# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime

import instock.core.crawling.baostock_spot as bssp
from instock.core.data.provider import FetchResult
from instock.core.data.providers._base import BaseProvider


class Provider(BaseProvider):
    provider_id = "baostock"

    def capabilities(self) -> set:
        return {"daily_spot_snapshot"}

    def healthcheck(self) -> bool:
        return bssp._baostock_allowed()

    def fetch_spot(self, trade_date: datetime.date, **kwargs) -> FetchResult:
        fill_mode = kwargs.get("fill_mode")
        data = bssp.stock_zh_a_spot_baostock(trade_date)
        if data is None or data.empty:
            return FetchResult(
                ok=False,
                provider_id=self.provider_id,
                trade_date=trade_date,
                error="Baostock spot 为空",
            )
        if fill_mode == "price_volume_only":
            data = data.copy()
            for c in list(data.columns):
                if c not in (
                    "code",
                    "name",
                    "new_price",
                    "change_rate",
                    "volume",
                    "deal_amount",
                    "open_price",
                    "high_price",
                    "low_price",
                    "pre_close_price",
                    "turnoverrate",
                ):
                    if c in data.columns:
                        data[c] = None
        return FetchResult(
            ok=True,
            data=data,
            is_partial=fill_mode == "price_volume_only",
            provider_id=self.provider_id,
            trade_date=trade_date,
        )
