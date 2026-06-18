-- Supabase 数据表迁移脚本
-- 在 Supabase Dashboard → SQL Editor 中执行此脚本

-- ============================================
-- 1. models 表
-- ============================================
CREATE TABLE IF NOT EXISTS models (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  provider TEXT NOT NULL,
  modalities JSONB NOT NULL DEFAULT '[]',
  pricing JSONB NOT NULL DEFAULT '{}',
  enabled BOOLEAN NOT NULL DEFAULT true,
  builtin BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 启用 RLS 并允许 service_role 完全访问
ALTER TABLE models ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow service_role full access" ON models
  FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');
-- 允许匿名读取（前端使用 service_role key，此策略为备用）
CREATE POLICY "Allow anon read" ON models
  FOR SELECT USING (true);

-- ============================================
-- 2. history 表
-- ============================================
CREATE TABLE IF NOT EXISTS history (
  id TEXT PRIMARY KEY,
  timestamp BIGINT NOT NULL,
  model_name TEXT NOT NULL,
  text_tokens INTEGER NOT NULL DEFAULT 0,
  image_tokens INTEGER NOT NULL DEFAULT 0,
  audio_tokens INTEGER NOT NULL DEFAULT 0,
  video_tokens INTEGER NOT NULL DEFAULT 0,
  total_input_tokens INTEGER NOT NULL DEFAULT 0,
  estimated_output_tokens INTEGER NOT NULL DEFAULT 0,
  input_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
  output_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
  total_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 启用 RLS 并允许 service_role 完全访问
ALTER TABLE history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow service_role full access" ON history
  FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "Allow anon read" ON history
  FOR SELECT USING (true);

-- ============================================
-- 3. 自动导入内置模型（upsert）
-- ============================================
INSERT INTO models (id, name, provider, modalities, pricing, enabled, builtin) VALUES
  ('gpt-4o', 'GPT-4o', 'OpenAI',
   '["text","image","audio","video"]',
   '{"text":{"inputPer1M":2.5,"outputPer1M":10},"image":{"inputPer1M":2.5},"audio":{"perMinute":0.006},"video":{"perMinute":0.006}}',
   true, true),
  ('gpt-4-turbo', 'GPT-4 Turbo', 'OpenAI',
   '["text","image"]',
   '{"text":{"inputPer1M":10,"outputPer1M":30},"image":{"inputPer1M":10},"audio":{"perMinute":0},"video":{"perMinute":0}}',
   true, true),
  ('gpt-3.5-turbo', 'GPT-3.5 Turbo', 'OpenAI',
   '["text"]',
   '{"text":{"inputPer1M":0.5,"outputPer1M":1.5},"image":{"inputPer1M":0},"audio":{"perMinute":0},"video":{"perMinute":0}}',
   true, true),
  ('claude-3-opus', 'Claude 3 Opus', 'Anthropic',
   '["text","image"]',
   '{"text":{"inputPer1M":15,"outputPer1M":75},"image":{"inputPer1M":15},"audio":{"perMinute":0},"video":{"perMinute":0}}',
   true, true),
  ('claude-3-5-sonnet', 'Claude 3.5 Sonnet', 'Anthropic',
   '["text","image"]',
   '{"text":{"inputPer1M":3,"outputPer1M":15},"image":{"inputPer1M":3},"audio":{"perMinute":0},"video":{"perMinute":0}}',
   true, true),
  ('claude-3-haiku', 'Claude 3 Haiku', 'Anthropic',
   '["text","image"]',
   '{"text":{"inputPer1M":0.25,"outputPer1M":1.25},"image":{"inputPer1M":0.25},"audio":{"perMinute":0},"video":{"perMinute":0}}',
   true, true),
  ('gemini-1-5-pro', 'Gemini 1.5 Pro', 'Google',
   '["text","image","audio","video"]',
   '{"text":{"inputPer1M":1.25,"outputPer1M":5},"image":{"inputPer1M":1.25},"audio":{"perMinute":0.005},"video":{"perMinute":0.005}}',
   true, true),
  ('gemini-1-5-flash', 'Gemini 1.5 Flash', 'Google',
   '["text","image","audio","video"]',
   '{"text":{"inputPer1M":0.075,"outputPer1M":0.3},"image":{"inputPer1M":0.075},"audio":{"perMinute":0.0005},"video":{"perMinute":0.0005}}',
   true, true),
  ('whisper', 'Whisper', 'OpenAI',
   '["audio"]',
   '{"text":{"inputPer1M":0,"outputPer1M":0},"image":{"inputPer1M":0},"audio":{"perMinute":0.006},"video":{"perMinute":0}}',
   true, true)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  provider = EXCLUDED.provider,
  modalities = EXCLUDED.modalities,
  pricing = EXCLUDED.pricing,
  enabled = EXCLUDED.enabled,
  builtin = EXCLUDED.builtin;
