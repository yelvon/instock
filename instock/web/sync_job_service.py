#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Web 触发的数据同步作业：子进程执行 instock/job 脚本，记录运行历史。"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import uuid
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

_max_output_chars = 20000

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_HISTORY_PATH = os.path.join(_REPO_ROOT, "instock", "log", "sync_job_history.json")
_LOCK = threading.Lock()
_RUNS: Dict[str, Dict[str, Any]] = {}
_ORDER: List[str] = []
_ACTIVE_PROCS: Dict[str, subprocess.Popen] = {}
_MAX_RUNS = 200
_COOKIE_MAX_BYTES = 65536


def cookie_file_path() -> str:
    return os.path.join(_REPO_ROOT, "instock", "config", "eastmoney_cookie.txt")


def read_eastmoney_cookie() -> Dict[str, Any]:
    path = cookie_file_path()
    if not os.path.isfile(path):
        return {"path": path, "content": "", "bytes": 0, "exists": False}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    b = len(text.encode("utf-8"))
    return {"path": path, "content": text, "bytes": b, "exists": True}


def save_eastmoney_cookie(content: str) -> str:
    raw = (content or "").replace("\r\n", "\n").strip()
    enc = raw.encode("utf-8")
    if len(enc) > _COOKIE_MAX_BYTES:
        raise ValueError(f"Cookie 过长（>{_COOKIE_MAX_BYTES} 字节）")
    path = cookie_file_path()
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw)
    return path


JOB_ITEMS: List[Dict[str, str]] = [
    {
        "id": "execute_daily_job",
        "script": "execute_daily_job.py",
        "title": "整体日作业",
        "hint": "按固定顺序跑完当日主流程",
        "description": "总控任务：依次执行 init → 基础快照 → 综合选股 →（并行）其它基础数据 → 盘后数据等，对应 execute_daily_job.py 源码顺序。适合「一键补全天流水线」。注意源码里指标/K 线/策略/事后统计可能被注释，需要时请单独跑单项作业。",
    },
    {
        "id": "init_job",
        "script": "init_job.py",
        "title": "初始化数据库",
        "hint": "建库、关注表等基础结构",
        "description": "首次部署或换库时执行：CREATE DATABASE（若不存在）、创建关注表等最小表结构。不涉及行情抓取；仅需日期模式选「默认」。",
    },
    {
        "id": "sync_trade_calendar_job",
        "script": "sync_trade_calendar_job.py",
        "title": "同步交易日历",
        "hint": "写入 trade_calendar 表",
        "description": "从网络拉取 A 股交易日历并 upsert 到本地表 trade_calendar，供断档检测与质量 H6 使用。建议新库或发现「数据缺口自检」提示日历为空时执行；仅需日期模式选「默认」。",
    },
    {
        "id": "sync_stock_universe_job",
        "script": "sync_stock_universe_job.py",
        "title": "同步证券主表",
        "hint": "cn_stock_universe；本地扫描见通达信页",
        "mootdx_panel": True,
        "description": "写入 cn_stock_universe。默认在线列表；通达信本地页触发时会设 INSTOCK_UNIVERSE_SOURCE=local 扫描 vipdoc。",
    },
    {
        "id": "mootdx_bars_sync_job",
        "script": "mootdx_bars_sync_job.py",
        "title": "遍历拉 K 线（日线·旧缓存）",
        "hint": "cache/hist；过渡用，标准库请用下方按源补数",
        "description": "按 cn_stock_universe 逐只拉日线写入 cache/hist（走 daily_bar_raw Registry）。回测已优先读标准表 cn_stock_daily_bar。\n· 默认：从约 3 年前至今。\n· 日线源可选自动链路、仅 mootdx、仅 Tushare、仅东财。",
    },
    {
        "id": "sync_bars_mootdx_local_job",
        "script": "sync_bars_source_job.py",
        "title": "标准库补数（通达信本地）",
        "hint": "仅读 INSTOCK_TDX_DIR/vipdoc",
        "canonical_source": "mootdx_local",
        "mootdx_panel": True,
        "description": "只读本地通达信 vipdoc，写入 cn_stock_daily_bar；需配置 INSTOCK_TDX_DIR 并先同步证券主表（本地扫描）。",
    },
    {
        "id": "sync_bars_mootdx_job",
        "script": "sync_bars_source_job.py",
        "title": "标准库补数（mootdx 本地→在线）",
        "hint": "本地失败后试 online",
        "canonical_source": "mootdx",
        "mootdx_panel": True,
        "description": "先 mootdx_local，失败再 mootdx_online；写入标准日线表。",
    },
    {
        "id": "sync_bars_tushare_job",
        "script": "sync_bars_source_job.py",
        "title": "标准库补数（Tushare）",
        "hint": "写入 cn_stock_daily_bar",
        "canonical_source": "tushare",
        "description": "仅 Tushare 独立补标准日线表。需配置 TUSHARE_TOKEN。",
    },
    {
        "id": "sync_bars_akshare_job",
        "script": "sync_bars_source_job.py",
        "title": "标准库补数（Akshare）",
        "hint": "写入 cn_stock_daily_bar",
        "canonical_source": "akshare",
        "description": "仅 Akshare 独立补标准日线表（volume 手→股）。需 pip install akshare。",
    },
    {
        "id": "sync_bars_eastmoney_job",
        "script": "sync_bars_source_job.py",
        "title": "标准库补数（东财）",
        "hint": "写入 cn_stock_daily_bar",
        "canonical_source": "eastmoney",
        "description": "仅东财 K 线独立补标准日线表。",
    },
    {
        "id": "basic_data_daily_job",
        "script": "basic_data_daily_job.py",
        "title": "股票/ETF 快照",
        "hint": "全市场当日报价快照",
        "description": "抓取当日 A 股全市场快照与 ETF 快照，写入 cn_stock_spot、cn_etf_spot，是多数模块的数据底座。盘中可多次更新；选择交易日日期运行。可在本页选择快照数据源（默认东财；可选仅 Baostock 或东财失败/为空时回补 Baostock）。",
    },
    {
        "id": "selection_data_daily_job",
        "script": "selection_data_daily_job.py",
        "title": "综合选股",
        "hint": "东财选股器类结果",
        "description": "按东方财富「综合选股」类接口写入 cn_stock_selection，用于页面「综合选股」等展示。依赖接口与 Cookie/网络环境。",
    },
    {
        "id": "basic_data_other_daily_job",
        "script": "basic_data_other_daily_job.py",
        "title": "其它基础数据",
        "hint": "龙虎榜、资金流、涨停原因等",
        "description": "一批扩展基础数据：龙虎榜统计、分红配送、个股/行业/概念资金流、早盘抢筹、涨停原因等（详见 作业说明.md）。建议先有当日快照 cn_stock_spot 再跑，耗时可较长。",
    },
    {
        "id": "basic_data_after_close_daily_job",
        "script": "basic_data_after_close_daily_job.py",
        "title": "盘后数据",
        "hint": "收盘后才完整的数据",
        "description": "收盘后更完整的数据流，如大宗交易、尾盘抢筹等（以源码为准）。请在收盘后或晚间运行对应日期。",
    },
    {
        "id": "indicators_data_daily_job",
        "script": "indicators_data_daily_job.py",
        "title": "技术指标",
        "hint": "指标与买卖信号表",
        "description": "计算技术指标并写入指标相关表及买卖信号表，运行时间通常较长。需已有足够历史 K 线等基础数据。",
    },
    {
        "id": "klinepattern_data_daily_job",
        "script": "klinepattern_data_daily_job.py",
        "title": "K 线形态",
        "hint": "Talib 形态写入 cn_stock_pattern",
        "description": "基于 K 线计算形态（如 Talib），结果写入 cn_stock_pattern。依赖历史行情已入库。",
    },
    {
        "id": "strategy_data_daily_job",
        "script": "strategy_data_daily_job.py",
        "title": "策略选股",
        "hint": "各策略表 cn_stock_strategy_*",
        "description": "按 tablestructure 中注册的策略函数逐策略跑批，写入各 cn_stock_strategy_* 表。需指标等前置数据按策略而定。",
    },
    {
        "id": "backtest_data_daily_job",
        "script": "backtest_data_daily_job.py",
        "title": "信号事后收益统计",
        "hint": "信号日后 N 日涨跌统计",
        "description": "对已有买卖信号与策略信号做「事后收益率」统计（非撮合级回测），写入表中带 RATE 扩展列。需先有信号日与历史收盘价数据。",
    },
    {
        "id": "ingest_tdx_gbbq_job",
        "script": "ingest_tdx_gbbq_job.py",
        "title": "同步通达信 gbbq（股本变迁）",
        "hint": "T0002/hq_cache/gbbq → 除权事件表",
        "mootdx_panel": True,
        "description": "解析本地通达信 gbbq，写入 cn_stock_corporate_action。前复权派生前须先同步 gbbq 目录。",
    },
    {
        "id": "derive_qfq_from_tdx_job",
        "script": "derive_qfq_from_tdx_job.py",
        "title": "派生前复权（标准库 qfq）",
        "hint": "raw → cn_stock_daily_bar_qfq；首次请选 full",
        "mootdx_panel": True,
        "description": "由 cn_stock_daily_bar(raw) 与 gbbq 派生前复权，写入 cn_stock_daily_bar_qfq。参数示例：--mode full 或 --mode incremental。",
    },
    {
        "id": "sync_tdx_local_pipeline_job",
        "script": "sync_tdx_local_pipeline_job.py",
        "title": "一键：通达信本地+前复权",
        "hint": "universe → raw → gbbq → qfq",
        "mootdx_panel": True,
        "description": "顺序执行：证券主表(本地) → 标准库补数(通达信本地) → ingest gbbq → 派生 qfq。CLI：--qfq-mode full|incremental",
    },
]

QFQ_MODE_JOB_IDS = frozenset({"derive_qfq_from_tdx_job", "sync_tdx_local_pipeline_job"})


def normalize_qfq_mode(mode: str, *, default: str = "incremental") -> str:
    m = (mode or default).strip().lower()
    return m if m in ("full", "incremental") else default


def get_repo_root() -> str:
    return _REPO_ROOT


def _ensure_log_dir() -> None:
    log_dir = os.path.dirname(_HISTORY_PATH)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir, exist_ok=True)


def _truncate(s: str) -> str:
    if len(s) <= _max_output_chars:
        return s
    return "...[truncated]\n" + s[-_max_output_chars:]


_ERR_PAT = re.compile(
    r"处理异常|Traceback|ERROR|Error:|Exception:|CRITICAL|致命|失败\[|\[FAIL\]",
    re.IGNORECASE,
)
_PROGRESS_PAT = re.compile(
    r"\[PROGRESS\]\s*(?:(\d+)/(\d+)\s+)?(\d{4}-\d{2}-\d{2})?\s*(.*)?",
    re.IGNORECASE,
)


def _progress_meta(merged_out: str) -> Tuple[int, int, int, str, str, int, int]:
    """字节数、行数、疑似报错行数、报错尾、最近进度文案、进度 current、进度 total。"""
    if not merged_out:
        return 0, 0, 0, "", "", 0, 0
    lines = merged_out.split("\n")
    nlines = len(lines)
    nbytes = len(merged_out.encode("utf-8"))
    hit_lines = [ln for ln in lines if _ERR_PAT.search(ln)]
    err_count = len(hit_lines)
    tail_err = "\n".join(hit_lines[-12:]) if hit_lines else ""
    prog_lines = [ln.strip() for ln in lines if "[PROGRESS]" in ln]
    progress_hint = prog_lines[-1] if prog_lines else ""
    cur, total = 0, 0
    if prog_lines:
        m = _PROGRESS_PAT.search(prog_lines[-1])
        if m and m.group(1) and m.group(2):
            cur, total = int(m.group(1)), int(m.group(2))
    return nbytes, nlines, err_count, tail_err, progress_hint, cur, total


def _collect_batch_ids_for_job(job_id: str) -> List[str]:
    """作业成功后附加最近 data_batch id（轻量可观测）。"""
    try:
        from instock.core.data.lineage import latest_batch_id

        bids: List[str] = []
        if job_id == "basic_data_daily_job":
            b = latest_batch_id("daily_spot_snapshot")
            if b:
                bids.append(b)
        elif job_id == "indicators_data_daily_job":
            b = latest_batch_id("derived_indicators")
            if b:
                bids.append(b)
        elif job_id == "sync_trade_calendar_job":
            b = latest_batch_id("trade_calendar")
            if b:
                bids.append(b)
        return bids
    except Exception:
        return []


def _verify_spot_dates_after_run(date_list_csv: str) -> Dict[str, Any]:
    """补数完成后核对枚举日期是否已写入 cn_stock_spot。"""
    import instock.lib.database as mdb

    names = [x.strip() for x in (date_list_csv or "").split(",") if x.strip()]
    if not names:
        return {"checked": 0, "still_missing": [], "ok_dates": []}
    still: List[str] = []
    ok: List[str] = []
    for ds in names:
        try:
            cnt = mdb.executeSqlCount(
                "SELECT COUNT(*) FROM `cn_stock_spot` WHERE `date` = %s", (ds,)
            )
            if cnt and cnt > 0:
                ok.append(ds)
            else:
                still.append(ds)
        except Exception:
            still.append(ds)
    return {"checked": len(names), "still_missing": still, "ok_dates": ok}


def _load() -> None:
    global _RUNS, _ORDER
    if not os.path.isfile(_HISTORY_PATH):
        return
    try:
        with open(_HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                rid = item.get("id")
                if rid:
                    item.setdefault("error_line_count", 0)
                    item.setdefault("last_errors_tail", "")
                    item.setdefault("date_start", "")
                    item.setdefault("date_end", "")
                    item.setdefault("date_list", "")
                    item.setdefault("spot_data_source", "")
                    item.setdefault("bar_data_source", "")
                    item.setdefault("trigger_source", "manual")
                    item.setdefault("schedule_id", "")
                    item.setdefault("schedule_title", "")
                    item.setdefault("progress_hint", "")
                    item.setdefault("progress_current", 0)
                    item.setdefault("progress_total", 0)
                    item.setdefault("post_verify", None)
                    item.setdefault("batch_ids", [])
                    _RUNS[rid] = item
                    _ORDER.append(rid)
    except Exception:
        pass


def _persist() -> None:
    _ensure_log_dir()
    lst = [_RUNS[i] for i in _ORDER if i in _RUNS]
    try:
        with open(_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(lst, f, ensure_ascii=False, indent=0)
    except Exception:
        pass


def init_history() -> None:
    with _LOCK:
        if not _RUNS:
            _load()


def list_jobs() -> List[Dict[str, str]]:
    return list(JOB_ITEMS)


def list_runs(limit: int = 100) -> List[Dict[str, Any]]:
    with _LOCK:
        items = [_RUNS[i] for i in reversed(_ORDER) if i in _RUNS]
    return items[: max(1, min(limit, _MAX_RUNS))]


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        return _RUNS.get(run_id)


def cancel_run(run_id: str) -> Dict[str, Any]:
    """终止运行中的子进程（用户手动停止）。"""
    with _LOCK:
        r = _RUNS.get(run_id)
        if not r:
            raise ValueError("记录不存在")
        if r.get("status") != "running":
            raise ValueError("任务未在运行中")
        r["status"] = "cancelled"
        r["error_message"] = "用户手动停止"
        proc = _ACTIVE_PROCS.get(run_id)
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        except Exception as e:
            logging.warning("cancel_run %s: %s", run_id, e)
    with _LOCK:
        r = _RUNS.get(run_id)
        if r:
            r["finished_at"] = datetime.now().isoformat(timespec="seconds")
            r["exit_code"] = -15
            _ACTIVE_PROCS.pop(run_id, None)
    _persist()
    return get_run(run_id) or {}


def _run_log_bytes(rec: Dict[str, Any]) -> int:
    """单条记录中日志文本占用的字节数（用于删除提示）。"""
    total = 0
    for key in ("stdout_tail", "stderr_tail", "last_errors_tail", "error_message"):
        val = rec.get(key)
        if val:
            total += len(str(val).encode("utf-8"))
    return total


def delete_run(run_id: str) -> Tuple[bool, int]:
    """
    删除执行记录及其全部实时输出（stdout_tail 等均在 sync_job_history.json 内）。
    返回 (是否成功, 释放的大约字节数)。
    """
    with _LOCK:
        if run_id not in _RUNS:
            return False, 0
        rec = _RUNS[run_id]
        if rec.get("status") == "running":
            raise ValueError("任务仍在运行，请先点「停止任务」再删除")
        freed = _run_log_bytes(rec)
        del _RUNS[run_id]
        try:
            _ORDER.remove(run_id)
        except ValueError:
            pass
        _ACTIVE_PROCS.pop(run_id, None)
    _persist()
    return True, freed


def delete_runs(run_ids: List[str]) -> Dict[str, Any]:
    """批量删除执行记录（含日志）。运行中的 id 会跳过。"""
    uniq = []
    seen = set()
    for rid in run_ids or []:
        s = str(rid).strip()
        if s and s not in seen:
            seen.add(s)
            uniq.append(s)
    removed = 0
    freed = 0
    skipped_running: List[str] = []
    not_found: List[str] = []
    with _LOCK:
        for rid in uniq:
            rec = _RUNS.get(rid)
            if not rec:
                not_found.append(rid)
                continue
            if rec.get("status") == "running":
                skipped_running.append(rid)
                continue
            freed += _run_log_bytes(rec)
            del _RUNS[rid]
            try:
                _ORDER.remove(rid)
            except ValueError:
                pass
            _ACTIVE_PROCS.pop(rid, None)
            removed += 1
    if removed:
        _persist()
    return {
        "removed": removed,
        "freed_bytes": freed,
        "skipped_running": skipped_running,
        "not_found": not_found,
        "history_bytes": history_file_bytes(),
    }


def delete_all_finished_runs() -> Dict[str, Any]:
    """删除所有非运行中记录。"""
    with _LOCK:
        ids = [rid for rid, rec in _RUNS.items() if rec.get("status") != "running"]
    return delete_runs(ids)


def prune_runs(keep_last: int = 50) -> Dict[str, Any]:
    """只保留最近 keep_last 条记录，其余（含日志）一并删除。"""
    keep = max(1, min(int(keep_last), _MAX_RUNS))
    removed = 0
    freed = 0
    with _LOCK:
        if len(_ORDER) <= keep:
            return {"removed": 0, "freed_bytes": 0, "remaining": len(_ORDER)}
        drop_ids = _ORDER[: len(_ORDER) - keep]
        for rid in drop_ids:
            rec = _RUNS.pop(rid, None)
            if rec:
                freed += _run_log_bytes(rec)
                removed += 1
            try:
                _ORDER.remove(rid)
            except ValueError:
                pass
    _persist()
    return {"removed": removed, "freed_bytes": freed, "remaining": keep}


def history_file_bytes() -> int:
    """当前历史文件大小（字节）。"""
    try:
        return os.path.getsize(_HISTORY_PATH) if os.path.isfile(_HISTORY_PATH) else 0
    except OSError:
        return 0


def retry_from_run(run_id: str) -> Dict[str, Any]:
    old = get_run(run_id)
    if not old:
        raise ValueError("记录不存在")
    return start_job(
        old["job_id"],
        date_mode=old.get("date_mode") or "default",
        date_start=old.get("date_start") or "",
        date_end=old.get("date_end") or "",
        date_list=old.get("date_list") or "",
        qfq_mode=old.get("qfq_mode") or "incremental",
        spot_data_source=old.get("spot_data_source") or "",
        bar_data_source=old.get("bar_data_source") or "",
        trigger_source="manual",
        schedule_id="",
        schedule_title="",
    )


def _mootdx_bars_cli_args(
    date_mode: str, date_start: str, date_end: str
) -> List[str]:
    """mootdx_bars_sync_job 使用 --from-date/--to-date，与按日作业的位置参数不同。"""
    import datetime

    import instock.lib.trade_time as trd

    dm = (date_mode or "default").strip().lower()
    if dm == "default":
        today = datetime.date.today().isoformat()
        ds, _ = trd.get_trade_hist_interval(today)
        return ["--from-date", ds]
    if dm == "range":
        ds = (date_start or "").strip()
        de = (date_end or "").strip()
        if not ds:
            raise ValueError("区间模式需要开始日期 YYYY-MM-DD（结束日期可选）")
        args = ["--from-date", ds]
        if de:
            args.extend(["--to-date", de])
        return args
    raise ValueError("K 线补数作业请使用「默认」或「区间」日期模式")


def _bar_data_source_env(bar_data_source: str) -> Dict[str, str]:
    from instock.core.data.profile import BAR_SOURCE_MOOTDX, normalize_bar_data_source

    source = normalize_bar_data_source(bar_data_source)
    env = {
        "INSTOCK_USE_DATA_REGISTRY": "1",
        "INSTOCK_BAR_MODE": "raw",
        "INSTOCK_BAR_DATA_SOURCE": source,
    }
    if source == BAR_SOURCE_MOOTDX:
        env["INSTOCK_BARS_MOOTDX_ONLY"] = "1"
    return env


def _build_command(
    job_id: str,
    date_mode: str,
    date_start: str,
    date_end: str,
    date_list: str,
    qfq_mode: str = "incremental",
) -> List[str]:
    job = next((j for j in JOB_ITEMS if j["id"] == job_id), None)
    if not job:
        raise ValueError("未知 job_id")
    script_path = os.path.join(_REPO_ROOT, "instock", "job", job["script"])
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"找不到脚本: {script_path}")
    cmd = [sys.executable, script_path]
    if job_id in (
        "init_job",
        "sync_trade_calendar_job",
        "sync_stock_universe_job",
        "ingest_tdx_gbbq_job",
    ):
        return cmd
    if job_id == "derive_qfq_from_tdx_job":
        cmd.extend(["--mode", normalize_qfq_mode(qfq_mode)])
        return cmd
    if job_id == "sync_tdx_local_pipeline_job":
        cmd.extend(["--qfq-mode", normalize_qfq_mode(qfq_mode)])
        return cmd
    canon_src = (job.get("canonical_source") or "").strip()
    if canon_src:
        cmd.extend(["--source", canon_src])
        cmd.extend(_mootdx_bars_cli_args(date_mode, date_start, date_end))
        if canon_src == "akshare":
            cmd.extend(["--workers", "2", "--sleep", "0.35"])
        elif canon_src == "mootdx_local":
            cmd.extend(["--workers", "1", "--sleep", "0.02"])
        return cmd
    if job_id == "mootdx_bars_sync_job":
        cmd.extend(_mootdx_bars_cli_args(date_mode, date_start, date_end))
        return cmd
    dm = (date_mode or "default").strip().lower()
    if dm == "default":
        return cmd
    if dm == "list":
        dl = (date_list or "").strip()
        if not dl:
            raise ValueError("枚举日期不能为空，格式：2024-01-02,2024-01-05")
        cmd.append(dl)
        return cmd
    if dm == "range":
        ds = (date_start or "").strip()
        de = (date_end or "").strip()
        if not ds or not de:
            raise ValueError("区间模式需要开始、结束日期 YYYY-MM-DD")
        cmd.extend([ds, de])
        return cmd
    raise ValueError("date_mode 只能是 default、list、range")


def _worker(run_id: str) -> None:
    run = _RUNS.get(run_id)
    if not run:
        return
    env = os.environ.copy()
    env["PYTHONPATH"] = _REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env["PYTHONUNBUFFERED"] = "1"
    if run.get("job_id") == "basic_data_daily_job":
        from instock.core.spot_source import (
            SPOT_SOURCE_AUTO,
            normalize_spot_source,
        )

        spot = normalize_spot_source(run.get("spot_data_source") or "")
        env["INSTOCK_SPOT_DATA_SOURCE"] = spot
        if spot == SPOT_SOURCE_AUTO:
            env["INSTOCK_USE_DATA_REGISTRY"] = "1"
        env.setdefault("INSTOCK_QUALITY_STRICT", "1")
        env.setdefault("INSTOCK_MAX_CONSECUTIVE_FETCH_FAIL", "5")
    elif run.get("job_id") == "mootdx_bars_sync_job":
        env.update(_bar_data_source_env(run.get("bar_data_source") or "auto"))
    elif (run.get("job_id") or "").startswith("sync_bars_"):
        env["INSTOCK_USE_DATA_REGISTRY"] = "0"
    extra = run.get("extra_env") or {}
    if isinstance(extra, dict):
        for k, v in extra.items():
            if k and v is not None:
                env[str(k)] = str(v)
        try:
            from instock.core.sync_preferences import read_prefs

            push2 = (read_prefs().get("eastmoney_push2_host") or "").strip()
            if push2 and push2 not in ("", "auto"):
                env["INSTOCK_EM_PUSH2_HOST"] = push2
        except Exception:
            pass
    cmd = list(run["command"])
    if cmd and cmd[0] == sys.executable and (len(cmd) < 2 or cmd[1] != "-u"):
        cmd.insert(1, "-u")
    proc = None
    merged_out = ""
    code = -1
    last_persist = 0.0
    start_exc: Optional[Exception] = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=_REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        with _LOCK:
            _ACTIVE_PROCS[run_id] = proc
        assert proc.stdout is not None
        while True:
            with _LOCK:
                if _RUNS.get(run_id, {}).get("status") == "cancelled":
                    break
            line = proc.stdout.readline()
            if not line:
                break
            merged_out += line
            if len(merged_out) > 8_000_000:
                merged_out = merged_out[-6_000_000:]
            now = time.time()
            nbytes, nlines, err_cnt, err_tail, prog_hint, prog_cur, prog_tot = _progress_meta(
                merged_out
            )
            with _LOCK:
                r = _RUNS.get(run_id)
                if r:
                    r["stdout_tail"] = _truncate(merged_out)
                    r["progress_bytes"] = nbytes
                    r["progress_lines"] = nlines
                    r["error_line_count"] = err_cnt
                    r["last_errors_tail"] = err_tail[-6000:] if err_tail else ""
                    r["progress_hint"] = prog_hint
                    r["progress_current"] = prog_cur
                    r["progress_total"] = prog_tot
            if now - last_persist > 0.5:
                last_persist = now
                _persist()
        code = proc.wait()
        if code is None:
            code = -1
    except Exception as e:
        start_exc = e
        merged_out += "\n[exception] " + str(e)
        code = -1
    finally:
        with _LOCK:
            _ACTIVE_PROCS.pop(run_id, None)
    mo = merged_out or ""
    nbytes, nlines, err_cnt, err_tail, prog_hint, prog_cur, prog_tot = _progress_meta(mo)
    has_fail_markers = "[FAIL]" in mo
    with _LOCK:
        r = _RUNS.get(run_id)
        if r:
            if r.get("status") == "cancelled":
                r["stdout_tail"] = _truncate(mo)
                _persist()
                return
            r["finished_at"] = datetime.now().isoformat(timespec="seconds")
            r["exit_code"] = code
            r["stdout_tail"] = _truncate(mo)
            r["stderr_tail"] = ""
            r["progress_bytes"] = nbytes
            r["progress_lines"] = nlines
            r["error_line_count"] = err_cnt
            r["last_errors_tail"] = (err_tail[-6000:] if err_tail else "")
            r["progress_hint"] = prog_hint
            r["progress_current"] = prog_cur
            r["progress_total"] = prog_tot

            status = "success" if code == 0 and not has_fail_markers else "failed"
            post_verify = None
            if (
                status == "success"
                and r.get("job_id") == "basic_data_daily_job"
                and (r.get("date_mode") or "").lower() == "list"
                and (r.get("date_list") or "").strip()
            ):
                post_verify = _verify_spot_dates_after_run(r.get("date_list") or "")
                r["post_verify"] = post_verify
                still = post_verify.get("still_missing") or []
                if still:
                    status = "failed"
                    r["error_message"] = (
                        f"进程已结束但仍有 {len(still)} 个交易日主表无数据："
                        + ", ".join(still[:15])
                        + ("…" if len(still) > 15 else "")
                    )
            r["status"] = status
            if status == "success":
                r["batch_ids"] = _collect_batch_ids_for_job(r.get("job_id") or "")

            if proc is None and start_exc is not None:
                r["error_message"] = str(start_exc)
            elif proc is None:
                r["error_message"] = "进程启动失败"
            elif code != 0 or has_fail_markers:
                hint = r.get("last_errors_tail") or ""
                if not hint.strip():
                    tail_lines = mo.split("\n")[-25:]
                    hint = "\n".join(tail_lines)
                if not r.get("error_message"):
                    r["error_message"] = (
                        hint.strip()[:4000] if hint.strip() else "任务失败，请查看完整输出"
                    )
            elif status == "success" and not r.get("error_message"):
                r["error_message"] = None
            if status == "success" and r.get("job_id") == "sync_bars_mootdx_local_job":
                _maybe_auto_derive_qfq(r)
    _persist()


def _maybe_auto_derive_qfq(run: Dict[str, Any]) -> None:
    """raw 本地补数成功后，按配置自动接续 qfq 派生。"""
    if os.environ.get("INSTOCK_AUTO_DERIVE_QFQ", "1").strip().lower() in (
        "0",
        "false",
        "no",
        "off",
    ):
        return
    try:
        from instock.core.adjustment.corporate_action_store import qfq_table_has_rows
        from instock.core.adjustment.derive import run_derive
        from instock.core.adjustment.gbbq_reader import gbbq_factor_version
        from instock.core.adjustment.corporate_action_store import get_stored_factor_version

        mode = "incremental"
        cur = gbbq_factor_version()
        stored = get_stored_factor_version()
        if cur and cur != stored:
            from instock.core.adjustment.corporate_action_store import ingest_gbbq_to_db

            ingest_gbbq_to_db()
            mode = "full"
        elif not qfq_table_has_rows():
            run["qfq_auto_skip"] = "qfq 表为空，请手动运行 derive_qfq_from_tdx_job --mode full"
            return

        def _log(msg: str) -> None:
            tail = (run.get("stdout_tail") or "") + f"\n[qfq-auto] {msg}\n"
            run["stdout_tail"] = _truncate(tail)

        r = run_derive(mode=mode, skip_ingest=True, log=_log)
        run["qfq_auto_result"] = r
    except Exception as e:
        run["qfq_auto_error"] = str(e)[:500]


def start_job(
    job_id: str,
    date_mode: str = "default",
    date_start: str = "",
    date_end: str = "",
    date_list: str = "",
    qfq_mode: str = "incremental",
    spot_data_source: str = "",
    bar_data_source: str = "",
    trigger_source: str = "manual",
    schedule_id: str = "",
    schedule_title: str = "",
    extra_env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    qfq_saved = normalize_qfq_mode(qfq_mode) if job_id in QFQ_MODE_JOB_IDS else ""
    cmd = _build_command(job_id, date_mode, date_start, date_end, date_list, qfq_mode=qfq_saved or "incremental")
    run_id = str(uuid.uuid4())
    label = next((j["title"] for j in JOB_ITEMS if j["id"] == job_id), job_id)
    spot_saved = ""
    if job_id == "basic_data_daily_job":
        from instock.core.spot_source import SPOT_SOURCE_EASTMONEY, normalize_spot_source

        spot_saved = normalize_spot_source(spot_data_source or SPOT_SOURCE_EASTMONEY)
    bar_saved = ""
    if job_id == "mootdx_bars_sync_job":
        from instock.core.data.profile import normalize_bar_data_source

        bar_saved = normalize_bar_data_source(bar_data_source)
    rec: Dict[str, Any] = {
        "id": run_id,
        "job_id": job_id,
        "label": label,
        "status": "running",
        "exit_code": None,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": None,
        "command": cmd,
        "date_mode": date_mode,
        "date_start": date_start,
        "date_end": date_end,
        "date_list": date_list,
        "qfq_mode": qfq_saved,
        "spot_data_source": spot_saved,
        "bar_data_source": bar_saved,
        "trigger_source": (trigger_source or "manual").strip() or "manual",
        "schedule_id": (schedule_id or "").strip(),
        "schedule_title": (schedule_title or "").strip()[:200],
        "stdout_tail": "",
        "stderr_tail": "",
        "error_message": None,
        "progress_bytes": 0,
        "progress_lines": 0,
        "error_line_count": 0,
        "last_errors_tail": "",
        "progress_hint": "",
        "progress_current": 0,
        "progress_total": 0,
        "post_verify": None,
        "batch_ids": [],
        "extra_env": dict(extra_env or {}),
    }
    with _LOCK:
        _RUNS[run_id] = rec
        _ORDER.append(run_id)
        while len(_ORDER) > _MAX_RUNS:
            old = _ORDER.pop(0)
            _RUNS.pop(old, None)
    _persist()
    t = threading.Thread(target=_worker, args=(run_id,), daemon=True)
    t.start()
    return rec
