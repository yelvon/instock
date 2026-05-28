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
from instock.core.canonical.sync_plan import (
    filter_bars_to_missing_dates,
    plan_canonical_sync,
    sync_skip_complete_enabled,
)
import instock.lib.database as mdb
from instock.core.canonical.writer import CanonicalBarWriter, ensure_canonical_tables
from instock.core.data.lineage import ensure_data_batch_table, record_canonical_batch
from instock.core.mootdx_universe import count_universe, load_universe_codes

VALID_SOURCES = ("mootdx", "mootdx_local", "mootdx_online", "tushare", "akshare", "eastmoney")
_QFQ_AFTER_SOURCES = frozenset({"mootdx_local", "mootdx"})


def _qfq_derive_mode() -> str:
    m = os.environ.get("INSTOCK_QFQ_DERIVE_MODE", "incremental").strip().lower()
    if m in ("0", "off", "no", "false", "skip"):
        return ""
    if m in ("full", "incremental"):
        return m
    return "incremental"


def _run_qfq_derive_phase(source: str, date_from: str, date_to: str) -> bool:
    """raw 补数结束后在同一进程派生前复权；区间与本次 raw 补数一致。"""
    mode = _qfq_derive_mode()
    if not mode or source not in _QFQ_AFTER_SOURCES:
        return True
    from instock.core.canonical.sync_plan import resolve_sync_range

    d0, d1 = resolve_sync_range(
        (date_from or "").strip() or "1990-01-01",
        (date_to or "").strip(),
    )
    scope_from = d0.isoformat()
    scope_to = d1.isoformat()
    from instock.core.adjustment.corporate_action_store import (
        get_stored_factor_version,
        ingest_gbbq_to_db,
        qfq_table_has_rows,
    )
    from instock.core.adjustment.derive import run_derive
    from instock.core.adjustment.gbbq_reader import gbbq_factor_version

    _emit(f"[PROGRESS] raw 阶段结束，开始派生前复权（mode={mode}）…")
    if not get_stored_factor_version():
        _emit("[qfq] gbbq 未入库，先 ingest …")
        ing = ingest_gbbq_to_db()
        if ing.get("error"):
            _emit(f"[FAIL] ingest gbbq: {ing.get('error')}")
            return False
        _emit(f"[qfq] ingest 完成 rows={ing.get('rows', 0)}")
    cur = gbbq_factor_version()
    stored = get_stored_factor_version()
    if cur and cur != stored:
        _emit(f"[qfq] gbbq 版本变化 {stored} -> {cur}，重新 ingest")
        ingest_gbbq_to_db()
        mode = "full"
    limit_scope = bool(scope_from)
    if mode == "incremental" and not qfq_table_has_rows():
        _emit("[HINT] qfq 表为空，首次执行全历史派生（与本次 raw 区间无关）")
        mode = "full"
        limit_scope = False
    elif limit_scope:
        _emit(
            f"[HINT] qfq 派生区间与 raw 补数一致: {scope_from} ~ {scope_to or '最新'} "
            f"（复权计算仍用该股全历史 raw，仅写入该区间）"
        )

    r = run_derive(
        mode=mode,
        skip_ingest=True,
        log=_emit,
        date_from=scope_from,
        date_to=scope_to,
        limit_sync_scope=limit_scope,
    )
    ok = bool(r.get("ok"))
    _emit(
        f"[PROGRESS] qfq 派生完成 ok={r.get('success', 0)} skip={r.get('skipped', 0)} "
        f"fail={r.get('failed', 0)} mode={mode}"
    )
    if not ok:
        _emit(f"[FAIL] qfq: {r.get('error') or r.get('hint') or 'derive failed'}")
    return ok


def _default_from_date() -> str:
    import datetime

    import instock.lib.trade_time as trd

    today = datetime.date.today().isoformat()
    ds, _ = trd.get_trade_hist_interval(today)
    return ds


def _emit(msg: str) -> None:
    """任务中心按行读 stdout；必须 flush 才能在运行中看到。"""
    print(msg, flush=True)


def _worker_db_init() -> None:
    """线程池 worker 内复用连接（每线程一条，避免 Errno 99）。"""
    mdb.begin_reuse_connection()


def _sync_one(
    source: str,
    code: str,
    date_from: str,
    date_to: str,
    also_pickle: bool,
    job_batch_id: str = "",
) -> tuple[str, bool, str]:
    try:
        if sync_skip_complete_enabled():
            plan = plan_canonical_sync(code, date_from, date_to, adjust_type="raw")
            if plan.get("skip"):
                return (
                    code,
                    True,
                    f"skip 已覆盖 {plan.get('expected_days')} 个交易日 "
                    f"({plan.get('date_from')}~{plan.get('date_to')})",
                )
            missing = plan.get("missing_dates") or []
        else:
            missing = []

        _emit(
            f"[FETCH] {code} 请求 {source} …"
            + (f" 缺 {len(missing)} 日" if missing else "")
        )
        df, pid, err = fetch_bars_single_source(source, code, date_from, date_to, adjust="raw")
        if df is None or df.empty:
            return code, False, f"empty provider={pid or source} {err or ''}"
        if missing:
            df = filter_bars_to_missing_dates(df, missing)
            if df is None or df.empty:
                return (
                    code,
                    True,
                    f"skip 拉取后无待补行（缺日 {len(missing)}，或源未含该区间）",
                )
        writer = CanonicalBarWriter(pid or source)
        stats = writer.write_dataframe(
            code, df, batch_id=job_batch_id or None
        )
        if stats.inserted + stats.filled == 0 and len(df) > 0:
            if stats.skipped > 0 and stats.errors == 0 and stats.conflict == 0:
                return (
                    code,
                    True,
                    f"skip 库内已完整 {stats.skipped} 日（拉取 {len(df)} 行）",
                )
            return (
                code,
                False,
                f"写入 0 行（拉取 {len(df)} 行），请检查日期列/归一化 provider={pid or source}",
            )
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
    # Parallels/SMB 挂载 vipdoc 时并发读 .day 易触发 Errno 5 EIO
    if source == "mootdx_local":
        return max(1, int(os.environ.get("INSTOCK_MOOTDX_LOCAL_WORKERS", "1")))
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
    if args.source == "mootdx_local":
        _emit(
            "[HINT] 本地通达信补数默认 workers=1，作业内复用 MySQL 连接；"
            "若见 Errno 99 / Can't connect：停止任务 → docker restart InStock → 再跑"
        )
    if sync_skip_complete_enabled():
        _emit(
            "[HINT] 已启用存量跳过（INSTOCK_SYNC_SKIP_COMPLETE=1）："
            "区间内 raw 已完整则不再拉取/写入；有缺口仅 merge 缺失日"
        )

    ensure_canonical_tables()
    ensure_data_batch_table()
    mdb.begin_reuse_connection()
    try:
        job_batch_id = record_canonical_batch(
            args.source,
            scope_key=f"sync_bars:{args.source}",
            row_count=0,
            job_id="sync_bars_source_job",
        )
    finally:
        mdb.end_reuse_connection()

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
        with ThreadPoolExecutor(
            max_workers=max(1, workers), initializer=_worker_db_init
        ) as ex:
            futs = {
                ex.submit(
                    _sync_one,
                    args.source,
                    c,
                    args.from_date,
                    args.to_date,
                    args.also_pickle,
                    job_batch_id,
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

    qfq_ok = _run_qfq_derive_phase(args.source, args.from_date, args.to_date or "")
    if not qfq_ok:
        raise SystemExit(2)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
    main()
