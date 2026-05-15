#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from abc import ABC

import tornado.web
import instock.web.base as webBase
import instock.web.sync_job_service as syncsvc

__author__ = "myh "
__date__ = "2026/4/30 "


class SyncPageHandler(webBase.BaseHandler, ABC):
    def get(self):
        syncsvc.init_history()
        self.render(
            "sync.html",
            leftMenu=webBase.GetLeftMenu(self.request.uri),
        )


class SyncJobsApiHandler(webBase.BaseHandler, ABC):
    def get(self):
        syncsvc.init_history()
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        self.write(json.dumps({"ok": True, "jobs": syncsvc.list_jobs()}, ensure_ascii=False))


class SyncRunsApiHandler(webBase.BaseHandler, ABC):
    def get(self):
        syncsvc.init_history()
        try:
            limit = int(self.get_argument("limit", "80"))
        except ValueError:
            limit = 80
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        self.write(json.dumps({"ok": True, "runs": syncsvc.list_runs(limit)}, ensure_ascii=False))


class DataHealthApiHandler(webBase.BaseHandler, ABC):
    """主数据缺口与行数摘要：GET from=YYYY-MM-DD&to=YYYY-MM-DD（可省略，默认近 60 天）。"""

    def get(self):
        import datetime

        import instock.web.data_health_service as dhs

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            ds = (self.get_argument("from", "") or "").strip()
            de = (self.get_argument("to", "") or "").strip()
            if not ds or not de:
                end = datetime.date.today()
                start = end - datetime.timedelta(days=60)
            else:
                start = dhs.parse_iso_date(ds)
                end = dhs.parse_iso_date(de)
            if start > end:
                raise ValueError("参数 from 不能晚于 to")
            rep = dhs.build_report(start, end)
            self.write(json.dumps(rep, ensure_ascii=False))
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class SyncRunDetailApiHandler(webBase.BaseHandler, ABC):
    def get(self):
        syncsvc.init_history()
        run_id = self.get_argument("id", None)
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        if not run_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 id"}, ensure_ascii=False))
            return
        r = syncsvc.get_run(run_id)
        if not r:
            self.set_status(404)
            self.write(json.dumps({"ok": False, "error": "记录不存在"}, ensure_ascii=False))
            return
        self.write(json.dumps({"ok": True, "run": r}, ensure_ascii=False))


class SyncRunPostHandler(webBase.BaseHandler, ABC):
    def post(self):
        syncsvc.init_history()
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        job_id = (body.get("job_id") or "").strip()
        if not job_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 job_id"}, ensure_ascii=False))
            return
        try:
            rec = syncsvc.start_job(
                job_id,
                date_mode=body.get("date_mode") or "default",
                date_start=body.get("date_start") or "",
                date_end=body.get("date_end") or "",
                date_list=body.get("date_list") or "",
                spot_data_source=(body.get("spot_data_source") or ""),
            )
            self.write(json.dumps({"ok": True, "run": rec}, ensure_ascii=False))
        except Exception as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class SyncRetryHandler(webBase.BaseHandler, ABC):
    def post(self):
        syncsvc.init_history()
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        run_id = (body.get("run_id") or "").strip()
        if not run_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 run_id"}, ensure_ascii=False))
            return
        try:
            rec = syncsvc.retry_from_run(run_id)
            self.write(json.dumps({"ok": True, "run": rec}, ensure_ascii=False))
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class SyncDeleteRunHandler(webBase.BaseHandler, ABC):
    def post(self):
        syncsvc.init_history()
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        run_id = (body.get("id") or body.get("run_id") or "").strip()
        if not run_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 id"}, ensure_ascii=False))
            return
        if syncsvc.delete_run(run_id):
            self.write(json.dumps({"ok": True}, ensure_ascii=False))
        else:
            self.set_status(404)
            self.write(json.dumps({"ok": False, "error": "记录不存在"}, ensure_ascii=False))


class SyncCookieApiHandler(webBase.BaseHandler, ABC):
    """东方财富 Cookie：与 instock/config/eastmoney_cookie.txt 对应（Docker 常挂载为同一路径）。"""

    def get(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            data = syncsvc.read_eastmoney_cookie()
            self.write(
                json.dumps(
                    {
                        "ok": True,
                        "path": data["path"],
                        "content": data["content"],
                        "bytes": data["bytes"],
                        "exists": data["exists"],
                    },
                    ensure_ascii=False,
                )
            )
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def post(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        cookie = body.get("cookie")
        if cookie is None:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 cookie 字段"}, ensure_ascii=False))
            return
        if not isinstance(cookie, str):
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "cookie 须为字符串"}, ensure_ascii=False))
            return
        try:
            path = syncsvc.save_eastmoney_cookie(cookie)
            self.write(
                json.dumps(
                    {
                        "ok": True,
                        "path": path,
                        "message": "已写入。新触发的数据作业子进程会读取此文件。",
                    },
                    ensure_ascii=False,
                )
            )
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class SyncPrefsApiHandler(webBase.BaseHandler, ABC):
    """默认快照数据源等偏好：GET/POST JSON。"""

    def get(self):
        import instock.web.sync_preferences as prefs

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        self.write(json.dumps({"ok": True, "prefs": prefs.read_prefs()}, ensure_ascii=False))

    def post(self):
        import instock.web.sync_preferences as prefs

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        try:
            out = prefs.write_prefs(body)
            self.write(json.dumps({"ok": True, "prefs": out}, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class SchedulerConfigApiHandler(webBase.BaseHandler, ABC):
    """应用内定时任务配置（触发记录见下方「执行记录」，trigger_source=scheduler）。"""

    def get(self):
        import instock.web.scheduler_service as sch

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        self.write(json.dumps({"ok": True, "config": sch.load_config()}, ensure_ascii=False))

    def post(self):
        import instock.web.scheduler_service as sch

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        try:
            cfg = sch.save_config(body)
            self.write(json.dumps({"ok": True, "config": cfg}, ensure_ascii=False))
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
