# 数据库表结构说明

本文档由代码 **`instock/core/tablestructure.py`** 自动生成，描述 MySQL 业务表的逻辑结构（列名、SQLAlchemy 类型、中文含义）。

## 维护方式

1. **单一真相**：新增或修改列时，改 `tablestructure.py`（及相关 job / Web 配置）。
2. **更新本文档**：在仓库 `instock` 目录下执行：

```bash
PYTHONPATH=. python3 scripts/gen_database_schema_doc.py
```

3. **初始化脚本中的特例**：`instock/job/init_job.py` 仅手写创建了 `cn_stock_attention`；其余表多在首次写入 DataFrame 时由 SQLAlchemy 按此处类型建表。线上库实际 DDL 若与本文不一致，以数据库为准或做一次迁移对齐。

## 非 MySQL 文件（备忘）

| 说明 | 路径 |
|------|------|
| Web 同步作业历史（JSON） | `instock/log/sync_job_history.json` |

---

## 表一览

| 表名（英文） | 中文说明 | 定义变量 |
|--------------|----------|----------|
| `calculate_indicator` | 股票统计/指标计算助手库 | `STOCK_STATS_DATA` |
| `cn_etf_spot` | 每日ETF数据 | `TABLE_CN_ETF_SPOT` |
| `cn_stock_attention` | 我的关注 | `TABLE_CN_STOCK_ATTENTION` |
| `cn_stock_backtest_data` | 股票回归测试数据 | `TABLE_CN_STOCK_BACKTEST_DATA` |
| `cn_stock_blocktrade` | 股票大宗交易 | `TABLE_CN_STOCK_BLOCKTRADE` |
| `cn_stock_bonus` | 股票分红配送 | `TABLE_CN_STOCK_BONUS` |
| `cn_stock_chip_race_end` | 尾盘抢筹数据 | `TABLE_CN_STOCK_CHIP_RACE_END` |
| `cn_stock_chip_race_open` | 早盘抢筹数据 | `TABLE_CN_STOCK_CHIP_RACE_OPEN` |
| `cn_stock_cpbd` | 操盘必读 | `CN_STOCK_CPBD` |
| `cn_stock_foreign_key` | 股票外键 | `TABLE_CN_STOCK_FOREIGN_KEY` |
| `cn_stock_fund_flow` | 股票资金流向 | `TABLE_CN_STOCK_FUND_FLOW` |
| `cn_stock_fund_flow_concept` | 概念资金流向 | `TABLE_CN_STOCK_FUND_FLOW_CONCEPT` |
| `cn_stock_fund_flow_industry` | 行业资金流向 | `TABLE_CN_STOCK_FUND_FLOW_INDUSTRY` |
| `cn_stock_indicators` | 股票指标数据 | `TABLE_CN_STOCK_INDICATORS` |
| `cn_stock_indicators_buy` | 股票指标买入 | `TABLE_CN_STOCK_INDICATORS_BUY` |
| `cn_stock_indicators_sell` | 股票指标卖出 | `TABLE_CN_STOCK_INDICATORS_SELL` |
| `cn_stock_lhb` | 股票龙虎榜 | `TABLE_CN_STOCK_lHB` |
| `cn_stock_limitup_reason` | 涨停原因揭密 | `TABLE_CN_STOCK_LIMITUP_REASON` |
| `cn_stock_pattern` | 股票K线形态 | `TABLE_CN_STOCK_KLINE_PATTERN` |
| `cn_stock_pattern_recognitions` | K线形态 | `STOCK_KLINE_PATTERN_DATA` |
| `cn_stock_selection` | 综合选股 | `TABLE_CN_STOCK_SELECTION` |
| `cn_stock_spot` | 每日股票数据 | `TABLE_CN_STOCK_SPOT` |
| `cn_stock_spot_buy` | 基本面选股 | `TABLE_CN_STOCK_SPOT_BUY` |
| `cn_stock_strategy_backtrace_ma250` | 回踩年线 | `TABLE_CN_STOCK_STRATEGIES[3]` |
| `cn_stock_strategy_breakthrough_platform` | 突破平台 | `TABLE_CN_STOCK_STRATEGIES[4]` |
| `cn_stock_strategy_climax_limitdown` | 放量跌停 | `TABLE_CN_STOCK_STRATEGIES[8]` |
| `cn_stock_strategy_enter` | 放量上涨 | `TABLE_CN_STOCK_STRATEGIES[0]` |
| `cn_stock_strategy_high_tight_flag` | 高而窄的旗形 | `TABLE_CN_STOCK_STRATEGIES[7]` |
| `cn_stock_strategy_keep_increasing` | 均线多头 | `TABLE_CN_STOCK_STRATEGIES[1]` |
| `cn_stock_strategy_low_atr` | 低ATR成长 | `TABLE_CN_STOCK_STRATEGIES[9]` |
| `cn_stock_strategy_low_backtrace_increase` | 无大幅回撤 | `TABLE_CN_STOCK_STRATEGIES[5]` |
| `cn_stock_strategy_parking_apron` | 停机坪 | `TABLE_CN_STOCK_STRATEGIES[2]` |
| `cn_stock_strategy_turtle_trade` | 海龟交易法则 | `TABLE_CN_STOCK_STRATEGIES[6]` |
| `cn_stock_top` | 股票龙虎榜(新浪) | `TABLE_CN_STOCK_TOP` |
| `fund_etf_hist_em` | 基金某时间段的日行情数据库 | `CN_STOCK_HIST_DATA` |

---

## `calculate_indicator`

- **中文名**：股票统计/指标计算助手库
- **代码引用**：`STOCK_STATS_DATA`

| 列名 | 类型 | 说明 |
|------|------|------|
| `close` | FLOAT | 价格 |
| `macd` | FLOAT | dif |
| `macds` | FLOAT | macd |
| `macdh` | FLOAT | histogram |
| `kdjk` | FLOAT | kdjk |
| `kdjd` | FLOAT | kdjd |
| `kdjj` | FLOAT | kdjj |
| `boll_ub` | FLOAT | boll上轨 |
| `boll` | FLOAT | boll |
| `boll_lb` | FLOAT | boll下轨 |
| `trix` | FLOAT | trix |
| `trix_20_sma` | FLOAT | trma |
| `tema` | FLOAT | tema |
| `cr` | FLOAT | cr |
| `cr-ma1` | FLOAT | cr-ma1 |
| `cr-ma2` | FLOAT | cr-ma2 |
| `cr-ma3` | FLOAT | cr-ma3 |
| `rsi_6` | FLOAT | rsi_6 |
| `rsi_12` | FLOAT | rsi_12 |
| `rsi` | FLOAT | rsi |
| `rsi_24` | FLOAT | rsi_24 |
| `vr` | FLOAT | vr |
| `vr_6_sma` | FLOAT | mavr |
| `roc` | FLOAT | roc |
| `rocma` | FLOAT | rocma |
| `rocema` | FLOAT | rocema |
| `pdi` | FLOAT | pdi |
| `mdi` | FLOAT | mdi |
| `dx` | FLOAT | dx |
| `adx` | FLOAT | adx |
| `adxr` | FLOAT | adxr |
| `wr_6` | FLOAT | wr_6 |
| `wr_10` | FLOAT | wr_10 |
| `wr_14` | FLOAT | wr_14 |
| `cci` | FLOAT | cci |
| `cci_84` | FLOAT | cci_84 |
| `tr` | FLOAT | tr |
| `atr` | FLOAT | atr |
| `dma` | FLOAT | dma |
| `dma_10_sma` | FLOAT | ama |
| `obv` | FLOAT | obv |
| `sar` | FLOAT | sar |
| `psy` | FLOAT | psy |
| `psyma` | FLOAT | psyma |
| `br` | FLOAT | br |
| `ar` | FLOAT | ar |
| `emv` | FLOAT | emv |
| `emva` | FLOAT | emva |
| `bias` | FLOAT | bias |
| `mfi` | FLOAT | mfi |
| `mfisma` | FLOAT | mfisma |
| `vwma` | FLOAT | vwma |
| `mvwma` | FLOAT | mvwma |
| `ppo` | FLOAT | ppo |
| `ppos` | FLOAT | ppos |
| `ppoh` | FLOAT | ppoh |
| `wt1` | FLOAT | wt1 |
| `wt2` | FLOAT | wt2 |
| `supertrend_ub` | FLOAT | supertrend_ub |
| `supertrend` | FLOAT | supertrend |
| `supertrend_lb` | FLOAT | supertrend_lb |
| `dpo` | FLOAT | dpo |
| `madpo` | FLOAT | madpo |
| `vhf` | FLOAT | vhf |
| `rvi` | FLOAT | rvi |
| `rvis` | FLOAT | rvis |
| `fi` | FLOAT | fi |
| `force_2` | FLOAT | force_2 |
| `force_13` | FLOAT | force_13 |
| `ene_ue` | FLOAT | ene上轨 |
| `ene` | FLOAT | ene |
| `ene_le` | FLOAT | ene下轨 |
| `stochrsi_k` | FLOAT | stochrsi_k |
| `stochrsi_d` | FLOAT | stochrsi_d |

## `cn_etf_spot`

- **中文名**：每日ETF数据
- **代码引用**：`TABLE_CN_ETF_SPOT`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `new_price` | FLOAT | 最新价 |
| `change_rate` | FLOAT | 涨跌幅 |
| `ups_downs` | FLOAT | 涨跌额 |
| `volume` | BIGINT | 成交量 |
| `deal_amount` | BIGINT | 成交额 |
| `open_price` | FLOAT | 开盘价 |
| `high_price` | FLOAT | 最高价 |
| `low_price` | FLOAT | 最低价 |
| `pre_close_price` | FLOAT | 昨收 |
| `turnoverrate` | FLOAT | 换手率 |
| `total_market_cap` | BIGINT | 总市值 |
| `free_cap` | BIGINT | 流通市值 |

## `cn_stock_attention`

- **中文名**：我的关注
- **代码引用**：`TABLE_CN_STOCK_ATTENTION`

| 列名 | 类型 | 说明 |
|------|------|------|
| `datetime` | DATETIME | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |

## `cn_stock_backtest_data`

- **中文名**：股票回归测试数据
- **代码引用**：`TABLE_CN_STOCK_BACKTEST_DATA`

| 列名 | 类型 | 说明 |
|------|------|------|
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_blocktrade`

- **中文名**：股票大宗交易
- **代码引用**：`TABLE_CN_STOCK_BLOCKTRADE`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `new_price` | FLOAT | 收盘价 |
| `change_rate` | FLOAT | 涨跌幅 |
| `average_price` | FLOAT | 成交均价 |
| `overflow_rate` | FLOAT | 折溢率 |
| `trade_number` | FLOAT | 成交笔数 |
| `sum_volume` | FLOAT | 成交总量 |
| `sum_turnover` | FLOAT | 成交总额 |
| `turnover_market_rate` | FLOAT | 成交占比流通市值 |

## `cn_stock_bonus`

- **中文名**：股票分红配送
- **代码引用**：`TABLE_CN_STOCK_BONUS`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `convertible_total_rate` | FLOAT | 送转股份-送转总比例 |
| `convertible_rate` | FLOAT | 送转股份-送转比例 |
| `convertible_transfer_rate` | FLOAT | 送转股份-转股比例 |
| `bonusaward_rate` | FLOAT | 现金分红-现金分红比例 |
| `bonusaward_yield` | FLOAT | 现金分红-股息率 |
| `basic_eps` | FLOAT | 每股收益 |
| `bvps` | FLOAT | 每股净资产 |
| `per_capital_reserve` | FLOAT | 每股公积金 |
| `per_unassign_profit` | FLOAT | 每股未分配利润 |
| `netprofit_yoy_ratio` | FLOAT | 净利润同比增长 |
| `total_shares` | BIGINT | 总股本 |
| `plan_date` | DATE | 预案公告日 |
| `record_date` | DATE | 股权登记日 |
| `ex_dividend_date` | DATE | 除权除息日 |
| `progress` | VARCHAR(50) COLLATE "utf8mb4_general_ci" | 方案进度 |
| `report_date` | DATE | 最新公告日期 |

## `cn_stock_chip_race_end`

- **中文名**：尾盘抢筹数据
- **代码引用**：`TABLE_CN_STOCK_CHIP_RACE_END`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `new_price` | FLOAT | 最新价 |
| `change_rate` | FLOAT | 涨跌幅 |
| `pre_close_price` | FLOAT | 昨收 |
| `open_price` | FLOAT | 今开 |
| `deal_amount` | BIGINT | 收盘金额 |
| `bid_rate` | FLOAT | 抢筹幅度 |
| `bid_trust_amount` | BIGINT | 抢筹委托金额 |
| `bid_deal_amount` | BIGINT | 抢筹成交金额 |
| `bid_ratio` | FLOAT | 抢筹占比 |
| `limitup_day` | SmallInteger | 天 |
| `limitup_board` | SmallInteger | 板 |

## `cn_stock_chip_race_open`

- **中文名**：早盘抢筹数据
- **代码引用**：`TABLE_CN_STOCK_CHIP_RACE_OPEN`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `new_price` | FLOAT | 最新价 |
| `change_rate` | FLOAT | 涨跌幅 |
| `pre_close_price` | FLOAT | 昨收 |
| `open_price` | FLOAT | 今开 |
| `deal_amount` | BIGINT | 开盘金额 |
| `bid_rate` | FLOAT | 抢筹幅度 |
| `bid_trust_amount` | BIGINT | 抢筹委托金额 |
| `bid_deal_amount` | BIGINT | 抢筹成交金额 |
| `bid_ratio` | FLOAT | 抢筹占比 |
| `limitup_day` | SmallInteger | 天 |
| `limitup_board` | SmallInteger | 板 |

## `cn_stock_cpbd`

- **中文名**：操盘必读
- **代码引用**：`CN_STOCK_CPBD`

| 列名 | 类型 | 说明 |
|------|------|------|
| `SECURITY_CODE` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `SECURITY_NAME_ABBR` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `PE_DYNAMIC` | FLOAT | 市盈率动 |
| `PE_TTM` | FLOAT | 市盈率TTM |
| `PE_STATIC` | FLOAT | 市盈率静 |
| `PB_MRQ_REALTIME` | FLOAT | 市净率 |
| `REPORT_DATE` | DATE | 财报期 |
| `EPSJB` | FLOAT | 每股收益 |
| `BPS` | FLOAT | 每股净资产 |
| `MGJYXJJE` | FLOAT | 每股经营现金流 |
| `MGZBGJ` | FLOAT | 每股公积金 |
| `MGWFPLR` | FLOAT | 每股未分配利润 |
| `ROEJQ` | FLOAT | 加权净资产收益率 |
| `XSMLL` | FLOAT | 毛利率 |
| `ZCFZL` | FLOAT | 资产负债率 |
| `TOTAL_OPERATEINCOME` | FLOAT | 营业收入 |
| `YYZSRGDHBZC` | FLOAT | 营业收入滚动环比增长 |
| `TOTALOPERATEREVETZ` | FLOAT | 营业收入同比增长 |
| `PARENT_NETPROFIT` | FLOAT | 归属净利润 |
| `NETPROFITRPHBZC` | FLOAT | 归属净利润滚动环比增长 |
| `PARENTNETPROFITTZ` | FLOAT | 归属净利润同比增长 |
| `KCFJCXSYJLR` | FLOAT | 扣非净利润 |
| `KFJLRGDHBZC` | FLOAT | 扣非净利润滚动环比增长 |
| `KCFJCXSYJLRTZ` | FLOAT | 扣非净利润同比增长 |
| `TOTAL_SHARE` | FLOAT | 总股本 |
| `FREE_SHARE` | FLOAT | 流通股本 |
| `BOARD_NAME` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 所属板块 |
| `END_DATE` | DATE | 股东日 |
| `HOLDER_TOTAL_NUM` | FLOAT | 股东人数 |
| `TOTAL_NUM_RATIO` | FLOAT | 较上期变化 |
| `AVG_FREE_SHARES` | FLOAT | 人均流通股 |
| `AVG_FREESHARES_RATIO` | FLOAT | 较上期变化 |
| `HOLD_FOCUS` | FLOAT | 筹码集中度 |
| `AVG_HOLD_AMT` | FLOAT | 人均持股金额 |
| `HOLD_RATIO_TOTAL` | FLOAT | 十大股东持股 |
| `FREEHOLD_RATIO_TOTAL` | FLOAT | 十大流通股东持股 |
| `LHBD_DATE` | DATE | 龙虎榜日 |
| `EXPLANATION` | FLOAT | 龙虎说明 |
| `TOTAL_BUY` | FLOAT | 买入金额 |
| `TOTAL_BUYRIOTOP` | FLOAT | 买入占比 |
| `TOTAL_SELL` | FLOAT | 卖出金额 |
| `TOTAL_SELLRIOTOP` | FLOAT | 卖出占比 |
| `DZJY_DATE` | DATE | 大宗交易日 |
| `DEAL_PRICE` | FLOAT | 成交价 |
| `PREMIUM_RATIO` | FLOAT | 折溢价率 |
| `DEAL_VOLUME` | FLOAT | 成交量 |
| `DEAL_AMT` | FLOAT | 成交额 |
| `BUYER_NAME` | FLOAT | 买营业部 |
| `SELLER_NAME` | FLOAT | 卖营业部 |
| `RZRQ_DATE` | DATE | 融资券日 |
| `FIN_BUY_AMT` | FLOAT | 融资买额 |
| `FIN_REPAY_AMT` | FLOAT | 融资还额 |
| `FIN_BALANCE` | FLOAT | 融资余额 |
| `LOAN_SELL_VOL` | FLOAT | 融券卖量 |
| `LOAN_REPAY_VOL` | FLOAT | 融券还量 |
| `LOAN_BALANCE` | FLOAT | 融券余额 |

## `cn_stock_foreign_key`

- **中文名**：股票外键
- **代码引用**：`TABLE_CN_STOCK_FOREIGN_KEY`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |

## `cn_stock_fund_flow`

- **中文名**：股票资金流向
- **代码引用**：`TABLE_CN_STOCK_FUND_FLOW`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `new_price` | FLOAT | 最新价 |
| `change_rate` | FLOAT | 今日涨跌幅 |
| `fund_amount` | BIGINT | 今日主力净流入-净额 |
| `fund_rate` | FLOAT | 今日主力净流入-净占比 |
| `fund_amount_super` | BIGINT | 今日超大单净流入-净额 |
| `fund_rate_super` | FLOAT | 今日超大单净流入-净占比 |
| `fund_amount_large` | BIGINT | 今日大单净流入-净额 |
| `fund_rate_large` | FLOAT | 今日大单净流入-净占比 |
| `fund_amount_medium` | BIGINT | 今日中单净流入-净额 |
| `fund_rate_medium` | FLOAT | 今日中单净流入-净占比 |
| `fund_amount_small` | BIGINT | 今日小单净流入-净额 |
| `fund_rate_small` | FLOAT | 今日小单净流入-净占比 |
| `change_rate_3` | FLOAT | 3日涨跌幅 |
| `fund_amount_3` | BIGINT | 3日主力净流入-净额 |
| `fund_rate_3` | FLOAT | 3日主力净流入-净占比 |
| `fund_amount_super_3` | BIGINT | 3日超大单净流入-净额 |
| `fund_rate_super_3` | FLOAT | 3日超大单净流入-净占比 |
| `fund_amount_large_3` | BIGINT | 3日大单净流入-净额 |
| `fund_rate_large_3` | FLOAT | 3日大单净流入-净占比 |
| `fund_amount_medium_3` | BIGINT | 3日中单净流入-净额 |
| `fund_rate_medium_3` | FLOAT | 3日中单净流入-净占比 |
| `fund_amount_small_3` | BIGINT | 3日小单净流入-净额 |
| `fund_rate_small_3` | FLOAT | 3日小单净流入-净占比 |
| `change_rate_5` | FLOAT | 5日涨跌幅 |
| `fund_amount_5` | BIGINT | 5日主力净流入-净额 |
| `fund_rate_5` | FLOAT | 5日主力净流入-净占比 |
| `fund_amount_super_5` | BIGINT | 5日超大单净流入-净额 |
| `fund_rate_super_5` | FLOAT | 5日超大单净流入-净占比 |
| `fund_amount_large_5` | BIGINT | 5日大单净流入-净额 |
| `fund_rate_large_5` | FLOAT | 5日大单净流入-净占比 |
| `fund_amount_medium_5` | BIGINT | 5日中单净流入-净额 |
| `fund_rate_medium_5` | FLOAT | 5日中单净流入-净占比 |
| `fund_amount_small_5` | BIGINT | 5日小单净流入-净额 |
| `fund_rate_small_5` | FLOAT | 5日小单净流入-净占比 |
| `change_rate_10` | FLOAT | 10日涨跌幅 |
| `fund_amount_10` | BIGINT | 10日主力净流入-净额 |
| `fund_rate_10` | FLOAT | 10日主力净流入-净占比 |
| `fund_amount_super_10` | BIGINT | 10日超大单净流入-净额 |
| `fund_rate_super_10` | FLOAT | 10日超大单净流入-净占比 |
| `fund_amount_large_10` | BIGINT | 10日大单净流入-净额 |
| `fund_rate_large_10` | FLOAT | 10日大单净流入-净占比 |
| `fund_amount_medium_10` | BIGINT | 10日中单净流入-净额 |
| `fund_rate_medium_10` | FLOAT | 10日中单净流入-净占比 |
| `fund_amount_small_10` | BIGINT | 10日小单净流入-净额 |
| `fund_rate_small_10` | FLOAT | 10日小单净流入-净占比 |

## `cn_stock_fund_flow_concept`

- **中文名**：概念资金流向
- **代码引用**：`TABLE_CN_STOCK_FUND_FLOW_CONCEPT`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `change_rate` | FLOAT | 今日涨跌幅 |
| `fund_amount` | BIGINT | 今日主力净流入-净额 |
| `fund_rate` | FLOAT | 今日主力净流入-净占比 |
| `fund_amount_super` | BIGINT | 今日超大单净流入-净额 |
| `fund_rate_super` | FLOAT | 今日超大单净流入-净占比 |
| `fund_amount_large` | BIGINT | 今日大单净流入-净额 |
| `fund_rate_large` | FLOAT | 今日大单净流入-净占比 |
| `fund_amount_medium` | BIGINT | 今日中单净流入-净额 |
| `fund_rate_medium` | FLOAT | 今日中单净流入-净占比 |
| `fund_amount_small` | BIGINT | 今日小单净流入-净额 |
| `fund_rate_small` | FLOAT | 今日小单净流入-净占比 |
| `stock_name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 今日主力净流入最大股 |
| `change_rate_5` | FLOAT | 5日涨跌幅 |
| `fund_amount_5` | BIGINT | 5日主力净流入-净额 |
| `fund_rate_5` | FLOAT | 5日主力净流入-净占比 |
| `fund_amount_super_5` | BIGINT | 5日超大单净流入-净额 |
| `fund_rate_super_5` | FLOAT | 5日超大单净流入-净占比 |
| `fund_amount_large_5` | BIGINT | 5日大单净流入-净额 |
| `fund_rate_large_5` | FLOAT | 5日大单净流入-净占比 |
| `fund_amount_medium_5` | BIGINT | 5日中单净流入-净额 |
| `fund_rate_medium_5` | FLOAT | 5日中单净流入-净占比 |
| `fund_amount_small_5` | BIGINT | 5日小单净流入-净额 |
| `fund_rate_small_5` | FLOAT | 5日小单净流入-净占比 |
| `stock_name_5` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 5日主力净流入最大股 |
| `change_rate_10` | FLOAT | 10日涨跌幅 |
| `fund_amount_10` | BIGINT | 10日主力净流入-净额 |
| `fund_rate_10` | FLOAT | 10日主力净流入-净占比 |
| `fund_amount_super_10` | BIGINT | 10日超大单净流入-净额 |
| `fund_rate_super_10` | FLOAT | 10日超大单净流入-净占比 |
| `fund_amount_large_10` | BIGINT | 10日大单净流入-净额 |
| `fund_rate_large_10` | FLOAT | 10日大单净流入-净占比 |
| `fund_amount_medium_10` | BIGINT | 10日中单净流入-净额 |
| `fund_rate_medium_10` | FLOAT | 10日中单净流入-净占比 |
| `fund_amount_small_10` | BIGINT | 10日小单净流入-净额 |
| `fund_rate_small_10` | FLOAT | 10日小单净流入-净占比 |
| `stock_name_10` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 10日主力净流入最大股 |

## `cn_stock_fund_flow_industry`

- **中文名**：行业资金流向
- **代码引用**：`TABLE_CN_STOCK_FUND_FLOW_INDUSTRY`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `change_rate` | FLOAT | 今日涨跌幅 |
| `fund_amount` | BIGINT | 今日主力净流入-净额 |
| `fund_rate` | FLOAT | 今日主力净流入-净占比 |
| `fund_amount_super` | BIGINT | 今日超大单净流入-净额 |
| `fund_rate_super` | FLOAT | 今日超大单净流入-净占比 |
| `fund_amount_large` | BIGINT | 今日大单净流入-净额 |
| `fund_rate_large` | FLOAT | 今日大单净流入-净占比 |
| `fund_amount_medium` | BIGINT | 今日中单净流入-净额 |
| `fund_rate_medium` | FLOAT | 今日中单净流入-净占比 |
| `fund_amount_small` | BIGINT | 今日小单净流入-净额 |
| `fund_rate_small` | FLOAT | 今日小单净流入-净占比 |
| `stock_name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 今日主力净流入最大股 |
| `change_rate_5` | FLOAT | 5日涨跌幅 |
| `fund_amount_5` | BIGINT | 5日主力净流入-净额 |
| `fund_rate_5` | FLOAT | 5日主力净流入-净占比 |
| `fund_amount_super_5` | BIGINT | 5日超大单净流入-净额 |
| `fund_rate_super_5` | FLOAT | 5日超大单净流入-净占比 |
| `fund_amount_large_5` | BIGINT | 5日大单净流入-净额 |
| `fund_rate_large_5` | FLOAT | 5日大单净流入-净占比 |
| `fund_amount_medium_5` | BIGINT | 5日中单净流入-净额 |
| `fund_rate_medium_5` | FLOAT | 5日中单净流入-净占比 |
| `fund_amount_small_5` | BIGINT | 5日小单净流入-净额 |
| `fund_rate_small_5` | FLOAT | 5日小单净流入-净占比 |
| `stock_name_5` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 5日主力净流入最大股 |
| `change_rate_10` | FLOAT | 10日涨跌幅 |
| `fund_amount_10` | BIGINT | 10日主力净流入-净额 |
| `fund_rate_10` | FLOAT | 10日主力净流入-净占比 |
| `fund_amount_super_10` | BIGINT | 10日超大单净流入-净额 |
| `fund_rate_super_10` | FLOAT | 10日超大单净流入-净占比 |
| `fund_amount_large_10` | BIGINT | 10日大单净流入-净额 |
| `fund_rate_large_10` | FLOAT | 10日大单净流入-净占比 |
| `fund_amount_medium_10` | BIGINT | 10日中单净流入-净额 |
| `fund_rate_medium_10` | FLOAT | 10日中单净流入-净占比 |
| `fund_amount_small_10` | BIGINT | 10日小单净流入-净额 |
| `fund_rate_small_10` | FLOAT | 10日小单净流入-净占比 |
| `stock_name_10` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 10日主力净流入最大股 |

## `cn_stock_indicators`

- **中文名**：股票指标数据
- **代码引用**：`TABLE_CN_STOCK_INDICATORS`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `close` | FLOAT | 价格 |
| `macd` | FLOAT | dif |
| `macds` | FLOAT | macd |
| `macdh` | FLOAT | histogram |
| `kdjk` | FLOAT | kdjk |
| `kdjd` | FLOAT | kdjd |
| `kdjj` | FLOAT | kdjj |
| `boll_ub` | FLOAT | boll上轨 |
| `boll` | FLOAT | boll |
| `boll_lb` | FLOAT | boll下轨 |
| `trix` | FLOAT | trix |
| `trix_20_sma` | FLOAT | trma |
| `tema` | FLOAT | tema |
| `cr` | FLOAT | cr |
| `cr-ma1` | FLOAT | cr-ma1 |
| `cr-ma2` | FLOAT | cr-ma2 |
| `cr-ma3` | FLOAT | cr-ma3 |
| `rsi_6` | FLOAT | rsi_6 |
| `rsi_12` | FLOAT | rsi_12 |
| `rsi` | FLOAT | rsi |
| `rsi_24` | FLOAT | rsi_24 |
| `vr` | FLOAT | vr |
| `vr_6_sma` | FLOAT | mavr |
| `roc` | FLOAT | roc |
| `rocma` | FLOAT | rocma |
| `rocema` | FLOAT | rocema |
| `pdi` | FLOAT | pdi |
| `mdi` | FLOAT | mdi |
| `dx` | FLOAT | dx |
| `adx` | FLOAT | adx |
| `adxr` | FLOAT | adxr |
| `wr_6` | FLOAT | wr_6 |
| `wr_10` | FLOAT | wr_10 |
| `wr_14` | FLOAT | wr_14 |
| `cci` | FLOAT | cci |
| `cci_84` | FLOAT | cci_84 |
| `tr` | FLOAT | tr |
| `atr` | FLOAT | atr |
| `dma` | FLOAT | dma |
| `dma_10_sma` | FLOAT | ama |
| `obv` | FLOAT | obv |
| `sar` | FLOAT | sar |
| `psy` | FLOAT | psy |
| `psyma` | FLOAT | psyma |
| `br` | FLOAT | br |
| `ar` | FLOAT | ar |
| `emv` | FLOAT | emv |
| `emva` | FLOAT | emva |
| `bias` | FLOAT | bias |
| `mfi` | FLOAT | mfi |
| `mfisma` | FLOAT | mfisma |
| `vwma` | FLOAT | vwma |
| `mvwma` | FLOAT | mvwma |
| `ppo` | FLOAT | ppo |
| `ppos` | FLOAT | ppos |
| `ppoh` | FLOAT | ppoh |
| `wt1` | FLOAT | wt1 |
| `wt2` | FLOAT | wt2 |
| `supertrend_ub` | FLOAT | supertrend_ub |
| `supertrend` | FLOAT | supertrend |
| `supertrend_lb` | FLOAT | supertrend_lb |
| `dpo` | FLOAT | dpo |
| `madpo` | FLOAT | madpo |
| `vhf` | FLOAT | vhf |
| `rvi` | FLOAT | rvi |
| `rvis` | FLOAT | rvis |
| `fi` | FLOAT | fi |
| `force_2` | FLOAT | force_2 |
| `force_13` | FLOAT | force_13 |
| `ene_ue` | FLOAT | ene上轨 |
| `ene` | FLOAT | ene |
| `ene_le` | FLOAT | ene下轨 |
| `stochrsi_k` | FLOAT | stochrsi_k |
| `stochrsi_d` | FLOAT | stochrsi_d |

## `cn_stock_indicators_buy`

- **中文名**：股票指标买入
- **代码引用**：`TABLE_CN_STOCK_INDICATORS_BUY`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_indicators_sell`

- **中文名**：股票指标卖出
- **代码引用**：`TABLE_CN_STOCK_INDICATORS_SELL`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_lhb`

- **中文名**：股票龙虎榜
- **代码引用**：`TABLE_CN_STOCK_lHB`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `ranking_times` | DATE | 上榜日 |
| `interpret` | VARCHAR(255) COLLATE "utf8mb4_general_ci" | 解读 |
| `new_price` | FLOAT | 收盘价 |
| `change_rate` | FLOAT | 涨跌幅 |
| `net_amount_buy` | FLOAT | 龙虎榜净买额 |
| `sum_buy` | FLOAT | 龙虎榜买入额 |
| `sum_sell` | FLOAT | 龙虎榜卖出额 |
| `lhb_amount` | FLOAT | 龙虎榜成交额 |
| `market_amount` | FLOAT | 市场总成交额 |
| `net_amount_rate` | FLOAT | 净买额占总成交比 |
| `sum_rate` | FLOAT | 成交额占总成交比 |
| `turnoverrate` | FLOAT | 换手率 |
| `free_cap` | BIGINT | 流通市值 |
| `reason` | VARCHAR(2000) COLLATE "utf8mb4_general_ci" | 上榜原因 |
| `ranking_after_1` | FLOAT | 上榜后1日 |
| `ranking_after_2` | FLOAT | 上榜后2日 |
| `ranking_after_5` | FLOAT | 上榜后5日 |
| `ranking_after_10` | FLOAT | 上榜后10日 |

## `cn_stock_limitup_reason`

- **中文名**：涨停原因揭密
- **代码引用**：`TABLE_CN_STOCK_LIMITUP_REASON`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `title` | VARCHAR(255) COLLATE "utf8mb4_general_ci" | 原因 |
| `reason` | VARCHAR(2000) COLLATE "utf8mb4_general_ci" | 详因 |
| `new_price` | FLOAT | 最新价 |
| `change_rate` | FLOAT | 涨跌幅 |
| `ups_downs` | FLOAT | 涨跌额 |
| `turnoverrate` | FLOAT | 换手率 |
| `volume` | BIGINT | 成交量 |
| `deal_amount` | BIGINT | 成交额 |
| `dde` | BIGINT | DDE |

## `cn_stock_pattern`

- **中文名**：股票K线形态
- **代码引用**：`TABLE_CN_STOCK_KLINE_PATTERN`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `tow_crows` | SmallInteger | 两只乌鸦 |
| `upside_gap_two_crows` | SmallInteger | 向上跳空的两只乌鸦 |
| `three_black_crows` | SmallInteger | 三只乌鸦 |
| `identical_three_crows` | SmallInteger | 三胞胎乌鸦 |
| `three_line_strike` | SmallInteger | 三线打击 |
| `dark_cloud_cover` | SmallInteger | 乌云压顶 |
| `evening_doji_star` | SmallInteger | 十字暮星 |
| `doji_Star` | SmallInteger | 十字星 |
| `hanging_man` | SmallInteger | 上吊线 |
| `hikkake_pattern` | SmallInteger | 陷阱 |
| `modified_hikkake_pattern` | SmallInteger | 修正陷阱 |
| `in_neck_pattern` | SmallInteger | 颈内线 |
| `on_neck_pattern` | SmallInteger | 颈上线 |
| `thrusting_pattern` | SmallInteger | 插入 |
| `shooting_star` | SmallInteger | 射击之星 |
| `stalled_pattern` | SmallInteger | 停顿形态 |
| `advance_block` | SmallInteger | 大敌当前 |
| `high_wave_candle` | SmallInteger | 风高浪大线 |
| `engulfing_pattern` | SmallInteger | 吞噬模式 |
| `abandoned_baby` | SmallInteger | 弃婴 |
| `closing_marubozu` | SmallInteger | 收盘缺影线 |
| `doji` | SmallInteger | 十字 |
| `up_down_gap` | SmallInteger | 向上/下跳空并列阳线 |
| `long_legged_doji` | SmallInteger | 长脚十字 |
| `rickshaw_man` | SmallInteger | 黄包车夫 |
| `marubozu` | SmallInteger | 光头光脚/缺影线 |
| `three_inside_up_down` | SmallInteger | 三内部上涨和下跌 |
| `three_outside_up_down` | SmallInteger | 三外部上涨和下跌 |
| `three_stars_in_the_south` | SmallInteger | 南方三星 |
| `three_white_soldiers` | SmallInteger | 三个白兵 |
| `belt_hold` | SmallInteger | 捉腰带线 |
| `breakaway` | SmallInteger | 脱离 |
| `concealing_baby_swallow` | SmallInteger | 藏婴吞没 |
| `counterattack` | SmallInteger | 反击线 |
| `dragonfly_doji` | SmallInteger | 蜻蜓十字/T形十字 |
| `evening_star` | SmallInteger | 暮星 |
| `gravestone_doji` | SmallInteger | 墓碑十字/倒T十字 |
| `hammer` | SmallInteger | 锤头 |
| `harami_pattern` | SmallInteger | 母子线 |
| `harami_cross_pattern` | SmallInteger | 十字孕线 |
| `homing_pigeon` | SmallInteger | 家鸽 |
| `inverted_hammer` | SmallInteger | 倒锤头 |
| `kicking` | SmallInteger | 反冲形态 |
| `kicking_bull_bear` | SmallInteger | 由较长缺影线决定的反冲形态 |
| `ladder_bottom` | SmallInteger | 梯底 |
| `long_line_candle` | SmallInteger | 长蜡烛 |
| `matching_low` | SmallInteger | 相同低价 |
| `mat_hold` | SmallInteger | 铺垫 |
| `morning_doji_star` | SmallInteger | 十字晨星 |
| `morning_star` | SmallInteger | 晨星 |
| `piercing_pattern` | SmallInteger | 刺透形态 |
| `rising_falling_three` | SmallInteger | 上升/下降三法 |
| `separating_lines` | SmallInteger | 分离线 |
| `short_line_candle` | SmallInteger | 短蜡烛 |
| `spinning_top` | SmallInteger | 纺锤 |
| `stick_sandwich` | SmallInteger | 条形三明治 |
| `takuri` | SmallInteger | 探水竿 |
| `tasuki_gap` | SmallInteger | 跳空并列阴阳线 |
| `tristar_pattern` | SmallInteger | 三星 |
| `unique_3_river` | SmallInteger | 奇特三河床 |
| `upside_downside_gap` | SmallInteger | 上升/下降跳空三法 |

## `cn_stock_pattern_recognitions`

- **中文名**：K线形态
- **代码引用**：`STOCK_KLINE_PATTERN_DATA`

| 列名 | 类型 | 说明 |
|------|------|------|
| `tow_crows` | SmallInteger | 两只乌鸦 |
| `upside_gap_two_crows` | SmallInteger | 向上跳空的两只乌鸦 |
| `three_black_crows` | SmallInteger | 三只乌鸦 |
| `identical_three_crows` | SmallInteger | 三胞胎乌鸦 |
| `three_line_strike` | SmallInteger | 三线打击 |
| `dark_cloud_cover` | SmallInteger | 乌云压顶 |
| `evening_doji_star` | SmallInteger | 十字暮星 |
| `doji_Star` | SmallInteger | 十字星 |
| `hanging_man` | SmallInteger | 上吊线 |
| `hikkake_pattern` | SmallInteger | 陷阱 |
| `modified_hikkake_pattern` | SmallInteger | 修正陷阱 |
| `in_neck_pattern` | SmallInteger | 颈内线 |
| `on_neck_pattern` | SmallInteger | 颈上线 |
| `thrusting_pattern` | SmallInteger | 插入 |
| `shooting_star` | SmallInteger | 射击之星 |
| `stalled_pattern` | SmallInteger | 停顿形态 |
| `advance_block` | SmallInteger | 大敌当前 |
| `high_wave_candle` | SmallInteger | 风高浪大线 |
| `engulfing_pattern` | SmallInteger | 吞噬模式 |
| `abandoned_baby` | SmallInteger | 弃婴 |
| `closing_marubozu` | SmallInteger | 收盘缺影线 |
| `doji` | SmallInteger | 十字 |
| `up_down_gap` | SmallInteger | 向上/下跳空并列阳线 |
| `long_legged_doji` | SmallInteger | 长脚十字 |
| `rickshaw_man` | SmallInteger | 黄包车夫 |
| `marubozu` | SmallInteger | 光头光脚/缺影线 |
| `three_inside_up_down` | SmallInteger | 三内部上涨和下跌 |
| `three_outside_up_down` | SmallInteger | 三外部上涨和下跌 |
| `three_stars_in_the_south` | SmallInteger | 南方三星 |
| `three_white_soldiers` | SmallInteger | 三个白兵 |
| `belt_hold` | SmallInteger | 捉腰带线 |
| `breakaway` | SmallInteger | 脱离 |
| `concealing_baby_swallow` | SmallInteger | 藏婴吞没 |
| `counterattack` | SmallInteger | 反击线 |
| `dragonfly_doji` | SmallInteger | 蜻蜓十字/T形十字 |
| `evening_star` | SmallInteger | 暮星 |
| `gravestone_doji` | SmallInteger | 墓碑十字/倒T十字 |
| `hammer` | SmallInteger | 锤头 |
| `harami_pattern` | SmallInteger | 母子线 |
| `harami_cross_pattern` | SmallInteger | 十字孕线 |
| `homing_pigeon` | SmallInteger | 家鸽 |
| `inverted_hammer` | SmallInteger | 倒锤头 |
| `kicking` | SmallInteger | 反冲形态 |
| `kicking_bull_bear` | SmallInteger | 由较长缺影线决定的反冲形态 |
| `ladder_bottom` | SmallInteger | 梯底 |
| `long_line_candle` | SmallInteger | 长蜡烛 |
| `matching_low` | SmallInteger | 相同低价 |
| `mat_hold` | SmallInteger | 铺垫 |
| `morning_doji_star` | SmallInteger | 十字晨星 |
| `morning_star` | SmallInteger | 晨星 |
| `piercing_pattern` | SmallInteger | 刺透形态 |
| `rising_falling_three` | SmallInteger | 上升/下降三法 |
| `separating_lines` | SmallInteger | 分离线 |
| `short_line_candle` | SmallInteger | 短蜡烛 |
| `spinning_top` | SmallInteger | 纺锤 |
| `stick_sandwich` | SmallInteger | 条形三明治 |
| `takuri` | SmallInteger | 探水竿 |
| `tasuki_gap` | SmallInteger | 跳空并列阴阳线 |
| `tristar_pattern` | SmallInteger | 三星 |
| `unique_3_river` | SmallInteger | 奇特三河床 |
| `upside_downside_gap` | SmallInteger | 上升/下降跳空三法 |

## `cn_stock_selection`

- **中文名**：综合选股
- **代码引用**：`TABLE_CN_STOCK_SELECTION`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `new_price` | FLOAT | 最新价 |
| `change_rate` | FLOAT | 涨跌幅 |
| `volume_ratio` | FLOAT | 量比 |
| `high_price` | FLOAT | 最高价 |
| `low_price` | FLOAT | 最低价 |
| `pre_close_price` | FLOAT | 昨收价 |
| `volume` | BIGINT | 成交量 |
| `deal_amount` | BIGINT | 成交额 |
| `turnoverrate` | FLOAT | 换手率 |
| `listing_date` | DATE | 上市时间 |
| `industry` | VARCHAR(50) COLLATE "utf8mb4_general_ci" | 行业 |
| `area` | VARCHAR(50) COLLATE "utf8mb4_general_ci" | 地区 |
| `concept` | VARCHAR(800) COLLATE "utf8mb4_general_ci" | 概念 |
| `style` | VARCHAR(255) COLLATE "utf8mb4_general_ci" | 板块 |
| `is_hs300` | VARCHAR(2) COLLATE "utf8mb4_general_ci" | 沪300 |
| `is_sz50` | VARCHAR(2) COLLATE "utf8mb4_general_ci" | 上证50 |
| `is_zz500` | VARCHAR(2) COLLATE "utf8mb4_general_ci" | 中证500 |
| `is_zz1000` | VARCHAR(2) COLLATE "utf8mb4_general_ci" | 中证1000 |
| `is_cy50` | VARCHAR(2) COLLATE "utf8mb4_general_ci" | 创业板50 |
| `pe9` | FLOAT | 市盈率TTM |
| `pbnewmrq` | FLOAT | 市净率MRQ |
| `pettmdeducted` | FLOAT | 市盈率TTM扣非 |
| `ps9` | FLOAT | 市销率TTM |
| `pcfjyxjl9` | FLOAT | 市现率TTM |
| `predict_pe_syear` | FLOAT | 预测市盈率今年 |
| `predict_pe_nyear` | FLOAT | 预测市盈率明年 |
| `total_market_cap` | BIGINT | 总市值 |
| `free_cap` | BIGINT | 流通市值 |
| `dtsyl` | FLOAT | 动态市盈率 |
| `ycpeg` | FLOAT | 预测PEG |
| `enterprise_value_multiple` | FLOAT | 企业价值倍数 |
| `basic_eps` | FLOAT | 每股收益 |
| `bvps` | FLOAT | 每股净资产 |
| `per_netcash_operate` | FLOAT | 每股经营现金流 |
| `per_fcfe` | FLOAT | 每股自由现金流 |
| `per_capital_reserve` | FLOAT | 每股资本公积 |
| `per_unassign_profit` | FLOAT | 每股未分配利润 |
| `per_surplus_reserve` | FLOAT | 每股盈余公积 |
| `per_retained_earning` | FLOAT | 每股留存收益 |
| `parent_netprofit` | BIGINT | 归属净利润 |
| `deduct_netprofit` | BIGINT | 扣非净利润 |
| `total_operate_income` | BIGINT | 营业总收入 |
| `roe_weight` | FLOAT | 净资产收益率ROE |
| `jroa` | FLOAT | 总资产净利率ROA |
| `roic` | FLOAT | 投入资本回报率ROIC |
| `zxgxl` | FLOAT | 最新股息率 |
| `sale_gpr` | FLOAT | 毛利率 |
| `sale_npr` | FLOAT | 净利率 |
| `netprofit_yoy_ratio` | FLOAT | 净利润增长率 |
| `deduct_netprofit_growthrate` | FLOAT | 扣非净利润增长率 |
| `toi_yoy_ratio` | FLOAT | 营收增长率 |
| `netprofit_growthrate_3y` | FLOAT | 净利润3年复合增长率 |
| `income_growthrate_3y` | FLOAT | 营收3年复合增长率 |
| `predict_netprofit_ratio` | FLOAT | 预测净利润同比增长 |
| `predict_income_ratio` | FLOAT | 预测营收同比增长 |
| `basiceps_yoy_ratio` | FLOAT | 每股收益同比增长率 |
| `total_profit_growthrate` | FLOAT | 利润总额同比增长率 |
| `operate_profit_growthrate` | FLOAT | 营业利润同比增长率 |
| `debt_asset_ratio` | FLOAT | 资产负债率 |
| `equity_ratio` | FLOAT | 产权比率 |
| `equity_multiplier` | FLOAT | 权益乘数 |
| `current_ratio` | FLOAT | 流动比率 |
| `speed_ratio` | FLOAT | 速动比率 |
| `total_shares` | BIGINT | 总股本 |
| `free_shares` | BIGINT | 流通股本 |
| `holder_newest` | BIGINT | 最新股东户数 |
| `holder_ratio` | FLOAT | 股东户数增长率 |
| `hold_amount` | FLOAT | 户均持股金额 |
| `avg_hold_num` | FLOAT | 户均持股数量 |
| `holdnum_growthrate_3q` | FLOAT | 户均持股数季度增长率 |
| `holdnum_growthrate_hy` | FLOAT | 户均持股数半年增长率 |
| `hold_ratio_count` | FLOAT | 十大股东持股比例合计 |
| `free_hold_ratio` | FLOAT | 十大流通股东比例合计 |
| `macd_golden_fork` | mysql.types.BIT | MACD金叉日线 |
| `macd_golden_forkz` | mysql.types.BIT | MACD金叉周线 |
| `macd_golden_forky` | mysql.types.BIT | MACD金叉月线 |
| `kdj_golden_fork` | mysql.types.BIT | KDJ金叉日线 |
| `kdj_golden_forkz` | mysql.types.BIT | KDJ金叉周线 |
| `kdj_golden_forky` | mysql.types.BIT | KDJ金叉月线 |
| `break_through` | mysql.types.BIT | 放量突破 |
| `low_funds_inflow` | mysql.types.BIT | 低位资金净流入 |
| `high_funds_outflow` | mysql.types.BIT | 高位资金净流出 |
| `breakup_ma_5days` | mysql.types.BIT | 向上突破均线5日 |
| `breakup_ma_10days` | mysql.types.BIT | 向上突破均线10日 |
| `breakup_ma_20days` | mysql.types.BIT | 向上突破均线20日 |
| `breakup_ma_30days` | mysql.types.BIT | 向上突破均线30日 |
| `breakup_ma_60days` | mysql.types.BIT | 向上突破均线60日 |
| `long_avg_array` | mysql.types.BIT | 均线多头排列 |
| `short_avg_array` | mysql.types.BIT | 均线空头排列 |
| `upper_large_volume` | mysql.types.BIT | 连涨放量 |
| `down_narrow_volume` | mysql.types.BIT | 下跌无量 |
| `one_dayang_line` | mysql.types.BIT | 一根大阳线 |
| `two_dayang_lines` | mysql.types.BIT | 两根大阳线 |
| `rise_sun` | mysql.types.BIT | 旭日东升 |
| `power_fulgun` | mysql.types.BIT | 强势多方炮 |
| `restore_justice` | mysql.types.BIT | 拨云见日 |
| `down_7days` | mysql.types.BIT | 七仙女下凡(七连阴) |
| `upper_8days` | mysql.types.BIT | 八仙过海(八连阳) |
| `upper_9days` | mysql.types.BIT | 九阳神功(九连阳) |
| `upper_4days` | mysql.types.BIT | 四串阳 |
| `heaven_rule` | mysql.types.BIT | 天量法则 |
| `upside_volume` | mysql.types.BIT | 放量上攻 |
| `bearish_engulfing` | mysql.types.BIT | 穿头破脚 |
| `reversing_hammer` | mysql.types.BIT | 倒转锤头 |
| `shooting_star` | mysql.types.BIT | 射击之星 |
| `evening_star` | mysql.types.BIT | 黄昏之星 |
| `first_dawn` | mysql.types.BIT | 曙光初现 |
| `pregnant` | mysql.types.BIT | 身怀六甲 |
| `black_cloud_tops` | mysql.types.BIT | 乌云盖顶 |
| `morning_star` | mysql.types.BIT | 早晨之星 |
| `narrow_finish` | mysql.types.BIT | 窄幅整理 |
| `limited_lift_f6m` | mysql.types.BIT | 限售解禁未来半年 |
| `limited_lift_f1y` | mysql.types.BIT | 限售解禁未来1年 |
| `limited_lift_6m` | mysql.types.BIT | 限售解禁近半年 |
| `limited_lift_1y` | mysql.types.BIT | 限售解禁近1年 |
| `directional_seo_1m` | mysql.types.BIT | 定向增发近1个月 |
| `directional_seo_3m` | mysql.types.BIT | 定向增发近3个月 |
| `directional_seo_6m` | mysql.types.BIT | 定向增发近6个月 |
| `directional_seo_1y` | mysql.types.BIT | 定向增发近1年 |
| `recapitalize_1m` | mysql.types.BIT | 资产重组近1个月 |
| `recapitalize_3m` | mysql.types.BIT | 资产重组近3个月 |
| `recapitalize_6m` | mysql.types.BIT | 资产重组近6个月 |
| `recapitalize_1y` | mysql.types.BIT | 资产重组近1年 |
| `equity_pledge_1m` | mysql.types.BIT | 股权质押近1个月 |
| `equity_pledge_3m` | mysql.types.BIT | 股权质押近3个月 |
| `equity_pledge_6m` | mysql.types.BIT | 股权质押近6个月 |
| `equity_pledge_1y` | mysql.types.BIT | 股权质押近1年 |
| `pledge_ratio` | FLOAT | 质押比例 |
| `goodwill_scale` | BIGINT | 商誉规模 |
| `goodwill_assets_ratro` | FLOAT | 商誉占净资产比例 |
| `predict_type` | VARCHAR(10) COLLATE "utf8mb4_general_ci" | 业绩预告 |
| `par_dividend_pretax` | FLOAT | 每股股利税前 |
| `par_dividend` | FLOAT | 每股红股 |
| `par_it_equity` | FLOAT | 每股转增股本 |
| `holder_change_3m` | FLOAT | 近3月股东增减比例 |
| `executive_change_3m` | FLOAT | 近3月高管增减比例 |
| `org_survey_3m` | SmallInteger | 近3月机构调研 |
| `org_rating` | VARCHAR(10) COLLATE "utf8mb4_general_ci" | 机构评级 |
| `allcorp_num` | SmallInteger | 机构持股家数合计 |
| `allcorp_fund_num` | SmallInteger | 基金持股家数 |
| `allcorp_qs_num` | SmallInteger | 券商持股家数 |
| `allcorp_qfii_num` | SmallInteger | QFII持股家数 |
| `allcorp_bx_num` | SmallInteger | 保险公司持股家数 |
| `allcorp_sb_num` | SmallInteger | 社保持股家数 |
| `allcorp_xt_num` | SmallInteger | 信托公司持股家数 |
| `allcorp_ratio` | FLOAT | 机构持股比例合计 |
| `allcorp_fund_ratio` | FLOAT | 基金持股比例 |
| `allcorp_qs_ratio` | FLOAT | 券商持股比例 |
| `allcorp_qfii_ratio` | FLOAT | QFII持股比例 |
| `allcorp_bx_ratio` | FLOAT | 保险公司持股比例 |
| `allcorp_sb_ratio` | FLOAT | 社保持股比例 |
| `allcorp_xt_ratio` | FLOAT | 信托公司持股比例 |
| `popularity_rank` | SmallInteger | 股吧人气排名 |
| `rank_change` | SmallInteger | 人气排名变化 |
| `upp_days` | SmallInteger | 人气排名连涨 |
| `down_days` | SmallInteger | 人气排名连跌 |
| `new_high` | SmallInteger | 人气排名创新高 |
| `new_down` | SmallInteger | 人气排名创新低 |
| `newfans_ratio` | FLOAT | 新晋粉丝占比 |
| `bigfans_ratio` | FLOAT | 铁杆粉丝占比 |
| `concern_rank_7days` | SmallInteger | 7日关注排名 |
| `browse_rank` | SmallInteger | 今日浏览排名 |
| `amplitude` | FLOAT | 振幅 |
| `is_issue_break` | mysql.types.BIT | 破发股票 |
| `is_bps_break` | mysql.types.BIT | 破净股票 |
| `now_newhigh` | mysql.types.BIT | 今日创历史新高 |
| `now_newlow` | mysql.types.BIT | 今日创历史新低 |
| `high_recent_3days` | mysql.types.BIT | 近期创历史新高近3日 |
| `high_recent_5days` | mysql.types.BIT | 近期创历史新高近5日 |
| `high_recent_10days` | mysql.types.BIT | 近期创历史新高近10日 |
| `high_recent_20days` | mysql.types.BIT | 近期创历史新高近20日 |
| `high_recent_30days` | mysql.types.BIT | 近期创历史新高近30日 |
| `low_recent_3days` | mysql.types.BIT | 近期创历史新低近3日 |
| `low_recent_5days` | mysql.types.BIT | 近期创历史新低近5日 |
| `low_recent_10days` | mysql.types.BIT | 近期创历史新低近10日 |
| `low_recent_20days` | mysql.types.BIT | 近期创历史新低近20日 |
| `low_recent_30days` | mysql.types.BIT | 近期创历史新低近30日 |
| `win_market_3days` | mysql.types.BIT | 近期跑赢大盘近3日 |
| `win_market_5days` | mysql.types.BIT | 近期跑赢大盘近5日 |
| `win_market_10days` | mysql.types.BIT | 近期跑赢大盘近10日 |
| `win_market_20days` | mysql.types.BIT | 近期跑赢大盘近20日 |
| `win_market_30days` | mysql.types.BIT | 近期跑赢大盘近30日 |
| `net_inflow` | FLOAT | 当日净流入额 |
| `netinflow_3days` | BIGINT | 3日主力净流入 |
| `netinflow_5days` | BIGINT | 5日主力净流入 |
| `nowinterst_ratio` | BIGINT | 当日增仓占比 |
| `nowinterst_ratio_3d` | FLOAT | 3日增仓占比 |
| `nowinterst_ratio_5d` | FLOAT | 5日增仓占比 |
| `ddx` | FLOAT | 当日DDX |
| `ddx_3d` | FLOAT | 3日DDX |
| `ddx_5d` | FLOAT | 5日DDX |
| `ddx_red_10d` | SmallInteger | 10日内DDX飘红天数 |
| `changerate_3days` | FLOAT | 3日涨跌幅 |
| `changerate_5days` | FLOAT | 5日涨跌幅 |
| `changerate_10days` | FLOAT | 10日涨跌幅 |
| `changerate_ty` | FLOAT | 今年以来涨跌幅 |
| `upnday` | SmallInteger | 连涨天数 |
| `downnday` | SmallInteger | 连跌天数 |
| `listing_yield_year` | FLOAT | 上市以来年化收益率 |
| `listing_volatility_year` | FLOAT | 上市以来年化波动率 |
| `mutual_netbuy_amt` | BIGINT | 沪深股通净买入金额 |
| `hold_ratio` | FLOAT | 沪深股通持股比例 |
| `secucode` | VARCHAR(10) COLLATE "utf8mb4_general_ci" | 全代码 |

## `cn_stock_spot`

- **中文名**：每日股票数据
- **代码引用**：`TABLE_CN_STOCK_SPOT`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `new_price` | FLOAT | 最新价 |
| `change_rate` | FLOAT | 涨跌幅 |
| `ups_downs` | FLOAT | 涨跌额 |
| `volume` | BIGINT | 成交量 |
| `deal_amount` | BIGINT | 成交额 |
| `amplitude` | FLOAT | 振幅 |
| `turnoverrate` | FLOAT | 换手率 |
| `volume_ratio` | FLOAT | 量比 |
| `open_price` | FLOAT | 今开 |
| `high_price` | FLOAT | 最高 |
| `low_price` | FLOAT | 最低 |
| `pre_close_price` | FLOAT | 昨收 |
| `speed_increase` | FLOAT | 涨速 |
| `speed_increase_5` | FLOAT | 5分钟涨跌 |
| `speed_increase_60` | FLOAT | 60日涨跌幅 |
| `speed_increase_all` | FLOAT | 年初至今涨跌幅 |
| `dtsyl` | FLOAT | 市盈率动 |
| `pe9` | FLOAT | 市盈率TTM |
| `pe` | FLOAT | 市盈率静 |
| `pbnewmrq` | FLOAT | 市净率 |
| `basic_eps` | FLOAT | 每股收益 |
| `bvps` | FLOAT | 每股净资产 |
| `per_capital_reserve` | FLOAT | 每股公积金 |
| `per_unassign_profit` | FLOAT | 每股未分配利润 |
| `roe_weight` | FLOAT | 加权净资产收益率 |
| `sale_gpr` | FLOAT | 毛利率 |
| `debt_asset_ratio` | FLOAT | 资产负债率 |
| `total_operate_income` | BIGINT | 营业收入 |
| `toi_yoy_ratio` | FLOAT | 营业收入同比增长 |
| `parent_netprofit` | BIGINT | 归属净利润 |
| `netprofit_yoy_ratio` | FLOAT | 归属净利润同比增长 |
| `report_date` | DATE | 报告期 |
| `total_shares` | BIGINT | 总股本 |
| `free_shares` | BIGINT | 已流通股份 |
| `total_market_cap` | BIGINT | 总市值 |
| `free_cap` | BIGINT | 流通市值 |
| `industry` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 所处行业 |
| `listing_date` | DATE | 上市时间 |

## `cn_stock_spot_buy`

- **中文名**：基本面选股
- **代码引用**：`TABLE_CN_STOCK_SPOT_BUY`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `new_price` | FLOAT | 最新价 |
| `change_rate` | FLOAT | 涨跌幅 |
| `ups_downs` | FLOAT | 涨跌额 |
| `volume` | BIGINT | 成交量 |
| `deal_amount` | BIGINT | 成交额 |
| `amplitude` | FLOAT | 振幅 |
| `turnoverrate` | FLOAT | 换手率 |
| `volume_ratio` | FLOAT | 量比 |
| `open_price` | FLOAT | 今开 |
| `high_price` | FLOAT | 最高 |
| `low_price` | FLOAT | 最低 |
| `pre_close_price` | FLOAT | 昨收 |
| `speed_increase` | FLOAT | 涨速 |
| `speed_increase_5` | FLOAT | 5分钟涨跌 |
| `speed_increase_60` | FLOAT | 60日涨跌幅 |
| `speed_increase_all` | FLOAT | 年初至今涨跌幅 |
| `dtsyl` | FLOAT | 市盈率动 |
| `pe9` | FLOAT | 市盈率TTM |
| `pe` | FLOAT | 市盈率静 |
| `pbnewmrq` | FLOAT | 市净率 |
| `basic_eps` | FLOAT | 每股收益 |
| `bvps` | FLOAT | 每股净资产 |
| `per_capital_reserve` | FLOAT | 每股公积金 |
| `per_unassign_profit` | FLOAT | 每股未分配利润 |
| `roe_weight` | FLOAT | 加权净资产收益率 |
| `sale_gpr` | FLOAT | 毛利率 |
| `debt_asset_ratio` | FLOAT | 资产负债率 |
| `total_operate_income` | BIGINT | 营业收入 |
| `toi_yoy_ratio` | FLOAT | 营业收入同比增长 |
| `parent_netprofit` | BIGINT | 归属净利润 |
| `netprofit_yoy_ratio` | FLOAT | 归属净利润同比增长 |
| `report_date` | DATE | 报告期 |
| `total_shares` | BIGINT | 总股本 |
| `free_shares` | BIGINT | 已流通股份 |
| `total_market_cap` | BIGINT | 总市值 |
| `free_cap` | BIGINT | 流通市值 |
| `industry` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 所处行业 |
| `listing_date` | DATE | 上市时间 |

## `cn_stock_strategy_backtrace_ma250`

- **中文名**：回踩年线
- **代码引用**：`TABLE_CN_STOCK_STRATEGIES[3]`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_strategy_breakthrough_platform`

- **中文名**：突破平台
- **代码引用**：`TABLE_CN_STOCK_STRATEGIES[4]`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_strategy_climax_limitdown`

- **中文名**：放量跌停
- **代码引用**：`TABLE_CN_STOCK_STRATEGIES[8]`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_strategy_enter`

- **中文名**：放量上涨
- **代码引用**：`TABLE_CN_STOCK_STRATEGIES[0]`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_strategy_high_tight_flag`

- **中文名**：高而窄的旗形
- **代码引用**：`TABLE_CN_STOCK_STRATEGIES[7]`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_strategy_keep_increasing`

- **中文名**：均线多头
- **代码引用**：`TABLE_CN_STOCK_STRATEGIES[1]`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_strategy_low_atr`

- **中文名**：低ATR成长
- **代码引用**：`TABLE_CN_STOCK_STRATEGIES[9]`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_strategy_low_backtrace_increase`

- **中文名**：无大幅回撤
- **代码引用**：`TABLE_CN_STOCK_STRATEGIES[5]`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_strategy_parking_apron`

- **中文名**：停机坪
- **代码引用**：`TABLE_CN_STOCK_STRATEGIES[2]`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_strategy_turtle_trade`

- **中文名**：海龟交易法则
- **代码引用**：`TABLE_CN_STOCK_STRATEGIES[6]`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `rate_1` | FLOAT | 1日收益率 |
| `rate_2` | FLOAT | 2日收益率 |
| `rate_3` | FLOAT | 3日收益率 |
| `rate_4` | FLOAT | 4日收益率 |
| `rate_5` | FLOAT | 5日收益率 |
| `rate_6` | FLOAT | 6日收益率 |
| `rate_7` | FLOAT | 7日收益率 |
| `rate_8` | FLOAT | 8日收益率 |
| `rate_9` | FLOAT | 9日收益率 |
| `rate_10` | FLOAT | 10日收益率 |
| `rate_11` | FLOAT | 11日收益率 |
| `rate_12` | FLOAT | 12日收益率 |
| `rate_13` | FLOAT | 13日收益率 |
| `rate_14` | FLOAT | 14日收益率 |
| `rate_15` | FLOAT | 15日收益率 |
| `rate_16` | FLOAT | 16日收益率 |
| `rate_17` | FLOAT | 17日收益率 |
| `rate_18` | FLOAT | 18日收益率 |
| `rate_19` | FLOAT | 19日收益率 |
| `rate_20` | FLOAT | 20日收益率 |
| `rate_21` | FLOAT | 21日收益率 |
| `rate_22` | FLOAT | 22日收益率 |
| `rate_23` | FLOAT | 23日收益率 |
| `rate_24` | FLOAT | 24日收益率 |
| `rate_25` | FLOAT | 25日收益率 |
| `rate_26` | FLOAT | 26日收益率 |
| `rate_27` | FLOAT | 27日收益率 |
| `rate_28` | FLOAT | 28日收益率 |
| `rate_29` | FLOAT | 29日收益率 |
| `rate_30` | FLOAT | 30日收益率 |
| `rate_31` | FLOAT | 31日收益率 |
| `rate_32` | FLOAT | 32日收益率 |
| `rate_33` | FLOAT | 33日收益率 |
| `rate_34` | FLOAT | 34日收益率 |
| `rate_35` | FLOAT | 35日收益率 |
| `rate_36` | FLOAT | 36日收益率 |
| `rate_37` | FLOAT | 37日收益率 |
| `rate_38` | FLOAT | 38日收益率 |
| `rate_39` | FLOAT | 39日收益率 |
| `rate_40` | FLOAT | 40日收益率 |
| `rate_41` | FLOAT | 41日收益率 |
| `rate_42` | FLOAT | 42日收益率 |
| `rate_43` | FLOAT | 43日收益率 |
| `rate_44` | FLOAT | 44日收益率 |
| `rate_45` | FLOAT | 45日收益率 |
| `rate_46` | FLOAT | 46日收益率 |
| `rate_47` | FLOAT | 47日收益率 |
| `rate_48` | FLOAT | 48日收益率 |
| `rate_49` | FLOAT | 49日收益率 |
| `rate_50` | FLOAT | 50日收益率 |
| `rate_51` | FLOAT | 51日收益率 |
| `rate_52` | FLOAT | 52日收益率 |
| `rate_53` | FLOAT | 53日收益率 |
| `rate_54` | FLOAT | 54日收益率 |
| `rate_55` | FLOAT | 55日收益率 |
| `rate_56` | FLOAT | 56日收益率 |
| `rate_57` | FLOAT | 57日收益率 |
| `rate_58` | FLOAT | 58日收益率 |
| `rate_59` | FLOAT | 59日收益率 |
| `rate_60` | FLOAT | 60日收益率 |
| `rate_61` | FLOAT | 61日收益率 |
| `rate_62` | FLOAT | 62日收益率 |
| `rate_63` | FLOAT | 63日收益率 |
| `rate_64` | FLOAT | 64日收益率 |
| `rate_65` | FLOAT | 65日收益率 |
| `rate_66` | FLOAT | 66日收益率 |
| `rate_67` | FLOAT | 67日收益率 |
| `rate_68` | FLOAT | 68日收益率 |
| `rate_69` | FLOAT | 69日收益率 |
| `rate_70` | FLOAT | 70日收益率 |
| `rate_71` | FLOAT | 71日收益率 |
| `rate_72` | FLOAT | 72日收益率 |
| `rate_73` | FLOAT | 73日收益率 |
| `rate_74` | FLOAT | 74日收益率 |
| `rate_75` | FLOAT | 75日收益率 |
| `rate_76` | FLOAT | 76日收益率 |
| `rate_77` | FLOAT | 77日收益率 |
| `rate_78` | FLOAT | 78日收益率 |
| `rate_79` | FLOAT | 79日收益率 |
| `rate_80` | FLOAT | 80日收益率 |
| `rate_81` | FLOAT | 81日收益率 |
| `rate_82` | FLOAT | 82日收益率 |
| `rate_83` | FLOAT | 83日收益率 |
| `rate_84` | FLOAT | 84日收益率 |
| `rate_85` | FLOAT | 85日收益率 |
| `rate_86` | FLOAT | 86日收益率 |
| `rate_87` | FLOAT | 87日收益率 |
| `rate_88` | FLOAT | 88日收益率 |
| `rate_89` | FLOAT | 89日收益率 |
| `rate_90` | FLOAT | 90日收益率 |
| `rate_91` | FLOAT | 91日收益率 |
| `rate_92` | FLOAT | 92日收益率 |
| `rate_93` | FLOAT | 93日收益率 |
| `rate_94` | FLOAT | 94日收益率 |
| `rate_95` | FLOAT | 95日收益率 |
| `rate_96` | FLOAT | 96日收益率 |
| `rate_97` | FLOAT | 97日收益率 |
| `rate_98` | FLOAT | 98日收益率 |
| `rate_99` | FLOAT | 99日收益率 |
| `rate_100` | FLOAT | 100日收益率 |

## `cn_stock_top`

- **中文名**：股票龙虎榜(新浪)
- **代码引用**：`TABLE_CN_STOCK_TOP`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `code` | VARCHAR(6) COLLATE "utf8mb4_general_ci" | 代码 |
| `name` | VARCHAR(20) COLLATE "utf8mb4_general_ci" | 名称 |
| `ranking_times` | FLOAT | 上榜次数 |
| `sum_buy` | FLOAT | 累积购买额 |
| `sum_sell` | FLOAT | 累积卖出额 |
| `net_amount` | FLOAT | 净额 |
| `buy_seat` | FLOAT | 买入席位数 |
| `sell_seat` | FLOAT | 卖出席位数 |

## `fund_etf_hist_em`

- **中文名**：基金某时间段的日行情数据库
- **代码引用**：`CN_STOCK_HIST_DATA`

| 列名 | 类型 | 说明 |
|------|------|------|
| `date` | DATE | 日期 |
| `open` | FLOAT | 开盘 |
| `close` | FLOAT | 收盘 |
| `high` | FLOAT | 最高 |
| `low` | FLOAT | 最低 |
| `volume` | FLOAT | 成交量 |
| `amount` | FLOAT | 成交额 |
| `amplitude` | FLOAT | 振幅 |
| `quote_change` | FLOAT | 涨跌幅 |
| `ups_downs` | FLOAT | 涨跌额 |
| `turnover` | FLOAT | 换手率 |
