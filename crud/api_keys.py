"""
crud/api_keys.py — API Key 数据库操作
"""
import json
import hashlib
from typing import Optional
from db.database import DBHelper
from core.security import hash_gateway_key, generate_gateway_key
from models.db_models import ApiKeyRow
from models.admin_models import ApiKeyCreate, ApiKeyUpdate


async def create_api_key(data: ApiKeyCreate) -> tuple[ApiKeyRow, str]:
    """
    创建新 API Key
    返回 (ApiKeyRow, full_key)，full_key 仅此返回一次
    """
    full_key, key_id, key_prefix = generate_gateway_key()
    key_hash = hash_gateway_key(full_key)

    sql = """
    INSERT INTO api_keys (
        key_id, key_hash, key_prefix, name, allowed_models,
        max_concurrency, daily_limit, monthly_limit,
        start_date, end_date, allowed_weekdays,
        allowed_time_start, allowed_time_end, remark
    ) VALUES (%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s, %s,%s,%s)
    """
    args = (
        key_id, key_hash, key_prefix, data.name,
        json.dumps(data.allowed_models, ensure_ascii=False),
        data.max_concurrency, data.daily_limit, data.monthly_limit,
        data.start_date, data.end_date, data.allowed_weekdays,
        data.allowed_time_start, data.allowed_time_end, data.remark,
    )
    async with DBHelper() as db:
        row_id = await db.execute(sql, args)
        row = await db.fetchone("SELECT * FROM api_keys WHERE id=%s", (row_id,))

    return ApiKeyRow.from_row(row), full_key


async def get_api_key_by_hash(key_hash: str) -> Optional[ApiKeyRow]:
    """通过 hash 查找 Key（用于鉴权）"""
    async with DBHelper() as db:
        row = await db.fetchone(
            "SELECT * FROM api_keys WHERE key_hash=%s AND is_enabled=1", (key_hash,)
        )
    if row:
        return ApiKeyRow.from_row(row)
    return None


async def get_api_key_by_id(key_db_id: int) -> Optional[ApiKeyRow]:
    """通过 DB 主键获取 Key"""
    async with DBHelper() as db:
        row = await db.fetchone("SELECT * FROM api_keys WHERE id=%s", (key_db_id,))
    if row:
        return ApiKeyRow.from_row(row)
    return None


async def list_api_keys(page: int = 1, page_size: int = 20) -> tuple[list[ApiKeyRow], int]:
    """分页列表"""
    offset = (page - 1) * page_size
    async with DBHelper() as db:
        total_row = await db.fetchone("SELECT COUNT(*) as cnt FROM api_keys")
        total = total_row["cnt"] if total_row else 0
        rows = await db.fetchall(
            "SELECT * FROM api_keys ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (page_size, offset)
        )
    return [ApiKeyRow.from_row(r) for r in rows], total


async def update_api_key(key_db_id: int, data: ApiKeyUpdate) -> Optional[ApiKeyRow]:
    """更新 API Key 字段"""
    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.allowed_models is not None:
        updates["allowed_models"] = json.dumps(data.allowed_models, ensure_ascii=False)
    if data.max_concurrency is not None:
        updates["max_concurrency"] = data.max_concurrency
    if data.daily_limit is not None:
        updates["daily_limit"] = data.daily_limit
    if data.monthly_limit is not None:
        updates["monthly_limit"] = data.monthly_limit
    if data.is_enabled is not None:
        updates["is_enabled"] = int(data.is_enabled)
    if data.start_date is not None:
        updates["start_date"] = data.start_date
    if data.end_date is not None:
        updates["end_date"] = data.end_date
    if data.allowed_weekdays is not None:
        updates["allowed_weekdays"] = data.allowed_weekdays
    if data.allowed_time_start is not None:
        updates["allowed_time_start"] = data.allowed_time_start
    if data.allowed_time_end is not None:
        updates["allowed_time_end"] = data.allowed_time_end
    if data.remark is not None:
        updates["remark"] = data.remark

    if not updates:
        return await get_api_key_by_id(key_db_id)

    set_clause = ", ".join(f"{k}=%s" for k in updates)
    sql = f"UPDATE api_keys SET {set_clause} WHERE id=%s"
    args = list(updates.values()) + [key_db_id]

    async with DBHelper() as db:
        await db.execute(sql, args)
        row = await db.fetchone("SELECT * FROM api_keys WHERE id=%s", (key_db_id,))
    if row:
        return ApiKeyRow.from_row(row)
    return None


async def delete_api_key(key_db_id: int) -> bool:
    """删除 API Key"""
    async with DBHelper() as db:
        rowcount_sql = "SELECT COUNT(*) as cnt FROM api_keys WHERE id=%s"
        exists = await db.fetchone(rowcount_sql, (key_db_id,))
        if not exists or exists["cnt"] == 0:
            return False
        await db.execute("DELETE FROM api_keys WHERE id=%s", (key_db_id,))
    return True


async def increment_key_stats(key_db_id: int, tokens: int, cost: float) -> None:
    """原子累加 Key 统计数据"""
    sql = """
    UPDATE api_keys
    SET total_tokens = total_tokens + %s,
        total_cost   = total_cost   + %s,
        call_count   = call_count   + 1
    WHERE id = %s
    """
    async with DBHelper() as db:
        await db.execute(sql, (tokens, cost, key_db_id))
