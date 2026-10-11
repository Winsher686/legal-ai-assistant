"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    try:
        from app.database.init_db import init_db, seed_db

        init_db()
        seed_db()
    except Exception as e:
        logger.warning("init_db failed: %s", e)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="企业法务知识库与法规制度智能问答系统（RAG + GraphRAG）",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/health")
def health():
    from app.core.health import get_health

    return get_health()


@app.get("/health/live")
def health_live():
    """存活探针（K8s/Docker 用）：进程活着即返回 200。"""
    return {"status": "alive"}


@app.get("/")
def root():
    return {"message": settings.APP_NAME, "docs": "/docs", "health": "/health"}
