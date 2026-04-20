"""
models/db_models.py — 数据库行映射 Pydantic 模型
"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime, date, time as dtime
import json


class ModelProviderRow(BaseModel):
    id: int
    name: str
    display_name: str
    base_url: str
    api_key: str          # 加密后的 Key
    max_concurrency: int
    timeout_seconds: int
    is_enabled: bool
    extra_headers: Optional[dict] = None
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelMappingRow(BaseModel):
    id: int
    model_alias: str
    provider_name: str
    upstream_model: str
    input_price: float
    output_price: float
    max_tokens: int
    supports_stream: bool
    is_enabled: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiKeyRow(BaseModel):
    id: int
    key_id: str
    key_hash: str
    key_prefix: str
    name: str
    allowed_models: list[str]   # 从 JSON 列解析
    max_concurrency: int
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None
    is_enabled: bool
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    allowed_weekdays: Optional[str] = "1,2,3,4,5,6,7"
    allowed_time_start: Optional[dtime] = None
    allowed_time_end: Optional[dtime] = None
    total_tokens: int = 0
    total_cost: float = 0.0
    call_count: int = 0
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: dict) -> "ApiKeyRow":
        """从 DB 原始字典构造，处理 JSON 字段"""
        if isinstance(row.get("allowed_models"), str):
            row = dict(row)
            row["allowed_models"] = json.loads(row["allowed_models"])
        return cls(**row)

    class Config:
        from_attributes = True


class RequestLogRow(BaseModel):
    id: int
    request_id: str
    api_key_id: Optional[int] = None
    key_id: Optional[str] = None
    model_alias: str
    provider_name: Optional[str] = None
    upstream_model: Optional[str] = None
    status: str
    is_stream: bool
    client_ip: Optional[str] = None
    upstream_status: Optional[int] = None
    error_message: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    ttft_ms: Optional[int] = None
    duration_ms: Optional[int] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UsageBillingRow(BaseModel):
    id: int
    request_id: str
    api_key_id: Optional[int] = None
    key_id: Optional[str] = None
    model_alias: str
    provider_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    input_price: float
    output_price: float
    input_cost: float
    output_cost: float
    total_cost: float
    billed_at: datetime

    class Config:
        from_attributes = True
