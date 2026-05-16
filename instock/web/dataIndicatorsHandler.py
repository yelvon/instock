#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

from abc import ABC
from urllib.parse import urlencode

from tornado import gen
import instock.web.base as webBase

__author__ = 'myh '
__date__ = '2023/3/10 '


# 经典指标页 → Vue SPA
class GetDataIndicatorsHandler(webBase.BaseHandler, ABC):
    @gen.coroutine
    def get(self):
        code = self.get_argument("code", default=None, strip=False)
        date = self.get_argument("date", default=None, strip=False)
        name = self.get_argument("name", default="", strip=False)
        if not code or not date:
            self.redirect("/instock/app/home", permanent=False)
            return
        q = {"code": code, "date": date}
        if name:
            q["name"] = name
        self.redirect("/instock/app/indicators?" + urlencode(q), permanent=False)


# 关注股票。
class SaveCollectHandler(webBase.BaseHandler, ABC):
    @gen.coroutine
    def get(self):
        import datetime
        import instock.core.tablestructure as tbs

        code = self.get_argument("code", default=None, strip=False)
        otype = self.get_argument("otype", default=None, strip=False)
        try:
            table_name = tbs.TABLE_CN_STOCK_ATTENTION["name"]
            if otype == "1":
                sql = f"DELETE FROM `{table_name}` WHERE `code` = %s"
                self.db.query(sql, code)
            else:
                sql = f"INSERT INTO `{table_name}`(`datetime`, `code`) VALUE(%s, %s)"
                self.db.query(
                    sql,
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    code,
                )
        except Exception:
            pass
        self.write('{"data":[{}]}')
