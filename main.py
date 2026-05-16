"""
main.py — AI Model Gateway 应用入口
FastAPI + asyncio + aiohttp，OpenAI 兼容网关
"""
import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

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
    title="模型网关",
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
from api.admin.agents import router as agents_router

app.include_router(overview_router)
app.include_router(monitor_router)
app.include_router(keys_router)
app.include_router(providers_router)
app.include_router(logs_router)
app.include_router(billing_router)
app.include_router(model_admin_router)
app.include_router(agents_router)


# ── 健康检查 ──────────────────────────────────────────────────
@app.get("/health", summary="健康检查", tags=["系统"])
async def health():
    return {"status": "ok", "service": "AI Model Gateway"}


@app.get("/", summary="根路由重定向到管理界面", tags=["系统"])
async def root():
    """根路由重定向到管理界面"""
    return RedirectResponse(url="/browser/")

@app.get("/manager/", summary="管理界面前端入口", tags=["系统"])
@app.get("/manager", summary="管理后台前端入口", tags=["系统"])
async def admin_ui():
    """管理后台前端入口"""
    static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return JSONResponse(
        status_code=404,
        content={"error": "前端文件不存在，请确认 static/index.html 已生成"},
    )


@app.get("/browser", summary="只读浏览界面（无需 Admin Token）", tags=["系统"])
@app.get("/browser/", summary="只读浏览界面入口", tags=["系统"])
async def browser_ui():
    """
    只读浏览模式入口，无需手动输入 Admin Token。
    - 所有数据均可查看
    - 禁止新增 / 编辑 / 删除操作
    - 隐藏系统设置和顶部 Token 输入框
    """
    static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if not os.path.exists(static_file):
        return JSONResponse(
            status_code=404,
            content={"error": "前端文件不存在，请确认 static/index.html 已生成"},
        )
    with open(static_file, "r", encoding="utf-8") as f:
        html = f.read()

    # 在 <script> 块最开始注入两个变量：
    #   BROWSER_MODE  = true   → 前端进入只读模式
    #   BROWSER_TOKEN = <token> → 自动填入合法 Admin Token，无需用户输入
    inject = (
        f'<script>window.BROWSER_MODE=true;'
        f'window.BROWSER_TOKEN={repr(settings.admin_token)};</script>\n'
    )
    html = html.replace("</head>", inject + "</head>", 1)
    return HTMLResponse(content=html)


# ── 静态文件服务（放在所有路由之后）───────────────────────────
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


# ── 入口 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8086,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
