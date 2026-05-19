#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from abc import ABC

import instock.web.base as webBase
import instock.web.backtest_service as svc


class BacktestRunsApiHandler(webBase.BaseHandler, ABC):
    def get(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            limit = int(self.get_argument("limit", "80"))
        except ValueError:
            limit = 80
        self.write(json.dumps({"ok": True, "items": svc.list_runs(limit)}, ensure_ascii=False))

    def post(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        try:
            run = svc.start_run(body)
            self.write(json.dumps({"ok": True, "id": run["id"], "status": run["status"], "run": run}, ensure_ascii=False))
        except svc.BacktestDataGapError as e:
            self.set_status(400)
            self.write(
                json.dumps(
                    {
                        "ok": False,
                        "error": "BACKTEST_DATA_GAP",
                        "message": "回测主数据缺失",
                        "prerequisites": e.report,
                    },
                    ensure_ascii=False,
                )
            )
        except Exception as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class BacktestRunDetailApiHandler(webBase.BaseHandler, ABC):
    def get(self, run_id: str):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        run = svc.get_run(run_id)
        if not run:
            self.set_status(404)
            self.write(json.dumps({"ok": False, "error": "回测任务不存在"}, ensure_ascii=False))
            return
        out = dict(run)
        out["ok"] = True
        self.write(json.dumps(out, ensure_ascii=False))

    def delete(self, run_id: str):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        res = svc.delete_run(run_id)
        self.write(json.dumps({"ok": True, **res}, ensure_ascii=False))


class BacktestRunCancelApiHandler(webBase.BaseHandler, ABC):
    def post(self, run_id: str):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            run = svc.cancel_run(run_id)
            self.write(json.dumps({"ok": True, "id": run_id, "status": run["status"], "run": run}, ensure_ascii=False))
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
