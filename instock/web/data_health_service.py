# -*- coding: utf-8 -*-
"""数据健康摘要：供 Web「数据同步」页展示缺口与补救步骤。"""

from __future__ import annotations

import datetime
import os
from typing import Any, Dict, List

import instock.core.tablestructure as tbs
import instock.core.pipeline.gaps as gaps
import instock.core.pipeline.trade_calendar as tcal
import instock.lib.database as mdb


def _norm_date_key(v) -> str:
    if isinstance(v, datetime.datetime):
        return v.date().isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    return str(v)[:10]


def _count_by_date(table: str, date_from: datetime.date, date_to: datetime.date) -> Dict[str, int]:
    if not mdb.checkTableIsExist(table):
        return {}
    sql = (
        f"SELECT `date`, COUNT(*) AS c FROM `{table}` "
        f"WHERE `date` >= %s AND `date` <= %s GROUP BY `date`"
    )
    rows = mdb.executeSqlFetch(sql, (date_from.isoformat(), date_to.isoformat()))
    if not rows:
        return {}
    return {_norm_date_key(r[0]): int(r[1]) for r in rows}


def build_report(date_from: datetime.date, date_to: datetime.date) -> Dict[str, Any]:
    missing, extra = gaps.detect_stock_spot_gaps(date_from, date_to)
    cal_rows = tcal.table_row_count()
    expected = gaps.expected_trade_dates_in_range(date_from, date_to)

    stock_t = tbs.TABLE_CN_STOCK_SPOT["name"]
    etf_t = tbs.TABLE_CN_ETF_SPOT["name"]
    stock_c = _count_by_date(stock_t, date_from, date_to)
    etf_c = _count_by_date(etf_t, date_from, date_to)

    missing_set = set(missing)
    daily: List[Dict[str, Any]] = []
    for d in expected:
        ds = d.isoformat()
        sr = stock_c.get(ds, 0)
        er = etf_c.get(ds, 0)
        daily.append(
            {
                "date": ds,
                "stock_rows": sr,
                "etf_rows": er,
                "missing_spot": d in missing_set,
                "low_stock": sr > 0 and sr < int(os.environ.get("QUALITY_STOCK_MIN_ROWS", "3500")),
            }
        )

    remediation: List[Dict[str, Any]] = []
    if cal_rows == 0:
        remediation.append(
            {
                "id": "no_calendar",
                "title": "本地交易日历表为空",
                "hint": "断档对比可能回退到实时拉取新浪日历，建议先落库。",
                "actions": [
                    "在下方作业选择「同步交易日历」后执行；或执行「整体日作业」（默认会同步日历）。",
                ],
            }
        )
    if missing:
        remediation.append(
            {
                "id": "spot_gap",
                "title": "股票主快照缺交易日",
                "dates": [d.isoformat() for d in missing],
                "actions": [
                    "选择作业「股票/ETF 快照」。",
                    "日期参数选「枚举」，填入上方缺失日期（可分批，逗号分隔）。",
                    "若接口失败，先检查东方财富 Cookie 与网络，再重试。",
                ],
            }
        )
    if extra:
        remediation.append(
            {
                "id": "extra_dates",
                "title": "库中存在非交易日历内的日期（可忽略或人工核对）",
                "dates": [d.isoformat() for d in extra],
                "actions": ["若 trade_calendar 已更新仍出现，多为历史脏数据或日历源差异。"],
            }
        )

    low_days = [x["date"] for x in daily if x.get("low_stock")]
    if low_days:
        remediation.append(
            {
                "id": "low_rows",
                "title": "部分交易日股票行数低于 QUALITY_STOCK_MIN_ROWS",
                "dates": low_days,
                "actions": [
                    "可能为半日数据或抓取不完整，可对对应日期重跑「股票/ETF 快照」默认或枚举模式。",
                    "命令行可执行：PYTHONPATH=. python3 scripts/validate_daily.py --date 某日",
                ],
            }
        )

    return {
        "ok": True,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "trade_calendar_rows": cal_rows,
        "expected_trade_days": len(expected),
        "missing_spot_trade_dates": [d.isoformat() for d in missing],
        "extra_spot_dates": [d.isoformat() for d in extra],
        "daily": daily,
        "remediation": remediation,
        "cli_hints": {
            "validate": "PYTHONPATH=. python3 scripts/validate_daily.py --date YYYY-MM-DD",
            "gaps": "PYTHONPATH=. python3 scripts/detect_gaps.py --from-date YYYY-MM-DD --to-date YYYY-MM-DD",
        },
    }


def parse_iso_date(s: str) -> datetime.date:
    return datetime.datetime.strptime(s.strip(), "%Y-%m-%d").date()
