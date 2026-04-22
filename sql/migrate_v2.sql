-- ============================================================
-- 迁移脚本 v2：智能体管理重构
-- 说明：在已有 model_gateway 数据库上执行此脚本完成升级
-- 执行时间：2026-04-22
-- ============================================================

USE `model_gateway`;

-- ────────────────────────────────────────────────────────────
-- 1. 为 model_providers 表新增 provider_type 字段
--    默认值 'model'，已有记录自动归为模型供应商
-- ────────────────────────────────────────────────────────────
ALTER TABLE `model_providers`
  ADD COLUMN IF NOT EXISTS `provider_type` VARCHAR(32) NOT NULL DEFAULT 'model'
    COMMENT '厂商类型: model（模型厂商）/ agent（智能体厂商）'
    AFTER `display_name`,
  ADD INDEX IF NOT EXISTS `idx_provider_type` (`provider_type`);

-- ────────────────────────────────────────────────────────────
-- 2. 删除旧的 agent_configs 表（若存在），重建
-- ────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS `agent_configs`;

CREATE TABLE `agent_configs` (
  `id`              BIGINT       UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `provider_name`   VARCHAR(64)  NOT NULL COMMENT '所属供应商名称（关联 model_providers.name，provider_type=agent）',
  `name`            VARCHAR(128) NOT NULL COMMENT '智能体唯一标识（全局唯一）',
  `display_name`    VARCHAR(128) NOT NULL COMMENT '显示名称',
  `bot_id`          VARCHAR(256)          DEFAULT NULL COMMENT 'Coze Bot ID / Dify App ID',
  `api_key`         TEXT                  DEFAULT NULL COMMENT '该智能体专属 API Key（加密存储）',
  `base_url`        VARCHAR(512)          DEFAULT NULL COMMENT '自定义API地址（覆盖供应商默认地址时使用）',
  `description`     VARCHAR(512)          DEFAULT NULL COMMENT '智能体描述',
  `config`          JSON                  DEFAULT NULL COMMENT '扩展配置（JSON）',
  `is_enabled`      TINYINT(1)   NOT NULL DEFAULT 1    COMMENT '是否启用',
  `total_calls`     BIGINT       NOT NULL DEFAULT 0    COMMENT '累计调用次数',
  `total_tokens`    BIGINT       NOT NULL DEFAULT 0    COMMENT '累计Token',
  `total_cost`      DECIMAL(14,4)NOT NULL DEFAULT 0.0000 COMMENT '累计费用',
  `remark`          VARCHAR(255)          DEFAULT NULL COMMENT '备注',
  `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_provider_name` (`provider_name`),
  KEY `idx_enabled` (`is_enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体配置（每行一个智能体实例，同供应商可多个）';

-- ────────────────────────────────────────────────────────────
-- 3. 插入默认智能体供应商（Coze / Dify）
--    api_key 留空，在各智能体上单独配置
-- ────────────────────────────────────────────────────────────
INSERT IGNORE INTO `model_providers`
    (`name`, `display_name`, `provider_type`, `base_url`, `api_key`, `max_concurrency`, `timeout_seconds`)
VALUES
    ('coze', 'Coze',   'agent', 'https://api.coze.cn/open_api/v2/chat', '', 20, 120),
    ('dify', 'Dify',   'agent', 'https://api.dify.ai/v1',               '', 20, 120);
