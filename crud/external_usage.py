"""
crud/external_usage.py — 外部 Token 使用量 CRUD
"""
from typing import Optional
from datetime import datetime
from db.database import DBHelper


async def batch_create_external_usage(
    source: str,
    client_ip: str,
    items: list[dict],
) -> dict:
    """批量插入外部使用记录，返回统计摘要"""
    total_prompt = 0
    total_completion = 0
    total_cost_sum = 0.0

    sql = """
    INSERT INTO external_usage
        (request_id, source, tool_name, provider_name, model_alias,
         prompt_tokens, completion_tokens, total_tokens,
         input_price, output_price, input_cost, output_cost, total_cost,
         client_ip, detail)
    VALUES (%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s,%s,%s, %s,%s)
    """

    rows = []
    for item in items:
        pt = item["prompt_tokens"]
        ct = item["completion_tokens"]
        tt = item.get("total_tokens", pt + ct)
        ip = item.get("input_price", 0.0)
        op = item.get("output_price", 0.0)
        ic = pt / 1000.0 * ip
        oc = ct / 1000.0 * op
        tc = ic + oc

        total_prompt += pt
        total_completion += ct
        total_cost_sum += tc

        rows.append((
            item["request_id"], source, item["tool_name"], item["provider_name"],
            item.get("model_alias", ""),
            pt, ct, tt,
            ip, op, ic, oc, tc,
            client_ip,
            __import__("json").dumps(item.get("detail"), ensure_ascii=False) if item.get("detail") else None,
        ))

    async with DBHelper() as db:
        await db.execute_many(sql, rows)

    return {
        "inserted": len(items),
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_cost": round(total_cost_sum, 8),
    }


async def get_external_total_tokens() -> int:
    """返回 external_usage 表的历史总 token 数"""
    async with DBHelper() as db:
        row = await db.fetchone("SELECT COALESCE(SUM(total_tokens),0) AS total FROM external_usage")
        return int(row["total"]) if row else 0


async def get_external_usage_summary(
    tool_name: Optional[str] = None,
    provider_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    group_by: str = "tool_name",
) -> list[dict]:
    """外部使用量汇总查询"""
    conditions = []
    args = []

    if tool_name:
        conditions.append("tool_name=%s")
        args.append(tool_name)
    if provider_name:
        conditions.append("provider_name=%s")
        args.append(provider_name)
    if start_time:
        conditions.append("created_at>=%s")
        args.append(start_time)
    if end_time:
        conditions.append("created_at<=%s")
        args.append(end_time)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    valid_groups = {"tool_name", "provider_name", "source", "DATE(created_at)"}
    if group_by not in valid_groups:
        group_by = "tool_name"

    sql = f"""
    SELECT
        {group_by} as group_key,
        SUM(prompt_tokens)     as total_prompt_tokens,
        SUM(completion_tokens) as total_completion_tokens,
        SUM(total_tokens)      as total_tokens,
        SUM(input_cost)        as input_cost,
        SUM(output_cost)       as output_cost,
        SUM(total_cost)        as total_cost,
        COUNT(*)               as request_count
    FROM external_usage
    {where_clause}
    GROUP BY {group_by}
    ORDER BY total_tokens DESC
    """

    async with DBHelper() as db:
        return await db.fetchall(sql, args)


async def get_external_usage_list(
    tool_name: Optional[str] = None,
    provider_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """分页查询外部使用记录"""
    conditions = []
    args = []

    if tool_name:
        conditions.append("tool_name=%s")
        args.append(tool_name)
    if provider_name:
        conditions.append("provider_name=%s")
        args.append(provider_name)
    if start_time:
        conditions.append("created_at>=%s")
        args.append(start_time)
    if end_time:
        conditions.append("created_at<=%s")
        args.append(end_time)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with DBHelper() as db:
        # 总数
        count_row = await db.fetchone(
            f"SELECT COUNT(*) as cnt FROM external_usage {where_clause}", args
        )
        total = int(count_row["cnt"]) if count_row else 0

        # 分页数据
        offset = (page - 1) * page_size
        rows = await db.fetchall(
            f"""
            SELECT * FROM external_usage {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            args + [page_size, offset],
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [dict(r) for r in rows],
    }
