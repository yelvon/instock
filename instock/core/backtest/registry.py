# -*- coding: utf-8 -*-
"""策略注册表。"""

from __future__ import annotations

import importlib
import os
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from instock.core.backtest.strategy import Strategy
from instock.core.backtest.strategies.buy_and_hold import BuyAndHoldStrategy
from instock.core.backtest.strategies.moving_average import MovingAverageCrossStrategy


@dataclass
class StrategyMeta:
    id: str
    title: str
    description: str
    strategy_cls: Type[Strategy]
    param_schema: Dict[str, Any] = field(default_factory=dict)


_REGISTRY: Dict[str, StrategyMeta] = {}
_INITIALIZED = False


def register(
    strategy_id: str,
    strategy_cls: Type[Strategy],
    *,
    title: str = "",
    description: str = "",
    param_schema: Optional[Dict[str, Any]] = None,
) -> None:
    _REGISTRY[strategy_id] = StrategyMeta(
        id=strategy_id,
        title=title or strategy_id,
        description=description,
        strategy_cls=strategy_cls,
        param_schema=param_schema or dict(getattr(strategy_cls, "default_params", {})),
    )


def get(strategy_id: str) -> Type[Strategy]:
    meta = _REGISTRY.get(strategy_id)
    if meta is None:
        raise ValueError(f"未知策略: {strategy_id}")
    return meta.strategy_cls


def list_strategies() -> List[Dict[str, Any]]:
    return [
        {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "paramSchema": m.param_schema,
        }
        for m in _REGISTRY.values()
    ]


def _register_builtins() -> None:
    register(
        MovingAverageCrossStrategy.strategy_id,
        MovingAverageCrossStrategy,
        title="双均线交叉",
        description="快线上穿慢线买入，下穿卖出；T 日信号 T+1 开盘成交。",
        param_schema={"fast": 5, "slow": 20},
    )
    register(
        BuyAndHoldStrategy.strategy_id,
        BuyAndHoldStrategy,
        title="买入持有",
        description="各标的在首个有 bar 的交易日等权买入并持有。",
        param_schema={},
    )
    try:
        from instock.core.backtest.strategies.screening_bridge import ScreeningBridgeStrategy

        register(
            ScreeningBridgeStrategy.strategy_id,
            ScreeningBridgeStrategy,
            title="选股桥接",
            description="调用 tablestructure 内置 check_* 选股函数，命中则次日买入。",
            param_schema={"strategy_table": "cn_stock_strategy_enter"},
        )
    except ImportError:
        pass


def _load_plugins() -> None:
    plugins_pkg = "instock.core.backtest.strategies.plugins"
    try:
        pkg = importlib.import_module(plugins_pkg)
    except ImportError:
        return
    path = getattr(pkg, "__path__", None)
    if not path:
        return
    for mod in pkgutil.iter_modules(path, prefix=plugins_pkg + "."):
        if mod.name.endswith(".example_hold"):
            continue
        try:
            importlib.import_module(mod.name)
        except Exception:
            continue
    extra = os.environ.get("INSTOCK_STRATEGY_PLUGINS", "").strip()
    if extra:
        for mod_path in extra.split(","):
            mod_path = mod_path.strip()
            if not mod_path:
                continue
            try:
                importlib.import_module(mod_path)
            except Exception:
                continue


def ensure_registry() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    _register_builtins()
    _load_plugins()
    _INITIALIZED = True


def run_backtest(
    *,
    run_id: str,
    title: str,
    strategy_id: str,
    strategy_params: Optional[Dict[str, Any]],
    bars_by_code: Dict[str, Any],
    initial_cash: float = 1000000.0,
    commission_rate: float = 0.0003,
    min_commission: float = 5.0,
    stamp_tax_rate: float = 0.001,
    transfer_fee_rate: float = 0.00002,
    max_weight_per_symbol: float = 0.1,
) -> Dict[str, Any]:
    ensure_registry()
    from instock.core.backtest.cerebro import Cerebro

    cls = get(strategy_id)
    cerebro = (
        Cerebro(
            run_id=run_id,
            title=title,
            initial_cash=initial_cash,
            commission_rate=commission_rate,
            min_commission=min_commission,
            stamp_tax_rate=stamp_tax_rate,
            transfer_fee_rate=transfer_fee_rate,
            max_weight_per_symbol=max_weight_per_symbol,
        )
        .add_strategy(cls, strategy_params)
        .set_bars(bars_by_code)
    )
    return cerebro.run()
