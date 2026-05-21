#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按单一数据源遍历补标准日线表 cn_stock_daily_bar（多源独立、幂等合并）。
示例：
  python sync_bars_source_job.py --source akshare --limit 10
  python sync_bars_source_job.py --source tushare
  python sync_bars_source_job.py --source mootdx
  python sync_bars_source_job.py --source eastmoney
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)

from instock.core.canonical.source_fetch import fetch_bars_single_source
from instock.core.canonical.writer import CanonicalBarWriter
from instock.core.mootdx_universe import count_universe, load_universe_codes

VALID_SOURCES = ("mootdx", "mootdx_local", "mootdx_online", "tushare", "akshare", "eastmoney")


def _default_from_date() -> str:
    import datetime

    import instock.lib.trade_time as trd

    today = datetime.date.today().isoformat()
    ds, _ = trd.get_trade_hist_interval(today)
    return ds


def _emit(msg: str) -> None:
    """任务中心按行读 stdout；必须 flush 才能在运行中看到。"""
    print(msg, flush=True)


def _sync_one(
    source: str,
    code: str,
    date_from: str,
    date_to: str,
    also_pickle: bool,
) -> tuple[str, bool, str]:
    _emit(f"[FETCH] {code} 请求 {source} …")
    try:
        df, pid, err = fetch_bars_single_source(source, code, date_from, date_to, adjust="raw")
        if df is None or df.empty:
            return code, False, f"empty provider={pid or source} {err or ''}"
        writer = CanonicalBarWriter(pid or source)
        stats = writer.write_dataframe(code, df)
        msg = f"rows={len(df)} {stats.to_dict()}"
        if also_pickle:
            try:
                import instock.core.stockfetch as stf

                stf.stock_hist_cache(
                    code,
                    date_from.replace("-", ""),
                    date_end=date_to.replace("-", "") if date_to else None,
                    is_cache=True,
                    adjust="",
                )
            except Exception:
                pass
        return code, True, msg
    except Exception as e:
        return code, False, str(e)[:120]


def _default_workers(source: str) -> int:
    if source == "akshare":
        return max(1, int(os.environ.get("INSTOCK_AKSHARE_WORKERS", "2")))
    return 4


def _default_sleep(source: str) -> float:
    if source == "akshare":
        return float(os.environ.get("INSTOCK_AKSHARE_SLEEP", "0.35"))
    return 0.05


def main():
    p = argparse.ArgumentParser(description="按数据源补标准日线库")
    p.add_argument(
        "--source",
        required=True,
        choices=VALID_SOURCES,
        help="mootdx|tushare|akshare|eastmoney|mootdx_local|mootdx_online",
    )
    p.add_argument("--from-date", default="", help="起始 YYYYMMDD 或 YYYY-MM-DD")
    p.add_argument("--to-date", default="", help="结束日")
    p.add_argument("--limit", type=int, default=0, help="仅处理前 N 只")
    p.add_argument("--workers", type=int, default=0, help="并发数，0=按数据源默认")
    p.add_argument("--sleep", type=float, default=-1, help="每只间隔秒，-1=默认")
    p.add_argument(
        "--also-pickle",
        action="store_true",
        help="并行写入 cache/hist（过渡，默认仅写标准表）",
    )
    args = p.parse_args()
    if not (args.from_date or "").strip():
        args.from_date = _default_from_date()
        logging.info("未指定 --from-date，使用默认起始日 %s", args.from_date)

    workers = args.workers if args.workers > 0 else _default_workers(args.source)
    sleep_sec = args.sleep if args.sleep >= 0 else _default_sleep(args.source)

    n_uni = count_universe()
    if n_uni == 0:
        raise RuntimeError("[FAIL] cn_stock_universe 为空，请先 sync_stock_universe_job")
    codes = load_universe_codes(args.limit if args.limit > 0 else None)
    prefix = f"bars_canonical[{args.source}]"
    total = len(codes)
    _emit(
        f"[PROGRESS] 0/{total} {prefix} 开始: 证券 {total} 只, "
        f"区间 {args.from_date} ~ {args.to_date or '最新'}, workers={workers}, sleep={sleep_sec}"
    )
    if args.source == "akshare":
        _emit(
            "[HINT] Akshare 易被限流/断连，默认 workers=2；"
            "若大量 RemoteDisconnected 请改为 --workers 1 --sleep 0.5"
        )

    ok_n = fail_n = 0
    done_n = 0
    t0 = time.time()
    stop_hb = threading.Event()

    def _heartbeat() -> None:
        while not stop_hb.wait(8):
            _emit(
                f"[PROGRESS] 等待网络/写入… 已完成 {done_n}/{total} "
                f"ok={ok_n} fail={fail_n} elapsed={time.time() - t0:.0f}s"
            )

    hb = threading.Thread(target=_heartbeat, daemon=True)
    hb.start()

    try:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futs = {
                ex.submit(
                    _sync_one,
                    args.source,
                    c,
                    args.from_date,
                    args.to_date,
                    args.also_pickle,
                ): c
                for c in codes
            }
            for i, fut in enumerate(as_completed(futs), 1):
                code, ok, msg = fut.result()
                done_n = i
                if ok:
                    ok_n += 1
                else:
                    fail_n += 1
                    _emit(f"[WARN] {prefix} {code} FAIL {msg}")
                if sleep_sec > 0:
                    time.sleep(sleep_sec)
                _emit(
                    f"[PROGRESS] {i}/{total} {code} "
                    f"{'OK' if ok else 'FAIL'} ok={ok_n} fail={fail_n} elapsed={time.time() - t0:.0f}s"
                )
    finally:
        stop_hb.set()
        hb.join(timeout=1)

    _emit(f"[PROGRESS] {total}/{total} {prefix} 完成 ok={ok_n} fail={fail_n}")
    logging.info("%s 完成: ok=%s fail=%s total=%s", prefix, ok_n, fail_n, total)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
    main()
