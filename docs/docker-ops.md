# InStock Docker 运维常用命令

与 [部署说明（deployment.md）](./deployment.md) 第 3 节配合使用。股市有风险，本系统仅供学习与研究。

**Compose 文件位置**：仓库内 `docker/docker-compose.yml`（同目录有 `.env.example` 与 `docker-compose.dev.yml`）。

---

## 1. 使用 Docker Compose 启停

在 **`docker/` 目录**下执行（路径请按你本机仓库调整）：

```bash
cd /path/to/instock/docker
```

**首次准备目录与空文件**（与 deployment 一致，默认用家目录下 `instock-docker`）：

```bash
mkdir -p ~/instock-docker/mariadb/data
touch ~/instock-docker/instockproxy.txt ~/instock-docker/eastmoneycookie.txt
```

**启动（后台）**：

```bash
docker compose up -d
```

**停止**（不删卷、不删网络，数据保留）：

```bash
docker compose stop
```

**停止并删除容器**（默认 **不** 删命名/匿名卷，数据库文件一般仍在；删卷需显式 `docker volume rm` 或 `down -v`）：

```bash
docker compose down
```

**拉取新镜像后重建容器**：

```bash
docker compose pull
docker compose up -d
```

**开发模式：额外挂载本机代码**（需先 `chmod +x` 宿主机上 `instock/bin/run_*.sh`）：

```bash
export INSTOCK_REPO_ROOT=/你的绝对路径/instock
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

---

## 2. 状态与日志

| 目的 | 命令 |
|------|------|
| 运行中的容器 | `docker ps` 或 `docker ps --filter name=InStock` |
| 含已停止的容器 | `docker ps -a` |
| 应用日志 | `docker logs InStock --tail 100 -f` |
| 数据库日志 | `docker logs InStockDbService --tail 100 -f` |
| 仅看最近 50 行 | `docker logs InStock --tail 50` |

---

## 3. 进入容器

| 目的 | 命令 |
|------|------|
| 进应用容器 shell | `docker exec -it InStock sh` 或 `bash`（视镜像是否有 bash） |
| 进库、用客户端 | `docker exec -it InStockDbService mariadb -uroot -proot` |
| 在应用容器里测 HTTP | `docker exec InStock python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:9988/').status)"` |

密码与 **`MYSQL_ROOT_PASSWORD`** / **`deployment.md`** 一致；若改过 root 密码请替换 `-proot`。

---

## 4. 重启与单一容器更新

```bash
docker restart InStock
docker restart InStockDbService
```

修改宿主机上挂载的 **proxy.txt / eastmoney_cookie.txt** 后，一般需要 **`docker restart InStock`** 生效。

---

## 5. 资源与占用

| 目的 | 命令 |
|------|------|
| 磁盘占用概览 | `docker system df` 或 `docker system df -v` |
| 卷列表 | `docker volume ls` |
| 查看某卷详情 | `docker volume inspect <卷名>` |

数据库逻辑大小（库表）可在 MariaDB 内查 `information_schema`；数据目录在容器内一般为 **`/var/lib/mysql`**（Compose 已把宿主机目录挂到此路径）。

---

## 6. 网络与端口

| 目的 | 命令 |
|------|------|
| 查看应用映射端口 | `docker port InStock 9988` |
| 查看数据库映射 | `docker port InStockDbService 3306` |
| 本机谁占用 9988 | `lsof -i :9988` |

Compose 使用网络名 **`InStockService`**；应用通过 **`db_host=InStockDbService`** 解析数据库容器。

---

## 7. 备份与恢复（思路）

| 目的 | 思路 |
|------|------|
| 逻辑备份 | `docker exec InStockDbService mariadb-dump -uroot -p --all-databases` 或只备份 `instockdb`，重定向到宿主机文件 |
| 物理备份 | 停库后打包挂载到 **`/var/lib/mysql`** 的宿主机目录（Compose 下即 **`~/instock-docker/mariadb/data`**） |

恢复前务必停写、确认版本兼容，生产环境建议以官方备份文档为准。

---

## 8. 清理（慎用）

| 命令 | 风险 |
|------|------|
| `docker container prune` | 删除**已停止**的容器 |
| `docker image prune` | 删除悬空镜像 |
| `docker volume prune` | 删除**未被任何容器使用**的卷 → **可能删掉数据库卷** |

不确定时先用 **`docker volume ls`**、**`docker inspect`** 确认卷用途，避免误删。

---

## 9. DataGrip / 本机客户端连库

- **主机**：`127.0.0.1`
- **端口**：与 **`MARIADB_HOST_PORT`**（默认 **3306**）一致
- **用户 / 库**：与 **`MYSQL_ROOT_PASSWORD`、`DB_*`** 或代码默认一致（一般为 `root` / `instockdb`）

---

## 10. 常见问题速查

| 现象 | 处理 |
|------|------|
| 9988 无法访问 | `docker logs InStock`；挂载代码时检查 **`instock/bin/run_web.sh`** 是否 **`chmod +x`** |
| 应用连不上库 | `docker network inspect InStockService`；确认 **`db_host=InStockDbService`** 与容器名一致 |
| DataGrip 只有系统库 | 确认端口映射、账号密码；执行 **`SHOW DATABASES;`**；首次需 **`init_job`** 等初始化 |

更多部署细节见 **[deployment.md](./deployment.md)**。
