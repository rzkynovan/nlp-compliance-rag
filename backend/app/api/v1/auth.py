"""
auth.py — Authentication endpoints.

POST /auth/login   → { access_token, token_type, role }
GET  /auth/me      → { username, role }
POST /auth/logout  → 200 OK (client drops token)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db, UserRow
from app.core.auth import verify_password, create_access_token, get_current_user
from app.models.user import TokenResponse, UserResponse
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserRow).filter_by(username=request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah",
        )
    token = create_access_token(username=user.username, role=user.role)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/me", response_model=UserResponse)
def me(current_user: UserResponse = Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout():
    # Token-based auth — client drops the token; nothing to invalidate server-side
    return {"message": "Logout berhasil"}
