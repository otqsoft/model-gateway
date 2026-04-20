"""
middleware/time_control.py — API Key 时段访问控制
验证：日期范围、允许星期、每日时间段
"""
from __future__ import annotations
import logging
from datetime import datetime, date
from fastapi import HTTPException
from models.db_models import ApiKeyRow

logger = logging.getLogger("gateway.time_control")


def check_time_access(key_row: ApiKeyRow) -> None:
    """
    校验 API Key 时段访问规则，不通过则抛 HTTPException 403
    """
    now = datetime.now()
    today = now.date()
    current_time = now.time()
    current_weekday = now.isoweekday()  # 1=周一 ... 7=周日

    # ── 1. 日期范围校验 ──────────────────────────────────────
    if key_row.start_date and today < key_row.start_date:
        _deny(f"API Key 尚未生效，生效日期为 {key_row.start_date}")
    if key_row.end_date and today > key_row.end_date:
        _deny(f"API Key 已过期，过期日期为 {key_row.end_date}")

    # ── 2. 允许星期校验 ──────────────────────────────────────
    if key_row.allowed_weekdays:
        allowed = set(key_row.allowed_weekdays.split(","))
        if str(current_weekday) not in allowed:
            _deny(f"当前星期（{current_weekday}）不在允许访问范围内")

    # ── 3. 每日时间段校验 ────────────────────────────────────
    if key_row.allowed_time_start and key_row.allowed_time_end:
        start = _to_time(key_row.allowed_time_start)
        end = _to_time(key_row.allowed_time_end)
        if start and end:
            if not (start <= current_time <= end):
                _deny(
                    f"当前时间 {current_time.strftime('%H:%M')} "
                    f"不在允许访问时段 {start.strftime('%H:%M')}-{end.strftime('%H:%M')}"
                )


def _deny(reason: str):
    logger.warning("[时段控制] 拒绝访问: %s", reason)
    raise HTTPException(
        status_code=403,
        detail={
            "error": {
                "message": reason,
                "type": "access_denied",
                "code": "time_access_denied",
            }
        },
    )


def _to_time(t):
    """将 timedelta / time / str 统一转为 time 对象"""
    from datetime import timedelta, time
    if isinstance(t, time):
        return t
    if isinstance(t, timedelta):
        # MySQL TIME 列通过 aiomysql 可能返回 timedelta
        total_seconds = int(t.total_seconds())
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)
        return time(h, m, s)
    if isinstance(t, str):
        try:
            parts = t.split(":")
            return time(int(parts[0]), int(parts[1]))
        except Exception:
            return None
    return None
