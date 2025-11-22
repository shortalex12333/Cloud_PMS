"""
Pydantic models for third-party integrations (Outlook, etc.)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class OutlookAuthUrlResponse(BaseModel):
    """Response containing Microsoft OAuth URL"""
    auth_url: str
    state: str


class OutlookStatusResponse(BaseModel):
    """Response indicating if user has Outlook connected"""
    connected: bool
    provider_email: Optional[str] = None
    display_name: Optional[str] = None
    connected_at: Optional[datetime] = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback data"""
    code: str
    state: str
    error: Optional[str] = None
    error_description: Optional[str] = None


class IntegrationTokenData(BaseModel):
    """Integration token data for internal use"""
    user_id: str
    provider: str
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: datetime
    provider_user_id: Optional[str] = None
    provider_email: Optional[str] = None
    display_name: Optional[str] = None
    scopes: Optional[List[str]] = None
