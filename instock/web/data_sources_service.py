# -*- coding: utf-8 -*-
"""多源 Registry 状态：Provider 健康检查、chain 解析、mootdx 专项。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from instock.core.data.profile import (
    effective_bar_mode,
    effective_data_profile,
    tdx_dir,
)
from instock.core.data.registry import get_registry


def _mootdx_importable() -> bool:
    try:
        import mootdx  # noqa: F401

        return True
    except ImportError:
        return False


def _provider_status(provider_id: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider_id": provider_id,
        "import_ok": False,
        "healthcheck": False,
        "error": None,
        "capabilities": [],
    }
    try:
        reg = get_registry()
        prov = reg.get_provider(provider_id)
        out["import_ok"] = True
        out["capabilities"] = sorted(prov.capabilities())
        try:
            out["healthcheck"] = bool(prov.healthcheck())
        except Exception as e:
            out["error"] = str(e)
    except Exception as e:
        out["error"] = str(e)
    return out


def _chain_steps(domain_id: str, profile: str) -> List[Dict[str, Any]]:
    reg = get_registry()
    chain = reg.resolve_chain(domain_id, profile)
    enrich = reg.resolve_enrich(domain_id, profile)
    steps: List[Dict[str, Any]] = []
    for i, s in enumerate(chain):
        steps.append(
            {
                "order": i + 1,
                "role": "chain",
                "provider": s.provider_id,
                "strict": s.strict,
                "when": s.when,
                "fill_mode": s.fill_mode,
                "mode": s.mode,
            }
        )
    for i, s in enumerate(enrich):
        steps.append(
            {
                "order": i + 1,
                "role": "enrich",
                "provider": s.provider_id,
                "strict": s.strict,
                "when": s.when,
                "fill_mode": s.fill_mode,
                "mode": s.mode,
            }
        )
    return steps


def _mootdx_local_detail() -> Dict[str, Any]:
    d = tdx_dir()
    detail: Dict[str, Any] = {
        "provider_id": "mootdx_local",
        "INSTOCK_TDX_DIR": d or "",
        "dir_exists": False,
        "vipdoc_exists": False,
        "healthcheck": False,
        "sample_ok": False,
        "sample_rows": 0,
        "sample_error": None,
        "active_in_chain": False,
        "hint": "在 Docker Compose 挂载通达信目录并设置 INSTOCK_TDX_DIR，重启 InStock 容器",
    }
    if not d:
        detail["sample_error"] = "未设置 INSTOCK_TDX_DIR"
        return detail
    p = Path(d)
    detail["dir_exists"] = p.is_dir()
    detail["vipdoc_exists"] = (p / "vipdoc").is_dir()
    if not detail["dir_exists"]:
        detail["sample_error"] = f"目录不存在: {d}"
        return detail
    try:
        from instock.core.data.providers.mootdx_local import Provider

        prov = Provider()
        detail["healthcheck"] = prov.healthcheck()
        res = prov.fetch_bars("600000", "20240101", adjust="raw")
        if res.ok and res.data is not None and not res.data.empty:
            detail["sample_ok"] = True
            detail["sample_rows"] = int(len(res.data))
        else:
            detail["sample_error"] = res.error or "样本 K 线为空"
    except Exception as e:
        detail["sample_error"] = str(e)
    prof = effective_data_profile()
    chain = _chain_steps("daily_bar_raw", prof)
    detail["active_in_chain"] = any(
        x.get("provider") == "mootdx_local" and x.get("role") == "chain" for x in chain
    )
    return detail


def _mootdx_online_detail() -> Dict[str, Any]:
    detail: Dict[str, Any] = {
        "provider_id": "mootdx_online",
        "healthcheck": False,
        "sample_ok": False,
        "sample_rows": 0,
        "sample_error": None,
        "fallback_when": "无 INSTOCK_TDX_DIR 或 local healthcheck 失败；需容器可连通达信行情站",
        "hint_empty_bestip": "若报 unpack 错误，多为 mootdx BESTIP 未初始化，已自动回退默认 HQ 服务器",
    }
    if not _mootdx_importable():
        detail["sample_error"] = "未安装 mootdx 包（pip install mootdx）"
        return detail
    try:
        from instock.core.data.providers.mootdx_online import Provider

        prov = Provider()
        detail["healthcheck"] = prov.healthcheck()
        res = prov.fetch_bars("600000", "20240101", adjust="raw")
        if res.ok and res.data is not None and not res.data.empty:
            detail["sample_ok"] = True
            detail["sample_rows"] = int(len(res.data))
        else:
            detail["sample_error"] = res.error or "样本 K 线为空"
    except Exception as e:
        detail["sample_error"] = str(e)
    return detail


def build_report() -> Dict[str, Any]:
    profile = effective_data_profile()
    bar_mode = effective_bar_mode()
    use_reg = os.environ.get("INSTOCK_USE_DATA_REGISTRY", "0").strip() in (
        "1",
        "true",
        "yes",
    )
    mootdx_ok = _mootdx_importable()

    provider_ids = [
        "eastmoney",
        "baostock",
        "mootdx_local",
        "mootdx_online",
        "tencent",
    ]
    providers = [_provider_status(pid) for pid in provider_ids]

    domains = {}
    for dom in ("daily_bar_raw", "daily_spot_snapshot"):
        domains[dom] = {
            "profile_live": _chain_steps(dom, "live"),
            "profile_backtest": _chain_steps(dom, "backtest"),
            "profile_current": _chain_steps(dom, profile),
        }

    bar_batches = []
    try:
        from instock.core.data.lineage import list_batches

        bar_batches = list_batches(domain_id="daily_bar_raw", limit=5)
    except Exception:
        pass

    from instock.core.eastmoney_push2 import (
        AUTO_HOST_ORDER,
        PUSH2_HOST_CHOICES,
        read_push2_host_preference,
    )

    return {
        "ok": True,
        "mootdx_installed": mootdx_ok,
        "eastmoney_push2": {
            "preference": read_push2_host_preference(),
            "choices": ["auto", *PUSH2_HOST_CHOICES],
            "auto_order": list(AUTO_HOST_ORDER),
        },
        "profile": profile,
        "bar_mode": bar_mode,
        "use_data_registry": use_reg,
        "registry_enabled_for_bars": use_reg or bar_mode == "raw",
        "mootdx_local": _mootdx_local_detail(),
        "mootdx_online": _mootdx_online_detail(),
        "providers": providers,
        "domains": domains,
        "recent_bar_batches": bar_batches,
        "management": {
            "docker_env": [
                "INSTOCK_TDX_DIR=/tdx",
                "INSTOCK_BAR_MODE=raw",
                "INSTOCK_USE_DATA_REGISTRY=1",
                "INSTOCK_DATA_PROFILE=backtest",
            ],
            "docker_volume": "- /path/to/tdx:/tdx:ro",
            "verify_cli": [
                "docker exec InStock python3 /data/InStock/scripts/verify_tdx_local.py --code 600000",
                "docker exec InStock python3 /data/InStock/scripts/verify_mootdx_online.py",
            ],
            "doc": "docs/plan/data-domains.md",
        },
    }


def verify_eastmoney() -> Dict[str, Any]:
    """同步快速探测（无实时日志）。页面测试请用 eastmoney_probe_service 后台接口。"""
    from instock.core.eastmoney_push2 import probe_push2_clist, read_push2_host_preference

    return probe_push2_clist(read_push2_host_preference())


def verify_provider(provider_id: str, code: str = "600000") -> Dict[str, Any]:
    """页面触发的单项连通性检测。"""
    if provider_id == "eastmoney":
        return verify_eastmoney()
    if provider_id == "mootdx_local":
        from instock.core.data.providers.mootdx_local import Provider

        prov = Provider()
        if not tdx_dir():
            return {"ok": False, "error": "INSTOCK_TDX_DIR 未配置"}
        hc = prov.healthcheck()
        res = prov.fetch_bars(code, "20240101", adjust="raw")
        return {
            "ok": hc and res.ok and res.data is not None and not res.data.empty,
            "healthcheck": hc,
            "rows": int(len(res.data)) if res.ok and res.data is not None else 0,
            "error": res.error,
            "provider_id": provider_id,
            "code": code,
        }
    if provider_id == "mootdx_online":
        from instock.core.data.providers.mootdx_online import Provider

        prov = Provider()
        hc = prov.healthcheck()
        res = prov.fetch_bars(code, "20240101", adjust="raw")
        return {
            "ok": hc and res.ok and res.data is not None and not res.data.empty,
            "healthcheck": hc,
            "rows": int(len(res.data)) if res.ok and res.data is not None else 0,
            "error": res.error,
            "provider_id": provider_id,
            "code": code,
        }
    return {"ok": False, "error": f"不支持 verify: {provider_id}"}
