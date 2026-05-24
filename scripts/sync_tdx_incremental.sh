#!/usr/bin/env bash
# Mac 侧增量备选：从 Parallels 共享盘 rsync 到 ~/tdx-local（比 Windows robocopy 慢，无需开 CMD）
# 推荐日常仍用 scripts/windows/sync_tdx_to_mac.bat（虚拟机里跑，最快）
set -euo pipefail

SRC="${TDX_VM_SRC:-/Users/fwj/tdx-docker-mount}"
DST="${TDX_LOCAL_DST:-$HOME/tdx-local}"
LOG="${TDX_SYNC_LOG:-$HOME/tdx-local-rsync.log}"

if [[ ! -d "$SRC/vipdoc/sh/lday" ]]; then
  echo "源不可用: $SRC（Parallels 未挂载?）" >&2
  exit 1
fi

mkdir -p "$DST"
echo "==> 增量: $SRC/vipdoc → $DST/vipdoc"
echo "    (-u 仅更新源比目标新的文件，与 robocopy /XO 类似)"
echo "    日志: $LOG"

# -u update: skip files newer on receiver; -a archive
rsync -au --partial "$SRC/vipdoc/" "$DST/vipdoc/" 2>&1 | tee -a "$LOG"

exec "$(dirname "$0")/tdx_local_status.sh"
