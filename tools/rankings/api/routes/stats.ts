import { Router, type Request, type Response } from 'express';
import { fetchModels } from '../services/openrouter.js';
import { fetchRankingsData, generateTopModelsFromLeaderboard } from '../services/rankingsScraper.js';

const router = Router();

/**
 * GET /api/stats - Get statistics
 */
router.get('/', async (req: Request, res: Response): Promise<void> => {
  try {
    const models = await fetchModels();
    const rankingsData = await fetchRankingsData();

    const totalModels = models.length;

    // Use real market share data if available, otherwise compute from models
    let providers;
    if (rankingsData.marketShare.length > 0) {
      providers = rankingsData.marketShare;
    } else {
      const providerMap = new Map<string, number>();
      for (const model of models) {
        providerMap.set(model.provider, (providerMap.get(model.provider) || 0) + 1);
      }
      providers = Array.from(providerMap.entries())
        .map(([name, count]) => ({
          name,
          count,
          share: parseFloat(((count / totalModels) * 100).toFixed(1)),
        }))
        .sort((a, b) => b.count - a.count);
    }

    // Category stats
    const categoryMap = new Map<string, number>();
    for (const model of models) {
      categoryMap.set(model.category, (categoryMap.get(model.category) || 0) + 1);
    }
    const categories = Array.from(categoryMap.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    res.json({ totalModels, providers, categories });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch stats' });
  }
});

/**
 * GET /api/stats/top-apps - Top applications using models
 */
router.get('/top-apps', async (req: Request, res: Response): Promise<void> => {
  try {
    const rankingsData = await fetchRankingsData();

    if (rankingsData.topApps.length > 0) {
      res.json(rankingsData.topApps);
      return;
    }

    // Fallback: hardcoded data from OpenRouter (as of June 2025)
    const apps = [
      { name: "Hermes Agent", description: "Open-source, self-improving AI agent by Nous Research that runs persistently with memory across sessions, and builds reusable skills from experience.", tokens: 748000000000 },
      { name: "OpenClaw", description: "Open-source AI agent that connects to your messaging apps and takes real actions on your behalf.", tokens: 170000000000 },
      { name: "Kilo Code", description: "Open-source AI coding agent for VS Code, JetBrains, and CLI", tokens: 169000000000 },
      { name: "pi", description: "There are many coding agents, but this one is yours.", tokens: 95300000000 },
      { name: "Claude Code", description: "Anthropic's agentic coding tool", tokens: 90700000000 },
      { name: "Descript", description: "AI Video & Podcast Editor", tokens: 71300000000 },
      { name: "Pioneer", description: "Inference API that improves with your traffic", tokens: 63700000000 },
      { name: "Lemonade", description: "The AI tool for Roblox games.", tokens: 54200000000 },
      { name: "Janitor AI", description: "Chatbot platform for custom AI characters", tokens: 30000000000 },
      { name: "ISEKAI ZERO", description: "AI adventures. Travel with your favorite characters", tokens: 29500000000 },
    ];
    res.json(apps);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch top apps' });
  }
});

/**
 * GET /api/stats/context-length - Context length distribution
 */
router.get('/context-length', async (req: Request, res: Response): Promise<void> => {
  try {
    const models = await fetchModels();
    const ranges = [
      { label: '< 1K', min: 0, max: 1000 },
      { label: '1K - 10K', min: 1000, max: 10000 },
      { label: '10K - 100K', min: 10000, max: 100000 },
      { label: '100K - 500K', min: 100000, max: 500000 },
      { label: '500K - 1M', min: 500000, max: 1000000 },
      { label: '> 1M', min: 1000000, max: Infinity },
    ];
    const distribution = ranges.map(r => ({
      label: r.label,
      count: models.filter(m => m.context_length >= r.min && m.context_length < r.max).length,
    }));
    res.json({ distribution });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch context length distribution' });
  }
});

/**
 * GET /api/stats/top-models - Top models weekly usage data for stacked bar chart
 * Returns last 52 weeks (1 year) of weekly token usage for top 10 models
 */
router.get('/top-models', async (req: Request, res: Response): Promise<void> => {
  try {
    const rankingsData = await fetchRankingsData();

    if (rankingsData.leaderboard.length > 0) {
      // Use real leaderboard data to generate chart data
      const result = generateTopModelsFromLeaderboard(rankingsData.leaderboard);
      res.json(result);
      return;
    }

    // Fallback: generate from model list with mock data
    const models = await fetchModels();
    const top10Models = [...models]
      .sort((a, b) => (b.weeklyTokens || 0) - (a.weeklyTokens || 0))
      .slice(0, 10);

    const now = new Date();
    const weeklyData: { date: string; models: { name: string; id: string; tokens: number; color: string }[] }[] = [];

    const generateWeeklyTokens = (modelName: string, weekIndex: number): number => {
      let hash = 0;
      for (let i = 0; i < modelName.length; i++) {
        hash = modelName.charCodeAt(i) + ((hash << 5) - hash);
        hash = hash & hash;
      }
      const base = Math.abs(hash) % 1000 + 500;
      const growth = 1 + (weekIndex / 52) * 0.8;
      const seasonality = Math.sin((weekIndex / 52) * Math.PI * 2) * 0.15 + 1;
      const weekVariation = (Math.abs(hash + weekIndex) % 200 - 100) / 1000;
      return Math.floor(base * 1_000_000_000_000 * growth * seasonality * (1 + weekVariation));
    };

    const colorPalette = [
      '#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6',
      '#ec4899', '#3b82f6', '#14b8a6', '#f97316', '#64748b',
    ];

    const modelColors = top10Models.map((m, i) => ({ name: m.name, id: m.id, color: colorPalette[i] }));

    for (let i = 51; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 7);
      const dateStr = date.toISOString().split('T')[0];
      const weekModels = top10Models.map((model, idx) => ({
        name: model.name,
        id: model.id,
        tokens: generateWeeklyTokens(model.name, i),
        color: colorPalette[idx],
      }));
      weeklyData.push({ date: dateStr, models: weekModels });
    }

    res.json({ weeklyData, modelColors });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch top models data' });
  }
});

export default router;
