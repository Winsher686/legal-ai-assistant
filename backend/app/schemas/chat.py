"""Pydantic 请求/响应模型。"""
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- 认证 ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- 问答 ----------
class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


class SourceItem(BaseModel):
    citation_id: str = ""
    document_id: str = ""
    document_name: str = ""
    chapter: str = ""
    article: str = ""
    page: int = 0
    text: str = ""


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem] = []
    confidence: float = 0.0
    intent: str = ""


# ---------- 文档 ----------
class DocumentItem(BaseModel):
    id: str
    name: str
    type: str
    version: str
    status: str
    created_at: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentItem] = []


class UploadResponse(BaseModel):
    document_id: str
    status: str


class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: int = 0
