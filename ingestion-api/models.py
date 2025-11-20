"""
Pydantic models for request/response validation
"""
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
import re


class IngestionInitRequest(BaseModel):
    """Request to initialize a file upload"""
    filename: str = Field(..., min_length=1, max_length=512)
    sha256: str = Field(..., min_length=64, max_length=64)
    size_bytes: int = Field(..., gt=0)
    source: Literal["nas", "email", "upload", "mobile"] = "nas"

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[a-f0-9]{64}$", v.lower()):
            raise ValueError("Invalid SHA256 hash format")
        return v.lower()

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        # Sanitize filename - remove path traversal attempts
        v = v.replace("..", "").replace("/", "_").replace("\\", "_")
        if not v:
            raise ValueError("Invalid filename")
        return v


class IngestionInitResponse(BaseModel):
    """Response from init endpoint"""
    upload_id: UUID
    storage_key: str
    expected_chunks: int
    status: str = "pending"


class UploadChunkResponse(BaseModel):
    """Response from chunk upload"""
    status: Literal["ok", "error"] = "ok"
    message: Optional[str] = None


class IngestionCompleteRequest(BaseModel):
    """Request to complete and assemble upload"""
    upload_id: UUID
    total_chunks: int = Field(..., gt=0)
    sha256: str = Field(..., min_length=64, max_length=64)
    filename: str = Field(..., min_length=1, max_length=512)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[a-f0-9]{64}$", v.lower()):
            raise ValueError("Invalid SHA256 hash format")
        return v.lower()


class IngestionCompleteResponse(BaseModel):
    """Response from complete endpoint"""
    document_id: UUID
    status: Literal["received", "error"]
    queued_for_indexing: bool
    message: Optional[str] = None


class IngestionState(BaseModel):
    """Internal model for tracking ingestion state"""
    upload_id: UUID
    yacht_id: UUID
    filename: str
    file_sha256: str
    file_size: int
    total_chunks: int
    chunks_received: int = 0
    status: Literal[
        "INITIATED",
        "UPLOADING",
        "ASSEMBLING",
        "VERIFYING",
        "UPLOADED",
        "READY_FOR_INDEXING",
        "ERROR"
    ]
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    source: str = "nas"


class DocumentMetadata(BaseModel):
    """Metadata for a document in Supabase"""
    document_id: UUID
    yacht_id: UUID
    filename: str
    file_sha256: str
    storage_path: str
    file_size: int
    original_name: str
    source: str
    status: str
    content_type: Optional[str] = None
    created_at: datetime
