#!/usr/local/bin/python
# -*- coding: utf-8 -*-


import logging
import datetime
import concurrent.futures
import sys
import time
import instock.lib.trade_time as trd


def _should_run_on_trade_date(run_date: datetime.date) -> bool:
    """与断档检测一致：本地 `trade_calendar` 有数据时优先用表；否则用新浪交易日集合。"""
    try:
        import instock.core.pipeline.trade_calendar as tcal

        if tcal.table_row_count() > 0:
            v = tcal.lookup_is_open(run_date)
            if v is not None:
                return bool(v)
    except Exception as e:
        logging.warning("run_template._should_run_on_trade_date: %s", e)
    return trd.is_trade_date(run_date)

__author__ = 'myh '
__date__ = '2023/3/10 '


# 通用函数，获得日期参数，支持批量作业。
def run_with_args(run_fun, *args):
    if len(sys.argv) == 3:
        # 区间作业 python xxx.py 2023-03-01 2023-03-21
        tmp_year, tmp_month, tmp_day = sys.argv[1].split("-")
        start_date = datetime.datetime(int(tmp_year), int(tmp_month), int(tmp_day)).date()
        tmp_year, tmp_month, tmp_day = sys.argv[2].split("-")
        end_date = datetime.datetime(int(tmp_year), int(tmp_month), int(tmp_day)).date()
        run_date = start_date
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                while run_date <= end_date:
                    if _should_run_on_trade_date(run_date):
                        executor.submit(run_fun, run_date, *args)
                        time.sleep(2.5)
                    run_date += datetime.timedelta(days=1)
        except Exception as e:
            logging.error(f"run_template.run_with_args处理异常：{run_fun}{sys.argv}{e}")
    elif len(sys.argv) == 2:
        # N个时间作业 python xxx.py 2023-03-01,2023-03-02
        dates = sys.argv[1].split(',')
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for date in dates:
                    tmp_year, tmp_month, tmp_day = date.split("-")
                    run_date = datetime.datetime(int(tmp_year), int(tmp_month), int(tmp_day)).date()
                    if _should_run_on_trade_date(run_date):
                        executor.submit(run_fun, run_date, *args)
                        time.sleep(2.5)
        except Exception as e:
            logging.error(f"run_template.run_with_args处理异常：{run_fun}{sys.argv}{e}")
    else:
        # 当前时间作业 python xxx.py
        try:
            run_date, run_date_nph = trd.get_trade_date_last()
            if run_fun.__name__.startswith('save_nph'):
                run_fun(run_date_nph, False)
            elif run_fun.__name__.startswith('save_after_close'):
                run_fun(run_date, *args)
            else:
                run_fun(run_date_nph, *args)
        except Exception as e:
            logging.error(f"run_template.run_with_args处理异常：{run_fun}{sys.argv}{e}")
