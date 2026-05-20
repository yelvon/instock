#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按 cn_stock_universe 遍历拉取日线 K 线（写入 cache/hist pickle，走 Registry daily_bar_raw）。
建议先跑 sync_stock_universe_job；可用 --limit 做小样本试跑。
"""

from __future__ import annotations

import argparse
import logging
import os.path
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)

from instock.core.mootdx_universe import count_universe, load_universe_codes


def _bar_source_label() -> str:
    try:
        from instock.core.data.profile import effective_bar_data_source

        return effective_bar_data_source()
    except Exception:
        return os.environ.get("INSTOCK_BAR_DATA_SOURCE", "auto") or "auto"


def _log_prefix() -> str:
    return f"bars_sync[{_bar_source_label()}]"


def _sync_one(code: str, date_from: str, date_to: str) -> tuple[str, bool, str]:
    try:
        import instock.core.stockfetch as stf

        ds = date_from.replace("-", "")
        de = date_to.replace("-", "") if date_to else None
        df = stf.stock_hist_cache(code, ds, de, is_cache=True, adjust="")
        if df is not None and not df.empty:
            return code, True, f"rows={len(df)}"
        return code, False, f"empty provider={_bar_source_label()}"
    except Exception as e:
        return code, False, str(e)[:120]


def _default_from_date() -> str:
    import datetime

    import instock.lib.trade_time as trd

    today = datetime.date.today().isoformat()
    ds, _ = trd.get_trade_hist_interval(today)
    return ds


def main():
    p = argparse.ArgumentParser(description="mootdx/Registry 遍历拉 K 线缓存")
    p.add_argument(
        "--from-date",
        default="",
        help="起始 YYYYMMDD 或 YYYY-MM-DD；省略时默认约 3 年前（与 get_trade_hist_interval 一致）",
    )
    p.add_argument("--to-date", default="", help="结束日，可省略")
    p.add_argument("--limit", type=int, default=0, help="仅处理前 N 只（0=全部）")
    p.add_argument("--workers", type=int, default=4, help="并发数")
    p.add_argument("--sleep", type=float, default=0.05, help="每只完成后休眠秒数")
    args = p.parse_args()
    if not (args.from_date or "").strip():
        args.from_date = _default_from_date()
        logging.info("未指定 --from-date，使用默认起始日 %s", args.from_date)

    n_uni = count_universe()
    if n_uni == 0:
        raise RuntimeError(
            "[FAIL] cn_stock_universe 为空，请先执行 sync_stock_universe_job"
        )
    codes = load_universe_codes(args.limit if args.limit > 0 else None)
    src = _bar_source_label()
    logging.info(
        "%s 开始: 日线源=%s 证券主表 %s 条，本次 %s 只，区间 %s ~ %s",
        _log_prefix(),
        src,
        n_uni,
        len(codes),
        args.from_date,
        args.to_date or "最新",
    )
    if src == "tushare":
        logging.info(
            "%s 提示: 日志前缀 bars_sync 为作业名，非 mootdx；空数据多为 Tushare 无该代码/区间行情或限频",
            _log_prefix(),
        )

    ok_n = 0
    fail_n = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {
            ex.submit(_sync_one, c, args.from_date, args.to_date): c for c in codes
        }
        for i, fut in enumerate(as_completed(futs), 1):
            code, ok, msg = fut.result()
            if ok:
                ok_n += 1
            else:
                fail_n += 1
                if fail_n <= 5 or fail_n % 100 == 0:
                    logging.warning("%s %s FAIL %s", _log_prefix(), code, msg)
            if args.sleep > 0:
                time.sleep(args.sleep)
            if i % 50 == 0 or i == len(codes):
                logging.info(
                    "进度 %s/%s ok=%s fail=%s elapsed=%.0fs",
                    i,
                    len(codes),
                    ok_n,
                    fail_n,
                    time.time() - t0,
                )

    logging.info(
        "%s 完成: ok=%s fail=%s total=%s",
        _log_prefix(),
        ok_n,
        fail_n,
        len(codes),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    main()
