#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据同步页偏好：默认快照数据源等（JSON，便于与定时任务共用）。"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict

_LOCK = threading.Lock()

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PREFS_PATH = os.path.join(_REPO_ROOT, "instock", "config", "sync_preferences.json")


def _ensure_dir() -> None:
    d = os.path.dirname(_PREFS_PATH)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def _defaults() -> Dict[str, Any]:
    return {
        "default_spot_data_source": "eastmoney",
        "eastmoney_push2_host": "auto",
    }


def _read_file_unlocked() -> Dict[str, Any]:
    if not os.path.isfile(_PREFS_PATH):
        return _defaults()
    try:
        with open(_PREFS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _defaults()
        out = _defaults()
        out.update({k: v for k, v in data.items() if k in out})
        raw = out.get("default_spot_data_source") or "eastmoney"
        from instock.core.spot_source import normalize_spot_source

        out["default_spot_data_source"] = normalize_spot_source(str(raw))
        from instock.core.eastmoney_push2 import normalize_push2_host

        out["eastmoney_push2_host"] = normalize_push2_host(
            str(out.get("eastmoney_push2_host") or "auto")
        )
        return out
    except Exception:
        return _defaults()


def read_prefs() -> Dict[str, Any]:
    with _LOCK:
        return _read_file_unlocked()


def write_prefs(updates: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        cur = _read_file_unlocked()
        if "default_spot_data_source" in updates:
            from instock.core.spot_source import normalize_spot_source

            cur["default_spot_data_source"] = normalize_spot_source(
                str(updates.get("default_spot_data_source") or "eastmoney")
            )
        if "eastmoney_push2_host" in updates:
            from instock.core.eastmoney_push2 import normalize_push2_host

            cur["eastmoney_push2_host"] = normalize_push2_host(
                str(updates.get("eastmoney_push2_host") or "auto")
            )
        _ensure_dir()
        with open(_PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(cur, f, ensure_ascii=False, indent=2)
        return dict(cur)
