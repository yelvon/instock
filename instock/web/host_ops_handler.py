#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from abc import ABC

import instock.web.base as webBase
import instock.web.host_ops_service as hos


class HostOpsStatusHandler(webBase.BaseHandler, ABC):
    def get(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        self.write(json.dumps({"ok": True, **hos.status()}, ensure_ascii=False))


class HostOpsTasksHandler(webBase.BaseHandler, ABC):
    def get(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        self.write(json.dumps({"ok": True, "tasks": hos.list_tasks()}, ensure_ascii=False))


class HostOpsRunsHandler(webBase.BaseHandler, ABC):
    def get(self):
        try:
            limit = int(self.get_argument("limit", "30"))
        except ValueError:
            limit = 30
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        self.write(json.dumps({"ok": True, "runs": hos.list_runs(limit)}, ensure_ascii=False))


class HostOpsRunDetailHandler(webBase.BaseHandler, ABC):
    def get(self):
        run_id = (self.get_argument("id", "") or "").strip()
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        if not run_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 id"}, ensure_ascii=False))
            return
        r = hos.get_run(run_id)
        if not r:
            self.set_status(404)
            self.write(json.dumps({"ok": False, "error": "记录不存在"}, ensure_ascii=False))
            return
        self.write(json.dumps({"ok": True, "run": r}, ensure_ascii=False))


class HostOpsTriggerHandler(webBase.BaseHandler, ABC):
    def post(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        task_id = (body.get("task_id") or "").strip()
        if not task_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 task_id"}, ensure_ascii=False))
            return
        try:
            run = hos.start_task(task_id, body.get("options") or {})
            self.write(json.dumps({"ok": True, "run": run}, ensure_ascii=False))
        except Exception as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class HostOpsCancelHandler(webBase.BaseHandler, ABC):
    def post(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        run_id = (body.get("id") or "").strip()
        if not run_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 id"}, ensure_ascii=False))
            return
        ok = hos.cancel_run(run_id)
        self.write(json.dumps({"ok": ok}, ensure_ascii=False))
