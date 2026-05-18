-- mootdx 全市场 A 股证券主表（供遍历拉 K 线）
CREATE TABLE IF NOT EXISTS `cn_stock_universe` (
  `code` varchar(6) NOT NULL COMMENT '证券代码',
  `name` varchar(32) DEFAULT NULL COMMENT '名称',
  `market` varchar(8) DEFAULT NULL COMMENT '市场 SH/SZ',
  `source_provider` varchar(32) DEFAULT NULL COMMENT '列表来源 mootdx_online/mootdx_local',
  `updated_at` datetime DEFAULT NULL COMMENT '最近同步时间',
  PRIMARY KEY (`code`),
  KEY `idx_market` (`market`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
  COMMENT='A股证券主表(mootdx在线或本地TDX扫描)';
