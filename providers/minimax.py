"""
providers/minimax.py — MiniMax 适配器
MiniMax ChatCompletion Pro 接口需要额外传入 GroupId
并对请求体进行适配
"""
from __future__ import annotations
import uuid
import os
from typing import AsyncGenerator, Union
from providers.base import BaseProvider
from models.openai_models import (
    ChatCompletionRequest, ChatCompletionResponse,
    Choice, ChatMessage
)


class MiniMaxProvider(BaseProvider):
    provider_name = "minimax"

    def _build_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        headers.update(self.extra_headers)
        return headers

    def _build_body(self, request: ChatCompletionRequest, upstream_model: str) -> dict:
        """
        MiniMax ChatCompletion v2 接口与 OpenAI 高度兼容
        需要确保 messages 中 role 使用 'user'/'assistant'/'system'
        """
        body = {
            "model": upstream_model,
            "messages": [
                {"role": m.role, "content": m.content or ""}
                for m in request.messages
            ],
            "stream": request.stream or False,
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.top_p is not None:
            body["top_p"] = request.top_p
        if request.max_tokens is not None:
            body["max_tokens"] = request.max_tokens
        return body

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        upstream_model: str,
    ) -> Union[ChatCompletionResponse, AsyncGenerator[str, None]]:
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        body = self._build_body(request, upstream_model)

        if request.stream:
            return self._stream_minimax(url, headers, body)
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
                    content=msg.get("content") or msg.get("text", ""),
                ),
                finish_reason=c.get("finish_reason"),
            ))
        return ChatCompletionResponse(
            id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:24]}"),
            model=model,
            choices=choices,
            usage=self._extract_usage(data),
        )

    async def _stream_minimax(
        self, url: str, headers: dict, body: dict
    ) -> AsyncGenerator[str, None]:
        async for line in self._do_stream(url, headers, body):
            yield line
