"""
api/admin/billing_api.py — 计费汇总查询接口
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from middleware.auth import authenticate_admin
from crud.billing import get_billing_summary, get_today_total_cost

router = APIRouter()


@router.get("/admin/billing", dependencies=[Depends(authenticate_admin)])
async def billing_summary(
    key_id: Optional[str] = Query(None, description="按 Key 过滤"),
    model_alias: Optional[str] = Query(None, description="按模型过滤"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    group_by: str = Query("key_id", description="分组维度: key_id | model_alias | provider_name"),
) -> dict:
    """
    计费汇总
    按 key_id / model_alias / provider_name 分组统计 Token 和费用
    """
    rows = await get_billing_summary(
        key_id=key_id,
        model_alias=model_alias,
        start_time=start_time,
        end_time=end_time,
        group_by=group_by,
    )
    today_cost = await get_today_total_cost()

    # 数值类型统一转 float
    items = []
    for r in rows:
        item = dict(r)
        for k in ("total_cost", "input_cost", "output_cost"):
            if k in item and item[k] is not None:
                item[k] = float(item[k])
        items.append(item)

    return {
        "group_by": group_by,
        "today_cost": today_cost,
        "items": items,
    }
