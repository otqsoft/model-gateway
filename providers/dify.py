"""
providers/dify.py — Dify 智能体适配器
Dify API 与 OpenAI 差异较大，需要做请求/响应的双向转换：
  - OpenAI 格式 => Dify API 格式
  - Dify SSE/JSON 响应 => OpenAI ChatCompletion 格式
Dify 的 app_key 即 API Key，存储在 provider.api_key 中
"""
from __future__ import annotations
import json
import uuid
import logging
from typing import AsyncGenerator, Union
from providers.base import BaseProvider, ProviderException
from models.openai_models import (
    ChatCompletionRequest, ChatCompletionResponse,
    Choice, ChatMessage, UsageInfo
)

logger = logging.getLogger("gateway.provider.dify")


class DifyProvider(BaseProvider):
    """
    Dify 智能体适配器
    支持流式和非流式 /v1/chat/completions
    Dify API doc: https://docs.dify.ai/getting-started/api
    """
    provider_name = "dify"

    def __init__(self, base_url: str, api_key: str, **kwargs):
        # base_url 填 Dify 服务地址，如 http://localhost
        super().__init__(base_url, api_key, **kwargs)
        self.base_url = self.base_url.rstrip("/")
        logger.info("Dify Provider 初始化: base_url=%s", self.base_url)

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        upstream_model: str,
    ) -> Union[ChatCompletionResponse, AsyncGenerator[str, None]]:
        headers = self._dify_headers()
        body = self._dify_request_body(request)

        if request.stream:
            return self._stream_dify(headers, body, upstream_model)
        else:
            return await self._non_stream_dify(headers, body, upstream_model)

    def _dify_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _dify_request_body(self, request: ChatCompletionRequest) -> dict:
        """
        OpenAI messages => Dify /v1/chat-messages 格式
        - query: 最后一条 user 消息内容
        - inputs: 从前面的 system/user messages 提取 key-value
        - conversation_id: 暂不支持多轮，固定为空
        """
        # 提取最后一条 user 消息作为 query
        query = ""
        for msg in reversed(request.messages):
            if msg.role == "user" and msg.content:
                query = msg.content
                break

        # Dify inputs: 尝试从 system 消息中解析键值对，兜底为空
        inputs = {}
        for msg in request.messages:
            if msg.role == "system" and msg.content:
                # 简单兜底：留空 inputs，Dify 应用自己处理
                pass

        body = {
            "inputs": inputs,
            "query": query,
            "response_mode": "streaming" if request.stream else "blocking",
            "conversation_id": "",
            "user": request.user or "gateway_user",
        }
        return body

    def _build_dify_url(self) -> str:
        url = f"{self.base_url}/v1/chat-messages"
        # logger.info("Dify API URL: %s", url)
        return url

    # ── 非流式 ───────────────────────────────────────────────────

    async def _non_stream_dify(
        self, headers: dict, body: dict, model: str
    ) -> ChatCompletionResponse:
        """
        Dify blocking 响应：
        {
          "event": "message",
          "task_id": "...",
          "id": "...",
          "conversation_id": "...",
          "mode": "chat",
          "answer": "...",
          "metadata": {...}
        }
        """
        import aiohttp
        url = self._build_dify_url()
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        # logger.info("Dify 非流式请求: url=%s, body=%s", url, json.dumps(body, ensure_ascii=False))

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=body, headers=headers) as resp:
                if resp.status != 200:
                    err_body = await resp.text()
                    raise ProviderException(
                        f"Dify 上游返回 {resp.status}: {err_body[:300]}",
                        status_code=502,
                        upstream_status=resp.status,
                    )
                data = await resp.json(content_type=None)

                answer = data.get("answer", "")

                # 尝试从 metadata 提取 token
                metadata = data.get("metadata", {}) or {}
                usage_data = metadata.get("usage", {}) or {}
                
                # 尝试从其他位置提取 usage
                if not usage_data:
                    usage_data = data.get("usage", {}) or {}
                
                prompt_tokens = usage_data.get("prompt_tokens", 0)
                completion_tokens = usage_data.get("completion_tokens", 0)
                total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)
                
                logger.info("Dify 非流式响应 usage: prompt_tokens=%d, completion_tokens=%d, total_tokens=%d", prompt_tokens, completion_tokens, total_tokens)

                return ChatCompletionResponse(
                    id=data.get("id", f"chatcmpl-dify-{uuid.uuid4().hex[:24]}"),
                    model=model,
                    choices=[Choice(
                        index=0,
                        message=ChatMessage(role="assistant", content=answer or ""),
                        finish_reason="stop",
                    )],
                    usage=UsageInfo(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                    ),
                )

    # ── 流式 ────────────────────────────────────────────────────

    async def _stream_dify(
        self, headers: dict, body: dict, model: str
    ) -> AsyncGenerator[str, None]:
        """
        Dify 流式响应 SSE 事件：
          event: message  data: {"answer": "内容片段", "conversation_id": "...", "message_id": "..."}
          event: agent_message  data: {"answer": "内容片段", ...}   (Agent模式下)
          event: end      data: {"conversation_id": "...", "task_id": "..."}
          event: error    data: {"message": "错误信息"}

        转换为 OpenAI SSE：
          data: {"id":"...","choices":[{"index":0,"delta":{"content":"片段"}}]}
          ...
          data: [DONE]
        """
        import aiohttp
        url = self._build_dify_url()
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        logger.info("Dify 流式请求: url=%s, body=%s", url, json.dumps(body, ensure_ascii=False))

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=body, headers=headers) as resp:
                if resp.status != 200:
                    err_body = await resp.text()
                    raise ProviderException(
                        f"Dify 上游返回 {resp.status}: {err_body[:300]}",
                        status_code=502,
                        upstream_status=resp.status,
                    )

                event_id = f"chatcmpl-dify-{uuid.uuid4().hex[:24]}"
                idx = 0
                event_type = None
                prompt_tokens = 0
                completion_tokens = 0
                full_content = ""
                done_yielded = False

                async for raw_line in resp.content:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    if not line.startswith("data:"):
                        continue

                    raw_json = line[5:].strip()
                    # logger.info("Dify SSE data: %s", raw_json[:200])
                    try:
                        event_data = json.loads(raw_json)
                    except json.JSONDecodeError:
                        logger.warning("Dify SSE JSON decode error: %s", raw_json[:100])
                        continue

                    # 从 event_data 中获取事件类型
                    event_type = event_data.get("event", "")
                    # logger.info("Dify SSE event: %s", event_type)

                    # Dify 流结束：在 [DONE] 前发送含 usage 的最终 chunk
                    if event_type in ("end", "finished", "message_end"):
                        # 尝试从结束事件补齐 usage（有些 Dify 部署只在 end 事件返回 usage）
                        metadata = event_data.get("metadata", {}) or {}
                        usage_in_end = (metadata.get("usage", {}) or {})
                        prompt_tokens = usage_in_end.get("prompt_tokens", prompt_tokens)
                        completion_tokens = usage_in_end.get("completion_tokens", completion_tokens)

                        if not done_yielded:
                            done_yielded = True
                            final_chunk = {
                                "id": event_id,
                                "object": "chat.completion.chunk",
                                "model": model,
                                "choices": [{
                                    "index": idx,
                                    "delta": {},
                                    "finish_reason": "stop",
                                }],
                                "usage": {
                                    "prompt_tokens": prompt_tokens,
                                    "completion_tokens": completion_tokens,
                                    "total_tokens": prompt_tokens + completion_tokens,
                                },
                            }
                            yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    if event_type in ("message", "agent_message"):
                        # Dify 内容可能在 answer 或 text 字段
                        msg_content = (
                            event_data.get("answer", "")
                            or event_data.get("text", "")
                            or ""
                        )

                        # 尝试从其他字段获取内容
                        if not msg_content:
                            # 检查 event_data.content
                            if "content" in event_data:
                                msg_content = event_data.get("content", "")
                            # 检查 event_data.message
                            elif "message" in event_data:
                                message_obj = event_data.get("message")
                                if isinstance(message_obj, dict):
                                    msg_content = message_obj.get("content", "")

                        # 尝试从 metadata.usage 提取 token
                        metadata = event_data.get("metadata", {}) or {}
                        usage_in_chunk = (metadata.get("usage", {}) or {})
                        prompt_tokens = usage_in_chunk.get("prompt_tokens", prompt_tokens)
                        completion_tokens = usage_in_chunk.get("completion_tokens", completion_tokens)

                        full_content += msg_content
                        if msg_content:
                            chunk = {
                                "id": event_id,
                                "object": "chat.completion.chunk",
                                "model": model,
                                "choices": [{
                                    "index": idx,
                                    "delta": {"content": msg_content},
                                    "finish_reason": None,
                                }],
                            }
                            # logger.info("Dify SSE yielding chunk: %s", json.dumps(chunk, ensure_ascii=False)[:200])
                            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                    if event_type == "error":
                        err_msg = event_data.get("message", "Dify 流式错误")
                        raise ProviderException(err_msg, status_code=502)
