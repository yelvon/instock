#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decode prlctl/Windows mixed UTF-8 + GBK stdout for Mac terminal."""

from __future__ import annotations

import sys


def decode_line(raw: bytes) -> str:
    if not raw:
        return ""
    raw = raw.rstrip(b"\r\n")
    if not raw:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    for enc in ("gb18030", "gbk", "cp936"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def main() -> int:
    buf = sys.stdin.buffer
    out = sys.stdout
    while True:
        line = buf.readline()
        if not line:
            break
        text = decode_line(line)
        if text:
            out.write(text + "\n")
            out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
