#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baostock 日线快照回补：在东财接口为空或异常时，按项目表结构构造 A 股 / ETF 快照 DataFrame。
"""
from __future__ import annotations

import datetime
import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

import instock.core.tablestructure as tbs

try:
    import baostock as bs
except ImportError:  # pragma: no cover
    bs = None  # type: ignore


def _is_a_stock(code: str) -> bool:
    """与 stockfetch.is_a_stock 保持一致，避免循环导入。"""
    return code.startswith(("600", "601", "603", "605", "000", "001", "002", "003", "300", "301"))


def _is_spot_equity_row(code_bs: str, digits: str) -> bool:
    """排除上证 sh.000* 指数、深证 sz.399* 指数等。"""
    if not _is_a_stock(digits):
        return False
    if code_bs.startswith("sh.") and digits.startswith("000"):
        return False
    if code_bs.startswith("sz.") and digits.startswith("399"):
        return False
    return True


def _baostock_allowed() -> bool:
    """全局禁用 Baostock（如离线环境）时设 ``INSTOCK_BAOSTOCK_DISABLED=1``。"""
    if bs is None:
        return False
    v = os.environ.get("INSTOCK_BAOSTOCK_DISABLED", "").strip().lower()
    return v not in ("1", "true", "yes", "on")


def _max_rows(kind: str) -> int:
    key = "INSTOCK_BAOSTOCK_MAX_STOCKS" if kind == "stock" else "INSTOCK_BAOSTOCK_MAX_ETFS"
    raw = os.environ.get(key, "0").strip()
    try:
        n = int(raw)
    except ValueError:
        return 0
    return max(0, n)


def _to_float(x: Any) -> float:
    if x is None or x == "":
        return float("nan")
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _turnover_to_percent(turn_s: Any) -> float:
    v = _to_float(turn_s)
    if np.isnan(v):
        return v
    # Baostock 多为小数比例（如 0.1057 表示约 10.57%）；若已大于 1 则视为已是百分比
    if v <= 1.0:
        return v * 100.0
    return v


def _bs_code_to_digits(code: str) -> str:
    if "." in code:
        return code.split(".", 1)[1]
    return code


def _trade_date_str(d: Optional[datetime.date]) -> str:
    if d is None:
        d = datetime.datetime.now().date()
    return d.strftime("%Y-%m-%d")


def _login() -> bool:
    if bs is None:
        logging.error("未安装 baostock，请 pip install baostock")
        return False
    lg = bs.login()
    if lg.error_code != "0":
        logging.error("Baostock login 失败: %s %s", lg.error_code, lg.error_msg)
        return False
    return True


def _logout() -> None:
    if bs is None:
        return
    try:
        bs.logout()
    except Exception:
        pass


def _k_row_one_day(bs_code: str, day: str) -> Optional[List[str]]:
    if bs is None:
        return None
    fields = "date,open,high,low,close,preclose,volume,amount,turn,tradestatus"
    rs = bs.query_history_k_data_plus(
        bs_code,
        fields,
        start_date=day,
        end_date=day,
        frequency="d",
        adjustflag="3",
    )
    if rs.error_code != "0":
        return None
    if not rs.next():
        return None
    return rs.get_row_data()


def stock_zh_a_spot_baostock(trade_date: Optional[datetime.date] = None) -> Optional[pd.DataFrame]:
    """
    使用 Baostock 构造与 ``stockfetch.fetch_stocks`` 兼容的 DataFrame（不含 date 列，由调用方 insert）。
    列名为 ``TABLE_CN_STOCK_SPOT`` 中除 date 外的英文字段，顺序一致。
    """
    if not _baostock_allowed():
        return None
    day = _trade_date_str(trade_date)
    if not _login():
        return None
    try:
        rs = bs.query_all_stock(day=day)
        if rs.error_code != "0":
            logging.warning("Baostock query_all_stock 失败: %s %s", rs.error_code, rs.error_msg)
            return None

        col_keys = [k for k in tbs.TABLE_CN_STOCK_SPOT["columns"].keys() if k != "date"]
        max_n = _max_rows("stock")
        rows: List[Dict[str, Any]] = []

        while rs.next():
            row = rs.get_row_data()
            code_bs, trade_status, code_name = row[0], row[1], row[2]
            digits = _bs_code_to_digits(code_bs)
            if trade_status != "1" or not _is_spot_equity_row(code_bs, digits):
                continue
            if max_n and len(rows) >= max_n:
                break

            kr = _k_row_one_day(code_bs, day)
            if not kr or len(kr) < 10:
                continue
            # date,open,high,low,close,preclose,volume,amount,turn,tradestatus
            if kr[9] != "1":
                continue

            o, h, low, c, pc = map(_to_float, (kr[1], kr[2], kr[3], kr[4], kr[5]))
            vol = _to_float(kr[6])
            amt = _to_float(kr[7])
            turn_pct = _turnover_to_percent(kr[8])

            if np.isnan(c) or c == 0:
                continue

            if not np.isnan(pc) and pc != 0:
                change_rate = (c - pc) / pc * 100.0
                ups = c - pc
                amplitude = (h - low) / pc * 100.0 if not np.isnan(h) and not np.isnan(low) else float("nan")
            else:
                change_rate = float("nan")
                ups = float("nan")
                amplitude = float("nan")

            listing = pd.NaT

            record = {k: np.nan for k in col_keys}
            record.update(
                {
                    "code": digits,
                    "name": code_name or "",
                    "new_price": c,
                    "change_rate": change_rate,
                    "ups_downs": ups,
                    "volume": vol,
                    "deal_amount": amt,
                    "amplitude": amplitude,
                    "turnoverrate": turn_pct,
                    "volume_ratio": float("nan"),
                    "open_price": o,
                    "high_price": h,
                    "low_price": low,
                    "pre_close_price": pc,
                    "listing_date": listing,
                    "industry": "",
                    "report_date": pd.NaT,
                }
            )
            rows.append(record)

        if not rows:
            logging.warning("Baostock A 股快照在 %s 无有效行", day)
            return None
        df = pd.DataFrame(rows, columns=col_keys)
        logging.info("Baostock A 股快照 %s 行数: %s", day, len(df.index))
        return df
    except Exception as e:
        logging.error("Baostock A 股快照异常: %s", e)
        return None
    finally:
        _logout()


def fund_etf_spot_baostock(trade_date: Optional[datetime.date] = None) -> Optional[pd.DataFrame]:
    """
    使用 Baostock 构造与 ``stockfetch.fetch_etfs`` 兼容的 ETF DataFrame（不含 date 列）。
    """
    if not _baostock_allowed():
        return None
    day = _trade_date_str(trade_date)
    if not _login():
        return None
    try:
        rs = bs.query_stock_basic()
        if rs.error_code != "0":
            logging.warning("Baostock query_stock_basic(ETF) 失败: %s %s", rs.error_code, rs.error_msg)
            return None

        etf_codes: List[tuple] = []
        while rs.next():
            row = rs.get_row_data()
            if len(row) >= 6 and row[4] == "5" and row[5] == "1":
                etf_codes.append((row[0], row[1] or ""))

        col_keys = [k for k in tbs.TABLE_CN_ETF_SPOT["columns"].keys() if k != "date"]
        max_n = _max_rows("etf")
        rows: List[Dict[str, Any]] = []

        for code_bs, name in etf_codes:
            if max_n and len(rows) >= max_n:
                break
            kr = _k_row_one_day(code_bs, day)
            if not kr or len(kr) < 10 or kr[9] != "1":
                continue
            o, h, low, c, pc = map(_to_float, (kr[1], kr[2], kr[3], kr[4], kr[5]))
            vol = _to_float(kr[6])
            amt = _to_float(kr[7])
            turn_pct = _turnover_to_percent(kr[8])
            if np.isnan(c) or c == 0:
                continue
            digits = _bs_code_to_digits(code_bs)
            if not np.isnan(pc) and pc != 0:
                change_rate = (c - pc) / pc * 100.0
                ups = c - pc
            else:
                change_rate = float("nan")
                ups = float("nan")

            record = {k: np.nan for k in col_keys}
            record.update(
                {
                    "code": digits,
                    "name": name,
                    "new_price": c,
                    "change_rate": change_rate,
                    "ups_downs": ups,
                    "volume": vol,
                    "deal_amount": amt,
                    "open_price": o,
                    "high_price": h,
                    "low_price": low,
                    "pre_close_price": pc,
                    "turnoverrate": turn_pct,
                }
            )
            rows.append(record)

        if not rows:
            logging.warning("Baostock ETF 快照在 %s 无有效行", day)
            return None
        df = pd.DataFrame(rows, columns=col_keys)
        logging.info("Baostock ETF 快照 %s 行数: %s", day, len(df.index))
        return df
    except Exception as e:
        logging.error("Baostock ETF 快照异常: %s", e)
        return None
    finally:
        _logout()
