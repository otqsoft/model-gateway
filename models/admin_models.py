"""
models/admin_models.py — 管理端请求/响应 Pydantic 模型
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional, Any, Union
from pydantic import BaseModel, Field, model_validator


# ── API Key ──────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str
    allowed_models: list[str] = Field(default_factory=list)
    max_concurrency: int = 20
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    allowed_weekdays: str = "1,2,3,4,5,6,7"
    allowed_time_start: Optional[str] = None   # "09:00"
    allowed_time_end: Optional[str] = None     # "18:00"
    remark: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_weekdays(cls, data: Any) -> Any:
        if isinstance(data, dict):
            wd = data.get("allowed_weekdays")
            if isinstance(wd, (list, tuple)):
                data = dict(data)
                data["allowed_weekdays"] = ",".join(str(int(w) if isinstance(w, float) else str(w)) for w in wd)
        return data


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    allowed_models: Optional[list[str]] = None
    max_concurrency: Optional[int] = None
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None
    is_enabled: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    allowed_weekdays: Optional[str] = None
    allowed_time_start: Optional[str] = None
    allowed_time_end: Optional[str] = None
    remark: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_weekdays(cls, data: Any) -> Any:
        if isinstance(data, dict):
            wd = data.get("allowed_weekdays")
            if isinstance(wd, (list, tuple)):
                data = dict(data)
                data["allowed_weekdays"] = ",".join(str(int(w) if isinstance(w, float) else str(w)) for w in wd)
        return data


class ApiKeyOut(BaseModel):
    id: int
    key_id: str
    key_prefix: str          # 只显示前8位
    name: str
    allowed_models: list[str]
    max_concurrency: int
    daily_limit: Optional[int]
    monthly_limit: Optional[int]
    is_enabled: bool
    start_date: Optional[date]
    end_date: Optional[date]
    allowed_weekdays: Optional[str]
    allowed_time_start: Optional[Any]
    allowed_time_end: Optional[Any]
    total_tokens: int
    total_cost: float
    call_count: int
    remark: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreated(ApiKeyOut):
    """创建 Key 时额外返回明文 Key（仅此一次）"""
    full_key: str


# ── 厂商管理 ─────────────────────────────────────────────────

class ProviderCreate(BaseModel):
    name: str
    display_name: str
    base_url: str
    api_key: str             # 明文，存储时加密
    max_concurrency: int = 50
    timeout_seconds: int = 120
    extra_headers: Optional[dict] = None
    remark: Optional[str] = None


class ProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    max_concurrency: Optional[int] = None
    timeout_seconds: Optional[int] = None
    is_enabled: Optional[bool] = None
    extra_headers: Optional[dict] = None
    remark: Optional[str] = None


class ProviderOut(BaseModel):
    id: int
    name: str
    display_name: str
    base_url: str
    max_concurrency: int
    timeout_seconds: int
    is_enabled: bool
    remark: Optional[str]
    created_at: datetime


# ── 模型映射 ─────────────────────────────────────────────────

class ModelMappingCreate(BaseModel):
    model_alias: str
    provider_name: str
    upstream_model: str
    input_price: float = 0.0
    output_price: float = 0.0
    max_tokens: int = 4096
    supports_stream: bool = True
    is_enabled: bool = True
    description: Optional[str] = None
    extra_headers: Optional[dict] = None   # Coze 等厂商的额外参数（如 bot_id）


class ModelMappingOut(BaseModel):
    id: int
    model_alias: str
    provider_name: str
    upstream_model: str
    input_price: float
    output_price: float
    max_tokens: int
    supports_stream: bool
    is_enabled: bool
    description: Optional[str]
    extra_headers: Optional[Any]   # 返回 Coze bot_id 等配置


# ── 总览统计 ─────────────────────────────────────────────────

class OverviewStats(BaseModel):
    total_requests: int
    success_requests: int
    error_requests: int
    timeout_requests: int
    success_rate: float
    total_tokens: int
    total_cost: float
    avg_duration_ms: float
    requests_today: int
    tokens_today: int
    cost_today: float


# ── 监控 ─────────────────────────────────────────────────────

class StatusDistribution(BaseModel):
    status: str
    count: int
    percentage: float


class LatencyBucket(BaseModel):
    bucket: str       # 如 "0-500ms"
    count: int


class MonitorData(BaseModel):
    status_distribution: list[StatusDistribution]
    latency_distribution: list[LatencyBucket]
    upstream_status_distribution: list[dict]


# ── 日志查询 ─────────────────────────────────────────────────

class LogQueryParams(BaseModel):
    request_id: Optional[str] = None
    key_id: Optional[str] = None
    model_alias: Optional[str] = None
    provider_name: Optional[str] = None
    status: Optional[str] = None
    upstream_status: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


# ── 计费汇总 ─────────────────────────────────────────────────

class BillingSummary(BaseModel):
    key_id: Optional[str]
    model_alias: Optional[str]
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost: float
    request_count: int
