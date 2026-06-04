"""
providers/openrouter.py — OpenRouter 适配器

OpenRouter 是一个统一的 AI 模型路由平台，聚合了数百个模型，
API 格式完全兼容 OpenAI v1，支持额外的 HTTP-Referer 和 X-Title 请求头。

官方文档：https://openrouter.ai/docs
"""
from __future__ import annotations
import uuid
from typing import AsyncGenerator, Union
from providers.base import BaseProvider
from models.openai_models import (
    ChatCompletionRequest, ChatCompletionResponse,
    Choice, ChatMessage
)


class OpenRouterProvider(BaseProvider):
    provider_name = "openrouter"

    # OpenRouter 推荐在请求头中传递来源信息，用于其仪表盘统计
    # 可通过 extra_headers 配置 HTTP-Referer 和 X-Title
    DEFAULT_HEADERS = {
        "HTTP-Referer": "https://github.com/model-gateway",
        "X-Title": "Model Gateway",
    }

    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 120,
                 extra_headers: dict | None = None):
        # 合并默认头与自定义头（自定义头优先）
        merged_headers = {**self.DEFAULT_HEADERS, **(extra_headers or {})}
        super().__init__(base_url, api_key, timeout_seconds, merged_headers)

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        upstream_model: str,
    ) -> Union[ChatCompletionResponse, AsyncGenerator[str, None]]:
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        body = self._build_body(request, upstream_model)

        if request.stream:
            return self._stream(url, headers, body)
        else:
            data, _ = await self._do_non_stream(url, headers, body)
            return self._parse_response(data, upstream_model)

    def _parse_response(self, data: dict, model: str) -> ChatCompletionResponse:
        """解析非流式响应（标准 OpenAI 格式）"""
        choices = []
        for c in data.get("choices", []):
            msg = c.get("message", {})
            choices.append(Choice(
                index=c.get("index", 0),
                message=ChatMessage(
                    role=msg.get("role", "assistant"),
                    content=msg.get("content"),
                ),
                finish_reason=c.get("finish_reason"),
            ))
        return ChatCompletionResponse(
            id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:24]}"),
            model=model,
            choices=choices,
            usage=self._extract_usage(data),
        )

    async def _stream(
        self,
        url: str,
        headers: dict,
        body: dict,
    ) -> AsyncGenerator[str, None]:
        """流式响应生成器，透传 SSE 行"""
        async for line in self._do_stream(url, headers, body):
            yield line
