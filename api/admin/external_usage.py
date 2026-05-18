"""
api/admin/external_usage.py — 外部 Token 使用量上报与查询接口
"""
import json
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request
from models.external_models import ExternalUsageBatch
from crud.external_usage import batch_create_external_usage, get_external_usage_summary, get_external_usage_list
from middleware.auth import authenticate_admin

logger = logging.getLogger("gateway.external_usage")
router = APIRouter()


# ── 上报接口（使用 ADMIN_TOKEN 鉴权）─────────────────────

@router.post("/admin/external-usage/report", summary="上报外部 Token 使用量", tags=["外部统计"])
async def report_external_usage(
    body: ExternalUsageBatch,
    request: Request,
    admin: dict = Depends(authenticate_admin),
):
    """
    批量上报外部 Token 使用量。

    - **source**: 来源标识（packet_capture / browser_ext / proxy / manual）
    - **items**: 使用记录列表，每条包含：
      - request_id: 请求唯一ID
      - tool_name: 工具名称（doubao / qianwen / cursor 等）
      - provider_name: 厂商标识
      - model_alias: 模型名称（可选）
      - prompt_tokens: 输入 token 数
      - completion_tokens: 输出 token 数
      - total_tokens: 总 token 数（可选，默认 = prompt + completion）
      - input_price / output_price: 单价（可选，默认0）
      - detail: 原始数据摘要（可选）
    """
    client_ip = request.client.host if request.client else "unknown"
    items_data = [item.model_dump() for item in body.items]

    try:
        result = await batch_create_external_usage(
            source=body.source,
            client_ip=client_ip,
            items=items_data,
        )
        logger.info(
            "外部上报: source=%s, items=%d, tokens=%d",
            body.source, result["inserted"],
            result["total_prompt_tokens"] + result["total_completion_tokens"],
        )
        return {"status": "ok", **result}
    except Exception as e:
        logger.exception("外部上报失败: %s", e)
        return {"status": "error", "message": str(e)}


# ── 查询接口 ────────────────────────────────────────────

@router.get("/admin/external-usage/summary", summary="外部使用量汇总", tags=["外部统计"])
async def external_usage_summary(
    tool_name: Optional[str] = Query(None, description="按工具过滤"),
    provider_name: Optional[str] = Query(None, description="按厂商过滤"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    group_by: str = Query("tool_name", description="分组: tool_name / provider_name / source"),
    admin: dict = Depends(authenticate_admin),
):
    """按工具/厂商/来源分组汇总外部 Token 使用量"""
    rows = await get_external_usage_summary(
        tool_name=tool_name,
        provider_name=provider_name,
        start_time=start_time,
        end_time=end_time,
        group_by=group_by,
    )

    items = []
    for r in rows:
        item = dict(r)
        for k in ("total_cost", "input_cost", "output_cost"):
            if k in item and item[k] is not None:
                item[k] = float(item[k])
        for k in ("total_prompt_tokens", "total_completion_tokens", "total_tokens", "request_count"):
            if k in item and item[k] is not None:
                item[k] = int(item[k])
        items.append(item)

    return {"group_by": group_by, "items": items}


@router.get("/admin/external-usage/list", summary="外部使用明细", tags=["外部统计"])
async def external_usage_list(
    tool_name: Optional[str] = Query(None),
    provider_name: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    admin: dict = Depends(authenticate_admin),
):
    """分页查询外部 Token 使用明细"""
    result = await get_external_usage_list(
        tool_name=tool_name,
        provider_name=provider_name,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )

    # Decimal → float/int
    for item in result.get("items", []):
        for k in ("total_cost", "input_cost", "output_cost", "input_price", "output_price"):
            if k in item and item[k] is not None:
                item[k] = float(item[k])
        for k in ("prompt_tokens", "completion_tokens", "total_tokens", "id"):
            if k in item and item[k] is not None:
                item[k] = int(item[k])
        if "detail" in item and isinstance(item["detail"], str):
            try:
                item["detail"] = json.loads(item["detail"])
            except Exception:
                pass

    return result
