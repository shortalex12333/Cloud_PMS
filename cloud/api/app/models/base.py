"""
Base Pydantic models for CelesteOS Cloud API
Common response formats and base classes
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime
from uuid import UUID


class SuccessResponse(BaseModel):
    """Standard success response"""

    status: str = "success"
    data: Optional[Any] = None
    message: Optional[str] = None


class ErrorDetail(BaseModel):
    """Error detail structure"""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: ErrorDetail


class PaginatedResponse(BaseModel):
    """Paginated response structure"""

    items: List[Any]
    total: int
    page: int
    page_size: int
    has_next: bool


class TimestampMixin(BaseModel):
    """Mixin for models with timestamps"""

    created_at: datetime
    updated_at: datetime


class UUIDModel(BaseModel):
    """Base model with UUID"""

    id: UUID
