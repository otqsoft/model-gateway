import { Router, type Request, type Response } from 'express';
import { fetchModels } from '../services/openrouter.js';

const router = Router();

/**
 * GET /api/stats - Get statistics
 */
router.get('/', async (req: Request, res: Response): Promise<void> => {
  try {
    const models = await fetchModels();

    const totalModels = models.length;

    // Provider stats
    const providerMap = new Map<string, number>();
    for (const model of models) {
      providerMap.set(model.provider, (providerMap.get(model.provider) || 0) + 1);
    }
    const providers = Array.from(providerMap.entries())
      .map(([name, count]) => ({
        name,
        count,
        share: parseFloat(((count / totalModels) * 100).toFixed(1)),
      }))
      .sort((a, b) => b.count - a.count);

    // Category stats
    const categoryMap = new Map<string, number>();
    for (const model of models) {
      categoryMap.set(model.category, (categoryMap.get(model.category) || 0) + 1);
    }
    const categories = Array.from(categoryMap.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    // Usage trend: mock data for the last 12 weeks
    const usageTrend = [];
    const now = new Date();
    for (let i = 11; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 7);
      const dateStr = date.toISOString().split('T')[0];
      usageTrend.push({
        date: dateStr,
        tokens: Math.floor(Math.random() * 50000000) + 10000000,
      });
    }

    res.json({ totalModels, providers, categories, usageTrend });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch stats' });
  }
});

/**
 * GET /api/stats/top-apps - Top applications using models
 */
router.get('/top-apps', async (req: Request, res: Response): Promise<void> => {
  const apps = [
    { name: "Hermes Agent", description: "Open-source, self-improving AI agent by Nous Research...", tokens: 523000000000 },
    { name: "GitLaw", description: "Collaborate on a live decentralized git network", tokens: 164000000000 },
    { name: "Kilo Code", description: "Open-source AI coding agent for VS Code, JetBrains, and CLI", tokens: 129000000000 },
    { name: "OpenClaw", description: "Open-source AI agent for messaging apps", tokens: 125000000000 },
    { name: "Claude Code", description: "Anthropic's agentic coding tool", tokens: 50100000000 },
    { name: "Descript", description: "AI Video & Podcast Editor", tokens: 42700000000 },
    { name: "pi", description: "There are many coding agents, but this one is yours.", tokens: 35900000000 },
    { name: "Janitor AI", description: "Chatbot platform for custom AI characters", tokens: 29000000000 },
    { name: "ISEKAI ZERO", description: "AI adventures. Travel with your favorite characters", tokens: 28000000000 },
    { name: "Mira", description: "Telegram-native AI assistant", tokens: 19700000000 },
  ];
  res.json(apps);
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
    // Trend data for the chart
    const trend = [];
    const now = new Date();
    for (let i = 11; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 7);
      trend.push({
        date: date.toISOString().split('T')[0],
        short1k: Math.floor(Math.random() * 30) + 20,
        mid10k: Math.floor(Math.random() * 40) + 30,
        long100k: Math.floor(Math.random() * 50) + 40,
      });
    }
    res.json({ distribution, trend });
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
    const models = await fetchModels();
    
    // Get top 10 models by weekly tokens (mock data)
    const top10Models = [...models]
      .sort((a, b) => (b.weeklyTokens || 0) - (a.weeklyTokens || 0))
      .slice(0, 10);
    
    // Generate 52 weeks of data (1 year)
    const now = new Date();
    const weeklyData: { date: string; models: { name: string; id: string; tokens: number; color: string }[] }[] = [];
    
    // Create deterministic token values based on model name hash
    const generateWeeklyTokens = (modelName: string, weekIndex: number): number => {
      let hash = 0;
      for (let i = 0; i < modelName.length; i++) {
        hash = modelName.charCodeAt(i) + ((hash << 5) - hash);
        hash = hash & hash;
      }
      // Base value with seasonal growth
      const base = Math.abs(hash) % 1000 + 500; // 500B - 1.5T base
      const growth = 1 + (weekIndex / 52) * 0.8; // Up to 80% growth over year
      const seasonality = Math.sin((weekIndex / 52) * Math.PI * 2) * 0.15 + 1; // ±15% seasonality
      const weekVariation = (Math.abs(hash + weekIndex) % 200 - 100) / 1000; // ±10% weekly variation
      
      return Math.floor(base * 1_000_000_000_000 * growth * seasonality * (1 + weekVariation));
    };
    
    // Unique color palette for models (35 distinct colors)
    const colorPalette = [
      '#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6',
      '#ec4899', '#3b82f6', '#14b8a6', '#f97316', '#64748b',
      '#a855f7', '#06b6d4', '#84cc16', '#eab308', '#f43f5e',
      '#22c55e', '#0ea5e9', '#7c3aed', '#db2777', '#059669',
      '#d97706', '#dc2626', '#4f46e5', '#0891b2', '#65a30d',
      '#ca8a04', '#be185d', '#15803d', '#1d4ed8', '#7e22ce',
      '#0284c7', '#4d7c0f', '#92400e', '#b91c1c', '#3730a3'
    ];
    
    // Hash function for model name to color index
    const hashModelName = (name: string): number => {
      let hash = 0;
      for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
        hash = hash & hash;
      }
      return Math.abs(hash);
    };
    
    // Assign unique colors to each model in top10
    const modelColorMap: Record<string, string> = {};
    const usedColorIndices = new Set<number>();
    
    top10Models.forEach((model) => {
      let colorIndex = hashModelName(model.name) % colorPalette.length;
      // If color is already used, find next available
      let attempts = 0;
      while (usedColorIndices.has(colorIndex) && attempts < colorPalette.length) {
        colorIndex = (colorIndex + 1) % colorPalette.length;
        attempts++;
      }
      usedColorIndices.add(colorIndex);
      modelColorMap[model.id] = colorPalette[colorIndex];
    });
    
    const getModelColor = (modelId: string): string => {
      return modelColorMap[modelId] || colorPalette[0];
    };
    
    for (let i = 51; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 7);
      const dateStr = date.toISOString().split('T')[0];
      
      const weekModels = top10Models.map(model => ({
        name: model.name,
        id: model.id,
        tokens: generateWeeklyTokens(model.name, i),
        color: getModelColor(model.id),
      }));
      
      weeklyData.push({ date: dateStr, models: weekModels });
    }
    
    res.json({
      weeklyData,
      modelColors: top10Models.map(m => ({ name: m.name, id: m.id, color: getModelColor(m.id) })),
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch top models data' });
  }
});

export default router;
