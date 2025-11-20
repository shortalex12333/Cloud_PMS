"""
Response models for ingestion API
"""
from pydantic import BaseModel, Field
from typing import Optional


class InitUploadResponse(BaseModel):
    """Response for init upload"""

    upload_id: str
    storage_key: str
    expected_chunks: int


class UploadChunkResponse(BaseModel):
    """Response for chunk upload"""

    status: str = "ok"
    chunk_index: int
    upload_id: str


class CompleteUploadResponse(BaseModel):
    """Response for complete upload"""

    document_id: str
    status: str
    queued_for_indexing: bool
    storage_path: str
