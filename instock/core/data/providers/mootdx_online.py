# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime
from typing import Optional

import pandas as pd

from instock.core.data.normalize import normalize_mootdx_bars
from instock.core.data.provider import FetchResult
from instock.core.data.providers._base import BaseProvider

_client = None


def _default_hq_server() -> tuple:
    from mootdx.consts import HQ_HOSTS

    host = HQ_HOSTS[0]
    return (str(host[1]), int(host[2]))


def _resolve_hq_server() -> tuple:
    """mootdx 首次在 Docker 内 BESTIP.HQ 常为空字符串，需显式指定 server。"""
    try:
        from mootdx import config

        config.setup()
        best = (config.get("BESTIP") or {}).get("HQ")
        if isinstance(best, (list, tuple)) and len(best) >= 2:
            return (str(best[0]), int(best[1]))
    except Exception:
        pass
    return _default_hq_server()


def _quotes():
    global _client
    if _client is None:
        from mootdx.quotes import Quotes

        _client = Quotes.factory(
            market="std",
            quiet=True,
            timeout=15,
            server=_resolve_hq_server(),
        )
    return _client


class Provider(BaseProvider):
    provider_id = "mootdx_online"

    def capabilities(self) -> set:
        return {"daily_bar_raw", "daily_bar", "daily_spot_snapshot_partial"}

    def healthcheck(self) -> bool:
        try:
            c = _quotes()
            df = c.bars(symbol="600000", frequency=9, offset=2)
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
        try:
            c = _quotes()
            if adjust in ("qfq", "adjusted"):
                end = date_to.replace("-", "") if date_to else None
                start = date_from.replace("-", "") if date_from else None
                df = c.get_k_data(code, start, end)
            else:
                df = c.bars(symbol=code, frequency=9, offset=800)
        except Exception as e:
            return FetchResult(ok=False, provider_id=self.provider_id, error=str(e))
        if df is None or df.empty:
            return FetchResult(ok=False, provider_id=self.provider_id, error="mootdx online 为空")
        df = normalize_mootdx_bars(df)
        if "date" in df.columns:
            df["_d"] = pd.to_datetime(df["date"], errors="coerce")
            d0 = pd.to_datetime(date_from, errors="coerce")
            mask = df["_d"] >= d0
            if date_to:
                mask &= df["_d"] <= pd.to_datetime(date_to, errors="coerce")
            df = df.loc[mask].drop(columns=["_d"], errors="ignore")
        if "date" in df.columns:
            df = df.set_index("date")
        return FetchResult(
            ok=not df.empty,
            data=df,
            provider_id=self.provider_id,
            metadata={"adjust": adjust},
        )

    def fetch_spot(self, trade_date: datetime.date, **kwargs) -> FetchResult:
        codes = kwargs.get("codes")
        if not codes:
            return FetchResult(ok=False, provider_id=self.provider_id, error="partial 需 codes 列表")
        try:
            c = _quotes()
            q = c.quotes(symbol=list(codes)[:80])
        except Exception as e:
            return FetchResult(ok=False, provider_id=self.provider_id, error=str(e))
        if q is None or q.empty:
            return FetchResult(ok=False, provider_id=self.provider_id, error="quotes 为空")
        return FetchResult(
            ok=True,
            data=q,
            provider_id=self.provider_id,
            trade_date=trade_date,
            is_partial=True,
        )
