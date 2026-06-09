"""
api/v1/chat.py — /v1/chat/completions OpenAI 兼容接口
完整实现：认证 → 时段校验 → 限流 → 路由 → 生命周期追踪 → 计费
"""
from __future__ import annotations
import json
import logging
import asyncio
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from middleware.auth import authenticate_request
from middleware.time_control import check_time_access
from core.limiter import ConcurrencyGuard, RateLimitExceeded
from core.utils import new_request_id, now_ms, calc_duration_ms, sse_done
from models.openai_models import ChatCompletionRequest, ChatCompletionResponse
from models.db_models import ApiKeyRow
from crud.request_logs import (
    create_request_log, update_log_running,
    update_log_success, update_log_error,
)
from crud.billing import create_billing_record
from crud.api_keys import increment_key_stats
from crud.models import get_model_by_alias
from crud.providers import get_provider_by_name
from crud.agents import get_agent_by_name, increment_agent_stats
from providers.registry import get_provider, get_agent_provider
from providers.base import ProviderException, TimeoutException

logger = logging.getLogger("gateway.chat")
router = APIRouter()


@router.post("/v1/chat/completions", summary="OpenAI 兼容 /v1/chat/completions 接口", tags=["会话"])
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    key_row: ApiKeyRow = Depends(authenticate_request),
):
    """
    OpenAI 兼容 /v1/chat/completions 接口
    支持 stream / non-stream
    """
    # ── 1. 时段访问控制 ────────────────────────────────────────
    check_time_access(key_row)

    # ── 2. 模型白名单校验 ──────────────────────────────────────
    model_alias = body.model
    if model_alias not in key_row.allowed_models:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "message": f"模型 '{model_alias}' 不在该 Key 的访问白名单中",
                    "type": "permission_error",
                    "code": "model_not_allowed",
                }
            },
        )

    # ── 3a. 判断是否为智能体请求（alias 以 "agent:" 前缀区分）────
    is_agent_request = model_alias.startswith("agent:")
    if is_agent_request:
        return await _handle_agent_request(request, body, key_row, model_alias)

    # ── 3. 查找模型映射 ─────────────────────────────────────────
    model_row = await get_model_by_alias(model_alias)
    if not model_row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"模型 '{model_alias}' 不存在或已禁用",
                    "type": "invalid_request_error",
                }
            },
        )

    provider_name = model_row["provider_name"]
    upstream_model = model_row["upstream_model"]

    # ── 4a. 注入模型级系统提示词 ───────────────────────────────
    system_prompt = (model_row.get("system_prompt") or "").strip()
    if system_prompt:
        body = _inject_system_prompt(body, system_prompt)

    # ── 4. 查找厂商获取并发配置 ────────────────────────────────
    provider_row = await get_provider_by_name(provider_name)
    if not provider_row or not provider_row.get("is_enabled"):
        raise HTTPException(status_code=503, detail={"error": {"message": "上游厂商不可用"}})

    provider_max_concurrency = provider_row.get("max_concurrency", 50)

    # ── 5. 创建请求日志（pending）────────────────────────────────
    request_id = new_request_id()
    client_ip = request.client.host if request.client else "unknown"
    is_stream = bool(body.stream)

    await create_request_log(
        request_id=request_id,
        api_key_id=key_row.id,
        key_id=key_row.key_id,
        model_alias=model_alias,
        is_stream=is_stream,
        client_ip=client_ip,
    )

    # ── 6. 三级并发限流 ─────────────────────────────────────────
    start_ms = now_ms()
    try:
        guard = ConcurrencyGuard(
            key_id=key_row.key_id,
            key_max_concurrency=key_row.max_concurrency,
            provider_name=provider_name,
            provider_max_concurrency=provider_max_concurrency,
        )
    except Exception:
        pass  # 构造不会异常

    try:
        async with guard:
            # 更新状态为 running
            await update_log_running(request_id, provider_name, upstream_model)

            # 获取厂商适配器（Coze 需要 model_row 中的 bot_id）
            provider = await get_provider(provider_name, model_row=model_row)

            if is_stream:
                # ── 流式处理 ──────────────────────────────────
                return StreamingResponse(
                    _stream_generator(
                        request_id=request_id,
                        provider=provider,
                        body=body,
                        upstream_model=upstream_model,
                        model_alias=model_alias,
                        provider_name=provider_name,
                        key_row=key_row,
                        model_row=model_row,
                        start_ms=start_ms,
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no",
                        "X-Request-Id": request_id,
                    },
                )
            else:
                # ── 非流式处理 ────────────────────────────────
                result = await provider.chat_completion(body, upstream_model)
                duration_ms = calc_duration_ms(start_ms)

                usage = result.usage
                await update_log_success(
                    request_id=request_id,
                    upstream_status=200,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    ttft_ms=None,
                    duration_ms=duration_ms,
                )

                # 计费
                bill = await create_billing_record(
                    request_id=request_id,
                    api_key_id=key_row.id,
                    key_id=key_row.key_id,
                    model_alias=model_alias,
                    provider_name=provider_name,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    input_price=float(model_row["input_price"]),
                    output_price=float(model_row["output_price"]),
                )
                await increment_key_stats(key_row.id, bill["total_tokens"], bill["total_cost"])

                # 覆盖返回的 model 名为客户端请求的别名
                result.model = model_alias
                return JSONResponse(
                    content=result.model_dump(),
                    headers={"X-Request-Id": request_id},
                )

    except RateLimitExceeded as e:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, None, f"Rate limited: {e.level}", duration_ms)
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "message": f"并发限流（{e.level}）超出限制，请稍后重试",
                    "type": "rate_limit_error",
                    "code": "rate_limit_exceeded",
                }
            },
        )
    except TimeoutException:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, 0, "Request timeout", duration_ms, is_timeout=True)
        raise HTTPException(
            status_code=504,
            detail={"error": {"message": "上游请求超时", "type": "timeout_error"}},
        )
    except ProviderException as e:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, e.upstream_status, str(e), duration_ms)
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": {"message": str(e), "type": "upstream_error"}},
        )
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, None, str(e), duration_ms)
        logger.exception("[%s] 未知错误: %s", request_id, e)
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "内部服务错误", "type": "internal_error"}},
        )


async def _handle_agent_request(
    request: Request,
    body: ChatCompletionRequest,
    key_row: ApiKeyRow,
    model_alias: str,
) -> JSONResponse | StreamingResponse:
    """
    处理 agent:xxx 格式的智能体调用请求。
    - model_alias 格式：agent:<agent_name>
    - 从 agent_configs 取智能体配置（含专属 api_key、bot_id）
    - 从关联供应商取 base_url / timeout / max_concurrency
    - 调用 get_agent_provider() 构建适配器（使用智能体的 api_key 而非供应商的 api_key）
    """
    agent_name = model_alias[len("agent:"):]   # 去掉前缀

    # 查找智能体配置
    agent_row = await get_agent_by_name(agent_name)
    if not agent_row or not agent_row.get("is_enabled"):
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"智能体 '{agent_name}' 不存在或已禁用",
                    "type": "invalid_request_error",
                }
            },
        )

    provider_name = agent_row["provider_name"]

    # 查找智能体供应商获取并发配置
    provider_row = await get_provider_by_name(provider_name)
    if not provider_row or not provider_row.get("is_enabled"):
        raise HTTPException(
            status_code=503,
            detail={"error": {"message": f"智能体供应商 '{provider_name}' 不可用"}},
        )
    provider_max_concurrency = provider_row.get("max_concurrency", 20)

    # 创建请求日志（pending）
    request_id = new_request_id()
    client_ip = request.client.host if request.client else "unknown"
    is_stream = bool(body.stream)

    await create_request_log(
        request_id=request_id,
        api_key_id=key_row.id,
        key_id=key_row.key_id,
        model_alias=model_alias,
        is_stream=is_stream,
        client_ip=client_ip,
    )

    start_ms = now_ms()
    guard = ConcurrencyGuard(
        key_id=key_row.key_id,
        key_max_concurrency=key_row.max_concurrency,
        provider_name=provider_name,
        provider_max_concurrency=provider_max_concurrency,
    )

    try:
        async with guard:
            await update_log_running(request_id, provider_name, agent_name)

            # 用智能体自己的 api_key 构建 Provider
            provider = await get_agent_provider(agent_row, provider_row)

            # upstream_model 对 Coze 来说就是 bot_id，对 Dify 来说无实质意义
            upstream_model = agent_row.get("bot_id") or agent_name

            if is_stream:
                return StreamingResponse(
                    _agent_stream_generator(
                        request_id=request_id,
                        provider=provider,
                        body=body,
                        upstream_model=upstream_model,
                        model_alias=model_alias,
                        provider_name=provider_name,
                        key_row=key_row,
                        agent_row=agent_row,
                        start_ms=start_ms,
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no",
                        "X-Request-Id": request_id,
                    },
                )
            else:
                result = await provider.chat_completion(body, upstream_model)
                duration_ms = calc_duration_ms(start_ms)

                usage = result.usage
                await update_log_success(
                    request_id=request_id,
                    upstream_status=200,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    ttft_ms=None,
                    duration_ms=duration_ms,
                )

                # 计费 & 智能体统计（价格按 0 处理，或后续可在 agent_configs 加价格字段）
                bill = await create_billing_record(
                    request_id=request_id,
                    api_key_id=key_row.id,
                    key_id=key_row.key_id,
                    model_alias=model_alias,
                    provider_name=provider_name,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    input_price=0.0,
                    output_price=0.0,
                )
                await increment_key_stats(key_row.id, bill["total_tokens"], bill["total_cost"])
                await increment_agent_stats(agent_row["id"], bill["total_tokens"], bill["total_cost"])

                result.model = model_alias
                return JSONResponse(
                    content=result.model_dump(),
                    headers={"X-Request-Id": request_id},
                )

    except RateLimitExceeded as e:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, None, f"Rate limited: {e.level}", duration_ms)
        raise HTTPException(
            status_code=429,
            detail={"error": {"message": f"并发限流超出，请稍后重试", "type": "rate_limit_error"}},
        )
    except TimeoutException:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, 0, "Request timeout", duration_ms, is_timeout=True)
        raise HTTPException(status_code=504, detail={"error": {"message": "上游请求超时"}})
    except ProviderException as e:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, e.upstream_status, str(e), duration_ms)
        raise HTTPException(status_code=e.status_code, detail={"error": {"message": str(e)}})
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, None, str(e), duration_ms)
        logger.exception("[%s] 智能体调用未知错误: %s", request_id, e)
        raise HTTPException(status_code=500, detail={"error": {"message": "内部服务错误"}})


async def _agent_stream_generator(
    request_id: str,
    provider,
    body: ChatCompletionRequest,
    upstream_model: str,
    model_alias: str,
    provider_name: str,
    key_row: ApiKeyRow,
    agent_row: dict,
    start_ms: int,
) -> AsyncGenerator[bytes, None]:
    """智能体流式 SSE 生成器（与模型路由逻辑相同，额外累计 agent 统计）"""
    ttft_ms: Optional[int] = None
    prompt_tokens = 0
    completion_tokens = 0
    upstream_status = 200
    error_msg: Optional[str] = None
    is_error = False
    first_chunk = True

    try:
        stream_gen = await provider.chat_completion(body, upstream_model)

        async for raw_line in stream_gen:
            if first_chunk and raw_line.startswith("data:"):
                ttft_ms = calc_duration_ms(start_ms)
                first_chunk = False

            if raw_line.startswith("data:") and not raw_line.startswith("data: [DONE]"):
                try:
                    chunk_str = raw_line[5:].strip()
                    chunk = json.loads(chunk_str)
                    usage = chunk.get("usage")
                    if usage:
                        prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                        completion_tokens = usage.get("completion_tokens", completion_tokens)
                    chunk["model"] = model_alias
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")
                    continue
                except Exception:
                    pass

            yield f"{raw_line}\n\n".encode("utf-8") if not raw_line.endswith("\n") else raw_line.encode("utf-8")

        yield b"data: [DONE]\n\n"

    except TimeoutException:
        is_error = True; upstream_status = 0; error_msg = "Request timeout"
        yield b"data: {\"error\":{\"message\":\"\\u4e0a\\u6e38\\u8bf7\\u6c42\\u8d85\\u65f6\"}}\n\n"
    except ProviderException as e:
        is_error = True; upstream_status = e.upstream_status; error_msg = str(e)
        yield f"data: {json.dumps({'error':{'message':str(e)}}, ensure_ascii=False)}\n\n".encode("utf-8")
    except Exception as e:
        is_error = True; upstream_status = 0; error_msg = str(e)
        logger.exception("[%s] 智能体流式异常: %s", request_id, e)
        yield b"data: {\"error\":{\"message\":\"\\u5185\\u90e8\\u670d\\u52a1\\u5668\\u9519\\u8bef\"}}\n\n"
    finally:
        duration_ms = calc_duration_ms(start_ms)
        if is_error:
            await update_log_error(request_id, upstream_status, error_msg or "stream error", duration_ms,
                                   is_timeout=(upstream_status == 0 and error_msg == "Request timeout"))
        else:
            await update_log_success(request_id=request_id, upstream_status=upstream_status,
                                     prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                                     ttft_ms=ttft_ms, duration_ms=duration_ms)
            total_tokens = prompt_tokens + completion_tokens
            total_cost = 0.0
            if total_tokens > 0:
                bill = await create_billing_record(
                    request_id=request_id, api_key_id=key_row.id, key_id=key_row.key_id,
                    model_alias=model_alias, provider_name=provider_name,
                    prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                    input_price=0.0, output_price=0.0,
                )
                total_tokens = bill["total_tokens"]
                total_cost = bill["total_cost"]

            # 即使 usage 缺失导致 tokens=0，也要统计“调用次数”
            await increment_key_stats(key_row.id, int(total_tokens), float(total_cost))
            await increment_agent_stats(agent_row["id"], int(total_tokens), float(total_cost))


async def _stream_generator(
    request_id: str,
    provider,
    body: ChatCompletionRequest,
    upstream_model: str,
    model_alias: str,
    provider_name: str,
    key_row: ApiKeyRow,
    model_row: dict,
    start_ms: int,
) -> AsyncGenerator[bytes, None]:
    """
    流式 SSE 生成器
    - 转发上游 SSE 行
    - 追踪 TTFT（首包时间）
    - 解析 usage 计费
    - 更新生命周期日志
    """
    ttft_ms: Optional[int] = None
    prompt_tokens = 0
    completion_tokens = 0
    upstream_status = 200
    error_msg: Optional[str] = None
    is_error = False
    first_chunk = True

    try:
        stream_gen = await provider.chat_completion(body, upstream_model)

        async for raw_line in stream_gen:
            # 计算 TTFT（第一个实际 data 行）
            if first_chunk and raw_line.startswith("data:"):
                ttft_ms = calc_duration_ms(start_ms)
                first_chunk = False

            # 解析 usage（最后一个 chunk 可能包含 usage）
            if raw_line.startswith("data:") and not raw_line.startswith("data: [DONE]"):
                try:
                    chunk_str = raw_line[5:].strip()
                    chunk = json.loads(chunk_str)
                    usage = chunk.get("usage")
                    if usage:
                        prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                        completion_tokens = usage.get("completion_tokens", completion_tokens)
                    # 替换 chunk 中的 model 为客户端别名
                    chunk["model"] = model_alias
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")
                    continue
                except Exception:
                    pass  # 解析失败则原样透传

            yield f"{raw_line}\n\n".encode("utf-8") if not raw_line.endswith("\n") else raw_line.encode("utf-8")

        # 发送 [DONE]
        # yield b"data: [DONE]\n\n"
        return

    except TimeoutException:
        is_error = True
        upstream_status = 0
        error_msg = "Request timeout"
        yield b"data: {\"error\": {\"message\": \"\\u4e0a\\u6e38\\u8bf7\\u6c42\\u8d85\\u65f6\", \"type\": \"timeout_error\"}}\n\n"

    except ProviderException as e:
        is_error = True
        upstream_status = e.upstream_status
        error_msg = str(e)
        err_json = json.dumps(
            {"error": {"message": str(e), "type": "upstream_error"}},
            ensure_ascii=False
        )
        yield f"data: {err_json}\n\n".encode("utf-8")

    except Exception as e:
        is_error = True
        upstream_status = 0
        error_msg = str(e)
        logger.exception("[%s] 流式异常: %s", request_id, e)
        yield b"data: {\"error\": {\"message\": \"\\u5185\\u90e8\\u670d\\u52a1\\u5668\\u9519\\u8bef\", \"type\": \"internal_error\"}}\n\n"

    finally:
        # 更新生命周期日志
        duration_ms = calc_duration_ms(start_ms)
        if is_error:
            await update_log_error(
                request_id, upstream_status, error_msg or "stream error",
                duration_ms, is_timeout=(upstream_status == 0 and error_msg == "Request timeout")
            )
        else:
            await update_log_success(
                request_id=request_id,
                upstream_status=upstream_status,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                ttft_ms=ttft_ms,
                duration_ms=duration_ms,
            )
            total_tokens = prompt_tokens + completion_tokens
            total_cost = 0.0
            if total_tokens > 0:
                bill = await create_billing_record(
                    request_id=request_id,
                    api_key_id=key_row.id,
                    key_id=key_row.key_id,
                    model_alias=model_alias,
                    provider_name=provider_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    input_price=float(model_row["input_price"]),
                    output_price=float(model_row["output_price"]),
                )
                total_tokens = bill["total_tokens"]
                total_cost = bill["total_cost"]

            # 即使 usage 缺失导致 tokens=0，也要统计"调用次数"
            await increment_key_stats(key_row.id, int(total_tokens), float(total_cost))


def _inject_system_prompt(
    body: ChatCompletionRequest,
    system_prompt: str,
) -> ChatCompletionRequest:
    """
    将模型级系统提示词注入到请求消息列表中。

    注入策略：
    - 若客户端已有 system 消息 → 将模型提示词**前置**拼接到第一条 system 消息内容之前
      （以换行分隔，允许客户端在模型提示词基础上追加自己的指令）
    - 若客户端无 system 消息 → 在 messages 列表头部插入新的 system 消息
    """
    from copy import deepcopy
    from models.openai_models import ChatMessage

    new_body = deepcopy(body)
    messages = list(new_body.messages or [])

    # 找第一条 system 消息的索引
    sys_idx = next((i for i, m in enumerate(messages) if m.role == "system"), None)

    if sys_idx is not None:
        # 已有 system 消息：模型提示词前置拼接
        existing_content = messages[sys_idx].content or ""
        messages[sys_idx] = ChatMessage(
            role="system",
            content=f"{system_prompt}\n\n{existing_content}".strip(),
        )
    else:
        # 无 system 消息：插入到列表最前面
        messages.insert(0, ChatMessage(role="system", content=system_prompt))

    new_body.messages = messages
    return new_body
