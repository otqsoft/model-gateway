import { Router, type Request, type Response } from 'express';
import { fetchModels, getModelById, type Model } from '../services/openrouter.js';

const router = Router();

/**
 * GET /api/models - List models with filtering and pagination
 */
router.get('/', async (req: Request, res: Response): Promise<void> => {
  try {
    let models = await fetchModels();

    // Filter by category
    const category = req.query.category as string;
    if (category) {
      models = models.filter((m) => m.category === category);
    }

    // Filter by search
    const search = req.query.search as string;
    if (search) {
      const q = search.toLowerCase();
      models = models.filter(
        (m) =>
          m.name.toLowerCase().includes(q) ||
          m.id.toLowerCase().includes(q) ||
          m.description.toLowerCase().includes(q),
      );
    }

    // Filter by context length range
    const contextLength = req.query.contextLength as string;
    if (contextLength) {
      models = models.filter((m) => {
        const cl = m.context_length;
        switch (contextLength) {
          case '1k-10k':
            return cl >= 1000 && cl <= 10000;
          case '10k-100k':
            return cl > 10000 && cl <= 100000;
          case '100k+':
            return cl > 100000;
          default:
            return true;
        }
      });
    }

    // Filter by capabilities
    if (req.query.hasToolCalls === 'true') {
      models = models.filter((m) => m.hasToolCalls);
    }
    if (req.query.hasImageInput === 'true') {
      models = models.filter((m) => m.hasImageInput);
    }
    if (req.query.hasImageOutput === 'true') {
      models = models.filter((m) => m.hasImageOutput);
    }
    if (req.query.hasAudioInput === 'true') {
      models = models.filter((m) => m.hasAudioInput);
    }

    // Sort
    const sort = req.query.sort as string;
    if (sort) {
      switch (sort) {
        case 'price_asc':
          models.sort((a, b) => a.inputPrice - b.inputPrice);
          break;
        case 'price_desc':
          models.sort((a, b) => b.inputPrice - a.inputPrice);
          break;
        case 'context_length':
          models.sort((a, b) => b.context_length - a.context_length);
          break;
        case 'usage':
        default:
          // No real usage data, keep default order
          break;
      }
    }

    // Pagination
    const page = Math.max(1, parseInt(req.query.page as string) || 1);
    const limit = Math.max(1, parseInt(req.query.limit as string) || 20);
    const total = models.length;
    const start = (page - 1) * limit;
    const data = models.slice(start, start + limit);

    res.json({ data, total, page, limit });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch models' });
  }
});

/**
 * GET /api/models/benchmarks - Get benchmark rankings
 */
router.get('/benchmarks', async (req: Request, res: Response): Promise<void> => {
  try {
    const models = await fetchModels();
    const sorted = [...models].sort((a, b) => {
      const avgA = (a.benchmarks.math + a.benchmarks.coding + a.benchmarks.reasoning + a.benchmarks.chat) / 4;
      const avgB = (b.benchmarks.math + b.benchmarks.coding + b.benchmarks.reasoning + b.benchmarks.chat) / 4;
      return avgB - avgA;
    });
    const top50 = sorted.slice(0, 50);
    res.json(top50);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch benchmark rankings' });
  }
});

/**
 * GET /api/models/fastest - Get fastest models
 */
router.get('/fastest', async (req: Request, res: Response): Promise<void> => {
  try {
    const models = await fetchModels();
    const sorted = [...models].sort((a, b) => b.speed - a.speed);
    const top20 = sorted.slice(0, 20);
    res.json(top20);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch fastest models' });
  }
});

/**
 * GET /api/models/:id - Get single model by id
 */
router.get('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const id = decodeURIComponent(req.params.id);
    const model = await getModelById(id);
    if (!model) {
      res.status(404).json({ error: 'Model not found' });
      return;
    }
    res.json(model);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch model' });
  }
});

export default router;
