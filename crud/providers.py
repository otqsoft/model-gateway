"""
crud/providers.py — 厂商配置 CRUD
"""
import json
from typing import Optional
from db.database import DBHelper
from core.security import encrypt_api_key, decrypt_api_key
from models.admin_models import ProviderCreate, ProviderUpdate


async def list_providers(provider_type: Optional[str] = None) -> list[dict]:
    """列出厂商（不含解密 Key）；provider_type 可过滤 model / agent"""
    sql = (
        "SELECT id,name,display_name,provider_type,base_url,max_concurrency,"
        "timeout_seconds,is_enabled,extra_headers,remark,created_at "
        "FROM model_providers"
    )
    args: tuple = ()
    if provider_type:
        sql += " WHERE provider_type=%s"
        args = (provider_type,)
    sql += " ORDER BY id"
    async with DBHelper() as db:
        rows = await db.fetchall(sql, args) if args else await db.fetchall(sql)
    return rows


async def get_provider(name: str) -> Optional[dict]:
    """按 name 获取厂商完整信息（含解密 Key）"""
    async with DBHelper() as db:
        row = await db.fetchone(
            "SELECT * FROM model_providers WHERE name=%s", (name,)
        )
    if row and row.get("api_key"):
        try:
            row["api_key_plain"] = decrypt_api_key(row["api_key"])
        except Exception:
            row["api_key_plain"] = ""
    return row


async def get_provider_by_name(name: str) -> Optional[dict]:
    """获取厂商（含解密 Key）"""
    return await get_provider(name)


async def create_provider(data: ProviderCreate) -> dict:
    """创建厂商"""
    # 智能体类供应商不需要 api_key，模型类供应商加密存储
    encrypted_key = ""
    if data.provider_type == "model" and data.api_key:
        encrypted_key = encrypt_api_key(data.api_key)
    extra = json.dumps(data.extra_headers) if data.extra_headers else None
    sql = """
    INSERT INTO model_providers
        (name, display_name, provider_type, base_url, api_key,
         max_concurrency, timeout_seconds, extra_headers, remark)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    async with DBHelper() as db:
        row_id = await db.execute(sql, (
            data.name, data.display_name, data.provider_type,
            data.base_url, encrypted_key,
            data.max_concurrency, data.timeout_seconds, extra, data.remark
        ))
        row = await db.fetchone(
            "SELECT id,name,display_name,provider_type,base_url,max_concurrency,"
            "timeout_seconds,is_enabled,remark,created_at "
            "FROM model_providers WHERE id=%s", (row_id,)
        )
    return row


async def delete_provider(provider_id: int) -> bool:
    """删除厂商；若仍有关联模型或智能体则返回 False"""
    async with DBHelper() as db:
        # 检查是否有关联模型映射
        ref_model = await db.fetchone(
            "SELECT id FROM model_mapping WHERE provider_name="
            "(SELECT name FROM model_providers WHERE id=%s) LIMIT 1",
            (provider_id,)
        )
        if ref_model:
            return False
        # 检查是否有关联智能体
        ref_agent = await db.fetchone(
            "SELECT id FROM agent_configs WHERE provider_name="
            "(SELECT name FROM model_providers WHERE id=%s) LIMIT 1",
            (provider_id,)
        )
        if ref_agent:
            return False
        affected = await db.execute_delete(
            "DELETE FROM model_providers WHERE id=%s", (provider_id,)
        )
    return bool(affected)


async def update_provider(provider_id: int, data: ProviderUpdate) -> Optional[dict]:
    """更新厂商"""
    updates = {}
    if data.display_name is not None:
        updates["display_name"] = data.display_name
    if data.provider_type is not None:
        updates["provider_type"] = data.provider_type
    if data.base_url is not None:
        updates["base_url"] = data.base_url
    if data.api_key is not None:
        updates["api_key"] = encrypt_api_key(data.api_key)
    if data.max_concurrency is not None:
        updates["max_concurrency"] = data.max_concurrency
    if data.timeout_seconds is not None:
        updates["timeout_seconds"] = data.timeout_seconds
    if data.is_enabled is not None:
        updates["is_enabled"] = int(data.is_enabled)
    if data.extra_headers is not None:
        updates["extra_headers"] = json.dumps(data.extra_headers)
    if data.remark is not None:
        updates["remark"] = data.remark

    if not updates:
        return None

    set_clause = ", ".join(f"{k}=%s" for k in updates)
    sql = f"UPDATE model_providers SET {set_clause} WHERE id=%s"

    async with DBHelper() as db:
        await db.execute(sql, list(updates.values()) + [provider_id])
        row = await db.fetchone(
            "SELECT id,name,display_name,provider_type,base_url,max_concurrency,"
            "timeout_seconds,is_enabled,remark,created_at "
            "FROM model_providers WHERE id=%s", (provider_id,)
        )
    return row
