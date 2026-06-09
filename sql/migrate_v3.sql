-- ============================================================
-- 迁移脚本 v3：新增 OpenRouter 供应商 + model_mapping.system_prompt 字段
-- 说明：在已有 model_gateway 数据库上执行此脚本完成升级
-- 执行时间：2026-06-09
-- ============================================================

USE `model_gateway`;

-- ────────────────────────────────────────────────────────────
-- 1. model_mapping 表新增 system_prompt 字段
--    使用 MEDIUMTEXT 以支持超长提示词（最大 16MB）
-- ────────────────────────────────────────────────────────────
ALTER TABLE `model_mapping`
  ADD COLUMN IF NOT EXISTS `system_prompt` MEDIUMTEXT DEFAULT NULL
    COMMENT '模型级系统提示词（注入到每次会话最前端）'
    AFTER `extra_headers`;

-- ────────────────────────────────────────────────────────────
-- 2. 新增 OpenRouter 供应商记录
--    若已存在则跳过（INSERT IGNORE）
-- ────────────────────────────────────────────────────────────
INSERT IGNORE INTO `model_providers`
    (`name`, `display_name`, `provider_type`, `base_url`, `api_key`, `max_concurrency`, `timeout_seconds`, `remark`)
VALUES
    ('openrouter', 'OpenRouter', 'model', 'https://openrouter.ai/api/v1', '', 50, 120,
     'OpenRouter 聚合路由平台，覆盖 GPT-4、Claude、Gemini、Llama 等数百个模型');

-- ────────────────────────────────────────────────────────────
-- 3. 初始化常用 OpenRouter 模型映射（可按需增删）
--    价格单位：元/1K tokens（以官方美元价 × 7.2 换算，仅供参考）
-- ────────────────────────────────────────────────────────────
INSERT IGNORE INTO `model_mapping`
    (`model_alias`, `provider_name`, `upstream_model`, `input_price`, `output_price`, `max_tokens`, `supports_stream`, `description`)
VALUES
-- OpenAI 系列（通过 OpenRouter 路由）
('openrouter/gpt-4o',               'openrouter', 'openai/gpt-4o',                0.018000, 0.054000, 128000, 1, 'GPT-4o via OpenRouter'),
('openrouter/gpt-4o-mini',          'openrouter', 'openai/gpt-4o-mini',           0.001080, 0.004320, 128000, 1, 'GPT-4o Mini via OpenRouter'),
-- Claude 系列
('openrouter/claude-3.5-sonnet',    'openrouter', 'anthropic/claude-3.5-sonnet',  0.021600, 0.108000, 200000, 1, 'Claude 3.5 Sonnet via OpenRouter'),
('openrouter/claude-3-haiku',       'openrouter', 'anthropic/claude-3-haiku',     0.001800, 0.002160, 200000, 1, 'Claude 3 Haiku via OpenRouter'),
-- Google Gemini 系列
('openrouter/gemini-pro-1.5',       'openrouter', 'google/gemini-pro-1.5',        0.025200, 0.075600, 1000000,1, 'Gemini 1.5 Pro via OpenRouter'),
('openrouter/gemini-flash-1.5',     'openrouter', 'google/gemini-flash-1.5',      0.005040, 0.015120, 1000000,1, 'Gemini 1.5 Flash via OpenRouter'),
-- Meta Llama 系列（免费模型）
('openrouter/llama-3.1-8b',         'openrouter', 'meta-llama/llama-3.1-8b-instruct', 0.000000, 0.000000, 131072, 1, 'Llama 3.1 8B (免费) via OpenRouter'),
('openrouter/llama-3.1-70b',        'openrouter', 'meta-llama/llama-3.1-70b-instruct',0.005760, 0.005760, 131072, 1, 'Llama 3.1 70B via OpenRouter'),
-- DeepSeek（通过 OpenRouter）
('openrouter/deepseek-r1',          'openrouter', 'deepseek/deepseek-r1',         0.003600, 0.010800, 65536, 1, 'DeepSeek R1 via OpenRouter'),
('openrouter/deepseek-chat-v3',     'openrouter', 'deepseek/deepseek-chat-v3-0324',0.000720, 0.002880, 65536, 1, 'DeepSeek Chat V3 via OpenRouter'),
-- Qwen 系列
('openrouter/qwen-2.5-72b',         'openrouter', 'qwen/qwen-2.5-72b-instruct',   0.002520, 0.002880, 131072, 1, 'Qwen2.5 72B via OpenRouter'),
-- Mistral 系列
('openrouter/mistral-large',        'openrouter', 'mistralai/mistral-large',      0.021600, 0.064800, 131072, 1, 'Mistral Large via OpenRouter');
