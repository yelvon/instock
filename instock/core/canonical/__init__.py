# -*- coding: utf-8 -*-
"""标准行情库：多源独立补数、幂等合并、回测统一读取。"""

from instock.core.canonical.reader import load_canonical_bars
from instock.core.canonical.writer import CanonicalBarWriter, MergeStats

__all__ = ["CanonicalBarWriter", "MergeStats", "load_canonical_bars"]
