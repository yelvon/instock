# -*- coding: utf-8 -*-
"""写入 cn_stock_daily_bar_qfq（仅派生，不走多源 merge）。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd
import pymysql

import instock.lib.database as mdb
from instock.core.adjustment.schema import ensure_qfq_tables
from instock.core.canonical.bar_tables import PROVIDER_QFQ_DERIVED, TABLE_BAR_QFQ
from instock.core.canonical import quality as q
from instock.core.data.lineage import record_canonical_batch

logger = logging.getLogger(__name__)


@dataclass
class QfqWriteStats:
    upserted: int = 0
    errors: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {"upserted": self.upserted, "errors": self.errors}


class QfqBarWriter:
    def __init__(self, factor_version: str = ""):
        ensure_qfq_tables()
        self.factor_version = factor_version or ""

    def write_dataframe(
        self,
        code: str,
        df: pd.DataFrame,
        *,
        batch_id: Optional[str] = None,
    ) -> QfqWriteStats:
        stats = QfqWriteStats()
        code = str(code).zfill(6)[:6]
        if df is None or df.empty:
            return stats
        bid = batch_id or record_canonical_batch(
            PROVIDER_QFQ_DERIVED,
            scope_key=code,
            row_count=len(df),
            job_id="derive_qfq_from_tdx_job",
        )
        work = df.copy()
        if "date" in work.columns:
            work["_dt"] = pd.to_datetime(work["date"], errors="coerce").dt.date
        else:
            return stats

        conn = pymysql.connect(**mdb.MYSQL_CONN_DBAPI)
        try:
            with conn.cursor() as cur:
                for _, row in work.iterrows():
                    dt = row.get("_dt")
                    if dt is None:
                        stats.errors += 1
                        continue
                    try:
                        vals = {
                            "open": row.get("open"),
                            "close": row.get("close"),
                            "high": row.get("high"),
                            "low": row.get("low"),
                            "volume": row.get("volume"),
                            "amount": row.get("amount"),
                        }
                        cur.execute(
                            f"""
                            INSERT INTO `{TABLE_BAR_QFQ}`
                            (date, code, open, close, high, low, volume, amount,
                             quality_status, completeness_score, primary_source, source_mask,
                             factor_version, derived_from_batch_id, last_batch_id)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'derived',100,%s,%s,%s,%s,%s)
                            ON DUPLICATE KEY UPDATE
                              open=VALUES(open), close=VALUES(close),
                              high=VALUES(high), low=VALUES(low),
                              volume=VALUES(volume), amount=VALUES(amount),
                              factor_version=VALUES(factor_version),
                              derived_from_batch_id=VALUES(derived_from_batch_id),
                              last_batch_id=VALUES(last_batch_id),
                              updated_at=CURRENT_TIMESTAMP
                            """,
                            (
                                dt,
                                code,
                                vals["open"],
                                vals["close"],
                                vals["high"],
                                vals["low"],
                                vals["volume"],
                                vals["amount"],
                                PROVIDER_QFQ_DERIVED,
                                json.dumps([PROVIDER_QFQ_DERIVED]),
                                self.factor_version,
                                bid,
                                bid,
                            ),
                        )
                        stats.upserted += 1
                    except Exception as e:
                        stats.errors += 1
                        logger.warning("qfq upsert %s %s: %s", code, dt, e)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return stats

    def write_factor_rows(
        self, code: str, factor: pd.Series, factor_version: str
    ) -> int:
        ensure_qfq_tables()
        code = str(code).zfill(6)[:6]
        n = 0
        conn = pymysql.connect(**mdb.MYSQL_CONN_DBAPI)
        try:
            with conn.cursor() as cur:
                for dt, fv in factor.items():
                    d = pd.Timestamp(dt).strftime("%Y-%m-%d")
                    cur.execute(
                        """
                        INSERT INTO cn_stock_adj_factor (code, date, adjust_kind, qfq_factor, factor_version)
                        VALUES (%s,%s,'qfq',%s,%s)
                        ON DUPLICATE KEY UPDATE qfq_factor=VALUES(qfq_factor),
                          factor_version=VALUES(factor_version)
                        """,
                        (code, d, float(fv), factor_version),
                    )
                    n += 1
            conn.commit()
        finally:
            conn.close()
        return n
