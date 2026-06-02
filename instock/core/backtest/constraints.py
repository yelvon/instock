# -*- coding: utf-8 -*-
"""A 股撮合约束：停牌、涨跌停、滑点。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from instock.core.backtest.result import _f


def limit_pct(code: str, *, name: str = "") -> float:
    """涨跌停幅度（近似）。"""
    code = str(code).zfill(6)[:6]
    nm = str(name or "")
    if "ST" in nm.upper() or nm.startswith("*"):
        return 0.05
    if code.startswith(("300", "688")):
        return 0.20
    return 0.10


def _prev_close(row: Dict[str, Any], prev_row: Optional[Dict[str, Any]]) -> float:
    if prev_row is not None:
        pc = _f(prev_row.get("close"))
        if pc > 0:
            return pc
    for key in ("pre_close", "pre_close_price", "preClose"):
        pc = _f(row.get(key))
        if pc > 0:
            return pc
    return 0.0


def is_suspended(row: Dict[str, Any]) -> bool:
    vol = _f(row.get("volume"))
    if vol <= 0:
        return True
    o = _f(row.get("open"))
    h = _f(row.get("high"))
    l = _f(row.get("low"))
    c = _f(row.get("close"))
    if o > 0 and o == h == l == c and vol <= 0:
        return True
    return False


def is_limit_up(row: Dict[str, Any], prev_row: Optional[Dict[str, Any]], code: str) -> bool:
    pc = _prev_close(row, prev_row)
    if pc <= 0:
        ch = _f(row.get("p_change"), _f(row.get("quote_change"), _f(row.get("ups_downs"))))
        return ch >= limit_pct(code) * 100 - 0.01
    limit_price = round(pc * (1 + limit_pct(code)), 2)
    open_p = _f(row.get("open"), _f(row.get("close")))
    close_p = _f(row.get("close"))
    tol = max(0.01, pc * 0.001)
    return open_p >= limit_price - tol or close_p >= limit_price - tol


def is_limit_down(row: Dict[str, Any], prev_row: Optional[Dict[str, Any]], code: str) -> bool:
    pc = _prev_close(row, prev_row)
    if pc <= 0:
        ch = _f(row.get("p_change"), _f(row.get("quote_change"), _f(row.get("ups_downs"))))
        return ch <= -limit_pct(code) * 100 + 0.01
    limit_price = round(pc * (1 - limit_pct(code)), 2)
    open_p = _f(row.get("open"), _f(row.get("close")))
    close_p = _f(row.get("close"))
    tol = max(0.01, pc * 0.001)
    return open_p <= limit_price + tol or close_p <= limit_price + tol


def apply_slippage(base_price: float, side: str, slippage_bps: float) -> Tuple[float, float]:
    """返回 (成交价, 滑点成本每股)。"""
    bps = max(0.0, float(slippage_bps or 0))
    if bps <= 0 or base_price <= 0:
        return base_price, 0.0
    factor = bps / 10000.0
    if side == "buy":
        fill = base_price * (1 + factor)
    else:
        fill = base_price * (1 - factor)
    slip = abs(fill - base_price)
    return fill, slip


def check_order_fill(
    *,
    code: str,
    side: str,
    row: Dict[str, Any],
    prev_row: Optional[Dict[str, Any]],
    slippage_bps: float = 0.0,
) -> Tuple[Optional[str], float, float]:
    """
    检查订单是否可成交。
    返回 (reject_reason, fill_price, slippage_per_share)。
    reject_reason 非空表示拒单。
    """
    if is_suspended(row):
        return "suspended", 0.0, 0.0
    if side == "buy" and is_limit_up(row, prev_row, code):
        return "limit_up", 0.0, 0.0
    if side == "sell" and is_limit_down(row, prev_row, code):
        return "limit_down", 0.0, 0.0
    base_open = _f(row.get("open"), _f(row.get("close")))
    if base_open <= 0:
        return "missing_bar", 0.0, 0.0
    fill_price, slip = apply_slippage(base_open, side, slippage_bps)
    return None, fill_price, slip
