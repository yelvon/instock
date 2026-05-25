# -*- coding: utf-8 -*-
"""
示例插件策略（可选启用：取消下方注释即注册）。

复制本文件为 my_strategy.py，实现 Strategy 子类并在模块末尾 register(...)。
"""

from __future__ import annotations

# from instock.core.backtest.registry import register
# from instock.core.backtest.strategy import Strategy
#
#
# class MyHoldStrategy(Strategy):
#     strategy_id = "my_hold"
#
#     def next(self, date: str) -> None:
#         if self.cerebro.broker.get_position_qty("600000") > 0:
#             return
#         if "600000" in self.cerebro.prepared:
#             self.cerebro.buy_target_weight(
#                 date=date,
#                 code="600000",
#                 target_weight=0.1,
#                 reason=self.strategy_id,
#             )
#
#
# register(
#     MyHoldStrategy.strategy_id,
#     MyHoldStrategy,
#     title="示例持有600000",
#     description="仅演示插件注册方式",
# )
