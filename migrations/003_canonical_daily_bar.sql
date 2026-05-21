-- 标准日线行情表（回测唯一读取入口）与来源贡献表
-- 执行：mysql instockdb < migrations/003_canonical_daily_bar.sql

CREATE TABLE IF NOT EXISTS `cn_stock_daily_bar` (
  `date` date NOT NULL COMMENT '交易日',
  `code` varchar(6) NOT NULL COMMENT '证券代码',
  `adjust_type` varchar(16) NOT NULL DEFAULT 'raw' COMMENT '复权口径 raw/qfq/hfq',
  `open` double DEFAULT NULL COMMENT '开盘价',
  `close` double DEFAULT NULL COMMENT '收盘价',
  `high` double DEFAULT NULL COMMENT '最高价',
  `low` double DEFAULT NULL COMMENT '最低价',
  `volume` double DEFAULT NULL COMMENT '成交量(股)',
  `amount` double DEFAULT NULL COMMENT '成交额(元)',
  `amplitude` double DEFAULT NULL COMMENT '振幅',
  `quote_change` double DEFAULT NULL COMMENT '涨跌幅',
  `ups_downs` double DEFAULT NULL COMMENT '涨跌额',
  `turnover` double DEFAULT NULL COMMENT '换手率',
  `quality_status` varchar(16) NOT NULL DEFAULT 'partial' COMMENT 'complete/partial/suspect',
  `completeness_score` tinyint unsigned NOT NULL DEFAULT 0 COMMENT '完整度 0-100',
  `primary_source` varchar(32) DEFAULT NULL COMMENT '主来源 provider_id',
  `source_mask` json DEFAULT NULL COMMENT '参与补数的源列表 JSON',
  `last_batch_id` varchar(64) DEFAULT NULL COMMENT '最近写入批次',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`code`,`date`,`adjust_type`),
  KEY `idx_date` (`date`),
  KEY `idx_quality` (`quality_status`),
  KEY `idx_primary_source` (`primary_source`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
  COMMENT='标准 A 股日线行情（多源幂等合并）';

CREATE TABLE IF NOT EXISTS `market_data_contribution` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `date` date NOT NULL COMMENT '交易日',
  `code` varchar(6) NOT NULL COMMENT '证券代码',
  `adjust_type` varchar(16) NOT NULL DEFAULT 'raw' COMMENT '复权口径',
  `source_provider` varchar(32) NOT NULL COMMENT '贡献源 provider_id',
  `batch_id` varchar(64) DEFAULT NULL COMMENT 'data_batch.batch_id',
  `fields_filled` json DEFAULT NULL COMMENT '本次写入/补全的字段列表',
  `row_hash` varchar(64) DEFAULT NULL COMMENT '来源行指纹',
  `quality_score` tinyint unsigned NOT NULL DEFAULT 0 COMMENT '来源质量分',
  `merge_action` varchar(16) NOT NULL COMMENT 'insert/fill/skip/conflict/suspect',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '贡献时间',
  PRIMARY KEY (`id`),
  KEY `idx_code_date` (`code`,`date`,`adjust_type`),
  KEY `idx_source` (`source_provider`),
  KEY `idx_batch` (`batch_id`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
  COMMENT='标准行情表来源贡献记录';
