"""
db/database.py — MySQL 异步连接池（基于 aiomysql）
"""
from __future__ import annotations
import aiomysql
import logging
from typing import Optional, List
from core.config import settings

logger = logging.getLogger("gateway.db")

# 全局连接池
_pool: Optional[aiomysql.Pool] = None


async def init_db_pool() -> None:
    """初始化连接池，应在 FastAPI lifespan 中调用"""
    global _pool
    _pool = await aiomysql.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        db=settings.db_name,
        minsize=settings.db_pool_min,
        maxsize=settings.db_pool_max,
        charset="utf8mb4",
        autocommit=True,
        cursorclass=aiomysql.DictCursor,  # 返回字典格式结果
    )
    logger.info("数据库连接池初始化完成 pool_min=%d pool_max=%d",
                settings.db_pool_min, settings.db_pool_max)


async def close_db_pool() -> None:
    """关闭连接池"""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        logger.info("数据库连接池已关闭")


def get_pool() -> aiomysql.Pool:
    """获取全局连接池"""
    if _pool is None:
        raise RuntimeError("数据库连接池尚未初始化，请先调用 init_db_pool()")
    return _pool


class DBHelper:
    """
    数据库操作辅助类，提供 execute / fetchone / fetchall 等方法
    使用 async with DBHelper() as db: 自动管理连接
    """

    def __init__(self):
        self._conn: Optional[aiomysql.Connection] = None
        self._cursor: Optional[aiomysql.DictCursor] = None

    async def __aenter__(self):
        pool = get_pool()
        self._conn = await pool.acquire()
        self._cursor = await self._conn.cursor(aiomysql.DictCursor)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._cursor:
            await self._cursor.close()
        if self._conn:
            get_pool().release(self._conn)
        return False

    async def execute(self, sql: str, args=None) -> int:
        """执行写操作，返回 lastrowid（INSERT 场景）"""
        await self._cursor.execute(sql, args)
        return self._cursor.lastrowid

    async def execute_delete(self, sql: str, args=None) -> int:
        """执行 DELETE/UPDATE，返回 affected rows"""
        await self._cursor.execute(sql, args)
        return self._cursor.rowcount

    async def fetchone(self, sql: str, args=None) -> Optional[dict]:
        """查询单行"""
        await self._cursor.execute(sql, args)
        return await self._cursor.fetchone()

    async def fetchall(self, sql: str, args=None) -> List[dict]:
        """查询多行"""
        await self._cursor.execute(sql, args)
        return await self._cursor.fetchall()

    async def execute_many(self, sql: str, args_list: list) -> int:
        """批量执行"""
        await self._cursor.executemany(sql, args_list)
        return self._cursor.rowcount
