-- 回测数据血缘：入库批次元数据
CREATE TABLE IF NOT EXISTS `data_batch` (
  `batch_id` varchar(64) NOT NULL COMMENT '批次唯一ID(UUID)',
  `domain_id` varchar(64) NOT NULL COMMENT '数据域ID，如 daily_spot_snapshot、daily_bar_raw、derived_indicators',
  `trade_date` date DEFAULT NULL COMMENT '业务交易日(日快照/衍生表)；K线域可为空',
  `date_from` date DEFAULT NULL COMMENT 'K线区间起始日(含)',
  `date_to` date DEFAULT NULL COMMENT 'K线区间结束日(含)',
  `scope_type` varchar(32) DEFAULT NULL COMMENT '范围类型：market/code/table 等',
  `scope_key` varchar(128) DEFAULT NULL COMMENT '范围标识，如 cn_stock_spot、股票代码',
  `row_count` int DEFAULT NULL COMMENT '本批次写入行数',
  `source_provider` varchar(32) NOT NULL COMMENT '主链数据源 provider_id，如 eastmoney、mootdx_local',
  `enrich_providers` json DEFAULT NULL COMMENT 'enrich 源列表 JSON，如 ["tencent"]',
  `mixed_source` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否混源：0否 1是(含 enrich 或 chain 多源)',
  `adjust_type` varchar(16) DEFAULT NULL COMMENT '复权口径：raw/qfq/hfq；K线 raw 域通常为 raw',
  `profile` varchar(16) NOT NULL DEFAULT 'live' COMMENT '数据配置档：live/backtest',
  `input_batches` json DEFAULT NULL COMMENT '上游依赖 batch_id 列表(衍生 job)',
  `status` varchar(16) NOT NULL DEFAULT 'success' COMMENT '批次状态：success/failed/partial',
  `job_id` varchar(128) DEFAULT NULL COMMENT '触发写入的作业ID，如 basic_data_daily_job',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  PRIMARY KEY (`batch_id`),
  KEY `idx_domain_date` (`domain_id`, `trade_date`),
  KEY `idx_provider` (`source_provider`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
  COMMENT='回测数据入库批次血缘(域/源/区间/依赖)';
