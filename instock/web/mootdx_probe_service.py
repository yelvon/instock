#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mootdx 连通性探测（后台线程 + 实时日志）。"""

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
_MAX_LOG_LINES = 400


@dataclass
class ProbeState:
    probe_id: str
    mode: str
    status: str = "running"
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


def _probe_local(state: ProbeState, log) -> Dict[str, Any]:
    from instock.core.data.profile import tdx_dir
    from instock.core.data.providers.mootdx_local import Provider
    from instock.core.mootdx_universe import count_universe, fetch_universe_from_tdx_dir

    d = tdx_dir()
    log(f"INSTOCK_TDX_DIR={d or '（未配置）'}")
    if not d:
        return {"ok": False, "error": "未配置 INSTOCK_TDX_DIR"}
    prov = Provider()
    log("healthcheck（样本 600000 日线）…")
    t0 = time.time()
    hc = prov.healthcheck()
    log(f"  healthcheck={'通过' if hc else '失败'} ({int((time.time()-t0)*1000)}ms)")
    if not hc:
        return {"ok": False, "error": "mootdx_local healthcheck 失败"}
    log("fetch_bars 600000 from=20240101 …")
    t0 = time.time()
    res = prov.fetch_bars("600000", "20240101", adjust="raw")
    rows = len(res.data) if res.ok and res.data is not None else 0
    log(f"  K 线样本 rows={rows} ({int((time.time()-t0)*1000)}ms)")
    if not res.ok:
        return {"ok": False, "error": res.error or "fetch_bars 失败"}
    log("扫描 vipdoc 统计本地代码数（不写入库）…")
    df = fetch_universe_from_tdx_dir(d, log=log)
    log(f"  扫描得到 A 股约 {len(df)} 只；库中 cn_stock_universe={count_universe()} 条")
    return {
        "ok": True,
        "provider_id": "mootdx_local",
        "rows": rows,
        "universe_scan": len(df),
        "tdx_dir": d,
    }


def _probe_online(state: ProbeState, log) -> Dict[str, Any]:
    from instock.core.data.providers.mootdx_online import Provider
    from instock.core.mootdx_universe import count_universe, fetch_universe_mootdx_online

    prov = Provider()
    log("healthcheck（在线 bars 600000）…")
    t0 = time.time()
    hc = prov.healthcheck()
    log(f"  healthcheck={'通过' if hc else '失败'} ({int((time.time()-t0)*1000)}ms)")
    if not hc:
        return {"ok": False, "error": "mootdx_online healthcheck 失败"}
    log("fetch_bars 600000 …")
    t0 = time.time()
    res = prov.fetch_bars("600000", "20240101", adjust="raw")
    rows = len(res.data) if res.ok and res.data is not None else 0
    log(f"  K 线 rows={rows} ({int((time.time()-t0)*1000)}ms)")
    if not res.ok:
        return {"ok": False, "error": res.error or "fetch_bars 失败"}
    log("拉取在线证券列表（仅统计，约需数秒）…")
    t0 = time.time()
    try:
        df = fetch_universe_mootdx_online(log=log)
        log(f"  在线列表 A 股 {len(df)} 条 ({int((time.time()-t0)*1000)}ms)")
    except Exception as e:
        log(f"  列表拉取失败: {e}")
        return {"ok": False, "error": str(e), "rows": rows}
    log(f"库中 cn_stock_universe={count_universe()} 条（需手动作业「同步证券主表」写入）")
    return {
        "ok": True,
        "provider_id": "mootdx_online",
        "rows": rows,
        "universe_online": len(df),
    }


def _run_worker(state: ProbeState) -> None:
    mode = state.mode

    def log(msg: str) -> None:
        if state.cancelled:
            raise RuntimeError("探测已取消")
        _append_log(state, msg)

    try:
        log(f"模式={mode}（auto=先本地后在线）")
        result: Dict[str, Any] = {"ok": False}
        if mode == "local":
            result = _probe_local(state, log)
        elif mode == "online":
            result = _probe_online(state, log)
        else:
            log("--- 尝试 mootdx_local ---")
            try:
                result = _probe_local(state, log)
                if result.get("ok"):
                    result["mode"] = "auto→local"
            except Exception as e:
                log(f"local 异常: {e}")
                result = {"ok": False, "error": str(e)}
            if not result.get("ok"):
                log("--- 回退 mootdx_online ---")
                result = _probe_online(state, log)
                if result.get("ok"):
                    result["mode"] = "auto→online"
        with _LOCK:
            state.result = result
            if state.cancelled:
                state.status = "cancelled"
            elif result.get("ok"):
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
        _append_log(state, f"异常: {e}")
        with _LOCK:
            state.result = {"ok": False, "error": str(e)}
            state.status = "failed"
            state.finished_at = time.time()


def start_probe(mode: str = "auto") -> str:
    m = (mode or "auto").strip().lower()
    if m not in ("auto", "local", "online"):
        m = "auto"
    probe_id = str(uuid.uuid4())
    state = ProbeState(probe_id=probe_id, mode=m)
    with _LOCK:
        if len(_PROBES) >= _MAX_PROBES:
            oldest = min(_PROBES.values(), key=lambda s: s.started_at)
            _PROBES.pop(oldest.probe_id, None)
        _PROBES[probe_id] = state
    threading.Thread(
        target=_run_worker,
        args=(state,),
        name=f"mootdx-probe-{probe_id[:8]}",
        daemon=True,
    ).start()
    return probe_id


def get_probe(probe_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        state = _PROBES.get(probe_id)
        if not state:
            return None
        return {
            "probe_id": state.probe_id,
            "mode": state.mode,
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
