"""数据库初始化：建表 + 种子数据。"""
from app.core.database import Base, SessionLocal, engine
from app.core.logger import logger
from app.core.security import hash_password
from app.models.entities import User
from app import models  # noqa: F401  确保模型注册到 Base.metadata


def init_db() -> None:
    logger.info("creating database tables ...")
    Base.metadata.create_all(bind=engine)
    logger.info("database tables ready")


def seed_db() -> None:
    """插入默认用户（admin/legal/employee）。"""
    db = SessionLocal()
    try:
        existing = db.query(User).count()
        if existing:
            return
        defaults = [
            User(username="admin", password_hash=hash_password("admin123"),
                 role="admin", department="信息中心"),
            User(username="legal", password_hash=hash_password("legal123"),
                 role="legal", department="法务部"),
            User(username="employee", password_hash=hash_password("emp123"),
                 role="employee", department="采购部"),
        ]
        db.add_all(defaults)
        db.commit()
        logger.info("seed users created: admin / legal / employee")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_db()
