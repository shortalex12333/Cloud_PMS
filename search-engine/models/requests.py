"""
Request models for search engine API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class SearchRequest(BaseModel):
    """Request model for search endpoint"""

    query: str = Field(..., min_length=1, description="Search query text")
    mode: str = Field(default="auto", description="Search mode: auto, rag, graph_rag")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters for equipment_id, document_type, etc."
    )
    partial: bool = Field(
        default=False,
        description="Whether this is a partial query (for autocomplete)"
    )
    top_k: Optional[int] = Field(
        default=None,
        description="Number of results to return"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "fault code E047 on main engine",
                "mode": "auto",
                "filters": {
                    "equipment_id": None,
                    "document_type": None
                }
            }
        }


class BatchSearchRequest(BaseModel):
    """Request model for batch search endpoint"""

    queries: List[str] = Field(..., min_items=1, max_items=50)
    mode: str = Field(default="auto")
    filters: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "queries": [
                    "CAT 3516 coolant manual",
                    "stabiliser pump leak fix"
                ]
            }
        }
