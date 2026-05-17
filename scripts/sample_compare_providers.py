#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双源抽样对比（东财 vs mootdx 收盘、东财 vs 腾讯估值），仅报告不阻断。"""

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

    from instock.core.data.providers.eastmoney import Provider as EM
    from instock.core.data.providers.mootdx_local import Provider as ML
    from instock.core.data.providers.mootdx_online import Provider as MO
    from instock.core.data.profile import tdx_dir

    em = EM().fetch_bars(args.code, args.from_date, adjust="raw")
    if tdx_dir():
        md = ML().fetch_bars(args.code, args.from_date, adjust="raw")
        src = "mootdx_local"
    else:
        md = MO().fetch_bars(args.code, args.from_date, adjust="raw")
        src = "mootdx_online"
    if not em.ok or not md.ok:
        print("SKIP: 一侧无数据", em.error, md.error)
        return 1
    a = em.data["close"].astype(float)
    b = md.data["close"].astype(float)
    joined = a.align(b, join="inner")
    diff = (joined[0] - joined[1]).abs()
    print(f"bar_close: eastmoney vs {src} aligned={len(diff)} max_abs_diff={diff.max():.4f} mean={diff.mean():.4f}")

    from instock.core.data.providers.tencent import tencent_quote

    tq = tencent_quote([args.code])
    if tq:
        print(f"tencent live pb={tq.get(args.code, {}).get('pb')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
