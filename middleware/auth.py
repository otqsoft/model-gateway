"""
middleware/auth.py — API Key 认证中间件
解析 Authorization: Bearer <key>，验证 hash，返回 ApiKeyRow
"""
from __future__ import annotations
import logging
from fastapi import Request, HTTPException
from core.security import hash_gateway_key
from crud.api_keys import get_api_key_by_hash
from models.db_models import ApiKeyRow

logger = logging.getLogger("gateway.auth")


async def authenticate_request(request: Request) -> ApiKeyRow:
    """
    FastAPI 依赖项：从请求头提取并验证 API Key
    返回 ApiKeyRow 供后续中间件使用
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Missing or invalid Authorization header. "
                               "Use 'Authorization: Bearer <your-key>'",
                    "type": "auth_error",
                    "code": "missing_auth",
                }
            },
        )

    raw_key = auth_header[7:].strip()
    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Empty API key", "type": "auth_error"}},
        )

    key_hash = hash_gateway_key(raw_key)
    key_row = await get_api_key_by_hash(key_hash)

    if not key_row:
        logger.warning("[认证] API Key 无效，prefix=%s", raw_key[:8])
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid API key",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key",
                }
            },
        )

    if not key_row.is_enabled:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "message": "API key has been disabled",
                    "type": "auth_error",
                    "code": "key_disabled",
                }
            },
        )

    return key_row


async def authenticate_admin(request: Request) -> None:
    """
    管理端鉴权：验证 X-Admin-Token 请求头
    """
    from core.config import settings
    token = request.headers.get("X-Admin-Token", "")
    if token != settings.admin_token:
        raise HTTPException(
            status_code=403,
            detail={"error": {"message": "Invalid admin token", "type": "auth_error"}},
        )
