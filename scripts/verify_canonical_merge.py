#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证标准表幂等合并（需 MySQL）。用法：PYTHONPATH=. python3 scripts/verify_canonical_merge.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from instock.core.canonical.writer import CanonicalBarWriter, ensure_canonical_tables


def main() -> int:
    ensure_canonical_tables()
    code = "600000"
    dt = pd.Timestamp("2024-01-15").date()
    row = {
        "date": dt,
        "open": 10.0,
        "close": 10.5,
        "high": 10.6,
        "low": 9.9,
        "volume": 1000000.0,
    }
    w1 = CanonicalBarWriter("tushare")
    s1 = w1.write_rows(code, [row])
    w2 = CanonicalBarWriter("akshare")
    s2 = w2.write_rows(code, [row])
    print("insert", s1.to_dict(), "skip", s2.to_dict())
    if s1.inserted >= 1 and s2.skipped >= 1:
        print("OK: 完整行不被低优先级重复覆盖")
        return 0
    print("WARN: 请检查库连接或已有数据", s1.to_dict(), s2.to_dict())
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
