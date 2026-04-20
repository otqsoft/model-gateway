"""
providers/modelscope.py — 魔塔社区 / 阿里云百炼适配器
使用阿里云 DashScope 兼容 OpenAI 的接口
"""
from __future__ import annotations
import uuid
from typing import AsyncGenerator, Union
from providers.base import BaseProvider
from models.openai_models import (
    ChatCompletionRequest, ChatCompletionResponse,
    Choice, ChatMessage
)


class ModelScopeProvider(BaseProvider):
    provider_name = "modelscope"

    def _build_headers(self) -> dict:
        """DashScope 使用 Authorization: Bearer {api_key}"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        # 流式模式下需要额外 header
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
            # DashScope 流式需要 stream=True 且返回 SSE
            headers["X-DashScope-SSE"] = "enable"
            return self._stream_ms(url, headers, body)
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

    async def _stream_ms(
        self, url: str, headers: dict, body: dict
    ) -> AsyncGenerator[str, None]:
        async for line in self._do_stream(url, headers, body):
            yield line
