## 1. 架构设计

```mermaid
flowchart TD
    "subgraph Frontend [前端层 - React SPA]"
    "F1[计算工作台]"
    "F2[模型管理]"
    "F3[历史记录]"
    "F4[Token 估算引擎]"
    "F5[费用计算引擎]"
    "end"
    "subgraph Storage [本地存储层]"
    "S1[localStorage - 模型库]"
    "S2[localStorage - 历史记录]"
    "S3[localStorage - 用户设置]"
    "end"
    "subgraph BrowserAPI [浏览器 API]"
    "B1[File API - 文件读取]"
    "B2[Audio/Video 元数据]"
    "B3[Image 位图解析]"
    "end"
    "F1 --> F4"
    "F1 --> F5"
    "F4 --> B1"
    "F4 --> B2"
    "F4 --> B3"
    "F5 --> S1"
    "F1 --> S2"
    "F2 --> S1"
    "F3 --> S2"
```

纯前端架构，无后端依赖。所有计算在浏览器本地完成，模型库与历史记录持久化到 localStorage。

## 2. 技术说明
- **前端**：React@18 + tailwindcss@3 + vite
- **初始化工具**：vite-init（`npm create vite@latest`）
- **路由**：react-router-dom@6
- **图标**：lucide-react
- **动效**：framer-motion
- **后端**：无
- **数据库**：无（使用 localStorage 持久化）

## 3. 路由定义
| 路由 | 用途 |
|------|------|
| `/` | 计算工作台（默认首页） |
| `/models` | 模型管理 |
| `/history` | 历史记录 |

## 4. Token 估算算法

### 4.1 文本 Token
- 中文：约 1 字 ≈ 1.5 Token（按字符数 × 1.5）
- 英文：约 4 字符 ≈ 1 Token（按字符数 / 4）
- 混合：中文字符按 1.5 计，其余字符按 /4 计，分别累加
- 空白与标点：计入字符数

### 4.2 图片 Token（参考 GPT-4V 公式）
- 基础 Token：85
- 分块数 tiles = ceil(width/512) × ceil(height/512)
- 单块 Token：170
- 总 Token = 85 + tiles × 170
- 缩略图（<512×512）按 1 tile 计

### 4.3 语音 Token（参考 Whisper）
- 按时长计：每分钟 ≈ 100 Token（约 1.67 Token/秒）
- 或按模型固定单价：美元/分钟（在模型计费中配置）

### 4.4 视频 Token
- 帧采样：每秒采 1 帧，每帧按图片公式计算
- 时长部分：按语音公式计算音轨
- 总 Token = Σ(帧图片 Token) + 音轨 Token
- 为避免大视频爆栈，帧采样上限 600 帧（10 分钟），超出按比例缩放

## 5. 模型计费规则

### 5.1 数据结构
```typescript
interface ModelConfig {
  id: string;
  name: string;              // 模型显示名
  provider: string;          // 厂商
  modalities: Modality[];    // 支持的模态 ['text','image','audio','video']
  pricing: {
    text: { inputPer1M: number; outputPer1M: number };   // 美元/1M Token
    image: { inputPer1M: number; outputPer1M?: number }; // 美元/1M Token
    audio: { perMinute: number };                        // 美元/分钟
    video: { perMinute: number };                        // 美元/分钟
  };
  enabled: boolean;
  builtin: boolean;          // 内置模型不可删除
}
```

### 5.2 内置模型库
| 模型 | 模态 | 输入价($/1M) | 输出价($/1M) | 音频($/min) | 视频($/min) |
|------|------|-------------|-------------|-------------|-------------|
| GPT-4o | 文/图/音/视 | 2.5 | 10 | 0.006 | 0.006 |
| GPT-4 Turbo | 文/图 | 10 | 30 | - | - |
| GPT-3.5 Turbo | 文 | 0.5 | 1.5 | - | - |
| Claude 3 Opus | 文/图 | 15 | 75 | - | - |
| Claude 3.5 Sonnet | 文/图 | 3 | 15 | - | - |
| Claude 3 Haiku | 文/图 | 0.25 | 1.25 | - | - |
| Gemini 1.5 Pro | 文/图/音/视 | 1.25 | 5 | 0.005 | 0.005 |
| Gemini 1.5 Flash | 文/图/音/视 | 0.075 | 0.3 | 0.0005 | 0.0005 |
| Whisper | 音 | - | - | 0.006 | - |

### 5.3 费用计算
- 文本费用 = 文本 Token × 输入价 / 1,000,000
- 图片费用 = 图片 Token × 图片输入价 / 1,000,000
- 音频费用 = 音频分钟数 × 音频单价
- 视频费用 = 视频分钟数 × 视频单价
- 输出费用 = 预估输出 Token × 输出价 / 1,000,000
- 总费用 = Σ 各模态输入费用 + 输出费用

## 6. 数据模型

### 6.1 localStorage 键值
```typescript
// 模型库
'tc_models': ModelConfig[]
// 历史记录
'tc_history': HistoryRecord[]
// 用户设置
'tc_settings': { defaultModelId: string; theme: 'dark' }

interface HistoryRecord {
  id: string;
  timestamp: number;
  modelName: string;
  textTokens: number;
  imageTokens: number;
  audioTokens: number;
  videoTokens: number;
  totalInputTokens: number;
  estimatedOutputTokens: number;
  inputCost: number;
  outputCost: number;
  totalCost: number;
}
```

### 6.2 ER 关系
```mermaid
erDiagram
    "ModelConfig ||--o{ HistoryRecord : 用于"
    "ModelConfig {
        string id PK
        string name
        string provider
        string[] modalities
        json pricing
        boolean enabled
        boolean builtin
    }
    "HistoryRecord {
        string id PK
        number timestamp
        string modelName
        number textTokens
        number imageTokens
        number audioTokens
        number videoTokens
        number totalInputTokens
        number estimatedOutputTokens
        number inputCost
        number outputCost
        number totalCost
    }
```
