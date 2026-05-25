# -*- coding: utf-8 -*-
"""K 线数据准备与按日索引。"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd


def prepare_bars(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "date" not in out.columns:
        out = out.reset_index()
        if "index" in out.columns and "date" not in out.columns:
            out = out.rename(columns={"index": "date"})
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    for col in ("open", "close", "high", "low", "volume"):
        if col not in out.columns:
            out[col] = out.get("close", 0)
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.dropna(subset=["date", "open", "close"]).sort_values("date").reset_index(drop=True)


def build_feeds(
    bars_by_code: Dict[str, pd.DataFrame],
) -> Tuple[Dict[str, pd.DataFrame], List[str], Dict[str, Dict[str, dict]]]:
    prepared = {
        code: prepare_bars(df) for code, df in bars_by_code.items() if df is not None and not df.empty
    }
    if not prepared:
        raise ValueError("没有可用于回测的日线数据")
    dates = sorted({d for df in prepared.values() for d in df["date"].dropna().tolist()})
    by_code_date = {
        code: {row["date"]: row.to_dict() for _, row in df.iterrows()} for code, df in prepared.items()
    }
    return prepared, dates, by_code_date
