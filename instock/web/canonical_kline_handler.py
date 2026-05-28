# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from abc import ABC

import instock.web.base as webBase
from instock.core.canonical.kline_payload import build_canonical_kline_payload


class CanonicalKlineApiHandler(webBase.BaseHandler, ABC):
    """GET /instock/api/canonical/kline?code=&date_from=&date_to=&adjust_type=&period="""

    def get(self):
        self.set_header("Content-Type", "application/json;charset=UTF-8")
        code = (self.get_argument("code", "") or "").strip()
        date_from = (self.get_argument("date_from", "") or "").strip()
        date_to = (self.get_argument("date_to", "") or "").strip()
        adjust_type = (self.get_argument("adjust_type", "raw") or "raw").strip()
        period = (self.get_argument("period", "daily") or "daily").strip()

        if not code:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": "缺少 code"}, ensure_ascii=False))
            return
        if not date_from or not date_to:
            self.set_status(400)
            self.write(
                json.dumps(
                    {"ok": False, "error": "缺少 date_from 或 date_to"},
                    ensure_ascii=False,
                )
            )
            return

        try:
            out = build_canonical_kline_payload(
                code,
                date_from,
                date_to,
                adjust_type=adjust_type,
                period=period,
            )
            self.write(json.dumps(out, ensure_ascii=False))
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
