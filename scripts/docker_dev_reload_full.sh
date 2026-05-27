#!/usr/bin/env bash
# 全量更新：构建 Vue 前端 + 重建 InStock 容器（较慢，约 2～5 分钟）
#
# 适用：改了 .vue / 前端路由 / 侧栏菜单 / 静态资源
#
# 用法:
#   ./scripts/docker_dev_reload_full.sh              # npm build + 重建容器
#   ./scripts/docker_dev_reload_full.sh --pip        # 同上 + pip install
#   ./scripts/docker_dev_reload_full.sh --quick      # 仍构建前端，但只 restart 不重建（少用）
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export DD_REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
export DD_SKIP_NPM=0
export DD_QUICK_RESTART=0
export DD_RELOAD_LABEL="全量（npm build + 重建容器）"

# shellcheck source=scripts/lib/docker_dev_reload_lib.sh
source "${SCRIPT_DIR}/lib/docker_dev_reload_lib.sh"
dd_reload_main "$@"
