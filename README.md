<div align="center">
	<img src="static/images/logo.png">
    <p align="center">
    <img src="https://img.shields.io/badge/python-3.8+-blue.svg" />
    <img src="https://img.shields.io/badge/FastAPI-0.95+-green.svg" />
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" />
    <img src="https://img.shields.io/pypi/v/wifi-densepose.svg" />
	</p>
	<p>&nbsp;</p>
</div>



# Model Gateway 模型网关

## 项目简介

Model Gateway 是一个基于 FastAPI + asyncio + aiohttp 构建的**生产级大模型 API 网关**，提供：

- **OpenAI 兼容接口**：对外完全兼容 OpenAI `/v1/chat/completions` 规范
- **多厂商路由**：DeepSeek、MiniMax、GLM、小米、硅基流动、魔塔社区
- **智能体支持**：支持coze、dify创建的智能体
- **异步三级限流**：全局并发 / API Key 并发 / 厂商并发
- **完整生命周期追踪**：pending→running→success/error/timeout
- **API Key 权限管理**：模型白名单、时段控制、有效期
- **Token 计费**：按模型配置单价，自动统计费用
- **管理端 REST API**：总览、监控、配置、错误分析



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



## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
# 或使用uv创建
uv sync
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
# 或
uv run uvicorn main:app --reload
```

### 5. 调用示例

```bash
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



## 演示图

<table>
    <tr>
        <td><img src="static/images/1.png"/></td>
        <td><img src="static/images/2.png"/></td>
    </tr>
    <tr>
        <td><img src="static/images/3.png"/></td>
        <td><img src="static/images/4.png"/></td>
    </tr>
    <tr>
        <td><img src="static/images/5.png"/></td>
        <td><img src="static/images/6.png"/></td>
    </tr>
</table>
