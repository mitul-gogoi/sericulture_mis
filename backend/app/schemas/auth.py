"""Auth request/response DTOs."""
from typing import Any, Dict
from pydantic import BaseModel

__all__ = ["LoginIn", "TokenOut", "RefreshIn", "ChangePasswordIn"]


class LoginIn(BaseModel):
    mobile_no: str
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class RefreshIn(BaseModel):
    refresh_token: str
