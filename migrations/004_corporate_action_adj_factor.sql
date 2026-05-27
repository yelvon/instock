-- 通达信 gbbq 除权事件、前复权因子链、qfq 行情表、水位表
-- mysql instockdb < migrations/004_corporate_action_adj_factor.sql

CREATE TABLE IF NOT EXISTS `cn_stock_corporate_action` (
  `code` varchar(6) NOT NULL COMMENT '证券代码',
  `ex_date` date NOT NULL COMMENT '除权除息生效日',
  `event_type` varchar(16) NOT NULL DEFAULT 'xdxr' COMMENT '事件类型',
  `category` int NOT NULL DEFAULT 1 COMMENT '通达信 category',
  `cash_div` double DEFAULT NULL COMMENT '现金分红(每股或每10股，与源一致)',
  `stock_div` double DEFAULT NULL COMMENT '送转股',
  `rights_ratio` double DEFAULT NULL COMMENT '配股比例',
  `rights_price` double DEFAULT NULL COMMENT '配股价',
  `source` varchar(16) NOT NULL DEFAULT 'tdx_gbbq',
  `factor_version` varchar(64) DEFAULT NULL COMMENT 'gbbq 文件版本',
  `ingested_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`code`,`ex_date`,`event_type`,`source`),
  KEY `idx_ex_date` (`ex_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
  COMMENT='股本变迁/除权除息事件';

CREATE TABLE IF NOT EXISTS `cn_stock_adj_factor` (
  `code` varchar(6) NOT NULL,
  `date` date NOT NULL,
  `adjust_kind` varchar(8) NOT NULL DEFAULT 'qfq',
  `qfq_factor` double NOT NULL COMMENT '前复权因子，最新交易日=1',
  `factor_version` varchar(64) DEFAULT NULL,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`code`,`date`,`adjust_kind`),
  KEY `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
  COMMENT='日频前复权因子链';

CREATE TABLE IF NOT EXISTS `cn_stock_qfq_watermark` (
  `code` varchar(6) NOT NULL COMMENT '__global__ 表示全局 gbbq 版本',
  `last_raw_date` date DEFAULT NULL,
  `last_factor_version` varchar(64) DEFAULT NULL,
  `last_derived_at` datetime DEFAULT NULL,
  `meta_json` json DEFAULT NULL,
  PRIMARY KEY (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
  COMMENT='qfq 派生水位';

CREATE TABLE IF NOT EXISTS `cn_stock_daily_bar_qfq` (
  `date` date NOT NULL,
  `code` varchar(6) NOT NULL,
  `open` double DEFAULT NULL,
  `close` double DEFAULT NULL,
  `high` double DEFAULT NULL,
  `low` double DEFAULT NULL,
  `volume` double DEFAULT NULL,
  `amount` double DEFAULT NULL,
  `amplitude` double DEFAULT NULL,
  `quote_change` double DEFAULT NULL,
  `ups_downs` double DEFAULT NULL,
  `turnover` double DEFAULT NULL,
  `quality_status` varchar(16) NOT NULL DEFAULT 'derived',
  `completeness_score` tinyint unsigned NOT NULL DEFAULT 100,
  `primary_source` varchar(32) DEFAULT 'tdx_qfq_derived',
  `source_mask` json DEFAULT NULL,
  `factor_version` varchar(64) DEFAULT NULL,
  `derived_from_batch_id` varchar(64) DEFAULT NULL,
  `last_batch_id` varchar(64) DEFAULT NULL,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`code`,`date`),
  KEY `idx_date` (`date`),
  KEY `idx_factor_version` (`factor_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
  COMMENT='前复权标准日线（由 raw+gbbq 派生）';
