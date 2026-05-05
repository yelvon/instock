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

_max_output_chars = 48000

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_HISTORY_PATH = os.path.join(_REPO_ROOT, "instock", "log", "sync_job_history.json")
_LOCK = threading.Lock()
_RUNS: Dict[str, Dict[str, Any]] = {}
_ORDER: List[str] = []
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
        "id": "basic_data_daily_job",
        "script": "basic_data_daily_job.py",
        "title": "股票/ETF 快照",
        "hint": "全市场当日报价快照",
        "description": "抓取当日 A 股全市场快照与 ETF 快照，写入 cn_stock_spot、cn_etf_spot，是多数模块的数据底座。盘中可多次更新；选择交易日日期运行。",
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
        "description": "一批扩展基础数据：龙虎榜统计、分红配送、个股/行业/概念资金流、早盘抢筹、涨停原因等（详见 jobs.md）。建议先有当日快照 cn_stock_spot 再跑，耗时可较长。",
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
]


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
    r"处理异常|Traceback|ERROR|Error:|Exception:|CRITICAL|致命|失败\[",
    re.IGNORECASE,
)


def _progress_meta(merged_out: str) -> Tuple[int, int, int, str]:
    """从子进程累计输出估算：字节数、行数、疑似报错行数、最近若干条报错相关行。"""
    if not merged_out:
        return 0, 0, 0, ""
    lines = merged_out.split("\n")
    nlines = len(lines)
    nbytes = len(merged_out.encode("utf-8"))
    hit_lines = [ln for ln in lines if _ERR_PAT.search(ln)]
    err_count = len(hit_lines)
    tail_err = "\n".join(hit_lines[-12:]) if hit_lines else ""
    return nbytes, nlines, err_count, tail_err


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


def delete_run(run_id: str) -> bool:
    with _LOCK:
        if run_id not in _RUNS:
            return False
        del _RUNS[run_id]
        try:
            _ORDER.remove(run_id)
        except ValueError:
            pass
    _persist()
    return True


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
    )


def _build_command(job_id: str, date_mode: str, date_start: str, date_end: str, date_list: str) -> List[str]:
    job = next((j for j in JOB_ITEMS if j["id"] == job_id), None)
    if not job:
        raise ValueError("未知 job_id")
    script_path = os.path.join(_REPO_ROOT, "instock", "job", job["script"])
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"找不到脚本: {script_path}")
    cmd = [sys.executable, script_path]
    if job_id == "init_job":
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
        assert proc.stdout is not None
        while True:
            chunk = proc.stdout.read(8192)
            if not chunk:
                break
            merged_out += chunk
            if len(merged_out) > 8_000_000:
                merged_out = merged_out[-6_000_000:]
            now = time.time()
            nbytes, nlines, err_cnt, err_tail = _progress_meta(merged_out)
            with _LOCK:
                r = _RUNS.get(run_id)
                if r:
                    r["stdout_tail"] = _truncate(merged_out)
                    r["progress_bytes"] = nbytes
                    r["progress_lines"] = nlines
                    r["error_line_count"] = err_cnt
                    r["last_errors_tail"] = err_tail[-6000:] if err_tail else ""
            if now - last_persist > 2.0:
                last_persist = now
                _persist()
        code = proc.wait()
        if code is None:
            code = -1
    except Exception as e:
        start_exc = e
        merged_out += "\n[exception] " + str(e)
        code = -1
    mo = merged_out or ""
    nbytes, nlines, err_cnt, err_tail = _progress_meta(mo)
    with _LOCK:
        r = _RUNS.get(run_id)
        if r:
            r["finished_at"] = datetime.now().isoformat(timespec="seconds")
            r["exit_code"] = code
            r["status"] = "success" if code == 0 else "failed"
            r["stdout_tail"] = _truncate(mo)
            r["stderr_tail"] = ""
            r["progress_bytes"] = nbytes
            r["progress_lines"] = nlines
            r["error_line_count"] = err_cnt
            r["last_errors_tail"] = (err_tail[-6000:] if err_tail else "")
            if proc is None and start_exc is not None:
                r["error_message"] = str(start_exc)
            elif proc is None:
                r["error_message"] = "进程启动失败"
            elif code != 0:
                hint = r.get("last_errors_tail") or ""
                if not hint.strip():
                    tail_lines = mo.split("\n")[-25:]
                    hint = "\n".join(tail_lines)
                r["error_message"] = (hint.strip()[:4000] if hint.strip() else "非零退出码，请查看完整输出")
            else:
                r["error_message"] = None
    _persist()


def start_job(
    job_id: str,
    date_mode: str = "default",
    date_start: str = "",
    date_end: str = "",
    date_list: str = "",
) -> Dict[str, Any]:
    cmd = _build_command(job_id, date_mode, date_start, date_end, date_list)
    run_id = str(uuid.uuid4())
    label = next((j["title"] for j in JOB_ITEMS if j["id"] == job_id), job_id)
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
        "stdout_tail": "",
        "stderr_tail": "",
        "error_message": None,
        "progress_bytes": 0,
        "progress_lines": 0,
        "error_line_count": 0,
        "last_errors_tail": "",
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
