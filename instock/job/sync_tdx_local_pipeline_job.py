#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键：证券主表(本地) → 标准库 raw → ingest gbbq → 派生 qfq。

  python sync_tdx_local_pipeline_job.py --qfq-mode full
  python sync_tdx_local_pipeline_job.py --qfq-mode incremental
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

cpath_current = os.path.dirname(os.path.dirname(__file__))
cpath = os.path.abspath(os.path.join(cpath_current, os.pardir))
sys.path.append(cpath)
JOB_DIR = os.path.join(cpath_current, "job")


def _run(script: str, extra: list[str] | None = None) -> int:
    cmd = [sys.executable, os.path.join(JOB_DIR, script)] + (extra or [])
    print("$", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=cpath)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--qfq-mode", choices=("incremental", "full"), default="incremental")
    p.add_argument("--skip-universe", action="store_true")
    p.add_argument("--skip-bars", action="store_true")
    args = p.parse_args()

    env = os.environ.copy()
    env["INSTOCK_UNIVERSE_SOURCE"] = "local"
    if not args.skip_universe:
        r = subprocess.call(
            [sys.executable, os.path.join(JOB_DIR, "sync_stock_universe_job.py")],
            cwd=cpath,
            env=env,
        )
        if r != 0:
            return r

    if not args.skip_bars:
        r = _run(
            "sync_bars_source_job.py",
            ["--source", "mootdx_local", "--workers", "1", "--sleep", "0.02"],
        )
        if r != 0:
            return r

    r = _run("ingest_tdx_gbbq_job.py")
    if r != 0:
        return r

    extra = ["--mode", args.qfq_mode]
    if args.qfq_mode == "full":
        extra.extend(["--from-date", "19900101"])
    return _run("derive_qfq_from_tdx_job.py", extra)


if __name__ == "__main__":
    raise SystemExit(main())
