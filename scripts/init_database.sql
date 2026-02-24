-- ============================================================
-- A股智能分析系统 - 数据库初始化脚本
-- 适用于: MySQL 5.7+ / MariaDB 10.3+
-- 创建日期: 2026-02-04
-- ============================================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 1. 股票日线数据表 (原有表，保持兼容)
-- ============================================================
DROP TABLE IF EXISTS `stock_daily`;
CREATE TABLE `stock_daily` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `date` DATE NOT NULL COMMENT '交易日期',
    `open` DECIMAL(12,4) DEFAULT NULL COMMENT '开盘价',
    `high` DECIMAL(12,4) DEFAULT NULL COMMENT '最高价',
    `low` DECIMAL(12,4) DEFAULT NULL COMMENT '最低价',
    `close` DECIMAL(12,4) DEFAULT NULL COMMENT '收盘价',
    `volume` DECIMAL(20,2) DEFAULT NULL COMMENT '成交量(股)',
    `amount` DECIMAL(20,2) DEFAULT NULL COMMENT '成交额(元)',
    `pct_chg` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `ma5` DECIMAL(12,4) DEFAULT NULL COMMENT '5日均线',
    `ma10` DECIMAL(12,4) DEFAULT NULL COMMENT '10日均线',
    `ma20` DECIMAL(12,4) DEFAULT NULL COMMENT '20日均线',
    `volume_ratio` DECIMAL(10,4) DEFAULT NULL COMMENT '量比',
    `data_source` VARCHAR(50) DEFAULT NULL COMMENT '数据来源',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uix_code_date` (`code`, `date`),
    INDEX `ix_code` (`code`),
    INDEX `ix_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股票日线数据';

-- ============================================================
-- 2. 用户表
-- ============================================================
DROP TABLE IF EXISTS `users`;
-- `ry-vue`.users definition
CREATE TABLE `users` (
                         `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '用户ID',
                         `uuid` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '用户UUID',
                         `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '手机号',
                         `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '邮箱(QQ邮箱)',
                         `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '密码哈希(可选,用于密码登录)',
                         `nickname` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '昵称',
                         `avatar` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '头像URL',
                         `is_admin` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否管理员 0-否 1-是',
                         `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '状态: active/disabled/deleted',
                         `membership_level` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'free' COMMENT '会员等级',
                         `membership_expire` datetime DEFAULT NULL COMMENT '会员过期时间',
                         `total_analysis_count` int unsigned NOT NULL DEFAULT '0' COMMENT '累计分析次数',
                         `email_verified` tinyint(1) NOT NULL DEFAULT '0' COMMENT '邮箱是否验证 0-否 1-是',
                         `phone_verified` tinyint(1) NOT NULL DEFAULT '0' COMMENT '手机是否验证 0-否 1-是',
                         `email_notify_enabled` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用邮件推送 0-否 1-是',
                         `register_ip` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '注册IP',
                         `last_login_ip` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '最后登录IP',
                         `last_login_at` datetime DEFAULT NULL COMMENT '最后登录时间',
                         `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
                         `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                         `referrer_id` bigint unsigned DEFAULT NULL COMMENT '邀请人用户ID',
                         `referral_bonus_balance` int NOT NULL DEFAULT 0 COMMENT '邀请奖励的免费使用次数余额',
                         `share_code` varchar(32) DEFAULT NULL COMMENT '分享码，用于生成邀请链接',
                         PRIMARY KEY (`id`),
                         UNIQUE KEY `uix_uuid` (`uuid`),
                         UNIQUE KEY `uix_phone` (`phone`),
                         UNIQUE KEY `uix_email` (`email`),
                         KEY `ix_status` (`status`),
                         KEY `ix_created_at` (`created_at`),
                         KEY `ix_referrer_id` (`referrer_id`),
                         UNIQUE KEY `uix_share_code` (`share_code`),
                         CONSTRAINT `fk_users_referrer` FOREIGN KEY (`referrer_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
-- ============================================================
-- 3. 验证码表 (短信/邮件验证码)
-- ============================================================
DROP TABLE IF EXISTS `verification_codes`;
CREATE TABLE `verification_codes` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `target` VARCHAR(100) NOT NULL COMMENT '目标(手机号或邮箱)',
    `code` VARCHAR(10) NOT NULL COMMENT '验证码',
    `type` VARCHAR(20) NOT NULL DEFAULT 'email' COMMENT '类型: sms/email',
    `purpose` VARCHAR(20) NOT NULL DEFAULT 'login' COMMENT '用途: login/register/reset',
    `expires_at` DATETIME NOT NULL COMMENT '过期时间',
    `used` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已使用 0-否 1-是',
    `used_at` DATETIME DEFAULT NULL COMMENT '使用时间',
    `ip_address` VARCHAR(50) DEFAULT NULL COMMENT '请求IP',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `ix_target` (`target`),
    INDEX `ix_target_code` (`target`, `code`),
    INDEX `ix_expires_at` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='验证码表';

-- ============================================================
-- 4. 用户会话表 (Session)
-- ============================================================
DROP TABLE IF EXISTS `user_sessions`;
CREATE TABLE `user_sessions` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    `session_token` VARCHAR(128) NOT NULL COMMENT 'Session Token',
    `device_type` ENUM('web', 'mobile', 'api') DEFAULT 'web' COMMENT '设备类型',
    `device_info` VARCHAR(255) DEFAULT NULL COMMENT '设备信息',
    `ip_address` VARCHAR(50) DEFAULT NULL COMMENT 'IP地址',
    `user_agent` TEXT DEFAULT NULL COMMENT '用户代理',
    `expire_at` DATETIME NOT NULL COMMENT '过期时间',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否有效',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `last_active_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '最后活跃时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uix_session_token` (`session_token`),
    INDEX `ix_user_id` (`user_id`),
    INDEX `ix_expire_at` (`expire_at`),
    CONSTRAINT `fk_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表';

-- ============================================================
-- 4.1 邀请记录表
-- ============================================================
DROP TABLE IF EXISTS `referral_records`;
CREATE TABLE `referral_records` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `referrer_id` BIGINT UNSIGNED NOT NULL COMMENT '邀请人用户ID',
    `referred_user_id` BIGINT UNSIGNED NOT NULL COMMENT '被邀请人用户ID',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `registration_reward_given` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已发放注册奖励 0-否 1-是',
    `subscription_reward_given` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已发放充值奖励 0-否 1-是',
    `subscription_plan_type` VARCHAR(20) DEFAULT NULL COMMENT '充值套餐类型: weekly/monthly/quarterly',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uix_referrer_referred` (`referrer_id`, `referred_user_id`),
    INDEX `ix_referrer_id` (`referrer_id`),
    INDEX `ix_referred_user_id` (`referred_user_id`),
    CONSTRAINT `fk_referral_referrer` FOREIGN KEY (`referrer_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_referral_referred` FOREIGN KEY (`referred_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邀请记录表';

-- ============================================================
-- 5. 会员套餐表
-- ============================================================
DROP TABLE IF EXISTS `membership_plans`;
CREATE TABLE `membership_plans` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '套餐ID',
    `name` VARCHAR(50) NOT NULL COMMENT '套餐名称',
    `description` VARCHAR(500) DEFAULT NULL COMMENT '套餐描述',
    `price` DECIMAL(10,2) NOT NULL COMMENT '价格(元)',
    `original_price` DECIMAL(10,2) DEFAULT NULL COMMENT '原价(用于展示划线价)',
    `duration_days` INT NOT NULL COMMENT '有效天数',
    `daily_analysis_limit` INT NOT NULL DEFAULT -1 COMMENT '每日分析次数限制(-1表示不限)',
    `watchlist_limit` INT NOT NULL DEFAULT 100 COMMENT '自选股数量限制',
    `features` JSON DEFAULT NULL COMMENT '功能列表JSON',
    `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序(越小越靠前)',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否上架 0-否 1-是',
    `is_recommended` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否推荐 0-否 1-是',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `ix_is_active` (`is_active`),
    INDEX `ix_sort_order` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会员套餐表';

-- ============================================================
-- 6. 订单表
-- ============================================================
DROP TABLE IF EXISTS `orders`;
CREATE TABLE `orders` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单ID',
    `order_no` VARCHAR(50) NOT NULL COMMENT '订单号',
    `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    `plan_id` BIGINT UNSIGNED NOT NULL COMMENT '套餐ID',
    `plan_name` VARCHAR(50) NOT NULL COMMENT '套餐名称(冗余)',
    `amount` DECIMAL(10,2) NOT NULL COMMENT '订单金额(元)',
    `pay_amount` DECIMAL(10,2) NOT NULL COMMENT '实付金额(元)',
    `discount_amount` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '优惠金额(元)',
    `payment_method` VARCHAR(20) NOT NULL DEFAULT 'wechat' COMMENT '支付方式: wechat/alipay',
    `payment_status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '支付状态: pending/paid/failed/refunded/closed',
    `transaction_id` VARCHAR(100) DEFAULT NULL COMMENT '第三方交易号',
    `prepay_id` VARCHAR(100) DEFAULT NULL COMMENT '预支付ID(微信)',
    `qrcode_url` VARCHAR(500) DEFAULT NULL COMMENT '支付二维码URL',
    `paid_at` DATETIME DEFAULT NULL COMMENT '支付时间',
    `expire_at` DATETIME DEFAULT NULL COMMENT '订单过期时间(未支付)',
    `refund_at` DATETIME DEFAULT NULL COMMENT '退款时间',
    `refund_reason` VARCHAR(500) DEFAULT NULL COMMENT '退款原因',
    `remark` VARCHAR(500) DEFAULT NULL COMMENT '备注',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uix_order_no` (`order_no`),
    INDEX `ix_user_id` (`user_id`),
    INDEX `ix_payment_status` (`payment_status`),
    INDEX `ix_created_at` (`created_at`),
    CONSTRAINT `fk_orders_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_orders_plan` FOREIGN KEY (`plan_id`) REFERENCES `membership_plans` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单表';

-- ============================================================
-- 7. 用户会员表
-- ============================================================
DROP TABLE IF EXISTS `user_memberships`;
CREATE TABLE `user_memberships` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    `plan_id` BIGINT UNSIGNED NOT NULL COMMENT '套餐ID',
    `order_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '关联订单ID',
    `start_at` DATETIME NOT NULL COMMENT '开始时间',
    `expire_at` DATETIME NOT NULL COMMENT '到期时间',
    `status` VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '状态: active/expired/cancelled',
    `daily_analysis_limit` INT NOT NULL DEFAULT -1 COMMENT '每日分析次数限制(继承自套餐)',
    `watchlist_limit` INT NOT NULL DEFAULT 100 COMMENT '自选股数量限制(继承自套餐)',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `ix_user_id` (`user_id`),
    INDEX `ix_status` (`status`),
    INDEX `ix_expire_at` (`expire_at`),
    CONSTRAINT `fk_memberships_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_memberships_plan` FOREIGN KEY (`plan_id`) REFERENCES `membership_plans` (`id`),
    CONSTRAINT `fk_memberships_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会员表';

-- ============================================================
-- 8. 每日使用量表 (用于限制免费用户)
-- ============================================================
DROP TABLE IF EXISTS `daily_usage`;
CREATE TABLE `daily_usage` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    `usage_date` DATE NOT NULL COMMENT '使用日期',
    `analysis_count` INT NOT NULL DEFAULT 0 COMMENT '当日分析次数',
    `watchlist_count` INT NOT NULL DEFAULT 0 COMMENT '自选股操作次数',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uix_user_date` (`user_id`, `usage_date`),
    INDEX `ix_usage_date` (`usage_date`),
    CONSTRAINT `fk_usage_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日使用量表';

-- ============================================================
-- 9. 分析任务表 (持久化任务状态)
-- ============================================================
DROP TABLE IF EXISTS `analysis_tasks`;
CREATE TABLE `analysis_tasks` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `task_id` VARCHAR(64) NOT NULL COMMENT '任务ID(业务ID)',
    `user_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '用户ID(可为空表示匿名)',
    `task_type` ENUM('single', 'batch', 'scheduled', 'market_review') NOT NULL DEFAULT 'single' COMMENT '任务类型',
    `status` ENUM('pending', 'running', 'completed', 'failed', 'cancelled') NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    `stock_codes` TEXT DEFAULT NULL COMMENT '股票代码列表（JSON）',
    `params` TEXT DEFAULT NULL COMMENT '其他参数（JSON）',
    `total_count` INT NOT NULL DEFAULT 0 COMMENT '总任务数',
    `completed_count` INT NOT NULL DEFAULT 0 COMMENT '已完成数',
    `failed_count` INT NOT NULL DEFAULT 0 COMMENT '失败数',
    `progress` INT NOT NULL DEFAULT 0 COMMENT '进度百分比(0-100)',
    `result` TEXT DEFAULT NULL COMMENT '任务结果（JSON）',
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `started_at` DATETIME DEFAULT NULL COMMENT '开始执行时间',
    `completed_at` DATETIME DEFAULT NULL COMMENT '完成时间',
    `source_ip` VARCHAR(50) DEFAULT NULL COMMENT '来源IP',
    `user_agent` VARCHAR(255) DEFAULT NULL COMMENT '用户代理',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uix_task_id` (`task_id`),
    INDEX `ix_user_id` (`user_id`),
    INDEX `ix_status` (`status`),
    INDEX `ix_created_at` (`created_at`),
    CONSTRAINT `fk_tasks_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分析任务表';

-- ============================================================
-- 10. 用户自选股表
-- ============================================================
DROP TABLE IF EXISTS `user_watchlists`;
CREATE TABLE `user_watchlists` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    `group_name` VARCHAR(50) DEFAULT '默认分组' COMMENT '分组名称',
    `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序顺序',
    `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '添加时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uix_user_stock` (`user_id`, `stock_code`),
    INDEX `ix_user_id` (`user_id`),
    INDEX `ix_user_group` (`user_id`, `group_name`),
    CONSTRAINT `fk_watchlist_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户自选股表';

-- ============================================================
-- 11. 分析历史表 (便于用户查看历史)
-- ============================================================
DROP TABLE IF EXISTS `analysis_history`;
CREATE TABLE `analysis_history` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '用户ID',
    `task_id` VARCHAR(64) DEFAULT NULL COMMENT '关联任务ID',
    `stock_code` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',
    `analysis_date` DATE NOT NULL COMMENT '分析日期',
    `market_data` TEXT DEFAULT NULL COMMENT '行情数据（JSON）',
    `analysis_result` TEXT DEFAULT NULL COMMENT '分析结果（JSON）',
    `ai_summary` TEXT DEFAULT NULL COMMENT 'AI 分析摘要',
    `score` INT DEFAULT NULL COMMENT '分析评分',
    `sentiment` ENUM('bullish', 'neutral', 'bearish') DEFAULT NULL COMMENT '情绪判断',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `ix_user_id` (`user_id`),
    INDEX `ix_stock_code` (`stock_code`),
    INDEX `ix_analysis_date` (`analysis_date`),
    INDEX `ix_user_stock_date` (`user_id`, `stock_code`, `analysis_date`),
    CONSTRAINT `fk_history_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分析历史表';

-- ============================================================
-- 12. 系统配置表 (可选,用于动态配置)
-- ============================================================
DROP TABLE IF EXISTS `system_configs`;
CREATE TABLE `system_configs` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `config_key` VARCHAR(100) NOT NULL COMMENT '配置键',
    `config_value` TEXT DEFAULT NULL COMMENT '配置值',
    `description` VARCHAR(500) DEFAULT NULL COMMENT '配置说明',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uix_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- ============================================================
-- 初始化数据
-- ============================================================

-- 初始化会员套餐
INSERT INTO `membership_plans` (`name`, `description`, `price`, `original_price`, `duration_days`, `daily_analysis_limit`, `watchlist_limit`, `features`, `sort_order`, `is_active`, `is_recommended`) VALUES
('免费版', '基础分析功能', 0.00, NULL, 36500, 5, 10, '["每日5次分析","10只自选股","7天历史记录"]', 0, 1, 0),
('周卡', '7天会员权益', 19.90, 29.90, 7, 50, 50, '["每日50次分析","50只自选股","30天历史记录","完整报告","邮件推送"]', 1, 1, 0),
('月卡', '30天会员权益', 49.90, 79.90, 30, 100, 100, '["每日100次分析","100只自选股","90天历史记录","完整报告","邮件推送","优先响应"]', 2, 1, 1),
('季卡', '90天会员权益', 99.90, 179.90, 90, -1, 200, '["不限分析次数","200只自选股","全部历史记录","完整报告","邮件推送","优先响应","专属客服"]', 3, 1, 0);

-- 初始化系统配置
INSERT INTO `system_configs` (`config_key`, `config_value`, `description`) VALUES
('free_daily_limit', '5', '免费用户每日分析次数限制'),
('free_watchlist_limit', '10', '免费用户自选股数量限制'),
('free_history_days', '7', '免费用户历史记录保留天数'),
('session_expire_hours', '24', 'Session过期时间(小时)'),
('verification_code_expire_minutes', '5', '验证码过期时间(分钟)'),
('verification_code_interval_seconds', '60', '验证码发送间隔(秒)'),
('referral_registration_reward', '10', '每邀请1人注册成功，邀请人获得的免费使用次数'),
('referral_reward_weekly', '30', '被邀请人购买周卡并支付成功后，邀请人获得的免费使用次数'),
('referral_reward_monthly', '100', '被邀请人购买月卡并支付成功后，邀请人获得的免费使用次数'),
('referral_reward_quarterly', '300', '被邀请人购买季卡并支付成功后，邀请人获得的免费使用次数');

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 完成
-- ============================================================
SELECT '数据库初始化完成!' AS message;
