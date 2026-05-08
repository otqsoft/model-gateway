"""
Dify Plugin - Credentials Schema
==================================
定义插件所需的凭证字段
"""

from typing import Optional
from dify_plugin.interfaces.model_provider import CredentialsSchema


def get_credentials_schema() -> CredentialsSchema:
    """
    返回凭证定义
    
    凭证字段:
      - gateway_url: model-gateway 服务地址
      - api_key: model-gateway 的 API Key
    """
    return CredentialsSchema(
        gateway_url={
            "label": {
                "en": "Gateway URL",
                "zh_Hans": "Gateway 地址"
            },
            "type": "text-input",
            "required": True,
            "default": "http://localhost:8000",
            "placeholder": "http://localhost:8000",
            "hint": {
                "en": "The URL of your model-gateway instance",
                "zh_Hans": "model-gateway 实例的访问地址"
            }
        },
        api_key={
            "label": {
                "en": "API Key",
                "zh_Hans": "API Key"
            },
            "type": "secret-input",
            "required": True,
            "placeholder": "sk-xxxxxxxxxxxxxxxx",
            "hint": {
                "en": "API Key created in model-gateway admin panel",
                "zh_Hans": "在 model-gateway 管理面板创建的 API Key"
            }
        }
    )
