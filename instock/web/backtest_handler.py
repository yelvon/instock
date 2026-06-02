#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from abc import ABC

import instock.web.base as webBase
import instock.web.backtest_service as svc


class BacktestStrategiesApiHandler(webBase.BaseHandler, ABC):
    def get(self):
        svc.ensure_registry()
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        self.write(json.dumps({"ok": True, "strategies": svc.list_strategies()}, ensure_ascii=False))


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


class BacktestRunKlineApiHandler(webBase.BaseHandler, ABC):
    """GET ?code=600000 返回回测区间 K 线与成交买卖点。"""

    def get(self, run_id: str):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        code = (self.get_argument("code", "") or "").strip()
        period = (self.get_argument("period", "daily") or "daily").strip()
        if not code:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 code"}, ensure_ascii=False))
            return
        try:
            out = svc.get_run_kline_chart(run_id, code, period=period)
            self.write(json.dumps(out, ensure_ascii=False))
        except ValueError as e:
            self.set_status(404 if "不存在" in str(e) else 400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class BacktestRunCancelApiHandler(webBase.BaseHandler, ABC):
    def post(self, run_id: str):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            run = svc.cancel_run(run_id)
            self.write(json.dumps({"ok": True, "id": run_id, "status": run["status"], "run": run}, ensure_ascii=False))
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class BacktestGridApiHandler(webBase.BaseHandler, ABC):
    def post(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        try:
            batch = svc.start_grid_batch(body)
            self.write(json.dumps({"ok": True, "batchId": batch["id"], "batch": batch}, ensure_ascii=False))
        except Exception as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class BacktestWalkforwardApiHandler(webBase.BaseHandler, ABC):
    def post(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        try:
            batch = svc.start_walkforward_batch(body)
            self.write(json.dumps({"ok": True, "batchId": batch["id"], "batch": batch}, ensure_ascii=False))
        except Exception as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class BacktestBatchDetailApiHandler(webBase.BaseHandler, ABC):
    def get(self, batch_id: str):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        batch = svc.get_batch(batch_id)
        if not batch:
            self.set_status(404)
            self.write(json.dumps({"ok": False, "error": "批量任务不存在"}, ensure_ascii=False))
            return
        self.write(json.dumps({"ok": True, "batch": batch}, ensure_ascii=False))


class BacktestCompareApiHandler(webBase.BaseHandler, ABC):
    def get(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        ids_raw = self.get_argument("ids", "")
        run_ids = [x.strip() for x in ids_raw.split(",") if x.strip()]
        if not run_ids:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 ids"}, ensure_ascii=False))
            return
        self.write(json.dumps(svc.compare_runs(run_ids), ensure_ascii=False))


class BacktestRunExportApiHandler(webBase.BaseHandler, ABC):
    def get(self, run_id: str):
        fmt = (self.get_argument("format", "csv") or "csv").strip().lower()
        try:
            if fmt != "csv":
                raise ValueError("仅支持 format=csv")
            content = svc.export_run_csv(run_id)
            self.set_header("Content-Type", "text/csv; charset=utf-8")
            self.set_header(
                "Content-Disposition",
                f'attachment; filename="backtest_{run_id[:8]}.csv"',
            )
            self.write(content)
        except ValueError as e:
            self.set_status(404 if "不存在" in str(e) else 400)
            self.set_header("Content-Type", "application/json;charset=UTF-8")
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
