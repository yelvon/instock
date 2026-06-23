import unittest


class BacktestStrategyMetaTest(unittest.TestCase):
    def test_list_strategies_exposes_dependency_domains(self):
        from instock.core.backtest.registry import ensure_registry, list_strategies, reset_registry_for_tests

        reset_registry_for_tests()
        ensure_registry()
        ma = next(s for s in list_strategies() if s["id"] == "moving_average_cross")
        self.assertIn("canonical_daily_bar", ma["dependencyDomains"])


if __name__ == "__main__":
    unittest.main()
