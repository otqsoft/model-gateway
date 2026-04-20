# AI Model Gateway — 多平台大模型统一网关

## 项目简介

AI Model Gateway 是一个基于 FastAPI + asyncio + aiohttp 构建的**生产级大模型 API 网关**，提供：

- **OpenAI 兼容接口**：对外完全兼容 OpenAI `/v1/chat/completions` 规范
- **多厂商路由**：DeepSeek、MiniMax、GLM、小米、硅基流动、魔塔社区
- **异步三级限流**：全局并发 / API Key 并发 / 厂商并发
- **完整生命周期追踪**：pending→running→success/error/timeout
- **API Key 权限管理**：模型白名单、时段控制、有效期
- **Token 计费**：按模型配置单价，自动统计费用
- **管理端 REST API**：总览、监控、配置、错误分析

---

## 项目结构

```
model-gateway/
├── main.py                    # FastAPI 应用入口
├── requirements.txt           # 依赖列表
├── .env.example               # 环境变量模板
├── sql/
│   └── init.sql               # MySQL 建表语句
├── core/
│   ├── config.py              # 全局配置（从环境变量读取）
│   ├── limiter.py             # 三级异步信号量限流
│   ├── security.py            # AES Key 加密工具
│   └── utils.py               # 公共工具函数
├── db/
│   └── database.py            # MySQL 异步连接池（aiomysql）
├── models/
│   ├── openai_models.py       # OpenAI 兼容 Pydantic 模型
│   ├── db_models.py           # 数据库行映射模型
│   └── admin_models.py        # 管理端请求/响应模型
├── providers/
│   ├── base.py                # 抽象基类
│   ├── deepseek.py            # DeepSeek 适配器
│   ├── minimax.py             # MiniMax 适配器
│   ├── glm.py                 # GLM（智谱）适配器
│   ├── xiaomi.py              # 小米适配器
│   ├── siliconflow.py         # 硅基流动适配器
│   ├── modelscope.py          # 魔塔社区适配器
│   └── registry.py            # 适配器注册表
├── crud/
│   ├── api_keys.py            # API Key CRUD
│   ├── request_logs.py        # 请求日志 CRUD
│   ├── billing.py             # 计费 CRUD
│   ├── providers.py           # 厂商配置 CRUD
│   └── models.py              # 模型映射 CRUD
├── api/
│   ├── v1/
│   │   ├── chat.py            # /v1/chat/completions
│   │   └── models_list.py     # /v1/models
│   └── admin/
│       ├── overview.py        # 总览统计
│       ├── monitor.py         # 实时监控
│       ├── keys.py            # API Key 管理
│       ├── providers.py       # 厂商管理
│       └── logs.py            # 日志查询
└── middleware/
    ├── auth.py                # API Key 认证
    ├── rate_limit.py          # 限流中间件
    └── time_control.py        # 时段访问控制
```

---

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
mysql -u root -p < sql/init.sql
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填写数据库连接和各厂商 API Key
```

### 4. 启动服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 调用示例

```bash
# 创建 API Key（管理端）
curl -X POST http://localhost:8000/admin/keys \
  -H "X-Admin-Token: your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{"name":"test-key","allowed_models":["gpt-3.5-turbo","deepseek-chat"]}'

# 调用对话接口（OpenAI 兼容）
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-xxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role":"user","content":"你好"}],
    "stream": false
  }'
```

---

## 并发限流说明

| 层级 | 参数 | 默认值 | 说明 |
|------|------|--------|------|
| 全局 | `GLOBAL_MAX_CONCURRENCY` | 200 | 所有请求总并发 |
| API Key | `KEY_MAX_CONCURRENCY` | 20 | 单 Key 最大并发 |
| 厂商 | 各厂商配置 | 50 | 单厂商最大并发 |

超过限制返回 HTTP 429，并记录限流日志。

---

## 支持厂商

| 厂商 | model 前缀/名称示例 |
|------|---------------------|
| DeepSeek | `deepseek-chat`, `deepseek-coder` |
| MiniMax | `abab6.5-chat`, `abab5.5-chat` |
| GLM（智谱） | `glm-4`, `glm-3-turbo` |
| 小米 | `xiaomi-*` |
| 硅基流动 | `Qwen/Qwen2-7B-Instruct` 等 |
| 魔塔社区 | `modelscope/*` |

---

## 管理端 API 清单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/overview` | 总览统计 |
| GET | `/admin/monitor/status` | 实时状态分布 |
| GET | `/admin/monitor/latency` | 耗时分布 |
| GET | `/admin/keys` | Key 列表 |
| POST | `/admin/keys` | 创建 Key |
| PUT | `/admin/keys/{id}` | 更新 Key |
| DELETE | `/admin/keys/{id}` | 删除 Key |
| GET | `/admin/providers` | 厂商列表 |
| POST | `/admin/providers` | 添加厂商 |
| GET | `/admin/logs` | 请求日志查询 |
| GET | `/admin/logs/{request_id}` | 单条日志详情 |
| GET | `/admin/billing` | 计费汇总 |
