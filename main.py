"""
main.py — AI Model Gateway 应用入口
FastAPI + asyncio + aiohttp，OpenAI 兼容网关
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from db.database import init_db_pool, close_db_pool

# ── 日志配置 ──────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("gateway")


# ── 应用生命周期 ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库连接池，关闭时释放"""
    logger.info("=== AI Model Gateway 启动中 ===")
    await init_db_pool()
    logger.info("=== 服务就绪 ===")
    yield
    logger.info("=== AI Model Gateway 关闭中 ===")
    await close_db_pool()


# ── 创建 FastAPI 应用 ─────────────────────────────────────────
app = FastAPI(
    title="AI Model Gateway",
    description="多平台大模型统一网关，完全兼容 OpenAI v1 接口",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 全局异常处理 ──────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("未捕获异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"message": "内部服务器错误", "type": "internal_error"}},
    )


# ── 路由注册 ──────────────────────────────────────────────────

# OpenAI 兼容接口
from api.v1.chat import router as chat_router
from api.v1.models_list import router as models_router

app.include_router(chat_router)
app.include_router(models_router)

# 管理端接口
from api.admin.overview import router as overview_router
from api.admin.monitor import router as monitor_router
from api.admin.keys import router as keys_router
from api.admin.providers import router as providers_router
from api.admin.logs import router as logs_router
from api.admin.billing_api import router as billing_router
from api.admin.model_admin import router as model_admin_router

app.include_router(overview_router)
app.include_router(monitor_router)
app.include_router(keys_router)
app.include_router(providers_router)
app.include_router(logs_router)
app.include_router(billing_router)
app.include_router(model_admin_router)


# ── 健康检查 ──────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "AI Model Gateway"}


@app.get("/")
async def root():
    return {
        "service": "AI Model Gateway",
        "version": "1.0.0",
        "docs": "/docs",
        "openai_compatible": True,
        "endpoints": {
            "chat": "/v1/chat/completions",
            "models": "/v1/models",
            "admin": "/admin/overview",
        },
    }


# ── 入口 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
