"""
api/admin/model_admin.py — 模型映射管理接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from middleware.auth import authenticate_admin
from models.admin_models import ModelMappingCreate, ModelMappingOut
from crud.models import list_models, create_model_mapping, update_model_mapping, delete_model_mapping, update_model_enabled

router = APIRouter()


@router.get("/admin/models", dependencies=[Depends(authenticate_admin)], summary="查询模型映射", tags=["模型"])
async def get_models(enabled_only: bool = False) -> dict:
    """列出模型映射（默认返回全部，含禁用）"""
    rows = await list_models(enabled_only=enabled_only)
    return {"items": rows, "total": len(rows)}


@router.post("/admin/models", dependencies=[Depends(authenticate_admin)], summary="新增模型映射", tags=["模型"])
async def add_model(data: ModelMappingCreate) -> dict:
    """新增模型映射"""
    row = await create_model_mapping(data)
    return row


@router.put("/admin/models/{model_id}", dependencies=[Depends(authenticate_admin)], summary="更新模型映射", tags=["模型"])
async def update_model(model_id: int, data: ModelMappingCreate) -> dict:
    """更新模型映射"""
    row = await update_model_mapping(model_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="模型不存在")
    return row


@router.patch("/admin/models/{model_id}/enable", dependencies=[Depends(authenticate_admin)], summary="启用/禁用模型", tags=["模型"])
async def set_model_enabled(
    model_id: int,
    is_enabled: bool = Query(..., description="true=启用 false=禁用"),
) -> dict:
    """启用/禁用模型"""
    await update_model_enabled(model_id, is_enabled)
    return {"message": "已更新", "id": model_id, "is_enabled": is_enabled}


@router.delete("/admin/models/{model_id}", dependencies=[Depends(authenticate_admin)], summary="删除模型映射", tags=["模型"])
async def remove_model(model_id: int) -> dict:
    """删除模型映射"""
    ok = await delete_model_mapping(model_id)
    if not ok:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"success": True, "id": model_id}

