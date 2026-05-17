#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回测主数据前置检查（不含选股域）。

用法::

    PYTHONPATH=. python3 scripts/check_backtest_data.py --from-date 2024-01-01 --to-date 2024-06-30
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def main() -> int:
    p = argparse.ArgumentParser(description="回测主数据缺口检查")
    p.add_argument("--from-date", required=True)
    p.add_argument("--to-date", required=True)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    import datetime

    d0 = datetime.datetime.strptime(args.from_date, "%Y-%m-%d").date()
    d1 = datetime.datetime.strptime(args.to_date, "%Y-%m-%d").date()

    from instock.core.pipeline.backtest_data_prerequisites import check_backtest_data

    report = check_backtest_data(d0, d1)
    payload = report.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not report.ok:
        print("\n建议补跑 job：", file=sys.stderr)
        for dom in report.domains.values():
            for j in dom.suggested_jobs:
                print(f"  - {j}", file=sys.stderr)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
