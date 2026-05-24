#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mac 宿主机运维 API（仅标准库）：供 Docker 内 Web 触发 docker_dev_reload、通达信同步等。

在 Mac 终端启动（开发时保持运行）：
  cd /path/to/instock
  python3 scripts/host_ops_server.py

默认 http://127.0.0.1:19888 ；容器通过 INSTOCK_HOST_OPS_URL=http://host.docker.internal:19888 访问。
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

cpath = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, cpath)

import instock.web.host_ops_runner as hor  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json;charset=UTF-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[host_ops] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self) -> None:
        hor.init_history()
        u = urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        qs = parse_qs(u.query)

        if path == "/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "host_ops",
                    "repo": hor.repo_root(),
                    "inside_docker": hor.is_inside_docker(),
                    "runner_version": 2,
                },
            )
            return
        if path == "/tasks":
            self._send_json(200, {"ok": True, "tasks": hor.list_tasks()})
            return
        if path == "/runs":
            try:
                limit = int((qs.get("limit") or ["30"])[0])
            except ValueError:
                limit = 30
            self._send_json(200, {"ok": True, "runs": hor.list_runs(limit)})
            return
        if path == "/run":
            run_id = (qs.get("id") or [""])[0].strip()
            if not run_id:
                self._send_json(400, {"ok": False, "error": "缺少 id"})
                return
            r = hor.get_run(run_id)
            if not r:
                self._send_json(404, {"ok": False, "error": "记录不存在"})
                return
            self._send_json(200, {"ok": True, "run": r})
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        hor.init_history()
        u = urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        n = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "error": "JSON 无效"})
            return

        if path == "/runs":
            task_id = (body.get("task_id") or "").strip()
            if not task_id:
                self._send_json(400, {"ok": False, "error": "缺少 task_id"})
                return
            try:
                run = hor.start_task(task_id, body.get("options") or {})
                self._send_json(200, {"ok": True, "run": run})
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return
        if path == "/cancel":
            run_id = (body.get("id") or "").strip()
            if not run_id:
                self._send_json(400, {"ok": False, "error": "缺少 id"})
                return
            ok = hor.cancel_run(run_id)
            self._send_json(200, {"ok": ok})
            return
        self._send_json(404, {"ok": False, "error": "not found"})


def _port_in_use(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def _existing_server_ok(port: int) -> bool:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as resp:
            if resp.status != 200:
                return False
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("service") == "host_ops"
    except Exception:
        return False


def main() -> None:
    port = int(os.environ.get("INSTOCK_HOST_OPS_PORT", "19888"))
    if _port_in_use(port):
        if _existing_server_ok(port):
            print(
                f"host_ops_server 已在运行: http://127.0.0.1:{port}\n"
                "无需重复启动。若要加载新代码，请先结束旧进程，例如：\n"
                f"  lsof -nP -iTCP:{port} -sTCP:LISTEN\n"
                f"  kill <PID>",
                flush=True,
            )
            return
        print(
            f"端口 {port} 已被占用，且不是 host_ops 服务。\n"
            f"请检查: lsof -nP -iTCP:{port} -sTCP:LISTEN",
            flush=True,
        )
        raise SystemExit(1)

    class ReuseHTTPServer(HTTPServer):
        allow_reuse_address = True

    server = ReuseHTTPServer(("127.0.0.1", port), Handler)
    print(f"host_ops_server listening on http://127.0.0.1:{port}", flush=True)
    print(f"REPO={hor.repo_root()}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
