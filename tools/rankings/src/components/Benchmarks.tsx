import { useState } from 'react';
import { BarChart3 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import useRankingStore from '@/store/useRankingStore';
import { useLanguageStore } from '@/store/useLanguageStore';
import { getProviderColor } from '@/utils/format';

function ScoreBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct = Math.min(100, (value / max) * 100);
  const color =
    value >= 85 ? 'bg-emerald-500' : value >= 70 ? 'bg-yellow-500' : value >= 50 ? 'bg-orange-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-light-200 dark:bg-dark-700">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-gray-500 dark:text-zinc-400">{value}</span>
    </div>
  );
}

export default function Benchmarks() {
  const { benchmarkModels } = useRankingStore();
  const { t } = useLanguageStore();
  const navigate = useNavigate();
  const [showAll, setShowAll] = useState(false);
  const displayList = showAll ? benchmarkModels.slice(0, 20) : benchmarkModels.slice(0, 10);

  return (
    <section id="benchmarks" className="py-12">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
          <BarChart3 className="h-5 w-5 text-accent" />
        </div>
        <div>
          <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">{t('benchmarks')}</h2>
          <p className="text-sm text-gray-500 dark:text-zinc-400">{t('model_performance')}</p>
        </div>
      </div>

      <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-light-300 dark:border-dark-700 text-left text-xs text-gray-400 dark:text-zinc-500">
              <th className="px-5 py-3 font-medium">#</th>
              <th className="px-5 py-3 font-medium">{t('model')}</th>
              <th className="px-5 py-3 font-medium">{t('math')}</th>
              <th className="px-5 py-3 font-medium">{t('coding')}</th>
              <th className="px-5 py-3 font-medium">{t('reasoning')}</th>
              <th className="px-5 py-3 font-medium">{t('chat')}</th>
              <th className="px-5 py-3 font-medium">{t('average')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-light-300 dark:divide-dark-700">
            {displayList.map((model, index) => {
              const avg = Math.round(
                (model.benchmarks.math + model.benchmarks.coding + model.benchmarks.reasoning + model.benchmarks.chat) / 4
              );
              return (
                <tr key={model.id} className="transition-colors hover:bg-light-200/50 dark:hover:bg-dark-700/50">
                  <td className="px-5 py-3 font-mono text-xs text-gray-400 dark:text-zinc-500">{index + 1}</td>
                  <td className="px-5 py-3">
                    <button
                      onClick={() => navigate(`/model/${encodeURIComponent(model.id)}`)}
                      className="flex items-center gap-2 text-left"
                    >
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ backgroundColor: getProviderColor(model.provider) }}
                      />
                      <span className="font-medium text-gray-900 dark:text-white hover:text-accent-light transition-colors">
                        {model.name}
                      </span>
                    </button>
                  </td>
                  <td className="px-5 py-3"><ScoreBar value={model.benchmarks.math} /></td>
                  <td className="px-5 py-3"><ScoreBar value={model.benchmarks.coding} /></td>
                  <td className="px-5 py-3"><ScoreBar value={model.benchmarks.reasoning} /></td>
                  <td className="px-5 py-3"><ScoreBar value={model.benchmarks.chat} /></td>
                  <td className="px-5 py-3 font-mono text-sm font-bold text-gray-900 dark:text-white">{avg}</td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {benchmarkModels.length > 10 && (
          <div className="border-t border-light-300 dark:border-dark-700 px-5 py-3 text-center">
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-sm font-medium text-accent-light hover:text-accent transition-colors"
            >
              {showAll ? t('show_less') : `${t('show_more')} (${benchmarkModels.length - 10} ${t('models')})`}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}