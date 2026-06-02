# -*- coding: utf-8 -*-
"""策略注册表。"""

from __future__ import annotations

import importlib
import logging
import os
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from instock.core.backtest.strategy import Strategy
from instock.core.backtest.strategy_meta import (
    ParamDef,
    normalize_param_schema,
    param_defaults_dict,
    validate_strategy_params,
)
from instock.core.backtest.strategies.builtins_catalog import iter_builtin_catalog

logger = logging.getLogger(__name__)


@dataclass
class StrategyMeta:
    id: str
    title: str
    description: str
    strategy_cls: Type[Strategy]
    category: str = "technical"
    tags: List[str] = field(default_factory=list)
    params: List[ParamDef] = field(default_factory=list)
    param_schema: Dict[str, Any] = field(default_factory=dict)
    deprecated: bool = False
    source: str = "builtin"


_REGISTRY: Dict[str, StrategyMeta] = {}
_INITIALIZED = False


def register(
    strategy_id: str,
    strategy_cls: Type[Strategy],
    *,
    title: str = "",
    description: str = "",
    param_schema: Optional[Any] = None,
    category: str = "plugin",
    tags: Optional[List[str]] = None,
    deprecated: bool = False,
    source: str = "plugin",
    param_defs: Optional[List[ParamDef]] = None,
) -> None:
    params = param_defs if param_defs is not None else normalize_param_schema(
        param_schema, strategy_cls=strategy_cls
    )
    _REGISTRY[strategy_id] = StrategyMeta(
        id=strategy_id,
        title=title or strategy_id,
        description=description,
        strategy_cls=strategy_cls,
        category=category,
        tags=list(tags or []),
        params=params,
        param_schema=param_defaults_dict(params),
        deprecated=deprecated,
        source=source,
    )


def register_catalog_entry(entry: Any) -> None:
    register(
        entry.strategy_id,
        entry.strategy_cls,
        title=entry.title,
        description=entry.description,
        category=entry.category,
        tags=entry.tags,
        param_defs=entry.param_defs,
        source="builtin",
    )


def get_meta(strategy_id: str) -> StrategyMeta:
    meta = _REGISTRY.get(strategy_id)
    if meta is None:
        raise ValueError(f"未知策略: {strategy_id}")
    return meta


def get(strategy_id: str) -> Type[Strategy]:
    return get_meta(strategy_id).strategy_cls


def list_strategies() -> List[Dict[str, Any]]:
    items = []
    for m in _REGISTRY.values():
        items.append(
            {
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "category": m.category,
                "tags": m.tags,
                "deprecated": m.deprecated,
                "source": m.source,
                "paramSchema": dict(m.param_schema),
                "params": [p.to_dict() for p in m.params],
            }
        )
    items.sort(key=lambda x: (x.get("category") or "", x.get("title") or ""))
    return items


def validate_params(strategy_id: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    ensure_registry()
    meta = get_meta(strategy_id)
    if meta.deprecated:
        raise ValueError(f"策略已下线: {strategy_id}")
    return validate_strategy_params(strategy_id, params, meta)


def _register_from_catalog() -> None:
    for entry in iter_builtin_catalog():
        register_catalog_entry(entry)


def _load_plugins() -> None:
    strict = os.environ.get("INSTOCK_STRATEGY_PLUGINS_STRICT", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
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
        except Exception as e:
            msg = f"回测策略插件加载失败: {mod.name}: {e}"
            if strict:
                raise RuntimeError(msg) from e
            logger.warning(msg)
    extra = os.environ.get("INSTOCK_STRATEGY_PLUGINS", "").strip()
    if extra:
        for mod_path in extra.split(","):
            mod_path = mod_path.strip()
            if not mod_path:
                continue
            try:
                importlib.import_module(mod_path)
            except Exception as e:
                msg = f"回测策略插件加载失败: {mod_path}: {e}"
                if strict:
                    raise RuntimeError(msg) from e
                logger.warning(msg)


def ensure_registry() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    _register_from_catalog()
    _load_plugins()
    _INITIALIZED = True


def reset_registry_for_tests() -> None:
    global _INITIALIZED
    _REGISTRY.clear()
    _INITIALIZED = False


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
    slippage_bps: float = 0.0,
    match_price: str = "next_open",
) -> Dict[str, Any]:
    ensure_registry()
    merged_params = validate_params(strategy_id, strategy_params)
    from instock.core.backtest.cerebro import Cerebro

    cls = get(strategy_id)
    meta = get_meta(strategy_id)
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
            slippage_bps=slippage_bps,
            match_price=match_price,
        )
        .add_strategy(cls, merged_params)
        .set_bars(bars_by_code)
    )
    result = cerebro.run()
    if isinstance(result.get("params"), dict):
        result["params"]["strategy"] = strategy_id
        result["params"]["strategyTitle"] = meta.title
        result["params"]["strategyParams"] = merged_params
    return result
