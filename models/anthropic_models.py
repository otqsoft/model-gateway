"""
models/anthropic_models.py — Anthropic Messages API 兼容 Pydantic 模型
覆盖 /v1/messages 请求与响应结构（文本 + 工具调用场景）
"""
from __future__ import annotations
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field
import time
import uuid


# ── 请求体 ───────────────────────────────────────────────────

class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImageSource(BaseModel):
    type: Literal["base64", "url"]
    media_type: str
    data: Optional[str] = None  # base64 时填
    url: Optional[str] = None   # url 时填


class ImageBlock(BaseModel):
    type: Literal["image"] = "image"
    source: ImageSource


class ToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict


class ToolResultBlock(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: Optional[Union[str, list]] = None
    is_error: Optional[bool] = False


ContentBlock = Union[TextBlock, ImageBlock, ToolUseBlock, ToolResultBlock]


class AnthropicMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Union[str, list[ContentBlock]]


class ToolDef(BaseModel):
    name: str
    description: Optional[str] = None
    input_schema: dict


class AnthropicRequest(BaseModel):
    model: str
    messages: list[AnthropicMessage]
    max_tokens: int = 1024
    system: Optional[Union[str, list[dict]]] = None
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    top_k: Optional[int] = None
    stream: Optional[bool] = False
    stop_sequences: Optional[list[str]] = None
    metadata: Optional[dict] = None
    tools: Optional[list[ToolDef]] = None
    tool_choice: Optional[Union[str, dict]] = None
    user: Optional[str] = None

    class Config:
        extra = "allow"


# ── 响应体（非流式）────────────────────────────────────────────

class ResponseTextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ResponseToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict


class AnthropicUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class AnthropicResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:24]}")
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    model: str
    content: list[Union[ResponseTextBlock, ResponseToolUseBlock]]
    stop_reason: Optional[str] = "end_turn"
    stop_sequence: Optional[str] = None
    usage: AnthropicUsage = Field(default_factory=AnthropicUsage)


# ── 流式 SSE 事件载荷 ─────────────────────────────────────────

class MessageStartEvent(BaseModel):
    type: Literal["message_start"] = "message_start"
    message: dict


class ContentBlockStartEvent(BaseModel):
    type: Literal["content_block_start"] = "content_block_start"
    index: int
    content_block: dict


class ContentBlockDeltaEvent(BaseModel):
    type: Literal["content_block_delta"] = "content_block_delta"
    index: int
    delta: dict


class ContentBlockStopEvent(BaseModel):
    type: Literal["content_block_stop"] = "content_block_stop"
    index: int


class MessageDeltaEvent(BaseModel):
    type: Literal["message_delta"] = "message_delta"
    delta: dict
    usage: dict


class MessageStopEvent(BaseModel):
    type: Literal["message_stop"] = "message_stop"


class AnthropicError(BaseModel):
    type: Literal["error"] = "error"
    error: dict
