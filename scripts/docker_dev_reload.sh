#!/usr/bin/env bash
# 开发挂载模式：构建 Vue 前端 + 重启 InStock 容器（后端 Python 经卷挂载即时生效）
#
# 在仓库根目录（含 requirements.txt）执行：
#   ./scripts/docker_dev_reload.sh
#   ./scripts/docker_dev_reload.sh --pip    # 同时在容器内 pip install 依赖
#   ./scripts/docker_dev_reload.sh --skip-npm # 仅重启容器（只改了后端）
#
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DOCKER_DIR="${REPO}/docker"
VUE_APP="${REPO}/instock/web/vue-app"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.dev.yml)
CONTAINER="${INSTOCK_CONTAINER_NAME:-InStock}"

SKIP_NPM=0
PIP_INSTALL=0
for arg in "$@"; do
  case "$arg" in
    --skip-npm) SKIP_NPM=1 ;;
    --pip) PIP_INSTALL=1 ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
    *)
      echo "未知参数: $arg（可用 --skip-npm --pip）" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${REPO}/requirements.txt" ]]; then
  echo "错误: 未在仓库根找到 requirements.txt，当前 REPO=${REPO}" >&2
  exit 1
fi

if [[ ! -d "${DOCKER_DIR}" ]]; then
  echo "错误: 找不到 ${DOCKER_DIR}" >&2
  exit 1
fi

export INSTOCK_REPO_ROOT="${REPO}"
echo "==> REPO=${REPO}"
echo "==> INSTOCK_REPO_ROOT=${INSTOCK_REPO_ROOT}"

# 首次挂载时容器内启动脚本需可执行
for f in run_web.sh run_job.sh run_cron.sh; do
  p="${REPO}/instock/bin/${f}"
  if [[ -f "$p" && ! -x "$p" ]]; then
    chmod +x "$p"
    echo "==> chmod +x instock/bin/${f}"
  fi
done

if [[ "$SKIP_NPM" -eq 0 ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "错误: 未找到 npm，请先安装 Node.js，或使用 --skip-npm" >&2
    exit 1
  fi
  echo "==> 构建前端: instock/web/vue-app"
  (
    cd "$VUE_APP"
    if [[ -f package-lock.json ]]; then
      npm ci
    else
      npm install
    fi
    npm run build
  )
  echo "==> 前端构建完成 -> instock/web/vue-dist"
else
  echo "==> 跳过 npm build（--skip-npm）"
fi

cd "$DOCKER_DIR"

if ! docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "==> 容器 ${CONTAINER} 不存在，执行 compose up -d"
  "${COMPOSE[@]}" up -d
elif docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "==> 重启容器 ${CONTAINER}"
  "${COMPOSE[@]}" restart instock
else
  echo "==> 容器 ${CONTAINER} 已停止，执行 compose up -d"
  "${COMPOSE[@]}" up -d
fi

if [[ "$PIP_INSTALL" -eq 1 ]]; then
  echo "==> 容器内安装 Python 依赖"
  docker exec "$CONTAINER" pip install -r /data/InStock/requirements.txt
fi

echo ""
echo "完成。访问: http://localhost:9988/instock/app"
echo "  任务中心: http://localhost:9988/instock/app/jobs"
echo "  数据同步: http://localhost:9988/instock/app/sync"
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "日志: docker logs ${CONTAINER} --tail 30 -f"
else
  echo "警告: ${CONTAINER} 未在运行，请检查: docker logs ${CONTAINER}" >&2
  exit 1
fi
