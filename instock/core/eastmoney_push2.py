#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""东财 push2 行情节点：固定节点或 auto 顺序回退（82 → 88 → 80）。"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

_log = logging.getLogger(__name__)

PUSH2_HOST_CHOICES: tuple[str, ...] = ("82", "88", "80")
AUTO_HOST_ORDER: tuple[str, ...] = ("82", "88", "80")
CLIST_PATH = "/api/qt/clist/get"

# 资金流等 clist 接口：短超时、少重试，避免 push2 不通时刷屏
CLIST_FAST_TIMEOUT = (3, 20)
CLIST_FAST_RETRY = 2


def normalize_push2_host(raw: Optional[str]) -> str:
    s = (raw or "auto").strip().lower()
    if s in ("auto", "automatic", "fallback", "自动"):
        return "auto"
    if s in PUSH2_HOST_CHOICES:
        return s
    return "auto"


def resolve_host_sequence(preference: Optional[str] = None) -> List[str]:
    pref = normalize_push2_host(preference)
    if pref != "auto":
        return [pref]
    order_env = os.environ.get("INSTOCK_EM_PUSH2_FALLBACK_ORDER", "").strip()
    if order_env:
        hosts = [
            h.strip()
            for h in order_env.split(",")
            if h.strip() in PUSH2_HOST_CHOICES
        ]
        if hosts:
            return hosts
    return list(AUTO_HOST_ORDER)


def read_push2_host_preference() -> str:
    env = os.environ.get("INSTOCK_EM_PUSH2_HOST", "").strip()
    if env:
        return normalize_push2_host(env)
    try:
        from instock.web.sync_preferences import read_prefs

        return normalize_push2_host(read_prefs().get("eastmoney_push2_host"))
    except Exception:
        return "auto"


def clist_get_url(host_id: str) -> str:
    return f"https://{host_id}.push2.eastmoney.com{CLIST_PATH}"


# 探测专用：单节点超时（秒），auto 模式下最多尝试 len(AUTO_HOST_ORDER) 个节点
PROBE_CONNECT_TIMEOUT = 3
PROBE_READ_TIMEOUT = 8


def probe_push2_clist(
    preference: Optional[str] = None,
    log: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    快速探测 clist 首屏；用于页面测试（后台线程），日志经 log(msg) 实时输出。
    """
    import time

    from instock.core.eastmoney_fetcher import eastmoney_fetcher
    from instock.web import sync_job_service as syncsvc

    pref = normalize_push2_host(preference) if preference is not None else read_push2_host_preference()
    hosts = resolve_host_sequence(pref)
    cookie_info = syncsvc.read_eastmoney_cookie()
    cookie_configured = bool(cookie_info.get("exists") and (cookie_info.get("bytes") or 0) > 0)

    def _log(msg: str) -> None:
        if log:
            log(msg)

    params = {
        "pn": 1,
        "pz": 50,
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f12",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
        "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f14,f15,f16,f17,f18,f20,f21,f22,f23,f24,f25,f26,f37,f38,f39,f40,f41,f45,f46,f48,f49,f57,f61,f100,f112,f113,f114,f115,f221",
        "_": "1623833739532",
    }
    timeout = (PROBE_CONNECT_TIMEOUT, PROBE_READ_TIMEOUT)
    fetcher = eastmoney_fetcher()
    t_all = time.time()
    last_err: Optional[str] = None

    for host in hosts:
        url = clist_get_url(host)
        _log(f"请求 {host}.push2.eastmoney.com …")
        t0 = time.time()
        try:
            r = fetcher.make_probe_request(url, params=params, timeout=timeout)
            elapsed = int((time.time() - t0) * 1000)
            data_json = r.json()
            data_block = data_json.get("data") if isinstance(data_json, dict) else None
            diff = (data_block or {}).get("diff") if isinstance(data_block, dict) else None
            rows = len(diff) if isinstance(diff, list) else 0
            total = int((data_block or {}).get("total") or 0) if isinstance(data_block, dict) else 0
            if rows > 0:
                _log(f"  成功 HTTP {r.status_code}，首屏 {rows} 条，全市场约 {total} 只，{elapsed}ms")
                return {
                    "ok": True,
                    "provider_id": "eastmoney",
                    "healthcheck": True,
                    "rows": rows,
                    "total": total,
                    "elapsed_ms": int((time.time() - t_all) * 1000),
                    "cookie_configured": cookie_configured,
                    "cookie_bytes": int(cookie_info.get("bytes") or 0),
                    "push2_preference": pref,
                    "push2_host": host,
                    "error": None,
                }
            last_err = "返回 data.diff 为空"
            _log(f"  失败：{last_err}（{elapsed}ms）")
        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            last_err = str(e)
            short = last_err if len(last_err) < 160 else last_err[:160] + "…"
            _log(f"  失败：{short}（{elapsed}ms）")

    if pref == "auto":
        _log("auto 模式下全部节点不可用")
    return {
        "ok": False,
        "provider_id": "eastmoney",
        "healthcheck": False,
        "rows": 0,
        "total": 0,
        "elapsed_ms": int((time.time() - t_all) * 1000),
        "cookie_configured": cookie_configured,
        "cookie_bytes": int(cookie_info.get("bytes") or 0),
        "push2_preference": pref,
        "push2_host": None,
        "error": last_err or "无可用 push2 节点",
    }


def probe_xuangu_selection(log: Optional[Any] = None) -> Dict[str, Any]:
    """探测综合选股 xuangu 接口（不经过 push2）。"""
    import time

    from instock.core.eastmoney_fetcher import eastmoney_fetcher

    def _log(msg: str) -> None:
        if log:
            log(msg)

    url = "https://data.eastmoney.com/dataapi/xuangu/list"
    params = {
        "sty": "SECURITY_CODE,SECURITY_NAME_ABBR,NEW_PRICE,CHANGE_RATE",
        "filter": '(MARKET+in+("上交所主板","深交所主板","深交所创业板"))(NEW_PRICE>0)',
        "p": 1,
        "ps": 5,
        "source": "SELECT_SECURITIES",
        "client": "WEB",
    }
    t0 = time.time()
    try:
        r = eastmoney_fetcher().make_request(url, params=params, timeout=(8, 30), retry=2)
        data_json = r.json()
        block = (data_json.get("result") or {}) if isinstance(data_json, dict) else {}
        rows = block.get("data") or []
        total = int(block.get("count") or 0)
        n = len(rows) if isinstance(rows, list) else 0
        elapsed = int((time.time() - t0) * 1000)
        if n > 0:
            _log(f"选股 xuangu 成功：首屏 {n} 条，全市场约 {total} 只，{elapsed}ms")
            return {
                "ok": True,
                "rows": n,
                "total": total,
                "elapsed_ms": elapsed,
                "error": None,
            }
        _log(f"选股 xuangu 返回空 data（{elapsed}ms）")
        return {"ok": False, "rows": 0, "total": total, "elapsed_ms": elapsed, "error": "xuangu data 为空"}
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        _log(f"选股 xuangu 失败：{str(e)[:160]}（{elapsed}ms）")
        return {"ok": False, "rows": 0, "total": 0, "elapsed_ms": elapsed, "error": str(e)[:500]}


def hosts_for_clist_requests(preference: Optional[str] = None) -> List[str]:
    """
    实际请求顺序：auto 为 82→88→80；固定节点时优先该节点，失败后仍尝试其余节点（避免偏好 82 时整批作业失败）。
    """
    pref = normalize_push2_host(preference) if preference is not None else read_push2_host_preference()
    primary = resolve_host_sequence(pref)
    if pref == "auto":
        return primary
    seen: set[str] = set()
    out: List[str] = []
    for h in primary + list(AUTO_HOST_ORDER):
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def clist_request(fetcher: Any, params: Dict[str, Any], **kwargs: Any) -> Any:
    """clist/get 统一走 Push2ClistRouter（82/88/80 HTTPS），替代旧 http://push2.eastmoney.com。"""
    router = Push2ClistRouter()
    hop = dict(kwargs)
    hop.setdefault("retry", CLIST_FAST_RETRY)
    hop.setdefault("timeout", CLIST_FAST_TIMEOUT)
    return router.make_request(fetcher, params=params, **hop)


class Push2ClistRouter:
    """按偏好选择 push2 节点；失败后依次尝试其它节点，成功后分页复用同一节点。"""

    def __init__(self, preference: Optional[str] = None) -> None:
        self.preference = (
            normalize_push2_host(preference) if preference is not None else read_push2_host_preference()
        )
        self._active_host: Optional[str] = None

    @property
    def active_host(self) -> Optional[str]:
        return self._active_host

    def make_request(self, fetcher: Any, params: Dict[str, Any], **kwargs: Any) -> Any:
        if self._active_host:
            return fetcher.make_request(
                clist_get_url(self._active_host), params=params, **kwargs
            )
        last_exc: Optional[Exception] = None
        for host in hosts_for_clist_requests(self.preference):
            try:
                hop_kw = dict(kwargs)
                hop_kw.setdefault("retry", 1)
                hop_kw.setdefault("timeout", (3, 12))
                r = fetcher.make_request(
                    clist_get_url(host), params=params, **hop_kw
                )
                self._active_host = host
                if self.preference != "auto" and host != self.preference:
                    _log.warning(
                        "eastmoney push2: 偏好节点 %s 不可用，已改用 %s.push2.eastmoney.com",
                        self.preference,
                        host,
                    )
                else:
                    _log.info("eastmoney push2: 使用节点 %s.push2.eastmoney.com", host)
                return r
            except Exception as e:
                last_exc = e
                _log.warning("eastmoney push2: 节点 %s 不可用: %s", host, e)
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("无可用东财 push2 节点")
