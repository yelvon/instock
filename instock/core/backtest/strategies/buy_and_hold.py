# -*- coding: utf-8 -*-
"""买入持有：首个可交易日按权重买入，持有至结束。"""

from __future__ import annotations

from instock.core.backtest.strategy import Strategy


class BuyAndHoldStrategy(Strategy):
    strategy_id = "buy_and_hold"
    default_params = {}

    def __init__(self, cerebro, params=None):
        super().__init__(cerebro, params)
        self._bought: set[str] = set()

    def next(self, date: str) -> None:
        max_w = self.cerebro.max_weight_per_symbol
        n = max(len(self.cerebro.prepared), 1)
        weight = min(max_w, 1.0 / n)
        for code in self.cerebro.prepared:
            if code in self._bought:
                continue
            if self.cerebro.by_code_date.get(code, {}).get(date) is None:
                continue
            self.cerebro.buy_target_weight(
                date=date,
                code=code,
                target_weight=weight,
                reason=self.strategy_id,
            )
            self._bought.add(code)
