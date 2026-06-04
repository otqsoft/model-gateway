import { LayoutGrid } from 'lucide-react';
import useRankingStore from '@/store/useRankingStore';
import { useLanguageStore } from '@/store/useLanguageStore';
import { formatTokens } from '@/utils/format';

export default function TopApps() {
  const { topApps } = useRankingStore();
  const { t } = useLanguageStore();

  return (
    <section id="top-apps" className="py-12">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
          <LayoutGrid className="h-5 w-5 text-accent" />
        </div>
        <div>
          <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">{t('top_apps')}</h2>
          <p className="text-sm text-gray-500 dark:text-zinc-400">{t('top_applications')}</p>
        </div>
      </div>

      <div className="rounded-xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800">
        <div className="divide-y divide-light-300 dark:divide-dark-700">
          {topApps.map((app, index) => (
            <div
              key={app.name}
              className="flex items-center gap-4 px-5 py-3 transition-colors hover:bg-light-200/50 dark:hover:bg-dark-700/50"
            >
              <span className="w-6 text-center font-mono text-sm font-bold text-gray-400 dark:text-zinc-500">
                {index + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium text-gray-900 dark:text-white">{app.name}</p>
                <p className="truncate text-xs text-gray-400 dark:text-zinc-500">{app.description}</p>
              </div>
              <span className="shrink-0 font-mono text-sm text-gray-700 dark:text-zinc-300">
                {formatTokens(app.tokens)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}