import cache from './cache.js';

const RANKINGS_URL = 'https://openrouter.ai/rankings';
const CACHE_KEY = 'rankings_data';
const CACHE_TTL = 600000; // 10 minutes
const FETCH_TIMEOUT = 8000; // 8 seconds timeout for scraper

export interface LeaderboardEntry {
  rank: number;
  id: string;
  name: string;
  provider: string;
  weeklyTokens: number;
  weeklyChange: number;
}

export interface TopModelsData {
  weeklyData: { date: string; models: { name: string; id: string; tokens: number; color: string }[] }[];
  modelColors: { name: string; id: string; color: string }[];
}

export interface MarketShareEntry {
  name: string;
  count: number;
  share: number;
}

export interface TopAppEntry {
  name: string;
  description: string;
  tokens: number;
}

export interface RankingsData {
  leaderboard: LeaderboardEntry[];
  marketShare: MarketShareEntry[];
  topApps: TopAppEntry[];
  fetchedAt: string;
}

/**
 * Fetch with timeout
 */
async function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
      },
    });
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Try to extract __NEXT_DATA__ JSON from HTML
 */
function extractNextData(html: string): Record<string, unknown> | null {
  const match = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
  if (!match) return null;
  try {
    return JSON.parse(match[1]);
  } catch {
    return null;
  }
}

/**
 * Parse leaderboard from __NEXT_DATA__
 */
function parseLeaderboardFromNextData(nextData: any): LeaderboardEntry[] {
  try {
    const props = nextData?.props?.pageProps;
    if (!props) return [];

    // Try various possible data paths
    const data = props.leaderboard || props.rankings || props.models || props.topModels;
    if (Array.isArray(data)) {
      return data.map((item: any, index: number) => ({
        rank: index + 1,
        id: item.id || item.model_id || item.slug || '',
        name: item.name || item.model_name || '',
        provider: item.provider || (item.id ? item.id.split('/')[0] : 'unknown'),
        weeklyTokens: item.weeklyTokens || item.tokens || item.weekly_tokens || item.usage?.tokens || 0,
        weeklyChange: item.weeklyChange || item.change || item.weekly_change || item.usage?.change || 0,
      }));
    }
  } catch (e) {
    console.error('Failed to parse __NEXT_DATA__ for leaderboard:', e);
  }
  return [];
}

/**
 * Parse market share from __NEXT_DATA__
 */
function parseMarketShareFromNextData(nextData: any): MarketShareEntry[] {
  try {
    const props = nextData?.props?.pageProps;
    if (!props) return [];
    const data = props.marketShare || props.providers || props.providerStats;
    if (Array.isArray(data)) {
      return data.map((item: any) => ({
        name: item.name || item.provider || '',
        count: item.count || item.models || 0,
        share: item.share || item.percentage || 0,
      }));
    }
  } catch (e) {
    console.error('Failed to parse __NEXT_DATA__ for market share:', e);
  }
  return [];
}

/**
 * Parse top apps from __NEXT_DATA__
 */
function parseTopAppsFromNextData(nextData: any): TopAppEntry[] {
  try {
    const props = nextData?.props?.pageProps;
    if (!props) return [];
    const data = props.topApps || props.apps || props.appRankings;
    if (Array.isArray(data)) {
      return data.map((item: any) => ({
        name: item.name || '',
        description: item.description || '',
        tokens: item.tokens || item.usage || 0,
      }));
    }
  } catch (e) {
    console.error('Failed to parse __NEXT_DATA__ for top apps:', e);
  }
  return [];
}

// Track if we're currently fetching to avoid duplicate requests
let isFetching = false;

/**
 * Main function to fetch and parse all rankings data
 * Returns cached data if available, empty data on failure (never blocks)
 */
export async function fetchRankingsData(): Promise<RankingsData> {
  const cached = cache.get<RankingsData>(CACHE_KEY);
  if (cached) return cached;

  // If already fetching, return empty data immediately (don't block)
  if (isFetching) {
    return { leaderboard: [], marketShare: [], topApps: [], fetchedAt: '' };
  }

  isFetching = true;
  try {
    const response = await fetchWithTimeout(RANKINGS_URL, FETCH_TIMEOUT);

    if (!response.ok) {
      console.warn(`Rankings scraper returned ${response.status}`);
      return { leaderboard: [], marketShare: [], topApps: [], fetchedAt: new Date().toISOString() };
    }

    const html = await response.text();

    // Try __NEXT_DATA__ extraction
    const nextData = extractNextData(html);
    let leaderboard: LeaderboardEntry[] = [];
    let marketShare: MarketShareEntry[] = [];
    let topApps: TopAppEntry[] = [];

    if (nextData) {
      leaderboard = parseLeaderboardFromNextData(nextData);
      marketShare = parseMarketShareFromNextData(nextData);
      topApps = parseTopAppsFromNextData(nextData);
    }

    const data: RankingsData = {
      leaderboard,
      marketShare,
      topApps,
      fetchedAt: new Date().toISOString(),
    };

    // Only cache if we got some useful data
    if (leaderboard.length > 0 || topApps.length > 0) {
      cache.set(CACHE_KEY, data, CACHE_TTL);
    }

    return data;
  } catch (error) {
    console.warn('Rankings scraper failed (will use mock data):', error instanceof Error ? error.message : error);
    return { leaderboard: [], marketShare: [], topApps: [], fetchedAt: new Date().toISOString() };
  } finally {
    isFetching = false;
  }
}

/**
 * Generate top models weekly data from leaderboard entries
 * Uses real leaderboard data as the current week's baseline
 */
export function generateTopModelsFromLeaderboard(leaderboard: LeaderboardEntry[]): TopModelsData {
  const top10 = leaderboard.slice(0, 10);

  const colorPalette = [
    '#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6',
    '#ec4899', '#3b82f6', '#14b8a6', '#f97316', '#64748b',
  ];

  const modelColors = top10.map((model, i) => ({
    name: model.name,
    id: model.id,
    color: colorPalette[i % colorPalette.length],
  }));

  // Generate 52 weeks of data based on current real data
  const now = new Date();
  const weeklyData = [];

  for (let i = 51; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i * 7);
    const dateStr = date.toISOString().split('T')[0];

    const models = top10.map((model, idx) => {
      const baseTokens = model.weeklyTokens;
      const weekFactor = (52 - i) / 52;
      const growthFactor = 0.3 + weekFactor * 0.7;
      const noise = 0.9 + Math.sin(i * 0.5 + idx) * 0.1;

      return {
        name: model.name,
        id: model.id,
        tokens: Math.floor(baseTokens * growthFactor * noise),
        color: colorPalette[idx % colorPalette.length],
      };
    });

    weeklyData.push({ date: dateStr, models });
  }

  return { weeklyData, modelColors };
}
