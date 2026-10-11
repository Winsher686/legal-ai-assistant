"""健康检查：返回各依赖（PostgreSQL/Redis/Milvus/Neo4j）的真实状态。

Mock 模式下各依赖标记为 degraded（本地无重组件，属预期）。
"""
from typing import Dict

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.logger import logger


def _check_postgres() -> str:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:
        logger.warning("postgres health check failed: %s", e)
        return "down"


def _check_redis() -> str:
    try:
        from app.utils.rate_limit import _get_redis

        r = _get_redis()
        if r is None:
            return "down"
        r.ping()
        return "ok"
    except Exception as e:
        logger.warning("redis health check failed: %s", e)
        return "down"


def _check_milvus() -> str:
    try:
        from app.rag.vector_store import get_vector_store

        get_vector_store().backend.count()
        return "ok"
    except Exception as e:
        logger.warning("milvus health check failed: %s", e)
        return "down"


def _check_neo4j() -> str:
    try:
        from app.graph.graph_store import get_graph_store

        get_graph_store().backend.find_related("__health_probe__")
        return "ok"
    except Exception as e:
        logger.warning("neo4j health check failed: %s", e)
        return "down"


def get_health() -> Dict:
    """汇总健康状态。Mock 模式下依赖标记为 degraded。"""
    if settings.USE_MOCK:
        deps = {k: "degraded" for k in
                ("postgres", "redis", "milvus", "neo4j")}
        return {
            "status": "ok",
            "service": settings.APP_NAME,
            "env": settings.APP_ENV,
            "mock": True,
            "dependencies": deps,
        }

    deps = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "milvus": _check_milvus(),
        "neo4j": _check_neo4j(),
    }
    overall = "ok" if all(v == "ok" for v in deps.values()) else "degraded"
    return {
        "status": overall,
        "service": settings.APP_NAME,
        "env": settings.APP_ENV,
        "mock": False,
        "dependencies": deps,
    }
