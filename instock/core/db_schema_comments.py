#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 tablestructure 元数据为 MySQL 表/列写入 COMMENT（不改动列类型）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "collect_table_definitions",
    "apply_table_and_column_comments",
    "build_comment_for_column",
]

# MySQL 列注释最大长度
_MAX_COMMENT_LEN = 1024


def _escape_comment(text: str) -> str:
    s = (text or "").replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
    return s[:_MAX_COMMENT_LEN]


def build_comment_for_column(table_cn: str, col_name: str, col_cn: str) -> str:
    """生成列 COMMENT：表说明 + 字段中文名 + 英文字段名。"""
    parts = []
    if col_cn:
        parts.append(col_cn.strip())
    if table_cn:
        parts.append(f"所属表:{table_cn.strip()}")
    parts.append(f"字段:{col_name}")
    return _escape_comment(" | ".join(parts))


def collect_table_definitions() -> List[Tuple[str, str, Dict[str, Dict[str, Any]]]]:
    """
    返回 [(table_name, table_cn, {col: {cn, type, ...}}), ...]。
    逻辑与 scripts/gen_database_schema_doc.py 一致。
    """
    import instock.core.tablestructure as tbs

    out: List[Tuple[str, str, Dict[str, Dict[str, Any]]]] = []

    def add(table_en: str, table_cn: str, cols: dict) -> None:
        out.append((table_en, table_cn or table_en, cols))

    for name in sorted(dir(tbs)):
        if not name.startswith("TABLE_"):
            continue
        obj = getattr(tbs, name, None)
        if not isinstance(obj, dict) or "name" not in obj or "columns" not in obj:
            continue
        add(obj["name"], obj.get("cn", ""), obj["columns"])

    strategies = getattr(tbs, "TABLE_CN_STOCK_STRATEGIES", None)
    if isinstance(strategies, list):
        for row in strategies:
            if isinstance(row, dict) and "name" in row and "columns" in row:
                add(row["name"], row.get("cn", ""), row["columns"])

    # 非 tablestructure 手写表
    add("cn_stock_attention", "我的关注", tbs.TABLE_CN_STOCK_ATTENTION["columns"])
    add("trade_calendar", "交易日历", {
        "cal_date": {"cn": "日历日期"},
        "is_open": {"cn": "是否交易日(1是0否)"},
        "synced_at": {"cn": "同步时间"},
    })
    add("data_batch", "回测数据入库批次血缘", {
        "batch_id": {"cn": "批次唯一ID(UUID)"},
        "domain_id": {"cn": "数据域ID"},
        "trade_date": {"cn": "业务交易日"},
        "date_from": {"cn": "K线区间起始日"},
        "date_to": {"cn": "K线区间结束日"},
        "scope_type": {"cn": "范围类型(market/code/table)"},
        "scope_key": {"cn": "范围标识"},
        "row_count": {"cn": "本批次写入行数"},
        "source_provider": {"cn": "主链数据源provider_id"},
        "enrich_providers": {"cn": "enrich源列表JSON"},
        "mixed_source": {"cn": "是否混源(0否1是)"},
        "adjust_type": {"cn": "复权口径raw/qfq/hfq"},
        "profile": {"cn": "数据配置档live/backtest"},
        "input_batches": {"cn": "上游依赖batch_id列表"},
        "status": {"cn": "批次状态success/failed/partial"},
        "job_id": {"cn": "触发写入的作业ID"},
        "created_at": {"cn": "记录创建时间"},
    })

    seen = set()
    dedup: List[Tuple[str, str, Dict[str, Dict[str, Any]]]] = []
    for item in sorted(out, key=lambda x: x[0]):
        if item[0] in seen:
            continue
        seen.add(item[0])
        dedup.append(item)
    return dedup


def _mdb():
    import instock.lib.database as mdb

    return mdb


def _table_exists(table: str) -> bool:
    return _mdb().checkTableIsExist(table)


def _fetch_column_meta(table: str) -> Dict[str, Dict[str, str]]:
    """返回 col_name -> {column_type, is_nullable, column_comment}。"""
    sql = """
    SELECT `COLUMN_NAME`, `COLUMN_TYPE`, `IS_NULLABLE`, `COLUMN_COMMENT`
    FROM `information_schema`.`COLUMNS`
    WHERE `TABLE_SCHEMA` = DATABASE() AND `TABLE_NAME` = %s
    ORDER BY `ORDINAL_POSITION`
    """
    rows = _mdb().executeSqlFetch(sql, (table,))
    meta: Dict[str, Dict[str, str]] = {}
    if not rows:
        return meta
    for r in rows:
        meta[str(r[0])] = {
            "column_type": str(r[1]),
            "is_nullable": str(r[2]),
            "column_comment": str(r[3] or ""),
        }
    return meta


def _modify_column_sql(table: str, col: str, column_type: str, nullable: str, comment: str) -> str:
    null_sql = "NULL" if nullable == "YES" else "NOT NULL"
    c = _escape_comment(comment)
    return (
        f"ALTER TABLE `{table}` MODIFY COLUMN `{col}` {column_type} {null_sql} "
        f"COMMENT '{c}'"
    )


def apply_table_and_column_comments(
    dry_run: bool = False,
    tables: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    为已存在的表写入表级 COMMENT 与列 COMMENT（仅修改注释，列类型以库中现有为准）。

    :param dry_run: 为 True 时只统计将执行的语句，不写入库
    :param tables: 仅处理这些表名；None 表示全部已知表
    """
    defs = collect_table_definitions()
    if tables:
        allow = set(tables)
        defs = [d for d in defs if d[0] in allow]

    stats = {
        "tables_total": len(defs),
        "tables_skipped_missing": 0,
        "table_comments": 0,
        "column_comments": 0,
        "column_skipped": 0,
        "errors": [],
        "statements": [],
    }

    for table_name, table_cn, cols in defs:
        if not _table_exists(table_name):
            stats["tables_skipped_missing"] += 1
            continue

        table_comment = _escape_comment(f"InStock · {table_cn}（{table_name}）")
        sql_table = f"ALTER TABLE `{table_name}` COMMENT = '{table_comment}'"
        stats["statements"].append(sql_table)
        if not dry_run:
            try:
                _mdb().executeSql(sql_table)
                stats["table_comments"] += 1
            except Exception as e:
                stats["errors"].append(f"{table_name} TABLE COMMENT: {e}")
                logging.error("db_schema_comments table %s: %s", table_name, e)
        else:
            stats["table_comments"] += 1

        db_cols = _fetch_column_meta(table_name)
        for col_name, col_def in cols.items():
            if col_name not in db_cols:
                stats["column_skipped"] += 1
                continue
            dbm = db_cols[col_name]
            new_comment = build_comment_for_column(
                table_cn,
                col_name,
                (col_def.get("cn") if isinstance(col_def, dict) else "") or "",
            )
            if dbm["column_comment"] == new_comment:
                continue
            sql_col = _modify_column_sql(
                table_name,
                col_name,
                dbm["column_type"],
                dbm["is_nullable"],
                new_comment,
            )
            stats["statements"].append(sql_col)
            if not dry_run:
                try:
                    _mdb().executeSql(sql_col)
                    stats["column_comments"] += 1
                except Exception as e:
                    stats["errors"].append(f"{table_name}.{col_name}: {e}")
                    logging.error("db_schema_comments %s.%s: %s", table_name, col_name, e)
            else:
                stats["column_comments"] += 1

    return stats
