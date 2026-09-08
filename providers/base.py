"""
providers/base.py — 厂商适配器抽象基类
所有厂商适配器继承此类，实现 chat_completion 方法
"""
from __future__ import annotations
import asyncio
import aiohttp
import json
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Any, Union
from models.openai_models import ChatCompletionRequest, ChatCompletionResponse, UsageInfo

logger = logging.getLogger("gateway.provider")


# ── 上游错误解析与友好提示 ──────────────────────────────────────

# 关键词 → 友好提示（按优先级排列，命中即返回）
_ERROR_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("insufficient_balance", "insufficient_quota", "insufficient account balance",
      "arrearage", "余额不足", "欠费"), "上游账户余额不足"),
    (("invalid_api_key", "invalid_apikey", "authentication_error", "unauthorized",
      "invalid token", "token is invalid", "api key", "apikey", "认证失败", "鉴权失败",
      "key 无效", "key 已失效"), "上游 API Key 无效或已失效"),
    (("permission_denied", "forbidden", "无权限", "禁止访问"), "上游拒绝访问"),
    (("model_not_found", "model_not_exist", "模型不存在"), "上游模型不存在"),
    (("rate_limit", "rate limit", "too many requests", "限流", "频率限制"), "上游限流，请稍后重试"),
    (("context_length_exceeded", "maximum context length", "上下文长度"), "请求超出模型上下文长度限制"),
]

# HTTP 状态码兜底提示
_STATUS_HINTS = {
    401: "上游 API Key 无效或已失效",
    402: "上游账户余额不足",
    403: "上游拒绝访问",
    404: "上游模型或接口不存在",
    429: "上游限流，请稍后重试",
    500: "上游服务内部错误",
    502: "上游服务内部错误",
    503: "上游服务不可用",
    504: "上游服务超时",
}


def _error_hint(status: int, code: Optional[str], err_type: Optional[str], message: str) -> Optional[str]:
    """根据上游错误码/类型/消息推断友好提示"""
    key = f"{code or ''} {err_type or ''}".lower()
    text = f"{key} {message or ''}".lower()
    for keywords, hint in _ERROR_HINTS:
        if any(k in text for k in keywords):
            return hint
    return _STATUS_HINTS.get(status)


def _parse_error_body(body: str) -> tuple[Optional[str], Optional[str], str]:
    """
    从上游错误响应体中提取 (code, type, message)。
    兼容 OpenAI 风格（嵌套 error 对象）与 Dify/Coze 风格（顶层 code/message）。
    """
    try:
        data = json.loads(body)
    except Exception:
        return None, None, body.strip()[:500]
    if not isinstance(data, dict):
        return None, None, str(data)[:500]

    err = data.get("error")
    if isinstance(err, dict):
        # OpenAI 风格: {"error": {"code": "...", "message": "...", "type": "..."}}
        return (
            str(err["code"]) if err.get("code") is not None else None,
            str(err["type"]) if err.get("type") is not None else None,
            str(err.get("message") or "").strip() or body.strip()[:500],
        )
    # Dify/Coze 风格: 顶层 code/msg
    code = data.get("code") if data.get("code") is not None else data.get("status")
    msg = data.get("message") or data.get("msg")
    return (
        str(code) if code is not None else None,
        str(data["type"]) if data.get("type") is not None else None,
        str(msg).strip() if msg else body.strip()[:500],
    )


class ProviderException(Exception):
    """
    上游请求异常，携带 HTTP 状态码与结构化上游错误信息。

    - message: 给客户端展示的组合消息（友好提示 + 上游原始消息）
    - upstream_code / upstream_type / upstream_message: 从上游错误体解析出的结构化字段
    """
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        upstream_status: int = 0,
        upstream_code: Optional[str] = None,
        upstream_type: Optional[str] = None,
        upstream_message: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.upstream_status = upstream_status
        self.upstream_code = upstream_code
        self.upstream_type = upstream_type
        self.upstream_message = upstream_message

    def to_error_dict(self) -> dict:
        """
        构造 OpenAI 兼容的标准错误响应体，返回给前端：
        {"error": {"message": "友好提示: 上游原始消息", "type": "upstream_error",
                    "code": "上游错误码", "upstream_status": 402}}
        """
        err: dict = {"message": str(self), "type": "upstream_error"}
        code = self.upstream_code or self.upstream_type
        if code:
            err["code"] = code
        if self.upstream_status:
            err["upstream_status"] = self.upstream_status
        return {"error": err}


def build_upstream_exception(status: int, err_body: str, prefix: str = "上游") -> ProviderException:
    """
    解析上游错误响应体并构造结构化异常（各 Provider 通用）。

    message 组合规则：
    - 能推断友好提示 → "友好提示: 上游原始消息"（如 "上游账户余额不足: Insufficient account balance"）
    - 无法推断       → "上游返回 402: 原始消息"
    """
    code, err_type, upstream_msg = _parse_error_body(err_body)
    hint = _error_hint(status, code, err_type, upstream_msg)

    if hint:
        message = f"{hint}: {upstream_msg}" if upstream_msg else hint
    else:
        message = f"{prefix}返回 {status}: {upstream_msg}" if upstream_msg else f"{prefix}返回 {status}"

    return ProviderException(
        message,
        status_code=BaseProvider._map_upstream_status(status),
        upstream_status=status,
        upstream_code=code,
        upstream_type=err_type,
        upstream_message=upstream_msg or None,
    )


class TimeoutException(ProviderException):
    """请求超时"""
    def __init__(self):
        super().__init__("Upstream request timeout", status_code=504, upstream_status=0)


class BaseProvider(ABC):
    """
    抽象基类：厂商适配器
    """
    provider_name: str = "base"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: int = 120,
        extra_headers: Optional[dict] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.extra_headers = extra_headers or {}

    def _build_headers(self) -> dict:
        """构建基础请求头"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        headers.update(self.extra_headers)
        return headers

    def _build_body(self, request: ChatCompletionRequest, upstream_model: str) -> dict:
        """
        构建上游请求体，默认直接使用 OpenAI 格式。
        子类可覆盖此方法做字段适配。

        思考模式处理：
        - thinking_mode=True 或 enable_thinking=True 时注入启用信号
        - thinking_mode=False 时注入禁用信号（某些模型默认启用思考，必须显式禁用）
        """
        body = request.model_dump(exclude_none=True, exclude={"model"})
        body["model"] = upstream_model

        # 思考模式控制：thinking_mode 优先（来自 Dify 插件），其次 enable_thinking（来自直接 API 调用）
        thinking_mode = body.pop("thinking_mode", None)
        enable_thinking = body.pop("enable_thinking", None)
        body.pop("thinking", None)
        body.pop("reasoning", None)

        # 确定是否启用思考模式
        if thinking_mode is not None:
            use_thinking = bool(thinking_mode)
        elif enable_thinking is not None:
            use_thinking = bool(enable_thinking)
        else:
            use_thinking = False

        if use_thinking:
            # 启用思考模式：注入所有格式的参数，兼容不同厂商
            body["enable_thinking"] = True
            body["thinking"] = {"type": "enabled"}
            body["reasoning"] = True
            logger.info("[%s] thinking=ON, injected enable params", upstream_model)
        else:
            # 关闭思考模式：显式发送禁用信号（某些模型默认启用思考，不传参数会导致思考仍然开启）
            body["enable_thinking"] = False
            body["thinking"] = {"type": "disabled"}
            body["reasoning"] = False
            logger.info("[%s] thinking=OFF, injected disable params", upstream_model)

        return body

    @abstractmethod
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        upstream_model: str,
    ) -> Union[ChatCompletionResponse, AsyncGenerator[str, None]]:
        """
        发起上游请求。
        - 非流式：返回 ChatCompletionResponse
        - 流式：返回 AsyncGenerator[str, None]，每次 yield SSE 文本行
        """
        ...

    async def _do_non_stream(
        self,
        url: str,
        headers: dict,
        body: dict,
    ) -> tuple[dict, int]:
        """
        通用非流式 HTTP 请求
        返回 (response_json, upstream_http_status)
        """
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.debug(f"请求头: {url} {headers} {body}")
                async with session.post(url, json=body, headers=headers) as resp:
                    status = resp.status
                    data = await resp.json(content_type=None)
                    if status != 200:
                        err_body = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
                        raise build_upstream_exception(status, err_body)
                    return data, status
        except asyncio.TimeoutError:
            raise TimeoutException()
        except ProviderException:
            raise
        except Exception as e:
            raise ProviderException(str(e), status_code=502, upstream_status=0)

    async def _do_stream(
        self,
        url: str,
        headers: dict,
        body: dict,
    ) -> AsyncGenerator[str, None]:
        """
        通用流式 HTTP 请求，逐行 yield SSE 原文
        """
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=body, headers=headers) as resp:
                    if resp.status != 200:
                        err_body = await resp.text()
                        raise build_upstream_exception(resp.status, err_body)
                    async for raw_line in resp.content:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if line:
                            yield line
        except asyncio.TimeoutError:
            raise TimeoutException()
        except ProviderException:
            raise
        except Exception as e:
            raise ProviderException(str(e), status_code=502, upstream_status=0)

    @staticmethod
    def _map_upstream_status(upstream: int) -> int:
        """将上游状态码映射为网关状态码（上游 4xx 客户端类错误直接透传，5xx 统一 502）"""
        mapping = {401: 401, 402: 402, 403: 403, 404: 404, 429: 429, 500: 502, 503: 503, 504: 504}
        return mapping.get(upstream, 502)

    @staticmethod
    def _extract_usage(data: dict) -> UsageInfo:
        """从上游响应中提取 usage"""
        usage = data.get("usage") or {}
        return UsageInfo(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )
