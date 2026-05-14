# 与当前仓库结构的衔接

本文档说明规划层与现有 InStock 代码布局的对应关系，减少实施时迷路。

## 目录映射（概念）

| 规划主题 | 现有或预期代码位置 |
|----------|-------------------|
| 数据抓取与核心逻辑 | `instock/core/`（如 `stockfetch.py`、`tablestructure.py`） |
| 每日批处理 | `instock/job/*_daily_job.py`、`execute_daily_job.py` |
| Web 与 API | `instock/web/`（`web_service.py`、`*Handler.py`） |
| 数据库连接 | `instock/lib/database.py` |
| 内置策略/选股 | `instock/core/strategy/` |
| 交易/机器人（与回测隔离） | `instock/trade/` |
| 启动脚本 | `instock/bin/*.sh` |
| Schema 文档脚本 | `scripts/gen_database_schema_doc.py` |

---

## 已知注意点

1. **`execute_daily_job.py`**  
   仓库中曾对部分并行步骤（指标、K 线、策略、回测等）使用注释方式关闭。长期维护建议改为**显式配置**（环境变量或 YAML），并在 `ops-scheduling.md` 中约定「默认流水线」与「精简流水线」，避免每人本地行为不一致。

2. **Docker 与本地路径**  
   `instock/bin/run_web.sh`、`run_job.sh` 中示例路径为 `/data/InStock/...`，本地开发需改为实际项目根或统一用环境变量表示根路径。

3. **依赖版本**  
   `requirements.txt` 已钉版本；回测与策略层新增库时应继续钉版本以利复现（见 `backtest.md` 复现性章节）。

4. **Web 同步作业**  
   `instock/web/sync_job_service.py` 及相关 Handler 可作为「作业可观测」的扩展基础，不必从零搭建。

---

## 实施建议

- 新功能优先在**独立模块**中实现，通过薄适配层调用现有 `core`/`job`，便于分 PR 合并。
- 每完成一个 `roadmap.md` 阶段，在本文件「进度」小节追加一行链接到 PR 或提交说明（可选）。

### 进度（可选维护）

| 阶段 | 状态 | 备注 |
|------|------|------|
| 阶段 1 | 未开始 | |
| 阶段 2 | 未开始 | |
| … | | |
