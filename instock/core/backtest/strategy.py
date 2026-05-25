# -*- coding: utf-8 -*-
"""策略基类（Backtrader 式生命周期）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from instock.core.backtest.cerebro import Cerebro


class Strategy:
    """子类实现 start / next / stop；通过 self.cerebro 下单。"""

    strategy_id: str = "base"
    default_params: Dict[str, Any] = {}

    def __init__(self, cerebro: "Cerebro", params: Dict[str, Any] | None = None) -> None:
        self.cerebro = cerebro
        merged = dict(self.default_params)
        if params:
            merged.update(params)
        self.params = merged

    def start(self) -> None:
        pass

    def next(self, date: str) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        pass
