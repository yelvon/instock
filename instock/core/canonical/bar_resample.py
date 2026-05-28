# -*- coding: utf-8 -*-
"""由标准日线 OHLCV 聚合周 K、月 K（运行时派生，不落库）。"""

from __future__ import annotations

import pandas as pd

_WEEKLY = "weekly"
_MONTHLY = "monthly"
_DAILY = "daily"


def normalize_kline_period(period: str) -> str:
    p = (period or _DAILY).strip().lower()
    if p in ("weekly", "1w", "w", "week"):
        return _WEEKLY
    if p in ("monthly", "1m", "m", "month"):
        return _MONTHLY
    return _DAILY


def _period_series(dates: pd.Series, period: str) -> pd.Series:
    ts = pd.to_datetime(dates)
    if period == _WEEKLY:
        return ts.dt.to_period("W-SUN")
    if period == _MONTHLY:
        return ts.dt.to_period("M")
    raise ValueError(f"unsupported resample period: {period}")


def resample_ohlcv(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    将日线聚合为周 K 或月 K。
    周期标签 date 取该自然周/月内最后一个交易日。
    """
    norm = normalize_kline_period(period)
    if norm == _DAILY:
        return df.copy()

    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    work = work.sort_values("date")
    for col in ("open", "high", "low", "close", "volume"):
        if col not in work.columns:
            work[col] = 0.0
    work = work.dropna(subset=["date"])
    if work.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    work["_period"] = _period_series(work["date"], norm)
    agg = (
        work.groupby("_period", sort=True)
        .agg(
            date=("date", "last"),
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        )
        .reset_index(drop=True)
    )
    agg["date"] = agg["date"].dt.strftime("%Y-%m-%d")
    return agg[["date", "open", "high", "low", "close", "volume"]]


def period_key_for_date(date_str: str, period: str) -> str:
    """用于将买卖点映射到周/月 K 横轴日期。"""
    norm = normalize_kline_period(period)
    if norm == _DAILY:
        return str(date_str)[:10]
    ts = pd.Timestamp(str(date_str)[:10])
    if norm == _WEEKLY:
        return str(ts.to_period("W-SUN"))
    return str(ts.to_period("M"))
