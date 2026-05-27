#!/usr/bin/env bash
# 开发环境 Docker 重载公共逻辑（由 docker_dev_reload_backend / _full 调用）
# 环境变量（调用方设置默认值）：
#   DD_SKIP_NPM=0|1
#   DD_QUICK_RESTART=0|1

set -euo pipefail

dd_reload_main() {
  local REPO="${DD_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  local DOCKER_DIR="${REPO}/docker"
  local VUE_APP="${REPO}/instock/web/vue-app"
  local COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.dev.yml)
  local CONTAINER="${INSTOCK_CONTAINER_NAME:-InStock}"
  local DB_CONTAINER="${INSTOCK_DB_CONTAINER_NAME:-InStockDbService}"

  local SKIP_NPM="${DD_SKIP_NPM:-0}"
  local PIP_INSTALL=0
  local QUICK_RESTART="${DD_QUICK_RESTART:-0}"

  for arg in "$@"; do
    case "$arg" in
      --skip-npm) SKIP_NPM=1 ;;
      --no-skip-npm) SKIP_NPM=0 ;;
      --pip) PIP_INSTALL=1 ;;
      --quick) QUICK_RESTART=1 ;;
      --recreate) QUICK_RESTART=0 ;;
      -h|--help)
        dd_reload_usage
        exit 0
        ;;
      *)
        echo "未知参数: $arg" >&2
        dd_reload_usage >&2
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

  if [[ -f "${DOCKER_DIR}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${DOCKER_DIR}/.env"
    set +a
  fi

  export INSTOCK_TDX_DIR_HOST="${INSTOCK_TDX_DIR_HOST:-${HOME}/tdx-local}"

  echo "==> REPO=${REPO}"
  echo "==> INSTOCK_REPO_ROOT=${INSTOCK_REPO_ROOT}"
  echo "==> INSTOCK_TDX_DIR_HOST=${INSTOCK_TDX_DIR_HOST}"
  echo "==> 模式: ${DD_RELOAD_LABEL:-reload}"

  if [[ ! -d "${INSTOCK_TDX_DIR_HOST}/vipdoc" ]]; then
    echo "警告: ${INSTOCK_TDX_DIR_HOST}/vipdoc 不存在。" >&2
    echo "  Parallels 需开机；或 ln -sfn 通达信目录到 ~/tdx-local" >&2
  fi

  for f in run_web.sh run_job.sh run_cron.sh; do
    p="${REPO}/instock/bin/${f}"
    if [[ -f "$p" && ! -x "$p" ]]; then
      chmod +x "$p"
      echo "==> chmod +x instock/bin/${f}"
    fi
  done

  if [[ "$SKIP_NPM" -eq 0 ]]; then
    if ! command -v npm >/dev/null 2>&1; then
      echo "错误: 未找到 npm，请安装 Node.js 或使用后端脚本 docker_dev_reload_backend.sh" >&2
      exit 1
    fi
    echo "==> 构建前端: instock/web/vue-app（约 1～3 分钟）"
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
    echo "==> 跳过前端构建（后端模式）"
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
      echo "==> 删除旧容器 ${CONTAINER}（保留 ${DB_CONTAINER}）"
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
      echo "==> 快速重启 ${CONTAINER}（Python 挂载代码立即生效）"
      "${COMPOSE[@]}" restart instock
    else
      echo "==> 容器 ${CONTAINER} 已停止，compose up instock"
      "${COMPOSE[@]}" up -d --no-deps instock 2>/dev/null || "${COMPOSE[@]}" up -d
    fi
  }

  if [[ "$QUICK_RESTART" -eq 1 ]]; then
    _quick_restart
  else
    echo "==> 重建 ${CONTAINER}（应用 docker/.env、INSTOCK_TDX_DIR 挂载）"
    _recreate_instock
  fi

  _ensure_mootdx() {
    if docker exec "$CONTAINER" python3 -c "import mootdx" 2>/dev/null; then
      echo "    mootdx 已安装"
      return 0
    fi
    echo "==> 容器内安装 mootdx"
    docker exec "$CONTAINER" pip install 'mootdx>=0.11.7'
  }

  _ensure_pytdx() {
    if docker exec "$CONTAINER" python3 -c "from pytdx.reader import GbbqReader" 2>/dev/null; then
      echo "    pytdx 已安装（gbbq）"
      return 0
    fi
    echo "==> 容器内安装 pytdx"
    docker exec "$CONTAINER" pip install 'pytdx>=1.72'
  }

  if [[ "$PIP_INSTALL" -eq 1 ]]; then
    echo "==> 容器内安装全部 Python 依赖"
    docker exec "$CONTAINER" pip install -r /data/InStock/requirements.txt
  else
    _ensure_mootdx
    _ensure_pytdx
  fi

  echo ""
  echo "==> 校验通达信挂载"
  if docker exec "$CONTAINER" printenv INSTOCK_TDX_DIR 2>/dev/null | grep -q .; then
    echo "    INSTOCK_TDX_DIR=$(docker exec "$CONTAINER" printenv INSTOCK_TDX_DIR)"
    if docker exec "$CONTAINER" test -d /tdx/vipdoc/sh/lday 2>/dev/null; then
      echo "    /tdx/vipdoc/sh/lday OK"
    else
      echo "    警告: 容器内 /tdx/vipdoc 不可见" >&2
    fi
  else
    echo "    警告: 容器内未设置 INSTOCK_TDX_DIR" >&2
  fi

  echo ""
  echo "完成。访问: http://localhost:9988/instock/app"
  if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "日志: docker logs ${CONTAINER} --tail 30 -f"
  else
    echo "警告: ${CONTAINER} 未在运行" >&2
    exit 1
  fi
}

dd_reload_usage() {
  cat <<'EOF'
用法见各入口脚本头部说明。
公共参数:
  --quick      仅 restart 容器（最快，改 Python 用）
  --recreate   删除并重建容器（改 docker/.env、/tdx 挂载用）
  --pip        容器内 pip install -r requirements.txt
  --skip-npm   跳过前端构建
  --no-skip-npm 强制构建前端
EOF
}
