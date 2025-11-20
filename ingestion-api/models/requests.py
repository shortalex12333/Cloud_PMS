"""
Request models for ingestion API
"""
from pydantic import BaseModel, Field
from typing import Optional


class InitUploadRequest(BaseModel):
    """Initialize upload session"""

    filename: str = Field(..., min_length=1, max_length=255)
    sha256: str = Field(..., min_length=64, max_length=64)
    size_bytes: int = Field(..., gt=0)
    source: str = Field(default="nas")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "MTU_Manual_2019.pdf",
                "sha256": "a1b2c3d4e5f6...",
                "size_bytes": 534553000,
                "source": "nas"
            }
        }


class CompleteUploadRequest(BaseModel):
    """Complete upload session"""

    upload_id: str = Field(..., min_length=1)
    total_chunks: int = Field(..., gt=0)
    sha256: str = Field(..., min_length=64, max_length=64)
    filename: str = Field(..., min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "upload_id": "uuid-here",
                "total_chunks": 17,
                "sha256": "a1b2c3d4e5f6...",
                "filename": "MTU_Manual_2019.pdf"
            }
        }
