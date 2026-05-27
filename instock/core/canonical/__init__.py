# -*- coding: utf-8 -*-
"""标准行情库：多源独立补数、幂等合并、回测统一读取。

子模块请显式导入，避免在包 __init__ 中加载 reader/writer 引发与 adjustment 的循环依赖。
"""

__all__ = [
    "CanonicalBarWriter",
    "MergeStats",
    "load_canonical_bars",
]
