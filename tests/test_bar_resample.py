# -*- coding: utf-8 -*-

import pandas as pd

from instock.core.canonical.bar_resample import (
    normalize_kline_period,
    period_key_for_date,
    resample_ohlcv,
)
from instock.core.canonical.kline_payload import map_marks_to_period


def _daily():
    return pd.DataFrame(
        [
            {"date": "2024-01-02", "open": 10, "high": 11, "low": 9.5, "close": 10.5, "volume": 100},
            {"date": "2024-01-03", "open": 10.5, "high": 11.2, "low": 10, "close": 11, "volume": 120},
            {"date": "2024-01-04", "open": 11, "high": 11.5, "low": 10.8, "close": 11.2, "volume": 90},
            {"date": "2024-01-08", "open": 11.5, "high": 12, "low": 11, "close": 11.8, "volume": 200},
            {"date": "2024-01-09", "open": 11.8, "high": 12.2, "low": 11.5, "close": 12, "volume": 150},
            {"date": "2024-01-31", "open": 12, "high": 12.5, "low": 11.8, "close": 12.3, "volume": 80},
            {"date": "2024-02-01", "open": 12.3, "high": 12.8, "low": 12, "close": 12.6, "volume": 110},
        ]
    )


def test_normalize_kline_period():
    assert normalize_kline_period("weekly") == "weekly"
    assert normalize_kline_period("1w") == "weekly"
    assert normalize_kline_period("monthly") == "monthly"
    assert normalize_kline_period("") == "daily"


def test_resample_weekly():
    w = resample_ohlcv(_daily(), "weekly")
    assert len(w) == 3
    assert w.iloc[0]["date"] == "2024-01-04"
    assert w.iloc[0]["open"] == 10.0
    assert w.iloc[0]["close"] == 11.2
    assert w.iloc[0]["high"] == 11.5
    assert w.iloc[0]["low"] == 9.5
    assert w.iloc[0]["volume"] == 310
    assert w.iloc[1]["date"] == "2024-01-09"
    assert w.iloc[2]["date"] == "2024-02-01"


def test_resample_monthly():
    m = resample_ohlcv(_daily(), "monthly")
    assert len(m) == 2
    assert m.iloc[0]["date"] == "2024-01-31"
    assert m.iloc[0]["close"] == 12.3
    assert m.iloc[1]["date"] == "2024-02-01"
    assert m.iloc[1]["close"] == 12.6


def test_map_marks_to_period_weekly():
    w = resample_ohlcv(_daily(), "weekly")
    dates = list(w["date"])
    marks = [{"date": "2024-01-03", "side": "buy", "price": 10.5, "qty": 100}]
    mapped = map_marks_to_period(marks, dates, "weekly")
    assert len(mapped) == 1
    assert mapped[0]["date"] == "2024-01-04"


def test_period_key_for_date():
    assert period_key_for_date("2024-01-03", "daily") == "2024-01-03"
    assert "2024-01" in period_key_for_date("2024-01-15", "monthly")
