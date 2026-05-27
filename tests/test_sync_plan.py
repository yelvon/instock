# -*- coding: utf-8 -*-
"""sync_plan 日期解析与缺日过滤（无数据库）。"""

import unittest

import pandas as pd

from instock.core.canonical.sync_plan import (
    filter_bars_to_missing_dates,
    resolve_sync_range,
)


class TestSyncPlan(unittest.TestCase):
    def test_resolve_sync_range(self):
        d0, d1 = resolve_sync_range("2024-01-02", "2024-01-10")
        self.assertEqual(d0.isoformat(), "2024-01-02")
        self.assertEqual(d1.isoformat(), "2024-01-10")

    def test_resolve_yyyymmdd(self):
        d0, d1 = resolve_sync_range("20240102", "20240110")
        self.assertEqual(d0.isoformat(), "2024-01-02")

    def test_filter_missing_dates(self):
        df = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
                "close": [1.0, 2.0, 3.0],
            }
        )
        out = filter_bars_to_missing_dates(df, ["2024-01-03"])
        self.assertEqual(len(out), 1)
        self.assertEqual(str(out.iloc[0]["date"])[:10], "2024-01-03")


if __name__ == "__main__":
    unittest.main()
