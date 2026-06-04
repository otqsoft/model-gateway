import type { Model } from '@/store/useRankingStore';
import { formatPrice, formatContextLength, getProviderColor, formatTokens, formatChange } from '@/utils/format';
import { Wrench, Image, ImagePlus, Mic, ArrowLeft, Hash, BarChart3 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useLanguageStore } from '@/store/useLanguageStore';

interface ModelCardProps {
  model: Model;
}

function InfoCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-light-300 bg-light-200 dark:border-dark-700 dark:bg-dark-700 p-4">
      <p className="mb-1 text-xs text-gray-400 dark:text-zinc-500">{label}</p>
      <p className="font-mono text-lg font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}

function CapabilityTag({ active, icon: Icon, label }: { active: boolean; icon: React.ElementType; label: string }) {
  if (!active) return null;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg bg-accent/10 px-3 py-1.5 text-sm text-accent-light">
      <Icon className="h-4 w-4" />
      {label}
    </span>
  );
}

export default function ModelCard({ model }: ModelCardProps) {
  const navigate = useNavigate();
  const { t } = useLanguageStore();

  const avgBenchmark = Math.round(
    (model.benchmarks.math + model.benchmarks.coding + model.benchmarks.reasoning + model.benchmarks.chat) / 4
  );

  return (
    <div className="overflow-hidden rounded-2xl border border-light-300 dark:border-dark-700 bg-white dark:bg-dark-800">
      <div className="h-1 bg-gradient-to-r from-accent via-accent-light to-accent-dark" />

      <div className="p-6">
        <button
          onClick={() => navigate('/')}
          className="mb-4 flex items-center gap-1 text-sm text-gray-500 dark:text-zinc-400 transition-colors hover:text-gray-900 dark:hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('back')}
        </button>

        <div className="mb-4 flex items-center gap-3">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: getProviderColor(model.provider) }}
          />
          <h1 className="font-heading text-2xl font-bold text-gray-900 dark:text-white">
            {model.name}
          </h1>
          <span className="rounded-lg bg-light-200 dark:bg-dark-700 px-2.5 py-1 font-mono text-sm text-gray-500 dark:text-zinc-400">
            {model.provider}
          </span>
        </div>

        {model.description && (
          <p className="mb-6 text-sm leading-relaxed text-gray-500 dark:text-zinc-400">
            {model.description}
          </p>
        )}

        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
          <InfoCard label={t('input_price')} value={formatPrice(model.inputPrice)} />
          <InfoCard label={t('output_price')} value={formatPrice(model.outputPrice)} />
          <InfoCard label={t('context_length')} value={formatContextLength(model.context_length)} />
          <InfoCard label={t('speed')} value={`${model.speed} tok/s`} />
          <InfoCard label={t('average') + ' ' + t('benchmarks')} value={String(avgBenchmark)} />
          <InfoCard label={t('weekly_tokens')} value={formatTokens(model.weeklyTokens)} />
        </div>

        {/* Weekly Change */}
        <div className="mb-6">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400 dark:text-zinc-500">{t('weekly_change')}:</span>
            <span
              className={`font-mono text-sm font-medium ${
                model.weeklyChange > 0 ? 'text-emerald-400' : model.weeklyChange < 0 ? 'text-red-400' : 'text-zinc-400'
              }`}
            >
              {formatChange(model.weeklyChange)}
            </span>
          </div>
        </div>

        {/* Benchmarks */}
        <div className="mb-6">
          <h3 className="mb-3 flex items-center gap-2 font-heading text-sm font-semibold text-gray-700 dark:text-zinc-300">
            <BarChart3 className="h-4 w-4 text-accent" />
            {t('benchmarks')}
          </h3>
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <span className="text-gray-400 dark:text-zinc-500">{t('math')}</span>
              <p className="font-mono text-gray-900 dark:text-white">{model.benchmarks.math}</p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-zinc-500">{t('coding')}</span>
              <p className="font-mono text-gray-900 dark:text-white">{model.benchmarks.coding}</p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-zinc-500">{t('reasoning')}</span>
              <p className="font-mono text-gray-900 dark:text-white">{model.benchmarks.reasoning}</p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-zinc-500">{t('chat')}</span>
              <p className="font-mono text-gray-900 dark:text-white">{model.benchmarks.chat}</p>
            </div>
          </div>
        </div>

        {/* Capabilities */}
        <div className="mb-6">
          <h3 className="mb-3 font-heading text-sm font-semibold text-gray-700 dark:text-zinc-300">
            {t('capabilities')}
          </h3>
          <div className="flex flex-wrap gap-2">
            <CapabilityTag active={model.hasToolCalls} icon={Wrench} label={t('tool_calls')} />
            <CapabilityTag active={model.hasImageInput} icon={Image} label={t('images')} />
            <CapabilityTag active={model.hasImageOutput} icon={ImagePlus} label={t('image_output')} />
            <CapabilityTag active={model.hasAudioInput} icon={Mic} label={t('audio_input')} />
          </div>
        </div>

        {/* Details */}
        <div className="mb-6">
          <h3 className="mb-3 font-heading text-sm font-semibold text-gray-700 dark:text-zinc-300">
            {t('model_details')}
          </h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400 dark:text-zinc-500">{t('max_completion_tokens')}</span>
              <p className="font-mono text-gray-900 dark:text-white">
                {model.top_provider?.max_completion_tokens
                  ? model.top_provider.max_completion_tokens.toLocaleString()
                  : 'N/A'}
              </p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-zinc-500">{t('modality')}</span>
              <p className="font-mono text-gray-900 dark:text-white">
                {model.architecture?.modality || 'N/A'}
              </p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-zinc-500">{t('input_modalities')}</span>
              <p className="font-mono text-gray-900 dark:text-white">
                {model.architecture?.input_modalities?.join(', ') || 'N/A'}
              </p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-zinc-500">{t('output_modalities')}</span>
              <p className="font-mono text-gray-900 dark:text-white">
                {model.architecture?.output_modalities?.join(', ') || 'N/A'}
              </p>
            </div>
          </div>
        </div>

        {model.supported_parameters && model.supported_parameters.length > 0 && (
          <div>
            <h3 className="mb-3 font-heading text-sm font-semibold text-gray-700 dark:text-zinc-300">
              {t('supported_parameters')}
            </h3>
            <div className="flex flex-wrap gap-2">
              {model.supported_parameters.map((param) => (
                <span
                  key={param}
                  className="inline-flex items-center gap-1 rounded-md bg-light-200 dark:bg-dark-700 px-2 py-1 font-mono text-xs text-gray-500 dark:text-zinc-400"
                >
                  <Hash className="h-3 w-3" />
                  {param}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}