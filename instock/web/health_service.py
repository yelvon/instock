#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""环境健康检查：数据源、DB、定时心跳。"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import instock.lib.database as mdb


def _check_mysql() -> Dict[str, Any]:
    try:
        n = mdb.executeSqlCount("SELECT 1")
        return {"ok": bool(n), "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_push2() -> Dict[str, Any]:
    try:
        from instock.core.eastmoney_push2 import probe_push2_clist

        r = probe_push2_clist() or {}
        return {
            "ok": bool(r.get("ok")),
            "error": r.get("error"),
            "hint": "不可用时可跑综合选股(xuangu)、盘后数据，跳过资金流",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_xuangu() -> Dict[str, Any]:
    try:
        from instock.core.eastmoney_push2 import probe_xuangu_selection

        r = probe_xuangu_selection() or {}
        return {"ok": bool(r.get("ok")), "error": r.get("error")}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_mootdx_local() -> Dict[str, Any]:
    try:
        from instock.core.data.providers.mootdx_local import run_healthcheck_once
        from instock.core.data.profile import tdx_dir

        d = tdx_dir()
        if not d or not os.path.isdir(d):
            return {"ok": False, "error": "INSTOCK_TDX_DIR 未挂载或不存在"}
        return {"ok": run_healthcheck_once(), "error": None, "tdx_dir": d}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _check_scheduler() -> Dict[str, Any]:
    try:
        from instock.web import scheduler_service as sch

        st = sch.get_status()
        age = st.get("tick_age_seconds")
        ok = age is not None and age <= 120
        return {
            "ok": ok,
            "last_tick_at": st.get("last_tick_at"),
            "tick_age_seconds": age,
            "hint": "应用内定时需 Web 持续运行",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def build_health_report() -> Dict[str, Any]:
    checks = {
        "mysql": _check_mysql(),
        "push2_clist": _check_push2(),
        "xuangu_selection": _check_xuangu(),
        "mootdx_local": _check_mootdx_local(),
        "scheduler": _check_scheduler(),
    }
    suggestions: List[str] = []
    if checks["push2_clist"].get("ok"):
        suggestions.append("可跑：股票快照 basic_data_daily_job")
    else:
        suggestions.append("push2 不通：快照改 Baostock/auto；资金流将跳过")
    if checks["xuangu_selection"].get("ok"):
        suggestions.append("可跑：综合选股 selection_data_daily_job")
    if checks["mootdx_local"].get("ok"):
        suggestions.append("可跑：通达信本地标准库补数")
    if not checks["scheduler"].get("ok"):
        suggestions.append("定时心跳异常：确认 Web 进程 run_web 在运行")
    return {
        "ok": all(c.get("ok") for k, c in checks.items() if k in ("mysql",)),
        "checks": checks,
        "suggestions": suggestions,
    }
