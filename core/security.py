"""
core/security.py — API Key 加密/哈希工具
使用 Fernet 对称加密存储上游 Key，SHA-256 哈希校验网关 Key
"""
from __future__ import annotations
import hashlib
import base64
import os
import hmac
import shortuuid
from typing import Optional, Tuple
from cryptography.fernet import Fernet
from core.config import settings


# 懒加载单例，避免模块导入时立即执行（防止配置未就绪时报错）
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """根据 ENCRYPT_SECRET_KEY 初始化 Fernet 实例（懒加载）"""
    global _fernet
    if _fernet is not None:
        return _fernet

    secret = settings.encrypt_secret_key.strip()
    if not secret:
        # 无配置时生成随机 key（仅开发模式，重启会变，不影响启动）
        key = Fernet.generate_key()
    else:
        # 将用户配置的任意字符串规范化为 Fernet 所需的 32 字节 URL-safe Base64
        try:
            # 尝试当作 base64 解码
            # 补齐 padding，避免 "Incorrect padding" 错误
            padded = secret + "=" * (-len(secret) % 4)
            raw = base64.b64decode(padded)[:32]
        except Exception:
            # 解码失败则直接把字符串当原始字节用
            raw = secret.encode()[:32]
        # 不足 32 字节则补零，保证 Fernet key 合法
        raw = raw.ljust(32, b'\x00')[:32]
        key = base64.urlsafe_b64encode(raw)

    _fernet = Fernet(key)
    return _fernet


def encrypt_api_key(plaintext: str) -> str:
    """加密上游 API Key，返回 Base64 密文"""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """解密上游 API Key"""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def hash_gateway_key(key: str) -> str:
    """对网关 API Key 做 SHA-256 哈希，用于数据库存储与验证"""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_gateway_key() -> Tuple[str, str, str]:
    """
    生成网关 API Key
    返回 (full_key, key_id, key_prefix)
    full_key 形如 sk-xxxxxxxxxxxxxxxxxxxxxx（22位随机）
    """
    uid = shortuuid.uuid()[:21]   # 21位 + "sk-"(3) = 24字符，匹配 DB CHAR(24)
    full_key = f"sk-{uid}"
    key_id = full_key          # key_id = full_key（CHAR(24)）
    key_prefix = full_key[:8]  # 前8位用于展示
    return full_key, key_id, key_prefix

