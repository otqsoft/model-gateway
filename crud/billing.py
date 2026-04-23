"""
crud/billing.py — 计费 CRUD
"""
from typing import Optional
from datetime import datetime
from db.database import DBHelper


async def create_billing_record(
    request_id: str,
    api_key_id: Optional[int],
    key_id: Optional[str],
    model_alias: str,
    provider_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    input_price: float,
    output_price: float,
) -> dict:
    """创建计费记录，自动计算费用"""
    total_tokens = prompt_tokens + completion_tokens
    input_cost = prompt_tokens / 1000.0 * input_price
    output_cost = completion_tokens / 1000.0 * output_price
    total_cost = input_cost + output_cost

    sql = """
    INSERT INTO usage_billing
        (request_id, api_key_id, key_id, model_alias, provider_name,
         prompt_tokens, completion_tokens, total_tokens,
         input_price, output_price, input_cost, output_cost, total_cost)
    VALUES (%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s,%s,%s)
    """
    args = (
        request_id, api_key_id, key_id, model_alias, provider_name,
        prompt_tokens, completion_tokens, total_tokens,
        input_price, output_price, input_cost, output_cost, total_cost,
    )
    async with DBHelper() as db:
        await db.execute(sql, args)

    return {
        "total_tokens": total_tokens,
        "total_cost": total_cost,
    }


async def get_billing_summary(
    key_id: Optional[str] = None,
    model_alias: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    group_by: str = "key_id",   # key_id | model_alias | provider_name
) -> list[dict]:
    """计费汇总查询"""
    conditions = []
    args = []

    if key_id:
        conditions.append("key_id=%s")
        args.append(key_id)
    if model_alias:
        conditions.append("model_alias=%s")
        args.append(model_alias)
    if start_time:
        conditions.append("billed_at>=%s")
        args.append(start_time)
    if end_time:
        conditions.append("billed_at<=%s")
        args.append(end_time)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    valid_groups = {"key_id", "model_alias", "provider_name"}
    if group_by not in valid_groups:
        group_by = "key_id"

    # 当按 key_id 分组时，join api_keys 获取 key 名称
    if group_by == "key_id":
        sql = f"""
        SELECT
            b.key_id,
            k.name as key_name,
            SUM(b.prompt_tokens)     as total_input_tokens,
            SUM(b.completion_tokens) as total_output_tokens,
            SUM(b.total_tokens)      as total_tokens,
            SUM(b.input_cost)        as input_cost,
            SUM(b.output_cost)       as output_cost,
            SUM(b.total_cost)         as total_cost,
            COUNT(*)                 as total_requests
        FROM usage_billing b
        LEFT JOIN api_keys k ON b.key_id = k.key_id
        {where_clause}
        GROUP BY b.key_id, k.name
        ORDER BY total_cost DESC
        """
    else:
        sql = f"""
        SELECT
            {group_by},
            SUM(prompt_tokens)     as total_input_tokens,
            SUM(completion_tokens) as total_output_tokens,
            SUM(total_tokens)      as total_tokens,
            SUM(input_cost)        as input_cost,
            SUM(output_cost)       as output_cost,
            SUM(total_cost)        as total_cost,
            COUNT(*)               as total_requests
        FROM usage_billing
        {where_clause}
        GROUP BY {group_by}
        ORDER BY total_cost DESC
        """
    async with DBHelper() as db:
        return await db.fetchall(sql, args)


async def get_today_total_cost() -> float:
    """获取今日总费用"""
    async with DBHelper() as db:
        row = await db.fetchone("""
            SELECT COALESCE(SUM(total_cost), 0) as today_cost
            FROM usage_billing
            WHERE DATE(billed_at) = CURDATE()
        """)
    return float(row["today_cost"]) if row else 0.0
