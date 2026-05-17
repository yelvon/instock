# -*- coding: utf-8 -*-
"""回测主数据：多源 Registry、血缘 batch、Provider 插件。"""

from instock.core.data.provider import FetchResult
from instock.core.data.profile import effective_data_profile, effective_bar_mode
from instock.core.data.registry import DataRegistry, get_registry

__all__ = [
    "FetchResult",
    "DataRegistry",
    "get_registry",
    "effective_data_profile",
    "effective_bar_mode",
]
