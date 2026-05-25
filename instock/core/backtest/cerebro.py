# -*- coding: utf-8 -*-
"""回测主引擎（Cerebro）：组装策略、数据、经纪商。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

import pandas as pd

from instock.core.backtest.broker import SimBroker
from instock.core.backtest.feeds import build_feeds
from instock.core.backtest.result import build_success_payload, pct
from instock.core.backtest.strategy import Strategy


class Cerebro:
    def __init__(
        self,
        *,
        run_id: str,
        title: str,
        initial_cash: float = 1000000.0,
        commission_rate: float = 0.0003,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 0.001,
        transfer_fee_rate: float = 0.00002,
        max_weight_per_symbol: float = 0.1,
    ) -> None:
        self.run_id = run_id
        self.title = title
        self.initial_cash = initial_cash
        self.max_weight_per_symbol = max_weight_per_symbol
        self.broker = SimBroker(
            initial_cash=initial_cash,
            commission_rate=commission_rate,
            min_commission=min_commission,
            stamp_tax_rate=stamp_tax_rate,
            transfer_fee_rate=transfer_fee_rate,
        )
        self._strategy_cls: Optional[Type[Strategy]] = None
        self._strategy_params: Dict[str, Any] = {}
        self._strategy_id = "unknown"
        self.prepared: Dict[str, pd.DataFrame] = {}
        self.dates: List[str] = []
        self.by_code_date: Dict[str, Dict[str, dict]] = {}
        self.equity_time: List[str] = []
        self.equity_value: List[float] = []
        self.total_assets_values: List[float] = []
        self.daily_returns: List[float] = []
        self.drawdowns: List[float] = []
        self.positions_rows: List[Dict[str, Any]] = []
        self.account_rows: List[Dict[str, Any]] = []
        self._previous_assets = float(initial_cash)

    def add_strategy(
        self, strategy_cls: Type[Strategy], params: Optional[Dict[str, Any]] = None
    ) -> "Cerebro":
        self._strategy_cls = strategy_cls
        self._strategy_params = dict(params or {})
        self._strategy_id = getattr(strategy_cls, "strategy_id", strategy_cls.__name__)
        return self

    def set_bars(self, bars_by_code: Dict[str, pd.DataFrame]) -> "Cerebro":
        self.prepared, self.dates, self.by_code_date = build_feeds(bars_by_code)
        return self

    def run(self) -> Dict[str, Any]:
        if self._strategy_cls is None:
            raise ValueError("未添加策略")
        if not self.prepared:
            raise ValueError("未设置 bars_by_code")
        strategy = self._strategy_cls(self, self._strategy_params)
        strategy.start()
        for date in self.dates:
            day_trade_count, day_turnover = self.broker.process_due_orders(
                date, self.by_code_date
            )
            strategy.next(date)
            market_value, day_pos = self.broker.snapshot_positions(
                date, self.dates, self.by_code_date
            )
            self.positions_rows.extend(day_pos)
            total_assets = self.broker.cash + market_value
            daily_ret = (
                0.0
                if self._previous_assets == 0
                else total_assets / self._previous_assets - 1.0
            )
            self._previous_assets = total_assets
            eq = total_assets / self.initial_cash if self.initial_cash else 1.0
            self.equity_time.append(date)
            self.equity_value.append(pct(eq))
            self.total_assets_values.append(round(total_assets, 2))
            self.daily_returns.append(pct(daily_ret))
            peak = max(self.equity_value) if self.equity_value else eq
            dd = eq / peak - 1.0 if peak else 0.0
            self.drawdowns.append(pct(dd))
            if day_pos and total_assets:
                for p in day_pos:
                    if p["date"] == date:
                        p["weight"] = pct(p["marketValue"] / total_assets)
            self.account_rows.append(
                {
                    "date": date,
                    "cash": round(self.broker.cash, 2),
                    "marketValue": round(market_value, 2),
                    "totalAssets": round(total_assets, 2),
                    "dailyReturn": pct(daily_ret),
                    "cumulativeReturn": pct(eq - 1.0),
                    "drawdown": pct(dd),
                    "tradeCount": day_trade_count,
                    "turnover": pct(day_turnover / total_assets) if total_assets else 0.0,
                }
            )
        strategy.stop()
        extra = dict(self._strategy_params)
        return build_success_payload(
            run_id=self.run_id,
            title=self.title,
            strategy_id=self._strategy_id,
            strategy_params=self._strategy_params,
            orders=self.broker.orders,
            trades=self.broker.trades,
            positions_rows=self.positions_rows,
            account_rows=self.account_rows,
            equity_time=self.equity_time,
            equity_value=self.equity_value,
            total_assets_values=self.total_assets_values,
            daily_returns=self.daily_returns,
            drawdowns=self.drawdowns,
            initial_cash=self.initial_cash,
            extra_params=extra,
        )

    def next_trading_date(self, date: str) -> Optional[str]:
        try:
            idx = self.dates.index(date)
        except ValueError:
            return None
        if idx + 1 >= len(self.dates):
            return None
        return self.dates[idx + 1]

    def buy_target_weight(
        self, *, date: str, code: str, target_weight: float, reason: str
    ) -> None:
        next_date = self.next_trading_date(date)
        if not next_date:
            return
        row = self.by_code_date.get(code, {}).get(next_date)
        if not row:
            return
        from instock.core.backtest.result import _f

        next_open = _f(row.get("open"), _f(row.get("close")))
        if next_open <= 0:
            return
        budget = self.initial_cash * target_weight
        target_qty = int((budget / next_open) // 100 * 100)
        if target_qty <= 0:
            return
        self.broker.submit_order(
            created_date=date,
            target_date=next_date,
            code=code,
            side="buy",
            requested_qty=target_qty,
            target_weight=target_weight,
            reason=reason,
        )

    def sell_all(self, *, date: str, code: str, reason: str) -> None:
        pos = self.broker.get_position(code)
        qty = int(pos.get("qty", 0))
        if qty <= 0:
            return
        next_date = self.next_trading_date(date)
        if not next_date:
            return
        if pos.get("buy_date") == next_date:
            return
        self.broker.submit_order(
            created_date=date,
            target_date=next_date,
            code=code,
            side="sell",
            requested_qty=qty,
            target_weight=0.0,
            reason=reason,
        )
