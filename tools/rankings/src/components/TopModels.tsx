import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { TrendingUp } from 'lucide-react';
import { useEffect, useState } from 'react';
import { formatTokens } from '@/utils/format';
import { useLanguageStore } from '@/store/useLanguageStore';
import { useThemeStore } from '@/store/useThemeStore';

interface ModelData {
  name: string;
  id: string;
  tokens: number;
  color: string;
}

interface WeeklyData {
  date: string;
  models: ModelData[];
}

interface TopModelsResponse {
  weeklyData: WeeklyData[];
  modelColors: { name: string; id: string; color: string }[];
}

const modelColorMap: Record<string, string> = {};

const API_BASE = import.meta.env.DEV ? '/api' : `${import.meta.env.BASE_URL}api`;

export default function TopModels() {
  const { t } = useLanguageStore();
  const { theme } = useThemeStore();
  const [data, setData] = useState<TopModelsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredWeek, setHoveredWeek] = useState<string | null>(null);
  const [isHovering, setIsHovering] = useState(false);

  const tickFill = theme === 'dark' ? '#71717a' : '#6b7280';

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE}/stats/top-models`);
        const result = await res.json();
        setData(result);
        result.modelColors.forEach((m: { name: string; color: string }) => {
          modelColorMap[m.name] = m.color;
        });
        setError(null);
      } catch (err) {
        setError(t('failed_fetch_top_models'));
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [t]);

  if (loading) {
    return (
      <section id="top-models" className="py-12">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
            <TrendingUp className="h-5 w-5 text-accent" />
          </div>
          <div>
            <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">{t('top_models')}</h2>
            <p className="text-sm text-gray-500 dark:text-zinc-400">{t('weekly_usage_across_openrouter')}</p>
          </div>
        </div>
        <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800 p-5">
          <div className="h-72 flex items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
              <span className="text-sm text-gray-400 dark:text-zinc-500">{t('loading')}</span>
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section id="top-models" className="py-12">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
            <TrendingUp className="h-5 w-5 text-accent" />
          </div>
          <div>
            <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">{t('top_models')}</h2>
            <p className="text-sm text-gray-500 dark:text-zinc-400">{t('weekly_usage_across_openrouter')}</p>
          </div>
        </div>
        <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800 p-5">
          <div className="h-72 flex items-center justify-center text-gray-400 dark:text-zinc-500">
            {error || t('failed_to_load_data')}
          </div>
        </div>
      </section>
    );
  }

  const chartData = data.weeklyData.map((week) => {
    const row: Record<string, number | string> = { date: week.date };
    week.models.forEach((model) => {
      row[model.name] = model.tokens;
    });
    row.dateLabel = week.date.slice(5);
    return row;
  });

  const barData = data.modelColors.map((model) => ({
    type: 'bar' as const,
    dataKey: model.name,
    fill: model.color,
    stackId: 'total',
    name: model.name,
  }));

  function formatTick(value: number): string {
    return formatTokens(value);
  }

  const selectedWeekData = hoveredWeek
    ? data.weeklyData.find((w) => w.date === hoveredWeek)
    : null;

  return (
    <section id="top-models" className="py-12">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
          <TrendingUp className="h-5 w-5 text-accent" />
        </div>
        <div>
          <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">{t('top_models')}</h2>
          <p className="text-sm text-gray-500 dark:text-zinc-400">{t('weekly_usage_across_openrouter')}</p>
        </div>
      </div>
      <div className="relative">
        <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800 p-5">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                onMouseMove={(e) => {
                  if (e.activeTooltipIndex !== undefined) {
                    const date = e.activePayload?.[0]?.payload?.date as string;
                    if (date) {
                      setHoveredWeek(date);
                      setIsHovering(true);
                    }
                  }
                }}
                onMouseLeave={() => {
                  setHoveredWeek(null);
                  setIsHovering(false);
                }}
              >
                <XAxis
                  type="category"
                  dataKey="dateLabel"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: tickFill, fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  interval={4}
                />
                <YAxis
                  type="number"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: tickFill, fontSize: 11, fontFamily: 'JetBrains Mono' }}
                  tickFormatter={formatTick}
                />
                {barData.map((bar, barIndex) => (
                  <Bar
                    key={bar.dataKey}
                    type={bar.type}
                    dataKey={bar.dataKey}
                    stackId="total"
                    name={bar.name}
                    onMouseEnter={() => {
                      setIsHovering(true);
                    }}
                    onMouseLeave={() => {
                      if (!hoveredWeek) {
                        setIsHovering(false);
                      }
                    }}
                  >
                    {chartData.map((entry, cellIndex) => {
                      const isHoveredWeek = hoveredWeek === entry.date;
                      const isLastModel = barIndex === barData.length - 1;
                      let fillColor = bar.fill;
                      if (isHoveredWeek && isLastModel) {
                        fillColor = bar.fill;
                      } else if (isHoveredWeek) {
                        fillColor = `${bar.fill}33`;
                      }
                      return <Cell key={`cell-${cellIndex}`} fill={fillColor} />;
                    })}
                  </Bar>
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 右侧固定面板 - 只在鼠标经过时显示 */}
        <div
          className={`absolute top-0 right-0 w-64 flex-shrink-0 transition-opacity duration-200 ${
            isHovering && selectedWeekData ? 'opacity-100' : 'opacity-0 pointer-events-none'
          }`}
          style={{ transform: 'translateX(calc(100% + 16px))' }}
        >
          <div className="h-85 rounded-lg border border-light-400 dark:border-dark-700 bg-white dark:bg-dark-800 p-4 shadow-xl flex flex-col">
            <p className="font-mono text-xs text-gray-400 dark:text-zinc-500 mb-3">
              {selectedWeekData ? selectedWeekData.date : ''}
            </p>
            {selectedWeekData && (
              <div className="space-y-2 flex-1 overflow-y-auto">
                {selectedWeekData.models
                  .sort((a, b) => b.tokens - a.tokens)
                  .map((model) => (
                    <div key={model.id} className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: model.color }}
                        />
                        <span className="text-sm text-gray-700 dark:text-zinc-300 truncate max-w-32">
                          {model.name}
                        </span>
                      </div>
                      <span className="font-mono text-sm text-gray-900 dark:text-white">
                        {formatTokens(model.tokens)}
                      </span>
                    </div>
                  ))}
                <div className="mt-3 pt-3 border-t border-light-300 dark:border-dark-700 flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900 dark:text-white">{t('total')}</span>
                  <span className="font-mono text-sm font-semibold text-accent">
                    {formatTokens(
                      selectedWeekData.models.reduce((sum, m) => sum + m.tokens, 0)
                    )}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
