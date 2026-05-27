#!/usr/bin/env bash
# 兼容入口：等同全量更新（npm + 重建）。日常改 Python 请用 docker_dev_reload_backend.sh
#
#   ./scripts/docker_dev_reload.sh              # 全量（慢）
#   ./scripts/docker_dev_reload_backend.sh      # 仅后端（快，推荐）
#   ./scripts/docker_dev_reload_full.sh         # 全量（与本文等价）
#
exec "$(cd "$(dirname "$0")" && pwd)/docker_dev_reload_full.sh" "$@"
