#!/usr/bin/env bash
# 将 Mac 仓库内最新 sync_tdx_to_mac.bat 部署到 Windows 虚拟机（不执行同步）
#
# 用法: ./scripts/push_sync_bat_to_vm.sh
# 环境: PRL_VM_NAME（默认 Windows 11）、PRL_START_VM=1

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/lib/prl_tdx_sync.sh
source "$(dirname "$0")/lib/prl_tdx_sync.sh"

prl_ensure_vm_running
prl_deploy_sync_bat
echo "==> 已部署到 Windows: ${PRL_BAT_DEPLOY_WIN}"
echo "    源 (Mac): ${REPO_ROOT}/scripts/windows/sync_tdx_to_mac.bat"
echo "    共享盘路径: $(prl_mac_path_to_win_z "${REPO_ROOT}/scripts/windows/sync_tdx_to_mac.bat")"
