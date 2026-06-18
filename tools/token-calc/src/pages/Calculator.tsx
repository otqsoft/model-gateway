import { useEffect, useMemo, useState } from "react";
import { Eraser, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ModelSelector } from "@/components/calculator/ModelSelector";
import { TextInputCard } from "@/components/calculator/TextInputCard";
import { ImageInputCard } from "@/components/calculator/ImageInputCard";
import { AudioInputCard } from "@/components/calculator/AudioInputCard";
import { VideoInputCard } from "@/components/calculator/VideoInputCard";
import { SummaryBar } from "@/components/calculator/SummaryBar";
import { ResultsPanel } from "@/components/calculator/ResultsPanel";
import { Button } from "@/components/ui/Button";
import { useModelStore } from "@/store/useModelStore";
import { useHistoryStore } from "@/store/useHistoryStore";
import { useSettingsStore } from "@/store/useSettingsStore";
import { calculateCost } from "@/lib/costCalc";
import type { ImageItemInfo, MediaItemInfo, TokenBreakdown } from "@/types";

export default function Calculator() {
  const models = useModelStore((s) => s.models);
  const loading = useModelStore((s) => s.loading);
  const settings = useSettingsStore((s) => s);
  const setDefaultModel = useSettingsStore((s) => s.setDefaultModel);
  const addHistory = useHistoryStore((s) => s.addRecord);

  const enabledModels = useMemo(() => models.filter((m) => m.enabled), [models]);
  const currentModel = useMemo(
    () =>
      enabledModels.find((m) => m.id === settings.defaultModelId) ||
      enabledModels[0],
    [enabledModels, settings.defaultModelId]
  );

  const [text, setText] = useState("");
  const [images, setImages] = useState<ImageItemInfo[]>([]);
  const [audios, setAudios] = useState<MediaItemInfo[]>([]);
  const [videos, setVideos] = useState<MediaItemInfo[]>([]);
  const [estimatedOutputTokens, setEstimatedOutputTokens] = useState(500);
  const [toast, setToast] = useState<string | null>(null);

  // 清理图片预览 URL
  useEffect(() => {
    return () => {
      images.forEach((i) => URL.revokeObjectURL(i.previewUrl));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const breakdown: TokenBreakdown = useMemo(() => {
    const textTokens = (() => {
      // 复用 tokenEstimate 的中文/英文混合估算
      let cjk = 0;
      let other = 0;
      for (const ch of text) {
        const code = ch.codePointAt(0)!;
        if (
          (code >= 0x4e00 && code <= 0x9fff) ||
          (code >= 0x3400 && code <= 0x4dbf) ||
          (code >= 0x3040 && code <= 0x30ff) ||
          (code >= 0xac00 && code <= 0xd7af)
        ) {
          cjk += 1.5;
        } else {
          other += 1;
        }
      }
      return Math.ceil(cjk + other / 4);
    })();
    const imageTokens = images.reduce((s, i) => s + i.tokens, 0);
    const audioTokens = audios.reduce((s, i) => s + i.tokens, 0);
    const videoTokens = videos.reduce((s, i) => s + i.tokens, 0);
    return {
      textTokens,
      imageTokens,
      audioTokens,
      videoTokens,
      textChars: text.length,
      textWords: text.trim().split(/\s+/).filter(Boolean).length,
      imageItems: images,
      audioItems: audios,
      videoItems: videos,
    };
  }, [text, images, audios, videos]);

  const totalInputTokens =
    breakdown.textTokens +
    breakdown.imageTokens +
    breakdown.audioTokens +
    breakdown.videoTokens;

  const cost = useMemo(() => {
    if (!currentModel) {
      return {
        textCost: 0,
        imageCost: 0,
        audioCost: 0,
        videoCost: 0,
        inputCost: 0,
        outputCost: 0,
        totalCost: 0,
      };
    }
    return calculateCost(currentModel, breakdown, estimatedOutputTokens);
  }, [currentModel, breakdown, estimatedOutputTokens]);

  function handleClearAll() {
    setText("");
    images.forEach((i) => URL.revokeObjectURL(i.previewUrl));
    setImages([]);
    setAudios([]);
    setVideos([]);
    setEstimatedOutputTokens(500);
  }

  function handleSave() {
    if (!currentModel) return;
    if (totalInputTokens === 0 && estimatedOutputTokens === 0) {
      setToast("没有可保存的计算内容");
      setTimeout(() => setToast(null), 2000);
      return;
    }
    addHistory({
      modelName: currentModel.name,
      textTokens: breakdown.textTokens,
      imageTokens: breakdown.imageTokens,
      audioTokens: breakdown.audioTokens,
      videoTokens: breakdown.videoTokens,
      totalInputTokens,
      estimatedOutputTokens,
      inputCost: cost.inputCost,
      outputCost: cost.outputCost,
      totalCost: cost.totalCost,
    });
    setToast("已保存到历史记录");
    setTimeout(() => setToast(null), 2000);
  }

  function handleModelChange(id: string) {
    setDefaultModel(id);
  }

  if (loading) {
    return (
      <div>
        <PageHeader
          title="计算工作台"
          subtitle="多模态 Token 估算与费用计算"
        />
        <div className="px-6 md:px-10 py-20 text-center text-ink-muted">
          正在加载模型数据…
        </div>
      </div>
    );
  }

  if (!currentModel) {
    return (
      <div>
        <PageHeader
          title="计算工作台"
          subtitle="多模态 Token 估算与费用计算"
        />
        <div className="px-6 md:px-10 py-20 text-center text-ink-muted">
          请先在「模型管理」中启用至少一个模型。
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="计算工作台"
        subtitle="输入文本、图片、语音或视频，实时估算 Token 数量与调用费用。所有计算在浏览器本地完成，无需联网。"
        actions={
          <>
            <Button
              variant="ghost"
              size="sm"
              icon={<Eraser size={14} />}
              onClick={handleClearAll}
            >
              清空
            </Button>
          </>
        }
      />

      <div className="px-6 md:px-10 py-6 space-y-6">
        {/* 模型选择条 */}
        <div className="rounded-xl border border-obs-border bg-obs-panel/40 p-4">
          <ModelSelector
            models={enabledModels}
            value={currentModel.id}
            onChange={handleModelChange}
          />
        </div>

        {/* 顶部汇总条 */}
        <SummaryBar
          totalInputTokens={totalInputTokens}
          estimatedOutputTokens={estimatedOutputTokens}
          inputCost={cost.inputCost}
          outputCost={cost.outputCost}
          totalCost={cost.totalCost}
          onOutputTokensChange={setEstimatedOutputTokens}
        />

        {/* 四模态输入卡片网格 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <TextInputCard value={text} onChange={setText} />
          <ImageInputCard
            items={images}
            onChange={setImages}
            totalTokens={breakdown.imageTokens}
          />
          <AudioInputCard
            items={audios}
            onChange={setAudios}
            totalTokens={breakdown.audioTokens}
          />
          <VideoInputCard
            items={videos}
            onChange={setVideos}
            totalTokens={breakdown.videoTokens}
          />
        </div>

        {/* 结果面板 */}
        <ResultsPanel
          breakdown={breakdown}
          cost={cost}
          totalInputTokens={totalInputTokens}
          onSave={handleSave}
        />

        {/* 提示信息 */}
        <div className="flex items-start gap-3 rounded-xl border border-obs-border bg-obs-panel/40 p-4">
          <Sparkles size={16} className="text-cyan shrink-0 mt-0.5" />
          <div className="text-xs text-ink-muted leading-relaxed">
            <span className="text-ink font-medium">估算说明：</span>
            文本按中英文混合估算（中文 1 字 ≈ 1.5 Token，英文 4 字符 ≈ 1 Token）；
            图片采用 GPT-4V 公式（85 + tiles × 170）；
            语音按 Whisper 标准（100 Token/分钟）；
            视频按帧采样（1 帧/秒，上限 600 帧）+ 音轨时长计算。
            实际 Token 数会因模型分词器而异，结果仅供参考。
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg bg-obs-cardHi border border-cyan/40 text-sm text-ink shadow-glow animate-fade-up">
          {toast}
        </div>
      )}
    </div>
  );
}
