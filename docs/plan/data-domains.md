# 回测相关数据域说明

与 [`instock/core/data/registry.yaml`](../instock/core/data/registry.yaml) 为配置真相；表结构见 [`tablestructure.py`](../instock/core/tablestructure.py)。

## 数据域一览

| domain_id | 主表/产物 | 自然键 | 主链权威源 |
|-----------|-----------|--------|------------|
| `trade_calendar` | `trade_calendar` | `cal_date` | DB 同步 job |
| `daily_spot_snapshot` | `cn_stock_spot`, `cn_etf_spot` | `date`, `code` | 东财 |
| `daily_bar_raw` | `cache/hist/*.pickle` | `code`, `date` | `mootdx_local`（有 TDX 目录） |
| `derived_indicators` | 指标/形态/策略表 | `date`, `code` | 本地计算，依赖上游 batch |

## chain 与 enrich

- **chain**：决定整表/整行主数据来源；`backtest` profile 下 `strict: true` 失败即停止，不静默换源。
- **enrich**：主链成功后补列；`tencent` 仅补 PE/PB/市值等空字段，不覆盖东财已有值。

## K 线：raw 与 qfq

- 本地 TDX `vipdoc/*/lday/*.day` 为 **raw**，不等于前复权。
- 本期 `INSTOCK_BAR_MODE=raw`；`daily_bar_adjusted`（qfq）延后。

## 环境变量

| 变量 | 说明 |
|------|------|
| `INSTOCK_DATA_PROFILE` | `live` / `backtest` |
| `INSTOCK_TDX_DIR` | 通达信安装根目录（含 `vipdoc/`） |
| `INSTOCK_BAR_MODE` | `raw`（默认） |
| `INSTOCK_TENCENT_ENRICH` | live 默认开；backtest 建议 `0` |
| `INSTOCK_USE_DATA_REGISTRY` | `1` 时 spot/K 线路径走 Registry |

## TDX 离线目录

- Windows 常见：`C:/new_tdx`
- Docker：`-v /path/to/tdx:/tdx:ro`，`INSTOCK_TDX_DIR=/tdx`
- 需本机通达信先同步日线到 `vipdoc/sh/lday`、`vipdoc/sz/lday`

## 接入第 N 个数据源

1. 新增 `instock/core/data/providers/<id>.py`，实现 `Provider` 类
2. 在 `registry.yaml` 注册 `providers` 与 `domains.*.chain` 或 `enrich`
3. 在 `normalize.py` 增加列映射
4. 可选 `scripts/verify_<id>.py`
5. 不改 job 主流程（经 `DataRegistry.fetch_domain`）

## 参考

- [mootdx 文档](https://mootdx-backup.github.io/index.html)
- 本地 `a-stock-data/SKILL.md`（腾讯 §1.2 字段口径；PB 为字段 46）
