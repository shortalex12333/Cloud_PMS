"""
Authentication models for CelesteOS Cloud API
Login, token, and user models
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class LoginRequest(BaseModel):
    """User login request"""

    email: EmailStr
    password: str
    yacht_signature: str


class LoginResponse(BaseModel):
    """User login response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserInfo"
    yacht: "YachtInfo"


class RefreshTokenRequest(BaseModel):
    """Token refresh request"""

    refresh_token: str
    yacht_signature: str


class RefreshTokenResponse(BaseModel):
    """Token refresh response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RevokeTokenRequest(BaseModel):
    """Token revocation request"""

    access_token: Optional[str] = None  # If not provided, revokes current token


class UserInfo(BaseModel):
    """User information"""

    id: UUID
    email: EmailStr
    name: str
    role: str
    yacht_id: UUID


class YachtInfo(BaseModel):
    """Yacht information"""

    id: UUID
    name: str
    signature: str
    status: str


# Update forward references
LoginResponse.model_rebuild()
