// 历史记录 store

import { create } from "zustand";
import type { HistoryRecord } from "@/types";
import { STORAGE_KEYS, generateId, loadJSON, saveJSON } from "@/lib/storage";
import { supabase } from "@/lib/supabase";
import { ensureHistoryReady } from "@/lib/supabaseInit";

interface HistoryState {
  records: HistoryRecord[];
  loading: boolean;
  init: () => Promise<void>;
  addRecord: (record: Omit<HistoryRecord, "id" | "timestamp">) => void;
  removeRecord: (id: string) => void;
  clearAll: () => void;
}

export const useHistoryStore = create<HistoryState>((set) => ({
  records: [],
  loading: true,

  init: async () => {
    set({ loading: true });

    const historyReady = await ensureHistoryReady();

    if (historyReady) {
      try {
        const { data, error } = await supabase
          .from("history")
          .select("*")
          .order("timestamp", { ascending: false })
          .limit(200);

        if (!error && data && data.length > 0) {
          const remoteRecords: HistoryRecord[] = data.map((row: Record<string, unknown>) => ({
            id: String(row.id),
            timestamp: Number(row.timestamp),
            modelName: String(row.model_name),
            textTokens: Number(row.text_tokens),
            imageTokens: Number(row.image_tokens),
            audioTokens: Number(row.audio_tokens),
            videoTokens: Number(row.video_tokens),
            totalInputTokens: Number(row.total_input_tokens),
            estimatedOutputTokens: Number(row.estimated_output_tokens),
            inputCost: Number(row.input_cost),
            outputCost: Number(row.output_cost),
            totalCost: Number(row.total_cost),
          }));
          set({ records: remoteRecords, loading: false });
          saveJSON(STORAGE_KEYS.history, remoteRecords);
          return;
        }
      } catch {
        // Supabase 请求失败，降级到本地
      }
    }

    // 降级：从 localStorage 加载
    const stored = loadJSON<HistoryRecord[]>(STORAGE_KEYS.history, []);
    set({ records: stored, loading: false });
  },

  addRecord: (record) => {
    set((s) => {
      const newRecord: HistoryRecord = {
        ...record,
        id: generateId(),
        timestamp: Date.now(),
      };
      const next: HistoryRecord[] = [newRecord, ...s.records].slice(0, 200);
      saveJSON(STORAGE_KEYS.history, next);

      // 异步写入 Supabase
      supabase
        .from("history")
        .insert({
          id: newRecord.id,
          timestamp: newRecord.timestamp,
          model_name: newRecord.modelName,
          text_tokens: newRecord.textTokens,
          image_tokens: newRecord.imageTokens,
          audio_tokens: newRecord.audioTokens,
          video_tokens: newRecord.videoTokens,
          total_input_tokens: newRecord.totalInputTokens,
          estimated_output_tokens: newRecord.estimatedOutputTokens,
          input_cost: newRecord.inputCost,
          output_cost: newRecord.outputCost,
          total_cost: newRecord.totalCost,
        })
        .then(({ error }) => {
          if (error) console.warn("写入 Supabase history 失败:", error.message);
        });

      return { records: next };
    });
  },

  removeRecord: (id) => {
    set((s) => {
      const next = s.records.filter((r) => r.id !== id);
      saveJSON(STORAGE_KEYS.history, next);

      // 异步删除 Supabase 记录
      supabase
        .from("history")
        .delete()
        .eq("id", id)
        .then(({ error }) => {
          if (error) console.warn("删除 Supabase history 失败:", error.message);
        });

      return { records: next };
    });
  },

  clearAll: () => {
    set({ records: [] });
    saveJSON(STORAGE_KEYS.history, []);

    // 异步清空 Supabase
    supabase
      .from("history")
      .delete()
      .neq("id", "")
      .then(({ error }) => {
        if (error) console.warn("清空 Supabase history 失败:", error.message);
      });
  },
}));
