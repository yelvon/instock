# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime
import urllib.request
from typing import Any, Dict, List

import pandas as pd

from instock.core.data.normalize import merge_tencent_valuation
from instock.core.data.provider import FetchResult
from instock.core.data.providers._base import BaseProvider

UA = "Mozilla/5.0 (compatible; InStock/1.0)"


def tencent_quote(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    if not codes:
        return {}
    prefixed = []
    for c in codes:
        c = str(c).zfill(6)[:6]
        if c.startswith(("6", "9")):
            prefixed.append(f"sh{c}")
        elif c.startswith("8"):
            prefixed.append(f"bj{c}")
        else:
            prefixed.append(f"sz{c}")
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    resp = urllib.request.urlopen(req, timeout=15)
    data = resp.read().decode("gbk", errors="replace")
    result: Dict[str, Dict[str, Any]] = {}
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        code = key[2:] if len(key) > 2 else key
        result[code] = {
            "name": vals[1],
            "price": _f(vals[3]),
            "pe_ttm": _f(vals[39]),
            "turnover_pct": _f(vals[38]),
            "mcap_yi": _f(vals[44]),
            "float_mcap_yi": _f(vals[45]),
            "pb": _f(vals[46]),
            "pe_static": _f(vals[52]),
        }
    return result


def _f(x: str) -> float:
    try:
        return float(x) if x else 0.0
    except (TypeError, ValueError):
        return 0.0


class Provider(BaseProvider):
    provider_id = "tencent"

    def capabilities(self) -> set:
        return {"spot_valuation_enrich", "daily_spot_snapshot_partial"}

    def healthcheck(self) -> bool:
        try:
            r = tencent_quote(["600000"])
            return "600000" in r or "000001" in r
        except Exception:
            return False

    def enrich_spot(
        self,
        df: pd.DataFrame,
        trade_date: datetime.date,
        *,
        mode: str = "valuation_only",
        **kwargs,
    ) -> FetchResult:
        if df is None or df.empty or "code" not in df.columns:
            return FetchResult(ok=False, provider_id=self.provider_id, data=df, error="无 code 列")
        codes = [str(c).zfill(6)[:6] for c in df["code"].tolist()]
        batch_size = 80
        merged = {}
        for i in range(0, len(codes), batch_size):
            merged.update(tencent_quote(codes[i : i + batch_size]))
        out = merge_tencent_valuation(df, merged)
        from instock.core.data.normalize import TENCENT_SPOT_MAP

        return FetchResult(
            ok=True,
            data=out,
            provider_id=self.provider_id,
            trade_date=trade_date,
            is_partial=True,
            fields_provided=list(TENCENT_SPOT_MAP.values()),
        )
