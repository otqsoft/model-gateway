"""
api/admin/model_admin.py — 模型映射管理接口
"""
from fastapi import APIRouter, Depends, HTTPException
from middleware.auth import authenticate_admin
from models.admin_models import ModelMappingCreate, ModelMappingOut
from crud.models import list_models, create_model_mapping, update_model_enabled

router = APIRouter()


@router.get("/admin/models", dependencies=[Depends(authenticate_admin)])
async def get_models(enabled_only: bool = False) -> dict:
    """列出模型映射"""
    rows = await list_models(enabled_only=enabled_only)
    return {"items": rows, "total": len(rows)}


@router.post("/admin/models", dependencies=[Depends(authenticate_admin)])
async def add_model(data: ModelMappingCreate) -> dict:
    """新增模型映射"""
    row = await create_model_mapping(data)
    return row


@router.patch("/admin/models/{model_id}/enable", dependencies=[Depends(authenticate_admin)])
async def set_model_enabled(model_id: int, is_enabled: bool) -> dict:
    """启用/禁用模型"""
    await update_model_enabled(model_id, is_enabled)
    return {"message": "已更新", "id": model_id, "is_enabled": is_enabled}
