# -*- coding: utf-8 -*-
"""内置回测策略目录（集中登记 title/category/参数中文名）。"""

from __future__ import annotations

from typing import List

from instock.core.backtest.strategy_meta import ParamDef, StrategyCatalogEntry
from instock.core.backtest.strategies.buy_and_hold import BuyAndHoldStrategy
from instock.core.backtest.strategies.moving_average import MovingAverageCrossStrategy
from instock.core.backtest.strategies.technicals import (
    BollingerBreakoutStrategy,
    MacdCrossStrategy,
    RsiReversalStrategy,
)


def _technical_catalog() -> List[StrategyCatalogEntry]:
    return [
        StrategyCatalogEntry(
            strategy_id=MovingAverageCrossStrategy.strategy_id,
            strategy_cls=MovingAverageCrossStrategy,
            title="双均线交叉",
            description="快线上穿慢线买入，下穿卖出；T 日信号 T+1 开盘成交。",
            category="technical",
            tags=["均线", "趋势"],
            param_defs=[
                ParamDef("fast", "快线周期", "int", 5, min=2, max=120),
                ParamDef("slow", "慢线周期", "int", 20, min=3, max=250),
            ],
        ),
        StrategyCatalogEntry(
            strategy_id=RsiReversalStrategy.strategy_id,
            strategy_cls=RsiReversalStrategy,
            title="RSI 反转",
            description="RSI 低于超卖线买入，高于超买线卖出。",
            category="technical",
            tags=["RSI", "震荡"],
            param_defs=[
                ParamDef("period", "RSI 周期", "int", 14, min=2, max=60),
                ParamDef("oversold", "超卖阈值", "float", 30, min=5, max=50),
                ParamDef("overbought", "超买阈值", "float", 70, min=50, max=95),
            ],
        ),
        StrategyCatalogEntry(
            strategy_id=MacdCrossStrategy.strategy_id,
            strategy_cls=MacdCrossStrategy,
            title="MACD 金叉死叉",
            description="MACD 线上穿信号线买入，下穿卖出。",
            category="technical",
            tags=["MACD", "趋势"],
            param_defs=[
                ParamDef("fast", "快线 EMA", "int", 12, min=2, max=60),
                ParamDef("slow", "慢线 EMA", "int", 26, min=5, max=120),
                ParamDef("signal", "信号线", "int", 9, min=2, max=60),
            ],
        ),
        StrategyCatalogEntry(
            strategy_id=BollingerBreakoutStrategy.strategy_id,
            strategy_cls=BollingerBreakoutStrategy,
            title="布林带突破",
            description="收盘价突破上轨买入，跌破下轨卖出。",
            category="technical",
            tags=["布林带", "突破"],
            param_defs=[
                ParamDef("period", "均线周期", "int", 20, min=5, max=120),
                ParamDef("std", "标准差倍数", "float", 2.0, min=0.5, max=4.0),
            ],
        ),
    ]


def _baseline_catalog() -> List[StrategyCatalogEntry]:
    return [
        StrategyCatalogEntry(
            strategy_id=BuyAndHoldStrategy.strategy_id,
            strategy_cls=BuyAndHoldStrategy,
            title="买入持有",
            description="各标的在首个有 bar 的交易日等权买入并持有。",
            category="baseline",
            tags=["基准"],
            param_defs=[],
        ),
    ]


def _screening_catalog() -> List[StrategyCatalogEntry]:
    from instock.core.backtest.strategies.screening_bridge import ScreeningBridgeStrategy
    from instock.core.backtest.strategies.screening_factory import (
        get_screening_strategy_class,
        screening_strategy_id,
    )
    import instock.core.tablestructure as tbs

    entries: List[StrategyCatalogEntry] = [
        StrategyCatalogEntry(
            strategy_id=ScreeningBridgeStrategy.strategy_id,
            strategy_cls=ScreeningBridgeStrategy,
            title="选股桥接（通用）",
            description="指定 strategy_table，调用 check_* 选股函数，命中则次日买入。",
            category="screening",
            tags=["选股", "桥接"],
            param_defs=[
                ParamDef(
                    "strategy_table",
                    "选股表名",
                    "str",
                    "cn_stock_strategy_enter",
                    required=True,
                ),
            ],
        ),
    ]
    for item in tbs.TABLE_CN_STOCK_STRATEGIES:
        table = item["name"]
        cn = item.get("cn") or table
        sid = screening_strategy_id(table)
        cls = get_screening_strategy_class(table, cn)
        entries.append(
            StrategyCatalogEntry(
                strategy_id=sid,
                strategy_cls=cls,
                title=f"选股·{cn}",
                description=f"回测桥接日批选股逻辑（表 {table}），命中则次日买入。",
                category="screening",
                tags=["选股", cn],
                param_defs=[
                    ParamDef("strategy_table", "选股表名", "str", table, required=True),
                ],
            )
        )
    return entries


def iter_builtin_catalog() -> List[StrategyCatalogEntry]:
    out: List[StrategyCatalogEntry] = []
    out.extend(_baseline_catalog())
    out.extend(_technical_catalog())
    try:
        out.extend(_screening_catalog())
    except Exception:
        pass
    return out
