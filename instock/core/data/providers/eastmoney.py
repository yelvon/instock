# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime
from typing import Optional

import instock.core.crawling.stock_hist_em as she
import instock.core.tablestructure as tbs
import instock.core.stockfetch as stf
from instock.core.data.provider import FetchResult
from instock.core.data.providers._base import BaseProvider


class Provider(BaseProvider):
    provider_id = "eastmoney"

    def capabilities(self) -> set:
        return {"daily_spot_snapshot", "daily_bar"}

    def healthcheck(self) -> bool:
        try:
            import instock.core.crawling.stock_hist_em as she

            return True
        except Exception:
            return False

    def fetch_spot(self, trade_date: datetime.date, **kwargs) -> FetchResult:
        try:
            data = she.stock_zh_a_spot_em()
        except Exception as e:
            return FetchResult(
                ok=False,
                provider_id=self.provider_id,
                trade_date=trade_date,
                error=str(e),
            )
        if data is None or data.empty:
            return FetchResult(
                ok=False,
                provider_id=self.provider_id,
                trade_date=trade_date,
                error="东财 spot 为空",
            )
        if trade_date is None:
            data.insert(0, "date", datetime.datetime.now().strftime("%Y-%m-%d"))
        else:
            data.insert(0, "date", trade_date.strftime("%Y-%m-%d"))
        data.columns = list(tbs.TABLE_CN_STOCK_SPOT["columns"])
        data = data.loc[data["code"].apply(stf.is_a_stock)].loc[
            data["new_price"].apply(stf.is_open)
        ]
        if data is None or data.empty:
            return FetchResult(
                ok=False,
                provider_id=self.provider_id,
                trade_date=trade_date,
                error="东财 spot 为空",
            )
        return FetchResult(
            ok=True,
            data=data,
            provider_id=self.provider_id,
            trade_date=trade_date,
            fields_provided=list(data.columns),
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
        adj = "qfq" if adjust in ("adjusted", "qfq") else ""
        try:
            if date_to:
                stock = she.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=date_from,
                    end_date=date_to,
                    adjust=adj,
                )
            else:
                stock = she.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=date_from,
                    adjust=adj,
                )
        except Exception as e:
            return FetchResult(ok=False, provider_id=self.provider_id, error=str(e))
        if stock is None or stock.empty:
            return FetchResult(ok=False, provider_id=self.provider_id, error="东财 K 线为空")
        import instock.core.tablestructure as tbs

        stock.columns = tuple(tbs.CN_STOCK_HIST_DATA["columns"])
        stock = stock.sort_index()
        if "volume" in stock.columns:
            stock["volume"] = stock["volume"].astype("float") * 100
        return FetchResult(
            ok=True,
            data=stock,
            provider_id=self.provider_id,
            metadata={"adjust": adj or "raw"},
            fields_provided=list(stock.columns),
        )
