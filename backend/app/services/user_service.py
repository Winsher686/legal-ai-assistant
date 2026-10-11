"""用户认证服务。"""
from typing import Optional

from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import User
from app.repositories.repository import UserRepository


class UserService:
    def __init__(self, db):
        self.db = db
        self.repo = UserRepository(db)

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        user = self.repo.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            return None
        token = create_access_token(
            subject=str(user.id),
            extra={"username": user.username, "role": user.role, "department": user.department},
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user.username,
            "role": user.role,
        }
