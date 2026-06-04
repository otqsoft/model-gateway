import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trophy } from 'lucide-react';
import useRankingStore from '@/store/useRankingStore';
import { useLanguageStore } from '@/store/useLanguageStore';
import { formatTokens, formatChange, getProviderColor } from '@/utils/format';

const RANK_COLORS: Record<number, string> = {
  1: 'text-yellow-400',
  2: 'text-zinc-300',
  3: 'text-amber-500',
};

export default function Leaderboard() {
  const { leaderboard } = useRankingStore();
  const { t } = useLanguageStore();
  const navigate = useNavigate();
  const [showAll, setShowAll] = useState(false);

  const displayList = showAll ? leaderboard.slice(0, 50) : leaderboard.slice(0, 10);

  return (
    <section id="leaderboard" className="py-12">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
          <Trophy className="h-5 w-5 text-accent" />
        </div>
        <div>
          <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">{t('leaderboard')}</h2>
          <p className="text-sm text-gray-500 dark:text-zinc-400">{t('compare_popular_models')}</p>
        </div>
        <span className="ml-auto rounded-full bg-accent/10 px-3 py-1 text-xs font-medium text-accent-light">
          {t('this_week')}
        </span>
      </div>

      <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800">
        <div className="divide-y divide-light-300 dark:divide-dark-700">
          {displayList.map((model, index) => {
            const rank = index + 1;
            return (
              <div
                key={model.id}
                className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-light-200/50 dark:hover:bg-dark-700/50"
              >
                <span
                  className={`w-6 text-center font-mono text-sm font-bold ${
                    RANK_COLORS[rank] || 'text-gray-400 dark:text-zinc-500'
                  }`}
                >
                  {rank}
                </span>
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: getProviderColor(model.provider) }}
                />
                <button
                  onClick={() => navigate(`/model/${encodeURIComponent(model.id)}`)}
                  className="min-w-0 flex-1 text-left"
                >
                  <span className="font-medium text-gray-900 dark:text-white hover:text-accent-light transition-colors">
                    {model.name}
                  </span>
                  <span className="ml-2 rounded bg-light-200 dark:bg-dark-700 px-1.5 py-0.5 font-mono text-[10px] text-gray-400 dark:text-zinc-500">
                    {model.provider}
                  </span>
                </button>
                <span className="shrink-0 font-mono text-sm text-gray-700 dark:text-zinc-300">
                  {formatTokens(model.weeklyTokens)} {t('tokens')}
                </span>
                <span
                  className={`shrink-0 font-mono text-xs font-medium ${
                    model.weeklyChange > 0 ? 'text-emerald-400' : model.weeklyChange < 0 ? 'text-red-400' : 'text-gray-400 dark:text-zinc-500'
                  }`}
                >
                  {formatChange(model.weeklyChange)}
                </span>
              </div>
            );
          })}
        </div>

        {leaderboard.length > 10 && (
          <div className="border-t border-light-300 dark:border-dark-700 px-5 py-3 text-center">
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-sm font-medium text-accent-light hover:text-accent transition-colors"
            >
              {showAll ? t('show_less') : `${t('show_more')} (${leaderboard.length - 10} ${t('models')})`}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}