"""
Vessel Attention Endpoint
=========================

GET /api/vessel/{vessel_id}/attention
  → Scored list of items needing attention across all PMS domains.
  → Replaces direct-Supabase queries in useNeedsAttention.ts with
    a proper backend endpoint that hits the tenant DB.
  → Scoped by yacht_id for multi-vessel support.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timedelta, timezone

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vessel", tags=["attention"])


# ── Vessel access validation (same pattern as vessel_surface_routes) ─────────

def _validate_vessel_access(auth: dict, vessel_id: str):
    vessel_ids = auth.get("vessel_ids", [auth.get("yacht_id")])
    if vessel_id == "all":
        if not auth.get("is_fleet_user"):
            raise HTTPException(status_code=403, detail="Access denied: overview mode requires fleet access")
        return
    if str(vessel_id) not in [str(v) for v in vessel_ids]:
        raise HTTPException(status_code=403, detail="Access denied: vessel_id does not match authenticated session")


def _resolve_yacht_ids(auth: dict, vessel_id: str) -> List[str]:
    if vessel_id == "all":
        return auth.get("vessel_ids", [auth.get("yacht_id")])
    return [vessel_id]


def _scope_query(query, yacht_ids: List[str]):
    if len(yacht_ids) == 1:
        return query.eq("yacht_id", yacht_ids[0])
    return query.in_("yacht_id", yacht_ids)


# ── Scoring helpers ──────────────────────────────────────────────────────────

def _days_until(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return (dt - datetime.now(timezone.utc)).days
    except Exception:
        return None


def _days_since(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return None


def _severity_label(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 50:
        return "warning"
    return "info"


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/{vessel_id}/attention")
async def get_vessel_attention(vessel_id: str, auth: dict = Depends(get_authenticated_user)):
    """
    Returns scored attention items across all PMS domains for the given vessel.
    Mirrors the queries in useNeedsAttention.ts but runs against the tenant DB.
    """
    _validate_vessel_access(auth, vessel_id)

    tenant_key = auth["tenant_key_alias"]
    yacht_ids = _resolve_yacht_ids(auth, vessel_id)
    supabase = get_tenant_client(tenant_key)

    items: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {
        "faults": 0, "work_orders": 0, "certificates": 0, "equipment": 0,
        "parts": 0, "hor_warnings": 0, "receiving": 0, "handover": 0,
        "shopping_list": 0,
    }

    # ── Faults: open, unresolved ─────────────────────────────────────────
    try:
        f_q = supabase.table("pms_faults").select(
            "id, title, severity, detected_at, equipment_id"
        )
        f_r = _scope_query(f_q, yacht_ids).is_("resolved_at", "null").order(
            "detected_at", desc=True
        ).limit(25).execute()

        faults = f_r.data or []
        counts["faults"] = len(faults)
        severity_scores = {"critical": 95, "high": 80, "medium": 60, "low": 40}
        for f in faults:
            base = severity_scores.get((f.get("severity") or "").lower(), 50)
            age = _days_since(f.get("detected_at"))
            time_bonus = min(20, (age or 0) * 2)
            score = min(100, base + time_bonus)
            items.append({
                "id": f"fault-{f['id']}",
                "entity_id": f["id"],
                "source": "fault",
                "severity": _severity_label(score),
                "score": score,
                "title": f.get("title") or "Unnamed Fault",
                "detail": f"FAULT · {(f.get('severity') or 'OPEN').upper()}",
                "date": f.get("detected_at"),
            })
    except Exception as e:
        logger.error(f"[Attention] Faults query failed: {e}")

    # ── Work Orders: planned or in_progress ──────────────────────────────
    try:
        wo_q = supabase.table("pms_work_orders").select(
            "id, title, priority, status, due_date, assigned_to, wo_number"
        )
        wo_r = _scope_query(wo_q, yacht_ids).in_(
            "status", ["planned", "in_progress"]
        ).order("due_date").limit(25).execute()

        work_orders = wo_r.data or []
        counts["work_orders"] = len(work_orders)
        now = datetime.now(timezone.utc)
        priority_scores = {"emergency": 95, "critical": 85, "important": 70, "routine": 40}
        for w in work_orders:
            is_overdue = False
            if w.get("due_date"):
                try:
                    due_dt = datetime.fromisoformat(w["due_date"].replace("Z", "+00:00"))
                    is_overdue = due_dt < now
                except Exception:
                    pass
            base = priority_scores.get((w.get("priority") or "").lower(), 50)
            if is_overdue:
                base = max(base, 90)
            items.append({
                "id": f"wo-{w['id']}",
                "entity_id": w["id"],
                "source": "work_order",
                "severity": "critical" if is_overdue else _severity_label(base),
                "score": base,
                "title": w.get("title") or "Work Order",
                "detail": f"W/O · {w.get('wo_number') or w['id'][:8]} · {(w.get('status') or 'planned').upper()}",
                "date": w.get("due_date"),
            })
    except Exception as e:
        logger.error(f"[Attention] Work orders query failed: {e}")

    # ── Certificates: expiring within 90 days ────────────────────────────
    try:
        cutoff = (now + timedelta(days=90)).isoformat()
        cert_q = supabase.table("pms_vessel_certificates").select(
            "id, certificate_name, expiry_date, next_survey_due, status, certificate_type"
        )
        cert_r = _scope_query(cert_q, yacht_ids).or_(
            f"expiry_date.lt.{cutoff},next_survey_due.lt.{cutoff}"
        ).order("expiry_date").limit(25).execute()

        certs = cert_r.data or []
        counts["certificates"] = len(certs)
        for c in certs:
            expiry_days = _days_until(c.get("expiry_date"))
            survey_days = _days_until(c.get("next_survey_due"))
            days_left = min(
                expiry_days if expiry_days is not None else 999,
                survey_days if survey_days is not None else 999,
            )
            if days_left <= 0:
                score = 95
            elif days_left <= 14:
                score = 85
            elif days_left <= 30:
                score = 70
            elif days_left <= 60:
                score = 55
            else:
                score = 40
            items.append({
                "id": f"cert-{c['id']}",
                "entity_id": c["id"],
                "source": "certificate",
                "severity": _severity_label(score),
                "score": score,
                "title": c.get("certificate_name") or "Certificate",
                "detail": f"CERT · {(c.get('certificate_type') or c.get('status') or 'UNKNOWN').upper()}",
                "date": c.get("expiry_date"),
                "days_remaining": days_left if days_left < 999 else None,
            })
    except Exception as e:
        logger.error(f"[Attention] Certificates query failed: {e}")

    # ── Equipment: degraded or failed ────────────────────────────────────
    try:
        eq_q = supabase.table("pms_equipment").select(
            "id, name, status, criticality, attention_flag, attention_reason"
        )
        eq_r = _scope_query(eq_q, yacht_ids).or_(
            "status.in.(degraded,failed),attention_flag.eq.true"
        ).limit(25).execute()

        equipment = eq_r.data or []
        counts["equipment"] = len(equipment)
        for e in equipment:
            is_failed = e.get("status") == "failed"
            is_critical = e.get("criticality") in ("critical", "high")
            score = 95 if is_failed else (80 if e.get("attention_flag") else (75 if is_critical else 55))
            items.append({
                "id": f"equip-{e['id']}",
                "entity_id": e["id"],
                "source": "equipment",
                "severity": "critical" if is_failed else "warning",
                "score": score,
                "title": e.get("name") or "Equipment",
                "detail": f"EQUIPMENT · {(e.get('criticality') or e.get('status') or '').upper()}",
                "date": None,
            })
    except Exception as e:
        logger.error(f"[Attention] Equipment query failed: {e}")

    # ── Parts: below minimum stock ───────────────────────────────────────
    try:
        p_q = supabase.table("pms_parts").select(
            "id, name, quantity_on_hand, minimum_quantity, part_number, is_critical"
        )
        p_r = _scope_query(p_q, yacht_ids).not_.is_(
            "minimum_quantity", "null"
        ).limit(50).execute()

        all_parts = p_r.data or []
        low_parts = [
            p for p in all_parts
            if (p.get("quantity_on_hand") or 0) <= (p.get("minimum_quantity") or 0)
        ]
        counts["parts"] = len(low_parts)
        for p in low_parts[:25]:
            is_empty = (p.get("quantity_on_hand") or 0) == 0
            is_crit = p.get("is_critical", False)
            score = 95 if (is_empty and is_crit) else (85 if is_empty else (70 if is_crit else 55))
            items.append({
                "id": f"part-{p['id']}",
                "entity_id": p["id"],
                "source": "parts",
                "severity": "critical" if is_empty else "warning",
                "score": score,
                "title": p.get("name") or "Part",
                "detail": f"PARTS · {p.get('part_number') or 'BELOW MIN STOCK'}",
                "date": None,
                "stock_level": p.get("quantity_on_hand"),
                "min_stock": p.get("minimum_quantity"),
            })
    except Exception as e:
        logger.error(f"[Attention] Parts query failed: {e}")

    # ── HoR Warnings: active, undismissed ────────────────────────────────
    try:
        hor_q = supabase.table("pms_crew_hours_warnings").select(
            "id, user_id, warning_type, severity, record_date, message"
        )
        hor_r = _scope_query(hor_q, yacht_ids).eq(
            "status", "active"
        ).eq("is_dismissed", False).order(
            "record_date", desc=True
        ).limit(25).execute()

        hor_warnings = hor_r.data or []
        counts["hor_warnings"] = len(hor_warnings)
        hor_severity_scores = {"critical": 90, "warning": 65, "info": 40}
        for h in hor_warnings:
            score = hor_severity_scores.get((h.get("severity") or "").lower(), 50)
            items.append({
                "id": f"horw-{h['id']}",
                "entity_id": h["id"],
                "source": "hor_warning",
                "severity": "critical" if h.get("severity") == "critical" else "warning",
                "score": score,
                "title": h.get("message") or h.get("warning_type") or "Rest violation",
                "detail": f"HOR · {(h.get('severity') or 'WARNING').upper()}",
                "date": h.get("record_date"),
            })
    except Exception as e:
        logger.error(f"[Attention] HoR warnings query failed: {e}")

    # ── Receiving: draft or in_review ────────────────────────────────────
    try:
        recv_q = supabase.table("pms_receiving").select(
            "id, vendor_name, status, received_date"
        )
        recv_r = _scope_query(recv_q, yacht_ids).in_(
            "status", ["draft", "in_review"]
        ).limit(25).execute()

        receiving = recv_r.data or []
        counts["receiving"] = len(receiving)
        for r in receiving:
            is_review = r.get("status") == "in_review"
            score = 70 if is_review else 40
            items.append({
                "id": f"recv-{r['id']}",
                "entity_id": r["id"],
                "source": "receiving",
                "severity": "warning" if is_review else "info",
                "score": score,
                "title": r.get("vendor_name") or "Shipment",
                "detail": f"RECEIVING · {'IN REVIEW' if is_review else 'DRAFT'}",
                "date": r.get("received_date"),
            })
    except Exception as e:
        logger.error(f"[Attention] Receiving query failed: {e}")

    # ── Handover: pending, critical or action-required ───────────────────
    try:
        hand_q = supabase.table("handover_items").select(
            "id, entity_type, summary, priority, category, created_at, is_critical, requires_action"
        )
        hand_r = _scope_query(hand_q, yacht_ids).eq(
            "status", "pending"
        ).or_(
            "is_critical.eq.true,requires_action.eq.true,priority.gte.2"
        ).order("created_at", desc=True).limit(25).execute()

        handover = hand_r.data or []
        counts["handover"] = len(handover)
        for h in handover:
            is_crit = h.get("is_critical", False)
            prio = h.get("priority") or 0
            score = 85 if is_crit else (80 if prio >= 3 else 60)
            items.append({
                "id": f"hand-{h['id']}",
                "entity_id": h["id"],
                "source": "handover",
                "severity": "critical" if is_crit else "warning",
                "score": score,
                "title": h.get("summary") or "Handover Item",
                "detail": f"HANDOVER · {'CRITICAL' if is_crit else f'P{prio}'} · {(h.get('category') or h.get('entity_type') or '').upper()}",
                "date": h.get("created_at"),
            })
    except Exception as e:
        logger.error(f"[Attention] Handover query failed: {e}")

    # ── Shopping List: critical/high urgency, not yet ordered ─────────────
    try:
        shop_q = supabase.table("pms_shopping_list_items").select(
            "id, part_name, urgency, status"
        )
        shop_r = _scope_query(shop_q, yacht_ids).in_(
            "urgency", ["critical", "high"]
        ).not_.in_(
            "status", ["ordered", "partially_fulfilled", "installed"]
        ).limit(25).execute()

        shopping = shop_r.data or []
        counts["shopping_list"] = len(shopping)
        for s in shopping:
            score = 70 if s.get("urgency") == "critical" else 50
            items.append({
                "id": f"shop-{s['id']}",
                "entity_id": s["id"],
                "source": "shopping_list",
                "severity": "warning" if s.get("urgency") == "critical" else "info",
                "score": score,
                "title": s.get("part_name") or "Item",
                "detail": f"SHOPPING · {(s.get('status') or 'CANDIDATE').upper()}",
                "date": None,
            })
    except Exception as e:
        logger.error(f"[Attention] Shopping list query failed: {e}")

    # ── Sort by score descending, return ─────────────────────────────────
    items.sort(key=lambda x: x["score"], reverse=True)

    return {
        "items": items,
        "counts": counts,
        "total": len(items),
        "vessel_id": vessel_id,
    }
