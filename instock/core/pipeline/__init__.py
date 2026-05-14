# -*- coding: utf-8 -*-
"""数据管线：交易日历落库、质量校验、断档检测、采集抽象。"""

from instock.core.pipeline.data_source import get_default_market_data_source

__all__ = ["get_default_market_data_source"]
