import { Coins, TrendingUp, Zap } from "lucide-react";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { formatCost, formatTokens } from "@/lib/costCalc";

interface SummaryBarProps {
  totalInputTokens: number;
  estimatedOutputTokens: number;
  inputCost: number;
  outputCost: number;
  totalCost: number;
  onOutputTokensChange: (n: number) => void;
}

export function SummaryBar({
  totalInputTokens,
  estimatedOutputTokens,
  inputCost,
  outputCost,
  totalCost,
  onOutputTokensChange,
}: SummaryBarProps) {
  return (
    <div className="rounded-2xl border border-obs-border bg-gradient-to-br from-obs-panel to-obs-card shadow-card overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr_1fr_1fr] divide-y lg:divide-y-0 lg:divide-x divide-obs-border">
        {/* 总 Token */}
        <div className="p-5 relative overflow-hidden">
          <div className="absolute -top-8 -right-8 w-32 h-32 bg-cyan/5 rounded-full blur-2xl" />
          <div className="relative">
            <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-cyan/70 mb-2">
              <Zap size={12} />
              <span>总输入 Token</span>
            </div>
            <AnimatedNumber
              value={totalInputTokens}
              className="font-display font-bold text-3xl md:text-4xl text-ink"
              format={(n) => formatTokens(Math.round(n))}
            />
            <div className="mt-1 text-xs text-ink-dim font-mono">
              {totalInputTokens.toLocaleString()} tokens
            </div>
          </div>
        </div>

        {/* 输入费用 */}
        <div className="p-5">
          <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-ink-dim mb-2">
            <TrendingUp size={12} />
            <span>输入费用</span>
          </div>
          <AnimatedNumber
            value={inputCost}
            className="font-display font-bold text-2xl text-ink"
            format={(n) => formatCost(n)}
          />
          <div className="mt-1 text-xs text-ink-dim font-mono">USD · 按各模态单价</div>
        </div>

        {/* 输出预估 */}
        <div className="p-5">
          <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-ink-dim mb-2">
            <TrendingUp size={12} />
            <span>输出费用</span>
          </div>
          <div className="flex items-center gap-2">
            <AnimatedNumber
              value={outputCost}
              className="font-display font-bold text-2xl text-ink"
              format={(n) => formatCost(n)}
            />
          </div>
          <div className="mt-2 flex items-center gap-2">
            <input
              type="number"
              min={0}
              value={estimatedOutputTokens}
              onChange={(e) =>
                onOutputTokensChange(Math.max(0, Number(e.target.value) || 0))
              }
              className="w-24 bg-obs-panel border border-obs-border rounded px-2 py-1 text-xs font-mono text-ink input-glow"
              placeholder="输出 Token"
            />
            <span className="text-[10px] text-ink-dim font-mono">预估输出</span>
          </div>
        </div>

        {/* 总费用 */}
        <div className="p-5 relative overflow-hidden bg-amber/[0.03]">
          <div className="absolute -top-8 -right-8 w-32 h-32 bg-amber/10 rounded-full blur-2xl" />
          <div className="relative">
            <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-amber/80 mb-2">
              <Coins size={12} />
              <span>总费用</span>
            </div>
            <AnimatedNumber
              value={totalCost}
              className="font-display font-bold text-3xl text-amber-glow drop-shadow-[0_0_12px_rgba(251,191,36,0.4)]"
              format={(n) => formatCost(n)}
            />
            <div className="mt-1 text-xs text-ink-dim font-mono">USD · 输入 + 输出</div>
          </div>
        </div>
      </div>
    </div>
  );
}
