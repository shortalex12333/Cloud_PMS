#!/usr/bin/env python3
"""
Show Related — Signal Discovery Handlers
=========================================

Standalone signal-based discovery layer. Parallel to the FK-based
related_handlers.py — runs independently so signal quality can be
validated before the two systems are merged.

How it works:
    entity (type + id)
        → entity_serializer  : "ABC Engine Manual; doc_type: manual; equipment: C18"
        → generate_embeddings: 1536-d vector (same model as spotlight)
        → call_hyper_search  : f1_search_cards RPC (same as spotlight search)
        → exclude self       : filter source entity from results
        → map + return       : items in RelatedItem shape

Two execution paths:
  1. asyncpg path (preferred): direct PostgreSQL via READ_DB_DSN
  2. Supabase path (fallback):  Supabase HTTP client via tenant credentials

Endpoint: GET /v1/show-related-signal?entity_type=...&entity_id=...

Consumed by: routes/show_related_signal_routes.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

import asyncpg
from fastapi import HTTPException

from cortex.rewrites import Rewrite, generate_embeddings
from services.entity_serializer import serialize_entity
from services.hyper_search import call_hyper_search
from services.types import UserContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment config
# ---------------------------------------------------------------------------

_SIGNAL_LIMIT = int(os.getenv("SHOW_RELATED_SIGNAL_LIMIT", "10"))


# ---------------------------------------------------------------------------
# Public handler — asyncpg path (preferred, requires READ_DB_DSN)
# ---------------------------------------------------------------------------

async def get_signal_related(
    entity_type: str,
    entity_id: str,
    conn: asyncpg.Connection,
    ctx: UserContext,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Discover semantically related entities using the spotlight pipeline.
    Uses asyncpg (direct PostgreSQL) for maximum performance.

    Returns:
    {
      "status": "success",
      "entity_type": "work_order",
      "entity_id": "...",
      "entity_text": "...",          # serialized text that was embedded
      "items": [...],                # RelatedItem list
      "count": 4,
      "signal_source": "entity_embedding",
      "metadata": { "limit": 10, "embedding_generated": true }
    }
    """
    effective_limit = limit if limit is not None else _SIGNAL_LIMIT

    # Guard: yacht_id is required — f1_search_cards scopes results per vessel.
    # NULL yacht_id would return results across ALL vessels in the org (data leak).
    if not ctx.yacht_id:
        raise HTTPException(
            status_code=403,
            detail="yacht_id required for signal search — cannot scope results to vessel",
        )

    # 1. Serialize entity to text
    entity_text = await serialize_entity(entity_type, entity_id, conn, ctx.yacht_id)
    if not entity_text:
        raise HTTPException(
            status_code=404,
            detail=f"{entity_type} '{entity_id}' not found or not serializable",
        )

    # 2. Generate embedding (same model as spotlight: text-embedding-3-small)
    # 3000ms budget: signal search is not on the hot path — panel opens on demand.
    # 800ms was too tight for cold-start OpenAI connections; 3000ms matches DB statement_timeout.
    rewrite = Rewrite(text=entity_text, source="entity_signal", confidence=1.0)
    rewrites = await generate_embeddings([rewrite], budget_ms=8000, org_id=ctx.org_id)
    embedding_generated = any(r.embedding is not None for r in rewrites)

    # 3. Call f1_search_cards — identical RPC call to spotlight search
    try:
        raw_results = await call_hyper_search(
            conn=conn,
            rewrites=rewrites,
            ctx=ctx,
            page_limit=effective_limit,
            exclude_ids=[entity_id],  # never return the source entity itself
        )
    except Exception as e:
        logger.error(f"[SignalRelated] call_hyper_search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Signal search failed")

    # 4. Map to RelatedItem shape — dedup by entity_id (search_index can have
    # multiple rows per entity when the projector creates partial updates).
    seen_ids: set = set()
    items = []
    for r in raw_results:
        item = _map_to_related_item(r)
        if item["entity_id"] not in seen_ids:
            seen_ids.add(item["entity_id"])
            items.append(item)

    logger.info(
        f"[SignalRelated] {entity_type}/{entity_id[:8]}... → "
        f"{len(items)} items (embedding={embedding_generated})"
    )

    return {
        "status": "success",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_text": entity_text,
        "items": items,
        "count": len(items),
        "signal_source": "entity_embedding",
        "metadata": {
            "limit": effective_limit,
            "embedding_generated": embedding_generated,
        },
    }


# ---------------------------------------------------------------------------
# Public handler — Supabase HTTP client fallback (no READ_DB_DSN required)
# ---------------------------------------------------------------------------

async def get_signal_related_supabase(
    entity_type: str,
    entity_id: str,
    supabase,
    ctx: UserContext,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Supabase HTTP client version of get_signal_related.

    Used when READ_DB_DSN / DATABASE_URL is not configured (e.g. local test
    containers without direct PostgreSQL access). Calls f1_search_cards via
    Supabase RPC. Embeddings still generated via OpenAI when available.
    """
    effective_limit = limit if limit is not None else _SIGNAL_LIMIT

    if not ctx.yacht_id:
        raise HTTPException(
            status_code=403,
            detail="yacht_id required for signal search — cannot scope results to vessel",
        )

    # 1. Serialize entity using Supabase HTTP client.
    # asyncio.to_thread() prevents synchronous table queries from blocking the event loop.
    entity_text = await asyncio.to_thread(
        _serialize_entity_supabase_sync, entity_type, entity_id, supabase, ctx.yacht_id or ""
    )
    if not entity_text:
        raise HTTPException(
            status_code=404,
            detail=f"{entity_type} '{entity_id}' not found or not serializable",
        )

    # 2. Generate embedding
    rewrite = Rewrite(text=entity_text, source="entity_signal", confidence=1.0)
    rewrites = await generate_embeddings([rewrite], budget_ms=8000, org_id=ctx.org_id)
    embedding_generated = any(r.embedding is not None for r in rewrites)

    # 3. Call f1_search_cards via Supabase RPC.
    # asyncio.to_thread() prevents the synchronous httpx call from blocking the event loop.
    try:
        raw_results = await asyncio.to_thread(
            _call_hyper_search_supabase,
            supabase,
            rewrites,
            ctx,
            effective_limit,
            [entity_id],
        )
    except Exception as e:
        logger.error(f"[SignalRelated/Supabase] hyper_search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Signal search failed")

    # 4. Map to RelatedItem shape — dedup by entity_id
    seen_ids_s: set = set()
    items = []
    for r in raw_results:
        item = _map_to_related_item(r)
        if item["entity_id"] not in seen_ids_s:
            seen_ids_s.add(item["entity_id"])
            items.append(item)

    logger.info(
        f"[SignalRelated/Supabase] {entity_type}/{entity_id[:8]}... → "
        f"{len(items)} items (embedding={embedding_generated})"
    )

    return {
        "status": "success",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_text": entity_text,
        "items": items,
        "count": len(items),
        "signal_source": "entity_embedding",
        "metadata": {
            "limit": effective_limit,
            "embedding_generated": embedding_generated,
            "backend": "supabase_rpc",
            "search_mode": "text",  # REST path uses text-only (no pgvector timeout)
        },
    }


# ---------------------------------------------------------------------------
# Supabase entity serializer
# ---------------------------------------------------------------------------

def _serialize_entity_supabase_sync(
    entity_type: str,
    entity_id: str,
    supabase,
    yacht_id: str,
) -> Optional[str]:
    """
    Serialize entity attributes to text using Supabase HTTP client.
    Mirrors entity_serializer.py but uses supabase.table().select() calls.
    Returns None if entity not found or type unknown.

    IMPORTANT: Synchronous — run via asyncio.to_thread() from async context.
    """
    try:
        if entity_type == "work_order":
            r = supabase.table("pms_work_orders").select(
                "title, description, status, priority, equipment_id"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            eq_name = None
            if row.get("equipment_id"):
                er = supabase.table("pms_equipment").select("name").eq(
                    "id", row["equipment_id"]
                ).maybe_single().execute()
                eq_name = er.data.get("name") if er.data else None
            parts = [row["title"]] if row.get("title") else []
            if eq_name:
                parts.append(f"equipment: {eq_name}")
            if row.get("status"):
                parts.append(f"status: {row['status']}")
            if row.get("priority"):
                parts.append(f"priority: {row['priority']}")
            desc = (row.get("description") or "").strip()
            if desc and desc != (row.get("title") or "").strip():
                parts.append(desc[:200])
            return "; ".join(parts) if parts else None

        elif entity_type == "fault":
            r = supabase.table("pms_faults").select(
                "title, description, severity, equipment_id"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            eq_name = None
            if row.get("equipment_id"):
                er = supabase.table("pms_equipment").select("name").eq(
                    "id", row["equipment_id"]
                ).maybe_single().execute()
                eq_name = er.data.get("name") if er.data else None
            parts = [row["title"]] if row.get("title") else []
            if eq_name:
                parts.append(f"equipment: {eq_name}")
            if row.get("severity"):
                parts.append(f"severity: {row['severity']}")
            # Only append description if it adds new information (not a repeat of title)
            desc = row.get("description") or ""
            if desc and desc.strip() != (row.get("title") or "").strip():
                parts.append(desc[:200])
            return "; ".join(parts) if parts else None

        elif entity_type == "equipment":
            # pms_equipment has system_type + criticality, NOT category
            r = supabase.table("pms_equipment").select(
                "name, manufacturer, model, system_type, location, criticality"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            parts = [row["name"]] if row.get("name") else []
            if row.get("manufacturer"):
                parts.append(f"manufacturer: {row['manufacturer']}")
            if row.get("model"):
                parts.append(f"model: {row['model']}")
            if row.get("system_type"):
                parts.append(f"system_type: {row['system_type']}")
            if row.get("location"):
                parts.append(f"location: {row['location']}")
            if row.get("criticality"):
                parts.append(f"criticality: {row['criticality']}")
            return "; ".join(parts) if parts else None

        elif entity_type in ("part", "inventory"):
            r = supabase.table("pms_parts").select(
                "name, part_number, category, manufacturer"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            parts = [row["name"]] if row.get("name") else []
            if row.get("part_number"):
                parts.append(f"part_number: {row['part_number']}")
            if row.get("category"):
                parts.append(f"category: {row['category']}")
            if row.get("manufacturer"):
                parts.append(f"manufacturer: {row['manufacturer']}")
            return "; ".join(parts) if parts else None

        elif entity_type in ("manual", "document"):
            r = supabase.table("doc_metadata").select(
                "filename, doc_type, equipment_ids"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            parts = [row["filename"]] if row.get("filename") else []
            if row.get("doc_type"):
                parts.append(f"doc_type: {row['doc_type']}")
            eq_ids = row.get("equipment_ids") or []
            if eq_ids:
                er = supabase.table("pms_equipment").select("name").in_(
                    "id", eq_ids
                ).execute()
                eq_names = [e["name"] for e in (er.data or []) if e.get("name")]
                if eq_names:
                    parts.append(f"equipment: {', '.join(eq_names)}")
            return "; ".join(parts) if parts else None

        elif entity_type == "handover":
            r = supabase.table("pms_handovers").select(
                "title, content"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if not r.data:
                return None
            row = r.data
            parts = [row["title"]] if row.get("title") else []
            if row.get("content"):
                parts.append(row["content"][:300])
            return "; ".join(parts) if parts else None

        else:
            return None

    except Exception as e:
        logger.error(f"[EntitySerializer/Supabase] {entity_type}/{entity_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Supabase f1_search_cards wrapper
# ---------------------------------------------------------------------------

def _call_hyper_search_supabase(
    supabase,
    rewrites: List[Dict],
    ctx: UserContext,
    page_limit: int = 20,
    exclude_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Call f1_search_cards via Supabase RPC (synchronous Supabase client).
    When embeddings are available, passes them as pgvector text literals.
    Falls back to text/trigram search only when no embedding is generated.

    IMPORTANT: Run this via asyncio.to_thread() — it is synchronous and will
    block the event loop if called directly from an async context.
    """
    # Patch postgrest client timeout to 30s — f1_search_cards with pgvector
    # embeddings can take 10-15s on cold start; default 5s is too short.
    try:
        import httpx
        supabase.postgrest.session.timeout = httpx.Timeout(30.0)
    except Exception:
        pass  # Best-effort; proceed with whatever timeout is configured

    rewrites = rewrites[:3]
    texts = [r.text for r in rewrites]

    # Supabase REST path always uses text-only search (embeddings=None).
    # Reason: f1_search_cards with pgvector ANN scan triggers statement_timeout
    # on the Supabase REST/PostgREST path — we can't SET statement_timeout
    # per-request through REST the way asyncpg can.
    # Text/trigram search is fast (<500ms) and produces good results from the
    # rich entity text. The asyncpg path (READ_DB_DSN) handles vector search.
    embeddings = None  # NULL → pg_trgm text search only (REST-safe)

    original_query = texts[0] if texts else ""
    trgm_limit = 0.07 if len(original_query.strip()) <= 6 else 0.15

    result = supabase.rpc("f1_search_cards", {
        "p_texts": texts,
        "p_embeddings": embeddings,
        "p_org_id": ctx.org_id,
        "p_yacht_id": ctx.yacht_id,
        "p_rrf_k": 60,
        "p_page_limit": page_limit,
        "p_trgm_limit": trgm_limit,
        "p_object_types": None,
    }).execute()

    rows = result.data or []

    # Post-RPC exclusion (remove source entity from its own results)
    if exclude_ids:
        exclude_set = set(str(i) for i in exclude_ids)
        rows = [r for r in rows if str(r.get("object_id", "")) not in exclude_set]

    return rows


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _map_to_related_item(result: Dict[str, Any]) -> Dict[str, Any]:
    """Map a raw f1_search_cards row to the RelatedItem shape.

    Title/subtitle extraction uses actual search_index payload keys discovered
    by live inspection. Key finding: work_order uses 'label' (pre-formatted
    "WO-NNNN: Title"), not 'title'. Other types use 'name' or 'title'.
    """
    payload = result.get("payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}

    object_type = result.get("object_type", "unknown")

    # Type-aware title extraction — keys verified against live search_index payload inspection.
    # Canonical payload schemas:
    #   work_order:    {label, status, equipment_id}
    #   equipment:     {name, status, source_table} or {code, name, status, location, manufacturer}
    #   part:          {name, category, location, part_number, manufacturer}
    #   shopping_item: {status, quantity, part_name, source_table}
    #   document:      {url, size, title, doc_type, source_table}
    #   email:         {folder, subject, received_at, preview_text}
    if object_type == "work_order":
        # 'label' = "WO-NNNN: Title" (pre-formatted by search_index projector)
        title = payload.get("label") or payload.get("title") or payload.get("name")
        subtitle = payload.get("status") or ""
    elif object_type == "equipment":
        title = payload.get("name") or payload.get("equipment_name")
        subtitle = payload.get("location") or payload.get("category") or payload.get("status") or ""
    elif object_type in ("part", "inventory"):
        title = payload.get("name") or payload.get("item_name")
        subtitle = payload.get("part_number") or payload.get("sku") or payload.get("category") or ""
    elif object_type == "shopping_item":
        title = payload.get("part_name") or payload.get("name")
        subtitle = payload.get("status") or ""
    elif object_type == "email":
        title = payload.get("subject") or payload.get("name")
        subtitle = payload.get("folder") or ""
    elif object_type == "fault":
        title = payload.get("title") or payload.get("label") or payload.get("name")
        subtitle = payload.get("severity") or payload.get("priority") or payload.get("status") or ""
    elif object_type in ("document", "manual", "certificate"):
        # search_index payload uses 'title' for documents (filename stored here)
        title = payload.get("title") or payload.get("name")
        subtitle = payload.get("doc_type") or payload.get("type") or payload.get("category") or ""
    elif object_type == "handover":
        title = payload.get("title") or payload.get("label") or payload.get("name")
        subtitle = payload.get("status") or ""
    else:
        # Generic: try all common fields in priority order
        title = (
            payload.get("label")
            or payload.get("title")
            or payload.get("subject")
            or payload.get("name")
            or payload.get("part_name")
        )
        subtitle = payload.get("status") or payload.get("code") or ""

    # Final fallback: use object_id prefix — never show "Related item"
    if not title:
        obj_id = str(result.get("object_id", ""))
        title = f"{object_type} {obj_id[:8]}…" if obj_id else "Related item"

    return {
        "entity_id": str(result.get("object_id", "")),
        "entity_type": object_type,
        "title": title,
        "subtitle": subtitle[:100] if subtitle else "",
        "match_reasons": ["signal:entity_embedding"],
        "fused_score": result.get("fused_score", 0.0),
        "weight": 50,
        "open_action": "focus",
    }


__all__ = ["get_signal_related", "get_signal_related_supabase"]
