"""
core/utils.py — 公共工具函数
"""
import uuid
import time
import json
from datetime import datetime, timezone
from typing import Any, Optional, Union


def new_request_id() -> str:
    """生成 UUID v4 请求 ID"""
    return str(uuid.uuid4())


def now_utc() -> datetime:
    """返回 UTC 当前时间"""
    return datetime.now(timezone.utc)


def now_ms() -> int:
    """返回当前时间戳（毫秒）"""
    return int(time.time() * 1000)


def calc_duration_ms(start_ms: int) -> int:
    """计算从 start_ms 到现在的耗时（毫秒）"""
    return now_ms() - start_ms


def safe_json_loads(s: Optional[Union[str, bytes]]) -> Any:
    """安全 JSON 解析，失败返回 None"""
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def sse_line(data: str) -> str:
    """格式化为 SSE data 行"""
    return f"data: {data}\n\n"


def sse_done() -> str:
    """SSE 结束标记"""
    return "data: [DONE]\n\n"


def build_error_response(
    message: str,
    error_type: str = "internal_error",
    code: Optional[str] = None,
    status_code: int = 500,
) -> dict:
    """构造 OpenAI 兼容错误响应体"""
    return {
        "error": {
            "message": message,
            "type": error_type,
            "code": code,
            "param": None,
        }
    }


def mask_key(key: str) -> str:
    """遮蔽 Key，只显示前 8 位和后 4 位"""
    if len(key) <= 12:
        return key[:4] + "****"
    return key[:8] + "****" + key[-4:]


# 请求体日志摘要限制
_REQ_STR_MAX = 512      # 单个字符串值最大长度（截断 base64 图片等）
_REQ_TOTAL_MAX = 65536  # 序列化结果总长度上限（64KB）


def summarize_request_body(body) -> str:
    """
    将请求体序列化为 JSON 字符串用于日志存储。
    - 超长字符串值（如 base64 图片）截断，保留前缀并标注原始长度
    - 总长度超过上限时整体截断
    """
    def _shrink(obj):
        if isinstance(obj, str):
            if len(obj) > _REQ_STR_MAX:
                return obj[:_REQ_STR_MAX] + f"...[已截断，原始长度 {len(obj)}]"
            return obj
        if isinstance(obj, dict):
            return {k: _shrink(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_shrink(v) for v in obj]
        return obj

    try:
        data = body.model_dump(exclude_none=True) if hasattr(body, "model_dump") else body
        s = json.dumps(_shrink(data), ensure_ascii=False)
    except Exception:
        return ""
    if len(s) > _REQ_TOTAL_MAX:
        s = s[:_REQ_TOTAL_MAX] + "...[已截断]"
    return s
