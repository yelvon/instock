import datetime
import unittest
from unittest.mock import patch


class BacktestPrerequisitesQualityTest(unittest.TestCase):
    def test_canonical_quality_issues_fail_backtest_prerequisites(self):
        from instock.core.pipeline.backtest_data_prerequisites import check_backtest_data

        with patch(
            "instock.core.pipeline.backtest_data_prerequisites.gaps.detect_canonical_daily_bar_gaps",
            return_value=([], [], {}),
        ), patch(
            "instock.core.pipeline.backtest_data_prerequisites.gaps.detect_canonical_quality_issues",
            create=True,
            return_value={"suspect": 2, "partial": 1, "low_score": 0},
        ), patch(
            "instock.core.canonical.bar_tables.resolve_bar_table",
            return_value="cn_stock_daily_bar",
        ):
            report = check_backtest_data(
                datetime.date(2024, 1, 2),
                datetime.date(2024, 1, 5),
                required_domains=["canonical_daily_bar"],
                codes=["600000"],
                adjust_type="raw",
            )

        self.assertFalse(report.ok)
        self.assertIn("质量", "；".join(report.messages))
        self.assertEqual(report.domains["canonical_daily_bar"].quality_issues["suspect"], 2)


if __name__ == "__main__":
    unittest.main()
