#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""东财 push2 连通性探测：后台线程执行，避免阻塞 Tornado 主线程。"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_PROBES: Dict[str, "ProbeState"] = {}
_MAX_PROBES = 32
_MAX_LOG_LINES = 300


@dataclass
class ProbeState:
    probe_id: str
    status: str = "running"  # running | success | failed | cancelled
    logs: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    cancelled: bool = False


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _append_log(state: ProbeState, msg: str) -> None:
    line = f"[{_ts()}] {msg}"
    with _LOCK:
        state.logs.append(line)
        if len(state.logs) > _MAX_LOG_LINES:
            state.logs = state.logs[-_MAX_LOG_LINES :]


def _run_probe_worker(state: ProbeState, preference: str) -> None:
    from instock.core.eastmoney_push2 import probe_push2_clist, probe_xuangu_selection
    from instock.web import sync_job_service as syncsvc

    try:
        cookie_info = syncsvc.read_eastmoney_cookie()
        cookie_ok = bool(cookie_info.get("exists") and (cookie_info.get("bytes") or 0) > 0)
        _append_log(
            state,
            f"push2 偏好={preference}（快照 clist；与「同步与快照偏好」一致）",
        )
        _append_log(
            state,
            f"Cookie 文件={cookie_info.get('path', '')} "
            f"({'已配置 ' + str(cookie_info.get('bytes', 0)) + ' 字节' if cookie_ok else '未配置'})；"
            "选股 xuangu 通常无需 Cookie",
        )

        def log_cb(msg: str) -> None:
            if state.cancelled:
                raise RuntimeError("探测已取消")
            _append_log(state, msg)

        xuangu = probe_xuangu_selection(log=log_cb)
        result = probe_push2_clist(preference, log=log_cb)
        result["xuangu_ok"] = bool(xuangu.get("ok"))
        result["xuangu_rows"] = xuangu.get("rows", 0)
        result["xuangu_total"] = xuangu.get("total", 0)
        if xuangu.get("ok") and not result.get("ok"):
            result["hint"] = (
                "push2 快照不可用，但综合选股 xuangu 可用；"
                "可运行「综合选股」作业；快照请改 Baostock 或 auto"
            )
        with _LOCK:
            state.result = result
            if state.cancelled:
                state.status = "cancelled"
            elif result.get("ok") or xuangu.get("ok"):
                state.status = "success"
            else:
                state.status = "failed"
            state.finished_at = time.time()
    except Exception as e:
        if str(e) == "探测已取消":
            with _LOCK:
                state.status = "cancelled"
                state.finished_at = time.time()
            return
        _append_log(state, f"探测异常: {e}")
        with _LOCK:
            state.result = {"ok": False, "error": str(e)}
            state.status = "failed"
            state.finished_at = time.time()


def start_probe(preference: Optional[str] = None) -> str:
    from instock.core.eastmoney_push2 import read_push2_host_preference

    pref = preference or read_push2_host_preference()
    probe_id = str(uuid.uuid4())
    state = ProbeState(probe_id=probe_id)
    with _LOCK:
        if len(_PROBES) >= _MAX_PROBES:
            oldest = min(_PROBES.values(), key=lambda s: s.started_at)
            _PROBES.pop(oldest.probe_id, None)
        _PROBES[probe_id] = state
    t = threading.Thread(
        target=_run_probe_worker,
        args=(state, pref),
        name=f"eastmoney-probe-{probe_id[:8]}",
        daemon=True,
    )
    t.start()
    return probe_id


def get_probe(probe_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        state = _PROBES.get(probe_id)
        if not state:
            return None
        return {
            "probe_id": state.probe_id,
            "status": state.status,
            "logs": list(state.logs),
            "log_count": len(state.logs),
            "result": state.result,
            "done": state.status != "running",
            "elapsed_ms": int(
                ((state.finished_at or time.time()) - state.started_at) * 1000
            ),
        }


def cancel_probe(probe_id: str) -> bool:
    with _LOCK:
        state = _PROBES.get(probe_id)
        if not state or state.status != "running":
            return False
        state.cancelled = True
        return True
