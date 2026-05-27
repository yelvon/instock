-- 修复 cn_stock_qfq_watermark.code 长度：全局水位使用 __global__（9 字符）
-- mysql instockdb < migrations/005_qfq_watermark_code_width.sql

ALTER TABLE `cn_stock_qfq_watermark`
  MODIFY COLUMN `code` varchar(16) NOT NULL
  COMMENT '__global__ 表示全局 gbbq 版本，其余为 6 位证券代码';
