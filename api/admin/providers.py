"""
api/admin/providers.py — 厂商管理接口
"""
from fastapi import APIRouter, Depends, HTTPException
from middleware.auth import authenticate_admin
from models.admin_models import ProviderCreate, ProviderUpdate
from crud.providers import list_providers, create_provider, update_provider, delete_provider

router = APIRouter()


@router.get("/admin/providers", dependencies=[Depends(authenticate_admin)])
async def get_providers() -> dict:
    """列出所有厂商（不含解密 Key）"""
    rows = await list_providers()
    return {"items": rows, "total": len(rows)}


@router.post("/admin/providers", dependencies=[Depends(authenticate_admin)])
async def add_provider(data: ProviderCreate) -> dict:
    """添加厂商配置"""
    row = await create_provider(data)
    return row


@router.put("/admin/providers/{provider_id}", dependencies=[Depends(authenticate_admin)])
async def modify_provider(provider_id: int, data: ProviderUpdate) -> dict:
    """更新厂商配置"""
    row = await update_provider(provider_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="厂商不存在")
    return row


@router.delete("/admin/providers/{provider_id}", dependencies=[Depends(authenticate_admin)])
async def remove_provider(provider_id: int) -> dict:
    """删除厂商；若仍有关联模型则拒绝删除"""
    ok = await delete_provider(provider_id)
    if ok is False:
        raise HTTPException(
            status_code=409,
            detail="该供应商下仍有关联模型，请先删除对应模型后再删除供应商"
        )
    return {"success": True, "id": provider_id}

