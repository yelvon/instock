# -*- coding: utf-8 -*-
"""容器内 Web 调用宿主机 host_ops_server，或在宿主机直接执行。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

import instock.web.host_ops_runner as hor


def _host_ops_base_url() -> str:
    return (os.environ.get("INSTOCK_HOST_OPS_URL") or "").strip().rstrip("/")


def status() -> Dict[str, Any]:
    base = _host_ops_base_url()
    inside = hor.is_inside_docker()
    reachable = bool(base) and hor.host_ops_reachable(base)
    can_local = not inside
    runner_version = 0
    if reachable:
        try:
            j = _http_json("GET", "/health", timeout=3)
            runner_version = int(j.get("runner_version") or 0)
        except Exception:
            runner_version = 0
    return {
        "inside_docker": inside,
        "host_ops_url": base or None,
        "host_reachable": reachable,
        "can_run_local": can_local,
        "ready": reachable or can_local,
        "repo_root": hor.repo_root(),
        "start_hint": "python3 scripts/host_ops_server.py",
        "runner_version": runner_version,
    }


def _http_json(method: str, path: str, body: Optional[dict] = None, timeout: float = 30.0) -> dict:
    base = _host_ops_base_url()
    if not base:
        raise RuntimeError("未配置 INSTOCK_HOST_OPS_URL")
    url = base + path
    data = None
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"ok": False, "error": str(e)}
        payload["http_status"] = e.code
        return payload


def list_tasks() -> list:
    return hor.list_tasks()


def list_runs(limit: int = 30) -> list:
    st = status()
    if st["host_reachable"]:
        j = _http_json("GET", f"/runs?limit={int(limit)}", timeout=10)
        return j.get("runs") or []
    if st["can_run_local"]:
        return hor.list_runs(limit)
    return []


def get_run(run_id: str) -> Optional[dict]:
    st = status()
    if st["host_reachable"]:
        j = _http_json("GET", f"/run?id={run_id}", timeout=10)
        return j.get("run") if j.get("ok") else None
    if st["can_run_local"]:
        return hor.get_run(run_id)
    return None


def start_task(task_id: str, options: Optional[Dict[str, Any]] = None) -> dict:
    st = status()
    if not st["ready"]:
        raise RuntimeError(
            "宿主机运维未就绪：请在 Mac 终端执行 "
            f"cd {hor.repo_root()} && python3 scripts/host_ops_server.py"
        )
    if st["host_reachable"]:
        j = _http_json(
            "POST",
            "/runs",
            {"task_id": task_id, "options": options or {}},
            timeout=15,
        )
        if not j.get("ok"):
            raise RuntimeError(j.get("error") or "宿主机任务启动失败")
        return j.get("run") or {}
    return hor.start_task(task_id, options)


def cancel_run(run_id: str) -> bool:
    st = status()
    if st["host_reachable"]:
        j = _http_json("POST", "/cancel", {"id": run_id}, timeout=10)
        return bool(j.get("ok"))
    if st["can_run_local"]:
        return hor.cancel_run(run_id)
    return False
