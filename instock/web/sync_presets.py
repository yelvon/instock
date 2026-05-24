# -*- coding: utf-8 -*-
"""数据同步一键预设：偏好 + 可选定时任务模板。"""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any, Dict, List, Literal, Optional

SchedulerMode = Literal["keep", "merge", "replace"]

PRESET_TUSHARE_KLINE = "tushare_kline"
PRESET_EASTMONEY_CLASSIC = "eastmoney_classic"
PRESET_BAOSTOCK_SPOT = "baostock_spot"
PRESET_MOOTDX_LOCAL = "mootdx_local"

_PRESETS: Dict[str, Dict[str, Any]] = {
    PRESET_MOOTDX_LOCAL: {
        "id": PRESET_MOOTDX_LOCAL,
        "title": "通达信本地（推荐）",
        "summary": "K 线走 vipdoc → 标准库；证券主表本地扫描；快照仍可用东财/Baostock",
        "prefs": {
            "default_spot_data_source": "auto",
            "default_bar_data_source": "mootdx",
            "eastmoney_push2_host": "auto",
            "active_preset_id": PRESET_MOOTDX_LOCAL,
        },
        "scheduler_templates": [
            {
                "title": "工作日-证券主表(本地vipdoc)",
                "job_id": "sync_stock_universe_job",
                "weekdays": [0, 1, 2, 3, 4],
                "times": ["17:00"],
                "extra_env": {"INSTOCK_UNIVERSE_SOURCE": "local"},
            },
            {
                "title": "工作日-标准库(通达信本地)",
                "job_id": "sync_bars_mootdx_local_job",
                "weekdays": [0, 1, 2, 3, 4],
                "times": ["22:00"],
            },
            {
                "title": "工作日-股票快照",
                "job_id": "basic_data_daily_job",
                "spot_data_source": "auto",
                "weekdays": [0, 1, 2, 3, 4],
                "times": ["17:30"],
            },
        ],
    },
    PRESET_TUSHARE_KLINE: {
        "id": PRESET_TUSHARE_KLINE,
        "title": "Tushare K 线优先（推荐）",
        "summary": "K 线仅 Tushare；快照东财失败自动 Baostock；push2 自动换节点",
        "prefs": {
            "default_spot_data_source": "auto",
            "default_bar_data_source": "tushare",
            "eastmoney_push2_host": "auto",
        },
        "scheduler_templates": [
            {
                "title": "工作日-股票快照",
                "job_id": "basic_data_daily_job",
                "spot_data_source": "auto",
                "weekdays": [0, 1, 2, 3, 4],
                "times": ["17:30"],
            },
            {
                "title": "工作日-标准库补数(Tushare)",
                "job_id": "sync_bars_tushare_job",
                "weekdays": [0, 1, 2, 3, 4],
                "times": ["22:30"],
            },
            {
                "title": "工作日-证券主表",
                "job_id": "sync_stock_universe_job",
                "weekdays": [0, 1, 2, 3, 4],
                "times": ["17:00"],
            },
        ],
    },
    PRESET_EASTMONEY_CLASSIC: {
        "id": PRESET_EASTMONEY_CLASSIC,
        "title": "东财传统",
        "summary": "快照与 K 线自动链路（含东财回退），与原版行为接近",
        "prefs": {
            "default_spot_data_source": "eastmoney",
            "default_bar_data_source": "auto",
            "eastmoney_push2_host": "auto",
        },
        "scheduler_templates": [
            {
                "title": "工作日-股票快照(东财)",
                "job_id": "basic_data_daily_job",
                "spot_data_source": "eastmoney",
                "weekdays": [0, 1, 2, 3, 4],
                "times": ["17:30"],
            },
        ],
    },
    PRESET_BAOSTOCK_SPOT: {
        "id": PRESET_BAOSTOCK_SPOT,
        "title": "快照 Baostock + K 线 Tushare",
        "summary": "快照不走东财；K 线仍用 Tushare（需 token）",
        "prefs": {
            "default_spot_data_source": "baostock",
            "default_bar_data_source": "tushare",
            "eastmoney_push2_host": "auto",
        },
        "scheduler_templates": [
            {
                "title": "工作日-股票快照(Baostock)",
                "job_id": "basic_data_daily_job",
                "spot_data_source": "baostock",
                "weekdays": [0, 1, 2, 3, 4],
                "times": ["17:30"],
            },
            {
                "title": "工作日-标准库补数(Tushare)",
                "job_id": "sync_bars_tushare_job",
                "weekdays": [0, 1, 2, 3, 4],
                "times": ["22:30"],
            },
        ],
    },
}


def list_presets() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in _PRESETS.values():
        out.append(
            {
                "id": p["id"],
                "title": p["title"],
                "summary": p["summary"],
                "prefs": deepcopy(p["prefs"]),
                "scheduler_template_count": len(p.get("scheduler_templates") or []),
            }
        )
    return out


def _normalize_template(tpl: Dict[str, Any]) -> Dict[str, Any]:
    from instock.core.data.profile import normalize_bar_data_source
    from instock.core.spot_source import normalize_spot_source

    job_id = str(tpl.get("job_id") or "").strip()
    spot = normalize_spot_source(str(tpl.get("spot_data_source") or "eastmoney"))
    bar = normalize_bar_data_source(str(tpl.get("bar_data_source") or "auto"))
    weekdays = tpl.get("weekdays") or [0, 1, 2, 3, 4]
    times = tpl.get("times") or ["17:30"]
    wd_clean: List[int] = []
    for w in weekdays:
        try:
            n = int(w)
        except (TypeError, ValueError):
            continue
        if 0 <= n <= 6:
            wd_clean.append(n)
    if not wd_clean:
        wd_clean = [0, 1, 2, 3, 4]
    return {
        "id": str(tpl.get("id") or "").strip() or str(uuid.uuid4()),
        "title": str(tpl.get("title") or "定时任务").strip()[:120],
        "enabled": bool(tpl.get("enabled", True)),
        "job_id": job_id,
        "date_mode": "default",
        "date_start": "",
        "date_end": "",
        "date_list": "",
        "weekdays": sorted(set(wd_clean)),
        "times": [str(t).strip() for t in times if str(t).strip()],
        "spot_data_source": spot,
        "bar_data_source": bar,
        "extra_env": dict(tpl.get("extra_env") or {}),
    }


def build_scheduler_from_preset(
    preset_id: str,
    *,
    mode: SchedulerMode = "merge",
    existing: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    p = _PRESETS.get(preset_id)
    if not p:
        raise ValueError(f"未知预设: {preset_id}")
    templates = [_normalize_template(t) for t in (p.get("scheduler_templates") or [])]
    if mode == "replace":
        return templates
    cur = list(existing or [])
    if mode == "keep":
        return cur
    # merge: 按 title+job_id 去重，保留用户已有项
    seen = {(str(x.get("title")), str(x.get("job_id"))) for x in cur}
    for t in templates:
        key = (t["title"], t["job_id"])
        if key not in seen:
            cur.append(t)
            seen.add(key)
    return cur


def apply_preset(
    preset_id: str,
    *,
    scheduler_mode: SchedulerMode = "keep",
) -> Dict[str, Any]:
    """
    写入 sync_preferences，并按 scheduler_mode 更新 scheduler.json（经 save_config 校验）。
    """
    p = _PRESETS.get(preset_id)
    if not p:
        raise ValueError(f"未知预设: {preset_id}")

    import instock.web.sync_preferences as prefs
    import instock.web.scheduler_service as sch

    pref_updates = dict(p["prefs"])
    pref_updates["active_preset_id"] = preset_id
    out_prefs = prefs.write_prefs(pref_updates)

    sched_result: Optional[Dict[str, Any]] = None
    if scheduler_mode != "keep":
        cfg = sch.load_config()
        merged = build_scheduler_from_preset(
            preset_id,
            mode=scheduler_mode,
            existing=cfg.get("schedules") or [],
        )
        cfg["schedules"] = merged
        sched_result = sch.save_config(cfg)

    return {
        "preset_id": preset_id,
        "prefs": out_prefs,
        "scheduler": sched_result,
        "scheduler_mode": scheduler_mode,
    }
