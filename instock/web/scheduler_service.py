#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用内定时同步：由 Web 进程每分钟检查一次配置，匹配则调用 sync_job_service.start_job。
与系统 crontab 独立；若 Docker 仍启用镜像内 cron，请避免同一作业在同一时刻重复触发。
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Set

_FILE_LOCK = threading.Lock()
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SCHEDULER_PATH = os.path.join(_REPO_ROOT, "instock", "config", "scheduler.json")

# 同一自然分钟内同一 schedule id 只触发一次（进程内）
_fired_minute_keys: Set[str] = set()
_MAX_FIRE_KEYS = 5000

_TIME_RE = re.compile(r"^\s*(\d{1,2})\s*:\s*(\d{2})\s*$")


def _ensure_dir() -> None:
    d = os.path.dirname(_SCHEDULER_PATH)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def default_config() -> Dict[str, Any]:
    return {
        "version": 1,
        "enabled_globally": True,
        "schedules": [],
    }


def load_config() -> Dict[str, Any]:
    with _FILE_LOCK:
        if not os.path.isfile(_SCHEDULER_PATH):
            return default_config()
        try:
            with open(_SCHEDULER_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return default_config()
            base = default_config()
            base.update({k: data[k] for k in ("version", "enabled_globally", "schedules") if k in data})
            if not isinstance(base.get("schedules"), list):
                base["schedules"] = []
            return base
        except Exception as e:
            logging.warning("scheduler_service.load_config: %s", e)
            return default_config()


def save_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """校验并写入完整配置。"""
    import instock.web.sync_job_service as syncsvc

    if not isinstance(cfg, dict):
        raise ValueError("配置须为 JSON 对象")
    job_ids = {j["id"] for j in syncsvc.JOB_ITEMS}
    schedules = cfg.get("schedules")
    if not isinstance(schedules, list):
        raise ValueError("schedules 须为数组")
    cleaned: List[Dict[str, Any]] = []
    for i, sch in enumerate(schedules):
        if not isinstance(sch, dict):
            continue
        sid = str(sch.get("id") or "").strip() or str(uuid.uuid4())
        title = str(sch.get("title") or f"定时任务{i+1}").strip()[:120]
        job_id = str(sch.get("job_id") or "").strip()
        if job_id not in job_ids:
            raise ValueError(f"未知 job_id: {job_id}")
        enabled = bool(sch.get("enabled", True))
        date_mode = str(sch.get("date_mode") or "default").strip().lower()
        if date_mode not in ("default", "list", "range"):
            date_mode = "default"
        if job_id in ("init_job", "sync_trade_calendar_job"):
            date_mode = "default"
        weekdays = sch.get("weekdays")
        if not isinstance(weekdays, list) or not weekdays:
            weekdays = [0, 1, 2, 3, 4]
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
        times = sch.get("times")
        if not isinstance(times, list) or not times:
            raise ValueError(f"「{title}」须至少填写一个触发时刻 HH:MM")
        times_clean: List[str] = []
        for t in times:
            s = str(t).strip()
            m = _TIME_RE.match(s)
            if not m:
                raise ValueError(f"非法时刻: {t}（须为 HH:MM，如 09:30）")
            hh, mm = int(m.group(1)), int(m.group(2))
            if hh > 23 or mm > 59:
                raise ValueError(f"非法时刻: {t}")
            times_clean.append(f"{hh:02d}:{mm:02d}")
        if not times_clean:
            raise ValueError("未解析到有效时刻")
        from instock.core.data.profile import normalize_bar_data_source
        from instock.core.spot_source import normalize_spot_source
        from instock.web.sync_preferences import read_prefs

        spot = normalize_spot_source(str(sch.get("spot_data_source") or "eastmoney"))
        bar = normalize_bar_data_source(
            str(sch.get("bar_data_source") or read_prefs().get("default_bar_data_source") or "auto")
        )
        cleaned.append(
            {
                "id": sid,
                "title": title,
                "enabled": enabled,
                "job_id": job_id,
                "date_mode": date_mode,
                "date_start": str(sch.get("date_start") or ""),
                "date_end": str(sch.get("date_end") or ""),
                "date_list": str(sch.get("date_list") or ""),
                "weekdays": sorted(set(wd_clean)),
                "times": sorted(set(times_clean)),
                "spot_data_source": spot,
                "bar_data_source": bar,
            }
        )
    out = {
        "version": int(cfg.get("version") or 1),
        "enabled_globally": bool(cfg.get("enabled_globally", True)),
        "schedules": cleaned,
    }
    with _FILE_LOCK:
        _ensure_dir()
        with open(_SCHEDULER_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def tick() -> None:
    """由 Tornado PeriodicCallback 每分钟调用一次。"""
    global _fired_minute_keys
    cfg = load_config()
    if not cfg.get("enabled_globally", True):
        return
    now = datetime.now()
    wd = now.weekday()
    hm = f"{now.hour:02d}:{now.minute:02d}"
    minute_bucket = now.strftime("%Y%m%d%H%M")

    import instock.web.sync_job_service as syncsvc

    for sch in cfg.get("schedules") or []:
        if not isinstance(sch, dict) or not sch.get("enabled", True):
            continue
        if wd not in sch.get("weekdays", [0, 1, 2, 3, 4]):
            continue
        if hm not in sch.get("times", []):
            continue
        sid = str(sch.get("id") or "")
        if not sid:
            continue
        key = f"{sid}:{minute_bucket}"
        with _FILE_LOCK:
            if key in _fired_minute_keys:
                continue
            _fired_minute_keys.add(key)
            if len(_fired_minute_keys) > _MAX_FIRE_KEYS:
                _fired_minute_keys = set(list(_fired_minute_keys)[-_MAX_FIRE_KEYS // 2 :])
        try:
            extra = sch.get("extra_env")
            if extra is not None and not isinstance(extra, dict):
                extra = None
            syncsvc.start_job(
                sch["job_id"],
                date_mode=str(sch.get("date_mode") or "default"),
                date_start=str(sch.get("date_start") or ""),
                date_end=str(sch.get("date_end") or ""),
                date_list=str(sch.get("date_list") or ""),
                spot_data_source=str(sch.get("spot_data_source") or "eastmoney"),
                bar_data_source=str(sch.get("bar_data_source") or ""),
                trigger_source="scheduler",
                schedule_id=sid,
                schedule_title=str(sch.get("title") or ""),
                extra_env=extra,
            )
            logging.info(
                "scheduler: 已触发 %s job=%s time=%s",
                sch.get("title"),
                sch.get("job_id"),
                hm,
            )
        except Exception as e:
            logging.error("scheduler tick 触发失败: %s", e)


def install_tornado_scheduler() -> None:
    """在 Web 主程序启动后注册每分钟 tick。"""
    try:
        from tornado.ioloop import PeriodicCallback
    except ImportError:
        return

    def _cb() -> None:
        try:
            tick()
        except Exception as e:
            logging.error("scheduler tick: %s", e)

    pc = PeriodicCallback(_cb, 60_000)
    pc.start()
    logging.info("scheduler_service: 已注册每分钟检查（应用内定时）")
