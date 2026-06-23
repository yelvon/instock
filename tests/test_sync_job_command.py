import unittest


class SyncJobCommandTest(unittest.TestCase):
    def test_bar_limit_is_passed_to_canonical_sync_job(self):
        from instock.web.sync_job_service import _build_command

        cmd = _build_command(
            "sync_bars_mootdx_local_job",
            "range",
            "2024-01-01",
            "2024-01-31",
            "",
            qfq_mode="incremental",
            limit=20,
        )

        self.assertIn("--limit", cmd)
        self.assertEqual(cmd[cmd.index("--limit") + 1], "20")

    def test_qfq_range_is_passed_to_derive_job(self):
        from instock.web.sync_job_service import _build_command

        cmd = _build_command(
            "derive_qfq_from_tdx_job",
            "range",
            "2024-01-01",
            "2024-01-31",
            "",
            qfq_mode="incremental",
        )

        self.assertIn("--from-date", cmd)
        self.assertEqual(cmd[cmd.index("--from-date") + 1], "2024-01-01")
        self.assertIn("--to-date", cmd)
        self.assertEqual(cmd[cmd.index("--to-date") + 1], "2024-01-31")


if __name__ == "__main__":
    unittest.main()
