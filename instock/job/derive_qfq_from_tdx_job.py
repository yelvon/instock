#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
由 raw 标准表 + gbbq 派生前复权 → cn_stock_daily_bar_qfq。

示例：
  python derive_qfq_from_tdx_job.py --mode full
  python derive_qfq_from_tdx_job.py --mode incremental --limit 50
  python derive_qfq_from_tdx_job.py --code 600000 --mode full
"""

from __future__ import annotations

import argparse
import os
import sys

cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)


def _emit(msg: str) -> None:
    print(msg, flush=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("incremental", "full"), default="incremental")
    p.add_argument("--code", default="", help="逗号分隔代码")
    p.add_argument("--from-date", default="", dest="date_from")
    p.add_argument("--to-date", default="", dest="date_to")
    p.add_argument("--force", action="store_true", help="等同 full")
    p.add_argument("--skip-ingest-gbbq", action="store_true")
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    mode = "full" if args.force else args.mode
    codes = [c.strip() for c in args.code.split(",") if c.strip()] or None

    from instock.core.adjustment.derive import run_derive

    r = run_derive(
        mode=mode,
        codes=codes,
        date_from=args.date_from or ("19900101" if mode == "full" else ""),
        date_to=args.date_to or None,
        skip_ingest=args.skip_ingest_gbbq,
        limit=args.limit,
        log=_emit,
    )
    _emit(str(r))
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
