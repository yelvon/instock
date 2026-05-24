# InStock — AI 助手项目上下文

> **用途**：跨对话保持对仓库的一致理解。人类文档见 [docs/文档索引.md](./docs/文档索引.md)。  
> **维护（AI 自维护）**：Cursor 规则要求助手在改 `instock/` 前先读本文件；**重大变更在同一轮对话内由助手更新**下文对应章节与 §9「近期变更」，勿复制长篇 plan 全文。用户无需手动维护本节。

---

## 1. 项目是什么

- **InStock**：A 股数据采集、指标/形态、选股、**事件驱动回测**、Web 展示；Docker 部署为主（`localhost:9988`）。
- **Python 包根**：`instock/instock/`（`import instock.*`）；**仓库根**：含 `requirements.txt`、`docker/`、`scripts/` 的那一层。
- **前端**：`instock/web/vue-app/`（Vue3 + Element Plus），构建产物 `instock/web/vue-dist/`。
- **Web 后端**：Tornado，`instock/web/`，任务由 `sync_job_service.py` 子进程跑 `instock/job/` 脚本。

---

## 2. 近期架构（数据源治理，2025–2026）

多源 **独立补数** → 幂等写入 **标准日线表** → 回测优先读标准库。

| 概念 | 位置 / 表 |
|------|-----------|
| 标准日线 | 表 `cn_stock_daily_bar`，迁移 `migrations/003_canonical_daily_bar.sql` |
| 来源贡献 | 表 `market_data_contribution` |
| 合并写入 | `instock/core/canonical/writer.py`（`CanonicalBarWriter`） |
| 回测读取 | `instock/core/canonical/reader.py`；开关 `INSTOCK_BACKTEST_USE_CANONICAL=1`（默认倾向开启） |
| 按源拉取 | `instock/core/canonical/source_fetch.py`、`instock/job/sync_bars_source_job.py` |
| Provider 注册 | `instock/core/data/registry.yaml` + `providers/`（含 `mootdx_local`、`akshare`、`tushare` 等） |
| 治理 API | `/instock/api/sync/canonical`、`data_sources_service.py` |
| 前端 | **回测数据管理** `/backtest-data`（概览/标准日线/补数/缺口）；任务中心 `MootdxLocalPanel`；回测 `/backtest` |
| 回测严格检查 | `profile=backtest` 时查 `canonical_daily_bar`，不默认要求 `cn_stock_spot` |

**旧路径仍存**：`instock/cache/hist/` pickle；新补数作业应写 `cn_stock_daily_bar`，不要假设只写 cache。

---

## 3. 目录速查

```
instock/
├── instock/job/              # 作业入口（sync_bars_*.py, basic_data_daily_job.py, …）
├── instock/core/
│   ├── canonical/            # 标准行情库
│   ├── data/providers/       # mootdx_local, akshare, …
│   ├── crawling/             # 东财等抓取
│   └── backtest/             # 回测引擎
├── instock/web/              # Tornado + vue-app + vue-dist
├── docker/                   # compose、Dockerfile、.env
├── scripts/                  # docker_dev_reload.sh, verify_*.py
├── migrations/               # SQL 迁移
└── docs/                     # 中文文档（部署、通达信、mootdx）
```

---

## 4. 关键环境变量

| 变量 | 含义 |
|------|------|
| `INSTOCK_TDX_DIR` | 容器内通达信根目录（含 `vipdoc/`），compose 常为 `/tdx` |
| `INSTOCK_TDX_DIR_HOST` | **宿主机**挂载源，在 `docker/.env`（如 `~/tdx-docker-mount` → Parallels `C:\new_tdx`） |
| `INSTOCK_UNIVERSE_SOURCE` | `local` = 从 vipdoc 扫代码；`online` = 在线列表 |
| `INSTOCK_BAR_DATA_SOURCE` | 遍历拉 K 线时的源：`mootdx` / `tushare` / `auto` 等 |
| `INSTOCK_USE_DATA_REGISTRY` | `1` 走 Registry 多源 |
| `INSTOCK_BAR_MODE` | 常为 `raw`（未复权标准库） |
| `INSTOCK_BACKTEST_USE_CANONICAL` | 回测读 `cn_stock_daily_bar` |
| `TUSHARE_TOKEN` | Tushare；勿写入本文件，用 `docker/.env` 或 `config/tushare_token.txt` |

示例见 [.env.example](./.env.example)、[docker/.env](./docker/.env)（含密钥，**勿提交**）。

---

## 5. 常用作业（任务中心 / API）

| job_id | 说明 |
|--------|------|
| `sync_bars_mootdx_local_job` | **仅本地 vipdoc** → `cn_stock_daily_bar`；需 `INSTOCK_TDX_DIR` + 证券主表 |
| `sync_bars_mootdx_job` | mootdx 在线/混合 |
| `sync_bars_tushare_job` / `sync_bars_akshare_job` / `sync_bars_eastmoney_job` | 各源独立补标准表 |
| `mootdx_bars_sync_job` | 旧版遍历写 cache/hist（治理页仍可能见到） |
| 预设 `mootdx_local` | `sync_presets.py`：universe local + `sync_bars_mootdx_local_job` |

验证本地通达信：

```bash
docker exec -e INSTOCK_TDX_DIR=/tdx InStock python3 /data/InStock/scripts/verify_tdx_local.py --tdx-dir /tdx
```

---

## 6. Docker 部署（本机常见）

- **Compose**：`docker/docker-compose.yml` + `docker-compose.dev.yml`（挂载 `INSTOCK_REPO_ROOT`）。
- **一键重建**（默认 **删容器再 up**，不是单纯 restart）：

  ```bash
  cd instock && ./scripts/docker_dev_reload.sh
  ```

  - `--quick`：仅 restart（**不会**应用新 env/卷）。
  - `--pip`：容器内 `pip install -r requirements.txt`。
  - 默认重建后会检测并 `pip install mootdx`（Hub 镜像 `mayanghua/instock:latest` **不带** mootdx/akshare）。

- **通达信挂载**：`${INSTOCK_TDX_DIR_HOST}:/tdx:ro`，容器内 `INSTOCK_TDX_DIR=/tdx`。
- **排障**：
  - 页面有 vipdoc 计数但 healthcheck `No module named 'mootdx'` → 容器内缺包，`pip install mootdx` 或跑 `docker_dev_reload.sh`。
  - 改了 compose/.env 仍不生效 → 必须 **recreate**，不要只 restart。
  - Web 装包后仍报错 → `docker exec InStock supervisorctl restart run_web`。

详见 [docs/部署命令速查.md](./docs/部署命令速查.md)、[docs/mootdx通达信-mac虚拟机.md](./docs/mootdx通达信-mac虚拟机.md)。

---

## 7. 开发约定（给 AI）

1. **先读本文件**：动手改 `instock/` 前阅读本文（见 `.cursor/rules/instock-context.mdc`）。
2. **自维护本文**：重大变更完成后更新相关章节 + §9，见下表。
3. **最小改动**：只动与需求相关的文件；匹配现有命名与分层。
4. **不要改** `docs/plan/` 里已批准的 plan 文件，除非用户明确要求。
5. **不要提交** `.env`、`docker/.env`、token；用户未要求不要 `git commit`。
6. **用户语言**：回复用 **中文**。
7. **验证**：声称修复完成前，在 Docker 或本机跑相关脚本/接口（见 `scripts/verify_*.py`、`tests/test_canonical_quality.py`）。
8. **前端改完**：在 `instock/web/vue-app` 执行 `npm run build`，产物进 `vue-dist`。

### 何时必须更新 AGENTS.md

| 变更类型 | 更新位置 |
|----------|----------|
| 新表 / 标准库逻辑 | §2、§8 链接 |
| 新作业 / 预设 | §5 |
| 环境变量 / Docker | §4、§6 |
| 前端主流程 | §2 前端行、§8 |
| 新踩坑 | §6 排障、§9 表格 |
| 任意重大功能 | §9「近期变更」+ 文首日期 |

---

## 8. 文档地图（按需深入）

| 主题 | 文档 |
|------|------|
| **通达信 → Mac 同步** | [docs/通达信数据同步Mac.md](./docs/通达信数据同步Mac.md) |
| 架构总览 | [docs/架构说明.md](./docs/架构说明.md) |
| 作业列表 | [docs/作业说明.md](./docs/作业说明.md) |
| 回测 API | [docs/回测-api契约.md](./docs/回测-api契约.md) |
| 数据管线规划 | [docs/plan/数据管线.md](./docs/plan/数据管线.md) |
| Registry / 多源 | [docs/plan/数据域.md](./docs/plan/数据域.md) |

---

## 9. 近期变更（请随开发更新）

| 日期 | 变更 |
|------|------|
| 2026-05 | 标准表 `cn_stock_daily_bar`、多源 `sync_bars_*_job`、任务中心「通达信本地」 |
| 2026-05 | Docker：`INSTOCK_TDX_DIR=/tdx`，`docker_dev_reload.sh` 默认 force-recreate；Dockerfile/脚本补装 `mootdx` |
| 2026-05-21 | 新增 `AGENTS.md` + `.cursor/rules/instock-context.mdc`：助手先读、重大变更自维护 |
| 2026-05-24 | 通达信本地补数：Parallels 挂载 `/tdx` 并发读 `.day` 易 `Errno 5 EIO`（`INSTOCK_MOOTDX_LOCAL_WORKERS=1`）；mootdx 归一化须把 index `date` 落列否则写入 0 行 |
| 2026-05-24 | Mac 本地盘 `~/tdx-local`；操作手册 [docs/通达信数据同步Mac.md](./docs/通达信数据同步Mac.md)；Mac 触发 `trigger_tdx_sync_from_mac.sh` |
| 2026-05 | SPA **回测数据管理** `/backtest-data`；`cn_stock_daily_bar` 表页双模式；回测 `profile=backtest` 严格检查标准日线 |
| 2026-05 | 宿主机运维：`scripts/host_ops_server.py` + 页面「Mac 宿主机运维」（同步 vipdoc / docker_dev_reload） |

---

*最后更新：2026-05*
