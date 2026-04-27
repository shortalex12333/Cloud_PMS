"""Warranty domain handlers — single source of truth for all warranty mutations."""

from typing import Any, Dict, List, Optional
import uuid
import logging
from datetime import datetime, timezone

from integrations.supabase import get_supabase_client

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class WarrantyHandlers:
    def __init__(self, supabase=None):
        self.supabase = supabase or get_supabase_client()

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get_approver_user_ids(self, yacht_id: str) -> List[str]:
        try:
            result = self.supabase.table("auth_users_roles").select("user_id").eq(
                "yacht_id", yacht_id
            ).in_("role", ["captain", "manager"]).execute()
            seen: set = set()
            ids: List[str] = []
            for row in (result.data or []):
                uid = row["user_id"]
                if uid not in seen:
                    seen.add(uid)
                    ids.append(uid)
            return ids
        except Exception:
            return []

    def _fetch_claim(self, warranty_id: str, yacht_id: str) -> Optional[Dict[str, Any]]:
        r = self.supabase.table("pms_warranty_claims").select("*").eq(
            "id", warranty_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()
        return r.data if r else None

    def _write_audit(self, yacht_id: str, entity_id: str, action: str,
                     user_id: Optional[str], new_values: Dict[str, Any]) -> None:
        try:
            self.supabase.table("pms_audit_log").insert({
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": "warranty",
                "entity_id": entity_id,
                "action": action,
                "user_id": user_id,
                "new_values": new_values,
                "created_at": _utcnow(),
            }).execute()
        except Exception as e:
            logger.warning("warranty audit log failed (%s): %s", action, e)

    def _notify(self, yacht_id: str, user_ids: List[str], triggered_by: Optional[str],
                notification_type: str, title: str, body: str,
                entity_id: str, priority: str = "normal",
                extra_key: str = "") -> None:
        if not user_ids:
            return
        notifs = [{
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "user_id": uid,
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "priority": priority,
            "entity_type": "warranty",
            "entity_id": entity_id,
            "triggered_by": triggered_by,
            "idempotency_key": (
                f"{notification_type}:{entity_id}:{uid}:{extra_key}"
                if extra_key else
                f"{notification_type}:{entity_id}:{uid}"
            ),
            "is_read": False,
            "created_at": _utcnow(),
        } for uid in user_ids]
        try:
            self.supabase.table("pms_notifications").upsert(
                notifs, on_conflict="yacht_id,user_id,idempotency_key"
            ).execute()
        except Exception as e:
            logger.warning("warranty notification failed (%s): %s", notification_type, e)

    def _next_claim_number(self, yacht_id: str) -> str:
        year = datetime.now(timezone.utc).year
        existing = self.supabase.table("pms_warranty_claims").select("claim_number").eq(
            "yacht_id", yacht_id
        ).like("claim_number", f"WC-{year}-%").execute()
        return f"WC-{year}-{len(existing.data or []) + 1:03d}"

    # -------------------------------------------------------------------------
    # Mutations
    # -------------------------------------------------------------------------

    async def draft_warranty_claim(
        self,
        yacht_id: str,
        user_id: Optional[str],
        title: str = "",
        description: str = "",
        equipment_id: Optional[str] = None,
        fault_id: Optional[str] = None,
        work_order_id: Optional[str] = None,
        vendor_name: Optional[str] = None,
        manufacturer: Optional[str] = None,
        warranty_expiry: Optional[str] = None,
        claimed_amount: Optional[float] = None,
        currency: Optional[str] = None,
        manufacturer_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        claim_id = str(uuid.uuid4())
        claim_number = self._next_claim_number(yacht_id)
        now = _utcnow()

        claim_data: Dict[str, Any] = {
            "id": claim_id,
            "yacht_id": yacht_id,
            "claim_number": claim_number,
            "title": title,
            "description": description,
            "status": "draft",
            "is_seed": False,
            "drafted_by": user_id,
            "drafted_at": now,
            "created_at": now,
            "updated_at": now,
        }
        for field, value in [
            ("equipment_id", equipment_id), ("fault_id", fault_id),
            ("work_order_id", work_order_id), ("vendor_name", vendor_name),
            ("manufacturer", manufacturer), ("warranty_expiry", warranty_expiry),
            ("claimed_amount", claimed_amount), ("currency", currency),
        ]:
            if value is not None:
                claim_data[field] = value

        if manufacturer_email:
            claim_data["metadata"] = {"manufacturer_email": manufacturer_email}

        self.supabase.table("pms_warranty_claims").insert(claim_data).execute()
        self._write_audit(yacht_id, claim_id, "drafted", user_id, {"status": "draft", "claim_number": claim_number})
        return {"status": "success", "claim_id": claim_id, "claim_number": claim_number}

    async def submit_warranty_claim(
        self,
        warranty_id: str,
        yacht_id: str,
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        claim = self._fetch_claim(warranty_id, yacht_id)
        if not claim:
            raise ValueError("Warranty claim not found")
        if claim.get("status") not in ("draft", "rejected"):
            raise ValueError("Claim must be in draft or rejected status to submit")

        self.supabase.table("pms_warranty_claims").update({
            "status": "submitted",
            "submitted_by": user_id,
            "submitted_at": _utcnow(),
            "updated_at": _utcnow(),
        }).eq("id", warranty_id).eq("yacht_id", yacht_id).execute()

        self._write_audit(yacht_id, warranty_id, "submitted", user_id, {"status": "submitted"})
        approver_ids = self._get_approver_user_ids(yacht_id)
        self._notify(
            yacht_id=yacht_id,
            user_ids=approver_ids,
            triggered_by=user_id,
            notification_type="warranty_submitted",
            title=f"Warranty Claim Submitted: {claim.get('title') or claim.get('claim_number', '')}",
            body=f"Claim {claim.get('claim_number', '')} requires your review and approval.",
            entity_id=warranty_id,
        )
        return {"status": "success", "claim_id": warranty_id, "new_status": "submitted"}

    async def approve_warranty_claim(
        self,
        warranty_id: str,
        yacht_id: str,
        user_id: Optional[str],
        approved_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        claim = self._fetch_claim(warranty_id, yacht_id)
        if not claim:
            raise ValueError("Warranty claim not found")
        if claim.get("status") != "submitted":
            raise ValueError("Claim must be submitted to approve")

        update: Dict[str, Any] = {
            "status": "approved",
            "approved_by": user_id,
            "approved_at": _utcnow(),
            "updated_at": _utcnow(),
        }
        if approved_amount is not None:
            update["approved_amount"] = approved_amount
        self.supabase.table("pms_warranty_claims").update(update).eq(
            "id", warranty_id
        ).eq("yacht_id", yacht_id).execute()

        self._write_audit(yacht_id, warranty_id, "approved", user_id, {"status": "approved"})
        recipients = list({claim.get("drafted_by"), claim.get("submitted_by")} - {None, user_id})
        self._notify(
            yacht_id=yacht_id,
            user_ids=recipients,
            triggered_by=user_id,
            notification_type="warranty_approved",
            title="Warranty Claim Approved",
            body=f"Claim {claim.get('claim_number', '')} has been approved.",
            entity_id=warranty_id,
        )
        return {"status": "success", "claim_id": warranty_id, "new_status": "approved"}

    async def reject_warranty_claim(
        self,
        warranty_id: str,
        yacht_id: str,
        user_id: Optional[str],
        rejection_reason: str = "",
    ) -> Dict[str, Any]:
        claim = self._fetch_claim(warranty_id, yacht_id)
        if not claim:
            raise ValueError("Warranty claim not found")
        if claim.get("status") != "submitted":
            raise ValueError("Claim must be submitted to reject")

        self.supabase.table("pms_warranty_claims").update({
            "status": "rejected",
            "rejection_reason": rejection_reason,
            "rejected_by": user_id,
            "rejected_at": _utcnow(),
            "updated_at": _utcnow(),
        }).eq("id", warranty_id).eq("yacht_id", yacht_id).execute()

        self._write_audit(yacht_id, warranty_id, "rejected", user_id, {"status": "rejected"})
        recipients = list({claim.get("drafted_by"), claim.get("submitted_by")} - {None, user_id})
        self._notify(
            yacht_id=yacht_id,
            user_ids=recipients,
            triggered_by=user_id,
            notification_type="warranty_rejected",
            title="Warranty Claim Rejected",
            body=f"Claim {claim.get('claim_number', '')} has been rejected. Reason: {rejection_reason}",
            entity_id=warranty_id,
            priority="high",
        )
        return {"status": "success", "claim_id": warranty_id, "new_status": "rejected"}

    async def close_warranty_claim(
        self,
        warranty_id: str,
        yacht_id: str,
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        claim = self._fetch_claim(warranty_id, yacht_id)
        if not claim:
            raise ValueError("Warranty claim not found")
        if claim.get("status") != "approved":
            raise ValueError("Claim must be approved to close")

        self.supabase.table("pms_warranty_claims").update({
            "status": "closed",
            "updated_at": _utcnow(),
        }).eq("id", warranty_id).eq("yacht_id", yacht_id).execute()

        self._write_audit(yacht_id, warranty_id, "closed", user_id, {"status": "closed"})
        recipients = list({claim.get("drafted_by"), claim.get("submitted_by")} - {None, user_id})
        self._notify(
            yacht_id=yacht_id,
            user_ids=recipients,
            triggered_by=user_id,
            notification_type="warranty_closed",
            title="Warranty Claim Closed",
            body=f"Claim {claim.get('claim_number', '')} has been closed.",
            entity_id=warranty_id,
        )
        return {"status": "success", "claim_id": warranty_id, "new_status": "closed"}

    async def compose_warranty_email(
        self,
        warranty_id: str,
        yacht_id: str,
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        claim = self._fetch_claim(warranty_id, yacht_id)
        if not claim:
            raise ValueError("Warranty claim not found")

        meta = claim.get("metadata") or {}
        to_address = meta.get("manufacturer_email") or claim.get("vendor_name") or "Supplier"
        salutation = claim.get("vendor_name") or claim.get("manufacturer") or "Sir/Madam"
        drafted_date = (claim.get("drafted_at") or "")[:10] or "N/A"

        email_draft = {
            "subject": f"Warranty Claim {claim['claim_number']} — {claim.get('title', '')}",
            "to": to_address,
            "body": (
                f"Dear {salutation},\n\n"
                f"We write regarding warranty claim {claim['claim_number']} filed on {drafted_date}.\n\n"
                f"Claim Details:\n"
                f"- Title: {claim.get('title', '')}\n"
                f"- Claimed Amount: {claim.get('currency', 'USD')} {claim.get('claimed_amount', 0)}\n\n"
                f"Description:\n{claim.get('description', '')}\n\n"
                f"Please confirm receipt and advise on the warranty assessment process.\n\nKind regards"
            ),
            "composed_at": _utcnow(),
            "composed_by": user_id,
        }
        self.supabase.table("pms_warranty_claims").update({
            "email_draft": email_draft,
            "updated_at": _utcnow(),
        }).eq("id", warranty_id).eq("yacht_id", yacht_id).execute()
        self._write_audit(yacht_id, warranty_id, "email_composed", user_id, {"email_draft": True})
        return {"status": "success", "email_draft": email_draft}

    async def view_warranty_claim(
        self,
        warranty_id: str,
        yacht_id: str,
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        claim = self._fetch_claim(warranty_id, yacht_id)
        if not claim:
            raise ValueError("Warranty claim not found")
        return {"status": "success", "claim": claim}

    async def add_warranty_note(
        self,
        warranty_id: str,
        yacht_id: str,
        user_id: Optional[str],
        note_text: str,
    ) -> Dict[str, Any]:
        if not note_text:
            raise ValueError("note_text is required")
        note_id = str(uuid.uuid4())
        now = _utcnow()
        self.supabase.table("pms_notes").insert({
            "id": note_id,
            "yacht_id": yacht_id,
            "warranty_id": warranty_id,
            "text": note_text,
            "note_type": "observation",
            "created_by": user_id,
            "created_by_role": "",
            "created_at": now,
            "updated_at": now,
        }).execute()
        self._write_audit(yacht_id, warranty_id, "note_added", user_id, {"note_id": note_id})
        result = {"status": "success", "note_id": note_id, "created_at": now}
        claim_r = self.supabase.table("pms_warranty_claims").select(
            "drafted_by, submitted_by, approved_by, claim_number"
        ).eq("id", warranty_id).eq("yacht_id", yacht_id).limit(1).execute()
        claim = claim_r.data[0] if claim_r.data else {}
        recipients = list(
            {claim.get("drafted_by"), claim.get("submitted_by"), claim.get("approved_by")}
            - {None, user_id}
        )
        self._notify(
            yacht_id=yacht_id,
            user_ids=recipients,
            triggered_by=user_id,
            notification_type="warranty_note_added",
            title="Note Added to Warranty Claim",
            body=f"A new note was added to claim {claim.get('claim_number', '')}.",
            entity_id=warranty_id,
            priority="low",
            extra_key=note_id,
        )
        return result
