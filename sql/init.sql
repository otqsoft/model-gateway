-- ============================================================
-- AI Model Gateway — MySQL 完整建表 SQL
-- 字符集: utf8mb4，引擎: InnoDB
-- ============================================================

CREATE DATABASE IF NOT EXISTS `model_gateway`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `model_gateway`;

-- ============================================================
-- 1. 厂商配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS `model_providers` (
  `id`              BIGINT       UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name`            VARCHAR(64)  NOT NULL COMMENT '厂商标识，如 deepseek / coze / dify',
  `display_name`    VARCHAR(128) NOT NULL COMMENT '显示名称',
  `provider_type`   VARCHAR(32)  NOT NULL DEFAULT 'model' COMMENT '厂商类型: model（模型厂商）/ agent（智能体厂商）',
  `base_url`        VARCHAR(512) NOT NULL COMMENT '上游 API 基础地址',
  `api_key`         TEXT         NOT NULL DEFAULT '' COMMENT '模型厂商 API Key（加密存储）；智能体厂商此字段留空，Key 在各智能体上配置',
  `max_concurrency` INT          NOT NULL DEFAULT 50  COMMENT '该厂商最大并发数',
  `timeout_seconds` INT          NOT NULL DEFAULT 120 COMMENT '请求超时秒数',
  `is_enabled`      TINYINT(1)   NOT NULL DEFAULT 1   COMMENT '是否启用 1启用 0禁用',
  `extra_headers`   JSON                  DEFAULT NULL COMMENT '附加请求头（JSON对象）',
  `remark`          VARCHAR(255)          DEFAULT NULL COMMENT '备注',
  `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_provider_type` (`provider_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='上游厂商配置';

-- ============================================================
-- 2. 模型映射与定价表
-- ============================================================
CREATE TABLE IF NOT EXISTS `model_mapping` (
  `id`                BIGINT       UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `model_alias`       VARCHAR(128) NOT NULL COMMENT '对外暴露的模型名，如 gpt-3.5-turbo',
  `provider_name`     VARCHAR(64)  NOT NULL COMMENT '对应厂商 name（关联 model_providers.name）',
  `upstream_model`    VARCHAR(128) NOT NULL COMMENT '上游真实模型名',
  `input_price`       DECIMAL(12,6)NOT NULL DEFAULT 0.000000 COMMENT '输入单价（元/1K tokens）',
  `output_price`      DECIMAL(12,6)NOT NULL DEFAULT 0.000000 COMMENT '输出单价（元/1K tokens）',
  `max_tokens`        INT          NOT NULL DEFAULT 4096  COMMENT '最大 token 数',
  `supports_stream`   TINYINT(1)   NOT NULL DEFAULT 1    COMMENT '是否支持流式',
  `supports_multimodal` TINYINT(1) NOT NULL DEFAULT 0    COMMENT '是否支持多模态（图像理解）',
  `is_enabled`        TINYINT(1)   NOT NULL DEFAULT 1    COMMENT '是否启用',
  `description`       VARCHAR(255)          DEFAULT NULL COMMENT '模型描述',
  `extra_headers`    JSON                  DEFAULT NULL COMMENT '厂商额外参数，如 Coze 的 bot_id',
  `created_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_alias` (`model_alias`),
  KEY `idx_provider` (`provider_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型映射与定价';

-- ============================================================
-- 3. API Key 管理表
-- ============================================================
CREATE TABLE IF NOT EXISTS `api_keys` (
  `id`               BIGINT       UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `key_id`           CHAR(24)     NOT NULL COMMENT 'Key ID，前缀 sk- 后 22 位随机，对外可见',
  `key_hash`         CHAR(64)     NOT NULL COMMENT 'SHA-256 哈希，用于鉴权比对',
  `key_prefix`       CHAR(8)      NOT NULL COMMENT 'Key 前8位，管理端展示用',
  `name`             VARCHAR(128) NOT NULL COMMENT 'Key 名称/标签',
  `allowed_models`   JSON         NOT NULL COMMENT '允许访问的模型别名列表（JSON数组）',
  `max_concurrency`  INT          NOT NULL DEFAULT 20   COMMENT '该 Key 最大并发数',
  `daily_limit`      INT                   DEFAULT NULL COMMENT '每日调用上限，NULL=不限',
  `monthly_limit`    INT                   DEFAULT NULL COMMENT '每月调用上限，NULL=不限',
  `is_enabled`       TINYINT(1)   NOT NULL DEFAULT 1    COMMENT '1启用 0禁用',
  `start_date`       DATE                  DEFAULT NULL COMMENT '生效日期（含）',
  `end_date`         DATE                  DEFAULT NULL COMMENT '失效日期（含）',
  `allowed_weekdays` VARCHAR(20)           DEFAULT '1,2,3,4,5,6,7' COMMENT '允许星期，逗号分隔1-7',
  `allowed_time_start` TIME                DEFAULT NULL COMMENT '每日允许开始时间',
  `allowed_time_end`   TIME                DEFAULT NULL COMMENT '每日允许结束时间',
  `total_tokens`     BIGINT       NOT NULL DEFAULT 0    COMMENT '累计 token 消耗',
  `total_cost`       DECIMAL(14,4)NOT NULL DEFAULT 0.0000 COMMENT '累计费用（元）',
  `call_count`       BIGINT       NOT NULL DEFAULT 0    COMMENT '累计调用次数',
  `remark`           VARCHAR(255)          DEFAULT NULL COMMENT '备注',
  `created_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_key_id`   (`key_id`),
  UNIQUE KEY `uk_key_hash` (`key_hash`),
  KEY `idx_enabled` (`is_enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API Key 管理';

-- ============================================================
-- 4. 请求全生命周期日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS `request_logs` (
  `id`              BIGINT       UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `request_id`      CHAR(36)     NOT NULL COMMENT 'UUID，全局唯一请求ID',
  `api_key_id`      BIGINT       UNSIGNED          DEFAULT NULL COMMENT '关联 api_keys.id',
  `key_id`          CHAR(24)              DEFAULT NULL COMMENT 'Key 标识（冗余存储）',
  `model_alias`     VARCHAR(128) NOT NULL COMMENT '请求的模型别名',
  `provider_name`   VARCHAR(64)           DEFAULT NULL COMMENT '路由到的厂商',
  `upstream_model`  VARCHAR(128)          DEFAULT NULL COMMENT '上游真实模型名',
  `status`          ENUM('pending','running','success','error','timeout')
                                 NOT NULL DEFAULT 'pending' COMMENT '请求状态',
  `is_stream`       TINYINT(1)   NOT NULL DEFAULT 0    COMMENT '是否流式请求',
  `client_ip`       VARCHAR(64)           DEFAULT NULL COMMENT '客户端IP',
  `request_body`    MEDIUMTEXT            DEFAULT NULL COMMENT '请求体（可选存储）',
  `upstream_status` SMALLINT              DEFAULT NULL COMMENT '上游HTTP状态码',
  `error_message`   TEXT                  DEFAULT NULL COMMENT '错误信息',
  `prompt_tokens`   INT          NOT NULL DEFAULT 0    COMMENT '输入 token 数',
  `completion_tokens` INT        NOT NULL DEFAULT 0    COMMENT '输出 token 数',
  `total_tokens`    INT          NOT NULL DEFAULT 0    COMMENT '总 token 数',
  `ttft_ms`         INT                   DEFAULT NULL COMMENT '首包时间 TTFT（毫秒，流式专用）',
  `duration_ms`     INT                   DEFAULT NULL COMMENT '总耗时（毫秒）',
  `started_at`      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '请求开始时间',
  `ended_at`        DATETIME(3)           DEFAULT NULL COMMENT '请求结束时间',
  `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_request_id` (`request_id`),
  KEY `idx_api_key_id`    (`api_key_id`),
  KEY `idx_key_id`        (`key_id`),
  KEY `idx_model_alias`   (`model_alias`),
  KEY `idx_provider`      (`provider_name`),
  KEY `idx_status`        (`status`),
  KEY `idx_started_at`    (`started_at`),
  KEY `idx_upstream_status` (`upstream_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='请求生命周期日志';

-- ============================================================
-- 5. 计费与 Token 明细表
-- ============================================================
CREATE TABLE IF NOT EXISTS `usage_billing` (
  `id`               BIGINT       UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `request_id`       CHAR(36)     NOT NULL COMMENT '关联请求ID',
  `api_key_id`       BIGINT       UNSIGNED          DEFAULT NULL COMMENT '关联 api_keys.id',
  `key_id`           CHAR(24)              DEFAULT NULL COMMENT 'Key 标识',
  `model_alias`      VARCHAR(128) NOT NULL COMMENT '模型别名',
  `provider_name`    VARCHAR(64)  NOT NULL COMMENT '厂商',
  `prompt_tokens`    INT          NOT NULL DEFAULT 0    COMMENT '输入 token',
  `completion_tokens`INT          NOT NULL DEFAULT 0    COMMENT '输出 token',
  `total_tokens`     INT          NOT NULL DEFAULT 0    COMMENT '总 token',
  `input_price`      DECIMAL(12,6)NOT NULL DEFAULT 0.000000 COMMENT '输入单价快照（元/1K tokens）',
  `output_price`     DECIMAL(12,6)NOT NULL DEFAULT 0.000000 COMMENT '输出单价快照',
  `input_cost`       DECIMAL(14,8)NOT NULL DEFAULT 0.00000000 COMMENT '输入费用（元）',
  `output_cost`      DECIMAL(14,8)NOT NULL DEFAULT 0.00000000 COMMENT '输出费用（元）',
  `total_cost`       DECIMAL(14,8)NOT NULL DEFAULT 0.00000000 COMMENT '总费用（元）',
  `billed_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '计费时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_request_id` (`request_id`),
  KEY `idx_api_key_id`  (`api_key_id`),
  KEY `idx_key_id`      (`key_id`),
  KEY `idx_model`       (`model_alias`),
  KEY `idx_billed_at`   (`billed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Token 计费明细';

-- ============================================================
-- 初始化默认厂商（API Key 留空，部署后通过管理端配置）
-- ============================================================
INSERT INTO `model_providers` (`name`, `display_name`, `base_url`, `api_key`, `max_concurrency`, `timeout_seconds`) VALUES
('deepseek',     'DeepSeek',        'https://api.deepseek.com/v1',                            '', 50, 120),
('minimax',      'MiniMax',         'https://api.minimax.chat/v1',                            '', 30, 120),
('glm',          'GLM 智谱',        'https://open.bigmodel.cn/api/paas/v4',                   '', 30, 120),
('xiaomi',       '小米 AI',         'https://ai.xiaomi.com/v1',                               '', 20, 120),
('siliconflow',  '硅基流动',        'https://api.siliconflow.cn/v1',                          '', 50, 120),
('modelscope',   '魔塔社区',        'https://dashscope.aliyuncs.com/compatible-mode/v1',      '', 30, 120),
('openrouter',   'OpenRouter',      'https://openrouter.ai/api/v1',                           '', 50, 120);

-- ============================================================
-- 6. 智能体配置表
-- 说明：每条记录是一个具体智能体实例，同一供应商（如coze）可有多个实例，
--       每个实例的 api_key 独立配置；供应商层面不存储 api_key
-- ============================================================
CREATE TABLE IF NOT EXISTS `agent_configs` (
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

-- 初始化智能体类供应商（api_key 留空，在各智能体上单独配置）
INSERT IGNORE INTO `model_providers` (`name`, `display_name`, `provider_type`, `base_url`, `api_key`, `max_concurrency`, `timeout_seconds`) VALUES
('coze',   'Coze',   'agent', 'https://api.coze.cn/open_api/v2/chat',           '', 20, 120),
('dify',   'Dify',   'agent', 'https://api.dify.ai/v1',                          '', 20, 120);

-- ============================================================
-- 初始化默认模型映射
-- ============================================================
INSERT INTO `model_mapping` (`model_alias`, `provider_name`, `upstream_model`, `input_price`, `output_price`, `max_tokens`, `supports_stream`) VALUES
('deepseek-chat',             'deepseek',    'deepseek-chat',                    0.001000, 0.002000, 32768, 1),
('deepseek-coder',            'deepseek',    'deepseek-coder',                   0.001000, 0.002000, 16384, 1),
('deepseek-reasoner',         'deepseek',    'deepseek-reasoner',                0.004000, 0.016000, 32768, 1),
('abab6.5-chat',              'minimax',     'abab6.5-chat',                     0.030000, 0.030000, 245760,1),
('abab5.5-chat',              'minimax',     'abab5.5-chat',                     0.015000, 0.015000, 16384, 1),
('glm-4',                     'glm',         'glm-4',                            0.100000, 0.100000, 128000,1),
('glm-4-flash',               'glm',         'glm-4-flash',                      0.000100, 0.000100, 128000,1),
('glm-3-turbo',               'glm',         'glm-3-turbo',                      0.005000, 0.005000, 128000,1),
('Qwen2-72B-Instruct',        'siliconflow', 'Qwen/Qwen2-72B-Instruct',          0.004133, 0.004133, 32768, 1),
('Qwen2-7B-Instruct',         'siliconflow', 'Qwen/Qwen2-7B-Instruct',           0.000350, 0.000350, 32768, 1),
('deepseek-ai/DeepSeek-V2',   'siliconflow', 'deepseek-ai/DeepSeek-V2',          0.001400, 0.002800, 32768, 1),
('qwen-max',                  'modelscope',  'qwen-max',                         0.040000, 0.120000, 32768, 1),
('qwen-plus',                 'modelscope',  'qwen-plus',                        0.004000, 0.012000, 131072,1),
('qwen-turbo',                'modelscope',  'qwen-turbo',                       0.002000, 0.006000, 131072,1),
-- OpenRouter 模型映射
('openrouter/gpt-4o',               'openrouter', 'openai/gpt-4o',                0.018000, 0.054000, 128000, 1),
('openrouter/gpt-4o-mini',          'openrouter', 'openai/gpt-4o-mini',           0.001080, 0.004320, 128000, 1),
('openrouter/claude-3.5-sonnet',    'openrouter', 'anthropic/claude-3.5-sonnet',  0.021600, 0.108000, 200000, 1),
('openrouter/claude-3-haiku',       'openrouter', 'anthropic/claude-3-haiku',     0.001800, 0.002160, 200000, 1),
('openrouter/gemini-pro-1.5',       'openrouter', 'google/gemini-pro-1.5',        0.025200, 0.075600, 1000000,1),
('openrouter/gemini-flash-1.5',     'openrouter', 'google/gemini-flash-1.5',      0.005040, 0.015120, 1000000,1),
('openrouter/llama-3.1-8b',         'openrouter', 'meta-llama/llama-3.1-8b-instruct', 0.000000, 0.000000, 131072, 1),
('openrouter/llama-3.1-70b',        'openrouter', 'meta-llama/llama-3.1-70b-instruct',0.005760, 0.005760, 131072, 1),
('openrouter/deepseek-r1',          'openrouter', 'deepseek/deepseek-r1',         0.003600, 0.010800, 65536, 1),
('openrouter/deepseek-chat-v3',     'openrouter', 'deepseek/deepseek-chat-v3-0324',0.000720, 0.002880, 65536, 1),
('openrouter/qwen-2.5-72b',         'openrouter', 'qwen/qwen-2.5-72b-instruct',   0.002520, 0.002880, 131072, 1),
('openrouter/mistral-large',        'openrouter', 'mistralai/mistral-large',      0.021600, 0.064800, 131072, 1);

-- ============================================================
-- 增量变更：为已有数据库添加 supports_multimodal 字段
-- ============================================================
ALTER TABLE `model_mapping`
  ADD COLUMN IF NOT EXISTS `supports_multimodal` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否支持多模态（图像理解）' AFTER `supports_stream`;
