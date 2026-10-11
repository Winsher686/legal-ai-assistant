"""安全与认证工具：密码哈希、JWT 签发与校验、RBAC 权限。"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"

# 角色 → 可访问文档类型（RBAC）
ROLE_PERMISSIONS = {
    "admin": {"*"},                    # 管理员：全部
    "legal": {"contract_template", "regulation", "company_policy", "case_file", "process_document"},
    "employee": {"company_policy", "process_document"},  # 普通员工：公开制度/流程
}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, extra: Optional[dict] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """解析 JWT，失败返回 None。"""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def has_permission(role: str, document_type: str) -> bool:
    """判断角色是否有权访问某类文档。"""
    allowed = ROLE_PERMISSIONS.get(role)
    if allowed is None:
        return False
    if "*" in allowed:
        return True
    return document_type in allowed
