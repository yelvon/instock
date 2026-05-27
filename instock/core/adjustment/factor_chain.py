# -*- coding: utf-8 -*-
"""由除权事件生成前复权因子链（最新交易日因子=1）。"""

from __future__ import annotations

import pandas as pd

from instock.core.adjustment.apply_qfq import apply_baoli_qfq


def build_qfq_factor_series(
    raw_bars: pd.DataFrame,
    xdxr: pd.DataFrame,
) -> pd.Series:
    """
    输入 raw OHLC（index 为 date），输出与 index 对齐的 qfq_factor，最新日为 1。
    """
    if raw_bars is None or raw_bars.empty:
        return pd.Series(dtype=float)
    work = raw_bars.copy()
    if "date" in work.columns:
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        work = work.set_index("date")
    work = work.sort_index()
    if "close" not in work.columns:
        return pd.Series(1.0, index=work.index)

    if xdxr is None or xdxr.empty:
        return pd.Series(1.0, index=work.index)

    qfq_ohlc = apply_baoli_qfq(work[["open", "high", "low", "close"]].copy(), xdxr)
    raw_close = work["close"].astype(float)
    qfq_close = qfq_ohlc["close"].astype(float)
    factor = (qfq_close / raw_close).replace([float("inf"), float("-inf")], pd.NA)
    factor = factor.fillna(1.0)
    if len(factor) > 0:
        last = float(factor.iloc[-1]) or 1.0
        factor = factor / last
    return factor
