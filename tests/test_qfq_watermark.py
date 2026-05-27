# -*- coding: utf-8 -*-
"""qfq 水位表 code 列宽与全局键。"""

import unittest

from instock.core.adjustment.corporate_action_store import GLOBAL_WATERMARK_CODE, _norm_stock_code


class TestQfqWatermark(unittest.TestCase):
    def test_global_code_fits_varchar16(self):
        self.assertEqual(GLOBAL_WATERMARK_CODE, "__global__")
        self.assertLessEqual(len(GLOBAL_WATERMARK_CODE), 16)

    def test_norm_stock_code(self):
        self.assertEqual(_norm_stock_code("600000"), "600000")
        self.assertEqual(_norm_stock_code("1"), "000001")
        self.assertEqual(_norm_stock_code(""), "")


if __name__ == "__main__":
    unittest.main()
