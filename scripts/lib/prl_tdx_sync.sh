#!/usr/bin/env bash
# Parallels + TDX sync bat deploy (sourced by trigger / push scripts)

PRL_VM_NAME="${PRL_VM_NAME:-Windows 11}"
PRL_BAT_DEPLOY_WIN='C:\ProgramData\InStock\sync_tdx_to_mac.bat'

prl_mac_path_to_win_z() {
  local p="$1"
  local home="${HOME:-}"
  if [[ -n "$home" && "$p" == "$home"/* ]]; then
    local rel="${p#"$home"/}"
    printf 'Z:\\%s' "${rel//\//\\}"
    return 0
  fi
  return 1
}

prl_ensure_vm_running() {
  if ! command -v prlctl >/dev/null 2>&1; then
    echo "未找到 prlctl，请确认已安装 Parallels Desktop" >&2
    exit 1
  fi
  local status
  status="$(prlctl list -o status -n "$PRL_VM_NAME" 2>/dev/null | awk 'NR==2 {print; exit}')"
  if [[ "$status" == "running" ]]; then
    return 0
  fi
  if [[ "${PRL_START_VM:-1}" != "1" ]]; then
    echo "虚拟机「${PRL_VM_NAME}」未运行" >&2
    exit 1
  fi
  echo "==> 启动虚拟机「${PRL_VM_NAME}」…"
  prlctl start "$PRL_VM_NAME"
  sleep 30
}

prl_deploy_sync_bat() {
  local repo_root="${REPO_ROOT:-}"
  if [[ -z "$repo_root" ]]; then
    echo "REPO_ROOT 未设置" >&2
    exit 1
  fi
  local bat_mac="${repo_root}/scripts/windows/sync_tdx_to_mac.bat"
  if [[ ! -f "$bat_mac" ]]; then
    echo "缺少 $bat_mac" >&2
    exit 1
  fi
  local bat_z
  if ! bat_z="$(prl_mac_path_to_win_z "$bat_mac")"; then
    echo "仓库不在 \$HOME 下，无法映射 Z: 路径: $bat_mac" >&2
    exit 1
  fi
  echo "==> 部署 sync bat -> ${PRL_BAT_DEPLOY_WIN}"
  echo "    从共享盘: ${bat_z}"

  # PowerShell 拷贝，避免 cmd 引号/UTF-8 问题
  prlctl exec "$PRL_VM_NAME" --current-user powershell.exe -NoProfile -Command \
    "\$src='${bat_z}'; \$dst='${PRL_BAT_DEPLOY_WIN}'; New-Item -ItemType Directory -Force -Path (Split-Path \$dst) | Out-Null; if (-not (Test-Path \$src)) { Write-Error \"not found: \$src\"; exit 1 }; Copy-Item -Force \$src \$dst; if (-not (Test-Path \$dst)) { exit 1 }; Select-String -Path \$dst -Pattern 'version=4' -Quiet; if (-not \$?) { Write-Warning 'bat may not be v4' }; Write-Host '[OK] deployed'"

  local rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "[ERROR] deploy failed, prlctl exit $rc" >&2
    echo "    请在 Windows 打开: ${bat_z}" >&2
    exit 1
  fi
}

prl_run_sync_bat() {
  prlctl exec "$PRL_VM_NAME" --current-user cmd.exe /c "call ${PRL_BAT_DEPLOY_WIN}"
}
