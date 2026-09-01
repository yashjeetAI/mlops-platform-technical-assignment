"""Auth request/response schemas."""
from datetime import datetime
from uuid import UUID

from pydantic import EmailStr

from app.core.enums import Role
from app.schemas.base import CamelModel


class LoginRequest(CamelModel):
    username: str
    password: str


class TokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(CamelModel):
    id: UUID
    username: str
    email: EmailStr
    full_name: str
    role: Role
    created_at: datetime
