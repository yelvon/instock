#!/usr/bin/env bash
# 从 Parallels 共享目录把通达信 vipdoc 拷到 Mac 本地（供 Docker 挂载，避免 Errno 5 EIO）
#
# 更快方案（推荐）: 在 Windows 虚拟机运行 scripts/windows/sync_tdx_to_mac.bat
# 日常增量: 同上 bat（robocopy /XO），或本脚本加 -u 见 sync_tdx_incremental.sh
set -euo pipefail

SRC="${TDX_VM_SRC:-/Users/fwj/tdx-docker-mount}"
DST="${TDX_LOCAL_DST:-$HOME/tdx-local}"
LOG="${TDX_SYNC_LOG:-$HOME/tdx-local-rsync.log}"

if [[ ! -d "$SRC/vipdoc/sh/lday" ]]; then
  echo "源目录不存在: $SRC/vipdoc（请确认 Parallels 已挂载 C:\\new_tdx）" >&2
  exit 1
fi

mkdir -p "$DST"
echo "==> 源: $SRC/vipdoc"
echo "==> 目标: $DST/vipdoc"
echo "==> 日志: $LOG"
echo "    （通过 Parallels 读盘较慢，约 400MB，预计 5～15 分钟，属正常）"
echo ""

# 不用 --delete，避免误删；--partial 可断点续传
rsync -a --partial --human-readable \
  "$SRC/vipdoc/" "$DST/vipdoc/" \
  2>&1 | tee -a "$LOG"

sh_n=$(find "$DST/vipdoc/sh/lday" -name '*.day' 2>/dev/null | wc -l | tr -d ' ')
sz_n=$(find "$DST/vipdoc/sz/lday" -name '*.day' 2>/dev/null | wc -l | tr -d ' ')
echo ""
echo "==> 完成: 沪 $sh_n · 深 $sz_n 个 .day"
echo "    下一步: 改 docker/.env → INSTOCK_TDX_DIR_HOST=$DST"
echo "    然后: cd instock && ./scripts/docker_dev_reload.sh"
