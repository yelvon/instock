#!/usr/bin/env python3
"""直接解析 .day 二进制，统计日期范围（不依赖 mootdx）。"""
from __future__ import annotations
import random
import struct
import sys
from datetime import date
from pathlib import Path

def first_last(path: Path):
    data = path.read_bytes()
    rec = 32
    n = len(data) // rec
    if n < 1:
        return None, None, 0
    def d_at(i):
        y, m, d = struct.unpack_from("<HHH", data, i * rec)
        return date(y, m, d)
    return d_at(0), d_at(n - 1), n

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "/tdx")
    sh = root / "vipdoc/sh/lday"
    sz = root / "vipdoc/sz/lday"
    files = list(sh.glob("*.day")) + list(sz.glob("*.day"))
    print(f"files={len(files)} sh={len(list(sh.glob('*.day')))} sz={len(list(sz.glob('*.day')))}")
    for name in ["sh600000.day", "sh600519.day", "sz000001.day", "sz300750.day", "sh688981.day"]:
        for base in (sh, sz):
            p = base / name
            if p.exists():
                a, b, n = first_last(p)
                print(f"  {name}: {a} ~ {b} ({n})")
    random.seed(1)
    pick = random.sample(files, min(800, len(files)))
    gmin = gmax = None
    for p in pick:
        a, b, _ = first_last(p)
        if a is None:
            continue
        gmin = a if gmin is None or a < gmin else gmin
        gmax = b if gmax is None or b > gmax else gmax
    print(f"random_{len(pick)}: {gmin} ~ {gmax}")

if __name__ == "__main__":
    main()
