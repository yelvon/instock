import unittest

import pandas as pd


def _sample_bars():
    return {
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


class BacktestRegistryTests(unittest.TestCase):
    def test_list_strategies_includes_builtin(self):
        from instock.core.backtest.registry import ensure_registry, list_strategies

        ensure_registry()
        ids = {s["id"] for s in list_strategies()}
        self.assertIn("moving_average_cross", ids)
        self.assertIn("buy_and_hold", ids)
        try:
            import instock.core.tablestructure  # noqa: F401

            self.assertIn("screening_bridge", ids)
        except ImportError:
            pass

    def test_buy_and_hold_runs(self):
        from instock.core.backtest.registry import run_backtest

        result = run_backtest(
            run_id="bah",
            title="bah",
            strategy_id="buy_and_hold",
            strategy_params={},
            bars_by_code=_sample_bars(),
            initial_cash=100000.0,
            max_weight_per_symbol=1.0,
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["params"]["strategy"], "buy_and_hold")

    def test_unknown_strategy_raises(self):
        from instock.core.backtest.registry import run_backtest

        with self.assertRaises(ValueError):
            run_backtest(
                run_id="x",
                title="x",
                strategy_id="not_exists",
                strategy_params={},
                bars_by_code=_sample_bars(),
            )

    def test_t1_cannot_sell_on_buy_day(self):
        from instock.core.backtest.registry import run_backtest

        bars = {
            "600000": pd.DataFrame(
                [
                    {"date": "2024-01-02", "open": 10.0, "close": 10.0},
                    {"date": "2024-01-03", "open": 10.0, "close": 20.0},
                    {"date": "2024-01-04", "open": 20.0, "close": 5.0},
                    {"date": "2024-01-05", "open": 5.0, "close": 5.0},
                ]
            )
        }
        result = run_backtest(
            run_id="t1",
            title="t1",
            strategy_id="moving_average_cross",
            strategy_params={"fast": 1, "slow": 2},
            bars_by_code=bars,
            initial_cash=1000000.0,
            max_weight_per_symbol=0.5,
        )
        buys = [t for t in result["trades"] if t["side"] == "buy"]
        if not buys:
            self.skipTest("no buy in fixture")
        buy_date = buys[0]["date"]
        sells_same = [t for t in result["trades"] if t["side"] == "sell" and t["date"] == buy_date]
        self.assertEqual(sells_same, [])

    def test_service_dispatches_buy_and_hold(self):
        from instock.web import backtest_service as svc

        svc.reset_for_tests()
        run = svc.start_run(
            {
                "title": "bah svc",
                "dateFrom": "2024-01-02",
                "dateTo": "2024-01-09",
                "universe": {"type": "codes", "codes": ["600000"]},
                "strategy": {"id": "buy_and_hold", "params": {}},
                "broker": {"initialCash": 100000},
                "data": {"requirePrerequisites": False},
            },
            run_inline=True,
        )
        detail = svc.get_run(run["id"])
        self.assertEqual(detail["status"], "success")
        self.assertEqual(detail["params"]["strategy"], "buy_and_hold")


if __name__ == "__main__":
    unittest.main()
