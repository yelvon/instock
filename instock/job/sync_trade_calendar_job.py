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
    try:
        from instock.core.data.lineage import record_batch
        from instock.core.data.provider import FetchResult

        record_batch(
            FetchResult(
                ok=True,
                domain_id="trade_calendar",
                provider_id="sina_trade_date",
                scope_type="table",
                scope_key=tc.TABLE_NAME,
                metadata={"row_synced": n},
            ),
            job_id="sync_trade_calendar_job",
        )
    except Exception as e:
        logging.warning("sync_trade_calendar_job record_batch: %s", e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    main()
