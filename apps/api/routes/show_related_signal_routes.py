#!/usr/bin/env python3
"""
Show Related Signal Routes
===========================

Standalone signal-based discovery endpoint. Runs in parallel to the
FK-based /v1/related endpoint — validate signal quality here before
merging into the main related panel.

Endpoint:
    GET /v1/show-related-signal
        ?entity_type=work_order
        &entity_id=<uuid>
        [&limit=10]

No writes. No state changes. Read-only probe.

Auth: JWT required (yacht_id extracted server-side, never from client).
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status

from middleware.auth import get_authenticated_user
from services.hyper_search import get_db_pool
from services.types import UserContext
from handlers.show_related_signal_handlers import get_signal_related, get_signal_related_supabase
from integrations.supabase import get_tenant_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/show-related-signal", tags=["show-related-signal"])

# Derived from entity_serializer._SERIALIZERS — never hardcode this list.
# Adding a new entity type: add it to entity_serializer.py only. This gate
# automatically stays in sync.
from services.entity_serializer import SUPPORTED_ENTITY_TYPES as _SUPPORTED
VALID_ENTITY_TYPES = sorted(_SUPPORTED)


def _build_user_context(auth: dict) -> UserContext:
    """Build UserContext from JWT auth payload. Raises 403 if org_id missing."""
    user_id = auth.get("user_id")
    org_id = auth.get("org_id") or auth.get("yacht_id")
    yacht_id = auth.get("yacht_id")
    role = auth.get("role", "crew")

    if not user_id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Missing user_id in auth context",
        )
    if not org_id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Missing org_id — RLS enforcement requires org scope",
        )

    return UserContext(
        user_id=str(user_id),
        org_id=str(org_id),
        yacht_id=str(yacht_id) if yacht_id else None,
        role=role,
        locale=auth.get("locale"),
    )


@router.get("/")
async def view_signal_related(
    entity_type: str = Query(..., description="Entity type (e.g. 'work_order', 'fault')"),
    entity_id: UUID = Query(..., description="Entity UUID"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results (1–50)"),
    auth: dict = Depends(get_authenticated_user),
):
    """
    Discover semantically related entities using the spotlight pipeline.

    Serializes the entity's attributes into text, generates an embedding,
    and runs f1_search_cards — the same RPC used by the spotlight search bar.

    This is the signal layer running standalone, before it is merged into
    the main /v1/related response. Use it to validate signal quality.

    Response:
    {
      "status": "success",
      "entity_type": "work_order",
      "entity_id": "...",
      "entity_text": "Replace fuel filters; equipment: main engine; status: open",
      "items": [
        {
          "entity_id": "...",
          "entity_type": "manual",
          "title": "C18 Engine Manual",
          "subtitle": "manual",
          "match_reasons": ["signal:entity_embedding"],
          "fused_score": 0.72,
          "weight": 50
        }
      ],
      "count": 4,
      "signal_source": "entity_embedding",
      "metadata": { "limit": 10, "embedding_generated": true }
    }
    """
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type. Must be one of: {', '.join(VALID_ENTITY_TYPES)}",
        )

    ctx = _build_user_context(auth)

    # Preferred path: asyncpg (direct PostgreSQL) — requires READ_DB_DSN / DATABASE_URL.
    # Fallback path: Supabase HTTP client — works in all environments with tenant credentials.
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await get_signal_related(
                entity_type=entity_type,
                entity_id=str(entity_id),
                conn=conn,
                ctx=ctx,
                limit=limit,
            )
        return result

    except HTTPException:
        raise

    except ValueError as e:
        # READ_DB_DSN not configured — fall back to Supabase HTTP client
        if "not configured" in str(e):
            logger.info("[SignalRelated] No READ_DB_DSN — using Supabase RPC fallback")
        else:
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        # Timeout, connection error, or other transient failure — try Supabase fallback
        logger.warning(f"[SignalRelated] asyncpg failed ({type(e).__name__}: {e}), falling back to Supabase")

    # Supabase text-only fallback (reached on missing DSN OR asyncpg failure)
    try:
        supabase = get_tenant_client(auth.get("tenant_key_alias", ""))
        result = await get_signal_related_supabase(
            entity_type=entity_type,
            entity_id=str(entity_id),
            supabase=supabase,
            ctx=ctx,
            limit=limit,
        )
        return result
    except HTTPException:
        raise
    except Exception as e2:
        logger.error(f"[SignalRelated/Supabase] Fallback also failed: {e2}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e2))


@router.get("/debug/status")
async def signal_related_status():
    """
    Health check — no auth required.
    Confirms the signal routes are registered and services importable.
    """
    return {
        "status": "ok",
        "endpoint": "GET /v1/show-related-signal",
        "signal_source": "entity_embedding",
        "rpc": "f1_search_cards",
        "supported_entity_types": VALID_ENTITY_TYPES,
    }
