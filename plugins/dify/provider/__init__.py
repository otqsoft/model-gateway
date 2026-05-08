"""
Dify Plugin - Model Gateway Provider
====================================
模型提供器核心实现

Dify 插件接口参考:
  https://github.com/langgenius/dify/tree/main/api/extensions/model-provider
"""

import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx

logger = logging.getLogger("dify_plugin.model_gateway")


# ───────────────────────────────────────────────────────
# 辅助函数：消息格式转换
# ───────────────────────────────────────────────────────

def _convert_messages(messages: List[Dict]) -> List[Dict]:
    """
    将 Dify 消息格式转换为 OpenAI 格式
    
    Dify 格式: [{"role": "user", "content": "..."}]
    OpenAI 格式: [{"role": "user", "content": "..."}]
    """
    result = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # 处理字典格式的 content
        if isinstance(content, dict):
            text = content.get("text", "")
            if not text and "blocks" in content:
                for block in content.get("blocks", []):
                    if block.get("type") == "text":
                        text = block.get("data", {}).get("text", "")
                        break
            content = text or str(content)
        
        result.append({
            "role": role,
            "content": content
        })
    return result


def _convert_tools(tools: List[Dict]) -> List[Dict]:
    """将 Dify 工具格式转换为 OpenAI function calling 格式"""
    openai_tools = []
    for tool in tools:
        if tool.get("type") == "function":
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["function"].get("name", ""),
                    "description": tool["function"].get("description", ""),
                    "parameters": tool["function"].get("parameters", {}),
                }
            })
    return openai_tools


# ───────────────────────────────────────────────────────
# ModelGatewayProvider 类
# ───────────────────────────────────────────────────────

class ModelGatewayProvider:
    """
    Model Gateway Dify 模型提供器
    
    实现 Dify 模型提供器接口，让 Dify 可以通过 model-gateway
    调用各种大模型（DeepSeek、GLM、MiniMax 等）
    """
    
    def __init__(self):
        self.provider_name = "model-gateway"
        logger.info("ModelGatewayProvider 初始化")
    
    def validate_credentials(self, credentials: Dict[str, str]) -> None:
        """
        验证凭证是否有效
        
        Args:
            credentials: 包含 gateway_url 和 api_key 的字典
            
        Raises:
            ValueError: 如果凭证无效
        """
        gateway_url = credentials.get("gateway_url", "").strip().rstrip("/")
        api_key = credentials.get("api_key", "").strip()
        
        if not gateway_url:
            raise ValueError("Gateway 地址不能为空")
        if not api_key:
            raise ValueError("API Key 不能为空")
        if not gateway_url.startswith(("http://", "https://")):
            raise ValueError("Gateway 地址必须以 http:// 或 https:// 开头")
        
        # 尝试调用 gateway 的 /v1/models 接口验证
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{gateway_url}/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if resp.status_code == 401:
                    raise ValueError("API Key 无效或已过期")
                if resp.status_code != 200:
                    raise ValueError(f"Gateway 返回错误: {resp.status_code}")
        except httpx.ConnectError:
            raise ValueError(f"无法连接到 Gateway: {gateway_url}")
        except httpx.TimeoutException:
            raise ValueError("Gateway 连接超时")
    
    def get_models(self, credentials: Dict[str, str]) -> List[Dict]:
        """
        获取可用模型列表
        
        Args:
            credentials: 凭证
            
        Returns:
            模型列表
        """
        # 返回预定义的模型列表
        return [
            {
                "name": "deepseek-chat",
                "label": {"en": "DeepSeek Chat", "zh_Hans": "DeepSeek Chat"},
                "model_type": "llm"
            },
            {
                "name": "deepseek-coder",
                "label": {"en": "DeepSeek Coder", "zh_Hans": "DeepSeek Coder"},
                "model_type": "llm"
            },
            {
                "name": "glm-4",
                "label": {"en": "GLM-4", "zh_Hans": "GLM-4"},
                "model_type": "llm"
            },
            {
                "name": "glm-4-flash",
                "label": {"en": "GLM-4-Flash", "zh_Hans": "GLM-4-Flash"},
                "model_type": "llm"
            },
            {
                "name": "glm-4-plus",
                "label": {"en": "GLM-4-Plus", "zh_Hans": "GLM-4-Plus"},
                "model_type": "llm"
            },
            {
                "name": "glm-3-turbo",
                "label": {"en": "GLM-3-Turbo", "zh_Hans": "GLM-3-Turbo"},
                "model_type": "llm"
            },
            {
                "name": "MiniMax-Text-01",
                "label": {"en": "MiniMax Text", "zh_Hans": "MiniMax Text"},
                "model_type": "llm"
            },
            {
                "name": "xiaomi-ai",
                "label": {"en": "Xiaomi AI", "zh_Hans": "小米 AI"},
                "model_type": "llm"
            }
        ]
    
    async def invoke(
        self,
        model: str,
        credentials: Dict[str, str],
        prompt_messages: List[Dict],
        model_parameters: Dict[str, Any],
        tools: Optional[List[Dict]] = None,
        stream: bool = True,
        timeout: Optional[int] = None,
    ) -> Union[Dict, AsyncGenerator[Dict, None]]:
        """
        调用模型进行对话
        
        Args:
            model: 模型名称
            credentials: 凭证（gateway_url, api_key）
            prompt_messages: 消息列表
            model_parameters: 模型参数
            tools: 工具定义
            stream: 是否流式输出
            timeout: 超时时间（秒）
            
        Returns:
            非流式: 完整的响应字典
            流式: AsyncGenerator，逐次 yield 响应片段
        """
        gateway_url = credentials.get("gateway_url", "").rstrip("/")
        api_key = credentials.get("api_key", "")
        
        # 构建请求体
        body = {
            "model": model,
            "messages": _convert_messages(prompt_messages),
            "stream": stream,
        }
        
        # 添加模型参数
        if model_parameters:
            for key in ["temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty"]:
                if key in model_parameters and model_parameters[key] is not None:
                    body[key] = model_parameters[key]
        
        # 处理 Function Calling
        if tools:
            body["tools"] = _convert_tools(tools)
        
        timeout_seconds = timeout or 120
        
        if stream:
            return self._stream_invoke(gateway_url, api_key, body, timeout_seconds)
        else:
            return await self._invoke_non_stream(gateway_url, api_key, body, timeout_seconds)
    
    async def _invoke_non_stream(
        self,
        gateway_url: str,
        api_key: str,
        body: Dict,
        timeout: int
    ) -> Dict:
        """非流式调用"""
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
            )
            
            if resp.status_code != 200:
                error_detail = resp.text
                try:
                    error_json = resp.json()
                    error_detail = error_json.get("error", {}).get("message", error_detail)
                except Exception:
                    pass
                raise Exception(f"Gateway 错误 ({resp.status_code}): {error_detail}")
            
            return resp.json()
    
    async def _stream_invoke(
        self,
        gateway_url: str,
        api_key: str,
        body: Dict,
        timeout: int
    ) -> AsyncGenerator[Dict, None]:
        """流式调用"""
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/v1/chat/completions",
                json=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
            ) as resp:
                if resp.status_code != 200:
                    error_detail = await resp.atext()
                    try:
                        error_json = await resp.json()
                        error_detail = error_json.get("error", {}).get("message", error_detail)
                    except Exception:
                        pass
                    raise Exception(f"Gateway 错误 ({resp.status_code}): {error_detail}")
                
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            yield {"finish": True}
                            return
                        try:
                            data = json.loads(data_str)
                            yield data
                        except json.JSONDecodeError:
                            logger.warning(f"JSON 解析失败: {data_str[:100]}")
                            continue


# ───────────────────────────────────────────────────────
# 导出
# ───────────────────────────────────────────────────────

__all__ = ["ModelGatewayProvider"]
