# InStock 作业脚本说明（`instock/job`）

说明各 `*_daily_job.py` 的**功能**、**依赖**、**如何运行**。所有命令默认在**仓库根目录**（含 `requirements.txt`）执行；**Docker** 内路径见 §6。

**命令行日期规则** 由 `instock/lib/run_template.py` 的 `run_with_args` 统一处理：

| 命令行 | 行为 |
|--------|------|
| `python3 instock/job/某脚本.py` | 无参：对「最近交易日」等执行（部分「实时」子任务还会结合是否盘中，见各节说明） |
| `python3 instock/job/某脚本.py 2024-06-03,2024-06-05` | 多个日期，逗号分隔（仅**交易日**会跑） |
| `python3 instock/job/某脚本.py 2024-06-01 2024-06-28` | 区间内逐日（仅**交易日**） |

日志见 **`instock/log/stock_execute_job.log`**（本机）或容器内 **`/data/InStock/instock/log/stock_execute_job.log`**。

### Web 页面触发（推荐）

启动 Web 后访问：**http://localhost:9988/instock/sync**（左侧菜单 **「数据同步」**）。可在页面选择作业、日期模式（默认 / 枚举 / 区间）、一键启动；下方列表显示每次运行的 **成功 / 失败 / 运行中**、退出码及 **stdout/stderr 尾部**。记录保存在 **`instock/log/sync_job_history.json`**（重启进程后仍会加载最近条目）。

**注意**：与原版一致，接口**未做登录鉴权**，请勿暴露在公网。

---

## 1. `init_job.py`

| 项 | 说明 |
|----|------|
| **作用** | 若库不存在则创建 `instockdb`；建最简表（如关注表等）。 |
| **何时跑** | 首次部署、换库、需要确保库存在时。 |
| **用法** | `python3 instock/job/init_job.py` |
| **依赖** | MySQL 可连；`instock/lib/database.py` 配置正确。 |

---

## 2. `execute_daily_job.py`

| 项 | 说明 |
|----|------|
| **作用** | **总控流水线**：按固定顺序调用多个子 job 的 `main()`，写同一日志文件。 |
| **当前仓库中的顺序** | `init_job` → `basic_data_daily_job` → `selection_data_daily_job` → 线程池跑 `basic_data_other_daily_job` → **`basic_data_after_close_daily_job`**。 |
| **重要** | 源码里 **`indicators_data_daily_job`、`klinepattern_data_daily_job`、`strategy_data_daily_job`、`backtest_data_daily_job` 被注释掉**，不会自动跑指标/形态/策略/回测统计；需要时请**单独运行**对应脚本或自行改源码取消注释。 |
| **用法** | `python3 instock/job/execute_daily_job.py` 或带日期同上表。 |

---

## 3. `basic_data_daily_job.py`

| 项 | 说明 |
|----|------|
| **作用** | 抓取**当日 A 股全市场快照**、**ETF 快照**，写入 `cn_stock_spot`、`cn_etf_spot`。盘中可频繁更新。 |
| **依赖** | 东方财富等接口；无需先有历史库表即可写入（会 `CREATE`/追加）。 |
| **用法** | `python3 instock/job/basic_data_daily_job.py` 或带日期。 |
| **说明** | 使用 `run_with_args` +「实时」语义（内部 `save_nph_*` 对 `before` 参数有分支，无参时对齐最近交易日逻辑）。 |

---

## 4. `selection_data_daily_job.py`

| 项 | 说明 |
|----|------|
| **作用** | 抓取东方财富**综合选股**结果，写入 `cn_stock_selection`。 |
| **依赖** | 接口可用；与当日 `date` 字段删插策略见源码。 |
| **用法** | `python3 instock/job/selection_data_daily_job.py` 或带日期。 |

---

## 5. `basic_data_other_daily_job.py`

| 项 | 说明 |
|----|------|
| **作用** | 一批「其它基础数据」，其 `main()` **依次**调度（每个都走 `run_with_args`）：①东财龙虎榜统计并触发基本面选股子逻辑、②分红配送、③个股资金流（多日维度合并）、④行业/概念板块资金流、⑤早盘抢筹、⑥涨停原因等；对应表如 `cn_stock_lhb`、`cn_stock_bonus`、`cn_stock_fund_flow`、`cn_stock_fund_flow_industry`、`cn_stock_fund_flow_concept`、`cn_stock_chip_race_open`、`cn_stock_limitup_reason` 等（以 `tablestructure.py` 为准）。 |
| **依赖** | 部分依赖 **当日 `cn_stock_spot` 已有数据**（如龙虎榜流程里的 `stock_spot_buy` 从 spot 筛基本面）。建议先有 **`basic_data_daily_job`**。 |
| **用法** | `python3 instock/job/basic_data_other_daily_job.py` 或带日期。 |
| **说明** | 源码中还有 **`save_nph_stock_top_data`（新浪龙虎榜）**，**未挂入 `main()`**；若要用需改 `main()` 自行加入或临时写小程序调用。资金流接口失败时日志会出现 **502** 等，与 Cookie/网络有关，见 [quick-start.md](./quick-start.md) 常见问题。 |

---

## 6. `basic_data_after_close_daily_job.py`

| 项 | 说明 |
|----|------|
| **作用** | **收盘后更晚才有**或适合盘后跑的数据：**大宗交易**（`cn_stock_blocktrade`）、**尾盘抢筹**（`cn_stock_chip_race_end`）。 |
| **依赖** | 大宗接口盘中常无数据，日志可能提示稍后再抓；需当日交易日参数语义正确。 |
| **用法** | `python3 instock/job/basic_data_after_close_daily_job.py` 或带日期。 |

---

## 7. `indicators_data_daily_job.py`

| 项 | 说明 |
|----|------|
| **作用** | ① 拉全体股票**历史 K 线**（经 `stock_hist_data`），计算 **Talib 技术指标**，写入 `cn_stock_indicators`；② 从指标表用 SQL **粗筛**「买入」「卖出」条件，写入 **`cn_stock_indicators_buy`**、**`cn_stock_indicators_sell`**（供 Web 与后续回测统计使用）。 |
| **依赖** | **强烈依赖** 当日股票列表与行情上下文（通常需先 **`basic_data_daily_job`**）；计算量大、耗时长。 |
| **用法** | `python3 instock/job/indicators_data_daily_job.py` 或带日期。 |
| **说明** | 若 Web 报 **表 `cn_stock_indicators_buy` 不存在**，多数是因为从未成功跑过本脚本。 |

---

## 8. `klinepattern_data_daily_job.py`

| 项 | 说明 |
|----|------|
| **作用** | 基于历史 K 线做 **Talib K 线形态（CDL*）** 识别，写入 `cn_stock_pattern`。 |
| **依赖** | 历史数据；需 **`basic_data_daily_job`** 提供当日股票池上下文（与 `stock_hist_data` 机制一致）。 |
| **用法** | `python3 instock/job/klinepattern_data_daily_job.py` 或带日期。 |

---

## 9. `strategy_data_daily_job.py`

| 项 | 说明 |
|----|------|
| **作用** | 遍历 **`tablestructure.TABLE_CN_STOCK_STRATEGIES`** 中每条内置策略（放量上涨、均线多头、停机坪等），写入对应 **`cn_stock_strategy_*`** 表。 |
| **依赖** | 历史 K 线；与 `stock_hist_data` 相同依赖链，建议基础数据已就绪。 |
| **用法** | `python3 instock/job/strategy_data_daily_job.py` 或带日期。 |

---

## 10. `backtest_data_daily_job.py`

| 项 | 说明 |
|----|------|
| **作用** | 对 **`cn_stock_indicators_buy/sell`** 与各 **`cn_stock_strategy_*`** 中已有信号，按收盘价计算 **信号后 N 日累计涨跌** 等统计字段（「信号事后收益」），写回扩展列。 |
| **依赖** | 必须先有指标/策略表及对应日期数据；详见 [architecture.md](./architecture.md) **§10（回测在本项目中的含义）**。 |
| **用法** | `python3 instock/job/backtest_data_daily_job.py` 或带日期。 |

---

## 11. 推荐执行顺序（补全一日或历史区间）

单日内建议依赖顺序（简化）：

1. `init_job.py`（仅首次或必要）  
2. `basic_data_daily_job.py`  
3. `selection_data_daily_job.py`  
4. `basic_data_other_daily_job.py`  
5. 收盘后：`basic_data_after_close_daily_job.py`  
6. `indicators_data_daily_job.py`  
7. `klinepattern_data_daily_job.py`  
8. `strategy_data_daily_job.py`  
9. `backtest_data_daily_job.py`  

历史上按日期批量时，对每个交易日重复上述逻辑即可（仍可用区间/枚举参数）。

---

## 12. Docker 内如何运行

进入应用容器（名称一般为 `InStock`）：

```bash
docker exec -it InStock bash
cd /data/InStock/instock/job
python3 execute_daily_job.py
# 或
python3 indicators_data_daily_job.py
```

镜像内定时任务已可能调用 `execute_daily_job` / `basic_data_daily_job`，与手动执行不冲突时注意数据库当日数据是否重复覆盖（设计为按 `date` 删后插，一般可重跑）。

---

## 13. 相关文档

- [快速开始](./quick-start.md)  
- [架构说明](./architecture.md)（流水线、`execute_daily_job` 注释现状、回测含义）  
- [部署说明](./deployment.md)  
