"""
models/external_models.py — 外部 Token 上报相关 Pydantic 模型
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class ExternalUsageItem(BaseModel):
    """单条外部 token 使用记录"""
    request_id: str = Field(description="请求唯一ID（由上报端生成）")
    tool_name: str = Field(description="工具名称：doubao / qianwen / cursor / trae 等")
    provider_name: str = Field(description="厂商标识：doubao / qianwen / openai 等")
    model_alias: str = Field(default="", description="模型名称")
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    input_price: float = Field(default=0.0, ge=0, description="输入单价（元/百万 tokens）")
    output_price: float = Field(default=0.0, ge=0, description="输出单价（元/百万 tokens）")
    detail: Optional[dict] = Field(default=None, description="原始请求/响应摘要（可选）")


class ExternalUsageBatch(BaseModel):
    """批量上报（一次可提交多条记录）"""
    source: str = Field(default="packet_capture", description="来源标识：packet_capture / browser_ext / proxy / manual")
    items: list[ExternalUsageItem] = Field(min_length=1, max_length=500, description="使用记录列表")


class ExternalUsageOut(BaseModel):
    """查询返回的单条记录"""
    id: int
    request_id: str
    source: str
    tool_name: str
    provider_name: str
    model_alias: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    input_price: float
    output_price: float
    input_cost: float
    output_cost: float
    total_cost: float
    client_ip: Optional[str]
    detail: Optional[Any]
    created_at: datetime

    class Config:
        from_attributes = True
