// Supabase 数据表初始化与种子数据导入
// 使用方式：先在 Supabase SQL Editor 中执行 supabase-migration.sql
// 然后应用启动时会自动检测并导入种子数据

import { supabase } from "./supabase";
import { BUILTIN_MODELS } from "./builtinModels";
import type { ModelConfig } from "@/types";

/**
 * 检测 models 表是否为空，为空则导入内置模型
 */
export async function ensureModelsSeeded(): Promise<void> {
  const { data, error } = await supabase.from("models").select("id").limit(1);

  if (error) {
    console.warn("Supabase models 表不可用，请先执行 supabase-migration.sql:", error.message);
    return;
  }

  if (!data || data.length === 0) {
    await seedModels();
  }
}

/**
 * 检测 history 表是否可用
 */
export async function ensureHistoryReady(): Promise<boolean> {
  const { error } = await supabase.from("history").select("id").limit(1);
  if (error) {
    console.warn("Supabase history 表不可用，请先执行 supabase-migration.sql:", error.message);
    return false;
  }
  return true;
}

/**
 * 将内置模型导入 Supabase
 */
async function seedModels(): Promise<void> {
  const rows = BUILTIN_MODELS.map((m: ModelConfig) => ({
    id: m.id,
    name: m.name,
    provider: m.provider,
    modalities: m.modalities,
    pricing: m.pricing,
    enabled: m.enabled,
    builtin: m.builtin,
  }));

  const { error } = await supabase.from("models").upsert(rows, {
    onConflict: "id",
  });

  if (error) {
    console.error("导入内置模型失败:", error.message);
  }
}
