# -*- coding: utf-8 -*-
"""数据管线：交易日历落库、质量校验、断档检测、采集抽象。"""


def get_default_market_data_source(*args, **kwargs):
    from instock.core.pipeline.data_source import get_default_market_data_source as _impl

    return _impl(*args, **kwargs)

__all__ = ["get_default_market_data_source"]
