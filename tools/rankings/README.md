# AI Model Rankings

一个基于 OpenRouter API 的 AI 模型排名网站，提供模型排行榜、性能基准测试、市场份额等数据可视化展示。

## ✨ 功能特性

- **LLM Leaderboard** - 基于周使用量的模型排行榜
- **Top Models** - 年度模型使用量趋势图表（堆叠柱状图）
- **Market Share** - 提供商市场份额分布图（环形图）
- **Benchmarks** - 模型性能基准测试排名
- **Fastest Models** - 最快响应速度模型排名
- **Categories** - 模型分类浏览
- **Languages / Programming** - 多语言与编程能力筛选
- **Context Length** - 上下文长度分布
- **Tool Calls / Images / Audio** - 功能能力筛选
- **Top Apps** - 热门应用排名

## 🛠️ 技术栈

### 前端
- React 18 + TypeScript
- Vite 6
- Tailwind CSS 3
- Zustand（状态管理）
- Recharts（图表库）
- React Router（路由）
- Lucide React（图标）

### 后端
- Node.js + TypeScript
- Express 4
- OpenRouter API

## 🚀 快速开始

### 前置要求
- Node.js >= 20.x
- npm >= 10.x

### 安装依赖

```bash
# 安装前端依赖
npm install

# 安装后端依赖
cd api
npm install
cd ..
```

### 启动开发服务器

**方式一：同时启动前后端**
```bash
# 终端1：启动后端（监听 127.0.0.1:3001）
npx tsx api/server.ts

# 终端2：启动前端（监听 127.0.0.1:5173）
npm run dev
```

**方式二：使用 npm 脚本**
```bash
# 启动后端
npm run start:backend

# 启动前端
npm run dev
```

访问地址：http://127.0.0.1:5173

### 构建生产版本

```bash
# 构建前端
npm run build

# 构建后端（可选）
cd api
npm run build
cd ..
```

## 📁 项目结构

```
├── api/                    # 后端代码
│   ├── routes/             # API 路由
│   │   ├── models.ts       # 模型相关接口
│   │   └── stats.ts        # 统计数据接口
│   ├── services/           # 业务服务
│   │   ├── openrouter.ts   # OpenRouter API 对接
│   │   ├── cache.ts        # 内存缓存服务
│   │   └── rankingsScraper.ts  # 排行榜数据爬虫
│   ├── app.ts              # Express 应用配置
│   ├── server.ts           # 服务器入口
│   └── package.json
├── src/                    # 前端代码
│   ├── components/         # 组件
│   │   ├── Navbar.tsx      # 导航栏
│   │   ├── Leaderboard.tsx # LLM 排行榜
│   │   ├── TopModels.tsx   # 年度趋势图表
│   │   ├── MarketShare.tsx # 市场份额
│   │   ├── Benchmarks.tsx  # 基准测试
│   │   ├── FastestModels.tsx  # 速度排名
│   │   ├── CategorySection.tsx # 分类组件
│   │   └── ...
│   ├── pages/              # 页面
│   │   ├── Home.tsx        # 首页
│   │   └── ModelDetail.tsx # 模型详情页
│   ├── store/              # Zustand 状态管理
│   │   ├── useRankingStore.ts
│   │   ├── useLanguageStore.ts
│   │   └── useThemeStore.ts
│   ├── utils/              # 工具函数
│   ├── App.tsx             # 根组件
│   ├── main.tsx            # 入口文件
│   └── index.css           # 全局样式
├── dist/                   # 构建输出目录
├── vite.config.ts          # Vite 配置
├── tailwind.config.js      # Tailwind 配置
└── package.json
```

## 🌐 多语言支持

项目支持中英文切换：
- 中文（默认）
- English

通过导航栏的语言切换按钮切换。

## 🎨 主题切换

支持深色/浅色主题切换：
- 深色主题（默认）
- 浅色主题

通过导航栏的主题切换按钮切换。

## 🔧 API 接口

### 模型相关
- `GET /api/models` - 获取模型列表（支持筛选/排序/分页）
- `GET /api/models/leaderboard` - 获取排行榜数据
- `GET /api/models/benchmarks` - 获取基准测试排名
- `GET /api/models/fastest` - 获取最快模型排名
- `GET /api/models/:id` - 获取单个模型详情

### 统计数据
- `GET /api/stats` - 获取整体统计数据
- `GET /api/stats/top-models` - 获取年度趋势数据
- `GET /api/stats/top-apps` - 获取热门应用数据
- `GET /api/stats/context-length` - 获取上下文长度分布

## 📦 部署

### 开发环境
```bash
# 启动后端
npx tsx api/server.ts

# 启动前端
npm run dev
```

### 生产环境
1. 构建前端：`npm run build`
2. 启动后端：`npx tsx api/server.ts`（推荐使用 PM2 管理）
3. 配置反向代理（Nginx/Apache）

详细部署说明请参考 [DEPLOYMENT.md](DEPLOYMENT.md)

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
