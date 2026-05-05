#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 instock.core.tablestructure 生成 docs/database-schema.md。

新增或修改业务表时：
1. 更新 instock/core/tablestructure.py
2. 在项目根目录执行：PYTHONPATH=. python3 scripts/gen_database_schema_doc.py
"""

from __future__ import annotations

import os
import re
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def _ensure_tablestructure_importable() -> None:
    """tablestructure 依赖 talib；环境未安装时用占位模块以便仍能生成文档。"""
    try:
        import talib  # noqa: F401
    except ImportError:

        class _FakeTalib:
            def __getattr__(self, name):
                def _stub(*_a, **_k):
                    return None

                return _stub

        sys.modules["talib"] = _FakeTalib()


def _fmt_sqlalchemy_type(t) -> str:
    s = str(t)
    s = re.sub(r"<class '([^']+)'>", r"\1", s)
    s = s.replace("sqlalchemy.sql.sqltypes.", "")
    s = s.replace("sqlalchemy.dialects.mysql.", "mysql.")
    s = s.replace("sqlalchemy.sql.sqltypes.", "")
    return s


def _collect_tables():
    _ensure_tablestructure_importable()
    import instock.core.tablestructure as tbs

    out: list[tuple[str, str, str, dict]] = []

    def add(source_var: str, table_en: str, table_cn: str, cols: dict):
        out.append((source_var, table_en, table_cn, cols))

    for name in sorted(dir(tbs)):
        if name.startswith("_"):
            continue
        # 模块里 for 循环泄漏的临时名（如 cf）会误被当成表定义
        if not name[0].isupper():
            continue
        obj = getattr(tbs, name)
        if not isinstance(obj, dict):
            continue
        if not ("name" in obj and "columns" in obj and "cn" in obj):
            continue
        add(name, obj["name"], obj["cn"], obj["columns"])

    strategies = getattr(tbs, "TABLE_CN_STOCK_STRATEGIES", None)
    if isinstance(strategies, list):
        for i, row in enumerate(strategies):
            if isinstance(row, dict) and "name" in row and "columns" in row:
                add(
                    "TABLE_CN_STOCK_STRATEGIES[%s]" % i,
                    row["name"],
                    row.get("cn", ""),
                    row["columns"],
                )

    seen = set()
    dedup: list[tuple[str, str, str, dict]] = []
    for item in sorted(out, key=lambda x: (x[1], x[0])):
        key = item[1]
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)
    return dedup


def _emit_md(path: str) -> None:
    rows = _collect_tables()
    lines: list[str] = []
    lines.append("# 数据库表结构说明")
    lines.append("")
    lines.append("本文档由代码 **`instock/core/tablestructure.py`** 自动生成，描述 MySQL 业务表的逻辑结构（列名、SQLAlchemy 类型、中文含义）。")
    lines.append("")
    lines.append("## 维护方式")
    lines.append("")
    lines.append("1. **单一真相**：新增或修改列时，改 `tablestructure.py`（及相关 job / Web 配置）。")
    lines.append("2. **更新本文档**：在仓库 `instock` 目录下执行：")
    lines.append("")
    lines.append("```bash")
    lines.append("PYTHONPATH=. python3 scripts/gen_database_schema_doc.py")
    lines.append("```")
    lines.append("")
    lines.append("3. **初始化脚本中的特例**：`instock/job/init_job.py` 仅手写创建了 `cn_stock_attention`；其余表多在首次写入 DataFrame 时由 SQLAlchemy 按此处类型建表。线上库实际 DDL 若与本文不一致，以数据库为准或做一次迁移对齐。")
    lines.append("")
    lines.append("## 非 MySQL 文件（备忘）")
    lines.append("")
    lines.append("| 说明 | 路径 |")
    lines.append("|------|------|")
    lines.append("| Web 同步作业历史（JSON） | `instock/log/sync_job_history.json` |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 表一览")
    lines.append("")
    lines.append("| 表名（英文） | 中文说明 | 定义变量 |")
    lines.append("|--------------|----------|----------|")
    for src, en, cn, _ in rows:
        lines.append("| `%s` | %s | `%s` |" % (en, cn, src))
    lines.append("")
    lines.append("---")
    lines.append("")

    for src, en, cn, cols in rows:
        lines.append("## `%s`" % en)
        lines.append("")
        lines.append("- **中文名**：%s" % cn)
        lines.append("- **代码引用**：`%s`" % src)
        lines.append("")
        lines.append("| 列名 | 类型 | 说明 |")
        lines.append("|------|------|------|")
        for col_name in cols.keys():
            meta = cols[col_name]
            if not isinstance(meta, dict):
                continue
            typ = _fmt_sqlalchemy_type(meta.get("type"))
            label = meta.get("cn", "")
            lines.append("| `%s` | %s | %s |" % (col_name, typ, label))
        lines.append("")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    out = os.path.join(_REPO, "docs", "database-schema.md")
    _emit_md(out)
    print("Wrote", out)


if __name__ == "__main__":
    main()
