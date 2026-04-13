"""
Ledger API Routes

Provides endpoints for fetching ledger events from the tenant database.
Frontend (Vercel) calls these endpoints since it only has access to Master DB.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import Optional, List
from datetime import datetime, date
from pathlib import Path
import logging
import hashlib
import hmac as _hmac
import json
import os
from uuid import uuid4
from pydantic import BaseModel

from middleware.auth import get_authenticated_user
from middleware.vessel_access import resolve_yacht_id

logger = logging.getLogger(__name__)


def _get_tenant_client(tenant_key_alias: str):
    """Get tenant-specific Supabase client."""
    from integrations.supabase import get_tenant_client
    return get_tenant_client(tenant_key_alias)

router = APIRouter(prefix="/v1/ledger", tags=["ledger"])


@router.get("/events")
async def get_ledger_events(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: Optional[str] = Query(default=None, description="Filter by specific user_id (for 'Me' view)"),
    action: Optional[str] = Query(default=None, description="Filter by action: add_note, artefact_opened, etc."),
    date_from: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    yacht_id: Optional[str] = Query(default=None, alias="yacht_id", description="Vessel scope (fleet users)"),
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Fetch ledger events for the current user's yacht.
    Returns events in reverse chronological order.
    - If user_id is provided, filters to only that user's events (Me view)
    - If user_id is not provided, returns all yacht events (Department view)
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        yacht_id = resolve_yacht_id(user_context, yacht_id)

        db_client = _get_tenant_client(tenant_alias)

        # Build query
        query = db_client.table("ledger_events").select("*")

        # Filter by yacht (RLS should handle this, but be explicit)
        query = query.eq("yacht_id", yacht_id)

        # Filter by user_id if provided (Me view)
        if user_id:
            query = query.eq("user_id", user_id)

        # Filter by action if provided
        if action:
            query = query.eq("action", action)

        if date_from:
            query = query.gte("created_at", f"{date_from}T00:00:00Z")

        if date_to:
            query = query.lte("created_at", f"{date_to}T23:59:59Z")

        # Order and paginate (use created_at since that's the actual column)
        query = query.order("created_at", desc=True)
        query = query.range(offset, offset + limit - 1)

        result = query.execute()

        return {
            "success": True,
            "events": result.data or [],
            "count": len(result.data or []),
            "offset": offset,
            "limit": limit,
            "has_more": len(result.data or []) == limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch ledger events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch ledger events: {str(e)}")


@router.get("/events/by-entity/{entity_type}/{entity_id}")
async def get_entity_ledger_events(
    entity_type: str,
    entity_id: str,
    limit: int = Query(default=50, le=100),
    yacht_id: Optional[str] = Query(default=None, description="Vessel scope (fleet users)"),
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Fetch ledger events for a specific entity.
    Useful for showing history on entity detail pages.
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        yacht_id = resolve_yacht_id(user_context, yacht_id)

        db_client = _get_tenant_client(tenant_alias)

        result = db_client.table("ledger_events").select("*").eq(
            "yacht_id", yacht_id
        ).eq(
            "entity_type", entity_type
        ).eq(
            "entity_id", entity_id
        ).order(
            "created_at", desc=True
        ).limit(limit).execute()

        return {
            "success": True,
            "events": result.data or [],
            "entity_type": entity_type,
            "entity_id": entity_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch entity ledger events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch entity ledger events: {str(e)}")


@router.get("/day-anchors")
async def get_day_anchors(
    days: int = Query(default=30, le=90, description="Number of days to fetch"),
    yacht_id: Optional[str] = Query(default=None, description="Vessel scope (fleet users)"),
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Fetch day anchor summaries for the ledger UI.
    Shows mutation/read counts per day.
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        yacht_id = resolve_yacht_id(user_context, yacht_id)

        db_client = _get_tenant_client(tenant_alias)

        # Get day anchors
        result = db_client.table("ledger_day_anchors").select("*").eq(
            "yacht_id", yacht_id
        ).order(
            "anchor_date", desc=True
        ).limit(days).execute()

        return {
            "success": True,
            "anchors": result.data or [],
            "days_requested": days
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch day anchors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch day anchors: {str(e)}")


@router.post("/record")
async def record_ledger_event(
    event_data: dict,
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Record a ledger event from the frontend.
    Used for tracking read events like artefact_opened.

    Required fields:
    - action: The action being performed (e.g., artefact_opened)
    - entity_type: Type of entity (e.g., work_order, fault)
    - entity_id: UUID of the entity

    Optional:
    - metadata: Additional context data
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        # Accept yacht_id from event payload for fleet users, validate against vessel_ids
        requested_yacht_id = event_data.get("yacht_id")
        yacht_id = resolve_yacht_id(user_context, requested_yacht_id)
        user_id = user_context.get("user_id")

        if not yacht_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing yacht_id or user_id in context")

        # Support both old (event_name) and new (action) field names for backwards compatibility
        action_name = event_data.get("action") or event_data.get("event_name")
        entity_type = event_data.get("entity_type") or event_data.get("payload", {}).get("artefact_type", "unknown")
        entity_id = event_data.get("entity_id") or event_data.get("payload", {}).get("artefact_id")
        metadata = event_data.get("metadata") or event_data.get("payload", {})

        if not action_name:
            raise HTTPException(status_code=400, detail="action or event_name is required")

        if not entity_id:
            raise HTTPException(status_code=400, detail="entity_id is required")

        db_client = _get_tenant_client(tenant_alias)

        # Map action to event_type (read events map to specific types)
        event_type_map = {
            "artefact_opened": "update",  # Read events are tracked as updates
            "situation_ended": "status_change",
            "view": "update",
            "open": "update",
        }
        event_type = event_type_map.get(action_name, "update")

        # Generate proof_hash
        hash_input = json.dumps({
            "yacht_id": str(yacht_id),
            "user_id": str(user_id),
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "action": action_name,
            "timestamp": datetime.utcnow().isoformat()
        }, sort_keys=True)
        proof_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        # Build ledger event using correct schema
        ledger_event = {
            "yacht_id": str(yacht_id),
            "user_id": str(user_id),
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "action": action_name,
            "user_role": user_context.get("role", "member"),
            "source_context": "microaction",  # Frontend read beacons
            "metadata": {
                **metadata,
                "user_role": user_context.get("role", "member"),
            },
            "proof_hash": proof_hash
        }

        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
            logger.info(f"[Ledger] Recorded {action_name} for user {user_id}")
        except Exception as insert_err:
            if "204" in str(insert_err):
                logger.info(f"[Ledger] {action_name} recorded (204)")
            else:
                logger.warning(f"[Ledger] Failed to record {action_name}: {insert_err}")
                raise

        return {"success": True, "message": f"Event {action_name} recorded"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record ledger event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record ledger event: {str(e)}")


@router.post("/read-event")
async def record_read_event(
    request: Request,
    user_context: dict = Depends(get_authenticated_user),
):
    """
    Frontend beacon: called fire-and-forget when a user opens an entity page or document.
    Writes event_category='read' to ledger_events. Never blocks the caller.
    """
    body = await request.json()
    entity_type = body.get("entity_type", "unknown")
    entity_id   = body.get("entity_id", "")
    entity_name = body.get("entity_name", "")
    metadata    = body.get("metadata", {})

    yacht_id      = resolve_yacht_id(user_context, body.get("yacht_id"))
    user_id       = user_context.get("user_id") or user_context.get("sub")
    user_role     = user_context.get("role", "")
    actor_name    = user_context.get("email", "")
    department    = user_context.get("department", "")
    tenant_alias  = user_context.get("tenant_key_alias", "")

    if not yacht_id or not entity_id:
        return {"success": False, "error": "yacht_id and entity_id required"}

    try:
        now_iso = datetime.utcnow().isoformat()
        change_summary = (
            f"Opened: {entity_name}" if entity_name
            else f"Opened {entity_type.replace('_', ' ')}"
        )
        ev = {
            "yacht_id":       str(yacht_id),
            "user_id":        str(user_id),
            "user_role":      user_role,
            "actor_name":     actor_name,
            "department":     department,
            "event_category": "read",
            "event_type":     "update",
            "action":         f"view_{entity_type}",
            "entity_type":    entity_type,
            "entity_id":      str(entity_id),
            "change_summary": change_summary,
            "source_context": "microaction",
            "metadata":       metadata,
            "proof_hash":     hashlib.sha256(
                (f"{yacht_id}{user_id}view{entity_type}{entity_id}{now_iso}").encode()
            ).hexdigest(),
        }
        if entity_name:
            ev["entity_name"] = entity_name
        db_client = _get_tenant_client(tenant_alias)
        db_client.table("ledger_events").insert(ev).execute()
        return {"success": True}
    except Exception as e:
        logger.warning(f"[Ledger] Read beacon failed: {e}")
        return {"success": False}


@router.get("/timeline")
async def get_ledger_timeline(
    limit: int = 50,
    offset: int = 0,
    event_category: Optional[str] = None,
    yacht_id: Optional[str] = Query(default=None, description="Vessel scope (fleet users)"),
    user_context: dict = Depends(get_authenticated_user),
):
    """
    Three-tier role-scoped timeline:
      captain             -> all events on this yacht (master of vessel)
      chief_engineer      -> engineering department events (chief_engineer + eto)
      manager             -> interior department events (manager + interior)
      all other roles     -> own events only
    """
    _DEPT_MEMBER_ROLES: dict = {
        "engineering": ["chief_engineer", "eto"],
        "interior":    ["manager", "interior"],
    }

    tenant_alias = user_context.get("tenant_key_alias", "")
    yacht_id     = resolve_yacht_id(user_context, yacht_id)
    user_id      = user_context.get("user_id") or user_context.get("sub")
    user_role    = user_context.get("role", "")
    department   = user_context.get("department", "")

    db_client = _get_tenant_client(tenant_alias)

    query = db_client.table("ledger_events") \
        .select("id, action, entity_type, entity_id, event_category, event_type, "
                "change_summary, user_role, actor_name, department, metadata, created_at") \
        .eq("yacht_id", str(yacht_id))

    if user_role == "captain":
        # Captain sees all yacht events — no further filter
        pass
    elif user_role in ("chief_engineer", "manager"):
        # HoD sees their department only — filter by the roles in that department
        dept_roles = _DEPT_MEMBER_ROLES.get(department, [])
        if dept_roles:
            query = query.in_("user_role", dept_roles)
        else:
            # Fallback: department unknown, show self only
            query = query.eq("user_id", str(user_id))
    else:
        # All other roles: self only
        query = query.eq("user_id", str(user_id))

    if event_category:
        query = query.eq("event_category", event_category)

    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"success": True, "events": result.data, "total": len(result.data)}


# ── Export helpers ─────────────────────────────────────────────────────────────

# Fields stripped from embedded JSON before export.
# Rationale for each:
#   user_id, yacht_id, entity_id  — replaced by HMAC refs (actor_ref, vessel_ref, entity_ref)
#   id                            — raw event UUID; no tenant/user info but zero reason to expose
#   session_id                    — internal session correlation, not evidence-relevant
#   day_anchor_id                 — internal chain anchor FK, not evidence-relevant
#   related_event_ids             — internal cross-reference UUIDs; if populated would leak event IDs
_STRIP_FIELDS = frozenset({
    "user_id", "yacht_id", "entity_id",
    "id", "session_id", "day_anchor_id", "related_event_ids",
})


def _mask_export_id(raw_id: str, secret: str) -> str:
    """HMAC-SHA256 mask for external-facing export identifiers.

    Unlike plain SHA-256, requires knowing EXPORT_HMAC_SECRET to reproduce.
    An attacker who obtains raw UUIDs cannot verify they match refs in an
    exported PDF without the server-side key.
    """
    return _hmac.new(
        secret.encode("utf-8"),
        str(raw_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _build_ledger_pdf(
    events: list,
    export_id: str,
    vessel_name: str,
    date_from: str,
    date_to: str,
    requester_name: str,
    scope_label: str,
    export_secret: str,
) -> bytes:
    """
    Build a PDF with embedded ledger_events.json attachment (PyMuPDF stage).

    IDs masked with HMAC-SHA256 before embedding:
      user_id   → actor_ref   (replaces, stripped from output)
      yacht_id  → vessel_ref  (replaces, stripped from output)
      entity_id → entity_ref  (replaces, stripped from output)

    Additionally stripped: id, session_id, day_anchor_id, related_event_ids
    See _STRIP_FIELDS for documented rationale.

    The cover page carries human-readable actor_name/email by design —
    evidence without attribution is worthless. The export preview UI
    must tell the operator this before they confirm.
    """
    import fitz  # PyMuPDF — imported here to keep workers from loading it

    # ── Mask and strip ──
    masked_events = []
    for e in events:
        masked = {k: v for k, v in e.items() if k not in _STRIP_FIELDS}
        masked["actor_ref"]  = _mask_export_id(e.get("user_id",   ""), export_secret)
        masked["vessel_ref"] = _mask_export_id(e.get("yacht_id",  ""), export_secret)
        masked["entity_ref"] = _mask_export_id(e.get("entity_id", ""), export_secret)
        masked["event_timestamp"] = masked.pop("created_at", None) or masked.get("event_timestamp")
        masked_events.append(masked)

    # Chronological order for JSON (verifier checks this)
    masked_events.sort(key=lambda e: e.get("event_timestamp") or "")
    json_bytes = json.dumps(masked_events, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")

    # ── Cover page ──
    _FONT_DIR = Path(__file__).parent.parent / "evidence" / "fonts"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Embed Inter — required for PDF/A-3 (Helvetica is never embedded)
    page.insert_font(fontname="Inter",     fontfile=str(_FONT_DIR / "Inter-Regular.ttf"))
    page.insert_font(fontname="InterBold", fontfile=str(_FONT_DIR / "Inter-Bold.ttf"))

    page.draw_rect(fitz.Rect(0, 0, 595, 4), color=None, fill=(0.18, 0.73, 0.91))

    y = 48
    def line(text: str, size: int = 10, bold: bool = False, color=(0.13, 0.13, 0.13), indent: int = 48):
        nonlocal y
        page.insert_text(fitz.Point(indent, y), text,
                         fontsize=size, color=color,
                         fontname="InterBold" if bold else "Inter")
        y += size * 1.55

    line("Ledger Evidence Export", size=22, bold=True, color=(0.08, 0.08, 0.08))
    line(vessel_name, size=14, color=(0.12, 0.72, 0.9))
    y += 12

    line("PERIOD", size=8, color=(0.55, 0.55, 0.55))
    line(f"{date_from}  ·  {date_to}", size=11)
    y += 6

    line("REQUESTED BY", size=8, color=(0.55, 0.55, 0.55))
    line(scope_label, size=11)
    y += 6

    line("EXPORT ID", size=8, color=(0.55, 0.55, 0.55))
    line(export_id, size=9, color=(0.40, 0.40, 0.40))
    y += 6

    line("GENERATED", size=8, color=(0.55, 0.55, 0.55))
    line(datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), size=9, color=(0.40, 0.40, 0.40))
    y += 16

    line(f"Events: {len(masked_events)}", size=10)
    y += 20

    page.draw_line(fitz.Point(48, y), fitz.Point(547, y), color=(0.88, 0.88, 0.88), width=0.5)
    y += 16

    # Explicit disclosure — operator must see this before confirming export
    line("DISCLOSURE", size=8, bold=True, color=(0.55, 0.55, 0.55))
    y += 2
    line("Actor names and email addresses appear in readable form in the embedded JSON", size=8, color=(0.55, 0.55, 0.55))
    line("and on this cover. This is by design: evidence without attribution is not", size=8, color=(0.55, 0.55, 0.55))
    line("evidence. Database identifiers (user_id, yacht_id, entity_id) are replaced", size=8, color=(0.55, 0.55, 0.55))
    line("with HMAC-SHA256 refs and do not appear anywhere in this document.", size=8, color=(0.55, 0.55, 0.55))
    y += 8

    line("ID MASKING", size=8, bold=True, color=(0.55, 0.55, 0.55))
    y += 2
    line("actor_ref, vessel_ref, entity_ref are HMAC-SHA256(id, EXPORT_HMAC_SECRET).", size=8, color=(0.55, 0.55, 0.55))
    line("Same actor = same actor_ref across all events. Cross-event correlation", size=8, color=(0.55, 0.55, 0.55))
    line("is preserved. Verification: verify.celeste7.ai", size=8, color=(0.55, 0.55, 0.55))
    y += 8

    line("SIGNATURE STATUS", size=8, bold=True, color=(0.55, 0.55, 0.55))
    y += 2
    line("v0.1 staging: proof_hash chain only. PAdES-B-LT + RFC 3161 timestamp planned v1.0.", size=8, color=(0.55, 0.55, 0.55))
    line("Public certificate: celeste7.ai/.well-known/verify.pem", size=8, color=(0.55, 0.55, 0.55))

    # ── Embed JSON ──
    doc.embfile_add("ledger_events.json", json_bytes, desc="CelesteOS Ledger Events")

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()

    return pdf_bytes


# ── Export schema ──────────────────────────────────────────────────────────────

class LedgerExportRequest(BaseModel):
    date_from: str
    date_to: str
    scope: str = "department"   # "me" | "department" | "all"
    scope_user_id: Optional[str] = None
    yacht_id: Optional[str] = None


# ── Export endpoints ──────────────────────────────────────────────────────────

@router.get("/export/count")
async def get_export_event_count(
    date_from: str = Query(..., description="Start date YYYY-MM-DD"),
    date_to: str = Query(..., description="End date YYYY-MM-DD"),
    scope: str = Query(default="department", description="me | department | all"),
    yacht_id: Optional[str] = Query(default=None),
    user_context: dict = Depends(get_authenticated_user),
):
    """Preview how many events a given export scope would include."""
    try:
        tenant_alias  = user_context.get("tenant_key_alias", "")
        resolved_yid  = resolve_yacht_id(user_context, yacht_id)
        user_id       = user_context.get("user_id") or user_context.get("sub")
        user_role     = user_context.get("role", "")

        db_client = _get_tenant_client(tenant_alias)
        query = db_client.table("ledger_events").select("id", count="exact") \
            .eq("yacht_id", str(resolved_yid)) \
            .gte("created_at", f"{date_from}T00:00:00Z") \
            .lte("created_at", f"{date_to}T23:59:59Z")

        if scope == "me":
            query = query.eq("user_id", str(user_id))
        elif scope == "department" and user_role not in ("captain",):
            query = query.eq("department", user_context.get("department", ""))

        result = query.execute()
        return {"success": True, "count": result.count or 0}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Ledger] export/count failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/actors")
async def get_export_actors(
    date_from: str = Query(...),
    date_to: str = Query(...),
    yacht_id: Optional[str] = Query(default=None),
    user_context: dict = Depends(get_authenticated_user),
):
    """Return distinct actors for the export preview UI.
    actor_ref (HMAC-masked) is safe to return to the frontend.
    Note: actor_name is intentionally returned — this is confirmed-disclosure data.
    """
    try:
        export_secret = os.environ.get("EXPORT_HMAC_SECRET", "")
        tenant_alias  = user_context.get("tenant_key_alias", "")
        resolved_yid  = resolve_yacht_id(user_context, yacht_id)

        db_client = _get_tenant_client(tenant_alias)
        result = db_client.table("ledger_events") \
            .select("user_id, actor_name, user_role") \
            .eq("yacht_id", str(resolved_yid)) \
            .gte("created_at", f"{date_from}T00:00:00Z") \
            .lte("created_at", f"{date_to}T23:59:59Z") \
            .execute()

        seen = {}
        for row in (result.data or []):
            uid = row.get("user_id", "")
            if uid not in seen:
                seen[uid] = {
                    "actor_ref":  _mask_export_id(uid, export_secret),
                    "actor_name": row.get("actor_name") or row.get("user_role") or "Unknown",
                    "user_role":  row.get("user_role", ""),
                }

        return {"success": True, "actors": list(seen.values())}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Ledger] export/actors failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def create_ledger_export(
    payload: LedgerExportRequest,
    user_context: dict = Depends(get_authenticated_user),
):
    """
    Generate a ledger evidence PDF with embedded JSON.

    IDs masked: user_id→actor_ref, yacht_id→vessel_ref, entity_id→entity_ref
    Storage path: {hmac(yacht_id)[:16]}/{export_id}.pdf  (no raw UUID in path)
    v1.0 sealing (PAdES + RFC 3161) activated by LEDGER_EXPORT_SEAL=true.
    """
    export_secret = os.environ.get("EXPORT_HMAC_SECRET", "")
    if not export_secret:
        raise HTTPException(status_code=500, detail="EXPORT_HMAC_SECRET not configured")

    try:
        tenant_alias  = user_context.get("tenant_key_alias", "")
        resolved_yid  = resolve_yacht_id(user_context, payload.yacht_id)
        user_id       = user_context.get("user_id") or user_context.get("sub")
        user_role     = user_context.get("role", "")

        if not resolved_yid:
            raise HTTPException(status_code=400, detail="yacht_id required")

        db_client = _get_tenant_client(tenant_alias)

        vessel_row = db_client.table("yacht_registry").select("name") \
            .eq("id", str(resolved_yid)).maybe_single().execute()
        vessel_name = (vessel_row.data or {}).get("name", "Unknown Vessel") if vessel_row else "Unknown Vessel"

        requester_name = user_context.get("email") or user_context.get("name") or str(user_id)

        scope_user_id = None
        if payload.scope == "me":
            scope_user_id = str(user_id)
            scope_label = f"Self ({requester_name})"
        elif payload.scope == "department":
            scope_label = f"Department: {user_context.get('department', 'all')}"
        else:
            scope_label = f"All crew · requested by {requester_name}"

        # ── Fetch events ──
        query = db_client.table("ledger_events").select("*") \
            .eq("yacht_id", str(resolved_yid)) \
            .gte("created_at", f"{payload.date_from}T00:00:00Z") \
            .lte("created_at", f"{payload.date_to}T23:59:59Z")

        if payload.scope == "me":
            query = query.eq("user_id", payload.scope_user_id or str(user_id))
        elif payload.scope == "department" and user_role not in ("captain",):
            query = query.eq("department", user_context.get("department", ""))

        events_result = query.order("created_at", desc=False).execute()
        events = events_result.data or []

        if not events:
            raise HTTPException(
                status_code=404,
                detail="No ledger events found for the requested scope and date range"
            )

        # ── Generate PDF (+ optional v1.0 sealing) ──
        export_id = str(uuid4())
        pdf_bytes = _build_ledger_pdf(
            events=events,
            export_id=export_id,
            vessel_name=vessel_name,
            date_from=payload.date_from,
            date_to=payload.date_to,
            requester_name=requester_name,
            scope_label=scope_label,
            export_secret=export_secret,
        )

        sealing_info = None
        is_sealed = os.environ.get("LEDGER_EXPORT_SEAL", "false").lower() == "true"
        if is_sealed:
            try:
                import asyncio
                from functools import partial
                from evidence.sealing import seal_export, SealingError
                loop = asyncio.get_event_loop()
                pdf_bytes, sealing_info = await loop.run_in_executor(
                    None, partial(seal_export, pdf_bytes)
                )
                logger.info(
                    f"[Ledger] Export {export_id} sealed — "
                    f"sha256={sealing_info.pdf_sha256[:16]}… "
                    f"tsa={sealing_info.tsa_authority}"
                )
            except Exception as seal_err:
                # Raise — never return an unsealed document when sealing is expected.
                # Caller must investigate; half-sealed state is unacceptable.
                logger.error(f"[Ledger] Sealing failed for {export_id}: {seal_err}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Sealing failed: {seal_err}. Export aborted — no document was stored."
                )

        # ── HMAC storage path — no raw UUID visible in any signed URL ──
        vessel_folder = _mask_export_id(str(resolved_yid), export_secret)[:16]
        storage_path  = f"{vessel_folder}/{export_id}.pdf"

        # ── Upload ──
        storage = db_client.storage.from_("ledger-exports")
        storage.upload(
            path=storage_path,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf", "cache-control": "no-store"},
        )

        signed = storage.create_signed_url(storage_path, expires_in=3600)
        download_url = signed.get("signedURL") or signed.get("signedUrl") or ""

        # ── Record ──
        insert_row = {
            "id":                   export_id,
            "yacht_id":             str(resolved_yid),
            "requested_by_user_id": str(user_id),
            "requested_by_role":    user_role or "member",
            "requested_by_dept":    user_context.get("department", ""),
            "requested_by_name":    requester_name,
            "scope_user_id":        scope_user_id,
            "scope_department":     user_context.get("department", "") if payload.scope == "department" else None,
            "date_from":            payload.date_from,
            "date_to":              payload.date_to,
            "event_count":          len(events),
            "storage_bucket":       "ledger-exports",
            "storage_path":         storage_path,
            "file_name":            f"celeste-evidence-{export_id[:8]}.pdf",
            "file_size_bytes":      len(pdf_bytes),
            "export_status":        "completed",
            "generated_at":         datetime.utcnow().isoformat(),
        }
        if sealing_info is not None:
            insert_row["content_hash"]     = sealing_info.pdf_sha256
            insert_row["tsa_authority"]    = sealing_info.tsa_authority
            insert_row["cert_fingerprint"] = sealing_info.cert_fingerprint
        db_client.table("ledger_exports").insert(insert_row).execute()

        logger.info(
            f"[Ledger] Export {export_id} — {len(events)} events, "
            f"{len(pdf_bytes):,} bytes, sealed={is_sealed}"
        )

        return {
            "success":          True,
            "export_id":        export_id,
            "event_count":      len(events),
            "file_size_bytes":  len(pdf_bytes),
            "download_url":     download_url,
            "storage_path":     storage_path,
            "sealed":           is_sealed,
            "tsa_authority":    sealing_info.tsa_authority if sealing_info else None,
            "cert_fingerprint": sealing_info.cert_fingerprint if sealing_info else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Ledger] export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
