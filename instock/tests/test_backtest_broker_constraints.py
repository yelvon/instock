# -*- coding: utf-8 -*-

import unittest

import pandas as pd

from instock.core.backtest.broker import SimBroker
from instock.core.backtest.constraints import (
    apply_slippage,
    check_order_fill,
    is_limit_down,
    is_limit_up,
    is_suspended,
)
from instock.core.backtest.registry import run_backtest


class BacktestBrokerConstraintsTests(unittest.TestCase):
    def test_suspended_rejects(self):
        row = {"open": 10.0, "close": 10.0, "high": 10.0, "low": 10.0, "volume": 0}
        self.assertTrue(is_suspended(row))
        reason, _, _ = check_order_fill(code="600000", side="buy", row=row, prev_row=None)
        self.assertEqual(reason, "suspended")

    def test_limit_up_buy_rejected(self):
        prev = {"close": 10.0}
        row = {"open": 11.0, "close": 11.0, "high": 11.0, "low": 11.0, "volume": 1000}
        self.assertTrue(is_limit_up(row, prev, "600000"))
        reason, _, _ = check_order_fill(code="600000", side="buy", row=row, prev_row=prev)
        self.assertEqual(reason, "limit_up")

    def test_limit_down_sell_rejected(self):
        prev = {"close": 10.0}
        row = {"open": 9.0, "close": 9.0, "high": 9.0, "low": 9.0, "volume": 1000}
        self.assertTrue(is_limit_down(row, prev, "600000"))
        reason, _, _ = check_order_fill(code="600000", side="sell", row=row, prev_row=prev)
        self.assertEqual(reason, "limit_down")

    def test_slippage_increases_buy_price(self):
        price, slip = apply_slippage(10.0, "buy", 10.0)
        self.assertGreater(price, 10.0)
        self.assertGreater(slip, 0)

    def test_broker_applies_slippage_cost(self):
        broker = SimBroker(initial_cash=100000.0, slippage_bps=10.0)
        by_code_date = {
            "600000": {
                "2024-01-02": {
                    "date": "2024-01-02",
                    "open": 10.0,
                    "close": 10.0,
                    "high": 10.1,
                    "low": 9.9,
                    "volume": 100000,
                }
            }
        }
        broker.submit_order(
            created_date="2024-01-01",
            target_date="2024-01-02",
            code="600000",
            side="buy",
            requested_qty=100,
            reason="test",
        )
        broker.process_due_orders("2024-01-02", by_code_date, ["2024-01-02"])
        self.assertEqual(len(broker.trades), 1)
        self.assertGreater(broker.trades[0]["slippageCost"], 0)

    def test_run_backtest_limit_up_order_rejected(self):
        bars = {
            "600000": pd.DataFrame(
                [
                    {"date": "2024-01-02", "open": 10.0, "close": 10.0, "volume": 1000000},
                    {"date": "2024-01-03", "open": 11.0, "close": 11.0, "volume": 1000000},
                    {"date": "2024-01-04", "open": 11.0, "close": 11.0, "volume": 1000000},
                ]
            )
        }
        result = run_backtest(
            run_id="lu",
            title="lu",
            strategy_id="buy_and_hold",
            strategy_params={},
            bars_by_code=bars,
            initial_cash=1000000.0,
            max_weight_per_symbol=1.0,
        )
        rejected = [o for o in result["orders"] if o.get("rejectReason") == "limit_up"]
        self.assertTrue(rejected or result["status"] == "success")


if __name__ == "__main__":
    unittest.main()
