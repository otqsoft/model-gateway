"""
models/openai_models.py — OpenAI 兼容 Pydantic 模型
完整覆盖 /v1/chat/completions 请求与响应结构
"""
from __future__ import annotations
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field
import time
import uuid


# ── 请求体 ───────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "function", "tool"]
    content: Optional[Union[str, list]] = None
    name: Optional[str] = None
    function_call: Optional[dict] = None
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, list[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[dict[str, float]] = None
    user: Optional[str] = None
    functions: Optional[list[dict]] = None
    function_call: Optional[Union[str, dict]] = None
    tools: Optional[list[dict]] = None
    tool_choice: Optional[Union[str, dict]] = None
    response_format: Optional[dict] = None
    seed: Optional[int] = None
    # 思考模式开关：默认不开启，true 时由网关翻译为上游各厂商对应的参数
    thinking_mode: Optional[bool] = False

    class Config:
        extra = "allow"  # 允许额外字段透传


# ── 响应体（非流式）────────────────────────────────────────────

class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Choice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None
    logprobs: Optional[Any] = None


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[Choice]
    usage: UsageInfo = Field(default_factory=UsageInfo)
    system_fingerprint: Optional[str] = None


# ── 响应体（流式 SSE delta）────────────────────────────────────

class DeltaMessage(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    function_call: Optional[dict] = None
    tool_calls: Optional[list[dict]] = None


class StreamChoice(BaseModel):
    index: int
    delta: DeltaMessage
    finish_reason: Optional[str] = None
    logprobs: Optional[Any] = None


class ChatCompletionStreamResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[StreamChoice]
    usage: Optional[UsageInfo] = None


# ── /v1/models 响应 ───────────────────────────────────────────

class ModelObject(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "model-gateway"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelObject]
