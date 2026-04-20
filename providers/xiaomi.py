"""
providers/xiaomi.py — 小米 AI 适配器
小米 AI API 兼容 OpenAI 接口规范
"""
from __future__ import annotations
import uuid
from typing import AsyncGenerator, Union
from providers.base import BaseProvider
from models.openai_models import (
    ChatCompletionRequest, ChatCompletionResponse,
    Choice, ChatMessage
)


class XiaomiProvider(BaseProvider):
    provider_name = "xiaomi"

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        upstream_model: str,
    ) -> Union[ChatCompletionResponse, AsyncGenerator[str, None]]:
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        body = self._build_body(request, upstream_model)

        if request.stream:
            return self._stream_xiaomi(url, headers, body)
        else:
            data, _ = await self._do_non_stream(url, headers, body)
            return self._parse_response(data, upstream_model)

    def _parse_response(self, data: dict, model: str) -> ChatCompletionResponse:
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

    async def _stream_xiaomi(
        self, url: str, headers: dict, body: dict
    ) -> AsyncGenerator[str, None]:
        async for line in self._do_stream(url, headers, body):
            yield line
