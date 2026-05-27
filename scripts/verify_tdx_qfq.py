#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验本地派生 qfq：L1 最新日 raw=qfq close；可选 L2 与 mootdx 在线对比。"""

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
    p.add_argument("--to-date", default="")
    p.add_argument("--l2", action="store_true", help="与 mootdx 在线 qfq 对比")
    args = p.parse_args()

    codes = [c.strip() for c in args.code.split(",") if c.strip()]
    from instock.core.canonical.reader import load_canonical_bars

    failed = 0
    for code in codes:
        raw = load_canonical_bars(code, args.from_date, args.to_date or None, "raw")
        qfq = load_canonical_bars(code, args.from_date, args.to_date or None, "qfq")
        if raw.empty:
            print(f"{code}: SKIP raw 无数据")
            continue
        if qfq.empty:
            print(f"{code}: FAIL qfq 无数据，请运行 derive_qfq_from_tdx_job --mode full")
            failed += 1
            continue
        merged = raw.merge(qfq, on="date", suffixes=("_raw", "_qfq"))
        if merged.empty:
            print(f"{code}: FAIL 日期无法对齐")
            failed += 1
            continue
        last = merged.iloc[-1]
        diff = abs(float(last["close_raw"]) - float(last["close_qfq"]))
        print(f"{code}: L1 最新日 close diff={diff:.6f} rows={len(merged)}")
        if diff > 1e-4:
            print(f"  FAIL L1 最新日应相等")
            failed += 1

        if args.l2:
            try:
                from instock.core.data.providers.mootdx_online import Provider

                mo = Provider().fetch_bars(code, args.from_date, args.to_date or None, adjust="qfq")
                if mo.ok and mo.data is not None and not mo.data.empty:
                    online = mo.data.reset_index()
                    if "date" not in online.columns:
                        online = online.reset_index()
                    online["date"] = online["date"].astype(str).str[:10]
                    m2 = merged.merge(
                        online[["date", "close"]].rename(columns={"close": "close_online"}),
                        on="date",
                        how="inner",
                    )
                    if not m2.empty:
                        d = (m2["close_qfq"].astype(float) - m2["close_online"].astype(float)).abs()
                        print(f"  L2 online aligned={len(m2)} max_diff={d.max():.4f} mean={d.mean():.4f}")
            except Exception as e:
                print(f"  L2 skip: {e}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
