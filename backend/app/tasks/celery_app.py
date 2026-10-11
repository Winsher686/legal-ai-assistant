"""Celery 应用配置。"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "legal_ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.tasks"], force=True)
