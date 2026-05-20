# AI Token 监控工具

一个用于监控AI工具（如豆包、Trae、Cursor等）网络流量并统计Token使用量的本地部署系统。

## 功能特性

1. **应用监控配置**：支持配置多个需要监控的AI应用
2. **Web管理界面**：提供友好的Web界面用于配置和查看监控数据
3. **网关上报**：自动将Token使用数据通过HTTP上报到指定网关
4. **实时统计**：实时展示发送/接收字节数、输入/输出Token数等数据
5. **测试API**：提供测试接口，方便验证统计功能

## 项目结构

```
token/
├── main.go              # 主程序入口
├── go.mod               # Go模块依赖
├── config.yaml          # 配置文件
├── README.md            # 使用说明
├── config/              # 配置模块
│   └── config.go
├── monitor/             # 监控模块
│   └── manager.go
├── gateway/             # 网关上报模块
│   └── client.go
├── server/              # Web服务器模块
│   └── server.go
├── web/                 # 前端文件
│   ├── index.html
│   └── static/
│       ├── style.css
│       └── app.js
├── run.bat              # 启动脚本
├── install-dependencies.bat # 依赖安装脚本
└── test-api.bat        # API测试脚本
```

## 快速开始

### 1. 安装依赖

```bash
go mod download
```

或双击运行 `install-dependencies.bat`

### 2. 配置

编辑 `config.yaml` 文件，配置需要监控的应用：

```yaml
server:
  port: 8080
  web_root: "./web"

gateway:
  url: "http://localhost:8086/admin/external-usage/report"
  enabled: true

monitored_apps:
  - name: "doubao"
    tool_name: "doubao"
    provider_name: "volcengine"
    process_name: "doubao"

  - name: "trae"
    tool_name: "trae"
    provider_name: "trae"
    process_name: "trae"

  - name: "cursor"
    tool_name: "cursor"
    provider_name: "cursor"
    process_name: "cursor"
```

### 3. 运行

```bash
go run main.go
```

或双击运行 `run.bat`

### 4. 访问Web界面

打开浏览器访问：`http://localhost:8080`

![](..\..\static\images\token.png)

## 测试统计功能

### 方法1：使用测试脚本

双击运行 `test-api.bat`，这会自动发送测试流量数据

### 方法2：使用curl手动测试

```bash
curl -X POST http://localhost:8080/api/test/traffic ^
  -H "Content-Type: application/json" ^
  -d "{\"app_name\":\"doubao\",\"sent_bytes\":1000,\"received_bytes\":2000}"
```

### 方法3：使用PowerShell测试

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/api/test/traffic" -Method Post -ContentType "application/json" -Body '{"app_name":"doubao","sent_bytes":1000,"received_bytes":2000}'
```

## API接口

### 1. 获取统计数据

**GET** `/api/stats`

响应示例：
```json
{
  "success": true,
  "data": {
    "doubao": {
      "ToolName": "doubao",
      "ProviderName": "volcengine",
      "TotalSentBytes": 3000,
      "TotalReceivedBytes": 6000,
      "TotalPromptTokens": 750,
      "TotalCompletionTokens": 1500,
      "SessionSentBytes": 3000,
      "SessionReceivedBytes": 6000,
      "SessionPromptTokens": 750,
      "SessionCompletionTokens": 1500,
      "LastUpdate": "2024-01-01T12:00:00Z"
    }
  }
}
```

### 2. 添加测试流量

**POST** `/api/test/traffic`

请求体：
```json
{
  "app_name": "doubao",
  "sent_bytes": 1000,
  "received_bytes": 2000
}
```

### 3. 获取配置

**GET** `/api/config`

### 4. 更新配置

**POST** `/api/config`

## 统计数据说明

系统维护两套统计数据：

1. **累计统计（Total）**：从程序启动以来的所有流量数据
2. **本次统计（Session）**：距离上次上报网关后的流量数据

- **发送字节（SentBytes）**：应用发送的网络流量
- **接收字节（ReceivedBytes）**：应用接收的网络流量
- **输入Token（PromptTokens）**：基于发送字节数估算的输入Token数
- **输出Token（CompletionTokens）**：基于接收字节数估算的输出Token数

### Token估算方式

由于无法直接获取真实Token数，系统采用估算方式：
- 输入Token ≈ 发送字节数 / 4
- 输出Token ≈ 接收字节数 / 4

## 网关接口

系统会定期（每30秒）向配置的网关地址上报数据，接口格式如下：

**请求方法**：POST

**请求地址**：配置的 gateway.url

**请求体**：
```json
{
  "request_id": "唯一请求ID",
  "tool_name": "工具名称",
  "provider_name": "厂商标识",
  "model_alias": "模型名称（可选）",
  "prompt_tokens": 输入Token数,
  "completion_tokens": 输出Token数,
  "total_tokens": 总Token数（可选）,
  "input_price": 输入单价（可选）,
  "output_price": 输出单价（可选）,
  "detail": "原始数据摘要（可选）"
}
```

## 注意事项

1. **实际网络抓包**：目前系统提供了统计框架，实际的网络抓包功能需要根据具体需求实现
2. **Token计算**：Token估算采用字节数/4的方式，这是基于平均字符-TOKEN比率的估算
3. **网关可用性**：请确保网关地址可访问，否则会导致上报失败（但不影响本地统计）
4. **权限要求**：在Windows上捕获网络流量可能需要管理员权限

## 统计修复说明

修复了以下问题：

1. ✅ **区分累计和本次统计**：添加了Total和Session两套统计指标
2. ✅ **正确的累加逻辑**：只对本次上报周期内的数据进行累加
3. ✅ **上报后重置**：每次上报网关后，自动重置Session统计数据
4. ✅ **移除模拟数据**：移除了自动生成模拟流量的逻辑
5. ✅ **添加测试API**：提供 `/api/test/traffic` 接口用于测试

## 开发说明

- 使用 Go 1.21+ 开发
- Web框架：Gin
- 日志：Logrus
- 配置：YAML

## 许可证

MIT License
