#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计本地通达信 vipdoc 日线日期覆盖（抽样 + 全市场 min/max）。"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def _codes_from_lday(root: Path, limit_sample: int) -> list[str]:
    codes: list[str] = []
    for market in ("sh", "sz"):
        d = root / "vipdoc" / market / "lday"
        if not d.is_dir():
            continue
        for p in d.glob("*.day"):
            name = p.stem.lower()
            if market == "sh" and name.startswith("sh") and len(name) >= 8:
                codes.append(name[2:8])
            elif market == "sz" and name.startswith("sz") and len(name) >= 8:
                codes.append(name[2:8])
    codes = sorted(set(c for c in codes if c.isdigit() and len(c) == 6))
    if limit_sample > 0 and len(codes) > limit_sample:
        random.seed(42)
        codes = sorted(random.sample(codes, limit_sample))
    return codes


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tdx-dir", default=os.environ.get("INSTOCK_TDX_DIR", ""))
    p.add_argument("--sample", type=int, default=80, help="抽样证券数，0=全部（较慢）")
    p.add_argument("--codes", default="", help="逗号分隔代码，优先于抽样")
    args = p.parse_args()
    tdx = args.tdx_dir or os.path.expanduser("~/tdx-local")
    root = Path(tdx)
    if not (root / "vipdoc").is_dir():
        print(f"FAIL: 无 vipdoc: {root}", file=sys.stderr)
        return 1

    if args.codes.strip():
        codes = [c.strip().zfill(6)[:6] for c in args.codes.split(",") if c.strip()]
    else:
        codes = _codes_from_lday(root, args.sample)

    os.environ["INSTOCK_TDX_DIR"] = str(root)
    from instock.core.data.providers.mootdx_local import Provider

    prov = Provider()
    if not prov.healthcheck():
        print("FAIL: mootdx_local healthcheck", file=sys.stderr)
        return 1

    global_min = None
    global_max = None
    ok_n = 0
    empty_n = 0
    rows_total = 0
    samples: list[tuple[str, str, str, int]] = []

    for code in codes:
        res = prov.fetch_bars(code, "19900101", adjust="raw")
        if not res.ok or res.data is None or res.data.empty:
            empty_n += 1
            continue
        df = res.data
        ok_n += 1
        rows_total += len(df)
        if hasattr(df.index, "min"):
            dmin = str(df.index.min())[:10]
            dmax = str(df.index.max())[:10]
        else:
            dmin = dmax = "?"
        if global_min is None or dmin < global_min:
            global_min = dmin
        if global_max is None or dmax > global_max:
            global_max = dmax
        if code in ("600000", "000001", "300750", "688981") or len(samples) < 8:
            samples.append((code, dmin, dmax, len(df)))

    sh_n = len(list((root / "vipdoc/sh/lday").glob("*.day"))) if (root / "vipdoc/sh/lday").is_dir() else 0
    sz_n = len(list((root / "vipdoc/sz/lday").glob("*.day"))) if (root / "vipdoc/sz/lday").is_dir() else 0

    print(f"TDX_DIR={root}")
    print(f"日线文件: 沪 {sh_n} · 深 {sz_n} · 合计 {sh_n + sz_n}")
    print(f"统计证券: {len(codes)} 只（可读 {ok_n}，空/失败 {empty_n}）")
    if global_min:
        print(f"抽样合并区间: {global_min} ~ {global_max}")
    print(f"抽样总 K 线行数: {rows_total}")
    print("--- 代表证券 ---")
    for code, dmin, dmax, n in samples:
        print(f"  {code}: {dmin} ~ {dmax} ({n} 行)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
