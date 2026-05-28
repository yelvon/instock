# -*- coding: utf-8 -*-
"""回测策略元数据与参数 schema。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

ParamType = str  # int | float | str | bool


@dataclass
class ParamDef:
    key: str
    label: str
    type: ParamType = "float"
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "key": self.key,
            "label": self.label,
            "type": self.type,
            "default": self.default,
            "required": self.required,
        }
        if self.min is not None:
            out["min"] = self.min
        if self.max is not None:
            out["max"] = self.max
        return out


@dataclass
class StrategyCatalogEntry:
    strategy_id: str
    strategy_cls: type
    title: str
    description: str = ""
    category: str = "technical"
    tags: List[str] = field(default_factory=list)
    param_defs: List[ParamDef] = field(default_factory=list)
    deprecated: bool = False


def _infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def normalize_param_schema(
    param_schema: Optional[Union[Dict[str, Any], List[ParamDef]]],
    *,
    strategy_cls: Optional[type] = None,
) -> List[ParamDef]:
    if param_schema is None:
        defaults = dict(getattr(strategy_cls, "default_params", {}) or {})
        return [
            ParamDef(key=k, label=k, type=_infer_type(v), default=v)
            for k, v in defaults.items()
        ]
    if isinstance(param_schema, list):
        return list(param_schema)
    out: List[ParamDef] = []
    for key, default in param_schema.items():
        out.append(ParamDef(key=key, label=key, type=_infer_type(default), default=default))
    return out


def param_defaults_dict(params: List[ParamDef]) -> Dict[str, Any]:
    return {p.key: p.default for p in params if p.key}


def validate_strategy_params(strategy_id: str, params: Optional[Dict[str, Any]], meta: Any) -> Dict[str, Any]:
    """校验并合并默认值，非法时抛 ValueError。"""
    raw = dict(params or {})
    merged: Dict[str, Any] = {}
    param_list: List[ParamDef] = getattr(meta, "params", None) or []

    for pdef in param_list:
        val = raw.get(pdef.key, pdef.default)
        if val is None and pdef.required and pdef.default is None:
            raise ValueError(f"策略 {strategy_id} 缺少参数: {pdef.key}")
        if val is None:
            merged[pdef.key] = pdef.default
            continue
        try:
            if pdef.type == "int":
                val = int(val)
            elif pdef.type == "float":
                val = float(val)
            elif pdef.type == "bool":
                val = bool(val) if not isinstance(val, str) else val.lower() in ("1", "true", "yes")
            else:
                val = str(val)
        except (TypeError, ValueError) as e:
            raise ValueError(f"参数 {pdef.key} 类型无效") from e
        if pdef.min is not None and val < pdef.min:
            raise ValueError(f"参数 {pdef.label} 不能小于 {pdef.min}")
        if pdef.max is not None and val > pdef.max:
            raise ValueError(f"参数 {pdef.label} 不能大于 {pdef.max}")
        merged[pdef.key] = val

    for key, val in raw.items():
        if key not in merged:
            merged[key] = val

    _validate_strategy_rules(strategy_id, merged)
    return merged


def _validate_strategy_rules(strategy_id: str, params: Dict[str, Any]) -> None:
    if strategy_id == "moving_average_cross":
        fast = int(params.get("fast", 5))
        slow = int(params.get("slow", 20))
        if fast >= slow:
            raise ValueError("快线周期必须小于慢线周期")
    if strategy_id == "macd_cross":
        fast = int(params.get("fast", 12))
        slow = int(params.get("slow", 26))
        if fast >= slow:
            raise ValueError("MACD 快线周期必须小于慢线周期")
    if strategy_id == "rsi_reversal":
        oversold = float(params.get("oversold", 30))
        overbought = float(params.get("overbought", 70))
        if oversold >= overbought:
            raise ValueError("RSI 超卖阈值必须小于超买阈值")
    if strategy_id == "bollinger_breakout":
        std = float(params.get("std", 2))
        if std <= 0:
            raise ValueError("布林带标准差倍数必须为正")
