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
    """旧地址重定向到 Vue SPA（保留书签与外链）。"""

    def get(self):
        syncsvc.init_history()
        self.redirect("/instock/app/sync", permanent=False)


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
            extra_env = body.get("extra_env")
            if extra_env is not None and not isinstance(extra_env, dict):
                extra_env = None
            rec = syncsvc.start_job(
                job_id,
                date_mode=body.get("date_mode") or "default",
                date_start=body.get("date_start") or "",
                date_end=body.get("date_end") or "",
                date_list=body.get("date_list") or "",
                spot_data_source=(body.get("spot_data_source") or ""),
                bar_data_source=(body.get("bar_data_source") or ""),
                extra_env=extra_env,
            )
            self.write(json.dumps({"ok": True, "run": rec}, ensure_ascii=False))
        except Exception as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class SyncCancelHandler(webBase.BaseHandler, ABC):
    """POST /instock/api/sync/cancel  body: { "run_id": "..." }"""

    def post(self):
        syncsvc.init_history()
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        run_id = (body.get("run_id") or body.get("id") or "").strip()
        if not run_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 run_id"}, ensure_ascii=False))
            return
        try:
            rec = syncsvc.cancel_run(run_id)
            self.write(json.dumps({"ok": True, "run": rec}, ensure_ascii=False))
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
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
        try:
            ok, freed = syncsvc.delete_run(run_id)
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
            return
        if ok:
            self.write(
                json.dumps(
                    {
                        "ok": True,
                        "freed_bytes": freed,
                        "history_bytes": syncsvc.history_file_bytes(),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            self.set_status(404)
            self.write(json.dumps({"ok": False, "error": "记录不存在"}, ensure_ascii=False))


class SyncDeleteRunsHandler(webBase.BaseHandler, ABC):
    """POST /instock/api/sync/delete_runs
    body: { "ids": ["uuid", ...] } 或 { "mode": "all_finished" }
    """

    def post(self):
        syncsvc.init_history()
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        mode = (body.get("mode") or "").strip().lower()
        try:
            if mode == "all_finished":
                stat = syncsvc.delete_all_finished_runs()
            else:
                ids = body.get("ids")
                if not isinstance(ids, list) or not ids:
                    self.set_status(400)
                    self.write(
                        json.dumps(
                            {"ok": False, "error": "请提供 ids 数组，或 mode=all_finished"},
                            ensure_ascii=False,
                        )
                    )
                    return
                stat = syncsvc.delete_runs(ids)
            stat["ok"] = True
            self.write(json.dumps(stat, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class SyncPruneRunsHandler(webBase.BaseHandler, ABC):
    """POST /instock/api/sync/prune_runs  body: { "keep_last": 50 }"""

    def post(self):
        syncsvc.init_history()
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        try:
            keep = int(body.get("keep_last") or 50)
        except (TypeError, ValueError):
            keep = 50
        try:
            stat = syncsvc.prune_runs(keep)
            stat["ok"] = True
            stat["history_bytes"] = syncsvc.history_file_bytes()
            self.write(json.dumps(stat, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


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
        import instock.web.sync_presets as presets

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        self.write(
            json.dumps(
                {
                    "ok": True,
                    "prefs": prefs.read_prefs(),
                    "presets": presets.list_presets(),
                },
                ensure_ascii=False,
            )
        )

    def post(self):
        import instock.web.sync_preferences as prefs
        import instock.web.sync_presets as presets

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        try:
            preset_id = str(body.get("apply_preset") or "").strip()
            if preset_id:
                mode = str(body.get("scheduler_mode") or "keep").strip().lower()
                if mode not in ("keep", "merge", "replace"):
                    mode = "keep"
                result = presets.apply_preset(preset_id, scheduler_mode=mode)  # type: ignore
                self.write(
                    json.dumps(
                        {
                            "ok": True,
                            "prefs": result["prefs"],
                            "preset_id": result["preset_id"],
                            "scheduler": result.get("scheduler"),
                            "scheduler_mode": result.get("scheduler_mode"),
                        },
                        ensure_ascii=False,
                    )
                )
                return
            updates = {k: v for k, v in body.items() if k != "apply_preset" and k != "scheduler_mode"}
            out = prefs.write_prefs(updates)
            self.write(json.dumps({"ok": True, "prefs": out}, ensure_ascii=False))
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class DataBatchesApiHandler(webBase.BaseHandler, ABC):
    """GET /instock/api/sync/data_batches?domain_id=&limit=50"""

    def get(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            from instock.core.data.lineage import list_batches

            domain_id = (self.get_argument("domain_id", "") or "").strip() or None
            try:
                limit = int(self.get_argument("limit", "50"))
            except ValueError:
                limit = 50
            try:
                offset = int(self.get_argument("offset", "0"))
            except ValueError:
                offset = 0
            items = list_batches(domain_id=domain_id, limit=limit, offset=offset)
            self.write(
                json.dumps(
                    {"ok": True, "batches": items, "count": len(items)},
                    ensure_ascii=False,
                )
            )
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class DataGovernanceEnvApiHandler(webBase.BaseHandler, ABC):
    """GET 当前进程数据治理相关环境（只读）。"""

    def get(self):
        import os

        from instock.core.data.profile import (
            effective_bar_mode,
            effective_data_profile,
            tencent_enrich_enabled,
            tdx_dir,
        )
        from instock.core.data.providers.tushare import read_tushare_token

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        tdx = tdx_dir()
        self.write(
            json.dumps(
                {
                    "ok": True,
                    "env": {
                        "INSTOCK_DATA_PROFILE": effective_data_profile(),
                        "INSTOCK_BAR_MODE": effective_bar_mode(),
                        "INSTOCK_TENCENT_ENRICH": "1" if tencent_enrich_enabled() else "0",
                        "INSTOCK_USE_DATA_REGISTRY": os.environ.get(
                            "INSTOCK_USE_DATA_REGISTRY", "0"
                        ),
                        "INSTOCK_TDX_DIR": tdx or "",
                        "INSTOCK_SPOT_DATA_SOURCE": os.environ.get(
                            "INSTOCK_SPOT_DATA_SOURCE", ""
                        ),
                        "tdx_configured": bool(tdx),
                        "tushare_token_configured": bool(read_tushare_token()),
                    },
                    "hint": "修改需在 Docker Compose environment 或 .env 中配置后重启 InStock 容器",
                },
                ensure_ascii=False,
            )
        )


class MootdxProbeApiHandler(webBase.BaseHandler, ABC):
    """POST {mode: auto|local|online} 启动 mootdx 探测；GET ?id= 轮询日志。"""

    def post(self):
        import instock.web.mootdx_probe_service as mps

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            body = {}
        mode = (body.get("mode") or "auto").strip().lower()
        probe_id = mps.start_probe(mode)
        self.write(
            json.dumps(
                {"ok": True, "probe_id": probe_id, "mode": mode},
                ensure_ascii=False,
            )
        )

    def get(self):
        import instock.web.mootdx_probe_service as mps

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        probe_id = (self.get_argument("id", "") or "").strip()
        if not probe_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 id"}, ensure_ascii=False))
            return
        snap = mps.get_probe(probe_id)
        if not snap:
            self.set_status(404)
            self.write(json.dumps({"ok": False, "error": "探测不存在或已过期"}, ensure_ascii=False))
            return
        self.write(json.dumps({"ok": True, **snap}, ensure_ascii=False))

    def delete(self):
        import instock.web.mootdx_probe_service as mps

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        probe_id = (self.get_argument("id", "") or "").strip()
        if not probe_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 id"}, ensure_ascii=False))
            return
        ok = mps.cancel_probe(probe_id)
        self.write(
            json.dumps(
                {"ok": ok, "message": "已请求取消" if ok else "无法取消"},
                ensure_ascii=False,
            )
        )


class EastmoneyProbeApiHandler(webBase.BaseHandler, ABC):
    """
    东财 push2 异步探测（不阻塞 Web 主线程）。
    POST {} 或 {push2_host?} 启动；GET ?id= 轮询日志与结果；DELETE ?id= 取消。
    """

    def post(self):
        import instock.web.eastmoney_probe_service as eps
        from instock.core.eastmoney_push2 import normalize_push2_host, read_push2_host_preference

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            body = {}
        pref = normalize_push2_host(
            body.get("push2_host") or read_push2_host_preference()
        )
        probe_id = eps.start_probe(pref)
        self.write(
            json.dumps(
                {
                    "ok": True,
                    "probe_id": probe_id,
                    "push2_preference": pref,
                    "message": "探测已在后台启动，请轮询本接口 GET ?id= 查看实时日志",
                },
                ensure_ascii=False,
            )
        )

    def get(self):
        import instock.web.eastmoney_probe_service as eps

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        probe_id = (self.get_argument("id", "") or "").strip()
        if not probe_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 id"}, ensure_ascii=False))
            return
        snap = eps.get_probe(probe_id)
        if not snap:
            self.set_status(404)
            self.write(json.dumps({"ok": False, "error": "探测不存在或已过期"}, ensure_ascii=False))
            return
        self.write(json.dumps({"ok": True, **snap}, ensure_ascii=False))

    def delete(self):
        import instock.web.eastmoney_probe_service as eps

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        probe_id = (self.get_argument("id", "") or "").strip()
        if not probe_id:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 id"}, ensure_ascii=False))
            return
        if eps.cancel_probe(probe_id):
            self.write(json.dumps({"ok": True, "message": "已请求取消"}, ensure_ascii=False))
        else:
            self.write(json.dumps({"ok": False, "error": "无法取消（可能已结束）"}, ensure_ascii=False))


class CanonicalGovernanceApiHandler(webBase.BaseHandler, ABC):
    """标准行情库覆盖率、冲突与来源贡献。"""

    def get(self):
        import instock.web.canonical_governance_service as cgs

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        code = (self.get_argument("code", "") or "").strip()
        try:
            if code:
                out = cgs.get_code_coverage(code)
            else:
                out = cgs.get_canonical_summary()
            self.write(json.dumps({"ok": True, **out}, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


class DataSourcesApiHandler(webBase.BaseHandler, ABC):
    """GET 多源 Registry 状态；POST body {provider_id, code?} 触发连通性检测。"""

    def get(self):
        import instock.web.data_sources_service as dss

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            self.write(json.dumps(dss.build_report(), ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def post(self):
        import instock.web.data_sources_service as dss

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        try:
            body = json.loads(self.request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "JSON 无效"}, ensure_ascii=False))
            return
        pid = (body.get("provider_id") or "").strip()
        code = (body.get("code") or "600000").strip()
        if not pid:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 provider_id"}, ensure_ascii=False))
            return
        if pid == "eastmoney":
            import instock.web.eastmoney_probe_service as eps
            from instock.core.eastmoney_push2 import normalize_push2_host, read_push2_host_preference

            pref = normalize_push2_host(
                body.get("push2_host") or read_push2_host_preference()
            )
            probe_id = eps.start_probe(pref)
            self.write(
                json.dumps(
                    {
                        "ok": True,
                        "async": True,
                        "probe_id": probe_id,
                        "push2_preference": pref,
                    },
                    ensure_ascii=False,
                )
            )
            return
        try:
            out = dss.verify_provider(pid, code)
            self.write(json.dumps(out, ensure_ascii=False))
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
