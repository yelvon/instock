# -*- coding: utf-8 -*-
"""Provider 输出 → 标准日线行字典。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from instock.core.data.normalize import normalize_provider_bars

HIST_COLS = [
    "date",
    "open",
    "close",
    "high",
    "low",
    "volume",
    "amount",
    "amplitude",
    "quote_change",
    "ups_downs",
    "turnover",
]


def dataframe_to_bar_rows(
    df: pd.DataFrame,
    provider_id: str,
    adjust_type: str = "raw",
) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    out_df = normalize_provider_bars(df, provider_id)
    if out_df is None or out_df.empty:
        return []
    if "date" not in out_df.columns:
        if isinstance(out_df.index, pd.DatetimeIndex):
            out_df = out_df.reset_index()
            if out_df.columns[0] != "date":
                out_df = out_df.rename(columns={out_df.columns[0]: "date"})
        else:
            out_df["date"] = pd.to_datetime(out_df.index).strftime("%Y-%m-%d")
    out_df["date"] = pd.to_datetime(out_df["date"], errors="coerce").dt.date
    rows: List[Dict[str, Any]] = []
    for _, r in out_df.iterrows():
        if pd.isna(r.get("date")):
            continue
        row = {"adjust_type": adjust_type}
        for c in HIST_COLS:
            v = r.get(c)
            if c == "date":
                row[c] = r["date"]
            elif pd.isna(v):
                row[c] = None
            else:
                row[c] = float(v) if c != "volume" else float(v)
        rows.append(row)
    return rows
