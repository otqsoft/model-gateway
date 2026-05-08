"""
Dify Plugin - Model Schemas
==================================
定义支持的模型及其参数
"""

from typing import List, Dict, Any


# ───────────────────────────────────────────────────────
# 通用参数定义
# ───────────────────────────────────────────────────────

BASE_PARAMS = [
    {
        "name": "temperature",
        "label": {
            "en": "Temperature",
            "zh_Hans": "温度"
        },
        "type": "float",
        "default": 0.7,
        "min": 0.0,
        "max": 2.0,
        "required": False
    },
    {
        "name": "top_p",
        "label": {
            "en": "Top P",
            "zh_Hans": "Top P"
        },
        "type": "float",
        "default": 1.0,
        "min": 0.0,
        "max": 1.0,
        "required": False
    },
    {
        "name": "max_tokens",
        "label": {
            "en": "Max Tokens",
            "zh_Hans": "最大 Token 数"
        },
        "type": "int",
        "default": 4096,
        "min": 1,
        "max": 128000,
        "required": False
    },
    {
        "name": "presence_penalty",
        "label": {
            "en": "Presence Penalty",
            "zh_Hans": "存在惩罚"
        },
        "type": "float",
        "default": 0.0,
        "min": -2.0,
        "max": 2.0,
        "required": False
    },
    {
        "name": "frequency_penalty",
        "label": {
            "en": "Frequency Penalty",
            "zh_Hans": "频率惩罚"
        },
        "type": "float",
        "default": 0.0,
        "min": -2.0,
        "max": 2.0,
        "required": False
    }
]


# ───────────────────────────────────────────────────────
# 模型定义
# ───────────────────────────────────────────────────────

def _make_model_schema(name: str, label: Dict[str, str], model_type: str = "llm") -> Dict[str, Any]:
    """创建一个模型定义"""
    return {
        "name": name,
        "label": label,
        "model_type": model_type,
        "features": ["streaming"],
        "parameter_rules": BASE_PARAMS
    }


# DeepSeek Chat
deepseek_chat = _make_model_schema(
    name="deepseek-chat",
    label={"en": "DeepSeek Chat", "zh_Hans": "DeepSeek Chat"}
)

# DeepSeek Coder
deepseek_coder = _make_model_schema(
    name="deepseek-coder",
    label={"en": "DeepSeek Coder", "zh_Hans": "DeepSeek Coder"}
)

# GLM-4
glm4 = _make_model_schema(
    name="glm-4",
    label={"en": "GLM-4", "zh_Hans": "GLM-4"}
)

# GLM-4-Flash
glm4_flash = _make_model_schema(
    name="glm-4-flash",
    label={"en": "GLM-4-Flash", "zh_Hans": "GLM-4-Flash"}
)

# GLM-4-Plus
glm4_plus = _make_model_schema(
    name="glm-4-plus",
    label={"en": "GLM-4-Plus", "zh_Hans": "GLM-4-Plus"}
)

# GLM-3-Turbo
glm3_turbo = _make_model_schema(
    name="glm-3-turbo",
    label={"en": "GLM-3-Turbo", "zh_Hans": "GLM-3-Turbo"}
)

# MiniMax Text
minimax_text = _make_model_schema(
    name="MiniMax-Text-01",
    label={"en": "MiniMax Text", "zh_Hans": "MiniMax Text"}
)

# Xiaomi AI
xiaomi_ai = _make_model_schema(
    name="xiaomi-ai",
    label={"en": "Xiaomi AI", "zh_Hans": "小米 AI"}
)

# GPT-3.5-Turbo (兼容)
gpt35_turbo = _make_model_schema(
    name="gpt-3.5-turbo",
    label={"en": "GPT-3.5-Turbo (Compatible)", "zh_Hans": "GPT-3.5-Turbo (兼容)"}
)

# GPT-4o (兼容)
gpt4o = _make_model_schema(
    name="gpt-4o",
    label={"en": "GPT-4o (Compatible)", "zh_Hans": "GPT-4o (兼容)"}
)


# ───────────────────────────────────────────────────────
# 导出所有模型 schema
# ───────────────────────────────────────────────────────

__all__ = [
    "deepseek_chat",
    "deepseek_coder",
    "glm4",
    "glm4_flash",
    "glm4_plus",
    "glm3_turbo",
    "minimax_text",
    "xiaomi_ai",
    "gpt35_turbo",
    "gpt4o"
]
