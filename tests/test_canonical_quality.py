# -*- coding: utf-8 -*-
"""标准行情合并规则单元测试（无数据库）。"""

import unittest

from instock.core.canonical import quality as q


class TestCanonicalQuality(unittest.TestCase):
    def test_completeness_complete(self):
        row = {"open": 1, "close": 2, "high": 3, "low": 0.5, "volume": 1000}
        self.assertGreaterEqual(q.completeness_score(row), 80)

    def test_price_conflict(self):
        ex = {"close": 10.0}
        inc = {"close": 10.5}
        self.assertTrue(q.price_conflict(ex, inc))
        inc2 = {"close": 10.05}
        self.assertFalse(q.price_conflict(ex, inc2))

    def test_fields_missing_fill(self):
        ex = {"open": 1, "close": None, "high": 3, "low": 0.5, "volume": 100}
        self.assertIn("close", q.fields_missing(ex))


if __name__ == "__main__":
    unittest.main()
