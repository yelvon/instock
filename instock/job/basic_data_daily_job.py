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


def _date_str(date) -> str:
    if hasattr(date, "strftime"):
        return date.strftime("%Y-%m-%d")
    return str(date)


def _assert_spot_results(trade_date, results) -> None:
    import instock.core.pipeline.data_quality as dq

    ds = _date_str(trade_date)
    for r in results:
        if r.skipped:
            raise RuntimeError(f"[FAIL] {ds} {r.table}: {r.message}")
        if not r.ok:
            raise RuntimeError(f"[FAIL] {ds} {r.table} 质量未通过: {r.errors}")
    if dq.any_hard_fail(results):
        raise RuntimeError(f"[FAIL] {ds} 数据质量硬规则未通过")


def _write_stock_spot(date) -> int:
    data = stf.fetch_stocks(date)
    if data is None or len(data.index) == 0:
        raise RuntimeError(f"[FAIL] {_date_str(date)} 股票快照抓取为空（请检查网络/Cookie/数据源）")

    table_name = tbs.TABLE_CN_STOCK_SPOT['name']
    if mdb.checkTableIsExist(table_name):
        del_sql = f"DELETE FROM `{table_name}` where `date` = '{_date_str(date)}'"
        mdb.executeSql(del_sql)
        cols_type = None
    else:
        cols_type = tbs.get_field_types(tbs.TABLE_CN_STOCK_SPOT['columns'])

    mdb.insert_db_from_df(data, table_name, cols_type, False, "`date`,`code`")
    n = len(data.index)
    print(f"[PROGRESS] {_date_str(date)} stock rows={n}", flush=True)
    return n


def _write_etf_spot(date) -> int:
    data = get_default_market_data_source().fetch_daily_etfs(date)
    if data is None or len(data.index) == 0:
        raise RuntimeError(f"[FAIL] {_date_str(date)} ETF 快照抓取为空")

    table_name = tbs.TABLE_CN_ETF_SPOT['name']
    if mdb.checkTableIsExist(table_name):
        del_sql = f"DELETE FROM `{table_name}` where `date` = '{_date_str(date)}'"
        mdb.executeSql(del_sql)
        cols_type = None
    else:
        cols_type = tbs.get_field_types(tbs.TABLE_CN_ETF_SPOT['columns'])

    mdb.insert_db_from_df(data, table_name, cols_type, False, "`date`,`code`")
    n = len(data.index)
    print(f"[PROGRESS] {_date_str(date)} etf rows={n}", flush=True)
    return n


def process_one_trade_date(date, before=True):
    """单日：股票快照 + ETF + 质量校验（Web 枚举/区间补数走此入口）。"""
    if before:
        return
    ds = _date_str(date)
    print(f"[PROGRESS] {ds} start", flush=True)
    try:
        import instock.core.pipeline.data_quality as dq

        _write_stock_spot(date)
        _write_etf_spot(date)
        results = dq.validate_spot_after_daily_jobs(date)
        _assert_spot_results(date, results)
        print(f"[PROGRESS] {ds} done", flush=True)
    except Exception as e:
        logging.error(f"basic_data_daily_job.process_one_trade_date处理异常：{ds} {e}")
        raise


# 兼容旧 run_template 双函数调用（已弃用，保留空壳避免 import 失败）
def save_nph_stock_spot_data(date, before=True):
    if before:
        return
    _write_stock_spot(date)


def save_nph_etf_spot_data(date, before=True):
    if before:
        return
    _write_etf_spot(date)
    import instock.core.pipeline.data_quality as dq

    results = dq.validate_spot_after_daily_jobs(date)
    _assert_spot_results(date, results)


def main():
    _ensure_spot_etf_tables()
    if job_argparse.uses_extended_flags():
        args = job_argparse.parse_job_args()
        if getattr(args, "spot_source", None):
            os.environ["INSTOCK_SPOT_DATA_SOURCE"] = args.spot_source
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
            sys.exit(1)
        if args.force:
            logging.warning("--force 已设置（审计）：将按日期覆盖写入 spot 表")
        failures = []
        for d in dates:
            try:
                process_one_trade_date(d, False)
            except Exception as e:
                failures.append(str(e))
        if failures:
            for msg in failures:
                print(f"[FAIL] {msg}", flush=True)
            sys.exit(1)
        return
    runt.run_with_args(process_one_trade_date)


# main函数入口
if __name__ == '__main__':
    main()
