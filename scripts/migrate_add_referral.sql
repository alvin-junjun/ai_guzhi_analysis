-- ============================================================
-- 邀请分享功能 - 数据库迁移脚本
-- 适用于: MySQL 5.7+ / MariaDB 10.3+
-- 执行前请备份数据库
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 1. 用户表新增字段：邀请人、分享码、邀请奖励余额
-- ============================================================
ALTER TABLE `users`
    ADD COLUMN `referrer_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '邀请人用户ID' AFTER `updated_at`,
    ADD COLUMN `referral_bonus_balance` INT NOT NULL DEFAULT 0 COMMENT '邀请奖励的免费使用次数余额' AFTER `referrer_id`,
    ADD COLUMN `share_code` VARCHAR(32) DEFAULT NULL COMMENT '分享码，用于生成邀请链接' AFTER `referral_bonus_balance`,
    ADD INDEX `ix_referrer_id` (`referrer_id`),
    ADD UNIQUE KEY `uix_share_code` (`share_code`),
    ADD CONSTRAINT `fk_users_referrer` FOREIGN KEY (`referrer_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

-- 为已有用户生成唯一 share_code（R + 6位id + 8位时间戳哈希，保证唯一）
UPDATE `users` u SET u.`share_code` = CONCAT('R', LPAD(u.id, 6, '0'), SUBSTRING(MD5(CONCAT(u.id, u.created_at)), 1, 8))
WHERE u.`share_code` IS NULL;

-- 将 share_code 改为 NOT NULL（已有行已填充）
ALTER TABLE `users` MODIFY COLUMN `share_code` VARCHAR(32) NOT NULL COMMENT '分享码，用于生成邀请链接';

-- ============================================================
-- 2. 邀请记录表：记录谁邀请了谁、是否已发注册/充值奖励
-- ============================================================
CREATE TABLE IF NOT EXISTS `referral_records` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `referrer_id` BIGINT UNSIGNED NOT NULL COMMENT '邀请人用户ID',
    `referred_user_id` BIGINT UNSIGNED NOT NULL COMMENT '被邀请人用户ID',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `registration_reward_given` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已发放注册奖励 0-否 1-是',
    `subscription_reward_given` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已发放充值奖励 0-否 1-是',
    `subscription_plan_type` VARCHAR(20) DEFAULT NULL COMMENT '充值套餐类型(发放充值奖励时记录): weekly/monthly/quarterly',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uix_referrer_referred` (`referrer_id`, `referred_user_id`),
    INDEX `ix_referrer_id` (`referrer_id`),
    INDEX `ix_referred_user_id` (`referred_user_id`),
    CONSTRAINT `fk_referral_referrer` FOREIGN KEY (`referrer_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_referral_referred` FOREIGN KEY (`referred_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邀请记录表';

-- ============================================================
-- 3. 系统配置：邀请奖励次数（可后续在管理端调整）
-- ============================================================
INSERT INTO `system_configs` (`config_key`, `config_value`, `description`) VALUES
('referral_registration_reward', '10', '每邀请1人注册成功，邀请人获得的免费使用次数'),
('referral_reward_weekly', '30', '被邀请人购买周卡并支付成功后，邀请人获得的免费使用次数'),
('referral_reward_monthly', '100', '被邀请人购买月卡并支付成功后，邀请人获得的免费使用次数'),
('referral_reward_quarterly', '300', '被邀请人购买季卡并支付成功后，邀请人获得的免费使用次数')
ON DUPLICATE KEY UPDATE `description` = VALUES(`description`);

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 完成
-- ============================================================
SELECT '邀请分享功能迁移完成' AS message;
