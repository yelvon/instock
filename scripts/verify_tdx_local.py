#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 INSTOCK_TDX_DIR 本地通达信日线可读。"""

from __future__ import annotations

import argparse
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--code", default="600000")
    p.add_argument("--from-date", default="20240101")
    p.add_argument("--tdx-dir", default="")
    args = p.parse_args()
    if args.tdx_dir:
        os.environ["INSTOCK_TDX_DIR"] = args.tdx_dir
    from instock.core.data.profile import tdx_dir
    from instock.core.data.providers.mootdx_local import Provider

    d = tdx_dir()
    if not d:
        print("FAIL: 未设置 INSTOCK_TDX_DIR", file=sys.stderr)
        return 1
    prov = Provider()
    if not prov.healthcheck():
        print(f"FAIL: healthcheck 失败，目录={d}", file=sys.stderr)
        return 1
    res = prov.fetch_bars(args.code, args.from_date, adjust="raw")
    if not res.ok or res.data is None or res.data.empty:
        print(f"FAIL: {res.error}", file=sys.stderr)
        return 1
    print(f"OK: provider=mootdx_local rows={len(res.data)} dir={d}")
    print(res.data.tail(3))
    from instock.core.adjustment.gbbq_reader import diagnose_gbbq, gbbq_factor_version

    gp, msg = diagnose_gbbq(d)
    print(msg)
    if gp:
        print(f"    version={gbbq_factor_version(d)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
