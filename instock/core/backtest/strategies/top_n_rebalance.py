# -*- coding: utf-8 -*-
"""Top-N 等权调仓：表驱动选股信号。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import instock.core.tablestructure as tbs
from instock.core.backtest.strategy import Strategy
from instock.core.backtest.universe_loader import load_daily_rows


def _rank_key(row: Dict[str, Any], rank_by: str) -> float:
    try:
        return float(row.get(rank_by) or 0)
    except (TypeError, ValueError):
        return 0.0


class TopNRebalanceStrategy(Strategy):
    strategy_id = "top_n_rebalance"
    default_params = {
        "signal_source": "selection_table",
        "table": tbs.TABLE_CN_STOCK_SELECTION["name"],
        "top_n": 10,
        "rebalance_days": 5,
        "rank_by": "change_rate",
        "exit_when_out": True,
    }

    def start(self) -> None:
        self._day_idx = 0
        self._table = str(self.params.get("table") or tbs.TABLE_CN_STOCK_SELECTION["name"])
        self._top_n = max(1, int(self.params.get("top_n") or 10))
        self._rebalance_days = max(1, int(self.params.get("rebalance_days") or 5))
        self._rank_by = str(self.params.get("rank_by") or "change_rate")
        self._exit_when_out = bool(self.params.get("exit_when_out", True))
        self._filters = self.params.get("filters") if isinstance(self.params.get("filters"), dict) else None

    def _target_codes(self, date: str) -> List[str]:
        rows = load_daily_rows(self._table, date, filters=self._filters)
        if not rows:
            return []
        universe_codes = set(self.cerebro.prepared.keys())
        filtered = [r for r in rows if str(r.get("code", "")).zfill(6)[:6] in universe_codes]
        if not filtered:
            filtered = rows
        if self._rank_by and self._rank_by != "equal":
            filtered.sort(key=lambda r: _rank_key(r, self._rank_by), reverse=True)
        codes = []
        for r in filtered:
            c = str(r.get("code", "")).zfill(6)[:6]
            if c and c not in codes:
                codes.append(c)
            if len(codes) >= self._top_n:
                break
        return codes

    def next(self, date: str) -> None:
        self._day_idx += 1
        if (self._day_idx - 1) % self._rebalance_days != 0:
            return
        targets = self._target_codes(date)
        if not targets:
            return
        held = {
            code
            for code, pos in self.cerebro.broker.positions.items()
            if int(pos.get("qty", 0)) > 0
        }
        if self._exit_when_out:
            for code in list(held):
                if code not in targets:
                    self.cerebro.sell_all(date=date, code=code, reason=f"{self.strategy_id}:exit")
        weight = min(self.cerebro.max_weight_per_symbol, 1.0 / len(targets))
        for code in targets:
            if self.cerebro.broker.get_position_qty(code) <= 0:
                self.cerebro.buy_target_weight(
                    date=date,
                    code=code,
                    target_weight=weight,
                    reason=f"{self.strategy_id}:rebalance",
                )
