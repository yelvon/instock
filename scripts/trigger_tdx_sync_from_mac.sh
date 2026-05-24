#!/usr/bin/env bash
# 在 Mac 上触发 Parallels Windows 虚拟机执行 sync_tdx_to_mac.bat（通达信 → ~/tdx-local）
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
VM_NAME="${PRL_VM_NAME:-Windows 11}"
BAT_WIN='Z:\stock\instock\scripts\windows\sync_tdx_to_mac.bat'
LOG_MAC="${HOME}/tdx-local-rsync.log"

if ! command -v prlctl >/dev/null 2>&1; then
  echo "未找到 prlctl，请确认已安装 Parallels Desktop" >&2
  exit 1
fi

_vm_status() {
  prlctl list -o status -n "$VM_NAME" 2>/dev/null | awk 'NR==2 {print; exit}'
}

status="$(_vm_status || true)"
if [[ "$status" != "running" ]]; then
  if [[ "${PRL_START_VM:-1}" == "1" ]]; then
    echo "==> 虚拟机「${VM_NAME}」未运行（当前: ${status:-未知}），正在启动…"
    prlctl start "$VM_NAME"
    echo "    等待 Windows 就绪（约 30s）…"
    sleep 30
  else
    echo "虚拟机「${VM_NAME}」未运行，请先启动或设 PRL_START_VM=1" >&2
    exit 1
  fi
fi

if [[ ! -f "$REPO_ROOT/scripts/windows/sync_tdx_to_mac.bat" ]]; then
  echo "缺少 $REPO_ROOT/scripts/windows/sync_tdx_to_mac.bat" >&2
  exit 1
fi

echo "==> 在「${VM_NAME}」中执行: $BAT_WIN"
echo "    Mac 日志（robocopy 详细日志在 Windows 用户目录 sync_tdx_to_mac.log）"
echo ""

# 必须用 --current-user，否则访问不到 Z: 共享盘
set +e
prlctl exec "$VM_NAME" --current-user cmd.exe /c "call ${BAT_WIN}"
rc=$?
set -e

echo ""
echo "==> Windows exit code: ${rc} (robocopy 0-7 = OK)"
echo "    Log: ${LOG_MAC}"

if [[ "${SKIP_STATUS:-0}" != "1" ]]; then
  echo ""
  "$(dirname "$0")/tdx_local_status.sh" || true
fi

if [[ "$rc" -ge 8 ]]; then
  exit "$rc"
fi
exit 0
