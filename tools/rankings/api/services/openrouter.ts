import cache from './cache.js';

export interface Model {
  id: string;
  name: string;
  description: string;
  context_length: number;
  pricing: {
    prompt: string;
    completion: string;
    web_search?: string;
    input_cache_read?: string;
  };
  architecture: {
    modality: string;
    input_modalities: string[];
    output_modalities: string[];
    tokenizer: string;
  };
  top_provider: {
    context_length: number;
    max_completion_tokens: number;
    is_moderated: boolean;
  };
  supported_parameters: string[];
  per_request_limits: number | null;
  provider: string;
  inputPrice: number;
  outputPrice: number;
  hasToolCalls: boolean;
  hasImageInput: boolean;
  hasImageOutput: boolean;
  hasAudioInput: boolean;
  category: string;
  speed: number;
  benchmarks: {
    math: number;
    coding: number;
    reasoning: number;
    chat: number;
  };
  weeklyTokens: number;
  weeklyChange: number;
}

interface RawModel {
  id: string;
  name: string;
  description: string;
  context_length: number;
  pricing: {
    prompt: string;
    completion: string;
    web_search?: string;
    input_cache_read?: string;
  };
  architecture: {
    modality: string;
    input_modalities: string[];
    output_modalities: string[];
    tokenizer: string;
  };
  top_provider: {
    context_length: number;
    max_completion_tokens: number;
    is_moderated: boolean;
  };
  supported_parameters: string[];
  per_request_limits: number | null;
}

const CACHE_KEY = 'openrouter_models';
const CACHE_TTL = 300000; // 5 minutes

function extractProvider(id: string): string {
  const parts = id.split('/');
  return parts.length > 1 ? parts[0] : 'unknown';
}

function categorizeModel(model: RawModel, hasToolCalls: boolean, hasImageInput: boolean): string {
  const nameLower = model.name.toLowerCase();
  const idLower = model.id.toLowerCase();
  if (
    hasToolCalls ||
    model.supported_parameters.includes('reasoning') ||
    nameLower.includes('code') ||
    idLower.includes('code')
  ) {
    return 'programming';
  }
  if (hasImageInput) {
    return 'vision';
  }
  return 'general';
}

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

function computeSpeed(id: string, name: string): number {
  const nameLower = name.toLowerCase();
  const idLower = id.toLowerCase();
  const h = hashString(id);
  if (nameLower.includes('flash') || nameLower.includes('lite') || idLower.includes('flash') || idLower.includes('lite')) {
    return 150 + (h % 51); // 150-200
  }
  if (nameLower.includes('pro') || nameLower.includes('opus') || idLower.includes('pro') || idLower.includes('opus')) {
    return 40 + (h % 41); // 40-80
  }
  return 80 + (h % 41); // 80-120
}

function computeBenchmarks(id: string, name: string): { math: number; coding: number; reasoning: number; chat: number } {
  const nameLower = name.toLowerCase();
  const idLower = id.toLowerCase();
  const h = hashString(id);
  const isHighEnd = nameLower.includes('pro') || nameLower.includes('opus') || idLower.includes('pro') || idLower.includes('opus') || nameLower.includes('o3') || idLower.includes('o3');
  const isMid = nameLower.includes('flash') || nameLower.includes('mini') || idLower.includes('flash') || idLower.includes('mini');

  const base = isHighEnd ? 85 : isMid ? 70 : 60;
  const range = isHighEnd ? 13 : isMid ? 15 : 30;

  return {
    math: base + (h % range),
    coding: base + ((h >> 4) % range),
    reasoning: base + ((h >> 8) % range),
    chat: base + ((h >> 12) % range),
  };
}

function computeWeeklyTokens(id: string, name: string): number {
  const nameLower = name.toLowerCase();
  const idLower = id.toLowerCase();
  const h = hashString(id);
  const isTopModel = nameLower.includes('deepseek') || nameLower.includes('claude') || nameLower.includes('gpt') || nameLower.includes('gemini') || idLower.includes('deepseek') || idLower.includes('claude') || idLower.includes('gpt') || idLower.includes('gemini');

  if (isTopModel) {
    return 500_000_000_000 + (h % 2_500_000_000_000); // 500B - 3T
  }
  return 10_000_000_000 + (h % 490_000_000_000); // 10B - 500B
}

function computeWeeklyChange(id: string): number {
  const h = hashString(id);
  // Range -10 to 500
  return -10 + (h % 511);
}

function processModel(raw: RawModel): Model {
  const provider = extractProvider(raw.id);
  const inputPrice = parseFloat(raw.pricing.prompt) * 1_000_000;
  const outputPrice = parseFloat(raw.pricing.completion) * 1_000_000;
  const hasToolCalls = raw.supported_parameters.includes('tools');
  const hasImageInput = raw.architecture.input_modalities.includes('image');
  const hasImageOutput = raw.architecture.output_modalities.includes('image');
  const hasAudioInput = raw.architecture.input_modalities.includes('audio');
  const category = categorizeModel(raw, hasToolCalls, hasImageInput);
  const speed = computeSpeed(raw.id, raw.name);
  const benchmarks = computeBenchmarks(raw.id, raw.name);
  const weeklyTokens = computeWeeklyTokens(raw.id, raw.name);
  const weeklyChange = computeWeeklyChange(raw.id);

  return {
    ...raw,
    provider,
    inputPrice,
    outputPrice,
    hasToolCalls,
    hasImageInput,
    hasImageOutput,
    hasAudioInput,
    category,
    speed,
    benchmarks,
    weeklyTokens,
    weeklyChange,
  };
}

export async function fetchModels(): Promise<Model[]> {
  const cached = cache.get<Model[]>(CACHE_KEY);
  if (cached) return cached;

  const apiKey = process.env.OPENROUTER_API_KEY;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`;
  }

  const response = await fetch('https://openrouter.ai/api/v1/models', {
    headers,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch models: ${response.status} ${response.statusText}`);
  }

  const data = (await response.json()) as { data: RawModel[] };
  const models = data.data.map(processModel);

  cache.set(CACHE_KEY, models, CACHE_TTL);
  return models;
}

export async function getModelById(id: string): Promise<Model | undefined> {
  const models = await fetchModels();
  return models.find((m) => m.id === id);
}
