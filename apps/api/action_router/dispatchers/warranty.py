"""Warranty domain action handlers."""

from typing import Dict, Any
import logging
from datetime import datetime
from integrations.supabase import get_supabase_client
from .shared import add_note

logger = logging.getLogger(__name__)


def _get_approver_user_ids(supabase, yacht_id: str) -> list:
    try:
        result = supabase.table("auth_users_roles").select("user_id").eq(
            "yacht_id", yacht_id
        ).in_("role", ["captain", "manager"]).execute()
        seen: set = set()
        ids = []
        for row in (result.data or []):
            uid = row["user_id"]
            if uid not in seen:
                seen.add(uid)
                ids.append(uid)
        return ids
    except Exception:
        return []


async def _draft_warranty_claim(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    yacht_id = params["yacht_id"]
    user_id = params.get("user_id")

    claim_id = str(uuid_lib.uuid4())
    year = datetime.utcnow().year
    existing = supabase.table("pms_warranty_claims").select("claim_number").eq(
        "yacht_id", yacht_id
    ).like("claim_number", f"WC-{year}-%").execute()
    next_num = len(existing.data or []) + 1
    claim_number = f"WC-{year}-{next_num:03d}"

    claim_data = {
        "id": claim_id,
        "yacht_id": yacht_id,
        "claim_number": claim_number,
        "title": params.get("title", ""),
        "description": params.get("description", ""),
        "status": "draft",
        "is_seed": False,
        "drafted_by": user_id,
        "drafted_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    for field in ("equipment_id", "fault_id", "work_order_id", "vendor_name",
                  "manufacturer", "warranty_expiry", "claimed_amount", "currency"):
        if params.get(field) is not None:
            claim_data[field] = params[field]
    metadata: dict = {}
    if params.get("manufacturer_email"):
        metadata["manufacturer_email"] = params["manufacturer_email"]
    if metadata:
        claim_data["metadata"] = metadata
    supabase.table("pms_warranty_claims").insert(claim_data).execute()
    return {"status": "success", "claim_id": claim_id, "claim_number": claim_number}


async def _submit_warranty_claim(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    warranty_id = params.get("warranty_id") or params.get("claim_id") or params.get("entity_id")
    user_id = params.get("user_id")
    yacht_id = params["yacht_id"]

    r = supabase.table("pms_warranty_claims").select("*").eq("id", warranty_id).eq("yacht_id", yacht_id).maybe_single().execute()
    claim = r.data if r else None
    if not claim:
        return {"status": "error", "message": "Warranty claim not found"}
    if claim.get("status") not in ("draft", "rejected"):
        return {"status": "error", "message": "Claim must be in draft or rejected status to submit"}

    supabase.table("pms_warranty_claims").update({
        "status": "submitted",
        "submitted_by": user_id,
        "submitted_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", warranty_id).eq("yacht_id", yacht_id).execute()

    try:
        supabase.table("pms_audit_log").insert({
            "id": str(uuid_lib.uuid4()),
            "yacht_id": yacht_id,
            "entity_type": "warranty",
            "entity_id": warranty_id,
            "action": "submitted",
            "user_id": user_id,
            "new_values": {"status": "submitted"},
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass

    try:
        approver_ids = _get_approver_user_ids(supabase, yacht_id)
        _notifs = [{
            "id": str(uuid_lib.uuid4()),
            "yacht_id": yacht_id,
            "user_id": _uid,
            "notification_type": "warranty_submitted",
            "title": f"Warranty Claim Submitted: {claim.get('title') or claim.get('claim_number', '')}",
            "body": f"Claim {claim.get('claim_number', '')} requires your review and approval.",
            "priority": "normal",
            "entity_type": "warranty",
            "entity_id": warranty_id,
            "triggered_by": user_id,
            "idempotency_key": f"warranty_submitted:{warranty_id}:{_uid}",
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
        } for _uid in approver_ids]
        if _notifs:
            supabase.table("pms_notifications").upsert(_notifs, on_conflict="yacht_id,user_id,idempotency_key").execute()
    except Exception:
        pass

    return {"status": "success", "claim_id": warranty_id, "new_status": "submitted"}


async def _approve_warranty_claim(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    warranty_id = params.get("warranty_id") or params.get("claim_id") or params.get("entity_id")
    user_id = params.get("user_id")
    yacht_id = params["yacht_id"]
    approved_amount = params.get("approved_amount")

    r = supabase.table("pms_warranty_claims").select("*").eq("id", warranty_id).eq("yacht_id", yacht_id).maybe_single().execute()
    claim = r.data if r else None
    if not claim:
        return {"status": "error", "message": "Warranty claim not found"}
    if claim.get("status") != "submitted":
        return {"status": "error", "message": "Claim must be submitted to approve"}

    update_data: Dict[str, Any] = {
        "status": "approved",
        "approved_by": user_id,
        "approved_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    if approved_amount is not None:
        update_data["approved_amount"] = approved_amount
    supabase.table("pms_warranty_claims").update(update_data).eq("id", warranty_id).eq("yacht_id", yacht_id).execute()

    try:
        supabase.table("pms_audit_log").insert({
            "id": str(uuid_lib.uuid4()),
            "yacht_id": yacht_id,
            "entity_type": "warranty",
            "entity_id": warranty_id,
            "action": "approved",
            "user_id": user_id,
            "new_values": {"status": "approved"},
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass

    for _uid in list({claim.get("drafted_by"), claim.get("submitted_by")} - {None, user_id}):
        try:
            supabase.table("pms_notifications").upsert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "user_id": _uid,
                "notification_type": "warranty_approved",
                "title": "Warranty Claim Approved",
                "body": f"Claim {claim.get('claim_number', '')} has been approved.",
                "priority": "normal",
                "entity_type": "warranty",
                "entity_id": warranty_id,
                "triggered_by": user_id,
                "idempotency_key": f"warranty_approved:{warranty_id}:{_uid}",
                "is_read": False,
                "created_at": datetime.utcnow().isoformat(),
            }, on_conflict="yacht_id,user_id,idempotency_key").execute()
        except Exception:
            pass

    return {"status": "success", "claim_id": warranty_id, "new_status": "approved"}


async def _reject_warranty_claim(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    warranty_id = params.get("warranty_id") or params.get("claim_id") or params.get("entity_id")
    user_id = params.get("user_id")
    yacht_id = params["yacht_id"]
    rejection_reason = params.get("rejection_reason", "")

    r = supabase.table("pms_warranty_claims").select("*").eq("id", warranty_id).eq("yacht_id", yacht_id).maybe_single().execute()
    claim = r.data if r else None
    if not claim:
        return {"status": "error", "message": "Warranty claim not found"}
    if claim.get("status") != "submitted":
        return {"status": "error", "message": "Claim must be submitted to reject"}

    supabase.table("pms_warranty_claims").update({
        "status": "rejected",
        "rejection_reason": rejection_reason,
        "rejected_by": user_id,
        "rejected_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", warranty_id).eq("yacht_id", yacht_id).execute()

    try:
        supabase.table("pms_audit_log").insert({
            "id": str(uuid_lib.uuid4()), "yacht_id": yacht_id, "entity_type": "warranty",
            "entity_id": warranty_id, "action": "rejected", "user_id": user_id,
            "new_values": {"status": "rejected"}, "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass

    for _uid in list({claim.get("drafted_by"), claim.get("submitted_by")} - {None, user_id}):
        try:
            supabase.table("pms_notifications").upsert({
                "id": str(uuid_lib.uuid4()), "yacht_id": yacht_id, "user_id": _uid,
                "notification_type": "warranty_rejected", "title": "Warranty Claim Rejected",
                "body": f"Claim {claim.get('claim_number', '')} has been rejected. Reason: {rejection_reason}",
                "priority": "high", "entity_type": "warranty", "entity_id": warranty_id,
                "triggered_by": user_id,
                "idempotency_key": f"warranty_rejected:{warranty_id}:{_uid}",
                "is_read": False, "created_at": datetime.utcnow().isoformat(),
            }, on_conflict="yacht_id,user_id,idempotency_key").execute()
        except Exception:
            pass

    return {"status": "success", "claim_id": warranty_id, "new_status": "rejected"}


async def _close_warranty_claim(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    warranty_id = params.get("warranty_id") or params.get("claim_id") or params.get("entity_id")
    user_id = params.get("user_id")
    yacht_id = params["yacht_id"]

    r = supabase.table("pms_warranty_claims").select("status, drafted_by, submitted_by, claim_number").eq(
        "id", warranty_id
    ).eq("yacht_id", yacht_id).maybe_single().execute()
    claim = r.data if r else None
    if not claim:
        return {"status": "error", "message": "Warranty claim not found"}
    if claim.get("status") != "approved":
        return {"status": "error", "message": "Claim must be approved to close"}

    supabase.table("pms_warranty_claims").update({
        "status": "closed", "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", warranty_id).eq("yacht_id", yacht_id).execute()

    try:
        supabase.table("pms_audit_log").insert({
            "id": str(uuid_lib.uuid4()), "yacht_id": yacht_id, "entity_type": "warranty",
            "entity_id": warranty_id, "action": "closed", "user_id": user_id,
            "new_values": {"status": "closed"}, "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass

    try:
        _recipients = list({claim.get("drafted_by"), claim.get("submitted_by")} - {None, user_id})
        _notifs = [{
            "id": str(uuid_lib.uuid4()), "yacht_id": yacht_id, "user_id": _uid,
            "notification_type": "warranty_closed", "title": "Warranty Claim Closed",
            "body": f"Claim {claim.get('claim_number', '')} has been closed.",
            "priority": "normal", "entity_type": "warranty", "entity_id": warranty_id,
            "triggered_by": user_id, "idempotency_key": f"warranty_closed:{warranty_id}:{_uid}",
            "is_read": False, "created_at": datetime.utcnow().isoformat(),
        } for _uid in _recipients]
        if _notifs:
            supabase.table("pms_notifications").upsert(_notifs, on_conflict="yacht_id,user_id,idempotency_key").execute()
    except Exception:
        pass

    return {"status": "success", "claim_id": warranty_id, "new_status": "closed"}


async def _compose_warranty_email(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    warranty_id = params.get("warranty_id") or params.get("claim_id") or params.get("entity_id")
    yacht_id = params["yacht_id"]

    r = supabase.table("pms_warranty_claims").select("*").eq("id", warranty_id).eq("yacht_id", yacht_id).maybe_single().execute()
    claim = r.data if r else None
    if not claim:
        return {"status": "error", "message": "Warranty claim not found"}

    drafted_date = (claim.get("drafted_at") or "")[:10] or "N/A"
    _meta = claim.get("metadata") or {}
    _to_address = _meta.get("manufacturer_email") or claim.get("vendor_name") or "Supplier"
    _salutation = claim.get("vendor_name") or claim.get("manufacturer") or "Sir/Madam"
    email_draft = {
        "subject": f"Warranty Claim {claim['claim_number']} — {claim.get('title', '')}",
        "to": _to_address,
        "body": f"Dear {_salutation},\n\nWe write regarding warranty claim {claim['claim_number']} filed on {drafted_date}.\n\nClaim Details:\n- Title: {claim.get('title', '')}\n- Claimed Amount: {claim.get('currency', 'USD')} {claim.get('claimed_amount', 0)}\n\nDescription:\n{claim.get('description', '')}\n\nPlease confirm receipt and advise on the warranty assessment process.\n\nKind regards",
        "composed_at": datetime.utcnow().isoformat(),
        "composed_by": params.get("user_id"),
    }

    supabase.table("pms_warranty_claims").update({
        "email_draft": email_draft, "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", warranty_id).eq("yacht_id", yacht_id).execute()

    return {"status": "success", "email_draft": email_draft}


async def _add_warranty_note_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    result = await add_note(params)
    if result.get("status") == "success":
        try:
            supabase = get_supabase_client()
            warranty_id = params.get("warranty_id") or params.get("entity_id")
            yacht_id = params["yacht_id"]
            user_id = params.get("user_id")
            r = supabase.table("pms_warranty_claims").select("drafted_by, submitted_by, approved_by, claim_number").eq(
                "id", warranty_id
            ).eq("yacht_id", yacht_id).limit(1).execute()
            claim = r.data[0] if r.data else {}
            _recipients = list({claim.get("drafted_by"), claim.get("submitted_by"), claim.get("approved_by")} - {None, user_id})
            _notifs = [{
                "id": str(uuid_lib.uuid4()), "yacht_id": yacht_id, "user_id": _uid,
                "notification_type": "warranty_note_added", "title": "Note Added to Warranty Claim",
                "body": f"A new note was added to claim {claim.get('claim_number', '')}.",
                "priority": "low", "entity_type": "warranty", "entity_id": warranty_id,
                "triggered_by": user_id,
                "idempotency_key": f"warranty_note:{warranty_id}:{_uid}:{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                "is_read": False, "created_at": datetime.utcnow().isoformat(),
            } for _uid in _recipients]
            if _notifs:
                supabase.table("pms_notifications").upsert(_notifs, on_conflict="yacht_id,user_id,idempotency_key").execute()
        except Exception:
            pass
    return result


HANDLERS: Dict[str, Any] = {
    "draft_warranty_claim": _draft_warranty_claim,
    "file_warranty_claim": _draft_warranty_claim,
    "submit_warranty_claim": _submit_warranty_claim,
    "approve_warranty_claim": _approve_warranty_claim,
    "reject_warranty_claim": _reject_warranty_claim,
    "close_warranty_claim": _close_warranty_claim,
    "compose_warranty_email": _compose_warranty_email,
    "add_warranty_note": _add_warranty_note_handler,
    "archive_warranty": None,  # soft_delete in index.py
    "void_warranty": None,
}
