import { Ruler } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import useRankingStore from '@/store/useRankingStore';
import { useLanguageStore } from '@/store/useLanguageStore';

interface CustomTooltipProps {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  const { t } = useLanguageStore();
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800 px-3 py-2 shadow-lg">
      <p className="text-sm text-gray-900 dark:text-white">{label}</p>
      <p className="font-mono text-xs text-gray-500 dark:text-zinc-400">{payload[0].value} {t('models')}</p>
    </div>
  );
}

export default function ContextLengthSection() {
  const { contextLengthData } = useRankingStore();
  const { t } = useLanguageStore();

  const chartData = contextLengthData?.distribution || [
    { label: '< 1K', count: 5 },
    { label: '1K - 10K', count: 15 },
    { label: '10K - 100K', count: 45 },
    { label: '100K - 500K', count: 60 },
    { label: '500K - 1M', count: 30 },
    { label: '> 1M', count: 20 },
  ];

  return (
    <section id="context-length" className="py-12">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
          <Ruler className="h-5 w-5 text-accent" />
        </div>
        <div>
          <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">{t('context_length')}</h2>
          <p className="text-sm text-gray-500 dark:text-zinc-400">{t('requests_by_length')}</p>
        </div>
        <span className="ml-auto rounded-full bg-light-200 dark:bg-dark-700 px-3 py-1 font-mono text-xs text-gray-500 dark:text-zinc-400">
          1K - 10K tokens
        </span>
      </div>

      <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800 p-5">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#71717a', fontSize: 11, fontFamily: 'JetBrains Mono' }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#71717a', fontSize: 11, fontFamily: 'JetBrains Mono' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}