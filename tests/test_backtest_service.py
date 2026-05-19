import unittest

import pandas as pd


class BacktestEngineTests(unittest.TestCase):
    def test_moving_average_run_outputs_ui_contract(self):
        from instock.core.backtest.engine import run_moving_average_backtest

        bars_by_code = {
            "600000": pd.DataFrame(
                [
                    {"date": "2024-01-02", "open": 10.0, "close": 10.0},
                    {"date": "2024-01-03", "open": 10.0, "close": 11.0},
                    {"date": "2024-01-04", "open": 11.0, "close": 12.0},
                    {"date": "2024-01-05", "open": 12.0, "close": 11.0},
                    {"date": "2024-01-08", "open": 11.0, "close": 10.0},
                    {"date": "2024-01-09", "open": 10.0, "close": 9.0},
                ]
            )
        }

        result = run_moving_average_backtest(
            run_id="unit-run",
            title="unit",
            bars_by_code=bars_by_code,
            initial_cash=100000.0,
            fast=2,
            slow=3,
        )

        self.assertEqual(result["id"], "unit-run")
        self.assertEqual(result["status"], "success")
        self.assertGreater(len(result["equity"]["time"]), 0)
        self.assertIn("orders", result)
        self.assertIn("trades", result)
        self.assertIn("positions", result)
        self.assertIn("dailyAccounts", result)
        self.assertGreaterEqual(len(result["orders"]), 1)
        self.assertGreaterEqual(len(result["trades"]), 1)
        self.assertIn("totalReturn", result["metrics"])
        self.assertIn("maxDrawdown", result["metrics"])
        self.assertEqual(result["lineage"]["profile"], "backtest")
        self.assertEqual(result["params"]["matchPrice"], "next_open")

    def test_signal_uses_next_open_without_lookahead(self):
        from instock.core.backtest.engine import run_moving_average_backtest

        bars_by_code = {
            "600000": pd.DataFrame(
                [
                    {"date": "2024-01-02", "open": 10.0, "close": 10.0},
                    {"date": "2024-01-03", "open": 10.0, "close": 11.0},
                    {"date": "2024-01-04", "open": 99.0, "close": 12.0},
                    {"date": "2024-01-05", "open": 13.0, "close": 13.0},
                ]
            )
        }

        result = run_moving_average_backtest(
            run_id="next-open-run",
            title="unit",
            bars_by_code=bars_by_code,
            initial_cash=100000.0,
            fast=2,
            slow=3,
        )

        first_buy = next(t for t in result["trades"] if t["side"] == "buy")
        self.assertEqual(first_buy["date"], "2024-01-05")
        self.assertEqual(first_buy["price"], 13.0)


class BacktestServiceTests(unittest.TestCase):
    def test_start_run_returns_detail_with_orders_and_curves(self):
        from instock.web import backtest_service as svc

        svc.reset_for_tests()
        run = svc.start_run(
            {
                "title": "单元测试回测",
                "dateFrom": "2024-01-02",
                "dateTo": "2024-01-09",
                "universe": {"type": "codes", "codes": ["600000"]},
                "strategy": {"id": "moving_average_cross", "params": {"fast": 2, "slow": 3}},
                "broker": {"initialCash": 100000},
                "data": {"requirePrerequisites": False},
            },
            run_inline=True,
        )

        detail = svc.get_run(run["id"])

        self.assertEqual(detail["status"], "success")
        self.assertTrue(detail["orders"])
        self.assertTrue(detail["trades"])
        self.assertTrue(detail["equity"]["time"])
        self.assertTrue(detail["drawdown"]["time"])
        self.assertTrue(detail["dailyAccounts"])
        self.assertEqual(svc.list_runs(10)[0]["id"], run["id"])

    def test_cancelled_run_is_not_overwritten_by_success(self):
        from instock.web import backtest_service as svc

        svc.reset_for_tests()
        run = svc.start_run(
            {
                "title": "取消测试",
                "dateFrom": "2024-01-02",
                "dateTo": "2024-01-09",
                "universe": {"type": "codes", "codes": ["600000"]},
                "strategy": {"id": "moving_average_cross", "params": {"fast": 2, "slow": 3}},
                "broker": {"initialCash": 100000},
                "data": {"requirePrerequisites": False},
            },
            run_inline=False,
        )
        svc.cancel_run(run["id"])
        svc._execute(run["id"], {"data": {"requirePrerequisites": False}})

        self.assertEqual(svc.get_run(run["id"])["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
