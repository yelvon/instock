# -*- coding: utf-8 -*-
"""主数据日线质量校验（规划 data.md §2）：硬规则 H1–H6 + 软规则警告。"""

from __future__ import annotations

import datetime
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import instock.core.tablestructure as tbs
import instock.lib.database as mdb
import instock.lib.trade_time as trd


def _date_sql(d: datetime.date) -> str:
    return d.strftime("%Y-%m-%d")


@dataclass
class ValidationResult:
    """单次表、单日校验结果。"""

    ok: bool
    table: str
    trade_date: datetime.date
    errors: List[Dict[str, Any]] = field(default_factory=list)
    soft_warnings: List[Dict[str, Any]] = field(default_factory=list)
    skipped: bool = False
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "table": self.table,
            "trade_date": _date_sql(self.trade_date),
            "errors": self.errors,
            "soft_warnings": self.soft_warnings,
            "skipped": self.skipped,
            "message": self.message,
        }


def _count_for_date(table: str, trade_date: datetime.date) -> int:
    ds = _date_sql(trade_date)
    return mdb.executeSqlCount(f"SELECT COUNT(*) FROM `{table}` WHERE `date` = %s", (ds,))


def _h6_check(trade_date: datetime.date) -> List[Dict[str, Any]]:
    errs: List[Dict[str, Any]] = []
    if os.environ.get("INSTOCK_SKIP_H6", "").strip() == "1":
        return errs
    if not trd.is_trade_date(trade_date):
        errs.append({"rule": "H6", "detail": "日期不在当前交易日历集合中"})
    return errs


def validate_cn_stock_spot(trade_date: datetime.date) -> ValidationResult:
    """校验 cn_stock_spot 单日数据。"""
    table = tbs.TABLE_CN_STOCK_SPOT["name"]
    ds = _date_sql(trade_date)
    cnt = _count_for_date(table, trade_date)
    if cnt == 0:
        return ValidationResult(
            True, table, trade_date, skipped=True, message="无数据，跳过质量校验"
        )

    min_rows = int(os.environ.get("QUALITY_STOCK_MIN_ROWS", "3500"))
    errs: List[Dict[str, Any]] = []

    if cnt < min_rows:
        errs.append({"rule": "H1", "detail": f"行数 {cnt} 低于阈值 {min_rows}"})

    errs.extend(_h6_check(trade_date))

    bad_sql = f"""
    SELECT `code` FROM `{table}` WHERE `date` = %s AND (
        `open_price` IS NULL OR `high_price` IS NULL OR `low_price` IS NULL OR `new_price` IS NULL
        OR `high_price` < `low_price`
        OR `high_price` < GREATEST(IFNULL(`open_price`, `new_price`), IFNULL(`new_price`, `open_price`))
        OR `low_price` > LEAST(IFNULL(`open_price`, `new_price`), IFNULL(`new_price`, `open_price`))
        OR (`volume` IS NOT NULL AND `volume` < 0)
        OR (`deal_amount` IS NOT NULL AND `deal_amount` < 0)
        OR CHAR_LENGTH(TRIM(`code`)) != 6
        OR TRIM(`code`) NOT REGEXP '^[0-9]{{6}}$'
    ) LIMIT 200
    """
    bad = mdb.executeSqlFetch(bad_sql, (ds,))
    if bad:
        codes = [r[0] for r in bad]
        errs.append(
            {
                "rule": "H2-H5",
                "detail": f"OHLC/量额/代码异常，示例 code 数={len(codes)}",
                "sample_codes": codes[:50],
            }
        )

    soft: List[Dict[str, Any]] = []
    abs_sql = f"""
    SELECT `code`, `change_rate` FROM `{table}` WHERE `date` = %s
      AND `change_rate` IS NOT NULL AND ABS(`change_rate`) > 25 LIMIT 50
    """
    ab = mdb.executeSqlFetch(abs_sql, (ds,))
    if ab:
        soft.append(
            {
                "rule": "S1",
                "detail": "涨跌幅绝对值>25% 的样本（科创板等可能正常）",
                "sample": [{"code": r[0], "change_rate": float(r[1])} for r in ab[:20]],
            }
        )

    ok = len(errs) == 0
    return ValidationResult(ok, table, trade_date, errs, soft)


def validate_cn_etf_spot(trade_date: datetime.date) -> ValidationResult:
    """校验 cn_etf_spot 单日数据。"""
    table = tbs.TABLE_CN_ETF_SPOT["name"]
    ds = _date_sql(trade_date)
    cnt = _count_for_date(table, trade_date)
    if cnt == 0:
        return ValidationResult(
            True, table, trade_date, skipped=True, message="无数据，跳过质量校验"
        )

    min_rows = int(os.environ.get("QUALITY_ETF_MIN_ROWS", "400"))
    errs: List[Dict[str, Any]] = []
    if cnt < min_rows:
        errs.append({"rule": "H1", "detail": f"行数 {cnt} 低于阈值 {min_rows}"})

    errs.extend(_h6_check(trade_date))

    bad_sql = f"""
    SELECT `code` FROM `{table}` WHERE `date` = %s AND (
        `open_price` IS NULL OR `high_price` IS NULL OR `low_price` IS NULL OR `new_price` IS NULL
        OR `high_price` < `low_price`
        OR `high_price` < GREATEST(IFNULL(`open_price`, `new_price`), IFNULL(`new_price`, `open_price`))
        OR `low_price` > LEAST(IFNULL(`open_price`, `new_price`), IFNULL(`new_price`, `open_price`))
        OR (`volume` IS NOT NULL AND `volume` < 0)
        OR (`deal_amount` IS NOT NULL AND `deal_amount` < 0)
        OR CHAR_LENGTH(TRIM(`code`)) != 6
        OR TRIM(`code`) NOT REGEXP '^[0-9]{{6}}$'
    ) LIMIT 200
    """
    bad = mdb.executeSqlFetch(bad_sql, (ds,))
    if bad:
        codes = [r[0] for r in bad]
        errs.append(
            {
                "rule": "H2-H5",
                "detail": f"OHLC/量额/代码异常，示例 code 数={len(codes)}",
                "sample_codes": codes[:50],
            }
        )

    ok = len(errs) == 0
    return ValidationResult(ok, table, trade_date, errs, [])


def validate_spot_after_daily_jobs(trade_date: datetime.date) -> List[ValidationResult]:
    """基础 spot 任务写库后调用：股票 + ETF 各校验一次。"""
    if os.environ.get("INSTOCK_QUALITY_DISABLED", "").strip() == "1":
        logging.info("数据质量校验已禁用 INSTOCK_QUALITY_DISABLED=1")
        return []
    results = [
        validate_cn_stock_spot(trade_date),
        validate_cn_etf_spot(trade_date),
    ]
    for r in results:
        if r.skipped:
            logging.info("数据质量 %s %s: %s", r.table, _date_sql(trade_date), r.message)
            continue
        if r.soft_warnings:
            logging.warning(
                "数据质量软规则 %s %s: %s", r.table, _date_sql(trade_date), r.soft_warnings
            )
        if not r.ok:
            logging.error(
                "数据质量失败 %s %s: %s", r.table, _date_sql(trade_date), r.errors
            )
        else:
            logging.info("数据质量通过 %s %s", r.table, _date_sql(trade_date))
    return results


def any_hard_fail(results: List[ValidationResult]) -> bool:
    return any(not r.skipped and not r.ok for r in results)
