# 通达信数据同步到 Mac 本地（操作手册）

本文说明如何把 **Windows 虚拟机里的通达信 vipdoc 日线** 同步到 Mac 本地目录，供 InStock Docker 挂载使用，并支持 **盘后增量更新**。

**相关文档**：[mootdx通达信-mac虚拟机.md](./mootdx通达信-mac虚拟机.md)（架构、mootdx、任务中心补数）· [部署命令速查.md](./部署命令速查.md)

---

## 1. 为什么要同步到 Mac 本地？

| 方式 | 问题 |
|------|------|
| Docker 直接挂载 Parallels 共享盘 `C:\new_tdx` | 高并发读 `.day` 易出现 **Errno 5 Input/output error**，补数几乎全失败 |
| 先拷到 Mac 本机盘 `~/tdx-local` 再挂载 Docker | **稳定**，与 InStock `mootdx_local` 兼容 |

**原则**：虚拟机只负责下载/更新数据；**Mac 本地盘**给 Docker 读。

---

## 2. 目录与路径约定

| 位置 | 路径 | 说明 |
|------|------|------|
| Windows 通达信根目录 | `C:\new_tdx` | 含 `vipdoc\sh\lday\*.day`（路径按你安装调整） |
| Mac 本地目标 | `~/tdx-local` | 即 `/Users/<你>/tdx-local` |
| Mac 本地结构 | `~/tdx-local/vipdoc/sh/lday/`、`sz/lday/` | **不要**只拷 `vipdoc` 里的子目录而漏层级 |
| Docker 容器内 | `/tdx` | `INSTOCK_TDX_DIR=/tdx`，由 compose 挂载 `~/tdx-local` |
| Windows 看 Mac 家目录 | `Z:\` | Parallels 共享文件夹（`prlctl --current-user` 下可用） |
| 仓库脚本（Windows） | `Z:\stock\instock\scripts\windows\sync_tdx_to_mac.bat` | 与 Mac 仓库同步 |

`docker/.env` 中应配置：

```bash
INSTOCK_TDX_DIR_HOST=/Users/<你的用户名>/tdx-local
```

---

## 3. 前置条件

- [ ] **Parallels Desktop** + **Windows 11**（或你的通达信虚拟机）已安装 **Parallels Tools**
- [ ] 虚拟机内通达信已做 **盘后数据下载**（沪/深 A 股日线）
- [ ] Parallels **共享文件夹**已开，Windows 资源管理器能访问 **`Z:\`**（即 Mac 用户目录）
- [ ] Mac 上 InStock 仓库路径示例：`/Users/<你>/stock/instock`

---

## 4. 推荐流程总览

```text
┌─────────────────────────────────────┐
│  Windows：通达信「盘后数据下载」       │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  同步 vipdoc → ~/tdx-local（见 §5）   │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  Mac：tdx_local_status.sh 校验数量   │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  docker/.env + docker_dev_reload.sh   │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│  任务中心：② 补标准日线（仅本地）      │
└─────────────────────────────────────┘
```

---

## 5. 同步数据（三选一）

### 5.1 方式 A：Mac 一键触发（推荐日常）

在 **Mac 终端**执行（会自动在 Windows 里跑 `robocopy /XO` 增量）：

```bash
cd /Users/<你>/stock/instock
bash ./scripts/trigger_tdx_sync_from_mac.sh
```

| 环境变量 | 含义 |
|----------|------|
| `PRL_VM_NAME` | 虚拟机名称，默认 `Windows 11` |
| `PRL_START_VM=1` | VM 未运行时自动启动（默认开） |
| `SKIP_STATUS=1` | 同步后跳过本地数量校验 |

依赖：`prlctl`（Parallels 命令行）。若 `./scripts/trigger_tdx_sync_from_mac.sh` 无输出即退出，请改用 **`bash ./scripts/...`**。

### 5.2 方式 B：Windows 手动/计划任务（最快、最稳）

在 **Windows 虚拟机 CMD** 中：

```bat
mkdir Z:\tdx-local\vipdoc 2>nul
Z:\stock\instock\scripts\windows\sync_tdx_to_mac.bat
```

或直接：

```bat
robocopy C:\new_tdx\vipdoc Z:\tdx-local\vipdoc /E /XO /R:2 /W:3
```

- **首次**与**日后增量**用**同一条命令**；`/XO` 只复制新增或更新的文件。
- 日志：`%USERPROFILE%\sync_tdx_to_mac.log`
- 可选：Windows **任务计划程序** 工作日 17:30 运行上述 bat（晚于通达信自动下载）。

### 5.3 方式 C：Mac 上 rsync（备选，较慢）

不打开 Windows CMD 时，从 Parallels 挂载盘拷到本地（经 Mac 读共享盘，**慢于方式 B**）：

```bash
./scripts/sync_tdx_incremental.sh
# 或首次/断点：./scripts/sync_tdx_from_vm.sh
```

源默认：`/Users/<你>/tdx-docker-mount`（指向 `C:\new_tdx` 的符号链接）。

---

## 6. 同步后校验

### 6.1 文件数量

```bash
./scripts/tdx_local_status.sh
```

| 市场 | 期望约 |
|------|--------|
| 沪 `sh/lday` | **4790** 个 `.day` |
| 深 `sz/lday` | **4391** 个 `.day` |

与虚拟机 `vipdoc` 数量一致即 **拷贝完整**。

### 6.2 与虚拟机源对比（可选）

```bash
ls ~/tdx-local/vipdoc/sh/lday | wc -l
ls ~/tdx-docker-mount/vipdoc/sh/lday | wc -l   # 若仍有共享盘挂载
```

### 6.3 日期区间（了解通达信下了多少年）

```bash
docker exec -e INSTOCK_TDX_DIR=/tdx InStock \
  python3 /data/InStock/scripts/tdx_date_range_report.py \
  --codes 600000,000001,399001
```

**常见情况**（以你本机盘后配置为准）：

| 类型 | 约略区间 |
|------|----------|
| 多数 A 股 | **2020-01-02 ~ 最近交易日**（约 1500+ 根/只） |
| 部分指数 | 可早至 **1990 年代** |
| 晚上市股票 | 从上市日起 |

需要更早历史：在通达信 **盘后数据下载** 里把起始年份调早 → 重新下载 → 再跑 §5 增量同步。

### 6.4 Docker 内可读性

```bash
docker exec -e INSTOCK_TDX_DIR=/tdx InStock \
  python3 /data/InStock/scripts/verify_tdx_local.py --code 600000
```

应输出 `OK: provider=mootdx_local rows=...`。

---

## 7. 接上 InStock Docker

### 7.1 配置挂载

编辑 `instock/docker/.env`：

```bash
INSTOCK_TDX_DIR_HOST=/Users/<你>/tdx-local
```

### 7.2 重建容器（必须 recreate，不要只 restart）

```bash
cd /Users/<你>/stock/instock
./scripts/docker_dev_reload.sh
```

脚本会校验容器内 `/tdx/vipdoc/sh/lday` 可访问。

### 7.3 写入标准库

浏览器打开 **任务中心 → 通达信本地**：

1. **① 同步证券主表（本地）**（`INSTOCK_UNIVERSE_SOURCE=local`）
2. **② 补标准日线（仅本地）**（`sync_bars_mootdx_local_job`）

---

## 8. 日常盘后操作清单（可打印）

| 步骤 | 在哪里做 | 做什么 |
|------|----------|--------|
| 1 | Windows 通达信 | 盘后数据下载（沪/深日线） |
| 2 | Mac 终端 | `bash ./scripts/trigger_tdx_sync_from_mac.sh` |
| 3 | Mac 终端 | `./scripts/tdx_local_status.sh` |
| 4 | 可选 | 任务中心跑 ② 补标准日线（仅本地） |

---

## 9. 脚本速查

| 脚本 | 运行环境 | 用途 |
|------|----------|------|
| `scripts/trigger_tdx_sync_from_mac.sh` | Mac | **推荐**：`prlctl` 触发 Windows 同步 |
| `scripts/windows/sync_tdx_to_mac.bat` | Windows | `robocopy /XO` 增量 |
| `scripts/tdx_local_status.sh` | Mac | 检查 `~/tdx-local` 文件数 |
| `scripts/sync_tdx_incremental.sh` | Mac | rsync 增量（备选） |
| `scripts/sync_tdx_from_vm.sh` | Mac | rsync 全量/断点（备选） |
| `scripts/tdx_date_range_report.py` | Docker/Mac | 抽样看日期区间 |
| `scripts/verify_tdx_local.py` | Docker | 单票健康检查 |
| `scripts/docker_dev_reload.sh` | Mac | 应用新 `INSTOCK_TDX_DIR_HOST` |

---

## 10. 常见问题

### Q1：`robocopy` 退出码 0~7 算失败吗？

不算。0~7 表示有文件复制或无需复制；**≥8** 才是真错误。

### Q2：Mac 上沪/深数量够，但补数仍失败？

- 确认 `docker/.env` 指向 **`~/tdx-local`**，且已 **`docker_dev_reload.sh`** 重建。
- 容器内执行 `verify_tdx_local.py`；若 OK 再跑任务中心 ②。

### Q3：`trigger_tdx_sync_from_mac.sh` 乱码或失败？

- 使用 **`bash ./scripts/trigger_tdx_sync_from_mac.sh`**。
- 确认 Windows 能访问 **`Z:\stock\instock\...`**。
- 可直接在 Windows 运行 **`sync_tdx_to_mac.bat`**（效果相同）。

### Q4：想要 2015 年以前的数据？

通达信里加长下载区间 → 盘后下载 → 再增量同步（§5）。本地 `.day` 里有什么，InStock 才能读什么。

### Q5：标准库行数很少，但文件已有 9000+？

文件同步 ≠ 已入库。需在任务中心执行 **② 补标准日线（仅本地）** 写入 `cn_stock_daily_bar`。

### Q6：补标准日线大量 `Can't connect to MySQL` / `Errno 99`？

**不是通达信读失败**（`[FETCH]` 正常），是写库时 **每行新建 MySQL 连接** 把容器临时端口耗尽。处理：

1. **停止**当前补数任务；
2. 更新代码后 **重建 InStock 容器**（`./scripts/docker_dev_reload.sh`）；
3. 重新跑 **② 补标准日线（仅本地）**（默认 `workers=1`）。

已写入库的约 14 只不会丢，幂等合并会跳过已有行。

---

## 11. 与本机路径示例（fwj）

以下为当前仓库常用配置，换机器时请改用户名：

```bash
# Mac
~/tdx-local                          # robocopy 目标
/Users/fwj/stock/instock             # 仓库
INSTOCK_TDX_DIR_HOST=/Users/fwj/tdx-local

# Windows
C:\new_tdx                           # 通达信根目录
Z:\stock\instock\scripts\windows\sync_tdx_to_mac.bat
```

---

*最后更新：2026-05-24*
