// 用户设置 store

import { create } from "zustand";
import type { AppSettings } from "@/types";
import { STORAGE_KEYS, loadJSON, saveJSON } from "@/lib/storage";

interface SettingsState extends AppSettings {
  init: () => void;
  setDefaultModel: (id: string) => void;
}

const DEFAULT_SETTINGS: AppSettings = {
  defaultModelId: "gpt-4o",
  theme: "dark",
};

export const useSettingsStore = create<SettingsState>((set) => ({
  ...DEFAULT_SETTINGS,
  init: () => {
    const stored = loadJSON<AppSettings>(STORAGE_KEYS.settings, DEFAULT_SETTINGS);
    set({ ...DEFAULT_SETTINGS, ...stored });
  },
  setDefaultModel: (id) => {
    set({ defaultModelId: id });
    const current = useSettingsStore.getState();
    saveJSON(STORAGE_KEYS.settings, {
      defaultModelId: current.defaultModelId,
      theme: current.theme,
    });
  },
}));
