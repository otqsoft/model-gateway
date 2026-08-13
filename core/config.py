"""
core/config.py — 全局配置，从环境变量读取
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # ── 数据库 ──────────────────────────────────────────────
    db_host: str = Field("127.0.0.1", env="DB_HOST")
    db_port: int = Field(3306, env="DB_PORT")
    db_user: str = Field("root", env="DB_USER")
    db_password: str = Field("", env="DB_PASSWORD")
    db_name: str = Field("model_gateway", env="DB_NAME")
    db_pool_min: int = Field(5, env="DB_POOL_MIN")
    db_pool_max: int = Field(20, env="DB_POOL_MAX")

    # ── 加密 ────────────────────────────────────────────────
    encrypt_secret_key: str = Field("", env="ENCRYPT_SECRET_KEY")

    # ── 并发控制 ────────────────────────────────────────────
    global_max_concurrency: int = Field(200, env="GLOBAL_MAX_CONCURRENCY")
    key_max_concurrency: int = Field(20, env="KEY_MAX_CONCURRENCY")

    # ── 管理端 ───────────────────────────────────────────────
    admin_token: str = Field("change_me", env="ADMIN_TOKEN")

    # ── 服务 ─────────────────────────────────────────────────
    app_env: str = Field("development", env="APP_ENV")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # ── HTTPS / SSL ──────────────────────────────────────────
    ssl_enabled: bool = Field(False, env="SSL_ENABLED")
    ssl_cert_dir: str = Field("certs", env="SSL_CERT_DIR")
    ssl_cert_file: str = Field("cert.pem", env="SSL_CERT_FILE")
    ssl_key_file: str = Field("key.pem", env="SSL_KEY_FILE")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
