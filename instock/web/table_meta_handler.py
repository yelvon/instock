#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""表元数据 JSON，供 Vue 数据表页使用。"""

import asyncio
import functools
import json
import os
from abc import ABC

import instock.core.singleton_stock_web_module_data as sswmd
import instock.lib.trade_time as trd
import instock.web.base as webBase


class TableMetaHandler(webBase.BaseHandler, ABC):
    def get(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        name = self.get_argument("table_name", default=None)
        if not name:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少参数 table_name"}, ensure_ascii=False))
            return
        try:
            wm = sswmd.stock_web_module_data().get_data(name)
        except KeyError:
            self.set_status(404)
            self.write(json.dumps({"ok": False, "error": "未知的 table_name"}, ensure_ascii=False))
            return

        run_date, run_date_nph = trd.get_trade_date_last()
        if wm.is_realtime:
            date_now_str = run_date_nph.strftime("%Y-%m-%d")
        else:
            date_now_str = run_date.strftime("%Y-%m-%d")

        def _json_default(o):
            if hasattr(o, "tolist"):
                return o.tolist()
            return str(o)

        try:
            cols = json.loads(json.dumps(wm.column_names, default=_json_default))
        except Exception:
            cols = wm.column_names if isinstance(wm.column_names, list) else []

        payload = {
            "ok": True,
            "table_name": wm.table_name,
            "name": wm.name,
            "is_realtime": bool(wm.is_realtime),
            "date_default": date_now_str,
            "column_names": cols,
        }
        if getattr(wm, "view_modes", None):
            payload["view_modes"] = list(wm.view_modes)
        if getattr(wm, "default_filters", None):
            payload["default_filters"] = dict(wm.default_filters)
        if getattr(wm, "requires_view_filter", False):
            payload["requires_view_filter"] = True
        self.write(json.dumps(payload, ensure_ascii=False))


def _kline_fetch_timeout_sec() -> float:
    try:
        return max(5.0, float(os.environ.get("INSTOCK_KLINE_FETCH_TIMEOUT", "18")))
    except (TypeError, ValueError):
        return 18.0


def _fetch_kline_hist(code: str, date: str):
    import instock.core.stockfetch as stf

    if code.startswith(("1", "5")):
        return stf.fetch_etf_hist((date, code))
    return stf.fetch_stock_hist((date, code))


class KlineBundleApiHandler(webBase.BaseHandler, ABC):
    """GET /instock/api/kline_bundle?code=&date=&name="""

    async def get(self):
        import instock.core.kline.kline_bundle_export as kbe

        self.set_header("Content-Type", "application/json;charset=UTF-8")
        code = self.get_argument("code", default=None, strip=False)
        date = self.get_argument("date", default=None, strip=False)
        name = self.get_argument("name", default="", strip=False)
        if not code or not date:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 code 或 date"}, ensure_ascii=False))
            return

        loop = asyncio.get_running_loop()
        fetch_timeout = _kline_fetch_timeout_sec()
        try:
            stock = await asyncio.wait_for(
                loop.run_in_executor(
                    None, functools.partial(_fetch_kline_hist, code, date)
                ),
                timeout=fetch_timeout,
            )
        except asyncio.TimeoutError:
            self.set_status(504)
            self.write(
                json.dumps(
                    {
                        "ok": False,
                        "error": (
                            f"拉取历史 K 线超时（{int(fetch_timeout)} 秒）。"
                            "指标页需从东方财富等源获取约 3 年日线；"
                            "请确认容器可访问外网，或在本机先打开该股票指标页以生成缓存"
                            "（instock/cache/hist/）。"
                        ),
                    },
                    ensure_ascii=False,
                )
            )
            return
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
            return

        if stock is None or getattr(stock, "empty", True):
            self.set_status(404)
            self.write(
                json.dumps(
                    {
                        "ok": False,
                        "error": (
                            "无法取得行情数据（接口无返回或代码/日期无效）。"
                            "请检查网络与 code/date，或稍后重试。"
                        ),
                    },
                    ensure_ascii=False,
                )
            )
            return

        try:
            bundle = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    functools.partial(kbe.build_kline_bundle, code, date, name, stock),
                ),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            self.set_status(504)
            self.write(
                json.dumps(
                    {"ok": False, "error": "指标计算超时，请稍后重试"},
                    ensure_ascii=False,
                )
            )
            return

        if bundle is None:
            self.set_status(404)
            self.write(json.dumps({"ok": False, "error": "指标或形态数据不可用"}, ensure_ascii=False))
            return
        self.write(json.dumps(bundle, ensure_ascii=False))
