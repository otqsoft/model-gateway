import { useNavigate } from 'react-router-dom';
import useRankingStore, { type Model } from '@/store/useRankingStore';
import { useLanguageStore } from '@/store/useLanguageStore';
import { formatTokens, formatChange, getProviderColor } from '@/utils/format';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
} from 'recharts';

interface CategorySectionProps {
  sectionId: string;
  titleKey: string;
  subtitleKey: string;
  icon: React.ElementType;
  filterFn: (model: Model) => boolean;
}

const MOCK_TREND = [
  { week: 'W1', tokens: 800_000_000 },
  { week: 'W2', tokens: 1_200_000_000 },
  { week: 'W3', tokens: 1_000_000_000 },
  { week: 'W4', tokens: 1_500_000_000 },
  { week: 'W5', tokens: 1_800_000_000 },
  { week: 'W6', tokens: 2_100_000_000 },
  { week: 'W7', tokens: 1_900_000_000 },
  { week: 'W8', tokens: 2_400_000_000 },
];

export default function CategorySection({ sectionId, titleKey, subtitleKey, icon: Icon, filterFn }: CategorySectionProps) {
  const { models } = useRankingStore();
  const { t } = useLanguageStore();
  const navigate = useNavigate();

  const filtered = models.filter(filterFn).sort((a, b) => b.weeklyTokens - a.weeklyTokens);
  const displayList = filtered.slice(0, 10);
  const totalTokens = filtered.reduce((s, m) => s + m.weeklyTokens, 0);

  return (
    <section id={sectionId} className="py-12">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
          <Icon className="h-5 w-5 text-accent" />
        </div>
        <div>
          <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">{t(titleKey)}</h2>
          <p className="text-sm text-gray-500 dark:text-zinc-400">{t(subtitleKey)}</p>
        </div>
        <span className="ml-auto rounded-full bg-light-200 dark:bg-dark-700 px-3 py-1 font-mono text-xs text-gray-500 dark:text-zinc-400">
          {filtered.length} {t('models')}
        </span>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800 p-5">
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_TREND}>
                <defs>
                  <linearGradient id={`grad-${sectionId}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="week" axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 10 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#71717a', fontSize: 10 }} tickFormatter={(v: number) => formatTokens(v)} />
                <Area type="monotone" dataKey="tokens" stroke="#6366f1" strokeWidth={2} fill={`url(#grad-${sectionId})`} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800">
          <div className="divide-y divide-light-300 dark:divide-dark-700">
            {displayList.map((model, index) => {
              const pct = totalTokens > 0 ? ((model.weeklyTokens / totalTokens) * 100).toFixed(1) : '0';
              return (
                <div
                  key={model.id}
                  className="flex items-center gap-3 px-5 py-2.5 transition-colors hover:bg-light-200/50 dark:hover:bg-dark-700/50"
                >
                  <span className="w-5 text-center font-mono text-xs text-gray-400 dark:text-zinc-500">{index + 1}</span>
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: getProviderColor(model.provider) }}
                  />
                  <button
                    onClick={() => navigate(`/model/${encodeURIComponent(model.id)}`)}
                    className="min-w-0 flex-1 text-left"
                  >
                    <span className="text-sm font-medium text-gray-900 dark:text-white hover:text-accent-light transition-colors truncate block">
                      {model.name}
                    </span>
                  </button>
                  <span className="shrink-0 font-mono text-xs text-gray-500 dark:text-zinc-400">{formatTokens(model.weeklyTokens)}</span>
                  <span className="shrink-0 font-mono text-[10px] text-gray-400 dark:text-zinc-500">{pct}%</span>
                  <span
                    className={`shrink-0 font-mono text-[10px] ${
                      model.weeklyChange > 0 ? 'text-emerald-400' : model.weeklyChange < 0 ? 'text-red-400' : 'text-zinc-500'
                    }`}
                  >
                    {formatChange(model.weeklyChange)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}