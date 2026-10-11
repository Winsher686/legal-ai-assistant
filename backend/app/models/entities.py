"""SQLAlchemy 数据模型（对应 PostgreSQL 业务数据表）。"""
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """用户表 user。"""
    __tablename__ = "user"

    id = Column(String(36), primary_key=True, default=_uuid)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False, default="employee")  # admin/legal/employee
    department = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    """文档信息表 document。"""
    __tablename__ = "document"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    type = Column(String(64), nullable=False)  # contract_template/regulation/company_policy/case_file/process_document
    path = Column(String(512), default="")
    version = Column(String(64), default="V1.0")
    status = Column(String(32), default="pending")  # pending/processing/completed/failed
    uploader_id = Column(String(36), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentChunk(Base):
    """文档切片表 document_chunk（业务关联，向量在 Milvus）。"""
    __tablename__ = "document_chunk"

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), nullable=False, index=True)
    content = Column(Text, default="")
    page_number = Column(Integer, default=0)
    chapter = Column(String(255), default="")
    article = Column(String(64), default="")
    vector_id = Column(String(128), default="")  # Milvus 对应 ID
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentTask(Base):
    """文档处理任务表 document_task。"""
    __tablename__ = "document_task"

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), nullable=False, index=True)
    task_type = Column(String(32), default="parse")  # parse/embedding/graph_extract
    status = Column(String(32), default="pending")  # pending/running/success/failed
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatHistory(Base):
    """查询记录表 chat_history。"""
    __tablename__ = "chat_history"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), default="")
    question = Column(Text, default="")
    answer = Column(Text, default="")
    sources = Column(JSON, default=list)
    confidence = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentPermission(Base):
    """权限表 document_permission。"""
    __tablename__ = "document_permission"

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), nullable=False, index=True)
    department = Column(String(64), default="")
    permission = Column(String(16), default="read")  # read/write
