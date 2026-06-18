import { useMemo, useState } from "react";
import { Download, History, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { useHistoryStore } from "@/store/useHistoryStore";
import { formatCost, formatTokens } from "@/lib/costCalc";

export default function HistoryPage() {
  const records = useHistoryStore((s) => s.records);
  const loading = useHistoryStore((s) => s.loading);
  const removeRecord = useHistoryStore((s) => s.removeRecord);
  const clearAll = useHistoryStore((s) => s.clearAll);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const totals = useMemo(() => {
    return records.reduce(
      (acc, r) => {
        acc.totalCost += r.totalCost;
        acc.totalTokens += r.totalInputTokens;
        return acc;
      },
      { totalCost: 0, totalTokens: 0 }
    );
  }, [records]);

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function exportJSON() {
    const target =
      selected.size > 0 ? records.filter((r) => selected.has(r.id)) : records;
    if (target.length === 0) return;
    const blob = new Blob([JSON.stringify(target, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `tokenlab-history-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <PageHeader
        title="历史记录"
        subtitle="本地保存的计算历史。最多保留 200 条，可单选或全部导出为 JSON。"
        actions={
          <>
            <Button
              variant="ghost"
              size="sm"
              icon={<Download size={14} />}
              onClick={exportJSON}
              disabled={records.length === 0}
            >
              导出 {selected.size > 0 ? `(${selected.size})` : "全部"}
            </Button>
            <Button
              variant="danger"
              size="sm"
              icon={<Trash2 size={14} />}
              onClick={clearAll}
              disabled={records.length === 0}
            >
              清空
            </Button>
          </>
        }
      />

      <div className="px-6 md:px-10 py-6 space-y-4">
        {loading ? (
          <div className="py-20 text-center text-ink-muted">正在加载历史记录…</div>
        ) : (
        <>
        {/* 汇总卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SummaryStat label="记录数" value={records.length.toString()} />
          <SummaryStat
            label="累计 Token"
            value={formatTokens(totals.totalTokens)}
            accent="cyan"
          />
          <SummaryStat
            label="累计费用"
            value={formatCost(totals.totalCost)}
            accent="amber"
          />
          <SummaryStat
            label="选中"
            value={selected.size.toString()}
          />
        </div>

        {/* 记录表格 */}
        {records.length === 0 ? (
          <div className="rounded-xl border border-obs-border bg-obs-card/40 py-20 text-center">
            <History size={32} className="mx-auto text-ink-dim mb-3" />
            <div className="text-sm text-ink-muted">暂无历史记录</div>
            <div className="text-xs text-ink-dim mt-1">
              在「计算工作台」保存计算结果后将显示在此
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-obs-border bg-obs-card/40 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[800px]">
                <thead>
                  <tr className="bg-obs-panel/60 text-[10px] font-mono uppercase text-ink-dim">
                    <th className="px-3 py-3 w-10"></th>
                    <th className="text-left px-3 py-3 font-medium">时间</th>
                    <th className="text-left px-3 py-3 font-medium">模型</th>
                    <th className="text-right px-3 py-3 font-medium">文本</th>
                    <th className="text-right px-3 py-3 font-medium">图片</th>
                    <th className="text-right px-3 py-3 font-medium">语音</th>
                    <th className="text-right px-3 py-3 font-medium">视频</th>
                    <th className="text-right px-3 py-3 font-medium">总输入</th>
                    <th className="text-right px-3 py-3 font-medium">输出</th>
                    <th className="text-right px-3 py-3 font-medium">费用</th>
                    <th className="text-right px-3 py-3 font-medium w-12"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-obs-border">
                  {records.map((r) => {
                    const date = new Date(r.timestamp);
                    const isSelected = selected.has(r.id);
                    return (
                      <tr
                        key={r.id}
                        className={
                          isSelected
                            ? "bg-cyan/5 hover:bg-cyan/10"
                            : "hover:bg-obs-panel/30"
                        }
                      >
                        <td className="px-3 py-2.5 text-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelect(r.id)}
                            className="w-3.5 h-3.5 accent-cyan"
                          />
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="text-xs text-ink font-mono">
                            {date.toLocaleDateString("zh-CN")}
                          </div>
                          <div className="text-[10px] text-ink-dim font-mono">
                            {date.toLocaleTimeString("zh-CN", { hour12: false })}
                          </div>
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="text-xs text-ink font-display font-medium">
                            {r.modelName}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-xs text-ink-muted">
                          {r.textTokens > 0 ? formatTokens(r.textTokens) : "—"}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-xs text-ink-muted">
                          {r.imageTokens > 0 ? formatTokens(r.imageTokens) : "—"}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-xs text-ink-muted">
                          {r.audioTokens > 0 ? formatTokens(r.audioTokens) : "—"}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-xs text-ink-muted">
                          {r.videoTokens > 0 ? formatTokens(r.videoTokens) : "—"}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-xs text-cyan font-semibold">
                          {formatTokens(r.totalInputTokens)}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-xs text-ink-muted">
                          {formatTokens(r.estimatedOutputTokens)}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-xs text-amber font-semibold">
                          {formatCost(r.totalCost)}
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          <button
                            onClick={() => removeRecord(r.id)}
                            className="w-6 h-6 rounded flex items-center justify-center text-ink-dim hover:text-warn hover:bg-warn/10 transition-colors"
                          >
                            <Trash2 size={12} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
        </>
        )}
      </div>
    </div>
  );
}

function SummaryStat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "cyan" | "amber";
}) {
  return (
    <div className="rounded-xl border border-obs-border bg-obs-card/40 px-4 py-3">
      <div className="text-[10px] font-mono uppercase text-ink-dim tracking-wider">
        {label}
      </div>
      <div
        className={
          "font-display font-bold text-xl mt-1 " +
          (accent === "cyan"
            ? "text-cyan"
            : accent === "amber"
            ? "text-amber"
            : "text-ink")
        }
      >
        {value}
      </div>
    </div>
  );
}
