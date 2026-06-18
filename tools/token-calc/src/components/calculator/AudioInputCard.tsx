import { useRef, useState } from "react";
import { Mic, Upload, X } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import {
  estimateAudioTokens,
  formatDuration,
  formatFileSize,
  readMediaDuration,
} from "@/lib/tokenEstimate";
import { formatTokens } from "@/lib/costCalc";
import type { MediaItemInfo } from "@/types";
import { cn } from "@/lib/utils";

interface AudioInputCardProps {
  items: MediaItemInfo[];
  onChange: (items: MediaItemInfo[]) => void;
  totalTokens: number;
}

export function AudioInputCard({ items, onChange, totalTokens }: AudioInputCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setLoading(true);
    try {
      const newItems: MediaItemInfo[] = [];
      for (const file of Array.from(files)) {
        if (!file.type.startsWith("audio/")) continue;
        try {
          const durationSec = await readMediaDuration(file);
          const tokens = estimateAudioTokens(durationSec);
          newItems.push({
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            name: file.name,
            durationSec,
            tokens,
            sizeLabel: formatFileSize(file.size),
          });
        } catch {
          // 跳过失败文件
        }
      }
      onChange([...items, ...newItems]);
    } finally {
      setLoading(false);
    }
  }

  function removeItem(id: string) {
    onChange(items.filter((i) => i.id !== id));
  }

  return (
    <Card className="flex flex-col h-full">
      <CardHeader
        title="语音输入"
        subtitle="Audio · Whisper 公式：100 tokens/min"
        icon={<Mic size={16} />}
        action={
          <div className="text-right">
            <div className="font-mono text-cyan font-semibold text-lg leading-none">
              {formatTokens(totalTokens)}
            </div>
            <div className="text-[10px] text-ink-dim font-mono uppercase mt-0.5">
              tokens
            </div>
          </div>
        }
      />
      <div className="flex-1 p-4 flex flex-col gap-3 min-h-0">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-all",
            dragging
              ? "border-cyan bg-cyan/5"
              : "border-obs-border hover:border-obs-borderHi hover:bg-obs-panel/40"
          )}
        >
          <Upload size={20} className="mx-auto text-ink-dim mb-1" />
          <div className="text-xs text-ink-muted">
            {loading ? "解析中…" : "点击或拖拽音频到此处"}
          </div>
          <div className="text-[10px] text-ink-dim mt-0.5 font-mono">
            MP3 · WAV · M4A · OGG
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="audio/*"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        {items.length > 0 && (
          <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
            {items.map((item) => (
              <div
                key={item.id}
                className="group flex items-center gap-3 rounded-lg border border-obs-border bg-obs-panel/60 px-3 py-2"
              >
                <div className="w-8 h-8 rounded bg-cyan/10 border border-cyan/30 flex items-center justify-center shrink-0">
                  <Mic size={14} className="text-cyan" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-ink truncate font-mono">{item.name}</div>
                  <div className="flex items-center gap-3 text-[10px] font-mono text-ink-dim mt-0.5">
                    <span>时长 {formatDuration(item.durationSec)}</span>
                    <span>{item.sizeLabel}</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="font-mono text-cyan font-semibold text-sm">
                    {formatTokens(item.tokens)}
                  </div>
                  <div className="text-[10px] text-ink-dim font-mono">tokens</div>
                </div>
                <button
                  onClick={() => removeItem(item.id)}
                  className="w-6 h-6 rounded flex items-center justify-center text-ink-dim hover:text-warn opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
