"""
api/admin/monitor.py — 实时监控接口
"""
from fastapi import APIRouter, Depends
from middleware.auth import authenticate_admin
from crud.request_logs import (
    get_status_distribution,
    get_latency_distribution,
    get_upstream_status_distribution,
)

router = APIRouter()


@router.get("/admin/monitor/status", dependencies=[Depends(authenticate_admin)])
async def status_distribution() -> dict:
    """实时请求状态分布"""
    rows = await get_status_distribution()
    total = sum(r["count"] for r in rows)
    result = []
    for r in rows:
        result.append({
            "status": r["status"],
            "count": r["count"],
            "percentage": round(r["count"] / total * 100, 2) if total > 0 else 0,
        })
    return {"status_distribution": result, "total": total}


@router.get("/admin/monitor/latency", dependencies=[Depends(authenticate_admin)])
async def latency_distribution() -> dict:
    """耗时分布"""
    rows = await get_latency_distribution()
    return {"latency_distribution": rows}


@router.get("/admin/monitor/upstream", dependencies=[Depends(authenticate_admin)])
async def upstream_status() -> dict:
    """上游状态码分布"""
    rows = await get_upstream_status_distribution()
    return {"upstream_status_distribution": rows}
