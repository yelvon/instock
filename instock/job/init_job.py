#!/usr/local/bin/python3
# -*- coding: utf-8 -*-


import logging
import pymysql
import os.path
import sys

cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)
import instock.lib.database as mdb

__author__ = 'myh '
__date__ = '2023/3/10 '


# 创建新数据库。
def create_new_database():
    _MYSQL_CONN_DBAPI = mdb.MYSQL_CONN_DBAPI.copy()
    _MYSQL_CONN_DBAPI['database'] = "mysql"
    with pymysql.connect(**_MYSQL_CONN_DBAPI) as conn:
        with conn.cursor() as db:
            try:
                create_sql = f"CREATE DATABASE IF NOT EXISTS `{mdb.db_database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
                db.execute(create_sql)
                create_new_base_table()
            except Exception as e:
                logging.error(f"init_job.create_new_database处理异常：{e}")


# 创建基础表。
def create_new_base_table():
    with pymysql.connect(**mdb.MYSQL_CONN_DBAPI) as conn:
        with conn.cursor() as db:
            create_table_sql = """CREATE TABLE IF NOT EXISTS `cn_stock_attention` (
                                  `datetime` datetime(0) NULL DEFAULT NULL, 
                                  `code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
                                  PRIMARY KEY (`code`) USING BTREE,
                                  INDEX `INIX_DATETIME`(`datetime`) USING BTREE
                                  ) CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;"""
            db.execute(create_table_sql)


def check_database():
    with pymysql.connect(**mdb.MYSQL_CONN_DBAPI) as conn:
        with conn.cursor() as db:
            db.execute(" select 1 ")


def main():
    # 检查，如果执行 select 1 失败，说明数据库不存在，然后创建一个新的数据库。
    try:
        check_database()
    except Exception as e:
        logging.error("执行信息：数据库不存在，将创建。")
        # 检查数据库失败，
        create_new_database()
    # 数据管线：交易日历表（无网络，仅建表）
    try:
        import instock.core.pipeline.trade_calendar as _tc

        _tc.ensure_table()
    except Exception as e:
        logging.error(f"init_job: trade_calendar 建表异常：{e}")
    # 将 tablestructure 中文说明写入已存在表的 MySQL COMMENT（仅改注释，不改列类型）
    if os.environ.get("INSTOCK_APPLY_DB_COMMENTS", "1") != "0":
        try:
            from instock.core import db_schema_comments as _dsc

            st = _dsc.apply_table_and_column_comments()
            logging.info(
                "init_job: 表/列 COMMENT 同步完成 tables=%s cols=%s missing=%s",
                st.get("table_comments"),
                st.get("column_comments"),
                st.get("tables_skipped_missing"),
            )
        except Exception as e:
            logging.error(
                "init_job: COMMENT 同步失败（可手动执行 scripts/apply_table_comments.py）：%s",
                e,
            )
    try:
        from instock.core.data.lineage import ensure_data_batch_table

        ensure_data_batch_table()
    except Exception as e:
        logging.error(f"init_job: data_batch 建表异常：{e}")
    try:
        from instock.core.mootdx_universe import ensure_cn_stock_universe_table

        ensure_cn_stock_universe_table()
    except Exception as e:
        logging.error(f"init_job: cn_stock_universe 建表异常：{e}")
    try:
        from instock.core.canonical.writer import ensure_canonical_tables

        ensure_canonical_tables()
    except Exception as e:
        logging.error(f"init_job: canonical daily bar 建表异常：{e}")
    # 执行数据初始化。


# main函数入口
if __name__ == '__main__':
    main()
