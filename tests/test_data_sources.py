import os
import sys
import types
import unittest
from unittest.mock import patch

import pandas as pd


class _JsonResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class EastmoneyHistTests(unittest.TestCase):
    def test_stock_hist_does_not_require_code_id_map(self):
        from instock.core.crawling import stock_hist_em as she

        payload = {
            "data": {
                "klines": [
                    "2024-01-02,7.00,7.10,7.20,6.90,100,71000.00,4.23,1.43,0.10,0.50",
                    "2024-01-03,7.10,7.20,7.30,7.00,120,86400.00,4.17,1.41,0.10,0.60",
                ]
            }
        }

        with patch.object(
            she,
            "code_id_map_em",
            side_effect=AssertionError("stock_zh_a_hist should not call code_id_map_em"),
        ), patch.object(she.fetcher, "make_request", return_value=_JsonResponse(payload)):
            df = she.stock_zh_a_hist("600000", start_date="20240101", adjust="")

        self.assertEqual(len(df), 2)
        self.assertEqual(list(df.columns), ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"])
        self.assertEqual(df.iloc[-1]["日期"], "2024-01-03")


class EastmoneyFetcherTests(unittest.TestCase):
    def test_session_ignores_system_proxy_by_default(self):
        from instock.core.eastmoney_fetcher import eastmoney_fetcher

        fetcher = eastmoney_fetcher()

        self.assertFalse(fetcher.session.trust_env)

    def test_cookie_is_opt_in(self):
        from instock.core.eastmoney_fetcher import eastmoney_fetcher

        with patch.dict(
            os.environ,
            {"EAST_MONEY_COOKIE": "stale-cookie", "INSTOCK_EM_USE_COOKIE": ""},
            clear=False,
        ):
            fetcher = eastmoney_fetcher()

        self.assertNotIn("Cookie", fetcher.session.headers)

    def test_cookie_can_be_enabled_explicitly(self):
        from instock.core.eastmoney_fetcher import eastmoney_fetcher

        with patch.dict(
            os.environ,
            {"EAST_MONEY_COOKIE": "fresh-cookie", "INSTOCK_EM_USE_COOKIE": "1"},
            clear=False,
        ):
            fetcher = eastmoney_fetcher()

        self.assertEqual(fetcher.session.headers.get("Cookie"), "fresh-cookie")

    def test_probe_request_uses_configured_session(self):
        from instock.core.eastmoney_fetcher import eastmoney_fetcher

        fetcher = eastmoney_fetcher()
        fake_session = unittest.mock.Mock()
        fake_session.get.return_value = _JsonResponse({"ok": True})

        with patch("instock.core.eastmoney_fetcher.requests.get") as raw_get, patch(
            "instock.core.eastmoney_fetcher.requests.Session", return_value=fake_session
        ):
            response = fetcher.make_probe_request("https://example.test", params={"a": "1"})

        raw_get.assert_not_called()
        self.assertFalse(fake_session.trust_env)
        fake_session.headers.update.assert_called()
        fake_session.get.assert_called_once()
        self.assertEqual(response.json(), {"ok": True})


class SpotSourceTests(unittest.TestCase):
    def test_default_spot_source_is_auto_fallback(self):
        from instock.core.spot_source import SPOT_SOURCE_AUTO, effective_spot_source

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(effective_spot_source(), SPOT_SOURCE_AUTO)


class TushareProviderTests(unittest.TestCase):
    def test_fetch_bars_normalizes_daily_rows(self):
        from instock.core.data.providers.tushare import Provider

        calls = {}

        class _Api:
            def daily(self, **kwargs):
                calls.update(kwargs)
                return pd.DataFrame(
                    [
                        {
                            "trade_date": "20240103",
                            "open": 7.1,
                            "high": 7.3,
                            "low": 7.0,
                            "close": 7.2,
                            "vol": 120.0,
                            "amount": 86.4,
                            "pct_chg": 1.41,
                            "change": 0.1,
                        },
                        {
                            "trade_date": "20240102",
                            "open": 7.0,
                            "high": 7.2,
                            "low": 6.9,
                            "close": 7.1,
                            "vol": 100.0,
                            "amount": 71.0,
                            "pct_chg": 1.43,
                            "change": 0.1,
                        },
                    ]
                )

        fake_tushare = types.SimpleNamespace(pro_api=lambda token: _Api())

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "unit-test-token"}, clear=False), patch.dict(
            sys.modules, {"tushare": fake_tushare}
        ):
            result = Provider().fetch_bars("600000", "20240101", "20240131", adjust="raw")

        self.assertTrue(result.ok)
        self.assertEqual(result.provider_id, "tushare")
        self.assertEqual(calls["ts_code"], "600000.SH")
        self.assertEqual(calls["start_date"], "20240101")
        self.assertEqual(calls["end_date"], "20240131")
        self.assertEqual(list(result.data["date"]), ["2024-01-02", "2024-01-03"])
        self.assertEqual(float(result.data.iloc[0]["volume"]), 10000.0)
        self.assertEqual(float(result.data.iloc[0]["amount"]), 71000.0)
        self.assertEqual(float(result.data.iloc[1]["quote_change"]), 1.41)

    def test_token_file_is_used_when_env_is_empty(self):
        from instock.core.data.providers.tushare import read_tushare_token

        with patch.dict(os.environ, {"TUSHARE_TOKEN": ""}, clear=False), patch(
            "instock.core.data.providers.tushare.TUSHARE_TOKEN_FILE"
        ) as token_file:
            token_file.exists.return_value = True
            token_file.read_text.return_value = " file-token \n"
            self.assertEqual(read_tushare_token(), "file-token")


class StockFetchNormalizeTests(unittest.TestCase):
    def test_align_hist_dataframe_maps_eastmoney_chinese_columns(self):
        from instock.core.stockfetch import _align_hist_dataframe

        raw = pd.DataFrame(
            [
                {
                    "日期": "2024-01-02",
                    "开盘": 7.0,
                    "收盘": 7.1,
                    "最高": 7.2,
                    "最低": 6.9,
                    "成交量": 100.0,
                    "成交额": 71000.0,
                    "振幅": 4.23,
                    "涨跌幅": 1.43,
                    "涨跌额": 0.1,
                    "换手率": 0.5,
                }
            ]
        )

        df = _align_hist_dataframe(raw)

        self.assertEqual(list(df.columns), ["date", "open", "close", "high", "low", "volume", "amount", "amplitude", "quote_change", "ups_downs", "turnover"])
        self.assertEqual(df.iloc[0]["date"], "2024-01-02")
        self.assertEqual(float(df.iloc[0]["open"]), 7.0)
        self.assertEqual(float(df.iloc[0]["close"]), 7.1)
        self.assertEqual(float(df.iloc[0]["amount"]), 71000.0)


class DataSourcesServiceTests(unittest.TestCase):
    def test_build_report_exposes_tushare_status(self):
        import instock.web.data_sources_service as dss

        fake_tushare = types.SimpleNamespace(
            pro_api=lambda token: types.SimpleNamespace(
                daily=lambda **kwargs: pd.DataFrame(
                    [
                        {
                            "trade_date": "20240102",
                            "open": 7.0,
                            "high": 7.2,
                            "low": 6.9,
                            "close": 7.1,
                            "vol": 100.0,
                            "amount": 71.0,
                            "pct_chg": 1.43,
                            "change": 0.1,
                        }
                    ]
                )
            )
        )

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "unit-test-token"}, clear=False), patch.dict(
            sys.modules, {"tushare": fake_tushare}
        ), patch.object(dss, "_mootdx_local_detail", return_value={"provider_id": "mootdx_local"}), patch.object(
            dss, "_mootdx_online_detail", return_value={"provider_id": "mootdx_online"}
        ):
            report = dss.build_report()

        provider_ids = [p["provider_id"] for p in report["providers"]]
        self.assertIn("tushare", provider_ids)
        self.assertTrue(report["tushare"]["token_configured"])
        self.assertEqual(report["tushare"]["token_source"], "env:TUSHARE_TOKEN")
        self.assertTrue(report["tushare"]["sample_ok"])
        self.assertEqual(report["tushare"]["sample_rows"], 1)

    def test_verify_provider_supports_tushare(self):
        import instock.web.data_sources_service as dss

        fake_tushare = types.SimpleNamespace(
            pro_api=lambda token: types.SimpleNamespace(
                daily=lambda **kwargs: pd.DataFrame(
                    [
                        {
                            "trade_date": "20240102",
                            "open": 7.0,
                            "high": 7.2,
                            "low": 6.9,
                            "close": 7.1,
                            "vol": 100.0,
                            "amount": 71.0,
                            "pct_chg": 1.43,
                            "change": 0.1,
                        }
                    ]
                )
            )
        )

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "unit-test-token"}, clear=False), patch.dict(
            sys.modules, {"tushare": fake_tushare}
        ):
            out = dss.verify_provider("tushare", "600000")

        self.assertTrue(out["ok"])
        self.assertEqual(out["provider_id"], "tushare")
        self.assertEqual(out["rows"], 1)
        self.assertEqual(out["code"], "600000")


class BarDataSourceSelectionTests(unittest.TestCase):
    def test_registry_can_force_tushare_bar_provider(self):
        from instock.core.data.registry import DataRegistry

        cfg = {
            "providers": {},
            "domains": {
                "daily_bar_raw": {
                    "profiles": {
                        "live": {
                            "chain": [
                                {"provider": "mootdx_online"},
                                {"provider": "tushare"},
                                {"provider": "eastmoney"},
                            ]
                        }
                    }
                }
            },
        }

        with patch.dict(
            os.environ,
            {
                "INSTOCK_DATA_PROFILE": "live",
                "INSTOCK_BAR_DATA_SOURCE": "tushare",
                "INSTOCK_BARS_MOOTDX_ONLY": "",
            },
            clear=False,
        ):
            chain = DataRegistry(cfg).resolve_chain("daily_bar_raw", "live")

        self.assertEqual([s.provider_id for s in chain], ["tushare"])

    def test_sync_job_env_for_tushare_does_not_force_mootdx_only(self):
        import instock.web.sync_job_service as svc

        env = svc._bar_data_source_env("tushare")

        self.assertEqual(env["INSTOCK_BAR_DATA_SOURCE"], "tushare")
        self.assertEqual(env["INSTOCK_USE_DATA_REGISTRY"], "1")
        self.assertEqual(env["INSTOCK_BAR_MODE"], "raw")
        self.assertNotIn("INSTOCK_BARS_MOOTDX_ONLY", env)

    def test_hosts_for_clist_requests_fixed_host_still_tries_fallbacks(self):
        from instock.core.eastmoney_push2 import hosts_for_clist_requests

        with patch.dict(os.environ, {"INSTOCK_EM_PUSH2_HOST": "82"}, clear=False):
            hosts = hosts_for_clist_requests("82")
        self.assertEqual(hosts[0], "82")
        self.assertIn("88", hosts)
        self.assertIn("80", hosts)

    def test_allow_eastmoney_hist_fallback_respects_bar_source(self):
        from instock.core.data.profile import allow_eastmoney_hist_fallback

        with patch.dict(os.environ, {"INSTOCK_BAR_DATA_SOURCE": "tushare"}, clear=False):
            self.assertFalse(allow_eastmoney_hist_fallback())
        with patch.dict(
            os.environ,
            {"INSTOCK_BAR_DATA_SOURCE": "auto", "INSTOCK_BARS_MOOTDX_ONLY": "1"},
            clear=False,
        ):
            self.assertFalse(allow_eastmoney_hist_fallback())
        with patch.dict(
            os.environ,
            {"INSTOCK_BAR_DATA_SOURCE": "auto", "INSTOCK_BARS_MOOTDX_ONLY": ""},
            clear=False,
        ):
            self.assertTrue(allow_eastmoney_hist_fallback())


if __name__ == "__main__":
    unittest.main()
