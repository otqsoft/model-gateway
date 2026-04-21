"""
api/admin/agents.py — 智能体管理接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from middleware.auth import authenticate_admin
from models.admin_models import AgentCreate, AgentUpdate, AgentOut
from crud.agents import (
    list_agents, get_agent_by_id,
    create_agent, update_agent, delete_agent,
)


router = APIRouter()


def _agent_to_out(row: dict) -> AgentOut:
    """将数据库行转换为输出模型"""
    return AgentOut(
        id=row["id"],
        name=row["name"],
        agent_type=row["agent_type"],
        display_name=row["display_name"],
        bot_id=row.get("bot_id"),
        base_url=row.get("base_url"),
        description=row.get("description"),
        config=row.get("config"),
        is_enabled=bool(row.get("is_enabled", 1)),
        total_calls=row.get("total_calls", 0),
        total_tokens=row.get("total_tokens", 0),
        total_cost=float(row.get("total_cost", 0)),
        remark=row.get("remark"),
        created_at=row["created_at"],
    )


@router.get("/admin/agents", dependencies=[Depends(authenticate_admin)])
async def get_agents(enabled_only: bool = Query(False)) -> dict:
    """列出所有智能体"""
    rows = await list_agents(enabled_only=enabled_only)
    items = [_agent_to_out(r).model_dump() for r in rows]
    return {"items": items, "total": len(items)}


@router.post("/admin/agents", dependencies=[Depends(authenticate_admin)])
async def add_agent(data: AgentCreate) -> dict:
    """新增智能体"""
    row = await create_agent(data)
    return _agent_to_out(row).model_dump()


@router.get("/admin/agents/{agent_id}", dependencies=[Depends(authenticate_admin)])
async def get_agent_detail(agent_id: int) -> dict:
    """获取智能体详情"""
    row = await get_agent_by_id(agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return _agent_to_out(row).model_dump()


@router.put("/admin/agents/{agent_id}", dependencies=[Depends(authenticate_admin)])
async def modify_agent(agent_id: int, data: AgentUpdate) -> dict:
    """更新智能体"""
    row = await update_agent(agent_id, data)
    if not row:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return _agent_to_out(row).model_dump()


@router.patch("/admin/agents/{agent_id}/enable", dependencies=[Depends(authenticate_admin)])
async def set_agent_enabled(
    agent_id: int,
    is_enabled: bool = Query(..., description="true=启用 false=禁用"),
) -> dict:
    """启用/禁用智能体"""
    row = await update_agent(agent_id, AgentUpdate(is_enabled=is_enabled))
    if not row:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return {"message": "已更新", "id": agent_id, "is_enabled": is_enabled}


@router.delete("/admin/agents/{agent_id}", dependencies=[Depends(authenticate_admin)])
async def remove_agent(agent_id: int) -> dict:
    """删除智能体"""
    ok = await delete_agent(agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return {"success": True, "id": agent_id}
