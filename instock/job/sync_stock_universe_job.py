#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 mootdx 在线（或本地 TDX 目录）同步全市场 A 股代码表 cn_stock_universe。"""

from __future__ import annotations

import logging
import os.path
import sys

cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)

import argparse

from instock.core.data.profile import tdx_dir
from instock.core.mootdx_universe import (
    fetch_universe_from_tdx_dir,
    fetch_universe_mootdx_online,
    upsert_universe_df,
)


def main():
    p = argparse.ArgumentParser(description="同步 cn_stock_universe")
    p.add_argument(
        "--source",
        choices=["online", "local"],
        default=os.environ.get("INSTOCK_UNIVERSE_SOURCE", "online"),
        help="online=mootdx 在线列表；local=扫描 INSTOCK_TDX_DIR/vipdoc",
    )
    args = p.parse_args()
    source = str(args.source).strip().lower()

    df = None
    if source == "local":
        d = tdx_dir()
        if not d:
            raise RuntimeError("[FAIL] INSTOCK_UNIVERSE_SOURCE=local 但未配置 INSTOCK_TDX_DIR")
        logging.info("sync_stock_universe: 从本地 TDX 扫描 %s", d)
        df = fetch_universe_from_tdx_dir(d, log=logging.info)
    else:
        logging.info("sync_stock_universe: 从 mootdx 在线拉取列表")
        df = fetch_universe_mootdx_online(log=logging.info)

    n = upsert_universe_df(df)
    logging.info("sync_stock_universe_job: 已写入 cn_stock_universe %s 条", n)
    try:
        from instock.core.data.lineage import record_batch
        from instock.core.data.provider import FetchResult

        record_batch(
            FetchResult(
                ok=True,
                domain_id="stock_universe",
                provider_id=df["source_provider"].iloc[0] if not df.empty else "mootdx_online",
                scope_type="table",
                scope_key="cn_stock_universe",
                metadata={"row_count": n},
            ),
            job_id="sync_stock_universe_job",
        )
    except Exception as e:
        logging.warning("sync_stock_universe_job record_batch: %s", e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    main()
