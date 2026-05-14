# InStock 部署说明

本文档补充官方 [README.md](../README.md) 中的安装说明，覆盖 **macOS 本机 Python** 与 **Docker** 两套流程，以及 **东方财富 Cookie** 的获取与配置。股市有风险，本系统仅供学习与研究。

**部署命令速查（精简）**：[deploy-cheatsheet.md](./deploy-cheatsheet.md) · **快速上手（运行方式与看日志）**：[quick-start.md](./quick-start.md) · **Docker 运维常用命令**：[docker-ops.md](./docker-ops.md) · **作业脚本说明**：[jobs.md](./jobs.md) · **架构与数据流**：[architecture.md](./architecture.md)

---

## 1. 部署方式概览

| 方式 | 说明 |
|------|------|
| **本机 Python** | 适合改源码、调试；需 Python 3.11、MySQL、TA-Lib 与依赖包。下文 **第 2 节**（macOS 步骤）。 |
| **Docker** | 适合快速体验、少装系统依赖；使用镜像 `mayanghua/instock` 与 `library/mariadb`。下文 **第 3 节**。 |

下文「**仓库根目录**」指含有 `requirements.txt` 与 `instock/` 包目录的那一层（克隆后的 `instock` 项目根路径）。

---

## 2. macOS 本机 Python 部署流程

README 中「常规安装」以 Windows 与 `.bat` 为主；在 Mac 上对应关系如下：依赖安装方式一致，**不要用** 仓库里 `instock/bin/run_web.sh`、`run_job.sh` 中写死的 `/data/InStock/...` 路径（那是给 Docker 用的），应在**仓库根目录**下用 `python3` 直接启动脚本。

### 2.1 环境准备

1. **Python 3.11**  
   从 [python.org](https://www.python.org/downloads/) 安装，或使用 `brew install python@3.11`。确认终端中 `python3 --version` 为 3.11.x。

2. **pip 镜像（可选，国内网络建议）**  

   ```bash
   python3 -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
   ```

3. **MySQL**  
   安装并启动 MySQL（可用 [官网安装包](https://dev.mysql.com/downloads/mysql/) 或 `brew install mysql` 等）。需能使用本机 `localhost`、端口 `3306`（或你实际使用的端口）连接。数据库名默认 **`instockdb`**（与代码一致即可，首次运行初始化作业会建表，见下）。

4. **TA-Lib（必须先装 C 库再装 Python 包）**  
   - 推荐：`brew install ta-lib`，再在仓库根目录执行 `python3 -m pip install TA-Lib`。  
   - 其他方式见 [TA-Lib 安装说明](https://ta-lib.org/install/)。

### 2.2 安装 Python 依赖

在**仓库根目录**执行：

```bash
cd /path/to/instock   # 替换为你的克隆路径
python3 -m pip install -r requirements.txt
```

### 2.3 配置数据库连接

编辑 **`instock/lib/database.py`**，按本机 MySQL 修改（示例为常见本地默认值）：

- `db_host`：本机一般为 `"localhost"`  
- `db_user`、`db_password`：你的 MySQL 账号  
- `db_port`：默认 `3306`  
- `db_database`：默认 `"instockdb"`  
- `db_charset`：保持 `utf8mb4`  

也可通过环境变量覆盖（与 Docker 相同变量名）：`db_host`、`db_user`、`db_password`、`db_database`、`db_port`。

### 2.4 代理与东方财富 Cookie（可选）

| 配置项 | 路径或方式 |
|--------|------------|
| 代理 | 编辑 **`instock/config/proxy.txt`**，每行一个 `ip:port` 或 `user:pass@ip:port`；不用代理则清空或删除内容后保存。修改后需**重启 Web / 作业进程**。 |
| Cookie | 编辑 **`instock/config/eastmoney_cookie.txt`** 写入整段 Cookie，或设置环境变量 **`EAST_MONEY_COOKIE`**。获取步骤见本文 **第 4 节**。 |

若 `instock/config/` 下尚无上述文件，可自行创建空文件或按需新建。

### 2.5 初始化数据库（首次）

在**仓库根目录**执行（脚本会把仓库根加入 `sys.path`，以便导入 `instock.lib` 等模块）：

```bash
python3 instock/job/init_job.py
```

若初始化失败，先确认 MySQL 已启动、账号密码与 `database.py` 一致，且已允许本机连接。

### 2.6 启动 Web

在**仓库根目录**执行：

```bash
python3 instock/web/web_service.py
```

浏览器访问：**http://localhost:9988/**

日志默认在 **`instock/log/stock_web.log`**。

### 2.7 执行数据作业

在**仓库根目录**执行整体日作业（支持 README 中说明的日期参数，此处不展开）：

```bash
python3 instock/job/execute_daily_job.py
```

单功能脚本同样在仓库根目录用 `python3 instock/job/xxx.py` 调用即可，例如：

```bash
python3 instock/job/basic_data_daily_job.py
```

更多批量日期、枚举、区间等写法见 README「安装说明 → 常规安装方式 → 运行说明」与「批量」相关章节。作业日志在 **`instock/log/stock_execute_job.log`**。

### 2.8 定时任务（可选）

README 建议工作日约 17:00 跑全量作业。Windows 用「任务计划程序」；在 macOS 上可使用 **cron** 或 **launchd**，自行将工作目录设为仓库根目录，并调用上述 `python3 instock/job/execute_daily_job.py`（或你封装好的 shell）。

### 2.9 自动交易（可选）

README 写明：**自动交易目前主要面向 Windows**（同花顺客户端、tesseract 等）。Mac 上一般只做数据抓取、指标与 Web 展示即可。

### 2.10 本机部署常见问题

| 现象或问题 | 处理建议 |
|------------|----------|
| `ModuleNotFoundError` / 找不到 `instock` | 确认当前目录为**仓库根目录**，且使用文档中的 `python3 instock/web/...` 路径启动，不要随意改工作目录除非你知道 `PYTHONPATH` 需求。 |
| TA-Lib 安装失败 | 先完成 **Homebrew 的 `ta-lib` C 库**，再 `pip install TA-Lib`；勿颠倒顺序。 |
| 连不上 MySQL | 检查 `database.py`、MySQL 是否监听 `127.0.0.1`、用户远程/本机权限。 |
| 东方财富限流 | 配置 Cookie 或代理，见第 4 节与上表。 |

---

## 3. macOS + Docker 部署流程

**Docker Compose 一键编排（推荐）**：仓库内 **`docker/docker-compose.yml`**，数据目录挂载为 **`/var/lib/mysql`**（与官方镜像一致，避免数据落入匿名卷）。常用启停、日志、备份思路见 **[docker-ops.md](./docker-ops.md)**。

### 3.1 前提条件

1. 安装并启动 [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)。
2. 终端执行 `docker version`，能同时看到 Client 与 Server 即表示可用。

### 3.2 准备本机目录与配置文件

官方示例使用宿主机路径 `/data/...`，在 Mac 上通常需要 `sudo`，且将**文件**挂载进容器时，宿主机上对应路径**必须已存在且为普通文件**（否则 Docker 可能误创建为目录）。

以下以 `~/instock-docker` 为例（可自行更换路径，但需与后续 `docker run` 的 `-v` 一致）：

```bash
mkdir -p ~/instock-docker/mariadb/data
touch ~/instock-docker/instockproxy.txt
touch ~/instock-docker/eastmoneycookie.txt
```

| 文件 | 用途 |
|------|------|
| `instockproxy.txt` | 代理列表；不用代理则保持**空文件**。每行一个：`ip:port` 或 `user:pass@ip:port`。修改后需**重启 InStock 容器**生效。 |
| `eastmoneycookie.txt` | 东方财富 Cookie；不用可留空。配置方法见本文第 4 节。 |

### 3.3 创建 Docker 网络

与官方 README 一致，网络名为 `InStockService`：

```bash
docker network create InStockService
```

若提示网络已存在，可忽略；或先停止并删除使用该网络的容器后，再执行 `docker network rm InStockService` 后重新创建。

### 3.4 启动数据库（MariaDB）

```bash
docker run -d --name InStockDbService \
  --network InStockService \
  -v ~/instock-docker/mariadb/data:/var/lib/instockdb \
  -e MYSQL_ROOT_PASSWORD=root \
  library/mariadb:latest
```

数据持久化在 `~/instock-docker/mariadb/data`（需将宿主机目录挂载到容器内 **`/var/lib/mysql`** 才是官方镜像实际数据目录；若误挂到 `/var/lib/instockdb`，数据会落在 Docker 匿名卷，见 [docker-ops.md](./docker-ops.md) 中 Compose 说明）。检查状态：

```bash
docker ps --filter name=InStockDbService
```

容器为 `Up` 后再启动应用。

### 3.5 启动 InStock 应用容器

```bash
docker run -dit --name InStock --network=InStockService \
  -p 9988:9988 \
  -v ~/instock-docker/instockproxy.txt:/data/InStock/instock/config/proxy.txt \
  -v ~/instock-docker/eastmoneycookie.txt:/data/InStock/instock/config/eastmoney_cookie.txt \
  -e db_host=InStockDbService \
  mayanghua/instock:latest
```

要点：

- **端口**：本机浏览器访问 **http://localhost:9988/**
- **`db_host=InStockDbService`**：必须与数据库容器的名称 `--name InStockDbService` 一致，且两容器均在 `InStockService` 网络上。
- **勿误用 `localhost`**：在应用容器内，`localhost` 指向容器自身，无法指向另一容器或宿主机 MySQL（除非按 README 另有说明自行改网络与主机名）。

首次运行会拉取镜像，耗时取决于网络。

### 3.5.1 挂载本机代码目录（开发 / 使用仓库内最新功能）

仅使用官方镜像、**不**挂载项目时，容器内跑的是镜像里**构建时**的代码；你在宿主机上 `git pull` 或改动的文件**不会**进入容器。

若希望容器直接使用本机克隆的代码（例如本仓库新增的 **数据同步** 页 `/instock/sync` 等），启动应用容器时增加整目录挂载，**建议与代理、Cookie 文件挂载同时使用**（路径与 [§3.2](#32-准备本机目录与配置文件) 一致）：

```bash
docker run -dit --name InStock --network=InStockService \
  -p 9988:9988 \
  -v /你的绝对路径/instock:/data/InStock \
  -v ~/instock-docker/instockproxy.txt:/data/InStock/instock/config/proxy.txt \
  -v ~/instock-docker/eastmoneycookie.txt:/data/InStock/instock/config/eastmoney_cookie.txt \
  -e db_host=InStockDbService \
  mayanghua/instock:latest
```

将 `/你的绝对路径/instock` 换成你本机仓库根目录（含 `requirements.txt` 与 `instock/` 子目录的那一层，例如 `~/stock/instock` 或 `/Users/用户名/stock/instock`）。

**重要：脚本需可执行（否则 Web 无法启动）**  
挂载后，supervisord 执行的是**宿主机上的** `instock/bin/run_*.sh`。在 macOS 上从 Git 检出的脚本常见为**不可执行**，会导致日志中出现 `spawnerr: ... is not executable`、`run_web entered FATAL state`，浏览器**无法访问 9988**。在**宿主机**仓库根目录执行一次：

```bash
chmod +x instock/bin/run_web.sh instock/bin/run_job.sh instock/bin/run_cron.sh
```

然后 `docker restart InStock`。建议将可执行位提交到 Git（`git add` 后这些文件会显示为模式变更），避免换机器后再次失败。

**Apple Silicon 上的平台提示**  
拉取或运行 `mayanghua/instock` 时可能出现 `linux/amd64` 与 `arm64` 不匹配的 **WARNING**，一般仍可通过模拟运行。若遇异常，可在 `docker run` 上增加 `--platform linux/amd64` 与官方行为对齐（可能略慢）。

### 3.6 验证

```bash
docker ps --filter name=InStock
```

浏览器打开：**http://localhost:9988/**

按 README，容器启动后会初始化并启动 Web，并有定时任务（如每小时基础数据、每日约 17:30 全量任务等）。

### 3.7 进容器执行补数或单次任务（可选）

```bash
docker exec -it InStock bash
cd /data/InStock/instock/job
python execute_daily_job.py
```

更多批量日期、单功能作业等见 README「docker 镜像安装方式」中「历史数据」一节。退出容器：`exit`。

### 3.8 查看日志

```bash
docker exec -it InStock bash
cat /data/InStock/instock/log/stock_execute_job.log
cat /data/InStock/instock/log/stock_web.log
```

### 3.9 停止与卸载（需要时）

```bash
docker container stop InStock InStockDbService
docker container rm InStock InStockDbService
```

删除镜像（下次会重新拉取）：

```bash
docker rmi mayanghua/instock:latest library/mariadb:latest
```

删除网络（需无容器占用）：

```bash
docker network rm InStockService
```

数据库文件仍保留在 `~/instock-docker/mariadb/data`，除非手动删除该目录。

### 3.10 常见问题（Mac / Docker）

| 现象或问题 | 处理建议 |
|------------|----------|
| 挂载后配置不生效 | 确认宿主机上是**文件**而非目录；修改代理或 Cookie 后**重启 InStock 容器**。 |
| 应用连不上库 | 确认 `db_host` 与数据库容器 `--name` 一致，且两容器在同一 `docker network`。 |
| 使用宿主机 MySQL | 将 `db_host` 设为 **`host.docker.internal`**（Docker Desktop for Mac），并正确配置 `db_user`、`db_password`、`db_database`、`db_port`；README 中 `db_host=localhost` 针对的是库与应用在同一网络命名空间内的场景。 |
| 仓库内 `docker/docker-compose.yml` | 已与 **`InStockService`** 网络、`db_host=InStockDbService`、端口 **9988 / 3306** 对齐；MariaDB 数据挂载 **`/var/lib/mysql`**。运维命令见 [docker-ops.md](./docker-ops.md)。 |
| 自动交易 | README 写明自动交易目前**仅支持 Windows**；Mac + Docker 一般仅使用数据与 Web 功能。 |
| **`docker logs` 出现 `is not executable`**、`run_web` **FATAL** | 未给 `instock/bin/run_web.sh` 等加执行权限，见上文 **§3.5.1**。 |
| **更新了仓库代码但容器里仍是旧行为** | 未挂载本机目录时，仅重启容器**不会**加载宿主机修改；需 **`-v 仓库根:/data/InStock`** 或自行 **`docker build`** 新镜像，见下文 **§3.11**。 |
| **拉镜像 TLS handshake timeout** | 网络或 Docker Hub 不稳定，稍后重试；或配置镜像加速 / 代理（见社区文档）。 |
| **页面上某表报「表不存在」**（如 `cn_stock_indicators_buy`） | 多为尚未跑过对应作业；在容器内执行 `indicators_data_daily_job.py`，或使用本仓库 Web 左侧菜单 **「数据同步」**（路径 **`/instock/sync`**，需挂载含该功能的代码），详见 [jobs.md](./jobs.md)。 |
| **作业日志里大量 502 Bad Gateway（东财）** | 多为接口侧网关问题或瞬时网络；可换时段重试、配置 Cookie；未必是 Cookie 单独失效。 |

### 3.11 更新代码后的容器操作小结

按你是否**挂载本机仓库**区分：

| 场景 | 更新代码后怎么做 |
|------|------------------|
| **未挂载**（仅用 `mayanghua/instock:latest`） | 宿主机改代码**不会影响**容器。要用新代码需：**①** 挂载目录（见 §3.5.1），或 **②** 用本仓库 `docker/Dockerfile` 自行构建镜像再替换 `docker run` 的镜像名。 |
| **已挂载** `-v /path/to/instock:/data/InStock` | 保存代码后即生效；仅 Python/Web 改动一般 **`docker restart InStock`**；若改了依赖（`requirements.txt`），需在镜像内安装或重建镜像。首次挂载或克隆后务必 **`chmod +x instock/bin/run_*.sh`**。 |

**推荐自检命令**（访问不了 9988 时优先执行）：

```bash
docker logs InStock --tail 50
docker exec InStock curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9988/
```

若日志中出现 **`not executable`**，回到 §3.5.1 执行 `chmod` 并重启容器。

**日志路径（挂载与本机一致时）**：容器内 **`/data/InStock/instock/log/`**（如 `stock_web.log`、`stock_execute_job.log`）；数据同步记录（若使用带该功能的代码）在 **`sync_job_history.json`** 同目录下。宿主机即你挂载目录下的 `instock/log/`。

---

## 4. 东方财富 Cookie 获取与配置

数据抓取频率过高时，东方财富可能限流，可通过注入 Cookie 缓解（与 README「设置东方财富网 Cookie」一致）。

### 4.1 在浏览器中获取 Cookie

1. 打开：**https://quote.eastmoney.com/center/gridlist.html#hs_a_board**
2. （建议）登录东方财富账号，Cookie 通常更稳定。
3. 打开开发者工具（Chrome / Edge / Arc 等：**⌥⌘I**），切换到 **Network（网络）**。
4. 刷新页面（**⌘R**）。
5. 在请求列表中选择 URL 包含 **`push2.eastmoney.com`** 的请求（没有则选 `eastmoney.com` 域名下的 XHR / fetch 请求）。
6. 在 **Request Headers（请求标头）** 中找到 **`Cookie:`**，复制**整段** Cookie 字符串。

### 4.2 写入项目 / Docker

- **本机 Python**：写入 **`instock/config/eastmoney_cookie.txt`**，或设置环境变量 **`EAST_MONEY_COOKIE`**（详见 README）。若 Cookie 含特殊字符，用文件保存通常比直接在 shell 里 `export` 更省事。
- **Docker（本文档第 3 节）**：将复制的内容写入宿主机 `~/instock-docker/eastmoneycookie.txt`，保存后执行 `docker restart InStock`。

### 4.3 注意事项

- Cookie 会过期（几天到数周不等），抓取异常时优先尝试重新获取。
- 建议定期更新；勿将 Cookie 提交到公开仓库或泄露给他人。

---

## 5. 与官方文档的关系

- 常规安装、自动交易、更多作业参数：**[README.md](../README.md)**「安装说明 → 常规安装方式」。
- Docker 镜像与 `-e` 环境变量：**[README.md](../README.md)**「安装说明 → docker 镜像安装方式」。
- Docker Hub：**https://hub.docker.com/r/mayanghua/instock**

若本文与 README 日后不一致，以 README 与镜像实际行为为准，欢迎在本仓库提交文档修正。
