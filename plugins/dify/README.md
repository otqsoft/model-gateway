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

> 注意：实际可用的模型取决于 model-gateway 中配置的上游服务商。插件内预置的模型别名需与 gateway 中 `model_mapping` 的别名一致；未列出的模型可在 `models/llm/` 下增加 YAML，并更新 `models/llm/_position.yaml` 与 `provider/model_gateway.yaml` 中的 `predefined`（与 [dify-official-plugins](https://github.com/langgenius/dify-official-plugins) 布局一致）。

## 插件结构（Dify 1.x / plugin_daemon）

本目录已按 [dify-official-plugins](https://github.com/langgenius/dify-official-plugins) 中模型类插件约定组织：

- `manifest.yaml`：`type: plugin`，并引用 `provider/model_gateway.yaml`
- `main.py` + `pyproject.toml`：Python 3.12 运行时，依赖 `dify_plugin`
- `provider/model_gateway.yaml`：供应商 UI 与凭证表单
- `provider/model_gateway.py`：`ModelProvider`，校验 `GET {gateway_url}/v1/models`
- `models/llm/llm.py`：`OAICompatLargeLanguageModel` 子类（**须在此路径**，与官方模型插件一致）
- `models/llm/*.yaml` + `_position.yaml`：预置模型定义（由 `provider/model_gateway.yaml` 的 `predefined` 引用）
- `_assets/icon_s_en.svg`、`_assets/icon_l_en.svg`：供应商图标（与 [dify-official-plugins](https://github.com/langgenius/dify-official-plugins) 一致，由 daemon 在打包时 remap；勿只放在仓库根目录）

若仍使用旧版「单文件 `type: model`」manifest，在新版 Dify 上安装时 **plugin_daemon 无法按新 schema 解析**，界面可能表现为 **`PluginDecodeResponse` / 无法解析 PluginDaemonBasicResponse**。

### 上传失败：`PluginDecodeResponse` / 解析 PluginDaemonBasicResponse 失败

常见原因：

1. **插件包格式过旧**（未包含上述目录与 `type: plugin` 的 manifest）——请使用本仓库当前 `plugins/dify` 重新打包上传。
2. **Dify API 与 `plugin_daemon` 镜像版本不一致**——请对齐 `docker/.env` 中与插件相关的镜像版本并全量重启。
3. **zip 根目录错误**——解压后根目录应直接可见 `manifest.yaml`，不要多包一层文件夹再打 zip。

处理步骤：查看 **`plugin_daemon` 容器日志**（通常比前端错误更具体）；按上文「签名验证」一节确认环境变量后重试安装。

## 安装

### 签名验证失败（bad signature）

若安装时出现：

`PluginDaemonBadRequestError: plugin verification has been enabled, and the plugin you want to install has a bad signature`

说明 **Dify 的 plugin_daemon 正在校验插件包密码学签名**；本地用 `zip` 打的包 **没有** Dify 应用商店/Marketplace 签名，会被判为无效。**这与 `manifest.yaml` 内容是否正确无关**，需要在部署侧选择其一：

**方案 A：仅内网 / 开发环境（关闭强制签名校验）**

1. 在 Dify 部署的 **`.env`**（以及若使用 `docker-compose.override.yaml`，确保 **`plugin_daemon` 服务** 能继承到相同变量）中增加或修改为：
   ```env
   FORCE_VERIFYING_SIGNATURE=false
   ENFORCE_LANGGENIUS_PLUGIN_SIGNATURES=false
   ```
2. 执行 **`docker compose down` 后再 `docker compose up -d`**，确保 **plugin_daemon 容器** 已重启并加载新环境变量。
3. 仍失败时用 `docker inspect <plugin_daemon 容器名>` 确认容器内上述变量已为 `false`。

关闭签名校验会降低安全性，仅建议在可信网络或测试环境使用。

**方案 B：生产 / 需保留校验（第三方签名）**

使用 Dify 官方流程生成密钥、对插件包签名，并在 plugin_daemon 上配置公钥与 `THIRD_PARTY_SIGNATURE_VERIFICATION_*`。说明见：[Third-party signature verification](https://docs.dify.ai/en/develop-plugin/publishing/standards/third-party-signature-verification)。

**方案 C：使用官方 CLI 打包**

新版本 Dify 更推荐使用 **`dify-plugin` CLI** 将工程打成 `.difypkg` 再上传；若仍需关闭校验，仍须配合方案 A 或对方案 B 签名后的包。

---

### 方式一：zip 本地安装（常用）

在 **`plugins/dify` 目录内** 执行打包，保证 zip 根目录即为插件根（含 `manifest.yaml`）：

```bash
cd plugins/dify
zip -r model-gateway-plugin.zip manifest.yaml main.py pyproject.toml _assets provider models
```

（若使用 `zip -r ... .`，注意不要打进 `.venv`、`__pycache__`、旧版 `model-gateway-plugin.zip` 本身。）

在 Dify：**设置 → 插件 / 模型供应商 → 本地安装**，上传上述 zip（或官方 CLI 生成的 `.difypkg`）。

**Docker 部署注意**：Dify 容器内访问宿主机上的 model-gateway 时，`Gateway base URL` 请使用例如 `http://host.docker.internal:8000`（Linux 可能需额外配置 host 网关），不要用容器内的 `127.0.0.1` 指向宿主机服务。

### 方式二：官方 CLI 打包（推荐与 Dify 文档一致）

安装 Dify 提供的 **`dify-plugin` CLI** 后，在本目录执行打包生成 `.difypkg`，再于控制台上传（具体命令以你使用的 Dify 版本文档为准）（如：dify-plugin plugin package ./dify）

### 方式三：复制到 Dify 插件目录

仅当你的部署方式支持「目录型」插件开发挂载时使用；生产环境仍建议 zip / difypkg 安装。

```bash
cp -r plugins/dify /path/to/dify/data/plugins/model-gateway/
```

## 配置

1. 在 Dify 中进入 **设置 > 模型供应商**
2. 找到 **Model Gateway** 并点击启用
3. 填写配置：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| Gateway base URL | model-gateway 根地址（无尾斜杠） | `http://192.168.1.10:8000`；Docker 访问宿主机可用 `http://host.docker.internal:8000` |
| API Key | model-gateway 管理端创建的 Key | `sk-xxxxxxxxxxxxxxxx` |

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
│   Dify      │────▶│  model-gateway   │────▶│  上游服务商     │
│  (插件)      │◀────│  Dify 插件       │◀────│  (DeepSeek/GLM) │
└─────────────┘     └──────────────────┘     └─────────────────┘
```

1. Dify 用户发起对话请求
2. Dify 调用插件的 `invoke()` 方法
3. 插件将请求转发给 model-gateway
4. model-gateway 调用上游服务商
5. 响应逐级返回给 Dify

## 添加更多模型

1. 在 `models/llm/` 下新增 `your-alias.yaml`（`model` 字段须与 model-gateway 中的 **模型别名** 一致）。
2. 在 `models/llm/_position.yaml` 中加入该模型 id，以控制下拉列表顺序。
3. 若未使用通配符 `models/llm/*.yaml`，需在 `provider/model_gateway.yaml` 的 `predefined` 中显式加入该文件路径。
3. 重新打包 zip / difypkg 并在 Dify 中更新插件。

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
