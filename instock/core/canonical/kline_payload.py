# -*- coding: utf-8 -*-
"""标准库 K 线序列组装（raw/qfq，日/周/月）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from instock.core.canonical.bar_resample import (
    normalize_kline_period,
    period_key_for_date,
    resample_ohlcv,
)


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def dataframe_to_kline_series(df: pd.DataFrame) -> tuple[List[str], List[List[float]], List[float]]:
    dates: List[str] = []
    ohlc: List[List[float]] = []
    volume: List[float] = []
    if df is None or df.empty:
        return dates, ohlc, volume
    for _, row in df.iterrows():
        d = str(row.get("date") or "")[:10]
        if not d:
            continue
        o = _f(row.get("open"))
        c = _f(row.get("close"))
        h = _f(row.get("high"))
        l = _f(row.get("low"))
        if c <= 0:
            continue
        dates.append(d)
        ohlc.append([round(o, 4), round(c, 4), round(l, 4), round(h, 4)])
        volume.append(_f(row.get("volume")))
    return dates, ohlc, volume


def map_marks_to_period(
    marks: List[Dict[str, Any]],
    bar_dates: List[str],
    period: str,
) -> List[Dict[str, Any]]:
    norm = normalize_kline_period(period)
    if norm == "daily" or not marks or not bar_dates:
        return marks
    key_to_bar: Dict[str, str] = {}
    for d in bar_dates:
        key_to_bar[period_key_for_date(d, norm)] = d
    out: List[Dict[str, Any]] = []
    for m in marks:
        md = str(m.get("date") or "")[:10]
        if not md:
            continue
        bar_date = key_to_bar.get(period_key_for_date(md, norm))
        if not bar_date:
            continue
        item = dict(m)
        item["date"] = bar_date
        out.append(item)
    return out


def load_canonical_bars_df(
    code: str,
    date_from: str,
    date_to: str,
    adjust_type: str = "raw",
) -> pd.DataFrame:
    code = str(code).strip().zfill(6)[:6]
    try:
        from instock.core.canonical.reader import canonical_read_enabled, load_canonical_bars

        if canonical_read_enabled():
            df = load_canonical_bars(code, date_from, date_to, adjust_type=adjust_type)
            if df is not None and not df.empty:
                return df
    except Exception:
        pass
    return pd.DataFrame()


def build_canonical_kline_payload(
    code: str,
    date_from: str,
    date_to: str,
    adjust_type: str = "raw",
    period: str = "daily",
    *,
    marks: Optional[List[Dict[str, Any]]] = None,
    empty_hint: Optional[str] = None,
) -> Dict[str, Any]:
    code = str(code).strip().zfill(6)[:6]
    date_from = str(date_from or "")[:10]
    date_to = str(date_to or "")[:10]
    adjust_type = (adjust_type or "raw").strip().lower() or "raw"
    norm_period = normalize_kline_period(period)

    df = load_canonical_bars_df(code, date_from, date_to, adjust_type)
    if df is None or df.empty:
        hint = empty_hint or (
            f"{code} 在 {date_from} ~ {date_to} 无标准日线"
            + ("（qfq）" if adjust_type == "qfq" else "")
            + "，请先在回测数据管理补数或运行派生前复权"
        )
        return {
            "ok": True,
            "code": code,
            "adjustType": adjust_type,
            "period": norm_period,
            "dateFrom": date_from,
            "dateTo": date_to,
            "dates": [],
            "ohlc": [],
            "volume": [],
            "marks": map_marks_to_period(marks or [], [], norm_period),
            "empty": True,
            "hint": hint,
        }

    if norm_period != "daily":
        df = resample_ohlcv(df, norm_period)

    dates, ohlc, volume = dataframe_to_kline_series(df)
    mapped_marks = map_marks_to_period(marks or [], dates, norm_period)

    return {
        "ok": True,
        "code": code,
        "adjustType": adjust_type,
        "period": norm_period,
        "dateFrom": date_from,
        "dateTo": date_to,
        "dates": dates,
        "ohlc": ohlc,
        "volume": volume,
        "marks": mapped_marks,
        "empty": False,
    }
