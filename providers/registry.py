"""
providers/registry.py — 适配器注册表
根据厂商名称动态获取对应适配器实例
"""
from __future__ import annotations
import json
import logging
from typing import Optional
from providers.base import BaseProvider, ProviderException
from providers.deepseek import DeepSeekProvider
from providers.minimax import MiniMaxProvider
from providers.glm import GLMProvider
from providers.xiaomi import XiaomiProvider
from providers.siliconflow import SiliconFlowProvider
from providers.modelscope import ModelScopeProvider
from providers.coze import CozeProvider
from providers.dify import DifyProvider
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
    "coze":        CozeProvider,
    "dify":        DifyProvider,
}


async def get_provider(provider_name: str, model_row: Optional[dict] = None) -> BaseProvider:
    """
    从数据库读取厂商配置，解密 API Key，返回对应适配器实例

    Args:
        provider_name: 厂商标识
        model_row: 模型映射行（含 extra_headers，用于 Coze 等需要 bot_id 的厂商）
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
        extra_headers = json.loads(extra_headers) if extra_headers else {}

    # Coze 需要从 model_mapping.extra_headers 读取 bot_id（作为必选位置参数）
    if provider_name == "coze":
        model_extra = (model_row or {}).get("extra_headers") or {}
        if isinstance(model_extra, str):
            model_extra = json.loads(model_extra) if model_extra else {}
        # model_mapping.extra_headers 中的 bot_id 优先级高于 provider.extra_headers
        bot_id = model_extra.get("bot_id") or extra_headers.pop("bot_id", "")
        logger.info("Coze Provider 构建: bot_id=%s", bot_id)

        return cls(
            base_url=row["base_url"],
            api_key=plain_key,
            bot_id=bot_id,
            timeout_seconds=row.get("timeout_seconds", 120),
        )

    return cls(
        base_url=row["base_url"],
        api_key=plain_key,
        timeout_seconds=row.get("timeout_seconds", 120),
        extra_headers=extra_headers,
    )


async def get_agent_provider(agent_row: dict, provider_row: dict) -> BaseProvider:
    """
    为智能体请求构建适配器。
    与 get_provider() 的区别：
      - api_key 来自 agent_row（每个智能体专属 key），而非 provider_row
      - bot_id / app_id 来自 agent_row.bot_id
      - base_url 优先用 agent_row.base_url，回退到 provider_row.base_url

    Args:
        agent_row: agent_configs 表中的行（含 api_key_plain 字段，由 get_agent_by_name 解密填充）
        provider_row: model_providers 表中的行（provider_type=agent）
    """
    provider_name = agent_row["provider_name"]

    cls = _PROVIDER_CLASS_MAP.get(provider_name)
    if cls is None:
        raise ProviderException(
            f"没有找到智能体供应商 '{provider_name}' 的适配器实现",
            status_code=501,
        )

    # 使用智能体自己的 api_key（get_agent_by_name 已解密到 api_key_plain）
    plain_key = agent_row.get("api_key_plain") or ""
    if not plain_key:
        # 兜底：尝试直接解密
        raw = agent_row.get("api_key", "")
        try:
            plain_key = decrypt_api_key(raw) if raw else ""
        except Exception:
            plain_key = raw

    # base_url：智能体自定义地址 > 供应商默认地址
    base_url = agent_row.get("base_url") or provider_row.get("base_url") or ""
    timeout = provider_row.get("timeout_seconds", 120)

    bot_id = agent_row.get("bot_id") or ""
    logger.info("Agent Provider 构建: provider=%s, agent=%s, bot_id=%s",
                provider_name, agent_row.get("name"), bot_id)

    if provider_name == "coze":
        return cls(
            base_url=base_url,
            api_key=plain_key,
            bot_id=bot_id,
            timeout_seconds=timeout,
        )

    if provider_name == "dify":
        return cls(
            base_url=base_url,
            api_key=plain_key,
            timeout_seconds=timeout,
        )

    # 其他供应商兜底（支持未来扩展）
    return cls(
        base_url=base_url,
        api_key=plain_key,
        timeout_seconds=timeout,
    )

