"""
Context Navigation Routes

API endpoints for situational continuity layer.
Handles navigation context lifecycle, related expansion, and user relations.
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from uuid import UUID
import logging
import os
from supabase import create_client, Client

from context_nav.schemas import (
    NavigationContextCreate,
    NavigationContext,
    RelatedRequest,
    RelatedResponse,
    AddRelatedRequest,
    AddRelatedResponse,
)
from handlers.context_navigation_handlers import (
    create_navigation_context,
    update_active_anchor,
    get_related,
    add_user_relation,
    end_navigation_context,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# SUPABASE CLIENT
# ============================================================================

def get_supabase_client() -> Client:
    """Get TENANT Supabase client for yacht context navigation.

    Uses DEFAULT_YACHT_CODE env var to route to correct tenant DB.
    """
    default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")

    url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise HTTPException(status_code=500, detail=f"TENANT Supabase config missing for {default_yacht}")

    return create_client(url, key)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/create", response_model=NavigationContext)
async def create_context(
    data: NavigationContextCreate,
    authorization: Optional[str] = Header(None)
):
    """
    Create a new navigation context when user opens an artifact from search.

    This is the entry point for situational continuity.

    Behavior:
    1. Insert navigation_contexts row
    2. Insert ledger_events row: artefact_opened
    3. Return context (per schema)
    """
    try:
        supabase = get_supabase_client()
        context = create_navigation_context(supabase, data)
        return context

    except Exception as e:
        logger.error(f"Failed to create context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{context_id}/update-anchor", response_model=NavigationContext)
async def update_anchor(
    context_id: UUID,
    anchor_type: str,
    anchor_id: UUID,
    yacht_id: UUID,
    user_id: UUID,
    authorization: Optional[str] = Header(None)
):
    """
    Update the active anchor when user navigates to a different artifact.

    This does NOT create a new context - it replaces the anchor within the same context.

    Behavior:
    1. Update navigation_contexts.active_anchor_type/id
    2. Insert ledger_events: artefact_opened
    3. Return updated context (per schema)
    """
    try:
        supabase = get_supabase_client()
        context = update_active_anchor(
            supabase, context_id, yacht_id, user_id, anchor_type, anchor_id
        )
        return context

    except Exception as e:
        logger.error(f"Failed to update anchor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/related", response_model=RelatedResponse)
async def get_related_artifacts(
    data: RelatedRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Get related artifacts for the current anchor (deterministic expansion only).

    CRITICAL: NO vector search, NO LLMs, NO ranking.
    Only JOIN/FK-based queries and user-added relations.

    Behavior:
    - Validate tenant + user auth
    - For each domain: run FK/JOIN query only
    - Union user_added_relations scoped by tenant
    - Order deterministic (created_at DESC)
    - Limit 20 items per domain
    - If domain fails: omit domain silently (do not error)
    - Return groups in FIXED domain order

    CRITICAL: NO audit event for viewing related (not in spec)
    """
    try:
        supabase = get_supabase_client()
        response = get_related(supabase, data)
        return response

    except Exception as e:
        logger.error(f"Failed to get related artifacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-relation", response_model=AddRelatedResponse)
async def add_relation(
    data: AddRelatedRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Add an explicit user relation between two artifacts.

    Relations are:
    - Directional (from → to)
    - Globally visible within tenant (subject to RBAC)
    - Immediately active
    - Permanently flagged as user-added

    Behavior:
    1. Insert user_added_relations (immediate active, source=user)
    2. Attribute created_by_user_id
    3. Insert ledger_events: relation_added
    4. Return created relation (per schema)
    """
    try:
        supabase = get_supabase_client()
        response = add_user_relation(supabase, data)
        return response

    except Exception as e:
        logger.error(f"Failed to add relation: {e}")
        # Check if it's a duplicate relation error
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=409, detail="Relation already exists")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{context_id}/end")
async def end_context(
    context_id: UUID,
    yacht_id: UUID,
    user_id: UUID,
    authorization: Optional[str] = Header(None)
):
    """
    End the navigation context when user returns to search bar home.

    This archives the context for audit and destroys the navigation stack.

    Behavior:
    1. Set navigation_contexts.ended_at = now()
    2. Insert ledger_events: situation_ended
    3. Return success
    """
    try:
        supabase = get_supabase_client()
        result = end_navigation_context(supabase, context_id, yacht_id, user_id)
        return result

    except Exception as e:
        logger.error(f"Failed to end context: {e}")
        raise HTTPException(status_code=500, detail=str(e))
