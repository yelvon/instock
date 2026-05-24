#!/usr/bin/env bash
# 检查 Mac 本地通达信 vipdoc 是否齐全（拷完后 / 增量后运行）
set -euo pipefail

DST="${TDX_LOCAL_DST:-$HOME/tdx-local}"
SH="$DST/vipdoc/sh/lday"
SZ="$DST/vipdoc/sz/lday"

if [[ ! -d "$SH" ]]; then
  echo "FAIL: 未找到 $SH"
  echo "  请先在 Windows 虚拟机运行: scripts\\windows\\sync_tdx_to_mac.bat"
  exit 1
fi

sh_n=$(find "$SH" -name '*.day' 2>/dev/null | wc -l | tr -d ' ')
sz_n=$(find "$SZ" -name '*.day' 2>/dev/null | wc -l | tr -d ' ')
echo "本地目录: $DST"
echo "沪 .day: $sh_n"
echo "深 .day: $sz_n"

if [[ "$sh_n" -lt 4000 ]] || [[ "$sz_n" -lt 3500 ]]; then
  echo "WARN: 数量偏少，可能尚未全量同步或路径不对"
  exit 2
fi
echo "OK: 数量正常，可设置 INSTOCK_TDX_DIR_HOST=$DST 并 docker_dev_reload.sh"
exit 0
