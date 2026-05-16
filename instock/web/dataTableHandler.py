#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import json
from abc import ABC
from decimal import Decimal
from urllib.parse import urlencode

from tornado import gen
import datetime
from pymysql.err import ProgrammingError

import instock.core.tablestructure as tbs
import instock.web.base as webBase

__author__ = 'myh '
__date__ = '2023/3/10 '

_ATTENTION_TABLE = tbs.TABLE_CN_STOCK_ATTENTION['name']
_MAX_PAGE_SIZE = 2000


class MyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, bytes):
            return "是" if (len(obj) == 1 and ord(obj) == 1) else "否"
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        else:
            return json.JSONEncoder.default(self, obj)


def _uses_attention_join(web_module_data) -> bool:
    """原 order_columns 为逐行子查询，大表极慢；改为 LEFT JOIN。"""
    oc = web_module_data.order_columns or ""
    return _ATTENTION_TABLE in oc and "SELECT" in oc.upper()


def _build_list_sql(web_module_data, date, limit=None, offset=None):
    """返回 (sql, params)。"""
    table = web_module_data.table_name
    params = []

    if _uses_attention_join(web_module_data):
        sql = (
            f"SELECT s.*, a.`datetime` AS `cdatetime` "
            f"FROM `{table}` s "
            f"LEFT JOIN `{_ATTENTION_TABLE}` a ON a.`code` = s.`code`"
        )
        if date is not None:
            sql += " WHERE s.`date` = %s"
            params.append(date)
        if web_module_data.order_by:
            sql += f" ORDER BY {web_module_data.order_by}"
    else:
        order_columns = ""
        if web_module_data.order_columns is not None:
            order_columns = f",{web_module_data.order_columns}"
        sql = f"SELECT *{order_columns} FROM `{table}`"
        if date is not None:
            sql += " WHERE `date` = %s"
            params.append(date)
        if web_module_data.order_by:
            sql += f" ORDER BY {web_module_data.order_by}"

    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset or 0)}"

    return sql, params


def _build_count_sql(web_module_data, date):
    table = web_module_data.table_name
    params = []
    if _uses_attention_join(web_module_data):
        sql = f"SELECT COUNT(*) AS `cnt` FROM `{table}` s"
        if date is not None:
            sql += " WHERE s.`date` = %s"
            params.append(date)
    else:
        sql = f"SELECT COUNT(*) AS `cnt` FROM `{table}`"
        if date is not None:
            sql += " WHERE `date` = %s"
            params.append(date)
    return sql, params


# 经典数据表页 → Vue SPA
class GetStockHtmlHandler(webBase.BaseHandler, ABC):
    @gen.coroutine
    def get(self):
        name = self.get_argument("table_name", default=None, strip=False)
        if not name:
            self.redirect("/instock/app/table", permanent=False)
            return
        self.redirect(
            "/instock/app/table?" + urlencode({"table_name": name}),
            permanent=False,
        )


# 获得股票数据内容。
class GetStockDataHandler(webBase.BaseHandler, ABC):
    def get(self):
        name = self.get_argument("name", default=None, strip=False)
        date = self.get_argument("date", default=None, strip=False)
        page_arg = self.get_argument("page", default=None)
        page_size_arg = self.get_argument("page_size", default=None)

        import instock.core.singleton_stock_web_module_data as sswmd

        web_module_data = sswmd.stock_web_module_data().get_data(name)
        self.set_header("Content-Type", "application/json;charset=UTF-8")

        use_page = page_size_arg is not None and str(page_size_arg).strip() != ""
        page_size = None
        page = 1
        if use_page:
            try:
                page_size = min(max(int(page_size_arg), 1), _MAX_PAGE_SIZE)
                page = max(int(page_arg or 1), 1)
            except (TypeError, ValueError):
                self.set_status(400)
                self.write(json.dumps({"ok": False, "error": "page / page_size 参数无效"}, ensure_ascii=False))
                return

        try:
            if use_page:
                count_sql, count_params = _build_count_sql(web_module_data, date)
                count_row = self.db.get(count_sql, *count_params)
                total = int(count_row["cnt"]) if count_row else 0
                offset = (page - 1) * page_size
                list_sql, list_params = _build_list_sql(
                    web_module_data, date, limit=page_size, offset=offset
                )
                data = self.db.query(list_sql, *list_params)
                self.write(
                    json.dumps(
                        {
                            "ok": True,
                            "total": total,
                            "page": page,
                            "page_size": page_size,
                            "rows": data,
                        },
                        cls=MyEncoder,
                        ensure_ascii=False,
                    )
                )
                return

            list_sql, list_params = _build_list_sql(web_module_data, date)
            data = self.db.query(list_sql, *list_params)
        except ProgrammingError as e:
            if e.args and e.args[0] == 1146:
                self.set_status(404)
                self.write(
                    json.dumps(
                        {
                            "ok": False,
                            "error": "数据表尚未创建（历史上若当日无行情数据则不会自动建表）。请执行「每日快照」作业或 Web「数据同步」，或：python3 instock/job/basic_data_daily_job.py。",
                        },
                        ensure_ascii=False,
                    )
                )
                return
            raise

        self.write(json.dumps(data, cls=MyEncoder, ensure_ascii=False))
