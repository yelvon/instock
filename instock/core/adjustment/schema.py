# -*- coding: utf-8 -*-
"""前复权相关表 DDL（与 migrations/004 一致）。"""

from __future__ import annotations

import pymysql

import instock.lib.database as mdb

# 勿从 instock.core.canonical 导入：包初始化会拉 reader → 本模块，导致循环导入
TABLE_BAR_QFQ = "cn_stock_daily_bar_qfq"

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS `cn_stock_corporate_action` (
      `code` varchar(6) NOT NULL,
      `ex_date` date NOT NULL,
      `event_type` varchar(16) NOT NULL DEFAULT 'xdxr',
      `category` int NOT NULL DEFAULT 1,
      `cash_div` double DEFAULT NULL,
      `stock_div` double DEFAULT NULL,
      `rights_ratio` double DEFAULT NULL,
      `rights_price` double DEFAULT NULL,
      `source` varchar(16) NOT NULL DEFAULT 'tdx_gbbq',
      `factor_version` varchar(64) DEFAULT NULL,
      `ingested_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`code`,`ex_date`,`event_type`,`source`),
      KEY `idx_ex_date` (`ex_date`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `cn_stock_adj_factor` (
      `code` varchar(6) NOT NULL,
      `date` date NOT NULL,
      `adjust_kind` varchar(8) NOT NULL DEFAULT 'qfq',
      `qfq_factor` double NOT NULL,
      `factor_version` varchar(64) DEFAULT NULL,
      `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`code`,`date`,`adjust_kind`),
      KEY `idx_date` (`date`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `cn_stock_qfq_watermark` (
      `code` varchar(16) NOT NULL,
      `last_raw_date` date DEFAULT NULL,
      `last_factor_version` varchar(64) DEFAULT NULL,
      `last_derived_at` datetime DEFAULT NULL,
      `meta_json` json DEFAULT NULL,
      PRIMARY KEY (`code`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """,
    f"""
    CREATE TABLE IF NOT EXISTS `{TABLE_BAR_QFQ}` (
      `date` date NOT NULL,
      `code` varchar(6) NOT NULL,
      `open` double DEFAULT NULL,
      `close` double DEFAULT NULL,
      `high` double DEFAULT NULL,
      `low` double DEFAULT NULL,
      `volume` double DEFAULT NULL,
      `amount` double DEFAULT NULL,
      `amplitude` double DEFAULT NULL,
      `quote_change` double DEFAULT NULL,
      `ups_downs` double DEFAULT NULL,
      `turnover` double DEFAULT NULL,
      `quality_status` varchar(16) NOT NULL DEFAULT 'derived',
      `completeness_score` tinyint unsigned NOT NULL DEFAULT 100,
      `primary_source` varchar(32) DEFAULT 'tdx_qfq_derived',
      `source_mask` json DEFAULT NULL,
      `factor_version` varchar(64) DEFAULT NULL,
      `derived_from_batch_id` varchar(64) DEFAULT NULL,
      `last_batch_id` varchar(64) DEFAULT NULL,
      `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`code`,`date`),
      KEY `idx_date` (`date`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """,
]


def _upgrade_qfq_watermark_code_column(cur) -> None:
    cur.execute(
        """
        SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'cn_stock_qfq_watermark'
          AND COLUMN_NAME = 'code'
        """
    )
    row = cur.fetchone()
    if row and row[0] is not None and int(row[0]) < 16:
        cur.execute(
            """
            ALTER TABLE `cn_stock_qfq_watermark`
            MODIFY COLUMN `code` varchar(16) NOT NULL
            COMMENT '__global__ 表示全局 gbbq 版本，其余为 6 位证券代码'
            """
        )


def ensure_qfq_tables() -> None:
    with pymysql.connect(**mdb.MYSQL_CONN_DBAPI) as conn:
        with conn.cursor() as cur:
            for ddl in _DDL:
                cur.execute(ddl)
            _upgrade_qfq_watermark_code_column(cur)
        conn.commit()
