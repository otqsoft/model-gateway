// 模型库 store

import { create } from "zustand";
import type { ModelConfig } from "@/types";
import { BUILTIN_MODELS } from "@/lib/builtinModels";
import { STORAGE_KEYS, generateId, loadJSON, saveJSON } from "@/lib/storage";
import { supabase } from "@/lib/supabase";
import { ensureModelsSeeded } from "@/lib/supabaseInit";

interface ModelState {
  models: ModelConfig[];
  loading: boolean;
  init: () => Promise<void>;
  addModel: (model: Omit<ModelConfig, "id" | "builtin">) => ModelConfig;
  updateModel: (id: string, patch: Partial<ModelConfig>) => void;
  removeModel: (id: string) => void;
  toggleEnabled: (id: string) => void;
  resetToBuiltin: () => void;
  getById: (id: string) => ModelConfig | undefined;
}

export const useModelStore = create<ModelState>((set, get) => ({
  models: [],
  loading: true,

  init: async () => {
    set({ loading: true });

    // 确保种子数据已导入
    await ensureModelsSeeded();

    try {
      const { data, error } = await supabase
        .from("models")
        .select("*")
        .order("id", { ascending: true });

      if (!error && data && data.length > 0) {
        const remoteModels: ModelConfig[] = data.map((row: Record<string, unknown>) => ({
          id: String(row.id),
          name: String(row.name),
          provider: String(row.provider),
          modalities: Array.isArray(row.modalities) ? row.modalities : [],
          pricing: row.pricing as ModelConfig["pricing"],
          enabled: row.enabled !== false,
          builtin: row.builtin === true,
        }));
        set({ models: remoteModels, loading: false });
        saveJSON(STORAGE_KEYS.models, remoteModels);
        return;
      }
    } catch {
      // Supabase 请求失败，使用本地缓存
    }

    // 降级：从 localStorage 加载，或使用内置模型
    const stored = loadJSON<ModelConfig[] | null>(STORAGE_KEYS.models, null);
    if (stored && stored.length > 0) {
      set({ models: stored, loading: false });
    } else {
      set({ models: BUILTIN_MODELS, loading: false });
      saveJSON(STORAGE_KEYS.models, BUILTIN_MODELS);
    }
  },

  addModel: (model) => {
    const newModel: ModelConfig = {
      ...model,
      id: generateId(),
      builtin: false,
    };
    set((s) => {
      const next = [...s.models, newModel];
      saveJSON(STORAGE_KEYS.models, next);
      return { models: next };
    });

    // 异步写入 Supabase
    supabase
      .from("models")
      .insert({
        id: newModel.id,
        name: newModel.name,
        provider: newModel.provider,
        modalities: newModel.modalities,
        pricing: newModel.pricing,
        enabled: newModel.enabled,
        builtin: newModel.builtin,
      })
      .then(({ error }) => {
        if (error) console.warn("写入 Supabase models 失败:", error.message);
      });

    return newModel;
  },

  updateModel: (id, patch) => {
    set((s) => {
      const next = s.models.map((m) => (m.id === id ? { ...m, ...patch } : m));
      saveJSON(STORAGE_KEYS.models, next);
      return { models: next };
    });

    // 异步更新 Supabase
    const updated = get().models.find((m) => m.id === id);
    if (updated) {
      const supabasePatch: Record<string, unknown> = {};
      if (patch.name !== undefined) supabasePatch.name = updated.name;
      if (patch.provider !== undefined) supabasePatch.provider = updated.provider;
      if (patch.modalities !== undefined) supabasePatch.modalities = updated.modalities;
      if (patch.pricing !== undefined) supabasePatch.pricing = updated.pricing;
      if (patch.enabled !== undefined) supabasePatch.enabled = updated.enabled;

      supabase
        .from("models")
        .update(supabasePatch)
        .eq("id", id)
        .then(({ error }) => {
          if (error) console.warn("更新 Supabase models 失败:", error.message);
        });
    }
  },

  removeModel: (id) => {
    set((s) => {
      const next = s.models.filter((m) => !(m.id === id && !m.builtin));
      saveJSON(STORAGE_KEYS.models, next);
      return { models: next };
    });

    // 异步删除 Supabase 记录
    supabase
      .from("models")
      .delete()
      .eq("id", id)
      .then(({ error }) => {
        if (error) console.warn("删除 Supabase models 失败:", error.message);
      });
  },

  toggleEnabled: (id) => {
    set((s) => {
      const next = s.models.map((m) =>
        m.id === id ? { ...m, enabled: !m.enabled } : m
      );
      saveJSON(STORAGE_KEYS.models, next);
      return { models: next };
    });

    // 异步更新 Supabase
    const model = get().models.find((m) => m.id === id);
    if (model) {
      supabase
        .from("models")
        .update({ enabled: model.enabled })
        .eq("id", id)
        .then(({ error }) => {
          if (error) console.warn("更新 Supabase models 失败:", error.message);
        });
    }
  },

  resetToBuiltin: () => {
    set({ models: BUILTIN_MODELS });
    saveJSON(STORAGE_KEYS.models, BUILTIN_MODELS);

    // 异步重置 Supabase：删除非内置模型，重置内置模型
    supabase
      .from("models")
      .delete()
      .neq("builtin", true)
      .then(() => {
        // 重新 upsert 内置模型
        const rows = BUILTIN_MODELS.map((m) => ({
          id: m.id,
          name: m.name,
          provider: m.provider,
          modalities: m.modalities,
          pricing: m.pricing,
          enabled: true,
          builtin: true,
        }));
        return supabase.from("models").upsert(rows, { onConflict: "id" });
      })
      .then(({ error }) => {
        if (error) console.warn("重置 Supabase models 失败:", error.message);
      });
  },

  getById: (id) => get().models.find((m) => m.id === id),
}));
