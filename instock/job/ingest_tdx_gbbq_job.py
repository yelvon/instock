#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描通达信 gbbq → cn_stock_corporate_action。"""

from __future__ import annotations

import os
import sys

cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)


def main() -> int:
    from instock.core.adjustment.corporate_action_store import ingest_gbbq_to_db
    from instock.core.adjustment.gbbq_reader import diagnose_gbbq

    path, diag = diagnose_gbbq()
    print(diag, flush=True)
    if not path:
        print("[FAIL] 未找到 gbbq", flush=True)
        return 1
    r = ingest_gbbq_to_db()
    print(r, flush=True)
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
