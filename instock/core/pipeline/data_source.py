# -*- coding: utf-8 -*-
"""市场数据采集抽象：默认实现委托 stockfetch，便于测试替换为 Mock。"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Optional, Protocol, Set, runtime_checkable

import pandas as pd

if TYPE_CHECKING:
    pass


@runtime_checkable
class MarketDataSource(Protocol):
    """采集层接口：job 与管线脚本应通过此协议访问行情与日历（渐进迁移）。"""

    def fetch_trade_dates(self) -> Optional[Set[datetime.date]]:
        """返回历史交易日集合；失败返回 None。"""

    def fetch_daily_stocks(self, trade_date: datetime.date) -> Optional[pd.DataFrame]:
        """日线全市场股票快照（列与 cn_stock_spot 一致）。"""

    def fetch_daily_etfs(self, trade_date: datetime.date) -> Optional[pd.DataFrame]:
        """日线 ETF 快照（列与 cn_etf_spot 一致）。"""


class StockfetchMarketDataSource:
    """委托 instock.core.stockfetch 的默认实现。"""

    def fetch_trade_dates(self) -> Optional[Set[datetime.date]]:
        import instock.core.stockfetch as stf

        return stf.fetch_stocks_trade_date()

    def fetch_daily_stocks(self, trade_date: datetime.date) -> Optional[pd.DataFrame]:
        import instock.core.stockfetch as stf

        return stf.fetch_stocks(trade_date)

    def fetch_daily_etfs(self, trade_date: datetime.date) -> Optional[pd.DataFrame]:
        import instock.core.stockfetch as stf

        return stf.fetch_etfs(trade_date)


_default_source: Optional[StockfetchMarketDataSource] = None


def get_default_market_data_source() -> MarketDataSource:
    global _default_source
    if _default_source is None:
        _default_source = StockfetchMarketDataSource()
    return _default_source


def set_default_market_data_source(src: Optional[MarketDataSource]) -> None:
    """单测注入 Mock 时调用。"""
    global _default_source
    _default_source = src  # type: ignore[assignment]
