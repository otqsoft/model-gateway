"""
api/v1/vision.py — /v1/vision 图像理解接口
支持上传图片和图片URL两种方式，将图片通过 OpenAI Vision 格式调用大模型
"""
from __future__ import annotations
import base64
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from middleware.auth import authenticate_request
from middleware.time_control import check_time_access
from core.limiter import ConcurrencyGuard, RateLimitExceeded
from core.utils import new_request_id, now_ms, calc_duration_ms
from models.openai_models import ChatCompletionRequest, ChatMessage
from models.db_models import ApiKeyRow
from crud.request_logs import (
    create_request_log, update_log_running,
    update_log_success, update_log_error,
)
from crud.billing import create_billing_record
from crud.api_keys import increment_key_stats
from crud.models import get_model_by_alias
from crud.providers import get_provider_by_name
from providers.registry import get_provider
from providers.base import ProviderException, TimeoutException

logger = logging.getLogger("gateway.vision")
router = APIRouter()

MAX_IMAGE_SIZE = 20 * 1024 * 1024


class VisionURLRequest(BaseModel):
    model: str
    image_url: str
    prompt: str = "请描述这张图片"
    stream: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None


def _build_vision_chat_request(
    model: str, prompt: str, image_url: str,
    stream: bool, temperature: float, max_tokens: Optional[int],
) -> ChatCompletionRequest:
    vision_message = ChatMessage(
        role="user",
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ],
    )
    return ChatCompletionRequest(
        model=model,
        messages=[vision_message],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )


async def _check_model_multimodal(model: str, key_row: ApiKeyRow) -> dict:
    if model not in key_row.allowed_models:
        raise HTTPException(
            status_code=403,
            detail={"error": {"message": f"模型 '{model}' 不在该 Key 的访问白名单中",
                               "type": "permission_error", "code": "model_not_allowed"}},
        )

    model_row = await get_model_by_alias(model)
    if not model_row:
        raise HTTPException(
            status_code=404,
            detail={"error": {"message": f"模型 '{model}' 不存在或已禁用", "type": "invalid_request_error"}},
        )

    if not model_row.get("supports_multimodal"):
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": f"模型 '{model}' 不支持多模态（图像理解），请在模型管理中启用多模态支持",
                               "type": "invalid_request_error", "code": "multimodal_not_supported"}},
        )

    provider_name = model_row["provider_name"]
    provider_row = await get_provider_by_name(provider_name)
    if not provider_row or not provider_row.get("is_enabled"):
        raise HTTPException(status_code=503, detail={"error": {"message": "上游厂商不可用"}})

    return model_row


async def _do_vision_request(
    request: Request, key_row: ApiKeyRow, model_row: dict,
    chat_request: ChatCompletionRequest,
):
    model = model_row["model_alias"]
    provider_name = model_row["provider_name"]
    upstream_model = model_row["upstream_model"]
    provider_max_concurrency = (await get_provider_by_name(provider_name)).get("max_concurrency", 50)

    request_id = new_request_id()
    client_ip = request.client.host if request.client else "unknown"

    await create_request_log(
        request_id=request_id, api_key_id=key_row.id, key_id=key_row.key_id,
        model_alias=model, is_stream=chat_request.stream, client_ip=client_ip,
    )

    start_ms = now_ms()

    try:
        guard = ConcurrencyGuard(
            key_id=key_row.key_id, key_max_concurrency=key_row.max_concurrency,
            provider_name=provider_name, provider_max_concurrency=provider_max_concurrency,
        )
    except Exception:
        pass

    try:
        async with guard:
            await update_log_running(request_id, provider_name, upstream_model)
            provider = await get_provider(provider_name, model_row=model_row)

            if chat_request.stream:
                return StreamingResponse(
                    _vision_stream_generator(
                        request_id=request_id, provider=provider,
                        chat_request=chat_request, upstream_model=upstream_model,
                        model_alias=model, provider_name=provider_name,
                        key_row=key_row, model_row=model_row, start_ms=start_ms,
                    ),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                             "X-Request-Id": request_id},
                )
            else:
                result = await provider.chat_completion(chat_request, upstream_model)
                duration_ms = calc_duration_ms(start_ms)

                usage = result.usage
                await update_log_success(
                    request_id=request_id, upstream_status=200,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    ttft_ms=None, duration_ms=duration_ms,
                )

                bill = await create_billing_record(
                    request_id=request_id, api_key_id=key_row.id, key_id=key_row.key_id,
                    model_alias=model, provider_name=provider_name,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    input_price=float(model_row["input_price"]),
                    output_price=float(model_row["output_price"]),
                )
                await increment_key_stats(key_row.id, bill["total_tokens"], bill["total_cost"])

                result.model = model
                return JSONResponse(
                    content=result.model_dump(exclude_none=True),
                    headers={"X-Request-Id": request_id},
                )

    except RateLimitExceeded as e:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, None, f"Rate limited: {e.level}", duration_ms)
        raise HTTPException(status_code=429,
                            detail={"error": {"message": f"并发限流（{e.level}）超出限制，请稍后重试"}})
    except TimeoutException:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, 0, "Request timeout", duration_ms, is_timeout=True)
        raise HTTPException(status_code=504, detail={"error": {"message": "上游请求超时"}})
    except ProviderException as e:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, e.upstream_status, str(e), duration_ms)
        raise HTTPException(status_code=e.status_code,
                            detail={"error": {"message": f"上游模型返回错误: {str(e)}"}})
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = calc_duration_ms(start_ms)
        await update_log_error(request_id, None, str(e), duration_ms)
        logger.exception("[%s] 图像理解未知错误: %s", request_id, e)
        raise HTTPException(status_code=500, detail={"error": {"message": "内部服务错误"}})


@router.post("/v1/vision", summary="图像理解接口（上传图片）", tags=["会话"])
async def vision_upload(
    request: Request,
    image: UploadFile = File(..., description="图片文件"),
    prompt: str = Form("请描述这张图片", description="提示文本"),
    model: str = Form(..., description="模型别名"),
    stream: bool = Form(False, description="是否流式输出"),
    temperature: float = Form(0.7, description="生成温度"),
    max_tokens: Optional[int] = Form(None, description="最大生成 token 数"),
    key_row: ApiKeyRow = Depends(authenticate_request),
):
    check_time_access(key_row)
    model_row = await _check_model_multimodal(model, key_row)

    image_data = await image.read()
    if len(image_data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400,
                            detail={"error": {"message": f"图片大小超过限制（最大 {MAX_IMAGE_SIZE // 1024 // 1024}MB）"}})

    content_type = image.content_type or "image/png"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail={"error": {"message": "上传文件必须是图片格式"}})

    b64_image = base64.b64encode(image_data).decode("utf-8")
    image_url = f"data:{content_type};base64,{b64_image}"

    chat_request = _build_vision_chat_request(model, prompt, image_url, stream, temperature, max_tokens)
    return await _do_vision_request(request, key_row, model_row, chat_request)


@router.post("/v1/vision/url", summary="图像理解接口（图片URL）", tags=["会话"])
async def vision_url(
    request: Request,
    body: VisionURLRequest,
    key_row: ApiKeyRow = Depends(authenticate_request),
):
    check_time_access(key_row)
    model_row = await _check_model_multimodal(body.model, key_row)

    chat_request = _build_vision_chat_request(
        body.model, body.prompt, body.image_url,
        body.stream, body.temperature, body.max_tokens,
    )
    return await _do_vision_request(request, key_row, model_row, chat_request)


async def _vision_stream_generator(
    request_id: str, provider,
    chat_request: ChatCompletionRequest,
    upstream_model: str, model_alias: str, provider_name: str,
    key_row: ApiKeyRow, model_row: dict, start_ms: int,
):
    ttft_ms: Optional[int] = None
    prompt_tokens = 0
    completion_tokens = 0
    upstream_status = 200
    error_msg: Optional[str] = None
    is_error = False
    first_chunk = True

    try:
        stream_gen = await provider.chat_completion(chat_request, upstream_model)

        async for raw_line in stream_gen:
            if first_chunk and raw_line.startswith("data:"):
                ttft_ms = calc_duration_ms(start_ms)
                first_chunk = False

            if raw_line.startswith("data:") and not raw_line.startswith("data: [DONE]"):
                try:
                    chunk_str = raw_line[5:].strip()
                    chunk = json.loads(chunk_str)
                    if "error" in chunk:
                        err_msg = chunk["error"].get("message", str(chunk["error"])) if isinstance(chunk["error"], dict) else str(chunk["error"])
                        is_error = True
                        error_msg = err_msg
                        yield f"data: {json.dumps({'error': {'message': f'上游模型返回错误: {err_msg}'}}, ensure_ascii=False)}\n\n".encode("utf-8")
                        continue
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
        yield f"data: {json.dumps({'error': {'message': '上游请求超时'}}, ensure_ascii=False)}\n\n".encode("utf-8")
    except ProviderException as e:
        is_error = True; upstream_status = e.upstream_status; error_msg = str(e)
        yield f"data: {json.dumps({'error': {'message': f'上游模型返回错误: {str(e)}'}}, ensure_ascii=False)}\n\n".encode("utf-8")
    except Exception as e:
        is_error = True; upstream_status = 0; error_msg = str(e)
        logger.exception("[%s] 图像理解流式异常: %s", request_id, e)
        yield f"data: {json.dumps({'error': {'message': '内部服务错误'}}, ensure_ascii=False)}\n\n".encode("utf-8")
    finally:
        duration_ms = calc_duration_ms(start_ms)
        if is_error:
            await update_log_error(request_id, upstream_status, error_msg or "stream error", duration_ms,
                                   is_timeout=(upstream_status == 0 and error_msg == "Request timeout"))
        else:
            await update_log_success(
                request_id=request_id, upstream_status=upstream_status,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                ttft_ms=ttft_ms, duration_ms=duration_ms,
            )
            total_tokens = prompt_tokens + completion_tokens
            total_cost = 0.0
            if total_tokens > 0:
                bill = await create_billing_record(
                    request_id=request_id, api_key_id=key_row.id, key_id=key_row.key_id,
                    model_alias=model_alias, provider_name=provider_name,
                    prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                    input_price=float(model_row["input_price"]),
                    output_price=float(model_row["output_price"]),
                )
                total_tokens = bill["total_tokens"]
                total_cost = bill["total_cost"]
            await increment_key_stats(key_row.id, int(total_tokens), float(total_cost))
