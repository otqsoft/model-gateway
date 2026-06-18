import { useEffect, useState } from "react";
import { Image as ImageIcon, Mic, Plus, RotateCcw, Type, Video } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { useModelStore } from "@/store/useModelStore";
import type { Modality, ModelConfig } from "@/types";
import { cn } from "@/lib/utils";

const MODALITIES: Modality[] = ["text", "image", "audio", "video"];
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

export default function Models() {
  const models = useModelStore((s) => s.models);
  const loading = useModelStore((s) => s.loading);
  const addModel = useModelStore((s) => s.addModel);
  const updateModel = useModelStore((s) => s.updateModel);
  const removeModel = useModelStore((s) => s.removeModel);
  const toggleEnabled = useModelStore((s) => s.toggleEnabled);
  const resetToBuiltin = useModelStore((s) => s.resetToBuiltin);

  const [editing, setEditing] = useState<ModelConfig | null>(null);
  const [creating, setCreating] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);

  return (
    <div>
      <PageHeader
        title="模型管理"
        subtitle="配置常用大模型的模态支持与计费规则。内置模型不可删除，可自定义新增模型。"
        actions={
          <>
            <Button
              variant="ghost"
              size="sm"
              icon={<RotateCcw size={14} />}
              onClick={() => setConfirmReset(true)}
            >
              重置
            </Button>
            <Button
              variant="primary"
              size="sm"
              icon={<Plus size={14} />}
              onClick={() => setCreating(true)}
            >
              新增模型
            </Button>
          </>
        }
      />

      <div className="px-6 md:px-10 py-6">
        {loading ? (
          <div className="py-20 text-center text-ink-muted">正在加载模型数据…</div>
        ) : (
        <div className="rounded-xl border border-obs-border bg-obs-card/40 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-obs-panel/60 text-[10px] font-mono uppercase text-ink-dim">
                <th className="text-left px-4 py-3 font-medium">模型</th>
                <th className="text-left px-4 py-3 font-medium">模态</th>
                <th className="text-right px-4 py-3 font-medium">文本输入价</th>
                <th className="text-right px-4 py-3 font-medium">文本输出价</th>
                <th className="text-right px-4 py-3 font-medium">音频价</th>
                <th className="text-right px-4 py-3 font-medium">视频价</th>
                <th className="text-center px-4 py-3 font-medium">启用</th>
                <th className="text-right px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-obs-border">
              {models.map((m) => (
                <tr key={m.id} className="hover:bg-obs-panel/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-display font-semibold text-ink">{m.name}</div>
                    <div className="text-[10px] font-mono text-ink-dim mt-0.5">
                      {m.provider}
                      {m.builtin && " · BUILTIN"}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 flex-wrap">
                      {MODALITIES.map((mod) => {
                        const active = m.modalities.includes(mod);
                        const Icon = MODALITY_ICONS[mod];
                        return (
                          <span
                            key={mod}
                            title={MODALITY_LABELS[mod]}
                            className={cn(
                              "w-6 h-6 rounded flex items-center justify-center border",
                              active
                                ? "bg-cyan/10 border-cyan/30 text-cyan"
                                : "bg-obs-panel/40 border-obs-border text-ink-dim/40"
                            )}
                          >
                            <Icon size={12} />
                          </span>
                        );
                      })}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-ink">
                    ${m.pricing.text.inputPer1M}/M
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-ink">
                    ${m.pricing.text.outputPer1M}/M
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-ink">
                    {m.pricing.audio.perMinute > 0
                      ? `$${m.pricing.audio.perMinute}/min`
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-ink">
                    {m.pricing.video.perMinute > 0
                      ? `$${m.pricing.video.perMinute}/min`
                      : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleEnabled(m.id)}
                      className={cn(
                        "block mx-auto w-10 h-5 rounded-full relative transition-colors",
                        m.enabled ? "bg-cyan/80" : "bg-obs-border"
                      )}
                    >
                      <span
                        className={cn(
                          "absolute top-0.5 w-4 h-4 rounded-full bg-obs-bg transition-transform",
                          m.enabled ? "translate-x-5" : "translate-x-0.5"
                        )}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditing(m)}
                        className="px-2 py-1 rounded text-[11px] font-mono text-cyan hover:bg-cyan/10 transition-colors"
                      >
                        编辑
                      </button>
                      {!m.builtin && (
                        <button
                          onClick={() => removeModel(m.id)}
                          className="px-2 py-1 rounded text-[11px] font-mono text-warn hover:bg-warn/10 transition-colors"
                        >
                          删除
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </div>

      {/* 编辑/新增弹窗 */}
      {(editing || creating) && (
        <ModelEditor
          model={editing}
          onClose={() => {
            setEditing(null);
            setCreating(false);
          }}
          onSave={(data) => {
            if (editing) {
              updateModel(editing.id, data);
            } else {
              addModel({ ...data, enabled: true });
            }
            setEditing(null);
            setCreating(false);
          }}
        />
      )}

      {/* 重置确认 */}
      <Modal
        open={confirmReset}
        onClose={() => setConfirmReset(false)}
        title="重置模型库"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmReset(false)}>
              取消
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                resetToBuiltin();
                setConfirmReset(false);
              }}
            >
              确认重置
            </Button>
          </>
        }
      >
        <p className="text-sm text-ink-muted">
          此操作将丢弃所有自定义模型与修改，恢复为内置模型库。是否继续？
        </p>
      </Modal>
    </div>
  );
}

interface ModelEditorProps {
  model: ModelConfig | null;
  onClose: () => void;
  onSave: (data: Omit<ModelConfig, "id" | "builtin">) => void;
}

function ModelEditor({ model, onClose, onSave }: ModelEditorProps) {
  const [name, setName] = useState(model?.name ?? "");
  const [provider, setProvider] = useState(model?.provider ?? "");
  const [modalities, setModalities] = useState<Modality[]>(
    model?.modalities ?? ["text"]
  );
  const [textIn, setTextIn] = useState(model?.pricing.text.inputPer1M ?? 0);
  const [textOut, setTextOut] = useState(model?.pricing.text.outputPer1M ?? 0);
  const [imageIn, setImageIn] = useState(model?.pricing.image.inputPer1M ?? 0);
  const [audioPerMin, setAudioPerMin] = useState(model?.pricing.audio.perMinute ?? 0);
  const [videoPerMin, setVideoPerMin] = useState(model?.pricing.video.perMinute ?? 0);
  const [enabled, setEnabled] = useState(model?.enabled ?? true);

  useEffect(() => {
    // 模态切换时无需副作用
  }, [modalities]);

  function toggleModality(m: Modality) {
    setModalities((prev) =>
      prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]
    );
  }

  function handleSave() {
    onSave({
      name: name.trim() || "未命名模型",
      provider: provider.trim() || "Custom",
      modalities,
      pricing: {
        text: { inputPer1M: Number(textIn) || 0, outputPer1M: Number(textOut) || 0 },
        image: { inputPer1M: Number(imageIn) || 0 },
        audio: { perMinute: Number(audioPerMin) || 0 },
        video: { perMinute: Number(videoPerMin) || 0 },
      },
      enabled,
    });
  }

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      title={model ? `编辑模型 · ${model.name}` : "新增模型"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            取消
          </Button>
          <Button variant="primary" onClick={handleSave}>
            保存
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <Field label="模型名称">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如 GPT-4o"
              className="w-full bg-obs-panel border border-obs-border rounded-lg px-3 py-2 text-sm text-ink input-glow"
            />
          </Field>
          <Field label="厂商">
            <input
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              placeholder="例如 OpenAI"
              className="w-full bg-obs-panel border border-obs-border rounded-lg px-3 py-2 text-sm text-ink input-glow"
            />
          </Field>
        </div>

        <Field label="支持模态">
          <div className="flex items-center gap-2 flex-wrap">
            {MODALITIES.map((m) => {
              const active = modalities.includes(m);
              const Icon = MODALITY_ICONS[m];
              return (
                <button
                  key={m}
                  type="button"
                  onClick={() => toggleModality(m)}
                  className={cn(
                    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono transition-colors",
                    active
                      ? "bg-cyan/10 border-cyan/40 text-cyan"
                      : "bg-obs-panel border-obs-border text-ink-dim hover:border-obs-borderHi"
                  )}
                >
                  <Icon size={12} />
                  {MODALITY_LABELS[m]}
                </button>
              );
            })}
          </div>
        </Field>

        <div className="rounded-lg border border-obs-border bg-obs-panel/40 p-4 space-y-3">
          <div className="text-[10px] font-mono uppercase text-ink-dim tracking-wider">
            文本计费 (USD / 1M Token)
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="输入单价">
              <NumberInput value={textIn} onChange={setTextIn} step={0.1} />
            </Field>
            <Field label="输出单价">
              <NumberInput value={textOut} onChange={setTextOut} step={0.1} />
            </Field>
          </div>
        </div>

        <div className="rounded-lg border border-obs-border bg-obs-panel/40 p-4 space-y-3">
          <div className="text-[10px] font-mono uppercase text-ink-dim tracking-wider">
            图片计费 (USD / 1M Token)
          </div>
          <Field label="输入单价">
            <NumberInput value={imageIn} onChange={setImageIn} step={0.1} />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-obs-border bg-obs-panel/40 p-4 space-y-3">
            <div className="text-[10px] font-mono uppercase text-ink-dim tracking-wider">
              音频 (USD / 分钟)
            </div>
            <Field label="单价">
              <NumberInput value={audioPerMin} onChange={setAudioPerMin} step={0.001} />
            </Field>
          </div>
          <div className="rounded-lg border border-obs-border bg-obs-panel/40 p-4 space-y-3">
            <div className="text-[10px] font-mono uppercase text-ink-dim tracking-wider">
              视频 (USD / 分钟)
            </div>
            <Field label="单价">
              <NumberInput value={videoPerMin} onChange={setVideoPerMin} step={0.001} />
            </Field>
          </div>
        </div>

        <Field label="启用状态">
          <button
            type="button"
            onClick={() => setEnabled(!enabled)}
            className={cn(
              "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono",
              enabled
                ? "bg-ok/10 border-ok/40 text-ok"
                : "bg-obs-panel border-obs-border text-ink-dim"
            )}
          >
            <span
              className={cn(
                "w-1.5 h-1.5 rounded-full",
                enabled ? "bg-ok animate-pulse-glow" : "bg-ink-dim"
              )}
            />
            {enabled ? "已启用" : "已禁用"}
          </button>
        </Field>
      </div>
    </Modal>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-[10px] font-mono uppercase text-ink-dim mb-1.5 tracking-wider">
        {label}
      </div>
      {children}
    </label>
  );
}

function NumberInput({
  value,
  onChange,
  step = 1,
}: {
  value: number;
  onChange: (n: number) => void;
  step?: number;
}) {
  return (
    <input
      type="number"
      min={0}
      step={step}
      value={value}
      onChange={(e) => onChange(Math.max(0, Number(e.target.value) || 0))}
      className="w-full bg-obs-panel border border-obs-border rounded-lg px-3 py-2 text-sm font-mono text-ink input-glow"
    />
  );
}
