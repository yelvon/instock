#!/bin/sh
# 在仓库的 docker/ 目录执行。将上级目录（仓库根）同步到 ./stock 供 Dockerfile COPY。
set -e

REPO_ROOT="$(cd .. && pwd)"
cd "$(dirname "$0")"

rm -rf stock
rsync -av --progress "${REPO_ROOT}/" stock/ \
  --exclude .git --exclude .idea --exclude '*.md' --exclude '*.bat' \
  --exclude __pycache__ --exclude .gitignore \
  --exclude docker --exclude img \
  --exclude instock/cache --exclude instock/log --exclude instock/test \
  --exclude 'instock/web/vue-app/node_modules' \
  --exclude 'instock/web/vue-dist'

rm -rf cron
cp -r "${REPO_ROOT}/cron" cron

DOCKER_NAME=mayanghua/instock
TAG1=$(date "+%Y%m")
TAG2=latest

echo " docker build -f Dockerfile -t ${DOCKER_NAME}:${TAG2} -t ${DOCKER_NAME}:${TAG1} ."
docker build -f Dockerfile -t "${DOCKER_NAME}:${TAG2}" -t "${DOCKER_NAME}:${TAG1}" .

echo "#################################################################"
echo " 本地使用: docker compose up -d --force-recreate instock"
echo " 推送到 Docker Hub 需 mayanghua 账号登录，且设置 DO_PUSH=1 后才会 push"
if [ "${DO_PUSH}" = "1" ]; then
  echo " docker push ${DOCKER_NAME} "
  docker push "${DOCKER_NAME}:${TAG1}"
  docker push "${DOCKER_NAME}:${TAG2}"
fi
