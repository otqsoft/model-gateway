"""
providers/glm.py — GLM（智谱 AI）适配器
GLM-4 API 兼容 OpenAI 格式，少量字段差异
"""
from __future__ import annotations
import uuid
from typing import AsyncGenerator, Union
from providers.base import BaseProvider
from models.openai_models import (
    ChatCompletionRequest, ChatCompletionResponse,
    Choice, ChatMessage
)


class GLMProvider(BaseProvider):
    provider_name = "glm"

    def _build_headers(self) -> dict:
        """智谱 API 使用 Authorization: Bearer {api_key}"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        headers.update(self.extra_headers)
        return headers

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        upstream_model: str,
    ) -> Union[ChatCompletionResponse, AsyncGenerator[str, None]]:
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        body = self._build_body(request, upstream_model)

        if request.stream:
            return self._stream_glm(url, headers, body)
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

    async def _stream_glm(
        self, url: str, headers: dict, body: dict
    ) -> AsyncGenerator[str, None]:
        async for line in self._do_stream(url, headers, body):
            yield line
