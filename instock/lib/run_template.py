#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import inspect
import logging
import datetime
import os
import sys
import time
import instock.lib.trade_time as trd

__author__ = 'myh '
__date__ = '2023/3/10 '


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


def _accepts_before(run_fun) -> bool:
    try:
        params = list(inspect.signature(run_fun).parameters.values())
    except (TypeError, ValueError):
        return False
    return len(params) >= 2 and params[1].name == "before"


def _max_consecutive_fail() -> int:
    try:
        return max(1, int(os.environ.get("INSTOCK_MAX_CONSECUTIVE_FETCH_FAIL", "5")))
    except (TypeError, ValueError):
        return 5


def _invoke_one(run_fun, run_date, extra_args):
    if _accepts_before(run_fun):
        run_fun(run_date, False, *extra_args)
    else:
        run_fun(run_date, *extra_args)


def _dates_from_argv() -> list:
    if len(sys.argv) == 3:
        tmp_year, tmp_month, tmp_day = sys.argv[1].split("-")
        start_date = datetime.datetime(int(tmp_year), int(tmp_month), int(tmp_day)).date()
        tmp_year, tmp_month, tmp_day = sys.argv[2].split("-")
        end_date = datetime.datetime(int(tmp_year), int(tmp_month), int(tmp_day)).date()
        out = []
        run_date = start_date
        while run_date <= end_date:
            if _should_run_on_trade_date(run_date):
                out.append(run_date)
            run_date += datetime.timedelta(days=1)
        return out
    if len(sys.argv) == 2:
        out = []
        for date in sys.argv[1].split(","):
            date = date.strip()
            if not date:
                continue
            tmp_year, tmp_month, tmp_day = date.split("-")
            run_date = datetime.datetime(int(tmp_year), int(tmp_month), int(tmp_day)).date()
            if _should_run_on_trade_date(run_date):
                out.append(run_date)
        return out
    return []


# 通用函数，获得日期参数，支持批量作业。
def run_with_args(run_fun, *args):
    batch_dates = _dates_from_argv()
    if batch_dates:
        total = len(batch_dates)
        max_consec = _max_consecutive_fail()
        print(
            f"[PROGRESS] 共 {total} 个交易日待处理（连续失败 {max_consec} 次将自动终止）",
            flush=True,
        )
        failures: list = []
        consecutive = 0
        for i, run_date in enumerate(batch_dates, 1):
            ds = run_date.strftime("%Y-%m-%d")
            print(f"[PROGRESS] {i}/{total} {ds} start", flush=True)
            try:
                _invoke_one(run_fun, run_date, args)
                consecutive = 0
                print(f"[PROGRESS] {i}/{total} {ds} done", flush=True)
            except Exception as e:
                consecutive += 1
                msg = str(e)
                failures.append(msg)
                logging.error("run_template 子任务失败 %s: %s", ds, e)
                print(f"[FAIL] {ds} {msg}", flush=True)
                if consecutive >= max_consec:
                    print(
                        f"[FAIL] 连续 {consecutive} 个交易日拉取失败，已停止后续日期",
                        flush=True,
                    )
                    sys.exit(1)
            time.sleep(2.5)
        if failures:
            print(f"[FAIL] 共 {len(failures)}/{total} 个交易日失败", flush=True)
            sys.exit(1)
        print(f"[PROGRESS] 全部 {total} 日完成", flush=True)
        return

    try:
        run_date, run_date_nph = trd.get_trade_date_last()
        if run_fun.__name__.startswith('save_after_close'):
            target = run_date
        else:
            target = run_date_nph
        if _accepts_before(run_fun):
            run_fun(target, False, *args)
        else:
            run_fun(target, *args)
    except Exception as e:
        logging.error(f"run_template.run_with_args处理异常：{run_fun}{sys.argv}{e}")
        sys.exit(1)
