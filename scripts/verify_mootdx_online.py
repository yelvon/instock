#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 mootdx 在线行情（无 TDX 目录时 fallback）。"""

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
    args = p.parse_args()
    from instock.core.data.providers.mootdx_online import Provider

    prov = Provider()
    if not prov.healthcheck():
        print("FAIL: mootdx_online healthcheck", file=sys.stderr)
        return 1
    res = prov.fetch_bars(args.code, args.from_date, adjust="raw")
    if not res.ok or res.data is None or res.data.empty:
        print(f"FAIL: {res.error}", file=sys.stderr)
        return 1
    print(f"OK: rows={len(res.data)}")
    print(res.data.tail(3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
