"""
crud/models.py — 模型映射 CRUD
"""
from typing import Optional, List
from db.database import DBHelper
from models.admin_models import ModelMappingCreate


async def list_models(enabled_only: bool = True) -> List[dict]:
    """列出所有模型映射"""
    condition = "WHERE is_enabled=1" if enabled_only else ""
    async with DBHelper() as db:
        return await db.fetchall(f"SELECT * FROM model_mapping {condition} ORDER BY id")


async def get_model_by_alias(model_alias: str) -> Optional[dict]:
    """按对外别名查找模型"""
    async with DBHelper() as db:
        return await db.fetchone(
            "SELECT * FROM model_mapping WHERE model_alias=%s AND is_enabled=1",
            (model_alias,)
        )


async def create_model_mapping(data: ModelMappingCreate) -> dict:
    """创建模型映射"""
    sql = """
    INSERT INTO model_mapping
        (model_alias, provider_name, upstream_model, input_price, output_price,
         max_tokens, supports_stream, description)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """
    async with DBHelper() as db:
        row_id = await db.execute(sql, (
            data.model_alias, data.provider_name, data.upstream_model,
            data.input_price, data.output_price, data.max_tokens,
            int(data.supports_stream), data.description
        ))
        return await db.fetchone("SELECT * FROM model_mapping WHERE id=%s", (row_id,))


async def update_model_mapping(model_id: int, data: ModelMappingCreate) -> Optional[dict]:
    """更新模型映射"""
    sql = """
    UPDATE model_mapping SET
        model_alias=%s, provider_name=%s, upstream_model=%s,
        input_price=%s, output_price=%s, max_tokens=%s,
        supports_stream=%s, description=%s
    WHERE id=%s
    """
    async with DBHelper() as db:
        await db.execute(sql, (
            data.model_alias, data.provider_name, data.upstream_model,
            data.input_price, data.output_price, data.max_tokens,
            int(data.supports_stream), data.description, model_id
        ))
        return await db.fetchone("SELECT * FROM model_mapping WHERE id=%s", (model_id,))


async def update_model_enabled(model_id: int, is_enabled: bool) -> None:
    """启用/禁用模型"""
    async with DBHelper() as db:
        await db.execute(
            "UPDATE model_mapping SET is_enabled=%s WHERE id=%s",
            (int(is_enabled), model_id)
        )

