"""
api/v1/models_list.py — /v1/models 接口
返回网关支持的模型列表（按 API Key 白名单过滤）
"""
from fastapi import APIRouter, Depends
from middleware.auth import authenticate_request
from models.db_models import ApiKeyRow
from models.openai_models import ModelListResponse, ModelObject
from crud.models import list_models

router = APIRouter()


@router.get("/v1/models")
async def list_available_models(
    key_row: ApiKeyRow = Depends(authenticate_request),
) -> ModelListResponse:
    """
    返回该 API Key 有权限访问的模型列表
    """
    all_models = await list_models(enabled_only=True)
    allowed = set(key_row.allowed_models)

    data = [
        ModelObject(id=m["model_alias"], owned_by=m["provider_name"])
        for m in all_models
        if m["model_alias"] in allowed
    ]

    return ModelListResponse(data=data)


@router.get("/v1/models/all")
async def list_all_models() -> ModelListResponse:
    """
    返回网关支持的全部模型列表（无需鉴权，用于接入指引）
    """
    all_models = await list_models(enabled_only=True)
    data = [
        ModelObject(id=m["model_alias"], owned_by=m["provider_name"])
        for m in all_models
    ]
    return ModelListResponse(data=data)
