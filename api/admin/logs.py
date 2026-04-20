"""
api/admin/logs.py — 请求日志查询接口
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from middleware.auth import authenticate_admin
from crud.request_logs import get_log_by_request_id, query_logs

router = APIRouter()


@router.get("/admin/logs", dependencies=[Depends(authenticate_admin)])
async def get_logs(
    request_id: Optional[str] = Query(None),
    key_id: Optional[str] = Query(None),
    model_alias: Optional[str] = Query(None),
    provider_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    upstream_status: Optional[int] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    """
    多条件分页查询请求日志
    支持按 request_id / key_id / 模型 / 厂商 / 状态 / 上游状态 / 时间范围筛选
    """
    rows, total = await query_logs(
        request_id=request_id,
        key_id=key_id,
        model_alias=model_alias,
        provider_name=provider_name,
        status=status,
        upstream_status=upstream_status,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    # 将 datetime 序列化为字符串
    items = []
    for r in rows:
        item = dict(r)
        for k, v in item.items():
            if isinstance(v, datetime):
                item[k] = v.isoformat()
        items.append(item)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/admin/logs/{request_id}", dependencies=[Depends(authenticate_admin)])
async def get_log_detail(request_id: str) -> dict:
    """按 request_id 查询单条日志详情"""
    row = await get_log_by_request_id(request_id)
    if not row:
        raise HTTPException(status_code=404, detail="日志不存在")
    item = dict(row)
    for k, v in item.items():
        if isinstance(v, datetime):
            item[k] = v.isoformat()
    return item
