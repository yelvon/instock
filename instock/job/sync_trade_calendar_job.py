#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将交易日历同步到本地表 trade_calendar，供断档检测与质量校验 H6。"""

import logging
import os.path
import sys

cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)

import instock.core.pipeline.trade_calendar as tc

__author__ = "pipeline"


def main():
    tc.ensure_table()
    n = tc.sync_from_network()
    logging.info("sync_trade_calendar_job: 已同步交易日条数约 %s（含 ON DUPLICATE 更新）", n)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    main()
