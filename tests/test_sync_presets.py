# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from unittest.mock import patch

from instock.web import sync_presets as presets


class SyncPresetsTests(unittest.TestCase):
    def test_list_presets_has_tushare_kline(self):
        ids = {p["id"] for p in presets.list_presets()}
        self.assertIn(presets.PRESET_TUSHARE_KLINE, ids)

    def test_build_scheduler_merge_dedupes(self):
        existing = [
            {
                "title": "工作日-股票快照",
                "job_id": "basic_data_daily_job",
                "spot_data_source": "eastmoney",
                "weekdays": [0],
                "times": ["09:00"],
            }
        ]
        merged = presets.build_scheduler_from_preset(
            presets.PRESET_TUSHARE_KLINE,
            mode="merge",
            existing=existing,
        )
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[0]["spot_data_source"], "eastmoney")
        extra = presets.build_scheduler_from_preset(
            presets.PRESET_TUSHARE_KLINE,
            mode="merge",
            existing=[],
        )
        self.assertGreater(len(extra), 1)

    def test_apply_preset_writes_prefs(self):
        with tempfile.TemporaryDirectory() as td:
            prefs_path = os.path.join(td, "sync_preferences.json")
            sched_path = os.path.join(td, "scheduler.json")
            with patch("instock.web.sync_preferences._PREFS_PATH", prefs_path):
                with patch("instock.web.scheduler_service._SCHEDULER_PATH", sched_path):
                    result = presets.apply_preset(
                        presets.PRESET_TUSHARE_KLINE,
                        scheduler_mode="keep",
                    )
            self.assertEqual(result["prefs"]["default_bar_data_source"], "tushare")
            self.assertEqual(result["prefs"]["default_spot_data_source"], "auto")


if __name__ == "__main__":
    unittest.main()
