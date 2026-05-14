# -*- coding: utf-8 -*-
"""Job 脚本扩展参数：与 run_template 位置参数兼容，支持 --date / --from-date / --to-date / --dry-run。"""

from __future__ import annotations

import argparse
import datetime
import sys
from typing import List, Optional


def uses_extended_flags(argv: Optional[List[str]] = None) -> bool:
    if argv is None:
        argv = sys.argv
    return len(argv) >= 2 and argv[1].startswith("-")


def parse_job_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="InStock job 扩展参数")
    p.add_argument("--date", help="单日 YYYY-MM-DD")
    p.add_argument("--from-date", dest="from_date", help="区间起始 YYYY-MM-DD")
    p.add_argument("--to-date", dest="to_date", help="区间结束 YYYY-MM-DD")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将执行的日期，不写库（由具体 job 解释）",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖等（由具体 job 解释）",
    )
    return p.parse_args(argv[1:] if argv is not None else sys.argv[1:])


def iter_trade_dates_inclusive(
    date_from: datetime.date, date_to: datetime.date
) -> List[datetime.date]:
    import instock.lib.trade_time as trd

    out: List[datetime.date] = []
    d = date_from
    while d <= date_to:
        if trd.is_trade_date(d):
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def parse_iso_date(s: str) -> datetime.date:
    return datetime.datetime.strptime(s.strip(), "%Y-%m-%d").date()
