# -*- coding: utf-8 -*-

import unittest

import pandas as pd


def _sample_bars():
    rows = []
    price = 10.0
    dates = pd.bdate_range("2024-01-02", periods=40)
    for i, d in enumerate(dates):
        price += 0.15 if i % 5 < 3 else -0.1
        o = price - 0.05
        c = price
        rows.append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "open": round(o, 2),
                "high": round(max(o, c) + 0.1, 2),
                "low": round(min(o, c) - 0.1, 2),
                "close": round(c, 2),
                "volume": 1000000 + i * 1000,
            }
        )
    return {"600000": pd.DataFrame(rows)}


class BacktestRegistryTests(unittest.TestCase):
    def setUp(self):
        from instock.core.backtest.registry import reset_registry_for_tests

        reset_registry_for_tests()

    def test_list_strategies_includes_builtin(self):
        from instock.core.backtest.registry import ensure_registry, list_strategies

        ensure_registry()
        ids = {s["id"] for s in list_strategies()}
        self.assertIn("moving_average_cross", ids)
        self.assertIn("buy_and_hold", ids)
        self.assertIn("rsi_reversal", ids)
        self.assertIn("macd_cross", ids)
        self.assertIn("bollinger_breakout", ids)
        try:
            import instock.core.tablestructure as tbs  # noqa: F401

            self.assertIn("screening_bridge", ids)
            self.assertIn("screening_cn_stock_strategy_enter", ids)
        except ImportError:
            pass

    def test_list_strategies_has_params_meta(self):
        from instock.core.backtest.registry import ensure_registry, list_strategies

        ensure_registry()
        ma = next(s for s in list_strategies() if s["id"] == "moving_average_cross")
        self.assertEqual(ma["category"], "technical")
        self.assertTrue(ma["params"])
        self.assertEqual(ma["params"][0]["key"], "fast")
        self.assertIn("label", ma["params"][0])

    def test_validate_moving_average_fast_slow(self):
        from instock.core.backtest.registry import ensure_registry, validate_params

        ensure_registry()
        with self.assertRaises(ValueError):
            validate_params("moving_average_cross", {"fast": 20, "slow": 5})

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

    def test_rsi_reversal_runs(self):
        from instock.core.backtest.registry import run_backtest

        result = run_backtest(
            run_id="rsi",
            title="rsi",
            strategy_id="rsi_reversal",
            strategy_params={"period": 6, "oversold": 40, "overbought": 60},
            bars_by_code=_sample_bars(),
            initial_cash=1000000.0,
            max_weight_per_symbol=0.5,
        )
        self.assertEqual(result["status"], "success")

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
                    {"date": "2024-01-03", "open": 10.0, "close": 11.0},
                    {"date": "2024-01-04", "open": 11.0, "close": 12.0},
                    {"date": "2024-01-05", "open": 12.0, "close": 11.0},
                    {"date": "2024-01-08", "open": 11.0, "close": 10.0},
                    {"date": "2024-01-09", "open": 10.0, "close": 9.0},
                ]
            )
        }
        result = run_backtest(
            run_id="t1",
            title="t1",
            strategy_id="moving_average_cross",
            strategy_params={"fast": 2, "slow": 3},
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

    def test_service_rejects_invalid_params(self):
        from instock.web import backtest_service as svc

        svc.reset_for_tests()
        with self.assertRaises(ValueError):
            svc.start_run(
                {
                    "title": "bad",
                    "dateFrom": "2024-01-02",
                    "dateTo": "2024-01-09",
                    "universe": {"type": "codes", "codes": ["600000"]},
                    "strategy": {"id": "moving_average_cross", "params": {"fast": 30, "slow": 5}},
                    "broker": {"initialCash": 100000},
                    "data": {"requirePrerequisites": False},
                },
                run_inline=True,
            )


if __name__ == "__main__":
    unittest.main()
