#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 tablestructure 中的中文说明写入 MySQL 表/列 COMMENT。

用法（在 instock 仓库根目录，与 gen_database_schema_doc.py 相同）：

  PYTHONPATH=. python3 scripts/apply_table_comments.py --dry-run
  PYTHONPATH=. python3 scripts/apply_table_comments.py
  PYTHONPATH=. python3 scripts/apply_table_comments.py --table cn_stock_spot,cn_stock_selection

Docker 容器内（已挂载代码时）：

  docker exec InStock bash -c 'cd /data/InStock && PYTHONPATH=. python3 scripts/apply_table_comments.py'
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def _ensure_tablestructure_importable() -> None:
    try:
        import talib  # noqa: F401
    except ImportError:

        class _FakeTalib:
            def __getattr__(self, _name):
                def _stub(*_a, **_k):
                    return None

                return _stub

        sys.modules["talib"] = _FakeTalib()


def main() -> int:
    parser = argparse.ArgumentParser(description="应用 MySQL 表/列 COMMENT")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只统计将更新的注释，不执行 ALTER",
    )
    parser.add_argument(
        "--table",
        default="",
        help="仅处理指定表，逗号分隔；默认处理所有已定义且库中已存在的表",
    )
    args = parser.parse_args()
    _ensure_tablestructure_importable()

    tables = None
    if args.table.strip():
        tables = [t.strip() for t in args.table.split(",") if t.strip()]

    import instock.core.db_schema_comments as dsc

    stats = dsc.apply_table_and_column_comments(dry_run=args.dry_run, tables=tables)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if stats.get("errors"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
