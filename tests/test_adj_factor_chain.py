# -*- coding: utf-8 -*-
"""前复权因子与 baoli 算法单测。"""

import pandas as pd

from instock.core.adjustment.apply_qfq import apply_baoli_qfq
from instock.core.adjustment.factor_chain import build_qfq_factor_series


def test_latest_bar_factor_is_one():
    dates = pd.date_range("2024-01-02", periods=5, freq="B")
    raw = pd.DataFrame(
        {
            "date": dates,
            "open": [10.0, 10.1, 10.2, 10.0, 9.5],
            "high": [10.5] * 5,
            "low": [9.5] * 5,
            "close": [10.0, 10.1, 10.2, 10.0, 9.5],
        }
    )
    xdxr = pd.DataFrame(
        {
            "fenhong": [0.5],
            "peigu": [0.0],
            "peigujia": [0.0],
            "songzhuangu": [0.0],
        },
        index=[dates[2]],
    )
    factor = build_qfq_factor_series(raw, xdxr)
    assert len(factor) == 5
    assert abs(float(factor.iloc[-1]) - 1.0) < 1e-9


def test_baoli_adjusts_history_only():
    dates = pd.date_range("2024-06-03", periods=3, freq="B")
    df = pd.DataFrame(
        {"open": [10.0, 10.0, 10.0], "high": [11.0, 11.0, 11.0],
         "low": [9.0, 9.0, 9.0], "close": [10.0, 10.0, 10.0]},
        index=dates,
    )
    xdxr = pd.DataFrame(
        {"fenhong": [1.0], "peigu": [0.0], "peigujia": [0.0], "songzhuangu": [0.0]},
        index=[dates[1]],
    )
    out = apply_baoli_qfq(df, xdxr)
    assert float(out.loc[dates[0], "close"]) < 10.0
    assert float(out.loc[dates[2], "close"]) == 10.0
