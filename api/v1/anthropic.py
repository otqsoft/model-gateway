"""
api/v1/anthropic.py — Anthropic Messages API 兼容接口 (/v1/messages)
策略：
  1. 接收 AnthropicRequest
  2. 转换为 OpenAI ChatCompletionRequest
  3. 复用 api.v1.chat.chat_completions 的完整业务逻辑（认证 / 限流 / 路由 / 计费）
  4. 拦截响应并转换回 Anthropic 格式（非流式 JSON / 流式 SSE 事件）
"""
from __future__ import annotations
import json
import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from middleware.auth import authenticate_request
from models.anthropic_models import AnthropicRequest
from models.openai_models import ChatCompletionResponse
from models.db_models import ApiKeyRow
from core.anthropic_converter import (
    anthropic_to_openai,
    openai_to_anthropic,
    openai_stream_to_anthropic,
)

logger = logging.getLogger("gateway.anthropic")
router = APIRouter()


def _anthropic_error(status_code: int, err_type: str, message: str) -> HTTPException:
    """构造 Anthropic 风格的错误 HTTPException"""
    return HTTPException(
        status_code=status_code,
        detail={
            "type": "error",
            "error": {"type": err_type, "message": message},
        },
    )


def _convert_http_exception(exc: HTTPException) -> HTTPException:
    """将 OpenAI 风格的 HTTPException detail 转换为 Anthropic 风格"""
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        # OpenAI 风格 {error: {message, type, code}}
        err = detail["error"]
        message = err.get("message", "")
        err_type = err.get("type", "api_error")
        code = err.get("code", "")

        # 类型映射
        type_map = {
            "auth_error": "authentication_error",
            "invalid_request_error": "invalid_request_error",
            "permission_error": "permission_error",
            "rate_limit_error": "rate_limit_error",
            "upstream_error": "api_error",
            "timeout_error": "api_error",
            "internal_error": "api_error",
        }
        anth_type = type_map.get(err_type, "api_error")

        # code → message 提示
        if code == "missing_auth":
            anth_type = "authentication_error"
        elif code == "invalid_api_key":
            anth_type = "authentication_error"
        elif code == "key_disabled":
            anth_type = "permission_error"
        elif code == "model_not_allowed":
            anth_type = "permission_error"
        elif code == "rate_limit_exceeded":
            anth_type = "rate_limit_error"

        return HTTPException(
            status_code=exc.status_code,
            detail={
                "type": "error",
                "error": {"type": anth_type, "message": message},
            },
        )
    elif isinstance(detail, dict) and detail.get("type") == "error":
        # 已经是 Anthropic 风格
        return exc
    else:
        return HTTPException(
            status_code=exc.status_code,
            detail={
                "type": "error",
                "error": {"type": "api_error", "message": str(detail)},
            },
        )


@router.post("/v1/messages", summary="Anthropic 兼容 /v1/messages 接口", tags=["会话"])
async def anthropic_messages(
    request: Request,
    body: AnthropicRequest,
    key_row: ApiKeyRow = Depends(authenticate_request),
):
    """
    Anthropic Messages API 兼容端点
    - 内部转换为 OpenAI 格式复用 /v1/chat/completions 逻辑
    - 响应转换回 Anthropic 格式
    """
    # 延迟导入避免循环依赖
    from api.v1.chat import chat_completions

    # 1. Anthropic → OpenAI 请求
    try:
        openai_body = anthropic_to_openai(body)
    except Exception as e:
        logger.exception("[Anthropic] 请求转换失败: %s", e)
        raise _anthropic_error(400, "invalid_request_error", f"请求格式转换失败: {e}")

    # 2. 调用 OpenAI 端点逻辑
    try:
        response = await chat_completions(request, openai_body, key_row)
    except HTTPException as exc:
        raise _convert_http_exception(exc)
    except Exception as e:
        logger.exception("[Anthropic] 调用上游失败: %s", e)
        raise _anthropic_error(500, "api_error", f"内部服务错误: {e}")

    # 3. 响应转换
    if isinstance(response, JSONResponse):
        # 非流式
        try:
            openai_data = json.loads(response.body)
            openai_resp = ChatCompletionResponse(**openai_data)
            anth_resp = openai_to_anthropic(openai_resp)
            return JSONResponse(
                content=anth_resp.model_dump(),
                headers={"X-Request-Id": response.headers.get("X-Request-Id", "")},
            )
        except Exception as e:
            logger.exception("[Anthropic] 响应转换失败: %s", e)
            raise _anthropic_error(500, "api_error", f"响应格式转换失败: {e}")

    elif isinstance(response, StreamingResponse):
        # 流式
        request_id = response.headers.get("X-Request-Id", "")
        model_name = body.model

        async def _gen():
            try:
                async for chunk in openai_stream_to_anthropic(
                    response.body_iterator, model=model_name
                ):
                    if isinstance(chunk, str):
                        yield chunk.encode("utf-8")
                    else:
                        yield chunk
            except Exception as e:
                logger.exception("[Anthropic] 流式转换失败: %s", e)
                err_payload = {
                    "type": "error",
                    "error": {"type": "api_error", "message": f"stream error: {e}"},
                }
                yield f"event: error\ndata: {json.dumps(err_payload, ensure_ascii=False)}\n\n".encode("utf-8")

        return StreamingResponse(
            _gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Request-Id": request_id,
            },
        )

    else:
        # 兜底
        return response
