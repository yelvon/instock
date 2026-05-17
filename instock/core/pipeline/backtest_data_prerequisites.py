# -*- coding: utf-8 -*-
"""回测主数据前置检查（不含选股域）。"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import instock.core.pipeline.gaps as gaps
import instock.core.tablestructure as tbs

DEFAULT_DOMAINS = ("trade_calendar", "daily_spot_snapshot", "derived_indicators")


@dataclass
class DomainGapReport:
    domain_id: str
    missing_trade_dates: List[datetime.date] = field(default_factory=list)
    extra_dates: List[datetime.date] = field(default_factory=list)
    table: str = ""
    suggested_jobs: List[str] = field(default_factory=list)


@dataclass
class PrerequisitesReport:
    date_from: datetime.date
    date_to: datetime.date
    domains: Dict[str, DomainGapReport] = field(default_factory=dict)
    ok: bool = True
    messages: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "date_from": self.date_from.isoformat(),
            "date_to": self.date_to.isoformat(),
            "messages": self.messages,
            "domains": {
                k: {
                    "missing_trade_dates": [d.isoformat() for d in v.missing_trade_dates],
                    "extra_dates": [d.isoformat() for d in v.extra_dates],
                    "table": v.table,
                    "suggested_jobs": v.suggested_jobs,
                }
                for k, v in self.domains.items()
            },
        }


_DERIVED_TABLES = (
    tbs.TABLE_CN_STOCK_INDICATORS["name"],
)


def check_backtest_data(
    date_from: datetime.date,
    date_to: datetime.date,
    required_domains: Optional[List[str]] = None,
) -> PrerequisitesReport:
    domains = list(required_domains or DEFAULT_DOMAINS)
    report = PrerequisitesReport(date_from=date_from, date_to=date_to)

    if "trade_calendar" in domains:
        miss_cal, extra_cal = gaps.detect_trade_calendar_gaps(date_from, date_to)
        dr = DomainGapReport(
            domain_id="trade_calendar",
            missing_trade_dates=miss_cal,
            extra_dates=extra_cal,
            table="trade_calendar",
            suggested_jobs=["sync_trade_calendar_job", "execute_daily_job"],
        )
        report.domains["trade_calendar"] = dr
        if miss_cal:
            report.ok = False
            report.messages.append(f"交易日历缺 {len(miss_cal)} 天")

    if "daily_spot_snapshot" in domains:
        miss, extra = gaps.detect_stock_spot_gaps(date_from, date_to)
        dr = DomainGapReport(
            domain_id="daily_spot_snapshot",
            missing_trade_dates=miss,
            extra_dates=extra,
            table=tbs.TABLE_CN_STOCK_SPOT["name"],
            suggested_jobs=["basic_data_daily_job"],
        )
        report.domains["daily_spot_snapshot"] = dr
        if miss:
            report.ok = False
            report.messages.append(f"cn_stock_spot 缺 {len(miss)} 个交易日")

    if "derived_indicators" in domains:
        all_miss: List[datetime.date] = []
        for tn in _DERIVED_TABLES:
            miss, extra = gaps.detect_table_date_gaps(tn, date_from, date_to)
            if miss:
                all_miss = sorted(set(all_miss) | set(miss))
            report.domains[f"derived:{tn}"] = DomainGapReport(
                domain_id="derived_indicators",
                missing_trade_dates=miss,
                extra_dates=extra,
                table=tn,
                suggested_jobs=["indicators_data_daily_job", "strategy_data_daily_job"],
            )
        if all_miss:
            report.ok = False
            report.messages.append("衍生指标表存在缺日")

    return report


def detect_all_backtest_domain_gaps(
    date_from: datetime.date, date_to: datetime.date
) -> PrerequisitesReport:
    return check_backtest_data(date_from, date_to, list(DEFAULT_DOMAINS))
