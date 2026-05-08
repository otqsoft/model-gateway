"""
Dify 模型提供插件 - model-gateway Integration
==============================================
让 Dify 能够使用 model-gateway 管理的所有模型（DeepSeek、GLM、MiniMax 等）

插件结构：
  provider.py  - Dify 模型提供器核心实现
  config.yaml - 插件配置（gateway 地址、API Key 等）

Dify 插件接口文档：
  https://docs.dify.ai/advanced/model-providers
"""
from .provider import ModelGatewayProvider

__all__ = ["ModelGatewayProvider"]
