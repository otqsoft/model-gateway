"""
providers/base.py — 厂商适配器抽象基类
所有厂商适配器继承此类，实现 chat_completion 方法
"""
from __future__ import annotations
import asyncio
import aiohttp
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Any, Union
from models.openai_models import ChatCompletionRequest, ChatCompletionResponse, UsageInfo

logger = logging.getLogger("gateway.provider")


class ProviderException(Exception):
    """上游请求异常，携带 HTTP 状态码"""
    def __init__(self, message: str, status_code: int = 500, upstream_status: int = 0):
        super().__init__(message)
        self.status_code = status_code
        self.upstream_status = upstream_status


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
        """
        body = request.model_dump(exclude_none=True, exclude={"model"})
        body["model"] = upstream_model
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
                        err_msg = data.get("error", {}).get("message", str(data)) if isinstance(data, dict) else str(data)
                        raise ProviderException(
                            f"上游返回 {status}: {err_msg}",
                            status_code=self._map_upstream_status(status),
                            upstream_status=status,
                        )
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
                        raise ProviderException(
                            f"上游返回 {resp.status}: {err_body[:200]}",
                            status_code=self._map_upstream_status(resp.status),
                            upstream_status=resp.status,
                        )
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
        """将上游状态码映射为网关状态码"""
        mapping = {401: 401, 403: 403, 429: 429, 500: 502, 503: 503, 504: 504}
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
