#!/usr/bin/env bash
# 开发挂载模式：构建 Vue 前端 + 用 compose 重建/重启 InStock 容器
#
# 在仓库根目录（含 requirements.txt）执行：
#   ./scripts/docker_dev_reload.sh              # 默认：--force-recreate instock（应用 docker/.env、TDX 挂载）
#   ./scripts/docker_dev_reload.sh --quick      # 仅 restart（改 Python 代码时用，不刷新环境变量/卷）
#   ./scripts/docker_dev_reload.sh --pip        # 重建后再 pip install 依赖
#   ./scripts/docker_dev_reload.sh --skip-npm   # 跳过前端构建
#
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DOCKER_DIR="${REPO}/docker"
VUE_APP="${REPO}/instock/web/vue-app"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.dev.yml)
CONTAINER="${INSTOCK_CONTAINER_NAME:-InStock}"
DB_CONTAINER="${INSTOCK_DB_CONTAINER_NAME:-InStockDbService}"

SKIP_NPM=0
PIP_INSTALL=0
QUICK_RESTART=0
for arg in "$@"; do
  case "$arg" in
    --skip-npm) SKIP_NPM=1 ;;
    --pip) PIP_INSTALL=1 ;;
    --quick) QUICK_RESTART=1 ;;
    -h|--help)
      sed -n '2,10p' "$0"
      exit 0
      ;;
    *)
      echo "未知参数: $arg（可用 --skip-npm --pip --quick）" >&2
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

# 读取 docker/.env（INSTOCK_TDX_DIR_HOST、TUSHARE_TOKEN 等）
if [[ -f "${DOCKER_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${DOCKER_DIR}/.env"
  set +a
fi

# 通达信挂载路径：优先 docker/.env，否则默认 ~/tdx-docker-mount
export INSTOCK_TDX_DIR_HOST="${INSTOCK_TDX_DIR_HOST:-${HOME}/tdx-docker-mount}"

echo "==> REPO=${REPO}"
echo "==> INSTOCK_REPO_ROOT=${INSTOCK_REPO_ROOT}"
echo "==> INSTOCK_TDX_DIR_HOST=${INSTOCK_TDX_DIR_HOST}"

if [[ ! -d "${INSTOCK_TDX_DIR_HOST}/vipdoc" ]]; then
  echo "警告: ${INSTOCK_TDX_DIR_HOST}/vipdoc 不存在。" >&2
  echo "  Parallels 需开机；或执行: ln -sfn \"/Volumes/[C] Windows 11/new_tdx\" ~/tdx-docker-mount" >&2
  echo "  并在 Win 通达信完成盘后数据下载。" >&2
fi

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

_ensure_network() {
  if ! docker network inspect InStockService >/dev/null 2>&1; then
    echo "==> 创建网络 InStockService"
    docker network create InStockService
  fi
}

_recreate_instock() {
  _ensure_network
  if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "==> 删除旧容器 ${CONTAINER}（保留 ${DB_CONTAINER}，避免库名冲突）"
    docker stop "$CONTAINER" 2>/dev/null || true
    docker rm "$CONTAINER" 2>/dev/null || true
  fi
  if docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    echo "==> 数据库容器 ${DB_CONTAINER} 已在运行，仅创建 ${CONTAINER}（--no-deps）"
    "${COMPOSE[@]}" up -d --no-deps instock
  else
    echo "==> 启动完整栈（db + instock）"
    "${COMPOSE[@]}" up -d
  fi
}

_quick_restart() {
  if ! docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "==> 容器 ${CONTAINER} 不存在，改为 compose 创建"
    _recreate_instock
    return
  fi
  if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "==> 快速重启 ${CONTAINER}（不重建，环境变量/卷不变）"
    "${COMPOSE[@]}" restart instock
  else
    echo "==> 容器 ${CONTAINER} 已停止，compose up instock"
    "${COMPOSE[@]}" up -d --no-deps instock 2>/dev/null || "${COMPOSE[@]}" up -d
  fi
}

if [[ "$QUICK_RESTART" -eq 1 ]]; then
  _quick_restart
else
  echo "==> 重建 ${CONTAINER}（应用 compose 中 INSTOCK_TDX_DIR=/tdx 与卷挂载）"
  _recreate_instock
fi

_ensure_mootdx() {
  if docker exec "$CONTAINER" python3 -c "import mootdx" 2>/dev/null; then
    echo "    mootdx 已安装"
    return 0
  fi
  echo "==> 容器内安装 mootdx（Hub 镜像默认未带，requirements.txt 里有）"
  docker exec "$CONTAINER" pip install 'mootdx>=0.11.7'
}

if [[ "$PIP_INSTALL" -eq 1 ]]; then
  echo "==> 容器内安装全部 Python 依赖（requirements.txt）"
  docker exec "$CONTAINER" pip install -r /data/InStock/requirements.txt
else
  _ensure_mootdx
fi

echo ""
echo "==> 校验通达信挂载"
if docker exec "$CONTAINER" printenv INSTOCK_TDX_DIR 2>/dev/null | grep -q .; then
  echo "    INSTOCK_TDX_DIR=$(docker exec "$CONTAINER" printenv INSTOCK_TDX_DIR)"
  if docker exec "$CONTAINER" test -d /tdx/vipdoc/sh/lday 2>/dev/null; then
    echo "    /tdx/vipdoc/sh/lday OK"
  else
    echo "    警告: 容器内 /tdx/vipdoc 不可见，请检查 INSTOCK_TDX_DIR_HOST 与 Parallels" >&2
  fi
else
  echo "    警告: 容器内未设置 INSTOCK_TDX_DIR（mootdx 本地将不可用）" >&2
fi

echo ""
echo "完成。访问: http://localhost:9988/instock/app"
echo "  任务中心 → 通达信本地: http://localhost:9988/instock/app/jobs?tab=mootdx"
echo "  数据同步: http://localhost:9988/instock/app/sync"
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "日志: docker logs ${CONTAINER} --tail 30 -f"
else
  echo "警告: ${CONTAINER} 未在运行，请检查: docker logs ${CONTAINER}" >&2
  exit 1
fi
