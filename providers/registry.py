"""
providers/registry.py — 适配器注册表
根据厂商名称动态获取对应适配器实例
"""
from __future__ import annotations
import logging
from typing import Optional
from providers.base import BaseProvider, ProviderException
from providers.deepseek import DeepSeekProvider
from providers.minimax import MiniMaxProvider
from providers.glm import GLMProvider
from providers.xiaomi import XiaomiProvider
from providers.siliconflow import SiliconFlowProvider
from providers.modelscope import ModelScopeProvider
from core.security import decrypt_api_key
from crud.providers import get_provider_by_name

logger = logging.getLogger("gateway.registry")

# 厂商名 -> 适配器类
_PROVIDER_CLASS_MAP: dict[str, type[BaseProvider]] = {
    "deepseek":    DeepSeekProvider,
    "minimax":     MiniMaxProvider,
    "glm":         GLMProvider,
    "xiaomi":      XiaomiProvider,
    "siliconflow": SiliconFlowProvider,
    "modelscope":  ModelScopeProvider,
}


async def get_provider(provider_name: str) -> BaseProvider:
    """
    从数据库读取厂商配置，解密 API Key，返回对应适配器实例
    """
    row = await get_provider_by_name(provider_name)
    if not row:
        raise ProviderException(
            f"厂商 '{provider_name}' 不存在或未启用",
            status_code=404,
        )
    if not row.get("is_enabled"):
        raise ProviderException(
            f"厂商 '{provider_name}' 已禁用",
            status_code=503,
        )

    # 解密上游 API Key
    encrypted_key = row.get("api_key", "")
    try:
        plain_key = decrypt_api_key(encrypted_key) if encrypted_key else ""
    except Exception:
        plain_key = encrypted_key  # 回退：可能是未加密的 Key

    cls = _PROVIDER_CLASS_MAP.get(provider_name)
    if cls is None:
        raise ProviderException(
            f"没有找到厂商 '{provider_name}' 的适配器实现",
            status_code=501,
        )

    extra_headers = row.get("extra_headers") or {}
    if isinstance(extra_headers, str):
        import json
        extra_headers = json.loads(extra_headers) if extra_headers else {}

    return cls(
        base_url=row["base_url"],
        api_key=plain_key,
        timeout_seconds=row.get("timeout_seconds", 120),
        extra_headers=extra_headers,
    )
