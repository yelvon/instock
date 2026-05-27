#!/usr/bin/env bash
# 仅更新后端：不构建 Vue，默认快速 restart（数秒～十几秒）
#
# 适用：改了 Python / 任务脚本 / API，开发挂载已启用 INSTOCK_REPO_ROOT
#
# 用法（在 instock 仓库根或任意目录）:
#   ./scripts/docker_dev_reload_backend.sh           # 默认 --quick
#   ./scripts/docker_dev_reload_backend.sh --recreate  # 改了 docker/.env 或 TDX 挂载路径
#   ./scripts/docker_dev_reload_backend.sh --pip       # 补装 Python 依赖（pytdx 等）
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export DD_REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
export DD_SKIP_NPM=1
export DD_QUICK_RESTART=1
export DD_RELOAD_LABEL="后端（跳过 npm，默认 restart）"

# shellcheck source=scripts/lib/docker_dev_reload_lib.sh
source "${SCRIPT_DIR}/lib/docker_dev_reload_lib.sh"
dd_reload_main "$@"
