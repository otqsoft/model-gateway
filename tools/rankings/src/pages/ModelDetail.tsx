import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import Navbar from '@/components/Navbar';
import ModelCard from '@/components/ModelCard';
import type { Model } from '@/store/useRankingStore';
import { useLanguageStore } from '@/store/useLanguageStore';

const API_BASE = import.meta.env.DEV ? '/api' : `${import.meta.env.BASE_URL}api`;

export default function ModelDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useLanguageStore();
  const [model, setModel] = useState<Model | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const fetchModel = async () => {
      try {
        const res = await fetch(`${API_BASE}/models/${encodeURIComponent(id)}`);
        if (!res.ok) throw new Error(t('failed_to_load_data'));
        const data = await res.json();
        setModel(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : t('failed_to_load_data'));
      } finally {
        setLoading(false);
      }
    };
    fetchModel();
  }, [id, t]);

  return (
    <div className="min-h-screen bg-light-50 dark:bg-dark-950">
      <Navbar />
      <main className="mx-auto max-w-4xl px-4 pt-20 pb-16 sm:px-6">
        <button
          onClick={() => navigate('/')}
          className="mb-8 flex items-center gap-2 text-sm text-gray-500 dark:text-zinc-400 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('back')}
        </button>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-3">
              <div className="h-10 w-10 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
              <span className="text-sm text-gray-400 dark:text-zinc-500">{t('loading')}</span>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-300 bg-red-50 p-6 text-center text-red-600 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-400">
            {error}
          </div>
        )}

        {!loading && !error && model && <ModelCard model={model} />}
      </main>
    </div>
  );
}