"""API 路由聚合。"""
from fastapi import APIRouter

from app.api import auth, chat, document, knowledge

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(document.router)
api_router.include_router(knowledge.router)
