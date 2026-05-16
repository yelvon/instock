#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 K 线/指标流水线导出 JSON，供 Vue + lightweight-charts / ECharts 使用（无 Bokeh）。"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

import instock.core.indicator.calculate_indicator as idr
import instock.core.kline.indicator_web_dic as iwd
import instock.core.pattern.pattern_recognitions as kpr
import instock.core.tablestructure as tbs


def _cell(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (np.floating,)):
        x = float(v)
        return None if math.isnan(x) or math.isinf(x) else x
    if isinstance(v, (np.integer,)):
        return int(v)
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()[:19] if hasattr(v, "hour") else str(v)[:10]
        except Exception:
            return str(v)
    return v


def _records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for rec in df.to_dict(orient="records"):
        row: Dict[str, Any] = {}
        for k, v in rec.items():
            row[str(k)] = _cell(v)
        out.append(row)
    return out


def build_kline_bundle(code: str, date: str, stock_name: str, stock: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    :param stock: fetch_stock_hist / fetch_etf_hist 返回的 K 线 DataFrame
    :return: 供前端渲染的字典；数据异常时返回 None
    """
    try:
        data = idr.get_indicators(stock, date, threshold=360)
        if data is None or data.empty:
            return None

        threshold = 120
        stock_column = tbs.STOCK_KLINE_PATTERN_DATA["columns"]
        data = kpr.get_pattern_recognitions(data, stock_column, threshold=threshold)
        if data is None or data.empty:
            return None

        k_length = len(data.index)
        data = data.copy()
        data["index"] = list(np.arange(k_length))
        data["is_red"] = data.apply(lambda row: "1" if row["close"] > row["open"] else "0", axis=1)

        display = data.tail(600).copy()
        display["index"] = list(np.arange(len(display)))

        bars = _records(display)

        pattern_keys = [k for k in stock_column if k in display.columns]
        patterns_meta = [{"key": k, "cn": stock_column[k]["cn"]} for k in pattern_keys]

        indicator_tabs: List[Dict[str, Any]] = []
        for conf in iwd.indicators_dic:
            series_list: List[Dict[str, Any]] = []
            for name in conf["dic"]:
                if name not in display.columns:
                    continue
                arr = display[name].replace({np.nan: None}).tolist()
                series_list.append(
                    {
                        "key": name,
                        "name": tbs.get_field_cn(name, tbs.STOCK_STATS_DATA),
                        "values": [_cell(x) for x in arr],
                    }
                )
            indicator_tabs.append(
                {
                    "title": conf["title"],
                    "desc": conf.get("desc") or "",
                    "series": series_list,
                }
            )

        is_etf = code.startswith(("1", "5"))
        attention_supported = not is_etf
        attention_state = "0"
        if attention_supported:
            import instock.lib.database as mdb

            table_name = tbs.TABLE_CN_STOCK_ATTENTION["name"]
            _sql = f"SELECT EXISTS(SELECT 1 FROM `{table_name}` WHERE `code` = %s)"
            try:
                rc = mdb.executeSqlCount(_sql, (code,))
                attention_state = "1" if rc else "0"
            except Exception:
                attention_state = "0"

        if code.startswith("6"):
            code_name = f"SH{code}"
        else:
            code_name = f"SZ{code}"

        links: Dict[str, Any] = {
            "eastmoneyHq": f"https://quote.eastmoney.com/{code_name}.html",
            "eastmoneyF10": None
            if is_etf
            else f"https://emweb.eastmoney.com/PC_HSF10/OperationsRequired/Index?code={code_name}",
            "tdxMine": None
            if is_etf
            else f"http://page1.tdx.com.cn:7615/site/pcwebcall_static/bxb/bxb.html?code={code}&color=0",
            "patternArticle": "https://www.ljjyy.com/archives/2023/04/100718.html",
        }

        return {
            "ok": True,
            "code": code,
            "date": date,
            "stockName": stock_name or "",
            "bars": bars,
            "patterns": patterns_meta,
            "indicatorTabs": indicator_tabs,
            "attention": {
                "supported": attention_supported,
                "state": attention_state,
            },
            "links": links,
        }
    except Exception as e:
        logging.error("kline_bundle_export.build_kline_bundle: %s", e)
        return None
