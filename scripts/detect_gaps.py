#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检测 cn_stock_spot 相对交易日的断档（规划 data.md §3）。

依赖 trade_calendar（可先跑 execute_daily_job 或 sync_trade_calendar_job）。

用法::

    PYTHONPATH=. python3 scripts/detect_gaps.py --from-date 2024-01-01 --to-date 2024-06-30
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def main() -> int:
    p = argparse.ArgumentParser(description="检测股票 spot 断档")
    p.add_argument("--from-date", required=True)
    p.add_argument("--to-date", required=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    d0 = datetime.datetime.strptime(args.from_date, "%Y-%m-%d").date()
    d1 = datetime.datetime.strptime(args.to_date, "%Y-%m-%d").date()

    import instock.core.pipeline.gaps as gaps

    missing, extra = gaps.detect_stock_spot_gaps(d0, d1)
    out = {
        "missing_trade_dates": [x.isoformat() for x in missing],
        "extra_dates_not_in_calendar": [x.isoformat() for x in extra],
        "missing_count": len(missing),
    }
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(out)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
