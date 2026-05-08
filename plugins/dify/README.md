# Model Gateway Dify 插件

让 Dify 能够使用 model-gateway 管理的所有模型。

## 支持的模型

| 模型 | 名称 | 说明 |
|------|------|------|
| DeepSeek | `deepseek-chat` | DeepSeek Chat 对话模型 |
| DeepSeek | `deepseek-coder` | DeepSeek 代码生成模型 |
| 智谱 GLM | `glm-4` | 智谱 GLM-4 |
| 智谱 GLM | `glm-4-flash` | 智谱 GLM-4-Flash（快速版） |
| 智谱 GLM | `glm-4-plus` | 智谱 GLM-4-Plus |
| 智谱 GLM | `glm-3-turbo` | 智谱 GLM-3-Turbo |
| MiniMax | `MiniMax-Text-01` | MiniMax 文本模型 |
| 小米 | `xiaomi-ai` | 小米 AI |
| 兼容 | `gpt-3.5-turbo` | GPT-3.5 兼容模式 |
| 兼容 | `gpt-4o` | GPT-4o 兼容模式 |

> 注意：实际可用的模型取决于 model-gateway 中配置的上游服务商。

## 安装

### 方式一：从源码安装

1. 将 `plugins/dify/` 目录打包：
   ```bash
   cd plugins/dify
   zip -r model-gateway-plugin.zip .
   ```

2. 在 Dify 中进入 **设置 > 模型供应商 > 安装插件**
3. 上传 `model-gateway-plugin.zip`

### 方式二：复制到 Dify 插件目录

```bash
cp -r plugins/dify /path/to/dify/data/plugins/model-gateway/
```

## 配置

1. 在 Dify 中进入 **设置 > 模型供应商**
2. 找到 **Model Gateway** 并点击启用
3. 填写配置：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| Gateway 地址 | model-gateway 服务地址 | `http://localhost:8000` |
| API Key | model-gateway 中的 API Key | `sk-xxxxxxxxxxxxxxxx` |

4. 点击 **验证** 确保配置正确
5. 保存后即可在应用中选用模型

## 使用示例

```python
# 通过 Dify API 调用
import requests

response = requests.post(
    "https://your-dify-instance/v1/chat-messages",
    headers={
        "Authorization": "Bearer YOUR-DIFY-APP-TOKEN",
        "Content-Type": "application/json",
    },
    json={
        "inputs": {},
        "query": "你好，请介绍一下自己",
        "response_mode": "streaming",
        "user": "user123",
        "model": "deepseek-chat",  # 使用 model-gateway 中的模型
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

## 与 Dify 的集成原理

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dify     │────▶│  model-gateway   │────▶│  上游服务商     │
│  (插件)    │◀────│  Dify 插件       │◀────│  (DeepSeek/GLM) │
└─────────────┘     └──────────────────┘     └─────────────────┘
```

1. Dify 用户发起对话请求
2. Dify 调用插件的 `invoke()` 方法
3. 插件将请求转发给 model-gateway
4. model-gateway 调用上游服务商
5. 响应逐级返回给 Dify

## 添加更多模型

如需添加其他模型，修改 `provider.py` 中的 `MODELS` 列表：

```python
MODELS = [
    # ... 现有模型
    {
        "name": "new-model-name",  # 与 model-gateway 中的 model_alias 一致
        "label": {"zh_Hans": "新模型", "en": "New Model"},
        "mode": "chat",
    },
]
```

## 故障排查

### 验证失败

- **连接被拒绝**：检查 Gateway 地址是否正确，服务是否启动
- **API Key 无效**：在 model-gateway 管理面板确认 Key 有效
- **权限不足**：确认 API Key 有权访问目标模型

### 调用超时

- 检查网络连接
- 调整 Gateway 的超时配置
- 降低 `max_tokens` 参数

### 模型不可用

- 确认模型已在 model-gateway 中配置
- 检查模型的 API Key 配额
