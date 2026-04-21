"""
crud/agents.py — 智能体配置 CRUD
"""
from typing import Optional, List
import json
from db.database import DBHelper
from core.security import encrypt_api_key, decrypt_api_key
from models.admin_models import AgentCreate, AgentUpdate


async def list_agents(enabled_only: bool = False) -> List[dict]:
    """列出所有智能体"""
    async with DBHelper() as db:
        rows = await db.fetchall(
            "SELECT id, name, agent_type, display_name, bot_id, base_url, "
            "description, config, is_enabled, total_calls, total_tokens, total_cost, "
            "remark, created_at, updated_at "
            "FROM agent_configs ORDER BY id"
        )
    return rows


async def get_agent_by_name(name: str) -> Optional[dict]:
    """按名称获取智能体（含解密Key）"""
    async with DBHelper() as db:
        row = await db.fetchone(
            "SELECT * FROM agent_configs WHERE name=%s", (name,)
        )
    if row and row.get("api_key"):
        try:
            row["api_key_plain"] = decrypt_api_key(row["api_key"])
        except Exception:
            row["api_key_plain"] = ""
    return row


async def get_agent_by_id(agent_id: int) -> Optional[dict]:
    """按ID获取智能体"""
    async with DBHelper() as db:
        return await db.fetchone(
            "SELECT * FROM agent_configs WHERE id=%s", (agent_id,)
        )


async def create_agent(data: AgentCreate) -> dict:
    """创建智能体"""
    encrypted_key = encrypt_api_key(data.api_key) if data.api_key else ""
    config_json = json.dumps(data.config) if data.config else None
    sql = """
    INSERT INTO agent_configs
        (name, agent_type, display_name, bot_id, api_key, base_url,
         description, config, remark)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    async with DBHelper() as db:
        row_id = await db.execute(sql, (
            data.name, data.agent_type, data.display_name,
            data.bot_id, encrypted_key, data.base_url,
            data.description, config_json, data.remark
        ))
        row = await db.fetchone(
            "SELECT id, name, agent_type, display_name, bot_id, base_url, "
            "description, config, is_enabled, total_calls, total_tokens, total_cost, "
            "remark, created_at FROM agent_configs WHERE id=%s", (row_id,)
        )
    return row


async def update_agent(agent_id: int, data: AgentUpdate) -> Optional[dict]:
    """更新智能体"""
    updates = {}
    if data.display_name is not None:
        updates["display_name"] = data.display_name
    if data.agent_type is not None:
        updates["agent_type"] = data.agent_type
    if data.bot_id is not None:
        updates["bot_id"] = data.bot_id
    if data.api_key is not None:
        updates["api_key"] = encrypt_api_key(data.api_key)
    if data.base_url is not None:
        updates["base_url"] = data.base_url
    if data.description is not None:
        updates["description"] = data.description
    if data.config is not None:
        updates["config"] = json.dumps(data.config)
    if data.is_enabled is not None:
        updates["is_enabled"] = int(data.is_enabled)
    if data.remark is not None:
        updates["remark"] = data.remark

    if not updates:
        return await get_agent_by_id(agent_id)

    set_clause = ", ".join(f"{k}=%s" for k in updates)
    sql = f"UPDATE agent_configs SET {set_clause} WHERE id=%s"

    async with DBHelper() as db:
        await db.execute(sql, list(updates.values()) + [agent_id])
        row = await db.fetchone(
            "SELECT id, name, agent_type, display_name, bot_id, base_url, "
            "description, config, is_enabled, total_calls, total_tokens, total_cost, "
            "remark, created_at FROM agent_configs WHERE id=%s", (agent_id,)
        )
    return row


async def delete_agent(agent_id: int) -> bool:
    """删除智能体"""
    async with DBHelper() as db:
        affected = await db.execute_delete(
            "DELETE FROM agent_configs WHERE id=%s", (agent_id,)
        )
    return bool(affected)


async def increment_agent_stats(agent_id: int, tokens: int, cost: float) -> None:
    """原子累加智能体统计数据"""
    sql = """
    UPDATE agent_configs
    SET total_calls = total_calls + 1,
        total_tokens = total_tokens + %s,
        total_cost = total_cost + %s
    WHERE id = %s
    """
    async with DBHelper() as db:
        await db.execute(sql, (tokens, cost, agent_id))


async def get_agent_usage_stats() -> List[dict]:
    """获取智能体使用统计"""
    async with DBHelper() as db:
        return await db.fetchall("""
            SELECT 
                agent_type,
                COUNT(*) as agent_count,
                SUM(total_calls) as total_calls,
                SUM(total_tokens) as total_tokens,
                SUM(total_cost) as total_cost
            FROM agent_configs
            WHERE total_calls > 0
            GROUP BY agent_type
        """)
