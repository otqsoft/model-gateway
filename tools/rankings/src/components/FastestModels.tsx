import { Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import useRankingStore from '@/store/useRankingStore';
import { useLanguageStore } from '@/store/useLanguageStore';
import { getProviderColor, formatTokens } from '@/utils/format';

export default function FastestModels() {
  const { fastestModels } = useRankingStore();
  const { t } = useLanguageStore();
  const navigate = useNavigate();
  const [showAll, setShowAll] = useState(false);
  const displayList = showAll ? fastestModels.slice(0, 20) : fastestModels.slice(0, 10);
  const maxSpeed = displayList.length > 0 ? displayList[0].speed : 200;

  return (
    <section id="fastest" className="py-12">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
          <Zap className="h-5 w-5 text-accent" />
        </div>
        <div>
          <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">{t('fastest_models')}</h2>
          <p className="text-sm text-gray-500 dark:text-zinc-400">{t('highest_output_speed')}</p>
        </div>
      </div>

      <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800">
        <div className="divide-y divide-light-300 dark:divide-dark-700">
          {displayList.map((model, index) => {
            const pct = Math.min(100, (model.speed / maxSpeed) * 100);
            return (
              <div
                key={model.id}
                className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-light-200/50 dark:hover:bg-dark-700/50"
              >
                <span className="w-6 text-center font-mono text-sm font-bold text-gray-400 dark:text-zinc-500">
                  {index + 1}
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
                <div className="flex items-center gap-3">
                  <div className="h-1.5 w-24 overflow-hidden rounded-full bg-light-200 dark:bg-dark-700">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="shrink-0 font-mono text-xs text-gray-700 dark:text-zinc-300">
                    {model.speed} {t('tokens_sec')}
                  </span>
                  <span className="shrink-0 font-mono text-xs text-gray-400 dark:text-zinc-500">
                    {formatTokens(model.weeklyTokens)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {fastestModels.length > 10 && (
          <div className="border-t border-light-300 dark:border-dark-700 px-5 py-3 text-center">
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-sm font-medium text-accent-light hover:text-accent transition-colors"
            >
              {showAll ? t('show_less') : `${t('show_more')} (${fastestModels.length - 10} ${t('models')})`}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}