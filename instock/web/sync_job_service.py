#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Web 触发的数据同步作业：子进程执行 instock/job 脚本，记录运行历史。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

_max_output_chars = 48000

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_HISTORY_PATH = os.path.join(_REPO_ROOT, "instock", "log", "sync_job_history.json")
_LOCK = threading.Lock()
_RUNS: Dict[str, Dict[str, Any]] = {}
_ORDER: List[str] = []
_MAX_RUNS = 200

JOB_ITEMS: List[Dict[str, str]] = [
    {"id": "execute_daily_job", "script": "execute_daily_job.py", "title": "整体日作业", "hint": "串联 init / 基础 / 综合选股 / 其它 / 盘后（见源码注释）"},
    {"id": "init_job", "script": "init_job.py", "title": "初始化数据库", "hint": "仅创建库与基础表；一般只需参数「默认（当前交易日逻辑）」"},
    {"id": "basic_data_daily_job", "script": "basic_data_daily_job.py", "title": "股票/ETF 快照", "hint": "cn_stock_spot、cn_etf_spot"},
    {"id": "selection_data_daily_job", "script": "selection_data_daily_job.py", "title": "综合选股", "hint": "cn_stock_selection"},
    {"id": "basic_data_other_daily_job", "script": "basic_data_other_daily_job.py", "title": "其它基础数据", "hint": "龙虎榜、资金流、分红、抢筹、涨停原因等"},
    {"id": "basic_data_after_close_daily_job", "script": "basic_data_after_close_daily_job.py", "title": "盘后数据", "hint": "大宗交易、尾盘抢筹"},
    {"id": "indicators_data_daily_job", "script": "indicators_data_daily_job.py", "title": "技术指标", "hint": "指标表 + 买卖信号表，耗时长"},
    {"id": "klinepattern_data_daily_job", "script": "klinepattern_data_daily_job.py", "title": "K 线形态", "hint": "cn_stock_pattern"},
    {"id": "strategy_data_daily_job", "script": "strategy_data_daily_job.py", "title": "策略选股", "hint": "各 cn_stock_strategy_* 表"},
    {"id": "backtest_data_daily_job", "script": "backtest_data_daily_job.py", "title": "信号事后收益统计", "hint": "依赖指标/策略已有数据"},
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
    with _LOCK:
        run = _RUNS.get(run_id)
    if not run:
        return
    env = os.environ.copy()
    env["PYTHONPATH"] = _REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    cmd = run["command"]
    proc = None
    out, err = "", ""
    code = -1
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=_REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,
        )
        out, err = proc.communicate()
        code = proc.returncode if proc.returncode is not None else -1
    except Exception as e:
        out, err = "", str(e)
        code = -1
    with _LOCK:
        r = _RUNS.get(run_id)
        if r:
            r["finished_at"] = datetime.now().isoformat(timespec="seconds")
            r["exit_code"] = code
            r["status"] = "success" if code == 0 else "failed"
            r["stdout_tail"] = _truncate(out or "")
            r["stderr_tail"] = _truncate(err or "")
            if proc is None:
                r["error_message"] = err or "进程启动失败"
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
        "stdout_tail": "",
        "stderr_tail": "",
        "error_message": None,
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
