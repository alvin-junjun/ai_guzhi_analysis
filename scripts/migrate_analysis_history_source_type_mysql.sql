-- 为 analysis_history 表添加 source_type、source_ref 列（MySQL）
-- 若表中已有这两列，执行时会报 Duplicate column，可忽略（表示已迁移过）。
-- 在项目根目录执行：mysql -u 用户名 -p 数据库名 < scripts/migrate_analysis_history_source_type_mysql.sql

ALTER TABLE analysis_history
  ADD COLUMN source_type VARCHAR(20) NOT NULL DEFAULT 'direct' COMMENT '分析来源: direct/url_crawl/prompt_crawl';

ALTER TABLE analysis_history
  ADD COLUMN source_ref TEXT DEFAULT NULL COMMENT '来源引用，如文章URL或自定义提示词';
