# -*- coding: utf-8 -*-
"""模拟经纪商：T+1、费用、次日开盘价撮合。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from instock.core.backtest.constraints import check_order_fill
from instock.core.backtest.result import _f


class SimBroker:
    def __init__(
        self,
        *,
        initial_cash: float,
        commission_rate: float = 0.0003,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 0.001,
        transfer_fee_rate: float = 0.00002,
        slippage_bps: float = 0.0,
    ) -> None:
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate
        self.transfer_fee_rate = transfer_fee_rate
        self.slippage_bps = float(slippage_bps or 0)
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []
        self.pending_orders: List[Dict[str, Any]] = []
        self._order_seq = 0

    def get_position_qty(self, code: str) -> int:
        return int(self.positions.get(code, {}).get("qty", 0))

    def get_position(self, code: str) -> Dict[str, Any]:
        return self.positions.get(code, {"qty": 0.0, "cost": 0.0, "buy_date": ""})

    def submit_order(
        self,
        *,
        created_date: str,
        target_date: str,
        code: str,
        side: str,
        requested_qty: int,
        target_weight: float = 0.0,
        reason: str,
    ) -> None:
        if requested_qty <= 0 or side not in ("buy", "sell"):
            return
        self._order_seq += 1
        order = {
            "orderId": f"order-{self._order_seq:04d}",
            "createdDate": created_date,
            "targetDate": target_date,
            "code": code,
            "name": code,
            "side": side,
            "orderType": "market",
            "requestedQty": int(requested_qty),
            "targetWeight": target_weight,
            "status": "pending",
            "rejectReason": None,
            "reason": reason,
        }
        self.orders.append(order)
        self.pending_orders.append(order)

    def _prev_row(
        self, code: str, date: str, dates: List[str], by_code_date: Dict[str, Dict[str, dict]]
    ) -> Optional[dict]:
        try:
            idx = dates.index(date)
        except ValueError:
            return None
        if idx <= 0:
            return None
        prev_date = dates[idx - 1]
        return by_code_date.get(code, {}).get(prev_date)

    def process_due_orders(
        self,
        date: str,
        by_code_date: Dict[str, Dict[str, dict]],
        dates: Optional[List[str]] = None,
    ) -> tuple[int, float]:
        day_trade_count = 0
        day_turnover = 0.0
        date_list = dates or []
        due = [o for o in self.pending_orders if o["targetDate"] == date]
        self.pending_orders = [o for o in self.pending_orders if o["targetDate"] != date]
        for order in due:
            code = str(order["code"])
            side = str(order["side"])
            target_qty = int(order["requestedQty"])
            row = by_code_date.get(code, {}).get(date)
            if row is None:
                order["status"] = "rejected"
                order["rejectReason"] = "missing_bar"
                continue
            prev_row = self._prev_row(code, date, date_list, by_code_date) if date_list else None
            reject, fill_price, slip_per_share = check_order_fill(
                code=code,
                side=side,
                row=row,
                prev_row=prev_row,
                slippage_bps=self.slippage_bps,
            )
            if reject:
                order["status"] = "rejected"
                order["rejectReason"] = reject
                continue
            open_price = fill_price
            slippage_cost = round(slip_per_share * target_qty, 2)
            amount = target_qty * open_price
            commission = max(self.min_commission, amount * self.commission_rate)
            stamp_tax = amount * self.stamp_tax_rate if side == "sell" else 0.0
            transfer_fee = amount * self.transfer_fee_rate
            total_cost = commission + stamp_tax + transfer_fee
            if side == "buy" and amount + total_cost + slippage_cost > self.cash:
                order["status"] = "rejected"
                order["rejectReason"] = "cash_not_enough"
                continue
            if side == "buy":
                self.cash -= amount + total_cost + slippage_cost
                self.positions[code] = {
                    "qty": float(target_qty),
                    "cost": open_price,
                    "buy_date": date,
                }
                position_after = target_qty
            else:
                self.cash += amount - total_cost - slippage_cost
                self.positions.pop(code, None)
                position_after = 0
            order["status"] = "filled"
            day_trade_count += 1
            day_turnover += amount
            self.trades.append(
                {
                    "tradeId": f"trade-{len(self.trades) + 1:04d}",
                    "orderId": order["orderId"],
                    "date": date,
                    "code": code,
                    "name": code,
                    "side": side,
                    "qty": target_qty,
                    "price": round(open_price, 4),
                    "amount": round(amount, 2),
                    "commission": round(commission, 2),
                    "stampTax": round(stamp_tax, 2),
                    "transferFee": round(transfer_fee, 2),
                    "slippageCost": slippage_cost,
                    "totalCost": round(total_cost + slippage_cost, 2),
                    "cashAfter": round(self.cash, 2),
                    "positionAfter": position_after,
                    "reason": order.get("reason"),
                }
            )
        return day_trade_count, day_turnover

    def snapshot_positions(
        self, date: str, dates: List[str], by_code_date: Dict[str, Dict[str, dict]]
    ) -> tuple[float, List[Dict[str, Any]]]:
        market_value = 0.0
        rows: List[Dict[str, Any]] = []
        for code, pos in list(self.positions.items()):
            row = by_code_date.get(code, {}).get(date)
            if row is None:
                continue
            close = _f(row.get("close"))
            qty = int(pos.get("qty", 0))
            mv = qty * close
            market_value += mv
            buy_date = str(pos.get("buy_date", ""))
            rows.append(
                {
                    "date": date,
                    "code": code,
                    "name": code,
                    "qty": qty,
                    "sellableQty": 0 if buy_date == date else qty,
                    "costPrice": round(_f(pos.get("cost")), 4),
                    "closePrice": round(close, 4),
                    "marketValue": round(mv, 2),
                    "unrealizedPnl": round((close - _f(pos.get("cost"), close)) * qty, 2),
                    "weight": 0.0,
                    "holdingDays": max(1, dates.index(date) - dates.index(buy_date) + 1)
                    if buy_date in dates
                    else 1,
                }
            )
        return market_value, rows
