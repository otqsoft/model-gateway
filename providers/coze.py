"""
providers/coze.py — Coze 智能体适配器
Coze API 格式与 OpenAI 差异较大，需要做请求/响应的双向转换：
  - OpenAI 格式 => Coze API 格式
  - Coze SSE/JSON 响应 => OpenAI ChatCompletion 格式
"""
from __future__ import annotations
import json
import uuid
import logging
from typing import AsyncGenerator, Optional, Union
from providers.base import BaseProvider, ProviderException
from models.openai_models import (
    ChatCompletionRequest, ChatCompletionResponse,
    Choice, ChatMessage, UsageInfo
)

logger = logging.getLogger("gateway.provider.coze")


class CozeProvider(BaseProvider):
    """
    Coze（扣子）智能体适配器
    支持流式(/v1/chat/completions stream=true)和非流式
    """
    provider_name = "coze"

    def __init__(self, base_url: str, api_key: str, bot_id: str, **kwargs):
        super().__init__(base_url, api_key, **kwargs)
        self.bot_id = bot_id  # Coze 智能体 ID，从 model_mapping.extra_headers 或 provider.extra_headers 中提取

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        upstream_model: str,   # Coze 中 upstream_model = bot_id
    ) -> Union[ChatCompletionResponse, AsyncGenerator[str, None]]:
        """
        upstream_model 在 Coze 中即 bot_id（智能体 ID）
        user 字段透传到 Coze 的 user_id
        """
        headers = self._build_headers()
        # Coze API URL 固定
        url = "https://api.coze.cn/v3/chat"

        body = self._coze_request_body(request, self.bot_id)

        if request.stream:
            return self._stream_coze(url, headers, body, self.bot_id)
        else:
            data, _ = await self._do_non_stream(url, headers, body)
            return self._parse_non_stream_response(data, self.bot_id)

    def _coze_request_body(self, request: ChatCompletionRequest, bot_id: str) -> dict:
        """OpenAI 格式 → Coze API 格式"""
        # 将 messages 转为 Coze 的 additional_messages
        coze_messages = []
        for msg in request.messages:
            role = msg.role if msg.role in ("user", "assistant", "system") else "user"
            coze_messages.append({
                "role": role,
                "content": msg.content or "",
                "content_type": "text",
                "type": "question" if role == "user" else "answer"
            })

        body = {
            "bot_id": bot_id,
            "stream": bool(request.stream),
            "additional_messages": coze_messages,
            "parameters": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_tokens": request.max_tokens,
            },
        }
        # Coze 使用 user_id 标识用户，来自请求的 user 字段
        if request.user:
            body["user_id"] = request.user
        else:
            body["user_id"] = "gateway_user"

        return body

    def _build_headers(self) -> dict:
        """Coze 使用 Authorization: Bearer {pat_token}"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        headers.update(self.extra_headers or {})
        return headers

    def _parse_non_stream_response(self, data: dict, model: str) -> ChatCompletionResponse:
        """
        Coze 非流式响应：
        {
          "code": 0,
          "msg": "success",
          "data": {
            "conversation_id": "...",
            "messages": [...]
          }
        }
        """
        code = data.get("code")
        if code != 0 and code is not None:
            msg = data.get("msg", str(data))
            raise ProviderException(f"Coze API 错误: {msg}", status_code=502, upstream_status=0)

        coze_data = data.get("data", {})
        messages = coze_data.get("messages", [])

        # 从 messages 中找到 assistant 的回复
        assistant_content = ""
        for m in messages:
            if m.get("role") == "assistant" and m.get("type") == "answer":
                assistant_content = m.get("content", "")
                break
        
        # 如果没有找到 assistant 的回复，尝试从其他地方获取
        if not assistant_content:
            # 检查 coze_data 是否直接包含 content
            if isinstance(coze_data, dict):
                assistant_content = coze_data.get("content", "")
                # 检查 coze_data.data 是否包含 content
                if not assistant_content and "data" in coze_data:
                    data_obj = coze_data.get("data")
                    if isinstance(data_obj, dict):
                        assistant_content = data_obj.get("content", "")

        choices = [Choice(
            index=0,
            message=ChatMessage(role="assistant", content=assistant_content),
            finish_reason="stop",
        )]

        # 尝试从 usage 中提取 token
        usage_data = coze_data.get("usage", {})
        usage = UsageInfo(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
            total_tokens=(
                usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
            ),
        )

        return ChatCompletionResponse(
            id=f"chatcmpl-coze-{uuid.uuid4().hex[:24]}",
            model=model,
            choices=choices,
            usage=usage,
        )

    async def _stream_coze(
        self, url: str, headers: dict, body: dict, model: str
    ) -> AsyncGenerator[str, None]:
        """
        Coze 流式响应是 SSE，每行格式：
          event: message
          data: {...}

        需要转换为 OpenAI 的 SSE 格式：
          data: {"id":"...","choices":[{"index":0,"delta":{"content":"..."}}]}

        处理的事件：
          - message: 内容片段
          - done: 结束
          - error: 错误
        """
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=body, headers=headers) as resp:
                    if resp.status != 200:
                        err_body = await resp.text()
                        raise ProviderException(
                            f"Coze 上游返回 {resp.status}: {err_body[:300]}",
                            status_code=502,
                            upstream_status=resp.status,
                        )

                    event_id = f"chatcmpl-coze-{uuid.uuid4().hex[:24]}"
                    idx = 0
                    event_type = None  # SSE 事件类型，event: 行才赋值

                    async for raw_line in resp.content:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line:
                            continue

                        # Coze SSE 格式：event: message / data: {...}
                        if line.startswith("event:"):
                            event_type = line.split(":", 1)[1].strip()
                            # logger.info("Coze SSE event: %s", event_type)
                            continue

                        # data 行必须跟在 event 行后面才处理，避免孤立的 data 行导致未定义 event_type
                        if not line.startswith("data:"):
                            continue

                        raw_json = line[5:].strip()
                        # logger.info("Coze SSE data: %s", raw_json[:200])

                        try:
                            event_data = json.loads(raw_json)
                        except json.JSONDecodeError:
                            logger.warning("Coze SSE JSON decode error: %s", raw_json[:100])
                            continue

                        # Coze done 事件
                        if event_type == "done":
                            # logger.info("Coze SSE done event")
                            # 发送 [DONE]
                            yield "data: [DONE]\n\n"
                            return

                        # 处理 Coze 实际的消息事件类型
                        if event_type in ["conversation.message.delta", "conversation.message.completed"]:
                            # 从 event_data 中获取内容
                            msg_content = event_data.get("content", "")
                            
                            # logger.info("Coze SSE message content: %s", msg_content)
                            if msg_content:
                                choice = {
                                    "index": idx,
                                    "delta": {"content": msg_content},
                                    "finish_reason": None,
                                }
                                chunk = {
                                    "id": event_id,
                                    "object": "chat.completion.chunk",
                                    "model": model,  # 使用 upstream_model 而非 self.bot_id
                                    "choices": [choice],
                                }
                                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                        if event_type == "error":
                            err_msg = event_data.get("msg", "Coze 流式错误")
                            raise ProviderException(err_msg, status_code=502)

        except aiohttp.ClientError as e:
            raise ProviderException(str(e), status_code=502)


class CozeProviderFactory:
    """
    从 provider 配置 + model_mapping.extra_headers 中构建 CozeProvider
    优先级：model_mapping.extra_headers['bot_id'] > provider.extra_headers['bot_id']
    """
    @staticmethod
    def from_config(provider_row: dict, model_row: dict) -> CozeProvider:
        """
        Args:
            provider_row: 从 model_providers 表读取的行
            model_row: 从 model_mapping 表读取的行（含 extra_headers）
        """
        from core.security import decrypt_api_key

        # 解密 PAT token
        encrypted_key = provider_row.get("api_key", "")
        api_key = decrypt_api_key(encrypted_key) if encrypted_key else ""

        base_url = provider_row.get("base_url", "")

        # 优先从 model_mapping 的 extra_headers 读 bot_id
        extra = model_row.get("extra_headers") or {}
        if isinstance(extra, str):
            extra = json.loads(extra) if extra else {}

        bot_id = extra.get("bot_id", "") or provider_row.get("extra_headers", {}).get("bot_id", "")

        if not bot_id:
            logger.warning("Coze Provider 未配置 bot_id，请在模型映射的 extra_headers 中设置 bot_id")

        return CozeProvider(
            base_url=base_url,
            api_key=api_key,
            bot_id=bot_id,
            timeout_seconds=provider_row.get("timeout_seconds", 120),
            extra_headers=extra,
        )
