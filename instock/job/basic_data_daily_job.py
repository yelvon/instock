#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import logging
import os
import os.path
import sys

import pandas as pd

cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)
import instock.lib.run_template as runt
import instock.lib.job_argparse as job_argparse
import instock.core.tablestructure as tbs
import instock.lib.database as mdb
import instock.core.stockfetch as stf
from instock.core.pipeline.data_source import get_default_market_data_source

__author__ = 'myh '
__date__ = '2023/3/10 '


def _ensure_table_from_tdef(tdef, primary_keys):
    """表不存在时按元数据建空表，避免当日无行情、未执行过 insert 时 Web 查表 1146。"""
    name = tdef['name']
    if mdb.checkTableIsExist(name):
        return
    cols = tdef['columns']
    empty = pd.DataFrame({k: [] for k in cols.keys()})
    ct = tbs.get_field_types(cols)
    mdb.insert_db_from_df(empty, name, ct, False, primary_keys)


def _ensure_spot_etf_tables():
    for tdef in (tbs.TABLE_CN_STOCK_SPOT, tbs.TABLE_CN_ETF_SPOT):
        try:
            _ensure_table_from_tdef(tdef, "`date`,`code`")
        except Exception as e:
            logging.error(f"basic_data_daily_job._ensure_spot_etf_tables：{tdef['name']} {e}")


def _run_spot_quality_after_etf(date):
    """无额外 argv 的同步单机跑批：在 ETF 写入后校验当日 spot（与 run_template 多进程模式不混用）。"""
    if len(sys.argv) != 1:
        return
    import instock.core.pipeline.data_quality as dq

    results = dq.validate_spot_after_daily_jobs(date)
    if dq.any_hard_fail(results) and os.environ.get("INSTOCK_QUALITY_STRICT") == "1":
        raise RuntimeError(f"INSTOCK_QUALITY_STRICT: 数据质量未通过 {date}")


# 股票实时行情数据。
def save_nph_stock_spot_data(date, before=True):
    if before:
        return
    # 股票列表
    try:
        # 勿用 singleton stock_data(date)：多日期枚举/线程池下只会缓存首个 date，导致补数异常。
        data = stf.fetch_stocks(date)
        if data is None or len(data.index) == 0:
            return

        table_name = tbs.TABLE_CN_STOCK_SPOT['name']
        # 删除老数据。
        if mdb.checkTableIsExist(table_name):
            del_sql = f"DELETE FROM `{table_name}` where `date` = '{date}'"
            mdb.executeSql(del_sql)
            cols_type = None
        else:
            cols_type = tbs.get_field_types(tbs.TABLE_CN_STOCK_SPOT['columns'])

        mdb.insert_db_from_df(data, table_name, cols_type, False, "`date`,`code`")

    except Exception as e:
        logging.error(f"basic_data_daily_job.save_stock_spot_data处理异常：{e}")


# 基金实时行情数据。
def save_nph_etf_spot_data(date, before=True):
    if before:
        return
    # 股票列表
    try:
        data = get_default_market_data_source().fetch_daily_etfs(date)
        if data is None or len(data.index) == 0:
            return

        table_name = tbs.TABLE_CN_ETF_SPOT['name']
        # 删除老数据。
        if mdb.checkTableIsExist(table_name):
            del_sql = f"DELETE FROM `{table_name}` where `date` = '{date}'"
            mdb.executeSql(del_sql)
            cols_type = None
        else:
            cols_type = tbs.get_field_types(tbs.TABLE_CN_ETF_SPOT['columns'])

        mdb.insert_db_from_df(data, table_name, cols_type, False, "`date`,`code`")
        _run_spot_quality_after_etf(date)
    except Exception as e:
        logging.error(f"basic_data_daily_job.save_nph_etf_spot_data处理异常：{e}")



def main():
    _ensure_spot_etf_tables()
    if job_argparse.uses_extended_flags():
        args = job_argparse.parse_job_args()
        if args.dry_run:
            if args.date:
                logging.info("dry-run: 将处理 %s", args.date)
            elif args.from_date and args.to_date:
                ds = job_argparse.iter_trade_dates_inclusive(
                    job_argparse.parse_iso_date(args.from_date),
                    job_argparse.parse_iso_date(args.to_date),
                )
                logging.info("dry-run: 将处理 %s 个交易日", len(ds))
            return
        if args.date:
            dates = [job_argparse.parse_iso_date(args.date)]
        elif args.from_date and args.to_date:
            dates = job_argparse.iter_trade_dates_inclusive(
                job_argparse.parse_iso_date(args.from_date),
                job_argparse.parse_iso_date(args.to_date),
            )
        else:
            logging.error("扩展参数需指定 --date YYYY-MM-DD 或 --from-date 与 --to-date")
            return
        if args.force:
            logging.warning("--force 已设置（审计）：将按日期覆盖写入 spot 表")
        import instock.core.pipeline.data_quality as dq

        for d in dates:
            save_nph_stock_spot_data(d, False)
            save_nph_etf_spot_data(d, False)
            results = dq.validate_spot_after_daily_jobs(d)
            if dq.any_hard_fail(results) and os.environ.get("INSTOCK_QUALITY_STRICT") == "1":
                raise RuntimeError(f"INSTOCK_QUALITY_STRICT: 数据质量未通过 {d}")
        return
    runt.run_with_args(save_nph_stock_spot_data)
    runt.run_with_args(save_nph_etf_spot_data)


# main函数入口
if __name__ == '__main__':
    main()
