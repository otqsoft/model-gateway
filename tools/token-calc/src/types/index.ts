// 多模态类型定义

export type Modality = "text" | "image" | "audio" | "video";

export interface ModelPricing {
  text: { inputPer1M: number; outputPer1M: number };
  image: { inputPer1M: number; outputPer1M?: number };
  audio: { perMinute: number };
  video: { perMinute: number };
}

export interface ModelConfig {
  id: string;
  name: string;
  provider: string;
  modalities: Modality[];
  pricing: ModelPricing;
  enabled: boolean;
  builtin: boolean;
}

export interface HistoryRecord {
  id: string;
  timestamp: number;
  modelName: string;
  textTokens: number;
  imageTokens: number;
  audioTokens: number;
  videoTokens: number;
  totalInputTokens: number;
  estimatedOutputTokens: number;
  inputCost: number;
  outputCost: number;
  totalCost: number;
}

export interface AppSettings {
  defaultModelId: string;
  theme: "dark";
}

// 单项输入的 Token 估算结果
export interface TokenBreakdown {
  textTokens: number;
  imageTokens: number;
  audioTokens: number;
  videoTokens: number;
  // 媒体元信息
  textChars: number;
  textWords: number;
  imageItems: ImageItemInfo[];
  audioItems: MediaItemInfo[];
  videoItems: MediaItemInfo[];
}

export interface ImageItemInfo {
  id: string;
  name: string;
  width: number;
  height: number;
  tiles: number;
  tokens: number;
  previewUrl: string;
}

export interface MediaItemInfo {
  id: string;
  name: string;
  durationSec: number;
  tokens: number;
  sizeLabel: string;
}
