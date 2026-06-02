# -*- coding: utf-8 -*-
"""CanonicalBarWriter：多源幂等合并写入 cn_stock_daily_bar。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd
import pymysql

import instock.lib.database as mdb
from instock.core.canonical import quality as q
from instock.core.data.lineage import ensure_data_batch_table, record_canonical_batch

logger = logging.getLogger(__name__)

TABLE_BAR = "cn_stock_daily_bar"
TABLE_CONTRIB = "market_data_contribution"
_CANONICAL_DDL_DONE = False


@dataclass
class MergeStats:
    inserted: int = 0
    filled: int = 0
    skipped: int = 0
    conflict: int = 0
    suspect: int = 0
    errors: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "inserted": self.inserted,
            "filled": self.filled,
            "skipped": self.skipped,
            "conflict": self.conflict,
            "suspect": self.suspect,
            "errors": self.errors,
        }


def ensure_canonical_tables() -> None:
    global _CANONICAL_DDL_DONE
    if _CANONICAL_DDL_DONE:
        return
    ddl_bar = """
    CREATE TABLE IF NOT EXISTS `cn_stock_daily_bar` (
      `date` date NOT NULL,
      `code` varchar(6) NOT NULL,
      `adjust_type` varchar(16) NOT NULL DEFAULT 'raw',
      `open` double DEFAULT NULL,
      `close` double DEFAULT NULL,
      `high` double DEFAULT NULL,
      `low` double DEFAULT NULL,
      `volume` double DEFAULT NULL,
      `amount` double DEFAULT NULL,
      `amplitude` double DEFAULT NULL,
      `quote_change` double DEFAULT NULL,
      `ups_downs` double DEFAULT NULL,
      `turnover` double DEFAULT NULL,
      `quality_status` varchar(16) NOT NULL DEFAULT 'partial',
      `completeness_score` tinyint unsigned NOT NULL DEFAULT 0,
      `primary_source` varchar(32) DEFAULT NULL,
      `source_mask` json DEFAULT NULL,
      `last_batch_id` varchar(64) DEFAULT NULL,
      `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`code`,`date`,`adjust_type`),
      KEY `idx_date` (`date`),
      KEY `idx_quality` (`quality_status`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """
    ddl_contrib = """
    CREATE TABLE IF NOT EXISTS `market_data_contribution` (
      `id` bigint unsigned NOT NULL AUTO_INCREMENT,
      `date` date NOT NULL,
      `code` varchar(6) NOT NULL,
      `adjust_type` varchar(16) NOT NULL DEFAULT 'raw',
      `source_provider` varchar(32) NOT NULL,
      `batch_id` varchar(64) DEFAULT NULL,
      `fields_filled` json DEFAULT NULL,
      `row_hash` varchar(64) DEFAULT NULL,
      `quality_score` tinyint unsigned NOT NULL DEFAULT 0,
      `merge_action` varchar(16) NOT NULL,
      `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      KEY `idx_code_date` (`code`,`date`,`adjust_type`),
      KEY `idx_source` (`source_provider`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """
    with mdb.connection_ctx() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl_bar)
            cur.execute(ddl_contrib)
        conn.commit()
    ensure_data_batch_table()
    _CANONICAL_DDL_DONE = True


class CanonicalBarWriter:
    """缺失插入；完整不覆盖；缺字段补空；明显冲突标 suspect。"""

    def __init__(self, provider_id: str, adjust_type: str = "raw"):
        ensure_canonical_tables()
        if (adjust_type or "raw").strip().lower() not in ("raw", ""):
            raise ValueError(
                "CanonicalBarWriter 仅写入 raw 表；qfq 请使用 QfqBarWriter / derive_qfq_from_tdx_job"
            )
        self.provider_id = provider_id
        self.adjust_type = "raw"
        self.quality_score = q.provider_quality(provider_id)

    def write_dataframe(
        self,
        code: str,
        df: pd.DataFrame,
        batch_id: Optional[str] = None,
    ) -> MergeStats:
        from instock.core.canonical.bar_rows import dataframe_to_bar_rows

        rows = dataframe_to_bar_rows(df, self.provider_id, self.adjust_type)
        return self.write_rows(code, rows, batch_id=batch_id)

    def write_rows(
        self,
        code: str,
        rows: List[Dict[str, Any]],
        batch_id: Optional[str] = None,
    ) -> MergeStats:
        stats = MergeStats()
        code = str(code).zfill(6)[:6]
        if not rows:
            return stats
        bid = batch_id or record_canonical_batch(
            self.provider_id,
            scope_key=code,
            row_count=len(rows),
            job_id="canonical_bar_writer",
        )
        conn = mdb.get_connection()
        if conn is None:
            raise RuntimeError("无法连接 MySQL，补数写入中止")
        try:
            existing_map = self._load_existing_map(conn, code, rows)
            for row in rows:
                try:
                    self._merge_one(code, row, bid, stats, conn, existing_map)
                except Exception as e:
                    stats.errors += 1
                    logger.warning("canonical merge %s %s: %s", code, row.get("date"), e)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            mdb._release_connection(conn)
        return stats

    def _load_existing_map(
        self,
        conn: pymysql.Connection,
        code: str,
        rows: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[Any, Dict[str, Any]]:
        sql = f"SELECT * FROM `{TABLE_BAR}` WHERE code=%s AND adjust_type=%s"
        params: List[Any] = [code, self.adjust_type]
        if rows:
            dates = [r.get("date") for r in rows if r.get("date") is not None]
            if dates:
                d_min, d_max = min(dates), max(dates)
                sql += " AND `date` >= %s AND `date` <= %s"
                params.extend([d_min, d_max])
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, tuple(params))
            rows_db = cur.fetchall() or []
        return {r["date"]: r for r in rows_db}

    def _record_contribution(
        self,
        conn: pymysql.Connection,
        code: str,
        dt,
        batch_id: str,
        fields_filled: List[str],
        row_hash: str,
        merge_action: str,
    ) -> None:
        sql = f"""
        INSERT INTO `{TABLE_CONTRIB}`
        (date, code, adjust_type, source_provider, batch_id, fields_filled,
         row_hash, quality_score, merge_action)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    dt,
                    code,
                    self.adjust_type,
                    self.provider_id,
                    batch_id,
                    json.dumps(fields_filled, ensure_ascii=False),
                    row_hash,
                    self.quality_score,
                    merge_action,
                ),
            )

    def _merge_one(
        self,
        code: str,
        incoming: Dict[str, Any],
        batch_id: str,
        stats: MergeStats,
        conn: pymysql.Connection,
        existing_map: Dict[Any, Dict[str, Any]],
    ) -> None:
        dt = incoming.get("date")
        if dt is None:
            stats.errors += 1
            return
        existing = existing_map.get(dt)
        inc = {k: incoming.get(k) for k in q.CORE_FIELDS + q.OPTIONAL_FIELDS}
        inc_hash = q.row_hash(inc)
        inc_score = q.completeness_score(inc)

        if existing is None:
            self._insert(conn, code, dt, inc, inc_score, batch_id)
            stats.inserted += 1
            self._record_contribution(
                conn, code, dt, batch_id, q.fields_present(inc), inc_hash, "insert"
            )
            existing_map[dt] = {"date": dt, "code": code, "quality_status": "partial"}
            return

        ex = {k: existing.get(k) for k in q.CORE_FIELDS + q.OPTIONAL_FIELDS}
        ex_score = int(existing.get("completeness_score") or 0)
        ex_complete = ex_score >= 80 and existing.get("quality_status") == "complete"

        if q.price_conflict(ex, inc) and not q.fields_missing(ex):
            stats.conflict += 1
            self._mark_suspect(conn, code, dt, existing, batch_id)
            stats.suspect += 1
            self._record_contribution(conn, code, dt, batch_id, [], inc_hash, "conflict")
            return

        if ex_complete:
            stats.skipped += 1
            self._record_contribution(conn, code, dt, batch_id, [], inc_hash, "skip")
            return

        fill_fields = [
            f
            for f in q.CORE_FIELDS + q.OPTIONAL_FIELDS
            if q._is_empty(ex.get(f)) and not q._is_empty(inc.get(f))
        ]
        if not fill_fields:
            stats.skipped += 1
            self._record_contribution(conn, code, dt, batch_id, [], inc_hash, "skip")
            return

        merged = dict(ex)
        for f in fill_fields:
            merged[f] = inc[f]
        new_score = q.completeness_score(merged)
        status = q.quality_status_from_score(new_score)
        mask = q.merge_masks(existing.get("source_mask"), self.provider_id)
        primary = existing.get("primary_source") or self.provider_id
        if self.quality_score > q.provider_quality(str(primary)):
            primary = self.provider_id

        self._update_row(conn, code, dt, merged, new_score, status, primary, mask, batch_id)
        stats.filled += 1
        self._record_contribution(conn, code, dt, batch_id, fill_fields, inc_hash, "fill")

    def _insert(
        self,
        conn: pymysql.Connection,
        code: str,
        dt,
        row: Dict[str, Any],
        score: int,
        batch_id: str,
    ) -> None:
        status = q.quality_status_from_score(score)
        mask = [self.provider_id]
        cols = ["date", "code", "adjust_type"] + list(q.CORE_FIELDS + q.OPTIONAL_FIELDS)
        cols += [
            "quality_status",
            "completeness_score",
            "primary_source",
            "source_mask",
            "last_batch_id",
        ]
        vals = [dt, code, self.adjust_type]
        vals += [row.get(f) for f in q.CORE_FIELDS + q.OPTIONAL_FIELDS]
        vals += [status, score, self.provider_id, json.dumps(mask), batch_id]
        ph = ",".join(["%s"] * len(vals))
        sql = f"INSERT INTO `{TABLE_BAR}` ({','.join(cols)}) VALUES ({ph})"
        with conn.cursor() as cur:
            cur.execute(sql, vals)

    def _update_row(
        self,
        conn: pymysql.Connection,
        code: str,
        dt,
        row: Dict[str, Any],
        score: int,
        status: str,
        primary: str,
        mask: List[str],
        batch_id: str,
    ) -> None:
        sets = [f"{f}=%s" for f in q.CORE_FIELDS + q.OPTIONAL_FIELDS]
        sets += [
            "quality_status=%s",
            "completeness_score=%s",
            "primary_source=%s",
            "source_mask=%s",
            "last_batch_id=%s",
        ]
        vals = [row.get(f) for f in q.CORE_FIELDS + q.OPTIONAL_FIELDS]
        vals += [status, score, primary, json.dumps(mask), batch_id, code, dt, self.adjust_type]
        sql = (
            f"UPDATE `{TABLE_BAR}` SET {','.join(sets)} "
            "WHERE code=%s AND date=%s AND adjust_type=%s"
        )
        with conn.cursor() as cur:
            cur.execute(sql, vals)

    def _mark_suspect(
        self,
        conn: pymysql.Connection,
        code: str,
        dt,
        existing: Dict[str, Any],
        batch_id: str,
    ) -> None:
        mask = q.merge_masks(existing.get("source_mask"), self.provider_id)
        sql = (
            f"UPDATE `{TABLE_BAR}` SET quality_status='suspect', "
            "source_mask=%s, last_batch_id=%s "
            "WHERE code=%s AND date=%s AND adjust_type=%s"
        )
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (json.dumps(mask), batch_id, code, dt, self.adjust_type),
            )
