# -*- coding: utf-8 -*-
"""桥接 tablestructure 选股函数：命中则次日等权买入（回测内用历史 K 线调用 check_*）。"""

from __future__ import annotations

import datetime
from typing import Any, Callable, Dict, Optional

import pandas as pd

import instock.core.tablestructure as tbs
from instock.core.backtest.strategy import Strategy


def _find_screening_func(strategy_table: str) -> Optional[Callable[..., Any]]:
    for item in tbs.TABLE_CN_STOCK_STRATEGIES:
        if item["name"] == strategy_table:
            return item["func"]
    return None


def _hist_for_check(df: pd.DataFrame, date_str: str) -> pd.DataFrame:
    hist = df[df["date"] <= date_str].copy()
    if "p_change" not in hist.columns and len(hist) > 1:
        hist["p_change"] = hist["close"].pct_change() * 100
    return hist


class ScreeningBridgeStrategy(Strategy):
    strategy_id = "screening_bridge"
    default_params = {"strategy_table": "cn_stock_strategy_enter"}

    def next(self, date: str) -> None:
        table = str(self.params.get("strategy_table") or "cn_stock_strategy_enter")
        check_fn = _find_screening_func(table)
        if check_fn is None:
            return
        try:
            dt = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return
        max_w = self.cerebro.max_weight_per_symbol
        hits = []
        for code, df in self.cerebro.prepared.items():
            if self.cerebro.broker.get_position_qty(code) > 0:
                continue
            hist = _hist_for_check(df, date)
            if len(hist) < 30:
                continue
            code_name = (dt, code, code)
            try:
                if check_fn(code_name, hist, date=dt):
                    hits.append(code)
            except Exception:
                continue
        if not hits:
            return
        weight = min(max_w, 1.0 / len(hits))
        for code in hits:
            self.cerebro.buy_target_weight(
                date=date,
                code=code,
                target_weight=weight,
                reason=f"{self.strategy_id}:{table}",
            )
