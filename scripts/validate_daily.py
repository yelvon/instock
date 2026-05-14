#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 cn_stock_spot / cn_etf_spot 单日数据质量（规划 data.md §2）。

用法（在项目根目录 instock/ 下，与 gen_database_schema_doc 一致）::

    PYTHONPATH=. python3 scripts/validate_daily.py --date 2024-06-03
    PYTHONPATH=. python3 scripts/validate_daily.py --date 2024-06-03 --json
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
    p = argparse.ArgumentParser(description="校验 spot 主数据质量")
    p.add_argument("--date", required=True, help="交易日 YYYY-MM-DD")
    p.add_argument("--json", action="store_true", help="以 JSON 打印结果")
    args = p.parse_args()
    d = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()

    import instock.core.pipeline.data_quality as dq

    rs = [dq.validate_cn_stock_spot(d), dq.validate_cn_etf_spot(d)]
    if args.json:
        print(json.dumps([x.to_dict() for x in rs], ensure_ascii=False, indent=2))
    else:
        for x in rs:
            print(x.to_dict())
    return 0 if all(x.ok or x.skipped for x in rs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
