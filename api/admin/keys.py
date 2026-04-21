"""
api/admin/keys.py — API Key 管理接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from middleware.auth import authenticate_admin
from models.admin_models import ApiKeyCreate, ApiKeyUpdate, ApiKeyOut, ApiKeyCreated
from models.db_models import ApiKeyRow
from crud.api_keys import (
    create_api_key, list_api_keys,
    update_api_key, delete_api_key,
    get_api_key_by_id,
)

router = APIRouter()


def _key_to_out(key_row: ApiKeyRow) -> ApiKeyOut:
    try:
        return ApiKeyOut(
            id=key_row.id,
            key_id=key_row.key_id,
            key_prefix=key_row.key_prefix,
            name=key_row.name,
            allowed_models=key_row.allowed_models,
            max_concurrency=key_row.max_concurrency,
            daily_limit=key_row.daily_limit,
            monthly_limit=key_row.monthly_limit,
            is_enabled=key_row.is_enabled,
            start_date=key_row.start_date,
            end_date=key_row.end_date,
            allowed_weekdays=key_row.allowed_weekdays,
            allowed_time_start=str(key_row.allowed_time_start) if key_row.allowed_time_start else None,
            allowed_time_end=str(key_row.allowed_time_end) if key_row.allowed_time_end else None,
            total_tokens=key_row.total_tokens,
            total_cost=key_row.total_cost,
            call_count=key_row.call_count,
            remark=key_row.remark,
            created_at=key_row.created_at,
        )
    except Exception as exc:
        import logging
        logging.getLogger("gateway.keys").exception("构建 ApiKeyOut 失败: %s", exc)
        raise


@router.get("/admin/keys", dependencies=[Depends(authenticate_admin)])
async def get_keys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    """分页获取 API Key 列表（不含完整 Key）"""
    keys, total = await list_api_keys(page=page, page_size=page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_key_to_out(k).model_dump() for k in keys],
    }


@router.post("/admin/keys", dependencies=[Depends(authenticate_admin)])
async def create_key(data: ApiKeyCreate) -> dict:
    """
    创建 API Key
    注意：full_key 仅在响应中返回一次，请妥善保存
    """
    key_row, full_key = await create_api_key(data)
    out = _key_to_out(key_row).model_dump()
    out["full_key"] = full_key  # 仅此一次返回明文
    return out


@router.put("/admin/keys/{key_id}", dependencies=[Depends(authenticate_admin)])
async def update_key(key_id: int, data: ApiKeyUpdate) -> dict:
    """更新 API Key 配置"""
    key_row = await update_api_key(key_id, data)
    if not key_row:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return _key_to_out(key_row).model_dump()


@router.delete("/admin/keys/{key_id}", dependencies=[Depends(authenticate_admin)])
async def delete_key(key_id: int) -> dict:
    """删除 API Key"""
    ok = await delete_api_key(key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"message": "已删除", "id": key_id}


@router.get("/admin/keys/{key_id}", dependencies=[Depends(authenticate_admin)])
async def get_key_detail(key_id: int) -> dict:
    """获取单个 Key 详情"""
    key_row = await get_api_key_by_id(key_id)
    if not key_row:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return _key_to_out(key_row).model_dump()
