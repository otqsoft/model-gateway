import { useMemo } from "react";
import { ChevronDown, Image as ImageIcon, Mic, Type, Video } from "lucide-react";
import type { Modality } from "@/types";
import { cn } from "@/lib/utils";

interface ModelSelectorProps {
  models: { id: string; name: string; provider: string; modalities: Modality[] }[];
  value: string;
  onChange: (id: string) => void;
}

const MODALITY_ICONS: Record<Modality, typeof Type> = {
  text: Type,
  image: ImageIcon,
  audio: Mic,
  video: Video,
};

export function ModelSelector({ models, value, onChange }: ModelSelectorProps) {
  const current = useMemo(
    () => models.find((m) => m.id === value),
    [models, value]
  );

  return (
    <div className="relative">
      <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-ink-dim mb-2">
        <span className="w-1.5 h-1.5 rounded-full bg-cyan animate-pulse-glow" />
        <span>Active Model</span>
      </div>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full appearance-none bg-obs-card border border-obs-border hover:border-obs-borderHi rounded-lg pl-4 pr-10 py-3 text-sm font-display font-semibold text-ink input-glow cursor-pointer transition-colors"
        >
          {models.map((m) => (
            <option key={m.id} value={m.id} className="bg-obs-panel text-ink">
              {m.name} · {m.provider}
            </option>
          ))}
        </select>
        <ChevronDown
          size={16}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-dim pointer-events-none"
        />
      </div>
      {current && (
        <div className="mt-2 flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-mono text-ink-dim uppercase">支持模态</span>
          {current.modalities.map((mod) => {
            const Icon = MODALITY_ICONS[mod];
            return (
              <span
                key={mod}
                className={cn(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono uppercase border",
                  "bg-cyan/5 border-cyan/30 text-cyan"
                )}
              >
                <Icon size={10} />
                {mod}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
