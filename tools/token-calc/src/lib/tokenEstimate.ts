// Token 估算引擎
// 参考文档：TechnicalArchitecture.md 第 4 节

import type { ImageItemInfo, MediaItemInfo } from "@/types";

/**
 * 文本 Token 估算
 * 中文：约 1 字 ≈ 1.5 Token
 * 英文：约 4 字符 ≈ 1 Token
 */
export function estimateTextTokens(text: string): {
  tokens: number;
  chars: number;
  words: number;
} {
  const chars = text.length;
  let cjkTokens = 0;
  let otherChars = 0;

  for (const ch of text) {
    const code = ch.codePointAt(0)!;
    // CJK 统一表意文字及常见中日韩字符
    if (
      (code >= 0x4e00 && code <= 0x9fff) || // CJK 统一表意文字
      (code >= 0x3400 && code <= 0x4dbf) || // CJK 扩展 A
      (code >= 0x3040 && code <= 0x30ff) || // 平假名 + 片假名
      (code >= 0xac00 && code <= 0xd7af)    // 韩文音节
    ) {
      cjkTokens += 1.5;
    } else {
      otherChars += 1;
    }
  }

  const otherTokens = otherChars / 4;
  const tokens = Math.ceil(cjkTokens + otherTokens);

  // 词数：按空白切分（英文友好），中文按字符
  const enWords = text.trim().split(/\s+/).filter(Boolean).length;
  const cjkChars = text.split("").filter((ch) => {
    const code = ch.codePointAt(0)!;
    return (
      (code >= 0x4e00 && code <= 0x9fff) ||
      (code >= 0x3400 && code <= 0x4dbf) ||
      (code >= 0x3040 && code <= 0x30ff) ||
      (code >= 0xac00 && code <= 0xd7af)
    );
  }).length;
  const words = Math.max(enWords, cjkChars);

  return { tokens, chars, words };
}

/**
 * 图片 Token 估算（参考 GPT-4V 公式）
 * 总 Token = 85 + tiles × 170
 * tiles = ceil(width/512) × ceil(height/512)
 */
export function estimateImageTokens(width: number, height: number): {
  tiles: number;
  tokens: number;
} {
  const tilesX = Math.max(1, Math.ceil(width / 512));
  const tilesY = Math.max(1, Math.ceil(height / 512));
  const tiles = tilesX * tilesY;
  const tokens = 85 + tiles * 170;
  return { tiles, tokens };
}

/**
 * 语音 Token 估算（参考 Whisper）
 * 每分钟 ≈ 100 Token（约 1.67 Token/秒）
 */
export function estimateAudioTokens(durationSec: number): number {
  return Math.ceil((durationSec / 60) * 100);
}

/**
 * 视频 Token 估算
 * 帧采样：每秒 1 帧，每帧按图片公式计算
 * 音轨：按语音公式计算
 * 帧采样上限 600 帧（10 分钟），超出按比例缩放
 */
export function estimateVideoTokens(
  durationSec: number,
  width: number,
  height: number
): { frameTokens: number; audioTokens: number; total: number; sampledFrames: number } {
  const maxFrames = 600;
  const rawFrames = Math.floor(durationSec); // 每秒 1 帧
  const sampledFrames = Math.min(rawFrames, maxFrames);
  const scale = rawFrames > maxFrames ? maxFrames / rawFrames : 1;

  const perFrame = estimateImageTokens(width, height).tokens;
  const frameTokens = Math.ceil(perFrame * sampledFrames * (rawFrames > maxFrames ? 1 : 1));
  // 当超出上限时，按比例缩放回完整时长
  const scaledFrameTokens =
    rawFrames > maxFrames ? Math.ceil(perFrame * rawFrames * scale) : frameTokens;

  const audioTokens = estimateAudioTokens(durationSec);
  return {
    frameTokens: scaledFrameTokens,
    audioTokens,
    total: scaledFrameTokens + audioTokens,
    sampledFrames,
  };
}

// ============ 文件元信息读取 ============

export function readImageMeta(
  file: File
): Promise<{ width: number; height: number; previewUrl: string }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight, previewUrl: url });
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("图片加载失败"));
    };
    img.src = url;
  });
}

export function readMediaDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const el = file.type.startsWith("video/")
      ? document.createElement("video")
      : document.createElement("audio");
    el.preload = "metadata";
    el.onloadedmetadata = () => {
      const dur = isFinite(el.duration) ? el.duration : 0;
      URL.revokeObjectURL(url);
      resolve(dur);
    };
    el.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("媒体加载失败"));
    };
    el.src = url;
  });
}

export function readVideoMeta(
  file: File
): Promise<{ durationSec: number; width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const el = document.createElement("video");
    el.preload = "metadata";
    el.onloadedmetadata = () => {
      const dur = isFinite(el.duration) ? el.duration : 0;
      const w = el.videoWidth || 1280;
      const h = el.videoHeight || 720;
      URL.revokeObjectURL(url);
      resolve({ durationSec: dur, width: w, height: h });
    };
    el.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("视频加载失败"));
    };
    el.src = url;
  });
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function formatDuration(sec: number): string {
  if (!isFinite(sec) || sec <= 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  if (m >= 60) {
    const h = Math.floor(m / 60);
    const mm = m % 60;
    return `${h}:${mm.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export type { ImageItemInfo, MediaItemInfo };
