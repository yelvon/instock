# -*- coding: utf-8 -*-
"""gbbq 路径与 events 映射（无真实 gbbq 文件时跳过）。"""

from instock.core.adjustment.gbbq_reader import find_gbbq_path, events_for_code
from instock.core.data.profile import tdx_dir


def test_find_gbbq_path_optional():
    p = find_gbbq_path(tdx_dir())
    if p is None:
        return
    assert p.is_file()


def test_events_for_code_empty():
    import pandas as pd

    ev = events_for_code(pd.DataFrame(), "600000")
    assert ev.empty
