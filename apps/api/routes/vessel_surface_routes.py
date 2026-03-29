"""
Vessel Surface & Domain List Endpoints
=======================================

Three endpoints powering the interface pivot:

1. GET /api/vessel/{vessel_id}/surface
   → Current-state summary for the Vessel Surface home screen.
   → 6 sections: work_orders, faults, last_handover, parts_below_min,
     recent_activity, certificates_expiring.

2. GET /api/vessel/{vessel_id}/domain/{domain}/records
   → Full record list for one domain. Powers list views.
   → Accepts q (NLP Tier 2), status, sort, limit, offset.

3. GET /api/vessel/{vessel_id}/domain/{domain}/search-inline
   → Fast typeahead for Tier 3 inline relational search.
   → Returns prefill_fields per result for form pre-population.

All endpoints are READ-ONLY. No mutations. No new tables.
All queries scope to yacht_id from auth context — vessel isolation enforced.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timedelta, timezone

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vessel", tags=["vessel-surface"])


# ── Table + column mappings ──────────────────────────────────────────────────

DOMAIN_TABLE_MAP = {
    "work_orders": "pms_work_orders",
    "faults": "pms_faults",
    "equipment": "pms_equipment",
    "parts": "pms_parts",
    "certificates": "pms_vessel_certificates",
    "documents": "doc_metadata",
    "handover": "handover_drafts",
    "hours_of_rest": "pms_hours_of_rest",
    "shopping_list": "pms_shopping_list_items",
    "purchase_orders": "pms_purchase_orders",
    "receiving": "pms_receiving",
    "warranty": "pms_warranty_claims",
}

# Select columns per domain (lightweight — only what list views need)
DOMAIN_SELECT = {
    "work_orders": "id, title, status, priority, assigned_to, equipment_id, due_date, created_at, updated_at",
    "faults": "id, title, status, severity, equipment_id, created_at, updated_at",
    "equipment": "id, name, system, location, status, manufacturer, model, created_at, updated_at",
    "parts": "id, name, part_number, quantity_on_hand, minimum_quantity, location, unit_cost, created_at, updated_at",
    "certificates": "id, certificate_name, certificate_type, certificate_number, issuing_authority, issue_date, expiry_date, status, created_at",
    "documents": "id, name, document_type, storage_path, created_at, updated_at",
    "handover": "id, title, state, generated_by_user_id, created_at",
    "hours_of_rest": "id, crew_member_name, date, rest_hours, status, created_at",
    "shopping_list": "id, item_name, quantity, status, requested_by, created_at, updated_at",
    "purchase_orders": "id, po_number, supplier_name, status, total_amount, currency, created_at, updated_at",
    "receiving": "id, po_id, received_by, status, received_date, created_at",
    "warranty": "id, vendor_name, part_number, status, expiry_date, claimed_amount, currency, created_at",
}

# Default sort per domain
DOMAIN_DEFAULT_SORT = {
    "work_orders": "created_at",
    "faults": "created_at",
    "equipment": "name",
    "parts": "name",
    "certificates": "expiry_date",
    "documents": "created_at",
    "handover": "created_at",
    "hours_of_rest": "date",
    "shopping_list": "created_at",
    "purchase_orders": "created_at",
    "receiving": "created_at",
    "warranty": "created_at",
}


def _validate_vessel_access(auth: dict, vessel_id: str):
    """Enforce vessel isolation: auth yacht_id must match requested vessel_id."""
    auth_yacht = auth.get("yacht_id")
    if not auth_yacht or str(auth_yacht) != str(vessel_id):
        raise HTTPException(
            status_code=403,
            detail="Access denied: vessel_id does not match authenticated session"
        )


def _age_display(dt_str: Optional[str]) -> str:
    """Convert ISO timestamp to human-readable age like '2d', '5h', '3w'."""
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        days = delta.days
        if days > 365:
            return f"{days // 365}y"
        if days > 30:
            return f"{days // 30}mo"
        if days > 7:
            return f"{days // 7}w"
        if days > 0:
            return f"{days}d"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h"
        return "<1h"
    except Exception:
        return ""


def _status_priority_key(record: dict) -> tuple:
    """Sort key: critical/overdue first, then by severity/priority."""
    status = (record.get("status") or "").lower()
    priority = (record.get("priority") or record.get("severity") or "").lower()

    status_order = {"overdue": 0, "critical": 1, "open": 2, "in_progress": 3, "due_soon": 4}
    priority_order = {"critical": 0, "high": 1, "normal": 2, "medium": 2, "low": 3}

    return (
        status_order.get(status, 5),
        priority_order.get(priority, 5),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1: VESSEL SURFACE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{vessel_id}/surface")
async def get_vessel_surface(vessel_id: str, auth: dict = Depends(get_authenticated_user)):
    """
    Returns current-state summary for the Vessel Surface home screen.
    6 sections, read-only, scoped to authenticated vessel.
    """
    _validate_vessel_access(auth, vessel_id)

    tenant_key = auth["tenant_key_alias"]
    yacht_id = auth["yacht_id"]
    supabase = get_tenant_client(tenant_key)

    result = {}

    # ── Work Orders: top 3 by urgency ────────────────────────────────────────
    try:
        wo_r = supabase.table("pms_work_orders").select(
            "id, title, status, priority, assigned_to, equipment_id, due_date, created_at"
        ).eq("yacht_id", yacht_id).in_(
            "status", ["planned", "in_progress"]
        ).order("created_at", desc=True).limit(20).execute()

        wo_items = wo_r.data or []

        # Enrich with equipment names in batch
        equip_ids = list({w.get("equipment_id") for w in wo_items if w.get("equipment_id")})
        equip_names = {}
        if equip_ids:
            try:
                eq_r = supabase.table("pms_equipment").select("id, name").in_("id", equip_ids).execute()
                equip_names = {e["id"]: e.get("name", "") for e in (eq_r.data or [])}
            except Exception:
                pass

        # Mark overdue
        now = datetime.now(timezone.utc)
        for w in wo_items:
            due = w.get("due_date")
            if due and w.get("status") not in ("overdue",):
                try:
                    due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
                    if due_dt < now:
                        w["status"] = "overdue"
                except Exception:
                    pass

        wo_items.sort(key=_status_priority_key)
        wo_top = wo_items[:3]

        overdue_count = sum(1 for w in wo_items if (w.get("status") or "").lower() == "overdue")

        result["work_orders"] = {
            "open_count": len(wo_items),
            "overdue_count": overdue_count,
            "items": [
                {
                    "id": w.get("id"),
                    "title": w.get("title", ""),
                    "equipment_id": w.get("equipment_id"),
                    "equipment_name": equip_names.get(w.get("equipment_id"), ""),
                    "assigned_to": w.get("assigned_to", ""),
                    "status": w.get("status", "open"),
                    "priority": w.get("priority", "normal"),
                    "age_days": (now - datetime.fromisoformat(
                        (w.get("created_at") or now.isoformat()).replace("Z", "+00:00")
                    )).days if w.get("created_at") else 0,
                    "due_date": w.get("due_date"),
                }
                for w in wo_top
            ],
            "limit": 3,
        }
    except Exception as e:
        logger.error(f"[VesselSurface] Work orders query failed: {e}")
        result["work_orders"] = {"open_count": 0, "overdue_count": 0, "items": [], "limit": 3}

    # ── Faults: top 3 by severity ────────────────────────────────────────────
    try:
        f_r = supabase.table("pms_faults").select(
            "id, title, status, severity, equipment_id, created_at"
        ).eq("yacht_id", yacht_id).in_(
            "status", ["open", "critical", "monitoring", "in_progress", "investigating"]
        ).order("created_at", desc=True).limit(20).execute()

        fault_items = f_r.data or []
        fault_items.sort(key=_status_priority_key)
        fault_top = fault_items[:3]

        critical_count = sum(1 for f in fault_items if (f.get("severity") or "").lower() == "critical")

        result["faults"] = {
            "open_count": len(fault_items),
            "critical_count": critical_count,
            "items": [
                {
                    "id": f.get("id"),
                    "title": f.get("title", ""),
                    "severity": f.get("severity", "normal"),
                    "status": f.get("status", "open"),
                    "assigned_to": f.get("assigned_to", ""),
                    "equipment_id": f.get("equipment_id"),
                    "age_display": _age_display(f.get("created_at")),
                }
                for f in fault_top
            ],
        }
    except Exception as e:
        logger.error(f"[VesselSurface] Faults query failed: {e}")
        result["faults"] = {"open_count": 0, "critical_count": 0, "items": []}

    # ── Last Handover ────────────────────────────────────────────────────────
    try:
        ho_r = supabase.table("handover_drafts").select(
            "id, title, state, generated_by_user_id, created_at"
        ).eq("yacht_id", yacht_id).order(
            "created_at", desc=True
        ).limit(1).execute()

        ho_data = (ho_r.data or [None])[0]
        if ho_data:
            result["last_handover"] = {
                "id": ho_data.get("id"),
                "from_crew": ho_data.get("generated_by_user_id", ""),
                "to_crew": "",
                "signed_at": ho_data.get("created_at"),
                "status": ho_data.get("state", "draft"),
            }
        else:
            result["last_handover"] = None
    except Exception as e:
        logger.error(f"[VesselSurface] Handover query failed: {e}")
        result["last_handover"] = None

    # ── Parts Below Min Stock ────────────────────────────────────────────────
    try:
        # Supabase doesn't support "column < other_column" in PostgREST easily
        # Fetch parts with low stock using a reasonable approach
        p_r = supabase.table("pms_parts").select(
            "id, name, quantity_on_hand, minimum_quantity, location"
        ).eq("yacht_id", yacht_id).execute()

        all_parts = p_r.data or []
        below_min = [
            p for p in all_parts
            if p.get("minimum_quantity") is not None
            and p.get("quantity_on_hand") is not None
            and p["quantity_on_hand"] < p["minimum_quantity"]
        ]

        # Sort: zero stock first, then by ratio ascending
        below_min.sort(key=lambda p: (
            0 if p.get("quantity_on_hand", 0) == 0 else 1,
            (p.get("quantity_on_hand", 0) / max(p.get("minimum_quantity", 1), 1)),
        ))

        result["parts_below_min"] = {
            "count": len(below_min),
            "items": [
                {
                    "id": p.get("id"),
                    "name": p.get("name", ""),
                    "stock_level": p.get("quantity_on_hand", 0),
                    "min_stock": p.get("minimum_quantity", 0),
                    "location": p.get("location", ""),
                }
                for p in below_min[:10]
            ],
        }
    except Exception as e:
        logger.error(f"[VesselSurface] Parts below min query failed: {e}")
        result["parts_below_min"] = {"count": 0, "items": []}

    # ── Recent Activity (from ledger) ────────────────────────────────────────
    try:
        led_r = supabase.table("ledger_events").select(
            "id, entity_type, entity_id, action, actor_name, created_at, change_summary"
        ).eq("yacht_id", yacht_id).neq(
            "event_category", "read"
        ).order("created_at", desc=True).limit(5).execute()

        result["recent_activity"] = [
            {
                "entity_type": ev.get("entity_type", ""),
                "entity_id": ev.get("entity_id", ""),
                "entity_ref": str(ev.get("entity_id", ""))[:8],
                "action": ev.get("action", ""),
                "actor": ev.get("actor_name", ""),
                "timestamp": ev.get("created_at"),
                "summary": ev.get("change_summary", ""),
            }
            for ev in (led_r.data or [])
        ]
    except Exception as e:
        logger.error(f"[VesselSurface] Recent activity query failed: {e}")
        result["recent_activity"] = []

    # ── Certificates Expiring (within 45 days) ───────────────────────────────
    try:
        cutoff = (datetime.now(timezone.utc) + timedelta(days=45)).strftime("%Y-%m-%d")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        cert_r = supabase.table("pms_vessel_certificates").select(
            "id, certificate_name, certificate_type, expiry_date, status"
        ).eq("yacht_id", yacht_id).gte(
            "expiry_date", today
        ).lte(
            "expiry_date", cutoff
        ).order("expiry_date").execute()

        cert_items = cert_r.data or []
        result["certificates_expiring"] = {
            "count": len(cert_items),
            "items": [
                {
                    "id": c.get("id"),
                    "certificate_name": c.get("certificate_name", ""),
                    "certificate_type": c.get("certificate_type", ""),
                    "expiry_date": c.get("expiry_date"),
                    "days_remaining": (
                        datetime.strptime(c["expiry_date"], "%Y-%m-%d") - datetime.now(timezone.utc).replace(
                            hour=0, minute=0, second=0, microsecond=0
                        )
                    ).days if c.get("expiry_date") else None,
                    "status": c.get("status", "valid"),
                }
                for c in cert_items
            ],
        }
    except Exception as e:
        logger.error(f"[VesselSurface] Certificates query failed: {e}")
        result["certificates_expiring"] = {"count": 0, "items": []}

    # ── Domain counts for sidebar badges ─────────────────────────────────────
    try:
        counts = {}
        # Work orders (open)
        counts["work_orders"] = result["work_orders"]["open_count"]
        counts["work_orders_overdue"] = result["work_orders"]["overdue_count"]

        # Faults (open)
        counts["faults"] = result["faults"]["open_count"]
        counts["faults_critical"] = result["faults"]["critical_count"]

        # Parts below min
        counts["parts_below_min"] = result["parts_below_min"]["count"]

        # Certificates expiring
        counts["certificates_expiring"] = result["certificates_expiring"]["count"]

        result["domain_counts"] = counts
    except Exception:
        result["domain_counts"] = {}

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2: DOMAIN RECORD LIST
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{vessel_id}/domain/{domain}/records")
async def get_domain_records(
    vessel_id: str,
    domain: str,
    auth: dict = Depends(get_authenticated_user),
    q: Optional[str] = Query(None, description="NLP search query (Tier 2)"),
    status: Optional[str] = Query(None, description="Status filter chip value"),
    assigned: Optional[str] = Query(None, description="Assigned to filter"),
    sort: Optional[str] = Query(None, description="Sort field"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Returns paginated record list for one domain. Powers domain list views.
    When q is provided, filters via search_index (same NLP pipeline, domain-scoped).
    """
    _validate_vessel_access(auth, vessel_id)

    if domain not in DOMAIN_TABLE_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown domain: {domain}")

    tenant_key = auth["tenant_key_alias"]
    yacht_id = auth["yacht_id"]
    supabase = get_tenant_client(tenant_key)

    table = DOMAIN_TABLE_MAP[domain]
    select_cols = DOMAIN_SELECT.get(domain, "*")
    sort_field = sort or DOMAIN_DEFAULT_SORT.get(domain, "created_at")
    sort_desc = sort_field in ("created_at", "updated_at", "date")

    try:
        # If NLP query provided, search via search_index first for IDs
        matching_ids = None
        if q and q.strip():
            matching_ids = await _search_domain_ids(supabase, yacht_id, domain, q.strip())

        # Build main query
        query = supabase.table(table).select(select_cols, count="exact").eq("yacht_id", yacht_id)

        # Apply search filter
        if matching_ids is not None:
            if len(matching_ids) == 0:
                return {"domain": domain, "total_count": 0, "filtered_count": 0, "records": []}
            query = query.in_("id", matching_ids)

        # Apply status chip filter
        if status:
            if domain == "faults":
                query = query.eq("severity" if status in ("critical", "high", "normal", "low") else "status", status)
            else:
                query = query.eq("status", status)

        # Apply assigned filter
        if assigned and domain in ("work_orders",):
            query = query.eq("assigned_to", assigned)

        # Soft-delete filter for documents
        if domain == "documents":
            query = query.is_("deleted_at", "null")

        # Sort
        query = query.order(sort_field, desc=sort_desc)

        # Paginate
        query = query.range(offset, offset + limit - 1)

        result = query.execute()
        records = result.data or []
        total = result.count or len(records)

        # Format records for frontend
        formatted = [_format_record(domain, r) for r in records]

        return {
            "domain": domain,
            "total_count": total,
            "filtered_count": len(formatted),
            "records": formatted,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DomainRecords] Query failed for {domain}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query {domain}")


async def _search_domain_ids(supabase, yacht_id: str, domain: str, query: str) -> List[str]:
    """
    Search search_index for matching IDs within a domain.
    Uses full-text search (tsv column) for natural language queries,
    with ilike fallback for short queries or codes that FTS may miss.
    Domain-scoped via object_type filter — same approach as f1_search_cards.
    """
    domain_to_object_type = {
        "work_orders": ["work_order"],
        "faults": ["fault"],
        "equipment": ["equipment"],
        "parts": ["part", "inventory"],
        "certificates": ["certificate"],
        "documents": ["document"],
        "handover": ["handover", "handover_item"],
        "hours_of_rest": ["hours_of_rest"],
        "shopping_list": ["shopping_item"],
        "purchase_orders": ["purchase_order"],
        "receiving": ["receiving"],
        "warranty": ["warranty"],
    }

    object_types = domain_to_object_type.get(domain, [domain])

    try:
        ids = set()

        # Multi-term AND search: each word must appear in search_text
        # "critical engine" → ilike '%critical%' AND ilike '%engine%'
        words = [w.strip() for w in query.split() if len(w.strip()) >= 2]

        if words:
            try:
                q = supabase.table("search_index").select("object_id").eq(
                    "yacht_id", yacht_id
                ).in_(
                    "object_type", object_types
                )
                for word in words:
                    q = q.ilike("search_text", f"%{word}%")
                q = q.limit(200)
                r = q.execute()
                ids.update(row["object_id"] for row in (r.data or []))
            except Exception as e:
                logger.debug(f"[DomainRecords] Multi-word search failed: {e}")

        # Fallback: single phrase match if multi-word returned nothing
        if not ids:
            try:
                r = supabase.table("search_index").select("object_id").eq(
                    "yacht_id", yacht_id
                ).in_(
                    "object_type", object_types
                ).ilike(
                    "search_text", f"%{query}%"
                ).limit(200).execute()
                ids.update(row["object_id"] for row in (r.data or []))
            except Exception as e:
                logger.debug(f"[DomainRecords] Phrase search failed: {e}")

        return list(ids)[:200]
    except Exception as e:
        logger.warning(f"[DomainRecords] search_index query failed: {e}")
        return []


def _format_record(domain: str, record: dict) -> dict:
    """Format a raw DB record into the standard list view shape."""
    now = datetime.now(timezone.utc)

    # Common fields
    base = {
        "id": record.get("id"),
        "updated_at": record.get("updated_at") or record.get("created_at"),
        "age_display": _age_display(record.get("created_at")),
    }

    if domain == "work_orders":
        base.update({
            "ref": f"WO-{str(record.get('id', ''))[:6]}",
            "title": record.get("title", ""),
            "status": record.get("status", "open"),
            "priority": record.get("priority", "normal"),
            "assigned_to": record.get("assigned_to", ""),
            "linked_equipment_id": record.get("equipment_id"),
            "meta": f"{record.get('priority', 'normal').upper()} · {record.get('status', 'open').upper()}",
        })
    elif domain == "faults":
        base.update({
            "ref": f"F-{str(record.get('id', ''))[:6]}",
            "title": record.get("title", ""),
            "status": record.get("status", "open"),
            "severity": record.get("severity", "normal"),
            "assigned_to": record.get("assigned_to", ""),
            "linked_equipment_id": record.get("equipment_id"),
            "meta": f"{record.get('severity', 'normal').upper()} · {record.get('status', 'open').upper()}",
        })
    elif domain == "equipment":
        base.update({
            "ref": f"E-{str(record.get('id', ''))[:6]}",
            "title": record.get("name", ""),
            "status": record.get("status", "active"),
            "system": record.get("system", ""),
            "location": record.get("location", ""),
            "meta": f"{record.get('system', '')} · {record.get('location', '')}",
        })
    elif domain == "parts":
        stock = record.get("quantity_on_hand", 0) or 0
        min_s = record.get("minimum_quantity", 0) or 0
        base.update({
            "ref": record.get("part_number", f"P-{str(record.get('id', ''))[:6]}"),
            "title": record.get("name", ""),
            "stock_level": stock,
            "min_stock": min_s,
            "stock_status": "critical" if stock == 0 else ("warning" if stock < min_s else "ok"),
            "location": record.get("location", ""),
            "meta": f"Stock: {stock}/{min_s} · {record.get('location', '')}",
        })
    elif domain == "certificates":
        days_rem = None
        if record.get("expiry_date"):
            try:
                exp = datetime.strptime(record["expiry_date"], "%Y-%m-%d")
                days_rem = (exp - now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)).days
            except Exception:
                pass
        base.update({
            "ref": record.get("certificate_number", f"C-{str(record.get('id', ''))[:6]}"),
            "title": record.get("certificate_name", ""),
            "certificate_type": record.get("certificate_type", ""),
            "expiry_date": record.get("expiry_date"),
            "days_remaining": days_rem,
            "status": record.get("status", "valid"),
            "meta": f"{record.get('certificate_type', '')} · Expires: {record.get('expiry_date', 'N/A')}",
        })
    elif domain == "purchase_orders":
        base.update({
            "ref": record.get("po_number", f"PO-{str(record.get('id', ''))[:6]}"),
            "title": f"PO {record.get('po_number', '')} — {record.get('supplier_name', '')}",
            "status": record.get("status", "draft"),
            "supplier_name": record.get("supplier_name", ""),
            "total_amount": record.get("total_amount"),
            "currency": record.get("currency", "EUR"),
            "meta": f"{record.get('supplier_name', '')} · {record.get('status', '').upper()}",
        })
    elif domain == "receiving":
        base.update({
            "ref": f"RCV-{str(record.get('id', ''))[:6]}",
            "title": f"Receiving {str(record.get('id', ''))[:8]}",
            "status": record.get("status", "pending"),
            "received_by": record.get("received_by", ""),
            "received_date": record.get("received_date"),
            "meta": f"{record.get('received_by', '')} · {record.get('status', '').upper()}",
        })
    else:
        # Generic fallback for other domains
        title_field = next(
            (record.get(f) for f in ("title", "name", "item_name", "certificate_name", "crew_member_name") if record.get(f)),
            str(record.get("id", ""))[:8],
        )
        base.update({
            "ref": str(record.get("id", ""))[:8],
            "title": title_field,
            "status": record.get("status", ""),
            "meta": record.get("status", ""),
        })

    return base


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3: TIER 3 INLINE RELATIONAL SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{vessel_id}/domain/{domain}/search-inline")
async def search_inline(
    vessel_id: str,
    domain: str,
    auth: dict = Depends(get_authenticated_user),
    q: str = Query("", description="Search query"),
    target: Optional[str] = Query(None, description="Target domain to search in"),
    exclude_ids: Optional[str] = Query(None, description="Comma-separated IDs to exclude"),
):
    """
    Fast typeahead search for Tier 3 inline relational popup.
    Returns max 10 results with prefill_fields for form pre-population.
    Scoped to current vessel — no cross-vessel leakage.
    """
    _validate_vessel_access(auth, vessel_id)

    search_domain = target or domain
    if search_domain not in DOMAIN_TABLE_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown target domain: {search_domain}")

    tenant_key = auth["tenant_key_alias"]
    yacht_id = auth["yacht_id"]
    supabase = get_tenant_client(tenant_key)

    table = DOMAIN_TABLE_MAP[search_domain]
    excluded = [eid.strip() for eid in (exclude_ids or "").split(",") if eid.strip()]

    try:
        # Fast text search: use ilike on key columns
        select_cols = DOMAIN_SELECT.get(search_domain, "*")
        query = supabase.table(table).select(select_cols).eq("yacht_id", yacht_id)

        # Soft-delete filter
        if search_domain == "documents":
            query = query.is_("deleted_at", "null")

        # Exclude already-linked IDs
        if excluded:
            for eid in excluded:
                query = query.neq("id", eid)

        # Text filter
        if q.strip():
            # Search on name/title column
            name_col = _name_column(search_domain)
            query = query.ilike(name_col, f"%{q.strip()}%")

        query = query.limit(10)
        result = query.execute()
        records = result.data or []

        return {
            "target": search_domain,
            "results": [_format_inline_result(search_domain, r) for r in records],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[InlineSearch] Query failed for {search_domain}: {e}")
        raise HTTPException(status_code=500, detail=f"Inline search failed for {search_domain}")


def _name_column(domain: str) -> str:
    """Return the primary searchable text column for a domain."""
    return {
        "work_orders": "title",
        "faults": "title",
        "equipment": "name",
        "parts": "name",
        "certificates": "certificate_name",
        "documents": "name",
        "handover": "title",
        "shopping_list": "item_name",
        "purchase_orders": "supplier_name",
        "receiving": "received_by",
        "warranty": "vendor_name",
        "hours_of_rest": "crew_member_name",
    }.get(domain, "id")


def _format_inline_result(domain: str, record: dict) -> dict:
    """Format a record for Tier 3 inline search response with prefill_fields."""
    base = {
        "id": record.get("id"),
        "ref": "",
        "display_name": "",
        "meta": "",
        "status_display": "",
        "status_level": "ok",
        "addable": True,
        "prefill_fields": {},
    }

    if domain == "parts":
        stock = record.get("quantity_on_hand", 0) or 0
        min_s = record.get("minimum_quantity", 0) or 0
        base.update({
            "ref": record.get("part_number", str(record.get("id", ""))[:8]),
            "display_name": record.get("name", ""),
            "meta": record.get("location", ""),
            "status_display": f"{stock} left" if stock > 0 else "Out of stock",
            "status_level": "critical" if stock == 0 else ("warning" if stock < min_s else "ok"),
            "addable": stock > 0,
            "prefill_fields": {
                k: v for k, v in {
                    "part_id": record.get("id"),
                    "part_name": record.get("name"),
                    "part_number": record.get("part_number"),
                    "unit_cost": record.get("unit_cost"),
                    "current_stock": stock,
                }.items() if v is not None
            },
        })
    elif domain == "equipment":
        base.update({
            "ref": f"E-{str(record.get('id', ''))[:6]}",
            "display_name": record.get("name", ""),
            "meta": f"{record.get('system', '')} · {record.get('location', '')}",
            "status_display": record.get("status", "active"),
            "status_level": "ok",
            "prefill_fields": {
                k: v for k, v in {
                    "equipment_id": record.get("id"),
                    "equipment_name": record.get("name"),
                    "equipment_system": record.get("system"),
                    "equipment_location": record.get("location"),
                    "manufacturer": record.get("manufacturer"),
                    "model": record.get("model"),
                }.items() if v is not None
            },
        })
    elif domain == "documents":
        base.update({
            "ref": str(record.get("id", ""))[:8],
            "display_name": record.get("name", ""),
            "meta": record.get("document_type", ""),
            "status_display": record.get("document_type", ""),
            "status_level": "ok",
            "prefill_fields": {
                k: v for k, v in {
                    "document_id": record.get("id"),
                    "document_name": record.get("name"),
                    "document_type": record.get("document_type"),
                }.items() if v is not None
            },
        })
    elif domain == "work_orders":
        base.update({
            "ref": f"WO-{str(record.get('id', ''))[:6]}",
            "display_name": record.get("title", ""),
            "meta": f"{record.get('priority', 'normal').upper()} · {record.get('status', 'open').upper()}",
            "status_display": record.get("status", "open"),
            "status_level": "critical" if record.get("status") == "overdue" else "ok",
            "prefill_fields": {
                k: v for k, v in {
                    "work_order_id": record.get("id"),
                    "work_order_title": record.get("title"),
                    "equipment_id": record.get("equipment_id"),
                }.items() if v is not None
            },
        })
    else:
        # Generic fallback
        name_col = _name_column(domain)
        base.update({
            "ref": str(record.get("id", ""))[:8],
            "display_name": record.get(name_col, str(record.get("id", ""))[:8]),
            "meta": record.get("status", ""),
            "status_display": record.get("status", ""),
        })

    return base


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4: ACTION CONTEXT PREFILL
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{vessel_id}/action/prefill")
async def action_prefill(
    vessel_id: str,
    body: dict,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Context resolution service for action button pre-population.
    Given action_id + source entity, returns prefill_fields map.
    Only resolves fields that are CERTAIN from context. Never fabricates.
    """
    _validate_vessel_access(auth, vessel_id)

    action_id = body.get("action_id", "")
    source_type = body.get("source_entity_type", "")
    source_id = body.get("source_entity_id", "")

    if not action_id or not source_type or not source_id:
        raise HTTPException(status_code=400, detail="action_id, source_entity_type, and source_entity_id required")

    tenant_key = auth["tenant_key_alias"]
    yacht_id = auth["yacht_id"]
    supabase = get_tenant_client(tenant_key)

    prefill = {}

    try:
        # Fetch source entity
        table = DOMAIN_TABLE_MAP.get(source_type)
        if not table:
            # Try singular form
            singular_map = {
                "fault": "faults", "work_order": "work_orders", "part": "parts",
                "certificate": "certificates", "document": "documents",
                "equipment": "equipment", "handover_export": "handover",
            }
            domain_key = singular_map.get(source_type, source_type)
            table = DOMAIN_TABLE_MAP.get(domain_key)

        if not table:
            return {"prefill_fields": {}}

        r = supabase.table(table).select("*").eq("id", source_id).eq("yacht_id", yacht_id).maybe_single().execute()
        if not r or not r.data:
            return {"prefill_fields": {}}

        entity = r.data

        # ── Resolve prefill based on action + source type ────────────────────
        if action_id == "create_work_order":
            if source_type in ("fault", "faults"):
                prefill = {
                    k: v for k, v in {
                        "linked_equipment_id": entity.get("equipment_id"),
                        "linked_fault_id": entity.get("id"),
                        "title": f"Repair: {entity.get('title', '')}" if entity.get("title") else None,
                    }.items() if v is not None
                }
            elif source_type in ("equipment",):
                prefill = {
                    k: v for k, v in {
                        "linked_equipment_id": entity.get("id"),
                        "equipment_name": entity.get("name"),
                        "equipment_location": entity.get("location"),
                    }.items() if v is not None
                }

        elif action_id == "log_fault":
            if source_type in ("equipment",):
                prefill = {
                    k: v for k, v in {
                        "linked_equipment_id": entity.get("id"),
                        "equipment_name": entity.get("name"),
                        "equipment_system": entity.get("system"),
                    }.items() if v is not None
                }

        elif action_id == "add_to_handover":
            # Always resolvable from any entity
            prefill = {
                k: v for k, v in {
                    "entity_type": source_type,
                    "entity_id": entity.get("id"),
                    "entity_title": entity.get("title") or entity.get("name") or entity.get("certificate_name") or entity.get("item_name", ""),
                    "entity_status": entity.get("status", ""),
                    "entity_ref": str(entity.get("id", ""))[:8],
                }.items() if v is not None
            }

        elif action_id == "add_to_shopping_list":
            if source_type in ("part", "parts"):
                prefill = {
                    k: v for k, v in {
                        "part_id": entity.get("id"),
                        "part_name": entity.get("name"),
                        "current_stock": entity.get("quantity_on_hand"),
                        "min_stock": entity.get("minimum_quantity"),
                        "unit_cost_last": entity.get("unit_cost"),
                    }.items() if v is not None
                }

        elif action_id == "order_part":
            if source_type in ("part", "parts"):
                stock = entity.get("quantity_on_hand", 0) or 0
                min_s = entity.get("minimum_quantity", 0) or 0
                suggested_qty = max(min_s - stock, 1) if min_s > stock else 1
                prefill = {
                    k: v for k, v in {
                        "part_id": entity.get("id"),
                        "part_name": entity.get("name"),
                        "supplier_last_used": entity.get("supplier"),
                        "quantity_suggestion": suggested_qty,
                    }.items() if v is not None
                }

        elif action_id == "issue_warranty_claim":
            if source_type in ("part", "parts"):
                prefill = {
                    k: v for k, v in {
                        "part_id": entity.get("id"),
                        "part_name": entity.get("name"),
                        "supplier": entity.get("supplier"),
                        "equipment_id": entity.get("equipment_id"),
                    }.items() if v is not None
                }
            elif source_type in ("equipment",):
                prefill = {
                    k: v for k, v in {
                        "equipment_id": entity.get("id"),
                        "equipment_name": entity.get("name"),
                    }.items() if v is not None
                }

        return {"prefill_fields": prefill}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ActionPrefill] Failed for {action_id} on {source_type}/{source_id}: {e}")
        return {"prefill_fields": {}}
