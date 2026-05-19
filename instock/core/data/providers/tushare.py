# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd

from instock.core.data.provider import FetchResult
from instock.core.data.providers._base import BaseProvider

TUSHARE_TOKEN_FILE = (
    Path(__file__).resolve().parents[3] / "config" / "tushare_token.txt"
)


def read_tushare_token() -> str:
    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if token:
        return token
    if TUSHARE_TOKEN_FILE.exists():
        return TUSHARE_TOKEN_FILE.read_text(encoding="utf-8", errors="replace").strip()
    return ""


def to_ts_code(code: str) -> str:
    s = str(code).strip()
    if "." in s:
        left, right = s.split(".", 1)
        if left.isdigit():
            return f"{left.zfill(6)}.{right.upper()}"
        return f"{right.zfill(6)}.{left.upper()}"
    s = s.zfill(6)
    if s.startswith("6"):
        return f"{s}.SH"
    if s.startswith(("8", "4")):
        return f"{s}.BJ"
    return f"{s}.SZ"


def _yyyymmdd(value: Optional[str], default: str = "") -> str:
    if not value:
        return default
    return str(value).replace("-", "")


def _normalize_daily(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["trade_date"], format="%Y%m%d", errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    out["volume"] = pd.to_numeric(out.get("vol"), errors="coerce") * 100
    # Tushare daily amount unit is thousand yuan; Eastmoney path uses yuan.
    out["amount"] = pd.to_numeric(out.get("amount"), errors="coerce") * 1000
    out["quote_change"] = pd.to_numeric(out.get("pct_chg"), errors="coerce")
    out["ups_downs"] = pd.to_numeric(out.get("change"), errors="coerce")
    out["amplitude"] = None
    out["turnover"] = pd.to_numeric(out.get("turnover_rate"), errors="coerce")
    cols = [
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
    for col in cols:
        if col not in out.columns:
            out[col] = None
    out = out[cols].sort_values("date").reset_index(drop=True)
    for col in ("open", "close", "high", "low"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


class Provider(BaseProvider):
    provider_id = "tushare"

    def capabilities(self) -> set:
        return {"daily_bar_raw", "daily_bar"}

    def healthcheck(self) -> bool:
        return bool(read_tushare_token())

    def fetch_bars(
        self,
        code: str,
        date_from: str,
        date_to: Optional[str] = None,
        *,
        adjust: str = "raw",
        **kwargs,
    ) -> FetchResult:
        if adjust not in ("", "raw"):
            return FetchResult(
                ok=False,
                provider_id=self.provider_id,
                error="Tushare provider 当前仅支持 raw 日线",
            )
        token = read_tushare_token()
        if not token:
            return FetchResult(
                ok=False,
                provider_id=self.provider_id,
                error="未配置 TUSHARE_TOKEN 或 instock/config/tushare_token.txt",
            )
        try:
            import tushare as ts

            api = ts.pro_api(token)
            df = api.daily(
                ts_code=to_ts_code(code),
                start_date=_yyyymmdd(date_from),
                end_date=_yyyymmdd(date_to, "20500101"),
            )
        except Exception as e:
            return FetchResult(ok=False, provider_id=self.provider_id, error=str(e))
        if df is None or df.empty:
            return FetchResult(ok=False, provider_id=self.provider_id, error="Tushare K 线为空")
        data = _normalize_daily(df)
        if data.empty:
            return FetchResult(ok=False, provider_id=self.provider_id, error="Tushare K 线为空")
        return FetchResult(
            ok=True,
            data=data,
            provider_id=self.provider_id,
            metadata={"adjust": "raw"},
            fields_provided=list(data.columns),
        )
