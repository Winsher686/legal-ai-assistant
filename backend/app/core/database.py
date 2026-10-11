"""数据库会话管理（SQLAlchemy）。"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Mock 模式使用 SQLite 便于本地验证
if settings.USE_MOCK:
    # 优先使用项目根目录 storage/mock.db，不存在则退回内存 SQLite
    storage_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "storage")
    storage_dir = os.path.abspath(storage_dir)
    os.makedirs(storage_dir, exist_ok=True)
    db_path = os.path.join(storage_dir, "mock.db")
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args=connect_args, future=True
    )
else:
    engine = create_engine(settings.postgres_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

Base = declarative_base()


def get_db():
    """FastAPI 依赖：提供数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
