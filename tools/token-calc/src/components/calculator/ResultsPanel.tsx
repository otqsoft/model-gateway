import { Image as ImageIcon, Mic, Save, Type, Video } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { formatCost, formatTokens } from "@/lib/costCalc";
import type { CostBreakdown } from "@/lib/costCalc";
import type { TokenBreakdown } from "@/types";

interface ResultsPanelProps {
  breakdown: TokenBreakdown;
  cost: CostBreakdown;
  totalInputTokens: number;
  onSave: () => void;
}

export function ResultsPanel({
  breakdown,
  cost,
  totalInputTokens,
  onSave,
}: ResultsPanelProps) {
  const rows = [
    {
      icon: Type,
      label: "文本",
      tokens: breakdown.textTokens,
      cost: cost.textCost,
      color: "text-cyan",
    },
    {
      icon: ImageIcon,
      label: "图片",
      tokens: breakdown.imageTokens,
      cost: cost.imageCost,
      color: "text-cyan",
    },
    {
      icon: Mic,
      label: "语音",
      tokens: breakdown.audioTokens,
      cost: cost.audioCost,
      color: "text-cyan",
    },
    {
      icon: Video,
      label: "视频",
      tokens: breakdown.videoTokens,
      cost: cost.videoCost,
      color: "text-amber",
    },
  ];

  return (
    <Card>
      <CardHeader
        title="费用明细"
        subtitle="Cost Breakdown · 按模态分项"
        icon={<Save size={16} />}
        action={
          <Button variant="primary" size="sm" icon={<Save size={14} />} onClick={onSave}>
            保存到历史
          </Button>
        }
      />
      <div className="p-4">
        <div className="overflow-hidden rounded-lg border border-obs-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-obs-panel/60 text-[10px] font-mono uppercase text-ink-dim">
                <th className="text-left px-4 py-2.5 font-medium">模态</th>
                <th className="text-right px-4 py-2.5 font-medium">Token</th>
                <th className="text-right px-4 py-2.5 font-medium">费用 (USD)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-obs-border">
              {rows.map((row) => {
                const Icon = row.icon;
                const active = row.tokens > 0 || row.cost > 0;
                return (
                  <tr
                    key={row.label}
                    className={active ? "bg-obs-card/40" : "opacity-40"}
                  >
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <Icon size={14} className={row.color} />
                        <span className="text-ink">{row.label}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-ink">
                      {formatTokens(row.tokens)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-ink">
                      {formatCost(row.cost)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="bg-obs-panel/80 border-t-2 border-obs-borderHi">
                <td className="px-4 py-3 font-display font-semibold text-ink">
                  输入合计
                </td>
                <td className="px-4 py-3 text-right font-mono font-semibold text-cyan">
                  {formatTokens(totalInputTokens)}
                </td>
                <td className="px-4 py-3 text-right font-mono font-semibold text-cyan">
                  {formatCost(cost.inputCost)}
                </td>
              </tr>
              <tr className="bg-amber/[0.04] border-t border-obs-border">
                <td className="px-4 py-3 font-display font-semibold text-ink">
                  输出预估
                </td>
                <td className="px-4 py-3 text-right font-mono text-ink-muted">—</td>
                <td className="px-4 py-3 text-right font-mono font-semibold text-amber">
                  {formatCost(cost.outputCost)}
                </td>
              </tr>
              <tr className="bg-amber/[0.08] border-t border-obs-border">
                <td className="px-4 py-3 font-display font-bold text-ink" colSpan={2}>
                  <div className="flex items-center justify-between">
                    <span>总计</span>
                    <span className="text-[10px] font-mono text-ink-dim uppercase">
                      input + output
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-mono font-bold text-amber-glow text-base">
                  {formatCost(cost.totalCost)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </Card>
  );
}
