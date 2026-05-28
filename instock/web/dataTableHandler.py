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


def _sortable_columns(web_module_data) -> set:
    allowed = {"cdatetime"}
    cols = web_module_data.columns or ()
    for c in cols:
        if isinstance(c, str):
            allowed.add(c)
    return allowed


def _table_prefix(use_join: bool) -> str:
    return "s" if use_join else ""


def _col_ref(use_join: bool, col: str) -> str:
    if use_join:
        return f"s.`{col}`"
    return f"`{col}`"


def _parse_query_context(web_module_data, args: dict) -> dict:
    """解析表查询上下文；大表必须带 date 或 code 筛选。"""
    view_mode = (args.get("view_mode") or "").strip().lower()
    if not view_mode and getattr(web_module_data, "view_modes", None):
        modes = web_module_data.view_modes
        view_mode = modes[0] if modes else ""

    code = (args.get("code") or "").strip()
    if code:
        code = str(code).zfill(6)[:6]

    adjust_type = (args.get("adjust_type") or "").strip()
    if not adjust_type:
        adjust_type = (web_module_data.default_filters or {}).get("adjust_type", "raw")

    date_val = (args.get("date") or "").strip() or None
    date_from = (args.get("date_from") or "").strip() or None
    date_to = (args.get("date_to") or "").strip() or None

    if getattr(web_module_data, "requires_view_filter", False):
        if view_mode == "series":
            if not code:
                raise ValueError("按股票代码浏览须填写 code")
        elif view_mode == "cross_section":
            if not date_val:
                raise ValueError("按交易日浏览须填写 date")
        else:
            if not date_val and not code:
                raise ValueError("须指定 date（横截面）或 code（时间序列）")

    return {
        "view_mode": view_mode,
        "code": code or None,
        "adjust_type": adjust_type,
        "date": date_val,
        "date_from": date_from,
        "date_to": date_to,
    }


def _resolve_bar_table_context(web_module_data, ctx: dict) -> tuple:
    """raw/qfq 分表：qfq 时改查 cn_stock_daily_bar_qfq 且不再过滤 adjust_type。"""
    table = web_module_data.table_name
    ctx = dict(ctx)
    if table != tbs.TABLE_CN_STOCK_DAILY_BAR["name"]:
        return table, ctx
    try:
        from instock.core.canonical.bar_tables import normalize_adjust_type, resolve_bar_table

        adj = normalize_adjust_type(ctx.get("adjust_type") or "raw")
        if adj == "qfq":
            return resolve_bar_table("qfq"), {**ctx, "adjust_type": None}
    except Exception:
        pass
    return table, ctx


def _build_where_sql(web_module_data, ctx: dict, use_join: bool) -> tuple:
    clauses = []
    params = []
    prefix = _table_prefix(use_join)

    defaults = getattr(web_module_data, "default_filters", None) or {}
    for k, v in defaults.items():
        if k in ("adjust_type",) and ctx.get("adjust_type"):
            continue
        col = _col_ref(use_join, k)
        clauses.append(f"{col} = %s")
        params.append(v)

    adj = ctx.get("adjust_type")
    if adj and "adjust_type" in (web_module_data.columns or ()):
        clauses.append(f"{_col_ref(use_join, 'adjust_type')} = %s")
        params.append(adj)

    view_mode = ctx.get("view_mode")
    if view_mode == "series" and ctx.get("code"):
        clauses.append(f"{_col_ref(use_join, 'code')} = %s")
        params.append(ctx["code"])
        if ctx.get("date_from"):
            clauses.append(f"{_col_ref(use_join, 'date')} >= %s")
            params.append(ctx["date_from"])
        if ctx.get("date_to"):
            clauses.append(f"{_col_ref(use_join, 'date')} <= %s")
            params.append(ctx["date_to"])
    elif ctx.get("date"):
        clauses.append(f"{_col_ref(use_join, 'date')} = %s")
        params.append(ctx["date"])
    elif ctx.get("code"):
        clauses.append(f"{_col_ref(use_join, 'code')} = %s")
        params.append(ctx["code"])
        if ctx.get("date_from"):
            clauses.append(f"{_col_ref(use_join, 'date')} >= %s")
            params.append(ctx["date_from"])
        if ctx.get("date_to"):
            clauses.append(f"{_col_ref(use_join, 'date')} <= %s")
            params.append(ctx["date_to"])

    where_sql = ""
    if clauses:
        where_sql = " WHERE " + " AND ".join(clauses)
    return where_sql, params


def _build_order_sql(web_module_data, sort_col, sort_dir, use_join: bool, ctx: dict) -> str:
    """用户点击表头排序时全表 ORDER BY；否则用模块默认 order_by。"""
    if sort_col and sort_col in _sortable_columns(web_module_data):
        direction = "ASC" if (sort_dir or "").lower() == "asc" else "DESC"
        if sort_col == "cdatetime" or not use_join:
            return f" ORDER BY `{sort_col}` {direction}"
        return f" ORDER BY s.`{sort_col}` {direction}"
    if ctx.get("view_mode") == "series" and getattr(web_module_data, "order_by_series", None):
        return f" ORDER BY {web_module_data.order_by_series}"
    if web_module_data.order_by:
        return f" ORDER BY {web_module_data.order_by}"
    return ""


def _build_list_sql(
    web_module_data,
    ctx: dict,
    limit=None,
    offset=None,
    sort_col=None,
    sort_dir=None,
):
    """返回 (sql, params)。"""
    table, ctx = _resolve_bar_table_context(web_module_data, ctx)
    use_join = _uses_attention_join(web_module_data)
    where_sql, params = _build_where_sql(web_module_data, ctx, use_join)
    order_sql = _build_order_sql(web_module_data, sort_col, sort_dir, use_join, ctx)

    if use_join:
        join_where = where_sql
        sql = (
            f"SELECT s.*, a.`datetime` AS `cdatetime` "
            f"FROM `{table}` s "
            f"LEFT JOIN `{_ATTENTION_TABLE}` a ON a.`code` = s.`code`"
            f"{join_where}{order_sql}"
        )
    else:
        order_columns = ""
        if web_module_data.order_columns is not None:
            order_columns = f",{web_module_data.order_columns}"
        sql = f"SELECT *{order_columns} FROM `{table}`"
        sql += where_sql
        sql += order_sql

    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset or 0)}"

    return sql, params


def _build_count_sql(web_module_data, ctx: dict):
    table, ctx = _resolve_bar_table_context(web_module_data, ctx)
    use_join = _uses_attention_join(web_module_data)
    where_sql, params = _build_where_sql(web_module_data, ctx, use_join)
    if use_join:
        sql = f"SELECT COUNT(*) AS `cnt` FROM `{table}` s" + where_sql
    else:
        sql = f"SELECT COUNT(*) AS `cnt` FROM `{table}`" + where_sql
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
        sort_col = self.get_argument("sort_col", default=None, strip=True) or None
        sort_dir = self.get_argument("sort_dir", default=None, strip=True) or None
        view_mode = self.get_argument("view_mode", default=None, strip=True) or None
        code = self.get_argument("code", default=None, strip=True) or None
        adjust_type = self.get_argument("adjust_type", default=None, strip=True) or None
        date_from = self.get_argument("date_from", default=None, strip=True) or None
        date_to = self.get_argument("date_to", default=None, strip=True) or None

        import instock.core.singleton_stock_web_module_data as sswmd

        web_module_data = sswmd.stock_web_module_data().get_data(name)
        self.set_header("Content-Type", "application/json;charset=UTF-8")

        try:
            ctx = _parse_query_context(
                web_module_data,
                {
                    "view_mode": view_mode,
                    "code": code,
                    "adjust_type": adjust_type,
                    "date": date,
                    "date_from": date_from,
                    "date_to": date_to,
                },
            )
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
            return

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
                count_sql, count_params = _build_count_sql(web_module_data, ctx)
                count_row = self.db.get(count_sql, *count_params)
                total = int(count_row["cnt"]) if count_row else 0
                offset = (page - 1) * page_size
                list_sql, list_params = _build_list_sql(
                    web_module_data,
                    ctx,
                    limit=page_size,
                    offset=offset,
                    sort_col=sort_col,
                    sort_dir=sort_dir,
                )
                data = self.db.query(list_sql, *list_params)
                payload = {
                    "ok": True,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "rows": data,
                }
                if sort_col:
                    payload["sort_col"] = sort_col
                    payload["sort_dir"] = (
                        "asc" if (sort_dir or "").lower() == "asc" else "desc"
                    )
                self.write(
                    json.dumps(
                        payload,
                        cls=MyEncoder,
                        ensure_ascii=False,
                    )
                )
                return

            list_sql, list_params = _build_list_sql(
                web_module_data, ctx, sort_col=sort_col, sort_dir=sort_dir
            )
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
