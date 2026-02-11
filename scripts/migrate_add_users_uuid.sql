-- ============================================================
-- 迁移: 为 users 表添加 uuid 列（与 src/models/user.py 一致）
-- 解决: Unknown column 'users.uuid' in 'field list'
-- 执行: mysql -u user -p database < scripts/migrate_add_users_uuid.sql
-- 若 uuid 列已存在，请注释掉第一条 ALTER，只保留 UPDATE 和第二条 ALTER（如有需要）。
-- ============================================================

SET NAMES utf8mb4;

ALTER TABLE `users` ADD COLUMN `uuid` VARCHAR(36) NULL UNIQUE COMMENT '用户UUID' AFTER `id`;

UPDATE `users` SET `uuid` = UUID() WHERE `uuid` IS NULL;

ALTER TABLE `users` MODIFY COLUMN `uuid` VARCHAR(36) NOT NULL COMMENT '用户UUID';
