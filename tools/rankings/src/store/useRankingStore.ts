import { create } from 'zustand';

export interface Model {
  id: string;
  name: string;
  description: string;
  context_length: number;
  pricing: { prompt: string; completion: string };
  architecture: { modality: string; input_modalities: string[]; output_modalities: string[] };
  top_provider: { context_length: number; max_completion_tokens: number };
  supported_parameters: string[];
  provider: string;
  inputPrice: number;
  outputPrice: number;
  hasToolCalls: boolean;
  hasImageInput: boolean;
  hasImageOutput: boolean;
  hasAudioInput: boolean;
  category: string;
  speed: number;
  benchmarks: { math: number; coding: number; reasoning: number; chat: number };
  weeklyTokens: number;
  weeklyChange: number;
}

interface TopApp {
  name: string;
  description: string;
  tokens: number;
}

interface RankingState {
  models: Model[];
  leaderboard: Model[];
  benchmarkModels: Model[];
  fastestModels: Model[];
  topApps: TopApp[];
  stats: { totalModels: number; providers: { name: string; count: number; share: number }[]; categories: { name: string; count: number }[] } | null;
  contextLengthData: { distribution: { label: string; count: number }[] } | null;
  loading: boolean;
  error: string | null;
  fetchAllData: () => Promise<void>;
}

// API base path - uses Vite's base URL in production, /api in development
const API_BASE = import.meta.env.DEV ? '/api' : `${import.meta.env.BASE_URL}api`;

/**
 * Safe fetch that returns null on failure instead of throwing
 */
async function safeFetch(url: string): Promise<Response | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) {
      console.warn(`Fetch failed: ${url} returned ${res.status}`);
      return null;
    }
    return res;
  } catch (err) {
    console.warn(`Fetch failed: ${url}`, err);
    return null;
  }
}

const useRankingStore = create<RankingState>((set) => ({
  models: [],
  leaderboard: [],
  benchmarkModels: [],
  fastestModels: [],
  topApps: [],
  stats: null,
  contextLengthData: null,
  loading: false,
  error: null,

  fetchAllData: async () => {
    set({ loading: true, error: null });
    try {
      const [modelsRes, statsRes, leaderboardRes, benchmarksRes, fastestRes, topAppsRes, contextLengthRes] = await Promise.all([
        safeFetch(`${API_BASE}/models?limit=200`),
        safeFetch(`${API_BASE}/stats`),
        safeFetch(`${API_BASE}/models/leaderboard`),
        safeFetch(`${API_BASE}/models/benchmarks`),
        safeFetch(`${API_BASE}/models/fastest`),
        safeFetch(`${API_BASE}/stats/top-apps`),
        safeFetch(`${API_BASE}/stats/context-length`),
      ]);

      // Parse each response, using fallback data if fetch failed
      const modelsData = modelsRes ? await modelsRes.json().catch(() => ({ data: [] })) : { data: [] };
      const statsData = statsRes ? await statsRes.json().catch(() => null) : null;
      const leaderboardData = leaderboardRes ? await leaderboardRes.json().catch(() => []) : [];
      const benchmarksData = benchmarksRes ? await benchmarksRes.json().catch(() => []) : [];
      const fastestData = fastestRes ? await fastestRes.json().catch(() => []) : [];
      const topAppsData = topAppsRes ? await topAppsRes.json().catch(() => []) : [];
      const contextLengthData = contextLengthRes ? await contextLengthRes.json().catch(() => null) : null;

      const allModels = modelsData.data || modelsData.models || [];

      // If leaderboard is empty, generate from models sorted by weeklyTokens
      const leaderboard = Array.isArray(leaderboardData) && leaderboardData.length > 0
        ? leaderboardData
        : [...allModels].sort((a: Model, b: Model) => b.weeklyTokens - a.weeklyTokens);

      set({
        models: allModels,
        leaderboard,
        benchmarkModels: benchmarksData,
        fastestModels: fastestData,
        topApps: topAppsData,
        stats: statsData,
        contextLengthData,
        loading: false,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      set({ error: message, loading: false });
    }
  },
}));

export default useRankingStore;
