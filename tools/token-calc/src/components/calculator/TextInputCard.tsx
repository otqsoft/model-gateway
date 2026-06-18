import { useMemo } from "react";
import { Type } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { estimateTextTokens } from "@/lib/tokenEstimate";
import { formatTokens } from "@/lib/costCalc";

interface TextInputCardProps {
  value: string;
  onChange: (v: string) => void;
}

export function TextInputCard({ value, onChange }: TextInputCardProps) {
  const { tokens, chars, words } = useMemo(
    () => estimateTextTokens(value),
    [value]
  );

  return (
    <Card className="flex flex-col h-full">
      <CardHeader
        title="文本输入"
        subtitle="Text · 支持中英文混合"
        icon={<Type size={16} />}
        action={
          <div className="text-right">
            <div className="font-mono text-cyan font-semibold text-lg leading-none">
              {formatTokens(tokens)}
            </div>
            <div className="text-[10px] text-ink-dim font-mono uppercase mt-0.5">
              tokens
            </div>
          </div>
        }
      />
      <div className="flex-1 p-4 flex flex-col gap-3 min-h-0">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="在此粘贴或输入文本内容…&#10;支持中英文混合，按字符类型分别估算 Token。"
          className="flex-1 min-h-[140px] resize-none bg-obs-panel/60 border border-obs-border rounded-lg p-3 text-sm text-ink font-sans input-glow placeholder:text-ink-dim/60"
        />
        <div className="grid grid-cols-3 gap-2">
          <Stat label="字符" value={chars} />
          <Stat label="词数" value={words} />
          <Stat label="Token" value={tokens} accent />
        </div>
      </div>
    </Card>
  );
}

function Stat({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div
      className={
        "rounded-lg border px-3 py-2 " +
        (accent
          ? "bg-cyan/5 border-cyan/30"
          : "bg-obs-panel/40 border-obs-border")
      }
    >
      <div className="text-[10px] font-mono uppercase text-ink-dim">{label}</div>
      <div
        className={
          "font-mono font-semibold text-sm mt-0.5 " +
          (accent ? "text-cyan" : "text-ink")
        }
      >
        {value.toLocaleString()}
      </div>
    </div>
  );
}
