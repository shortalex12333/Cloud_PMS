"""
Search API endpoints
/v1/search route
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.core.auth import get_current_user, YachtContext

router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    """Search request"""
    query: str
    mode: str = "auto"  # auto, standard, graph
    filters: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """Individual search result"""
    type: str  # document_chunk, history_event, equipment, etc.
    id: UUID
    score: float
    text_preview: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchAction(BaseModel):
    """Suggested action from search"""
    label: str
    action: str
    context: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response"""
    query_id: UUID
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    results: List[SearchResult]
    actions: List[SearchAction] = []


@router.post("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search(
    request: SearchRequest,
    context: YachtContext = Depends(get_current_user)
):
    """
    Universal search endpoint

    Performs hybrid RAG search across:
    - Documents and chunks
    - Work order history
    - Equipment database
    - Fault logs
    - Graph RAG for multi-hop reasoning

    NOTE: Search logic delegated to separate search service/worker
    This endpoint validates input and routes to search pipeline
    """
    # TODO: Implement search pipeline integration
    # - Entity extraction
    # - Intent detection
    # - Standard RAG retrieval
    # - Graph RAG (if needed)
    # - Result fusion and ranking

    return SearchResponse(
        query_id=UUID("00000000-0000-0000-0000-000000000000"),
        intent="search",
        results=[],
        actions=[]
    )
