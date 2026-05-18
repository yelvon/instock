# -*- coding: utf-8 -*-
"""加载 registry.yaml，解析 chain/enrich，调度 Provider。"""

from __future__ import annotations

import datetime
import importlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from instock.core.data.profile import (
    PROFILE_BACKTEST,
    bars_mootdx_only,
    effective_data_profile,
    effective_bar_mode,
    tencent_enrich_enabled,
    tdx_dir,
)
from instock.core.data.provider import DomainProvider, FetchResult

_REGISTRY: Optional["DataRegistry"] = None
_LOG = logging.getLogger(__name__)


@dataclass
class ChainStep:
    provider_id: str
    strict: bool = False
    when: Optional[str] = None
    fill_mode: Optional[str] = None
    mode: Optional[str] = None


def _load_yaml(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        raise ImportError(
            "加载 registry.yaml 需要 PyYAML：pip install pyyaml"
        ) from None


def _step_from_dict(d: Dict[str, Any]) -> ChainStep:
    return ChainStep(
        provider_id=str(d.get("provider", "")),
        strict=bool(d.get("strict", False)),
        when=d.get("when"),
        fill_mode=d.get("fill_mode"),
        mode=d.get("mode"),
    )


def _step_applies(step: ChainStep) -> bool:
    if step.when == "tdx_dir_set":
        return bool(tdx_dir())
    return True


class DataRegistry:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config is None:
            cfg_path = Path(__file__).resolve().parent / "registry.yaml"
            config = _load_yaml(cfg_path)
        self._config = config
        self._provider_cache: Dict[str, DomainProvider] = {}

    def get_provider(self, provider_id: str) -> DomainProvider:
        if provider_id in self._provider_cache:
            return self._provider_cache[provider_id]
        pinfo = (self._config.get("providers") or {}).get(provider_id)
        if not pinfo:
            raise KeyError(f"未知 provider: {provider_id}")
        mod_path = pinfo["module"]
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, "Provider", None)
        if cls is None:
            raise ImportError(f"{mod_path} 缺少 Provider 类")
        inst = cls()
        self._provider_cache[provider_id] = inst
        return inst

    def resolve_chain(self, domain_id: str, profile: Optional[str] = None) -> List[ChainStep]:
        prof = effective_data_profile(profile)
        dom = (self._config.get("domains") or {}).get(domain_id) or {}
        prof_cfg = (dom.get("profiles") or {}).get(prof) or {}
        steps = [_step_from_dict(x) for x in (prof_cfg.get("chain") or [])]
        steps = [s for s in steps if _step_applies(s)]
        if bars_mootdx_only() and domain_id in ("daily_bar_raw", "daily_bar"):
            steps = [s for s in steps if s.provider_id in ("mootdx_local", "mootdx_online")]
        return steps

    def resolve_enrich(self, domain_id: str, profile: Optional[str] = None) -> List[ChainStep]:
        prof = effective_data_profile(profile)
        if domain_id == "daily_spot_snapshot" and not tencent_enrich_enabled(prof):
            return []
        dom = (self._config.get("domains") or {}).get(domain_id) or {}
        prof_cfg = (dom.get("profiles") or {}).get(prof) or {}
        steps = [_step_from_dict(x) for x in (prof_cfg.get("enrich") or [])]
        return [s for s in steps if _step_applies(s)]

    def fetch_domain(
        self,
        domain_id: str,
        trade_date: Optional[datetime.date] = None,
        *,
        profile: Optional[str] = None,
        code: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> FetchResult:
        prof = effective_data_profile(profile)
        chain = self.resolve_chain(domain_id, prof)
        last: Optional[FetchResult] = None
        mixed = False

        if domain_id in ("daily_spot_snapshot",):
            if trade_date is None:
                trade_date = datetime.date.today()
            for step in chain:
                try:
                    prov = self.get_provider(step.provider_id)
                    res = prov.fetch_spot(
                        trade_date,
                        fill_mode=step.fill_mode,
                        strict=step.strict,
                    )
                    res.domain_id = domain_id
                    if res.ok and res.data is not None and not res.data.empty:
                        last = res
                        break
                    if step.strict and prof == PROFILE_BACKTEST:
                        last = res
                        break
                except Exception as e:
                    _LOG.warning("fetch_domain %s %s: %s", domain_id, step.provider_id, e)
                    if step.strict and prof == PROFILE_BACKTEST:
                        return FetchResult(
                            ok=False,
                            error=str(e),
                            provider_id=step.provider_id,
                            domain_id=domain_id,
                            trade_date=trade_date,
                        )
            if last is None or not last.ok or last.data is None or last.data.empty:
                return last or FetchResult(
                    ok=False,
                    error="无可用 spot 数据",
                    domain_id=domain_id,
                    trade_date=trade_date,
                )
            enrich_steps = self.resolve_enrich(domain_id, prof)
            enrich_ids: List[str] = []
            for step in enrich_steps:
                try:
                    prov = self.get_provider(step.provider_id)
                    er = prov.enrich_spot(
                        last.data,
                        trade_date,
                        mode=step.mode or "valuation_only",
                    )
                    if er.ok and er.data is not None:
                        last.data = er.data
                        enrich_ids.append(step.provider_id)
                        mixed = True
                except Exception as e:
                    _LOG.warning("enrich %s: %s", step.provider_id, e)
            last.mixed_source = mixed
            last.metadata["enrich_providers"] = enrich_ids
            return last

        if domain_id in ("daily_bar_raw", "daily_bar"):
            if not code or not date_from:
                return FetchResult(
                    ok=False,
                    error="daily_bar_raw 需要 code 与 date_from",
                    domain_id=domain_id,
                )
            adjust = effective_bar_mode()
            for step in chain:
                try:
                    prov = self.get_provider(step.provider_id)
                    res = prov.fetch_bars(
                        code,
                        date_from,
                        date_to,
                        adjust=adjust,
                        strict=step.strict,
                    )
                    res.domain_id = domain_id
                    if res.ok and res.data is not None and not res.data.empty:
                        return res
                    if step.strict and prof == PROFILE_BACKTEST:
                        return res
                    last = res
                except Exception as e:
                    _LOG.warning("fetch_bars %s: %s", step.provider_id, e)
                    if step.strict and prof == PROFILE_BACKTEST:
                        return FetchResult(
                            ok=False,
                            error=str(e),
                            provider_id=step.provider_id,
                            domain_id=domain_id,
                        )
            return last or FetchResult(ok=False, error="无 K 线数据", domain_id=domain_id)

        return FetchResult(ok=False, error=f"未实现域: {domain_id}", domain_id=domain_id)


def get_registry() -> DataRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = DataRegistry()
    return _REGISTRY
