"""
crud/request_logs.py — 请求生命周期日志 CRUD
"""
from typing import Optional
from datetime import datetime
from db.database import DBHelper


async def create_request_log(
    request_id: str,
    api_key_id: Optional[int],
    key_id: Optional[str],
    model_alias: str,
    is_stream: bool,
    client_ip: Optional[str],
) -> None:
    """创建初始日志记录（pending 状态）"""
    sql = """
    INSERT INTO request_logs
        (request_id, api_key_id, key_id, model_alias, status, is_stream, client_ip, started_at)
    VALUES (%s, %s, %s, %s, 'pending', %s, %s, NOW(3))
    """
    async with DBHelper() as db:
        await db.execute(sql, (request_id, api_key_id, key_id, model_alias,
                               int(is_stream), client_ip))


async def update_log_running(request_id: str, provider_name: str, upstream_model: str) -> None:
    """更新状态为 running"""
    sql = """
    UPDATE request_logs
    SET status='running', provider_name=%s, upstream_model=%s
    WHERE request_id=%s
    """
    async with DBHelper() as db:
        await db.execute(sql, (provider_name, upstream_model, request_id))


async def update_log_success(
    request_id: str,
    upstream_status: int,
    prompt_tokens: int,
    completion_tokens: int,
    ttft_ms: Optional[int],
    duration_ms: int,
) -> None:
    """更新状态为 success"""
    total_tokens = prompt_tokens + completion_tokens
    sql = """
    UPDATE request_logs
    SET status='success',
        upstream_status=%s,
        prompt_tokens=%s,
        completion_tokens=%s,
        total_tokens=%s,
        ttft_ms=%s,
        duration_ms=%s,
        ended_at=NOW(3)
    WHERE request_id=%s
    """
    async with DBHelper() as db:
        await db.execute(sql, (
            upstream_status, prompt_tokens, completion_tokens,
            total_tokens, ttft_ms, duration_ms, request_id
        ))


async def update_log_error(
    request_id: str,
    upstream_status: Optional[int],
    error_message: str,
    duration_ms: int,
    is_timeout: bool = False,
) -> None:
    """更新状态为 error 或 timeout"""
    status = "timeout" if is_timeout else "error"
    sql = """
    UPDATE request_logs
    SET status=%s,
        upstream_status=%s,
        error_message=%s,
        duration_ms=%s,
        ended_at=NOW(3)
    WHERE request_id=%s
    """
    async with DBHelper() as db:
        await db.execute(sql, (status, upstream_status, error_message, duration_ms, request_id))


async def get_log_by_request_id(request_id: str) -> Optional[dict]:
    """按 request_id 查询单条日志"""
    async with DBHelper() as db:
        return await db.fetchone(
            "SELECT * FROM request_logs WHERE request_id=%s", (request_id,)
        )


async def query_logs(
    request_id: Optional[str] = None,
    key_id: Optional[str] = None,
    model_alias: Optional[str] = None,
    provider_name: Optional[str] = None,
    status: Optional[str] = None,
    upstream_status: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """多条件分页查询日志"""
    conditions = []
    args = []

    if request_id:
        conditions.append("request_id=%s")
        args.append(request_id)
    if key_id:
        conditions.append("key_id=%s")
        args.append(key_id)
    if model_alias:
        conditions.append("model_alias=%s")
        args.append(model_alias)
    if provider_name:
        conditions.append("provider_name=%s")
        args.append(provider_name)
    if status:
        conditions.append("status=%s")
        args.append(status)
    if upstream_status is not None:
        conditions.append("upstream_status=%s")
        args.append(upstream_status)
    if start_time:
        conditions.append("started_at >= %s")
        args.append(start_time)
    if end_time:
        conditions.append("started_at <= %s")
        args.append(end_time)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size

    async with DBHelper() as db:
        cnt_row = await db.fetchone(
            f"SELECT COUNT(*) as cnt FROM request_logs {where_clause}", args
        )
        total = cnt_row["cnt"] if cnt_row else 0

        rows = await db.fetchall(
            f"SELECT * FROM request_logs {where_clause} "
            f"ORDER BY started_at DESC LIMIT %s OFFSET %s",
            args + [page_size, offset]
        )
    return rows, total


async def get_overview_stats() -> dict:
    """总览统计查询"""
    async with DBHelper() as db:
        # 全量统计
        all_stats = await db.fetchone("""
            SELECT
                COUNT(*) as total_requests,
                SUM(status='success') as success_requests,
                SUM(status='error') as error_requests,
                SUM(status='timeout') as timeout_requests,
                SUM(total_tokens) as total_tokens,
                AVG(duration_ms) as avg_duration_ms
            FROM request_logs
        """)
        # 今日统计
        today_stats = await db.fetchone("""
            SELECT
                COUNT(*) as requests_today,
                SUM(total_tokens) as tokens_today
            FROM request_logs
            WHERE DATE(started_at) = CURDATE()
        """)
    return {**(all_stats or {}), **(today_stats or {})}


async def get_status_distribution() -> list[dict]:
    """状态分布"""
    async with DBHelper() as db:
        return await db.fetchall("""
            SELECT status, COUNT(*) as count
            FROM request_logs
            GROUP BY status
        """)


async def get_latency_distribution() -> list[dict]:
    """耗时分布（按桶）"""
    async with DBHelper() as db:
        return await db.fetchall("""
            SELECT
                CASE
                    WHEN duration_ms < 500   THEN '0-500ms'
                    WHEN duration_ms < 1000  THEN '500ms-1s'
                    WHEN duration_ms < 3000  THEN '1s-3s'
                    WHEN duration_ms < 5000  THEN '3s-5s'
                    WHEN duration_ms < 10000 THEN '5s-10s'
                    ELSE '>10s'
                END as bucket,
                COUNT(*) as count
            FROM request_logs
            WHERE duration_ms IS NOT NULL
            GROUP BY bucket
            ORDER BY MIN(duration_ms)
        """)


async def get_upstream_status_distribution() -> list[dict]:
    """上游状态码分布"""
    async with DBHelper() as db:
        return await db.fetchall("""
            SELECT upstream_status, COUNT(*) as count
            FROM request_logs
            WHERE upstream_status IS NOT NULL
            GROUP BY upstream_status
            ORDER BY count DESC
        """)
