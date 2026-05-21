#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 cache/hist/*.pickle 一次性导入 cn_stock_daily_bar（来源 legacy_cache）。"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

cpath = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(cpath))

import instock.lib.database as mdb
from instock.core.canonical.writer import CanonicalBarWriter
from instock.core import stockfetch as stf

logger = logging.getLogger(__name__)


def _collect_pickles(root: Path) -> list[Path]:
    return sorted(root.rglob("*.pickle"))


def main():
    p = argparse.ArgumentParser(description="迁移 cache/hist 到标准日线表")
    p.add_argument("--limit", type=int, default=0, help="最多处理 N 个 pickle")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    hist_dir = Path(stf.stock_hist_cache_path)
    if not hist_dir.is_dir():
        logger.error("目录不存在: %s", hist_dir)
        return 1
    files = [p for p in _collect_pickles(hist_dir) if p.name.endswith(".gzip.pickle")]
    if args.limit > 0:
        files = files[: args.limit]
    writer = CanonicalBarWriter("legacy_cache")
    ok = fail = 0
    for fp in files:
        # 文件名多为 600000.pickle 或路径末段
        code = fp.stem.split("_")[0].zfill(6)[:6]
        try:
            import pickle

            with open(fp, "rb") as f:
                df = pickle.load(f)
            if args.dry_run:
                logger.info("[dry-run] %s rows=%s", code, len(df) if df is not None else 0)
                ok += 1
                continue
            stats = writer.write_dataframe(code, df)
            logger.info("%s %s", code, stats.to_dict())
            ok += 1
        except Exception as e:
            fail += 1
            logger.warning("%s FAIL %s", code, e)
    logger.info("完成 ok=%s fail=%s (db=%s)", ok, fail, mdb.db_database)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
