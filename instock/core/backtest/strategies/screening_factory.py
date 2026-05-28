# -*- coding: utf-8 -*-
"""为 tablestructure 选股表批量生成回测桥接策略类。"""

from __future__ import annotations

from typing import Dict, Type

from instock.core.backtest.strategies.screening_bridge import ScreeningBridgeStrategy


def screening_strategy_id(strategy_table: str) -> str:
    return f"screening_{strategy_table}"


def make_screening_strategy_class(strategy_table: str, title_cn: str) -> Type[ScreeningBridgeStrategy]:
    sid = screening_strategy_id(strategy_table)

    class _ScreeningStrategy(ScreeningBridgeStrategy):
        strategy_id = sid
        default_params = {"strategy_table": strategy_table}

    _ScreeningStrategy.__name__ = f"Screening_{strategy_table}"
    _ScreeningStrategy.__qualname__ = _ScreeningStrategy.__name__
    return _ScreeningStrategy


_CACHE: Dict[str, Type[ScreeningBridgeStrategy]] = {}


def get_screening_strategy_class(strategy_table: str, title_cn: str = "") -> Type[ScreeningBridgeStrategy]:
    if strategy_table not in _CACHE:
        _CACHE[strategy_table] = make_screening_strategy_class(strategy_table, title_cn)
    return _CACHE[strategy_table]
