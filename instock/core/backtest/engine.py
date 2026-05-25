# -*- coding: utf-8 -*-
"""兼容层：保留 run_moving_average_backtest 对外签名。"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from instock.core.backtest.registry import run_backtest


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
    return run_backtest(
        run_id=run_id,
        title=title,
        strategy_id="moving_average_cross",
        strategy_params={"fast": fast, "slow": slow},
        bars_by_code=bars_by_code,
        initial_cash=initial_cash,
        commission_rate=commission_rate,
        min_commission=min_commission,
        stamp_tax_rate=stamp_tax_rate,
        transfer_fee_rate=transfer_fee_rate,
        max_weight_per_symbol=max_weight_per_symbol,
    )
