// 费用计算引擎
// 参考文档：TechnicalArchitecture.md 第 5.3 节

import type { ModelConfig, TokenBreakdown } from "@/types";

export interface CostBreakdown {
  textCost: number;
  imageCost: number;
  audioCost: number;
  videoCost: number;
  inputCost: number;
  outputCost: number;
  totalCost: number;
}

/**
 * 计算输入费用 + 输出费用
 * - 文本费用 = 文本 Token × 输入价 / 1M
 * - 图片费用 = 图片 Token × 图片输入价 / 1M
 * - 音频费用 = 音频分钟数 × 音频单价
 * - 视频费用 = 视频分钟数 × 视频单价
 * - 输出费用 = 预估输出 Token × 输出价 / 1M
 */
export function calculateCost(
  model: ModelConfig,
  breakdown: TokenBreakdown,
  estimatedOutputTokens: number
): CostBreakdown {
  const { pricing } = model;

  const textCost = (breakdown.textTokens * pricing.text.inputPer1M) / 1_000_000;
  const imageCost = (breakdown.imageTokens * pricing.image.inputPer1M) / 1_000_000;

  const audioMinutes = breakdown.audioItems.reduce((s, i) => s + i.durationSec, 0) / 60;
  const audioCost = audioMinutes * pricing.audio.perMinute;

  const videoMinutes = breakdown.videoItems.reduce((s, i) => s + i.durationSec, 0) / 60;
  const videoCost = videoMinutes * pricing.video.perMinute;

  const inputCost = textCost + imageCost + audioCost + videoCost;
  const outputCost = (estimatedOutputTokens * pricing.text.outputPer1M) / 1_000_000;
  const totalCost = inputCost + outputCost;

  return {
    textCost,
    imageCost,
    audioCost,
    videoCost,
    inputCost,
    outputCost,
    totalCost,
  };
}

export function formatCost(usd: number): string {
  if (usd === 0) return "$0.0000";
  if (usd < 0.0001) return "<$0.0001";
  if (usd < 1) return `$${usd.toFixed(6)}`;
  if (usd < 100) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

export function formatTokens(n: number): string {
  if (n < 1000) return n.toString();
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}K`;
  return `${(n / 1_000_000).toFixed(2)}M`;
}
