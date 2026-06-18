import { useRef, useState } from "react";
import { Image as ImageIcon, Upload, X } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import {
  estimateImageTokens,
  formatFileSize,
  readImageMeta,
} from "@/lib/tokenEstimate";
import { formatTokens } from "@/lib/costCalc";
import type { ImageItemInfo } from "@/types";
import { cn } from "@/lib/utils";

interface ImageInputCardProps {
  items: ImageItemInfo[];
  onChange: (items: ImageItemInfo[]) => void;
  totalTokens: number;
}

export function ImageInputCard({ items, onChange, totalTokens }: ImageInputCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setLoading(true);
    try {
      const newItems: ImageItemInfo[] = [];
      for (const file of Array.from(files)) {
        if (!file.type.startsWith("image/")) continue;
        try {
          const meta = await readImageMeta(file);
          const { tiles, tokens } = estimateImageTokens(meta.width, meta.height);
          newItems.push({
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            name: file.name,
            width: meta.width,
            height: meta.height,
            tiles,
            tokens,
            previewUrl: meta.previewUrl,
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
    const target = items.find((i) => i.id === id);
    if (target) URL.revokeObjectURL(target.previewUrl);
    onChange(items.filter((i) => i.id !== id));
  }

  return (
    <Card className="flex flex-col h-full">
      <CardHeader
        title="图片输入"
        subtitle="Image · GPT-4V 公式：85 + tiles × 170"
        icon={<ImageIcon size={16} />}
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
            {loading ? "解析中…" : "点击或拖拽图片到此处"}
          </div>
          <div className="text-[10px] text-ink-dim mt-0.5 font-mono">
            JPG · PNG · WEBP · GIF
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        {items.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-[280px] overflow-y-auto pr-1">
            {items.map((item) => (
              <div
                key={item.id}
                className="group relative rounded-lg overflow-hidden border border-obs-border bg-obs-panel/60"
              >
                <div className="aspect-square bg-obs-bg">
                  <img
                    src={item.previewUrl}
                    alt={item.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-obs-bg/95 to-transparent px-2 py-1.5">
                  <div className="text-[10px] text-ink truncate font-mono">
                    {item.name}
                  </div>
                  <div className="flex items-center justify-between text-[10px] font-mono">
                    <span className="text-ink-dim">
                      {item.width}×{item.height} · {item.tiles}t
                    </span>
                    <span className="text-cyan font-semibold">
                      {formatTokens(item.tokens)}
                    </span>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeItem(item.id);
                  }}
                  className="absolute top-1 right-1 w-5 h-5 rounded bg-obs-bg/80 backdrop-blur-sm flex items-center justify-center text-ink-dim hover:text-warn opacity-0 group-hover:opacity-100 transition-opacity"
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

export { formatFileSize };
