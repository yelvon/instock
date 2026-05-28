# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from instock.core.data.normalize import normalize_mootdx_bars
from instock.core.data.profile import tdx_dir
from instock.core.data.provider import FetchResult
from instock.core.data.providers._base import BaseProvider


def _reader():
    from mootdx.reader import Reader

    d = tdx_dir()
    if not d or not Path(d).is_dir():
        return None
    return Reader.factory(market="std", tdxdir=d)


class Provider(BaseProvider):
    provider_id = "mootdx_local"

    def capabilities(self) -> set:
        return {"daily_bar_raw", "daily_bar", "daily_spot_snapshot_partial"}

    def healthcheck(self) -> bool:
        r = _reader()
        if r is None:
            return False
        try:
            df = r.daily(symbol="600000")
            return df is not None and not df.empty
        except Exception:
            return False

    def fetch_bars(
        self,
        code: str,
        date_from: str,
        date_to: Optional[str] = None,
        *,
        adjust: str = "raw",
        **kwargs,
    ) -> FetchResult:
        r = _reader()
        if r is None:
            return FetchResult(
                ok=False,
                provider_id=self.provider_id,
                error="INSTOCK_TDX_DIR 未配置或目录不存在",
            )
        try:
            df = r.daily(symbol=code)
        except Exception as e:
            return FetchResult(ok=False, provider_id=self.provider_id, error=str(e))
        if df is None or df.empty:
            return FetchResult(ok=False, provider_id=self.provider_id, error="TDX 日线为空")
        df = normalize_mootdx_bars(df)
        if "date" in df.columns:
            df["_d"] = pd.to_datetime(df["date"], errors="coerce")
            d0 = pd.to_datetime(date_from, errors="coerce")
            mask = df["_d"] >= d0
            if date_to:
                d1 = pd.to_datetime(date_to, errors="coerce")
                mask &= df["_d"] <= d1
            df = df.loc[mask].drop(columns=["_d"], errors="ignore")
        meta = {"tdx_dir": tdx_dir(), "adjust": "raw"}
        return FetchResult(
            ok=not df.empty,
            data=df,
            provider_id=self.provider_id,
            metadata=meta,
            fields_provided=list(df.columns) if hasattr(df, "columns") else [],
            error=None if not df.empty else "区间无数据",
        )

    def fetch_spot(self, trade_date: datetime.date, **kwargs) -> FetchResult:
        """从日线末行截取价量 partial（非全市场）。"""
        code = kwargs.get("code")
        if not code:
            return FetchResult(ok=False, provider_id=self.provider_id, error="partial 需 code")
        br = self.fetch_bars(code, trade_date.strftime("%Y%m%d"), adjust="raw")
        if not br.ok or br.data is None or br.data.empty:
            return br
        row = br.data.iloc[-1:]
        return FetchResult(
            ok=True,
            data=row,
            provider_id=self.provider_id,
            trade_date=trade_date,
            is_partial=True,
        )
