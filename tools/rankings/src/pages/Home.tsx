import { useEffect } from 'react';
import useRankingStore from '@/store/useRankingStore';
import { useLanguageStore } from '@/store/useLanguageStore';
import Navbar from '@/components/Navbar';
import TopModels from '@/components/TopModels';
import Leaderboard from '@/components/Leaderboard';
import MarketShare from '@/components/MarketShare';
import Benchmarks from '@/components/Benchmarks';
import FastestModels from '@/components/FastestModels';
import CategorySection from '@/components/CategorySection';
import ContextLengthSection from '@/components/ContextLengthSection';
import TopApps from '@/components/TopApps';
import { Code, Globe, Terminal, Wrench, Image, ImagePlus, Mic } from 'lucide-react';
import type { Model } from '@/store/useRankingStore';

export default function Home() {
  const { fetchAllData, loading, error } = useRankingStore();
  const { t } = useLanguageStore();

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  return (
    <div className="min-h-screen bg-light-50 dark:bg-dark-950">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-16 sm:px-6">
        {/* Hero */}
        <div className="py-12 text-center">
          <h1 className="font-heading text-4xl font-bold text-gray-900 dark:text-white sm:text-5xl">
            AI {t('model')} Rankings
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-gray-500 dark:text-zinc-400">
            {t('hero_subtitle')}
          </p>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-3">
              <div className="h-10 w-10 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
              <span className="text-sm text-gray-400 dark:text-zinc-500">{t('loading')}</span>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-300 bg-red-50 text-red-600 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-400 p-6 text-center">
            {error}
          </div>
        )}

        {!loading && !error && (
          <>
            <TopModels />
            <Leaderboard />
            <MarketShare />
            <Benchmarks />
            <FastestModels />
            <CategorySection
              sectionId="categories"
              titleKey="categories"
              subtitleKey="categories_desc"
              icon={Code}
              filterFn={(m: Model) => m.category === 'programming'}
            />
            <CategorySection
              sectionId="languages"
              titleKey="languages"
              subtitleKey="languages_desc"
              icon={Globe}
              filterFn={(m: Model) => m.architecture.input_modalities.includes('text')}
            />
            <CategorySection
              sectionId="programming"
              titleKey="programming"
              subtitleKey="programming_desc"
              icon={Terminal}
              filterFn={(m: Model) => m.category === 'programming'}
            />
            <ContextLengthSection />
            <CategorySection
              sectionId="tool-calls"
              titleKey="tool_calls"
              subtitleKey="tool_calls_desc"
              icon={Wrench}
              filterFn={(m: Model) => m.hasToolCalls}
            />
            <CategorySection
              sectionId="images"
              titleKey="images"
              subtitleKey="images_desc"
              icon={Image}
              filterFn={(m: Model) => m.hasImageInput}
            />
            <CategorySection
              sectionId="image-output"
              titleKey="image_output"
              subtitleKey="image_output_desc"
              icon={ImagePlus}
              filterFn={(m: Model) => m.hasImageOutput}
            />
            <CategorySection
              sectionId="audio-input"
              titleKey="audio_input"
              subtitleKey="audio_input_desc"
              icon={Mic}
              filterFn={(m: Model) => m.hasAudioInput}
            />
            <TopApps />
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-light-300 dark:border-dark-700 py-8 text-center text-sm text-gray-400 dark:text-zinc-500">
        AI Model Rankings — {t('powered_by')} OpenRouter
      </footer>
    </div>
  );
}