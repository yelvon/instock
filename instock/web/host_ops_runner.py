#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宿主机脚本执行（通达信同步、docker_dev_reload 等），供 host_ops_server 与容器内 API 复用。"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_HISTORY_PATH = os.path.join(_REPO_ROOT, "instock", "log", "host_ops_history.json")
_LOCK = threading.Lock()
_RUNS: Dict[str, Dict[str, Any]] = {}
_ORDER: List[str] = []
_ACTIVE: Dict[str, subprocess.Popen] = {}
_MAX_RUNS = 50
_MAX_TAIL = 2_000_000

TASK_DEFS: Dict[str, Dict[str, Any]] = {
    "tdx_sync": {
        "title": "同步通达信 vipdoc → ~/tdx-local",
        "script": "scripts/trigger_tdx_sync_from_mac.sh",
        "cwd": _REPO_ROOT,
    },
    "docker_dev_reload": {
        "title": "重建 InStock 容器（docker_dev_reload）",
        "script": "scripts/docker_dev_reload.sh",
        "cwd": _REPO_ROOT,
    },
}


def repo_root() -> str:
    return _REPO_ROOT


def is_inside_docker() -> bool:
    return os.path.isfile("/.dockerenv")


def _truncate(s: str, limit: int = _MAX_TAIL) -> str:
    if len(s) <= limit:
        return s
    return s[-limit:]


def _persist() -> None:
    try:
        d = os.path.dirname(_HISTORY_PATH)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(_HISTORY_PATH, "w", encoding="utf-8") as f:
            ids = _ORDER[-_MAX_RUNS:]
            json.dump([_RUNS[i] for i in ids if i in _RUNS], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def init_history() -> None:
    with _LOCK:
        if _RUNS:
            return
        if not os.path.isfile(_HISTORY_PATH):
            return
        try:
            with open(_HISTORY_PATH, encoding="utf-8", errors="replace") as f:
                rows = json.load(f)
            if not isinstance(rows, list):
                return
            for r in rows:
                rid = r.get("id")
                if rid:
                    _RUNS[rid] = r
                    _ORDER.append(rid)
        except Exception:
            pass


def list_tasks() -> List[Dict[str, Any]]:
    return [
        {
            "id": k,
            "title": v["title"],
            "script": v["script"],
        }
        for k, v in TASK_DEFS.items()
    ]


def list_runs(limit: int = 30) -> List[Dict[str, Any]]:
    init_history()
    with _LOCK:
        ids = list(reversed(_ORDER[-limit:]))
        return [_summarize(_RUNS[i]) for i in ids if i in _RUNS]


def _summarize(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": r.get("id"),
        "task_id": r.get("task_id"),
        "title": r.get("title"),
        "status": r.get("status"),
        "created_at": r.get("created_at"),
        "finished_at": r.get("finished_at"),
        "exit_code": r.get("exit_code"),
        "progress_hint": r.get("progress_hint"),
    }


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    init_history()
    with _LOCK:
        r = _RUNS.get(run_id)
        return dict(r) if r else None


def _build_command(task_id: str, options: Optional[Dict[str, Any]]) -> List[str]:
    if task_id not in TASK_DEFS:
        raise ValueError(f"未知任务: {task_id}")
    script = os.path.join(_REPO_ROOT, TASK_DEFS[task_id]["script"])
    if not os.path.isfile(script):
        raise FileNotFoundError(f"脚本不存在: {script}")
    cmd = ["/bin/bash", script]
    opts = options or {}
    if task_id == "docker_dev_reload":
        if opts.get("quick"):
            cmd.append("--quick")
        if opts.get("skip_npm"):
            cmd.append("--skip-npm")
        if opts.get("pip"):
            cmd.append("--pip")
    return cmd


def start_task(task_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    init_history()
    tdef = TASK_DEFS.get(task_id)
    if not tdef:
        raise ValueError(f"未知任务: {task_id}")
    with _LOCK:
        for rid, r in _RUNS.items():
            if r.get("task_id") == task_id and r.get("status") == "running":
                raise RuntimeError(f"任务「{tdef['title']}」仍在运行中（id={rid}）")

    cmd = _build_command(task_id, options)
    run_id = str(uuid.uuid4())
    rec = {
        "id": run_id,
        "task_id": task_id,
        "title": tdef["title"],
        "command": cmd,
        "options": options or {},
        "status": "running",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": None,
        "exit_code": None,
        "stdout_tail": "",
        "progress_hint": "启动中…",
    }
    with _LOCK:
        _RUNS[run_id] = rec
        _ORDER.append(run_id)
        if len(_ORDER) > _MAX_RUNS:
            old = _ORDER.pop(0)
            _RUNS.pop(old, None)
    _persist()
    t = threading.Thread(
        target=_execute, args=(run_id, task_id, cmd, tdef["cwd"]), daemon=True
    )
    t.start()
    return _summarize(rec)


def cancel_run(run_id: str) -> bool:
    with _LOCK:
        r = _RUNS.get(run_id)
        if not r or r.get("status") != "running":
            return False
        r["status"] = "cancelled"
        proc = _ACTIVE.get(run_id)
    if proc and proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass
    _persist()
    return True


def _stream_encoding(task_id: str) -> str:
    """通达信同步经 Windows/prlctl，日志多为 GBK。"""
    if task_id == "tdx_sync":
        return "gbk"
    return "utf-8"


def _execute(run_id: str, task_id: str, cmd: List[str], cwd: str) -> None:
    merged = ""
    code = -1
    proc = None
    last_persist = 0.0
    enc = _stream_encoding(task_id)
    env = os.environ.copy()
    env.setdefault("LANG", "en_US.UTF-8")
    env.setdefault("LC_ALL", "en_US.UTF-8")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding=enc,
            errors="replace",
            bufsize=1,
        )
        with _LOCK:
            _ACTIVE[run_id] = proc
        assert proc.stdout is not None
        while True:
            with _LOCK:
                if _RUNS.get(run_id, {}).get("status") == "cancelled":
                    break
            try:
                line = proc.stdout.readline()
            except UnicodeDecodeError:
                continue
            if not line:
                break
            merged += line
            if len(merged) > _MAX_TAIL:
                merged = merged[-_MAX_TAIL:]
            hint = line.strip()[:200] if line.strip() else ""
            now = time.time()
            with _LOCK:
                r = _RUNS.get(run_id)
                if r:
                    r["stdout_tail"] = _truncate(merged)
                    if hint.startswith("==>"):
                        r["progress_hint"] = hint
            if now - last_persist > 0.5:
                last_persist = now
                _persist()
        code = proc.wait()
    except Exception as e:
        merged += f"\n[exception] {e}\n"
        code = -1
    finally:
        with _LOCK:
            _ACTIVE.pop(run_id, None)
            r = _RUNS.get(run_id)
            if not r:
                return
            if r.get("status") == "cancelled":
                r["stdout_tail"] = _truncate(merged)
                r["finished_at"] = datetime.now().isoformat(timespec="seconds")
                _persist()
                return
            r["finished_at"] = datetime.now().isoformat(timespec="seconds")
            r["exit_code"] = code
            r["stdout_tail"] = _truncate(merged)
            r["status"] = "success" if code == 0 else "failed"
            if r["status"] == "success":
                r["progress_hint"] = "完成"
            else:
                r["progress_hint"] = f"退出码 {code}"
    _persist()


def host_ops_reachable(base_url: str, timeout: float = 2.0) -> bool:
    import urllib.error
    import urllib.request

    url = (base_url or "").rstrip("/") + "/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False
