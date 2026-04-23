"""
api/v1/models_list.py — /v1/models 接口
返回网关支持的模型列表（按 API Key 白名单过滤），同时包含有权限的智能体（agent: 前缀）
"""
from fastapi import APIRouter, Depends
from middleware.auth import authenticate_request
from models.db_models import ApiKeyRow
from models.openai_models import ModelListResponse, ModelObject
from crud.models import list_models
from crud.agents import list_agents

router = APIRouter()


@router.get("/v1/models", summary="查询Key可用模型列表", tags=["会话"])
async def list_available_models(
    key_row: ApiKeyRow = Depends(authenticate_request),
) -> ModelListResponse:
    """
    返回该 API Key 有权限访问的模型 + 智能体列表。
    智能体 ID 格式：agent:<agent_name>
    """
    allowed = set(key_row.allowed_models)

    # 模型部分
    all_models = await list_models(enabled_only=True)
    data = [
        ModelObject(id=m["model_alias"], owned_by=m["provider_name"])
        for m in all_models
        if m["model_alias"] in allowed
    ]

    # 智能体部分（alias 格式：agent:<name>）
    all_agents = await list_agents(enabled_only=True)
    for a in all_agents:
        alias = f"agent:{a['name']}"
        if alias in allowed:
            data.append(ModelObject(id=alias, owned_by=a["provider_name"]))

    return ModelListResponse(data=data)


@router.get("/v1/models/all", summary="查询全部模型列表", tags=["会话"])
async def list_all_models() -> ModelListResponse:
    """
    返回网关支持的全部模型 + 智能体列表（无需鉴权，用于接入指引）
    """
    all_models = await list_models(enabled_only=True)
    data = [
        ModelObject(id=m["model_alias"], owned_by=m["provider_name"])
        for m in all_models
    ]
    all_agents = await list_agents(enabled_only=True)
    for a in all_agents:
        data.append(ModelObject(id=f"agent:{a['name']}", owned_by=a["provider_name"]))
    return ModelListResponse(data=data)
