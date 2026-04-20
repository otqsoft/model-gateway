"""
providers/deepseek.py — DeepSeek 适配器
DeepSeek API 完全兼容 OpenAI 格式，直接透传即可
"""
from __future__ import annotations
import json
import uuid
import time
from typing import AsyncGenerator, Union
from providers.base import BaseProvider, ProviderException
from models.openai_models import (
    ChatCompletionRequest, ChatCompletionResponse,
    Choice, ChatMessage, ChatCompletionStreamResponse,
    StreamChoice, DeltaMessage
)


class DeepSeekProvider(BaseProvider):
    provider_name = "deepseek"

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        upstream_model: str,
    ) -> Union[ChatCompletionResponse, AsyncGenerator[str, None]]:
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        body = self._build_body(request, upstream_model)

        if request.stream:
            return self._stream(url, headers, body, upstream_model)
        else:
            data, status = await self._do_non_stream(url, headers, body)
            return self._parse_response(data, upstream_model)

    def _parse_response(self, data: dict, model: str) -> ChatCompletionResponse:
        """解析非流式响应"""
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
        model: str,
    ) -> AsyncGenerator[str, None]:
        """流式响应生成器，透传 SSE 行"""
        async for line in self._do_stream(url, headers, body):
            yield line
