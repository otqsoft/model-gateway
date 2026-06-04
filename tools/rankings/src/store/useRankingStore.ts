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
  stats: { totalModels: number; providers: { name: string; count: number; share: number }[]; categories: { name: string; count: number }[]; usageTrend: { date: string; tokens: number }[] } | null;
  contextLengthData: { distribution: { label: string; count: number }[]; trend: { date: string; short1k: number; mid10k: number; long100k: number }[] } | null;
  loading: boolean;
  error: string | null;
  fetchAllData: () => Promise<void>;
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
      const [modelsRes, statsRes, benchmarksRes, fastestRes, topAppsRes, contextLengthRes] = await Promise.all([
        fetch('/api/models?limit=200'),
        fetch('/api/stats'),
        fetch('/api/models/benchmarks'),
        fetch('/api/models/fastest'),
        fetch('/api/stats/top-apps'),
        fetch('/api/stats/context-length'),
      ]);

      const modelsData = await modelsRes.json();
      const statsData = await statsRes.json();
      const benchmarksData = await benchmarksRes.json();
      const fastestData = await fastestRes.json();
      const topAppsData = await topAppsRes.json();
      const contextLengthData = await contextLengthRes.json();

      const allModels = modelsData.data || modelsData.models || [];
      const leaderboard = [...allModels].sort((a: Model, b: Model) => b.weeklyTokens - a.weeklyTokens);

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
