# -*- coding: utf-8 -*-

import unittest

from instock.core.backtest.batch_runner import (
    build_walk_forward_payloads,
    expand_param_grid,
    summarize_batch_runs,
)


class BacktestBatchRunnerTests(unittest.TestCase):
    def test_expand_param_grid(self):
        base = {"title": "t", "strategy": {"id": "moving_average_cross", "params": {"fast": 5, "slow": 20}}}
        grid = {"fast": [5, 10], "slow": [20, 30]}
        combos = expand_param_grid(base, grid)
        self.assertEqual(len(combos), 4)
        self.assertEqual(combos[0]["strategy"]["params"]["fast"], 5)

    def test_walk_forward_windows(self):
        base = {"title": "wf", "dateFrom": "2024-01-02", "dateTo": "2024-06-30"}
        jobs = build_walk_forward_payloads(base, train_days=20, test_days=10, step_days=10)
        self.assertTrue(len(jobs) >= 1)
        self.assertIn("dateFrom", jobs[0][1])

    def test_summarize_batch(self):
        summary = summarize_batch_runs(
            [{"status": "success", "metrics": {"totalReturn": 0.1, "sharpe": 1.0}}]
        )
        self.assertEqual(summary["success"], 1)


if __name__ == "__main__":
    unittest.main()
