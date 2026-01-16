"""
Context Navigation Routes

API endpoints for situational continuity layer.
Handles navigation context lifecycle, related expansion, and user relations.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

# Placeholder imports - will implement in Phase 4
# from ..context_nav.schemas import (
#     NavigationContextCreate,
#     NavigationContext,
#     RelatedRequest,
#     RelatedResponse,
#     AddRelatedRequest,
#     AddRelatedResponse,
# )
# from ..handlers.context_navigation_handlers import (
#     create_navigation_context,
#     update_active_anchor,
#     get_related_artifacts,
#     add_user_relation,
#     end_navigation_context,
# )

router = APIRouter()


@router.post("/create")
async def create_context():
    """
    Create a new navigation context when user opens an artifact from search.

    This is the entry point for situational continuity.
    """
    # TODO: Implement in Phase 4
    raise HTTPException(status_code=501, detail="Not implemented - Phase 4")


@router.put("/{context_id}/update-anchor")
async def update_anchor():
    """
    Update the active anchor when user navigates to a different artifact.

    This does NOT create a new context - it replaces the anchor within the same context.
    """
    # TODO: Implement in Phase 4
    raise HTTPException(status_code=501, detail="Not implemented - Phase 4")


@router.post("/related")
async def get_related():
    """
    Get related artifacts for the current anchor (deterministic expansion only).

    CRITICAL: NO vector search, NO LLMs, NO ranking.
    Only JOIN/FK-based queries and user-added relations.
    """
    # TODO: Implement in Phase 4
    raise HTTPException(status_code=501, detail="Not implemented - Phase 4")


@router.post("/add-relation")
async def add_relation():
    """
    Add an explicit user relation between two artifacts.

    Relations are:
    - Directional (from → to)
    - Globally visible within tenant (subject to RBAC)
    - Immediately active
    - Permanently flagged as user-added
    """
    # TODO: Implement in Phase 4
    raise HTTPException(status_code=501, detail="Not implemented - Phase 4")


@router.post("/{context_id}/end")
async def end_context():
    """
    End the navigation context when user returns to search bar home.

    This archives the context for audit and destroys the navigation stack.
    """
    # TODO: Implement in Phase 4
    raise HTTPException(status_code=501, detail="Not implemented - Phase 4")


# Note: This router will be registered in pipeline_service.py as:
# app.include_router(context_navigation_routes.router, prefix="/api/context", tags=["context-nav"])
