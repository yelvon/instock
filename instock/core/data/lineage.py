# -*- coding: utf-8 -*-
"""data_batch 血缘写入。"""

from __future__ import annotations

import datetime
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import instock.lib.database as mdb
from instock.core.data.profile import effective_data_profile
from instock.core.data.provider import FetchResult

_LOG = logging.getLogger(__name__)
_TABLE = "data_batch"


def ensure_data_batch_table() -> None:
    if mdb.checkTableIsExist(_TABLE):
        return
    sql = """
    CREATE TABLE IF NOT EXISTS `data_batch` (
      `batch_id` varchar(64) NOT NULL COMMENT '批次唯一ID(UUID)',
      `domain_id` varchar(64) NOT NULL COMMENT '数据域ID，如 daily_spot_snapshot、daily_bar_raw、derived_indicators',
      `trade_date` date DEFAULT NULL COMMENT '业务交易日(日快照/衍生表)；K线域可为空',
      `date_from` date DEFAULT NULL COMMENT 'K线区间起始日(含)',
      `date_to` date DEFAULT NULL COMMENT 'K线区间结束日(含)',
      `scope_type` varchar(32) DEFAULT NULL COMMENT '范围类型：market/code/table 等',
      `scope_key` varchar(128) DEFAULT NULL COMMENT '范围标识，如 cn_stock_spot、股票代码',
      `row_count` int DEFAULT NULL COMMENT '本批次写入行数',
      `source_provider` varchar(32) NOT NULL COMMENT '主链数据源 provider_id，如 eastmoney、mootdx_local',
      `enrich_providers` json DEFAULT NULL COMMENT 'enrich 源列表 JSON，如 ["tencent"]',
      `mixed_source` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否混源：0否 1是(含 enrich 或 chain 多源)',
      `adjust_type` varchar(16) DEFAULT NULL COMMENT '复权口径：raw/qfq/hfq；K线 raw 域通常为 raw',
      `profile` varchar(16) NOT NULL DEFAULT 'live' COMMENT '数据配置档：live/backtest',
      `input_batches` json DEFAULT NULL COMMENT '上游依赖 batch_id 列表(衍生 job)',
      `status` varchar(16) NOT NULL DEFAULT 'success' COMMENT '批次状态：success/failed/partial',
      `job_id` varchar(128) DEFAULT NULL COMMENT '触发写入的作业ID，如 basic_data_daily_job',
      `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
      PRIMARY KEY (`batch_id`),
      KEY `idx_domain_date` (`domain_id`, `trade_date`),
      KEY `idx_provider` (`source_provider`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
      COMMENT='回测数据入库批次血缘(域/源/区间/依赖)';
    """
    mdb.executeSql(sql)


def record_canonical_batch(
    provider_id: str,
    *,
    scope_key: str = "",
    row_count: int = 0,
    date_from: Optional[datetime.date] = None,
    date_to: Optional[datetime.date] = None,
    job_id: Optional[str] = None,
    status: str = "success",
) -> str:
    """标准行情合并写入的批次血缘（不依赖 FetchResult）。"""
    ensure_data_batch_table()
    batch_id = str(uuid.uuid4())
    prof = effective_data_profile()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
    INSERT INTO `data_batch` (
      `batch_id`, `domain_id`, `trade_date`, `date_from`, `date_to`,
      `scope_type`, `scope_key`, `row_count`, `source_provider`,
      `enrich_providers`, `mixed_source`, `adjust_type`, `profile`,
      `input_batches`, `status`, `job_id`, `created_at`
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    params = (
        batch_id,
        "daily_bar_raw",
        None,
        date_from,
        date_to,
        "code",
        scope_key or None,
        row_count,
        provider_id,
        json.dumps([]),
        0,
        "raw",
        prof,
        json.dumps([]),
        status,
        job_id,
        now,
    )
    mdb.executeSql(sql, params)
    return batch_id


def record_batch(
    result: FetchResult,
    *,
    status: str = "success",
    job_id: Optional[str] = None,
    input_batches: Optional[List[str]] = None,
    profile: Optional[str] = None,
) -> str:
    """写入一条 batch 记录，返回 batch_id。"""
    ensure_data_batch_table()
    batch_id = str(uuid.uuid4())
    prof = effective_data_profile(profile)
    enrich = result.metadata.get("enrich_providers") or []
    if isinstance(enrich, str):
        enrich = [enrich]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
    INSERT INTO `data_batch` (
      `batch_id`, `domain_id`, `trade_date`, `date_from`, `date_to`,
      `scope_type`, `scope_key`, `row_count`, `source_provider`,
      `enrich_providers`, `mixed_source`, `adjust_type`, `profile`,
      `input_batches`, `status`, `job_id`, `created_at`
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    params = (
        batch_id,
        result.domain_id or "",
        result.trade_date,
        result.date_from,
        result.date_to,
        result.scope_type or None,
        result.scope_key or None,
        result.row_count,
        result.provider_id or "",
        json.dumps(enrich, ensure_ascii=False) if enrich else None,
        1 if result.mixed_source else 0,
        result.metadata.get("adjust_type") or result.metadata.get("adjust"),
        prof,
        json.dumps(input_batches, ensure_ascii=False) if input_batches else None,
        "failed" if not result.ok else status,
        job_id,
        now,
    )
    try:
        mdb.executeSql(sql, params)
    except Exception as e:
        _LOG.error("record_batch 失败: %s", e)
    return batch_id


def _row_to_batch_dict(r: tuple) -> Dict[str, Any]:
    import json as _json

    enrich = r[9]
    if isinstance(enrich, str):
        try:
            enrich = _json.loads(enrich)
        except Exception:
            enrich = enrich
    inp = r[13]
    if isinstance(inp, str):
        try:
            inp = _json.loads(inp)
        except Exception:
            inp = inp
    return {
        "batch_id": r[0],
        "domain_id": r[1],
        "trade_date": str(r[2]) if r[2] else None,
        "date_from": str(r[3]) if r[3] else None,
        "date_to": str(r[4]) if r[4] else None,
        "scope_type": r[5],
        "scope_key": r[6],
        "row_count": r[7],
        "source_provider": r[8],
        "enrich_providers": enrich,
        "mixed_source": bool(r[10]),
        "adjust_type": r[11],
        "profile": r[12],
        "input_batches": inp,
        "status": r[14],
        "job_id": r[15],
        "created_at": str(r[16]) if r[16] else None,
    }


_BATCH_SELECT = """
SELECT `batch_id`,`domain_id`,`trade_date`,`date_from`,`date_to`,
       `scope_type`,`scope_key`,`row_count`,`source_provider`,
       `enrich_providers`,`mixed_source`,`adjust_type`,`profile`,
       `input_batches`,`status`,`job_id`,`created_at`
FROM `data_batch`
"""


def list_batches(
    domain_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    ensure_data_batch_table()
    lim = max(1, min(int(limit), 200))
    off = max(0, int(offset))
    if domain_id:
        rows = mdb.executeSqlFetch(
            _BATCH_SELECT + " WHERE `domain_id`=%s ORDER BY `created_at` DESC LIMIT %s OFFSET %s",
            (domain_id, lim, off),
        )
    else:
        rows = mdb.executeSqlFetch(
            _BATCH_SELECT + " ORDER BY `created_at` DESC LIMIT %s OFFSET %s",
            (lim, off),
        )
    return [_row_to_batch_dict(r) for r in rows or []]


def list_recent_batches(domain_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    return list_batches(domain_id=domain_id, limit=limit, offset=0)


def latest_batch_id(domain_id: str, trade_date: Optional[datetime.date] = None) -> Optional[str]:
    ensure_data_batch_table()
    if trade_date:
        row = mdb.executeSqlFetch(
            "SELECT `batch_id` FROM `data_batch` WHERE `domain_id`=%s AND `trade_date`=%s "
            "ORDER BY `created_at` DESC LIMIT 1",
            (domain_id, trade_date.strftime("%Y-%m-%d")),
        )
    else:
        row = mdb.executeSqlFetch(
            "SELECT `batch_id` FROM `data_batch` WHERE `domain_id`=%s "
            "ORDER BY `created_at` DESC LIMIT 1",
            (domain_id,),
        )
    if row:
        return str(row[0][0])
    return None
