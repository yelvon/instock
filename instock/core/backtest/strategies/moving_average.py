# -*- coding: utf-8 -*-
"""双均线金叉死叉策略。"""

from __future__ import annotations

from instock.core.backtest.strategy import Strategy


class MovingAverageCrossStrategy(Strategy):
    strategy_id = "moving_average_cross"
    default_params = {"fast": 5, "slow": 20}

    def next(self, date: str) -> None:
        fast = int(self.params.get("fast", 5))
        slow = int(self.params.get("slow", 20))
        max_w = self.cerebro.max_weight_per_symbol
        for code, df in self.cerebro.prepared.items():
            hist = df[df["date"] <= date]
            if len(hist.index) < slow:
                continue
            next_date = self.cerebro.next_trading_date(date)
            if not next_date:
                continue
            if self.cerebro.by_code_date.get(code, {}).get(next_date) is None:
                continue
            fast_ma = float(hist["close"].tail(fast).mean())
            slow_ma = float(hist["close"].tail(slow).mean())
            qty = self.cerebro.broker.get_position_qty(code)
            pos = self.cerebro.broker.get_position(code)
            if fast_ma > slow_ma and qty <= 0:
                self.cerebro.buy_target_weight(
                    date=date,
                    code=code,
                    target_weight=max_w,
                    reason=self.strategy_id,
                )
            elif fast_ma < slow_ma and qty > 0 and pos.get("buy_date") != next_date:
                self.cerebro.sell_all(date=date, code=code, reason=self.strategy_id)
