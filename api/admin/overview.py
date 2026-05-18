"""
api/admin/overview.py — 总览统计接口
"""
from fastapi import APIRouter, Depends, Query
from middleware.auth import authenticate_admin
from crud.request_logs import get_overview_stats, get_hourly_stats
from crud.billing import get_today_total_cost
from crud.external_usage import get_external_total_tokens
from models.admin_models import OverviewStats

router = APIRouter()


@router.get("/admin/overview", dependencies=[Depends(authenticate_admin)], summary="查询总览统计", tags=["仪表盘"])
async def overview() -> dict:
    """
    总览统计：请求量、成功率、Token、费用、平均耗时
    """
    stats = await get_overview_stats()
    today_cost = await get_today_total_cost()
    external_tokens = await get_external_total_tokens()

    total = stats.get("total_requests") or 0
    success = stats.get("success_requests") or 0
    success_rate = round(success / total * 100, 2) if total > 0 else 0.0
    gw_tokens = int(stats.get("total_tokens") or 0)

    return {
        "total_requests":    total,
        "success_requests":  success,
        "error_requests":    int(stats.get("error_requests") or 0),
        "timeout_requests":  int(stats.get("timeout_requests") or 0),
        "success_rate":      success_rate,
        "total_tokens":      gw_tokens + external_tokens,
        "gateway_tokens":    gw_tokens,
        "external_tokens":   external_tokens,
        "avg_duration_ms":   round(float(stats.get("avg_duration_ms") or 0), 2),
        "requests_today":    int(stats.get("requests_today") or 0),
        "tokens_today":      int(stats.get("tokens_today") or 0),
        "cost_today":        today_cost,
    }


@router.get("/admin/billing/hourly", dependencies=[Depends(authenticate_admin)], summary="近N小时趋势", tags=["仪表盘"])
async def hourly_trend(hours: int = Query(24, ge=1, le=168)) -> dict:
    """
    近N小时按小时聚合的请求趋势数据
    """
    rows = await get_hourly_stats(hours)
    return {"items": rows, "count": len(rows)}
