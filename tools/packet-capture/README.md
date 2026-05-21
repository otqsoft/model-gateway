# AI Token 监控工具

一个用于监控AI工具（如豆包、Trae、Cursor等）网络流量并统计Token使用量的本地部署系统。

## 功能特性

1. **应用监控配置**：支持配置多个需要监控的AI应用
2. **Web管理界面**：提供友好的Web界面用于配置和查看监控数据
3. **网关上报**：自动将Token使用数据通过HTTP上报到指定网关
4. **实时统计**：实时展示发送/接收字节数、输入/输出Token数等数据
5. **协议感知解析**：自动识别OpenAI兼容API响应，从JSON中精确提取token数
6. **SSE流式解析**：支持解析流式（stream）响应中携带的usage字段
7. **自适应估算器**：在无法精确解析时，根据历史精确样本动态校准字节→Token比率
8. **精度追踪**：区分"精确解析"和"字节估算"两种来源，实时显示token精度
9. **每日日志轮转**：日志按天自动切割为 `logs/app-YYYY-MM-DD.log`，同步输出到控制台

## 项目结构

```
token/
├── main.go              # 主程序入口（含日志初始化）
├── go.mod               # Go模块依赖
├── config.yaml          # 配置文件
├── README.md            # 使用说明
├── config/
│   └── config.go        # 配置模块
├── logger/
│   ├── logger.go        # 每日自动轮转日志写入器
│   └── logger_test.go   # 单元测试
├── monitor/
│   ├── manager.go       # 监控管理器（含自适应估算逻辑）
│   ├── process.go       # 进程IO采样
│   ├── protocol.go      # 协议层解析器（HTTP/SSE/JSON token提取）
│   └── capture.go       # 连接追踪与自适应Token估算器
├── gateway/
│   └── client.go        # 网关上报模块
├── server/
│   └── server.go        # Web服务器与API路由
└── web/                 # 前端文件
    ├── index.html
    └── static/
        ├── style.css
        └── app.js
```

## 快速开始

### 1. 安装依赖

```bash
# 初始化模块
go mod tidy
# 安装依赖
go mod vendor
```

### 2. 配置

编辑 `config.yaml` 文件，配置需要监控的应用：

```yaml
server:
  port: 8080
  web_root: "./web"

gateway:
  url: "http://localhost:8086/admin/external-usage/report"
  enabled: true
  report_interval: 10   # 上报间隔（秒）

monitored_apps:
  - name: "doubao"
    tool_name: "doubao"
    provider_name: "doubao"
    process_names:
      - "doubao"
      - "DoubaoDesktop"
    # network_ratio: AI API流量在该进程总IO中的占比估算（0.0~1.0）
    # 豆包桌面端混合大量媒体流量，API仅占约10%
    network_ratio: 0.10
```

### 3. 运行

```bash
go run main.go
```

### 4. 访问Web界面

打开浏览器访问：`http://localhost:8080`

![](https://gitee.com/work25/model-gateway/raw/master/static/images/token.png)
## Token计算精度说明

本系统采用**三层精度**的Token计算策略，自动选择最优来源：

### 第一层：精确解析（最准确）✅

通过 `/api/usage/exact` 或 `/api/usage/parse` 接口，将AI应用返回的真实API响应中的 `usage` 字段直接注入系统。

**数据源**：
- 浏览器扩展插件拦截HTTPS响应
- 本地HTTP代理（如mitmproxy）转发解析结果
- 应用自身的日志文件解析

**精度**：100%（与API服务端实际计费完全一致）

### 第二层：协议特征解析（较准确）✅

对于走明文HTTP的流量，系统自动调用 `ProtocolParser` 识别 OpenAI 兼容格式的响应体：

- 非流式响应：直接解析 `response.usage.prompt_tokens` / `completion_tokens`
- 流式SSE响应：扫描所有 `data:` 块，提取带有 `usage` 字段的最后一块
- 支持gzip压缩响应自动解压

**适用场景**：使用本地HTTP代理的应用、明文HTTP调用

### 第三层：自适应字节估算（兜底）⚠️

当无法直接获取真实token数时，使用 `AdaptiveTokenEstimator` 进行估算：

- **初始比率**：请求 5.5 字节/token，响应 3.5 字节/token（基于实测统计）
- **自适应校准**：每次收到精确token样本后，自动更新比率（加权滑动平均）
- **分离计算**：请求（prompt）和响应（completion）使用独立比率，精度更高

**与旧方式的区别**：

| 对比项 | 旧方式 | 新方式 |
|--------|--------|--------|
| 估算比率 | 固定 `字节/4` | 动态校准（初始5.5/3.5） |
| 输入/输出区分 | 相同比率 | 独立比率 |
| 精确优先 | 无 | 有（精确值覆盖估算值） |
| 精度追踪 | 无 | 有（token_accuracy字段）|

## API接口

### 1. 获取统计数据

**GET** `/api/stats`

新增字段说明：
```json
{
  "success": true,
  "data": {
    "doubao": {
      "TotalExactPromptTokens": 1500,      // 精确解析的prompt tokens累计
      "TotalExactCompletionTokens": 800,   // 精确解析的completion tokens累计
      "ExactSampleCount": 12,              // 精确解析成功次数
      "TokenAccuracy": 0.95,               // 精确解析占比（0~1）
      "EstimateRatioReq": 5.2,             // 当前请求估算比率（字节/token）
      "EstimateRatioRsp": 3.3,             // 当前响应估算比率（字节/token）
      "LastModelName": "doubao-pro-32k"    // 最后一次检测到的模型名
    }
  }
}
```

### 2. 上报精确Token数（最高精度）

**POST** `/api/usage/exact`

```json
{
  "app_name": "doubao",
  "prompt_tokens": 512,
  "completion_tokens": 256,
  "total_tokens": 768,
  "model_name": "doubao-pro-32k",
  "sent_bytes": 2800,
  "received_bytes": 1100
}
```

### 3. 上传HTTP响应体解析Token

**POST** `/api/usage/parse`

```json
{
  "app_name": "doubao",
  "raw_json": "{\"id\":\"...\",\"usage\":{\"prompt_tokens\":100,\"completion_tokens\":50}}",
  "sent_bytes": 500,
  "received_bytes": 300
}
```

### 4. 添加测试流量

**POST** `/api/test/traffic`

```json
{
  "app_name": "doubao",
  "sent_bytes": 1000,
  "received_bytes": 2000
}
```

### 5. 获取/更新配置

**GET/POST** `/api/config`

### 6. 获取上报历史

**GET** `/api/report-history`

上报记录新增 `token_source` 字段（`"parsed"` | `"estimated"`）

## 精确Token数据获取方案

### 方案A：浏览器插件（推荐，覆盖HTTPS）

编写浏览器扩展，在 `onBeforeRequest`/`onCompleted` 中拦截 AI API 请求/响应，提取 `usage` 字段后调用本地 `/api/usage/exact` 接口上报。

示例（manifest v3）：
```javascript
chrome.webRequest.onCompleted.addListener(
  async (details) => {
    if (details.url.includes('/chat/completions')) {
      // 通过 devtools 或 service worker fetch 获取响应体
      // 解析 usage 字段，POST 到 http://localhost:8080/api/usage/exact
    }
  },
  { urls: ["<all_urls>"] },
  ["responseHeaders"]
);
```

### 方案B：本地透明代理（适合开发环境）

使用 mitmproxy 设置透明代理，编写插件转发 token 数据：

```python
# mitmproxy_token_reporter.py
import json, requests

def response(flow):
    if '/chat/completions' in flow.request.url:
        try:
            body = json.loads(flow.response.content)
            usage = body.get('usage', {})
            if usage:
                requests.post('http://localhost:8080/api/usage/exact', json={
                    'app_name': detect_app(flow),
                    'prompt_tokens': usage.get('prompt_tokens', 0),
                    'completion_tokens': usage.get('completion_tokens', 0),
                    'sent_bytes': len(flow.request.content),
                    'received_bytes': len(flow.response.content),
                })
        except: pass
```

### 方案C：日志解析（适合已有日志的场景）

如果AI工具输出包含 token 数量的访问日志，可通过 `ParseHTTPLogLine()` 工具函数解析。

## 配置说明

### `network_ratio` 调优指南

| 应用 | 推荐值 | 说明 |
|------|--------|------|
| 豆包桌面端 | 0.08~0.15 | 混合大量图文媒体流量 |
| Trae | 0.60~0.90 | 几乎全部为AI API调用 |
| Cursor | 0.50~0.80 | 主要为代码补全API |
| WorkBuddy | 0.03~0.08 | 混合大量UI资源加载 |

> **提示**：`network_ratio` 只影响基于字节估算的精度。一旦系统积累了足够的精确样本（方案A/B），`AdaptiveTokenEstimator` 会自动校准比率，`network_ratio` 的影响会逐渐减小。

## 网关上报格式

```json
{
 "source": "packet_capture",
 "items": [{
    "request_id": "uuid-xxx5",
    "tool_name": "doubao",
    "provider_name": "doubao",
    "model_alias": "doubao-pro-32k",
    "prompt_tokens": 1500,
    "completion_tokens": 800,
    "total_tokens": 2300
 }]
}
```

## 注意事项

1. **HTTPS加密限制**：大多数AI API走HTTPS，系统默认只能通过进程IO字节数估算。要获得精确token数，需要配合浏览器插件或代理方案
2. **network_ratio配置**：该值影响字节估算精度，建议通过观察实际使用情况调整
3. **权限要求**：在Windows上采集进程IO数据可能需要管理员权限

## 开发说明

- 使用 Go 1.21+ 开发
- Web框架：Gin
- 日志：Logrus
- 配置：YAML

## 许可证

MIT License
