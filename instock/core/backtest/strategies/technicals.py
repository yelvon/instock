# -*- coding: utf-8 -*-
"""技术指标类回测策略（轻量 pandas 实现，不访问 DB/Web）。"""

from __future__ import annotations

import pandas as pd

from instock.core.backtest.strategy import Strategy


def _rsi_series(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    return 100 - (100 / (1 + rs))


class RsiReversalStrategy(Strategy):
    strategy_id = "rsi_reversal"
    default_params = {"period": 14, "oversold": 30, "overbought": 70}

    def next(self, date: str) -> None:
        period = int(self.params.get("period", 14))
        oversold = float(self.params.get("oversold", 30))
        overbought = float(self.params.get("overbought", 70))
        max_w = self.cerebro.max_weight_per_symbol
        for code, df in self.cerebro.prepared.items():
            hist = df[df["date"] <= date]
            if len(hist) < period + 2:
                continue
            next_date = self.cerebro.next_trading_date(date)
            if not next_date or self.cerebro.by_code_date.get(code, {}).get(next_date) is None:
                continue
            rsi = float(_rsi_series(hist["close"], period).iloc[-1])
            qty = self.cerebro.broker.get_position_qty(code)
            pos = self.cerebro.broker.get_position(code)
            if rsi < oversold and qty <= 0:
                self.cerebro.buy_target_weight(
                    date=date, code=code, target_weight=max_w, reason=self.strategy_id
                )
            elif rsi > overbought and qty > 0 and pos.get("buy_date") != next_date:
                self.cerebro.sell_all(date=date, code=code, reason=self.strategy_id)


class MacdCrossStrategy(Strategy):
    strategy_id = "macd_cross"
    default_params = {"fast": 12, "slow": 26, "signal": 9}

    def next(self, date: str) -> None:
        fast = int(self.params.get("fast", 12))
        slow = int(self.params.get("slow", 26))
        signal = int(self.params.get("signal", 9))
        max_w = self.cerebro.max_weight_per_symbol
        need = slow + signal + 2
        for code, df in self.cerebro.prepared.items():
            hist = df[df["date"] <= date]
            if len(hist) < need:
                continue
            next_date = self.cerebro.next_trading_date(date)
            if not next_date or self.cerebro.by_code_date.get(code, {}).get(next_date) is None:
                continue
            close = hist["close"]
            ema_fast = close.ewm(span=fast, adjust=False).mean()
            ema_slow = close.ewm(span=slow, adjust=False).mean()
            macd = ema_fast - ema_slow
            sig = macd.ewm(span=signal, adjust=False).mean()
            if len(macd) < 2:
                continue
            prev_diff = float(macd.iloc[-2] - sig.iloc[-2])
            curr_diff = float(macd.iloc[-1] - sig.iloc[-1])
            qty = self.cerebro.broker.get_position_qty(code)
            pos = self.cerebro.broker.get_position(code)
            if prev_diff <= 0 < curr_diff and qty <= 0:
                self.cerebro.buy_target_weight(
                    date=date, code=code, target_weight=max_w, reason=self.strategy_id
                )
            elif prev_diff >= 0 > curr_diff and qty > 0 and pos.get("buy_date") != next_date:
                self.cerebro.sell_all(date=date, code=code, reason=self.strategy_id)


class BollingerBreakoutStrategy(Strategy):
    strategy_id = "bollinger_breakout"
    default_params = {"period": 20, "std": 2.0}

    def next(self, date: str) -> None:
        period = int(self.params.get("period", 20))
        mult = float(self.params.get("std", 2.0))
        max_w = self.cerebro.max_weight_per_symbol
        for code, df in self.cerebro.prepared.items():
            hist = df[df["date"] <= date]
            if len(hist) < period + 1:
                continue
            next_date = self.cerebro.next_trading_date(date)
            if not next_date or self.cerebro.by_code_date.get(code, {}).get(next_date) is None:
                continue
            close = hist["close"]
            ma = close.rolling(period).mean()
            std = close.rolling(period).std()
            upper = ma + mult * std
            lower = ma - mult * std
            c = float(close.iloc[-1])
            u = float(upper.iloc[-1])
            l = float(lower.iloc[-1])
            qty = self.cerebro.broker.get_position_qty(code)
            pos = self.cerebro.broker.get_position(code)
            if c > u and qty <= 0:
                self.cerebro.buy_target_weight(
                    date=date, code=code, target_weight=max_w, reason=self.strategy_id
                )
            elif c < l and qty > 0 and pos.get("buy_date") != next_date:
                self.cerebro.sell_all(date=date, code=code, reason=self.strategy_id)
