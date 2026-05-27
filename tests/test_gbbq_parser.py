# -*- coding: utf-8 -*-
"""gbbq 路径与日期解析。"""

import pandas as pd

from instock.core.adjustment.gbbq_reader import find_gbbq_path, events_for_code, parse_gbbq_datetime
from instock.core.data.profile import tdx_dir


def test_parse_gbbq_datetime_int_yyyymmdd():
    s = pd.Series([19900301, 20240604, 0, None])
    out = parse_gbbq_datetime(s)
    assert str(out.iloc[0].date()) == "1990-03-01"
    assert str(out.iloc[1].date()) == "2024-06-04"
    assert pd.isna(out.iloc[2])
    assert pd.isna(out.iloc[3])


def test_find_gbbq_path_optional():
    p = find_gbbq_path(tdx_dir())
    if p is None:
        return
    assert p.is_file()


def test_events_for_code_empty():
    ev = events_for_code(pd.DataFrame(), "600000")
    assert ev.empty
