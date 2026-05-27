#!/usr/bin/env bash
# 在 Mac 上触发 Parallels Windows 虚拟机执行 sync_tdx_to_mac.bat（通达信 → ~/tdx-local）
#
# 每次运行前会把 Mac 仓库最新 bat 部署到 C:\ProgramData\InStock\（避免 VM 里旧副本）
#
# 依赖: Parallels Desktop、prlctl、虚拟机已装 Parallels Tools、共享文件夹 Z: → Mac 用户目录
#
# 用法:
#   ./scripts/trigger_tdx_sync_from_mac.sh
#   PRL_VM_NAME="Windows 11" ./scripts/trigger_tdx_sync_from_mac.sh
#
# 环境变量:
#   PRL_VM_NAME     虚拟机名称（默认 Windows 11）
#   PRL_START_VM    若 VM 未运行是否自动启动（默认 1）
#   SKIP_STATUS     设为 1 则同步后不跑 tdx_local_status.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/lib/prl_tdx_sync.sh
source "$(dirname "$0")/lib/prl_tdx_sync.sh"

LOG_MAC="${HOME}/tdx-local-rsync.log"

prl_ensure_vm_running
prl_deploy_sync_bat

echo ""
echo "==> 在「${PRL_VM_NAME}」中执行同步: ${PRL_BAT_DEPLOY_WIN}"
echo "    vipdoc + gbbq；详细 robocopy 见 Windows %USERPROFILE%\\sync_tdx_to_mac.log"
echo "    终端仅显示英文摘要行，避免 GBK 乱码"
echo ""

DECODER="$(dirname "$0")/lib/decode_prl_output.py"
set +e
prl_run_sync_bat 2>&1 | python3 "$DECODER" | tee -a "$LOG_MAC"
rc=${PIPESTATUS[0]}
set -e

echo ""
echo "==> Windows exit code: ${rc} (robocopy 0-7 = OK)"
echo "    Mac 日志追加: ${LOG_MAC}"

if [[ "${SKIP_STATUS:-0}" != "1" ]]; then
  echo ""
  "$(dirname "$0")/tdx_local_status.sh" || true
fi

if [[ "$rc" -ge 8 ]]; then
  exit "$rc"
fi
exit 0
