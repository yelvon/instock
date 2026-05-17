#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证腾讯 qt.gtimg.cn 估值字段（实时，非历史日）。"""

from __future__ import annotations

import argparse
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--codes", default="600000,000001")
    args = p.parse_args()
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    from instock.core.data.providers.tencent import tencent_quote

    data = tencent_quote(codes)
    if not data:
        print("FAIL: 无返回", file=sys.stderr)
        return 1
    for c, row in data.items():
        print(f"{c}: pe_ttm={row.get('pe_ttm')} pb={row.get('pb')} mcap_yi={row.get('mcap_yi')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
