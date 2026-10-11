"""认证 API。"""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.entities import User
from app.schemas.chat import LoginRequest, TokenResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db=Depends(get_db)):
    result = UserService(db).authenticate(req.username, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return TokenResponse(access_token=result["access_token"])


@router.get("/profile")
def profile(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "role": current_user.role,
        "department": current_user.department,
    }
