"""
core/anthropic_converter.py — Anthropic ↔ OpenAI 格式双向转换
- anthropic_to_openai:  AnthropicRequest  -> ChatCompletionRequest
- openai_to_anthropic:  ChatCompletionResponse -> AnthropicResponse
- 流式：把 OpenAI SSE chunks 转成 Anthropic SSE 事件序列
"""
from __future__ import annotations
import json
import logging
from typing import Any, Optional
from models.anthropic_models import (
    AnthropicRequest,
    ResponseTextBlock, ResponseToolUseBlock, AnthropicResponse, AnthropicUsage,
)
from models.openai_models import (
    ChatCompletionRequest, ChatMessage, ChatCompletionResponse,
)

logger = logging.getLogger("gateway.anthropic.converter")


# ── Anthropic 请求 → OpenAI 请求 ─────────────────────────────

def anthropic_to_openai(req: AnthropicRequest) -> ChatCompletionRequest:
    """将 Anthropic /v1/messages 请求转换为 OpenAI /v1/chat/completions 请求"""
    openai_messages: list[ChatMessage] = []

    # 1. system 字段 → 第一条 system 消息
    if req.system:
        if isinstance(req.system, str):
            openai_messages.append(ChatMessage(role="system", content=req.system))
        elif isinstance(req.system, list):
            # Anthropic 允许 system 是数组（带 cache_control 等），合并为纯文本
            sys_text = "\n\n".join(
                blk.get("text", "") for blk in req.system
                if isinstance(blk, dict) and blk.get("type") == "text"
            )
            if sys_text:
                openai_messages.append(ChatMessage(role="system", content=sys_text))

    # 2. 逐条转换 messages
    for msg in req.messages:
        role = msg.role  # user / assistant
        content = msg.content

        if isinstance(content, str):
            openai_messages.append(ChatMessage(role=role, content=content))
            continue

        # 列表内容：分别处理 text / image / tool_use / tool_result
        text_parts: list[str] = []
        image_urls: list[dict] = []
        tool_calls: list[dict] = []
        tool_call_id: Optional[str] = None
        tool_result_content: Optional[str] = None

        for blk in content:
            blk_type = blk.type if hasattr(blk, "type") else blk.get("type")

            if blk_type == "text":
                text_parts.append(blk.text if hasattr(blk, "text") else blk.get("text", ""))

            elif blk_type == "image":
                src = blk.source if hasattr(blk, "source") else blk.get("source", {})
                if src.get("type") == "base64":
                    url = f"data:{src.get('media_type', 'image/png')};base64,{src.get('data', '')}"
                else:
                    url = src.get("url", "")
                if url:
                    image_urls.append({"type": "image_url", "image_url": {"url": url}})

            elif blk_type == "tool_use":
                # assistant 消息中的工具调用
                tool_calls.append({
                    "id": blk.id if hasattr(blk, "id") else blk.get("id"),
                    "type": "function",
                    "function": {
                        "name": blk.name if hasattr(blk, "name") else blk.get("name"),
                        "arguments": json.dumps(
                            blk.input if hasattr(blk, "input") else blk.get("input", {}),
                            ensure_ascii=False,
                        ),
                    },
                })

            elif blk_type == "tool_result":
                # user 消息中的工具结果 → OpenAI 的 role=tool 消息
                tool_call_id = blk.tool_use_id if hasattr(blk, "tool_use_id") else blk.get("tool_use_id")
                rc = blk.content if hasattr(blk, "content") else blk.get("content")
                if isinstance(rc, list):
                    # 提取 text 部分
                    tool_result_content = "\n".join(
                        b.get("text", "") for b in rc
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                else:
                    tool_result_content = rc or ""

        # 组装消息
        if role == "assistant" and tool_calls:
            openai_messages.append(ChatMessage(
                role="assistant",
                content="".join(text_parts) or None,
                tool_calls=tool_calls,
            ))
        elif role == "user" and tool_call_id is not None:
            # 工具结果作为 role=tool 单独消息
            openai_messages.append(ChatMessage(
                role="tool",
                content=tool_result_content or "",
                tool_call_id=tool_call_id,
            ))
            # 如果还有额外文本，作为 user 消息追加
            if text_parts and "".join(text_parts).strip():
                openai_messages.append(ChatMessage(role="user", content="".join(text_parts)))
        else:
            # 普通文本 + 图片混合
            if image_urls:
                parts: list[dict] = []
                if text_parts:
                    parts.append({"type": "text", "text": "".join(text_parts)})
                parts.extend(image_urls)
                openai_messages.append(ChatMessage(role=role, content=parts))
            else:
                openai_messages.append(ChatMessage(role=role, content="".join(text_parts)))

    # 3. tools 字段转换
    openai_tools = None
    if req.tools:
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.input_schema or {"type": "object", "properties": {}},
                },
            }
            for t in req.tools
        ]

    # 4. tool_choice 转换
    openai_tool_choice = None
    if req.tool_choice:
        if isinstance(req.tool_choice, str):
            # auto / any / none → auto / required / none
            mapping = {"auto": "auto", "any": "required", "none": "none"}
            openai_tool_choice = mapping.get(req.tool_choice, "auto")
        elif isinstance(req.tool_choice, dict):
            name = req.tool_choice.get("name")
            if name:
                openai_tool_choice = {"type": "function", "function": {"name": name}}

    # 5. stop_sequences → stop
    openai_stop = req.stop_sequences if req.stop_sequences else None

    return ChatCompletionRequest(
        model=req.model,
        messages=openai_messages,
        temperature=req.temperature,
        top_p=req.top_p,
        stream=bool(req.stream),
        max_tokens=req.max_tokens,
        stop=openai_stop,
        user=req.user,
        tools=openai_tools,
        tool_choice=openai_tool_choice,
    )


# ── OpenAI 响应 → Anthropic 响应 ─────────────────────────────

def _finish_to_stop_reason(finish: Optional[str]) -> str:
    """OpenAI finish_reason → Anthropic stop_reason"""
    return {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
        "function_call": "tool_use",
        "content_filter": "end_turn",
    }.get(finish or "", "end_turn")


def _extract_text_and_tool_calls(msg: ChatMessage) -> tuple[str, list[dict]]:
    """从 OpenAI assistant 消息中提取文本和工具调用"""
    text = ""
    if isinstance(msg.content, str):
        text = msg.content
    elif isinstance(msg.content, list):
        # 罕见情况：content 是数组
        for part in msg.content:
            if isinstance(part, dict) and part.get("type") == "text":
                text += part.get("text", "")

    tool_calls = msg.tool_calls or []
    return text, tool_calls


def openai_to_anthropic(resp: ChatCompletionResponse) -> AnthropicResponse:
    """将 OpenAI ChatCompletion 响应转换为 Anthropic Messages 响应"""
    content_blocks: list = []
    stop_reason = "end_turn"

    if resp.choices:
        choice = resp.choices[0]
        stop_reason = _finish_to_stop_reason(choice.finish_reason)
        text, tool_calls = _extract_text_and_tool_calls(choice.message)

        if text:
            content_blocks.append(ResponseTextBlock(type="text", text=text))

        for tc in tool_calls:
            try:
                args = json.loads(tc.get("function", {}).get("arguments", "{}"))
            except (json.JSONDecodeError, AttributeError):
                args = {}
            content_blocks.append(ResponseToolUseBlock(
                type="tool_use",
                id=tc.get("id", "tool_default_id"),
                name=tc.get("function", {}).get("name", ""),
                input=args,
            ))

    if not content_blocks:
        content_blocks.append(ResponseTextBlock(type="text", text=""))

    usage = resp.usage
    return AnthropicResponse(
        id=resp.id.replace("chatcmpl-", "msg_") if resp.id.startswith("chatcmpl-") else resp.id,
        model=resp.model,
        content=content_blocks,
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=AnthropicUsage(
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        ),
    )


# ── 流式：OpenAI SSE → Anthropic SSE ──────────────────────────

async def openai_stream_to_anthropic(
    openai_stream,
    model: str,
):
    """
    将 OpenAI SSE 流（"data: {...}\n\n" 行）转换为 Anthropic SSE 事件流。
    生成器 yield 形如 "event: xxx\ndata: {...}\n\n" 的字符串。

    Anthropic 事件序列：
      message_start
      content_block_start  (index=0, text)
      content_block_delta  (text_delta) × N
      content_block_stop   (index=0)
      [如有 tool_use：再发一组 start/delta/stop]
      message_delta        (stop_reason + usage)
      message_stop
    """
    msg_id = f"msg_{__import__('uuid').uuid4().hex[:24]}"

    # 1. message_start
    yield _sse("message_start", {
        "type": "message_start",
        "message": {
            "id": msg_id,
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": model,
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
    })

    # 状态机
    text_block_opened = False
    tool_blocks: dict[int, dict] = {}  # index → {id, name, args_buffer}
    next_index = 0
    final_stop_reason = "end_turn"
    final_usage = {"input_tokens": 0, "output_tokens": 0}

    try:
        async for raw_line in openai_stream:
            if not raw_line:
                continue
            line_str = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, (bytes, bytearray)) else raw_line
            line_str = line_str.strip()
            if not line_str.startswith("data:"):
                continue
            payload = line_str[5:].strip()
            if payload == "[DONE]":
                break
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                continue

            # 检测错误
            if "error" in chunk:
                yield _sse("error", {
                    "type": "error",
                    "error": {
                        "type": "upstream_error",
                        "message": chunk["error"].get("message", "upstream error"),
                    },
                })
                return

            choices = chunk.get("choices") or []
            if not choices:
                # 仅含 usage 的最终 chunk
                u = chunk.get("usage")
                if u:
                    final_usage["input_tokens"] = u.get("prompt_tokens", final_usage["input_tokens"])
                    final_usage["output_tokens"] = u.get("completion_tokens", final_usage["output_tokens"])
                continue

            choice = choices[0]
            delta = choice.get("delta", {}) or {}
            finish_reason = choice.get("finish_reason")

            # 文本增量
            text_delta = delta.get("content")
            if text_delta:
                if not text_block_opened:
                    yield _sse("content_block_start", {
                        "type": "content_block_start",
                        "index": next_index,
                        "content_block": {"type": "text", "text": ""},
                    })
                    text_block_opened = True
                    current_text_index = next_index
                    next_index += 1
                yield _sse("content_block_delta", {
                    "type": "content_block_delta",
                    "index": current_text_index,
                    "delta": {"type": "text_delta", "text": text_delta},
                })

            # 工具调用增量
            tool_calls = delta.get("tool_calls") or []
            for tc in tool_calls:
                tc_idx = tc.get("index", 0)
                if tc_idx not in tool_blocks:
                    # 关闭已打开的文本块
                    if text_block_opened:
                        yield _sse("content_block_stop", {
                            "type": "content_block_stop",
                            "index": current_text_index,
                        })
                        text_block_opened = False
                    # 开启新 tool_use 块
                    block_index = next_index
                    next_index += 1
                    tool_blocks[tc_idx] = {
                        "block_index": block_index,
                        "id": tc.get("id", f"toolu_{__import__('uuid').uuid4().hex[:24]}"),
                        "name": tc.get("function", {}).get("name", ""),
                        "args_buffer": "",
                    }
                    yield _sse("content_block_start", {
                        "type": "content_block_start",
                        "index": block_index,
                        "content_block": {
                            "type": "tool_use",
                            "id": tool_blocks[tc_idx]["id"],
                            "name": tool_blocks[tc_idx]["name"],
                            "input": {},
                        },
                    })
                # 增量 arguments
                args_delta = tc.get("function", {}).get("arguments", "")
                if args_delta:
                    tool_blocks[tc_idx]["args_buffer"] += args_delta
                    yield _sse("content_block_delta", {
                        "type": "content_block_delta",
                        "index": tool_blocks[tc_idx]["block_index"],
                        "delta": {"type": "input_json_delta", "partial_json": args_delta},
                    })

            # usage（部分 provider 在最后 chunk 带 usage）
            u = chunk.get("usage")
            if u:
                final_usage["input_tokens"] = u.get("prompt_tokens", final_usage["input_tokens"])
                final_usage["output_tokens"] = u.get("completion_tokens", final_usage["output_tokens"])

            if finish_reason:
                final_stop_reason = _finish_to_stop_reason(finish_reason)

        # 关闭文本块
        if text_block_opened:
            yield _sse("content_block_stop", {
                "type": "content_block_stop",
                "index": current_text_index,
            })
            text_block_opened = False

        # 关闭所有 tool 块
        for tb in tool_blocks.values():
            yield _sse("content_block_stop", {
                "type": "content_block_stop",
                "index": tb["block_index"],
            })

        # message_delta
        yield _sse("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": final_stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": final_usage["output_tokens"]},
        })

        # message_stop
        yield _sse("message_stop", {"type": "message_stop"})

    except Exception as e:
        logger.exception("Anthropic 流式转换异常: %s", e)
        yield _sse("error", {
            "type": "error",
            "error": {"type": "internal_error", "message": f"stream conversion error: {e}"},
        })


def _sse(event: str, data: dict) -> str:
    """构造 Anthropic SSE 事件块"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
