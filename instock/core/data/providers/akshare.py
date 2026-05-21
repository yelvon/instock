# -*- coding: utf-8 -*-
"""Akshare A 股日线（raw）。"""

from __future__ import annotations

import os
import time
from typing import Optional

import pandas as pd

from instock.core.data.normalize import normalize_akshare_bars
from instock.core.data.provider import FetchResult
from instock.core.data.providers._base import BaseProvider


def _yyyymmdd(value: Optional[str], default: str = "") -> str:
    if not value:
        return default
    return str(value).replace("-", "")[:8]


class Provider(BaseProvider):
    provider_id = "akshare"

    def capabilities(self) -> set:
        return {"daily_bar_raw", "daily_bar"}

    def healthcheck(self) -> bool:
        try:
            import akshare  # noqa: F401

            return True
        except ImportError:
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
        if not self.healthcheck():
            return FetchResult(
                ok=False,
                provider_id=self.provider_id,
                domain_id="daily_bar_raw",
                error="akshare 未安装",
            )
        import akshare as ak

        sym = str(code).strip().zfill(6)[:6]
        start = _yyyymmdd(date_from)
        end = _yyyymmdd(date_to) or ""
        adj = ""
        if str(adjust).lower() in ("qfq", "hfq"):
            adj = str(adjust).lower()
        retries = max(1, int(os.environ.get("INSTOCK_AKSHARE_RETRIES", "3")))
        last_err: Optional[str] = None
        raw = None
        for attempt in range(1, retries + 1):
            try:
                raw = ak.stock_zh_a_hist(
                    symbol=sym,
                    period="daily",
                    start_date=start,
                    end_date=end or "20500101",
                    adjust=adj,
                )
                last_err = None
                break
            except Exception as e:
                last_err = str(e)[:200]
                if attempt < retries:
                    time.sleep(0.8 * attempt)
        if last_err:
            return FetchResult(
                ok=False,
                provider_id=self.provider_id,
                domain_id="daily_bar_raw",
                scope_key=str(code).zfill(6)[:6],
                error=last_err,
            )
        if raw is None or raw.empty:
            return FetchResult(
                ok=False,
                provider_id=self.provider_id,
                domain_id="daily_bar_raw",
                scope_key=str(code).zfill(6)[:6],
                error="empty",
            )
        df = normalize_akshare_bars(raw)
        return FetchResult(
            ok=True,
            data=df,
            provider_id=self.provider_id,
            domain_id="daily_bar_raw",
            scope_type="code",
            scope_key=str(code).zfill(6)[:6],
            fields_provided=list(df.columns),
        )
