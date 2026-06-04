import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { PieChart as PieChartIcon } from 'lucide-react';
import useRankingStore from '@/store/useRankingStore';
import { useLanguageStore } from '@/store/useLanguageStore';
import { getProviderColor } from '@/utils/format';

interface CustomTooltipProps {
  active?: boolean;
  payload?: { name: string; value: number; payload: { share: number } }[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div className="rounded-lg border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800 px-3 py-2 shadow-lg">
      <p className="text-sm font-medium text-gray-900 dark:text-white">{item.name}</p>
      <p className="font-mono text-xs text-gray-500 dark:text-zinc-400">{item.payload.share}%</p>
    </div>
  );
}

export default function MarketShare() {
  const { stats } = useRankingStore();
  const { t } = useLanguageStore();

  const chartData = stats?.providers
    ? stats.providers.slice(0, 8).map((p) => ({
        name: p.name,
        value: p.count,
        share: p.share,
      }))
    : [];

  const totalModels = stats?.totalModels || 0;

  return (
    <section id="market-share" className="py-12">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
          <PieChartIcon className="h-5 w-5 text-accent" />
        </div>
        <div>
          <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">{t('market_share')}</h2>
          <p className="text-sm text-gray-500 dark:text-zinc-400">{t('compare_token_share')}</p>
        </div>
      </div>

      <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800 p-5">
        <div className="flex flex-col items-center gap-8 lg:flex-row">
          <div className="relative h-64 w-64 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={105}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={getProviderColor(entry.name)}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <p className="font-mono text-2xl font-bold text-gray-900 dark:text-white">{totalModels}</p>
              <p className="text-xs text-gray-400 dark:text-zinc-500">{t('models')}</p>
            </div>
          </div>

          <div className="grid flex-1 grid-cols-2 gap-x-8 gap-y-3">
            {chartData.map((entry) => (
              <div key={entry.name} className="flex items-center gap-2">
                <span
                  className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: getProviderColor(entry.name) }}
                />
                <span className="text-sm text-gray-700 dark:text-zinc-300 truncate">{entry.name}</span>
                <span className="ml-auto font-mono text-xs text-gray-400 dark:text-zinc-500">{entry.share}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}