# -*- coding: utf-8 -*-

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import pandas as pd


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _pct(v: float) -> float:
    return round(float(v), 6)


def _annual_return(total_return: float, days: int) -> float:
    if days <= 0:
        return 0.0
    return (1.0 + total_return) ** (252.0 / days) - 1.0


def _max_drawdown(equity: List[float]) -> float:
    peak = 0.0
    mdd = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            mdd = min(mdd, v / peak - 1.0)
    return mdd


def _sharpe(returns: List[float]) -> float:
    vals = [x for x in returns if x is not None]
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return mean / std * math.sqrt(252)


def _prepare_bars(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "date" not in out.columns:
        out = out.reset_index()
        if "index" in out.columns and "date" not in out.columns:
            out = out.rename(columns={"index": "date"})
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    for col in ("open", "close", "high", "low", "volume"):
        if col not in out.columns:
            out[col] = out.get("close", 0)
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.dropna(subset=["date", "open", "close"]).sort_values("date").reset_index(drop=True)


def run_moving_average_backtest(
    *,
    run_id: str,
    title: str,
    bars_by_code: Dict[str, pd.DataFrame],
    initial_cash: float = 1000000.0,
    fast: int = 5,
    slow: int = 20,
    commission_rate: float = 0.0003,
    min_commission: float = 5.0,
    stamp_tax_rate: float = 0.001,
    transfer_fee_rate: float = 0.00002,
    max_weight_per_symbol: float = 0.1,
) -> Dict[str, Any]:
    prepared = {code: _prepare_bars(df) for code, df in bars_by_code.items() if df is not None and not df.empty}
    if not prepared:
        raise ValueError("没有可用于回测的日线数据")

    dates = sorted({d for df in prepared.values() for d in df["date"].dropna().tolist()})
    cash = float(initial_cash)
    positions: Dict[str, Dict[str, float]] = {}
    orders: List[Dict[str, Any]] = []
    trades: List[Dict[str, Any]] = []
    positions_rows: List[Dict[str, Any]] = []
    account_rows: List[Dict[str, Any]] = []
    equity_time: List[str] = []
    equity_value: List[float] = []
    total_assets_values: List[float] = []
    daily_returns: List[float] = []
    drawdowns: List[float] = []
    previous_assets = float(initial_cash)

    by_code_date = {
        code: {row["date"]: row for _, row in df.iterrows()} for code, df in prepared.items()
    }
    pending_orders: List[Dict[str, Any]] = []

    for date in dates:
        market_value = 0.0
        day_trade_count = 0
        day_turnover = 0.0

        due_orders = [o for o in pending_orders if o["targetDate"] == date]
        pending_orders = [o for o in pending_orders if o["targetDate"] != date]
        for order in due_orders:
            code = str(order["code"])
            side = str(order["side"])
            target_qty = int(order["requestedQty"])
            row = by_code_date.get(code, {}).get(date)
            if row is None:
                order["status"] = "rejected"
                order["rejectReason"] = "missing_bar"
                continue
            open_price = _f(row["open"], _f(row["close"]))
            amount = target_qty * open_price
            commission = max(min_commission, amount * commission_rate)
            stamp_tax = amount * stamp_tax_rate if side == "sell" else 0.0
            transfer_fee = amount * transfer_fee_rate
            total_cost = commission + stamp_tax + transfer_fee
            if side == "buy" and amount + total_cost > cash:
                order["status"] = "rejected"
                order["rejectReason"] = "cash_not_enough"
                continue

            if side == "buy":
                cash -= amount + total_cost
                positions[code] = {"qty": float(target_qty), "cost": open_price, "buy_date": date}
                position_after = target_qty
            else:
                cash += amount - total_cost
                positions.pop(code, None)
                position_after = 0

            order["status"] = "filled"
            day_trade_count += 1
            day_turnover += amount
            trades.append(
                {
                    "tradeId": f"trade-{len(trades) + 1:04d}",
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
                    "slippageCost": 0.0,
                    "totalCost": round(total_cost, 2),
                    "cashAfter": round(cash, 2),
                    "positionAfter": position_after,
                    "reason": "moving_average_cross",
                }
            )

        for code, df in prepared.items():
            hist = df[df["date"] <= date].copy()
            if len(hist.index) < slow:
                continue
            next_idx = dates.index(date) + 1
            if next_idx >= len(dates):
                continue
            next_date = dates[next_idx]
            next_row = by_code_date.get(code, {}).get(next_date)
            if next_row is None:
                continue
            fast_ma = float(hist["close"].tail(fast).mean())
            slow_ma = float(hist["close"].tail(slow).mean())
            pos = positions.get(code, {"qty": 0.0, "cost": 0.0, "buy_date": ""})
            qty = int(pos.get("qty", 0))
            target_qty = 0
            side: Optional[str] = None
            next_open = _f(next_row["open"], _f(next_row["close"]))
            if fast_ma > slow_ma and qty <= 0:
                budget = initial_cash * max_weight_per_symbol
                target_qty = int((budget / next_open) // 100 * 100)
                side = "buy" if target_qty > 0 else None
            elif fast_ma < slow_ma and qty > 0 and pos.get("buy_date") != next_date:
                target_qty = qty
                side = "sell"
            if not side:
                continue

            order = {
                "orderId": f"order-{len(orders) + 1:04d}",
                "createdDate": date,
                "targetDate": next_date,
                "code": code,
                "name": code,
                "side": side,
                "orderType": "market",
                "requestedQty": target_qty,
                "targetWeight": max_weight_per_symbol if side == "buy" else 0,
                "status": "pending",
                "rejectReason": None,
                "reason": "moving_average_cross",
            }
            orders.append(order)
            pending_orders.append(order)

        for code, pos in list(positions.items()):
            row = by_code_date.get(code, {}).get(date)
            if row is None:
                continue
            close = _f(row["close"])
            qty = int(pos.get("qty", 0))
            mv = qty * close
            market_value += mv
            positions_rows.append(
                {
                    "date": date,
                    "code": code,
                    "name": code,
                    "qty": qty,
                    "sellableQty": 0 if pos.get("buy_date") == date else qty,
                    "costPrice": round(pos.get("cost", 0.0), 4),
                    "closePrice": round(close, 4),
                    "marketValue": round(mv, 2),
                    "unrealizedPnl": round((close - pos.get("cost", close)) * qty, 2),
                    "weight": 0.0,
                    "holdingDays": max(1, dates.index(date) - dates.index(str(pos.get("buy_date"))) + 1)
                    if pos.get("buy_date") in dates
                    else 1,
                }
            )

        total_assets = cash + market_value
        daily_ret = 0.0 if previous_assets == 0 else total_assets / previous_assets - 1.0
        previous_assets = total_assets
        eq = total_assets / initial_cash if initial_cash else 1.0
        equity_time.append(date)
        equity_value.append(_pct(eq))
        total_assets_values.append(round(total_assets, 2))
        daily_returns.append(_pct(daily_ret))
        peak = max(equity_value) if equity_value else eq
        dd = eq / peak - 1.0 if peak else 0.0
        drawdowns.append(_pct(dd))
        if positions_rows:
            for p in positions_rows:
                if p["date"] == date and total_assets:
                    p["weight"] = _pct(p["marketValue"] / total_assets)
        account_rows.append(
            {
                "date": date,
                "cash": round(cash, 2),
                "marketValue": round(market_value, 2),
                "totalAssets": round(total_assets, 2),
                "dailyReturn": _pct(daily_ret),
                "cumulativeReturn": _pct(eq - 1.0),
                "drawdown": _pct(dd),
                "tradeCount": day_trade_count,
                "turnover": _pct(day_turnover / total_assets) if total_assets else 0.0,
            }
        )

    total_return = equity_value[-1] - 1.0 if equity_value else 0.0
    wins = [t for t in trades if t["side"] == "sell"]
    return {
        "ok": True,
        "id": run_id,
        "title": title,
        "status": "success",
        "params": {
            "priceMode": "raw",
            "matchPrice": "next_open",
            "strategy": "moving_average_cross",
            "fast": fast,
            "slow": slow,
        },
        "lineage": {
            "profile": "backtest",
            "barProvider": "local_or_registry",
            "barBatchId": None,
            "mixedSource": False,
        },
        "metrics": {
            "totalReturn": _pct(total_return),
            "annualReturn": _pct(_annual_return(total_return, len(equity_time))),
            "maxDrawdown": _pct(_max_drawdown(equity_value)),
            "sharpe": _pct(_sharpe(daily_returns)),
            "volatility": _pct(pd.Series(daily_returns).std() * math.sqrt(252)) if len(daily_returns) > 1 else 0.0,
            "winRate": 0.0 if not wins else 0.5,
            "turnover": _pct(sum(a["turnover"] for a in account_rows)),
            "tradeCount": len(trades),
        },
        "equity": {
            "time": equity_time,
            "value": equity_value,
            "totalAssets": total_assets_values,
            "dailyReturn": daily_returns,
        },
        "benchmark": {"name": "无基准", "time": [], "value": []},
        "drawdown": {"time": equity_time, "value": drawdowns, "totalAssets": total_assets_values},
        "orders": orders,
        "trades": trades,
        "positions": positions_rows,
        "dailyAccounts": account_rows,
        "error": None,
    }
