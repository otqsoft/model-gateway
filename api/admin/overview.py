"""
api/admin/overview.py — 总览统计接口
"""
from fastapi import APIRouter, Depends
from middleware.auth import authenticate_admin
from crud.request_logs import get_overview_stats
from crud.billing import get_today_total_cost
from models.admin_models import OverviewStats

router = APIRouter()


@router.get("/admin/overview", dependencies=[Depends(authenticate_admin)])
async def overview() -> dict:
    """
    总览统计：请求量、成功率、Token、费用、平均耗时
    """
    stats = await get_overview_stats()
    today_cost = await get_today_total_cost()

    total = stats.get("total_requests") or 0
    success = stats.get("success_requests") or 0
    success_rate = round(success / total * 100, 2) if total > 0 else 0.0

    return {
        "total_requests":    total,
        "success_requests":  success,
        "error_requests":    stats.get("error_requests") or 0,
        "timeout_requests":  stats.get("timeout_requests") or 0,
        "success_rate":      success_rate,
        "total_tokens":      stats.get("total_tokens") or 0,
        "avg_duration_ms":   round(float(stats.get("avg_duration_ms") or 0), 2),
        "requests_today":    stats.get("requests_today") or 0,
        "tokens_today":      stats.get("tokens_today") or 0,
        "cost_today":        today_cost,
    }
