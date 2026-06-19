import { useMemo, useRef, useState } from "react";
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

const MODALITY_LABELS: Record<Modality, string> = {
  text: "文本",
  image: "图片",
  audio: "语音",
  video: "视频",
};

export function ModelSelector({ models, value, onChange }: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const current = useMemo(
    () => models.find((m) => m.id === value),
    [models, value]
  );

  function handleSelect(id: string) {
    onChange(id);
    setOpen(false);
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-ink-dim mb-2">
        <span className="w-1.5 h-1.5 rounded-full bg-cyan animate-pulse-glow" />
        <span>Active Model</span>
      </div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-center justify-between rounded-lg pl-4 pr-3 py-3 text-sm font-display font-semibold text-ink cursor-pointer transition-colors outline-none",
          open ? "ring-2 ring-cyan/30" : "hover:bg-obs-panel/40"
        )}
      >
        <span>{current ? current.name : "选择模型"}</span>
        <div className="flex items-center gap-1.5">
          {current && current.modalities.map((mod) => {
            const Icon = MODALITY_ICONS[mod];
            return (
              <span
                key={mod}
                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase border border-obs-borderHi text-ink-dim"
              >
                <Icon size={9} />
                {MODALITY_LABELS[mod]}
              </span>
            );
          })}
          <ChevronDown
            size={16}
            className={cn("text-ink-dim transition-transform duration-200", open && "rotate-180")}
          />
        </div>
      </button>

      {open && (
        <>
          {/* 背景遮罩 */}
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div
            className="absolute left-0 right-0 top-full mt-1 z-50 rounded-lg border border-obs-border bg-obs-card shadow-lg overflow-hidden"
          >
            {models.map((m) => {
              const active = m.id === value;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => handleSelect(m.id)}
                  className={cn(
                    "w-full flex items-center justify-between gap-2 px-4 py-2.5 text-left transition-colors",
                    active
                      ? "bg-cyan/10 text-cyan"
                      : "text-ink hover:bg-obs-panel/60"
                  )}
                >
                  <span className="text-sm font-display font-semibold truncate">{m.name}</span>
                  <div className="flex items-center gap-1 shrink-0">
                    {m.modalities.map((mod) => {
                      const Icon = MODALITY_ICONS[mod];
                      return (
                        <span
                          key={mod}
                          className={cn(
                            "inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-mono uppercase border",
                            active
                              ? "border-cyan/30 text-cyan"
                              : "border-obs-borderHi text-ink-dim"
                          )}
                        >
                          <Icon size={9} />
                          {MODALITY_LABELS[mod]}
                        </span>
                      );
                    })}
                  </div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
