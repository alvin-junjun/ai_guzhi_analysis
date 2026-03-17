-- 为已有 analysis_history 表增加 source_type、source_ref 字段（若不存在）
-- 执行方式：根据数据库类型选择其一执行

-- MySQL / MariaDB:
-- ALTER TABLE analysis_history ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'direct' COMMENT '分析来源: direct/url_crawl/prompt_crawl';
-- ALTER TABLE analysis_history ADD COLUMN IF NOT EXISTS source_ref TEXT DEFAULT NULL COMMENT '来源引用';

-- 若 MySQL 版本不支持 ADD COLUMN IF NOT EXISTS，可先检查再执行：
-- SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'analysis_history' AND COLUMN_NAME = 'source_type';
-- 若为 0，再执行：
-- ALTER TABLE analysis_history ADD COLUMN source_type VARCHAR(20) NOT NULL DEFAULT 'direct' COMMENT '分析来源';
-- ALTER TABLE analysis_history ADD COLUMN source_ref TEXT DEFAULT NULL COMMENT '来源引用';

-- SQLite（在项目根目录执行）:
-- sqlite3 data/stock_analysis.db "ALTER TABLE analysis_history ADD COLUMN source_type VARCHAR(20) DEFAULT 'direct';"
-- sqlite3 data/stock_analysis.db "ALTER TABLE analysis_history ADD COLUMN source_ref TEXT;"
