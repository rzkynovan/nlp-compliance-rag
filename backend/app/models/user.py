"""
user.py — User models for role-based access control.
Two roles: basic (audit + history only) and advanced (all features).
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel


UserRole = Literal["basic", "advanced"]


class UserResponse(BaseModel):
    username: str
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole


class TokenData(BaseModel):
    username: str
    role: UserRole
