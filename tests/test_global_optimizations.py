# -*- coding: utf-8 -*-
import datetime
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


class TestSchedulerFireHistory(unittest.TestCase):
    def test_append_and_list(self):
        import instock.web.scheduler_service as sch

        with tempfile.TemporaryDirectory() as td:
            hist = os.path.join(td, "fire.json")
            state = os.path.join(td, "state.json")
            with patch.object(sch, "_FIRE_HISTORY_PATH", hist), patch.object(
                sch, "_STATE_PATH", state
            ):
                ev = sch.append_fire_event(
                    schedule_id="s1",
                    schedule_title="测试",
                    job_id="basic_data_daily_job",
                    job_label="快照",
                    trigger_time="09:30",
                    weekday=0,
                    status="triggered",
                    run_id="r1",
                )
                self.assertEqual(ev["status"], "triggered")
                items = sch.list_fire_history(10)
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["run_id"], "r1")


class TestSyncPlanPrefetch(unittest.TestCase):
    def test_plan_with_actual_dates(self):
        from instock.core.canonical.sync_plan import plan_canonical_sync

        d0 = datetime.date(2026, 5, 26)
        d1 = datetime.date(2026, 5, 28)
        with patch(
            "instock.core.canonical.sync_plan.gaps._expected_trade_dates",
            return_value=[d0, d1],
        ):
            plan = plan_canonical_sync(
                "600000",
                "2026-05-26",
                "2026-05-28",
                actual_dates={d0},
            )
            self.assertFalse(plan["skip"])
            self.assertIn("2026-05-28", plan["missing_dates"])


class TestHealthService(unittest.TestCase):
    def test_build_report_mysql_mock(self):
        import instock.web.health_service as hs

        with patch.object(hs, "_check_mysql", return_value={"ok": True}), patch.object(
            hs, "_check_push2", return_value={"ok": False, "error": "x"}
        ), patch.object(hs, "_check_xuangu", return_value={"ok": True}), patch.object(
            hs, "_check_mootdx_local", return_value={"ok": False}
        ), patch.object(hs, "_check_scheduler", return_value={"ok": True}):
            rep = hs.build_health_report()
            self.assertTrue(rep["ok"])
            self.assertIn("suggestions", rep)


if __name__ == "__main__":
    unittest.main()
