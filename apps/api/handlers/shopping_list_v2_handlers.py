"""
Shopping List V2 — Document-Level Handlers
============================================

These handlers operate on the *list document* (pms_shopping_lists), not on
individual items. The V1 per-item handlers in shopping_list_handlers.py stay
unchanged — they are still used for single-item detail actions (approve/reject
from the item lens card).

New lifecycle:
  DRAFT → SUBMITTED → HOD_APPROVED → (PURCHASE05: convert_to_po → converted_to_po)

Actions handled here:
  - create_shopping_list        All crew
  - add_item_to_list            All crew (while list is draft)
  - update_list_item            Requester (while list is draft)
  - delete_list_item            Requester / HOD (while draft or submitted)
  - submit_shopping_list        Requester (draft → submitted)
  - hod_review_list_item        HOD / Captain — approve or reject single line
  - approve_shopping_list       HOD / Captain — mark list hod_approved

PDF export lives in routes/shopping_list_pdf_route.py (inline PyMuPDF).
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Valid departments
DEPARTMENTS = ["engine", "deck", "galley", "interior", "bridge", "general"]

# Roles that can approve/reject (HOD + Captain + Manager)
HOD_ROLES = {"chief_engineer", "chief_officer", "captain", "manager"}

# All operational crew
CREW_ROLES = {"crew", "deckhand", "bosun", "eto", "chief_engineer", "chief_officer", "captain", "manager"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require(params: Dict, *keys: str) -> Optional[str]:
    """Return first missing key name, or None if all present."""
    for k in keys:
        if not params.get(k):
            return k
    return None


def _notify(db, *, yacht_id: str, user_id: str, notification_type: str,
            title: str, body: str, entity_id: str, cta_action_id: str = None,
            cta_payload: dict = None, priority: str = "normal", idem_key: str):
    """Fire-and-forget notification insert. Never raises."""
    try:
        db.table("pms_notifications").upsert({
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "user_id": user_id,
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "priority": priority,
            "entity_type": "shopping_list",
            "entity_id": entity_id,
            "cta_action_id": cta_action_id,
            "cta_payload": cta_payload or {},
            "idempotency_key": idem_key,
            "is_read": False,
            "created_at": _now(),
        }, on_conflict="yacht_id,user_id,idempotency_key").execute()
    except Exception as exc:
        logger.warning(f"[sl_v2] notification failed (non-critical): {exc}")


def _ledger(db, *, yacht_id: str, user_id: str, entity_id: str,
            event_type: str, action: str, summary: str, new_state: dict = None):
    """Fire-and-forget ledger row. Never raises."""
    try:
        db.table("ledger_events").insert({
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "event_type": event_type,
            "entity_type": "shopping_list",
            "entity_id": entity_id,
            "action": action,
            "user_id": user_id,
            "change_summary": summary,
            "new_state": new_state or {},
            "metadata": {},
            "proof_hash": "n/a",
            "event_timestamp": _now(),
            "created_at": _now(),
        }).execute()
    except Exception as exc:
        logger.warning(f"[sl_v2] ledger write failed (non-critical): {exc}")


class ShoppingListV2Handlers:

    def __init__(self, db):
        self.db = db

    # =========================================================================
    # create_shopping_list
    # =========================================================================

    async def create_shopping_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new named shopping list document (status=draft).

        Required: yacht_id, name
        Optional: department, currency (default EUR), notes
        """
        missing = _require(params, "yacht_id", "name")
        if missing:
            return {"status": "error", "error_code": "MISSING_FIELD", "message": f"{missing} is required"}

        yacht_id = params["yacht_id"]
        user_id = params.get("user_id")
        name = params["name"].strip()
        department = params.get("department", "general")
        currency = params.get("currency", "EUR")
        notes = params.get("notes")

        if not name:
            return {"status": "error", "error_code": "VALIDATION_FAILED", "message": "name cannot be empty"}

        if department not in DEPARTMENTS:
            return {"status": "error", "error_code": "VALIDATION_FAILED",
                    "message": f"department must be one of: {', '.join(DEPARTMENTS)}"}

        try:
            result = self.db.table("pms_shopping_lists").insert({
                "yacht_id": yacht_id,
                # list_number auto-set by DB trigger (SL-2026-001…)
                "name": name,
                "department": department,
                "status": "draft",
                "currency": currency,
                "notes": notes,
                "created_by": user_id,
                "estimated_total": 0,
                "created_at": _now(),
                "is_seed": False,
            }).execute()

            if not result.data:
                return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to create shopping list"}

            sl = result.data[0]
            _ledger(self.db, yacht_id=yacht_id, user_id=user_id, entity_id=sl["id"],
                    event_type="shopping_list.created", action="create_shopping_list",
                    summary=f"Shopping list '{name}' created ({sl['list_number']})",
                    new_state={"status": "draft", "name": name})

            return {
                "status": "success",
                "action": "create_shopping_list",
                "result": {
                    "shopping_list_id": sl["id"],
                    "list_number": sl["list_number"],
                    "name": name,
                    "department": department,
                    "currency": currency,
                    "status": "draft",
                },
                "message": f"Shopping list {sl['list_number']} created",
            }

        except Exception as exc:
            logger.error(f"[sl_v2] create_shopping_list failed: {exc}", exc_info=True)
            return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}

    # =========================================================================
    # add_item_to_list
    # =========================================================================

    async def add_item_to_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a line item to an existing DRAFT shopping list.

        Required: yacht_id, shopping_list_id, part_name, quantity_requested
        Optional: part_id (existing catalogue part — auto-fills part_number/unit/price),
                  part_number, unit, estimated_unit_price, preferred_supplier,
                  urgency, required_by_date, source_work_order_id, source_notes
        """
        missing = _require(params, "yacht_id", "shopping_list_id", "part_name", "quantity_requested")
        if missing:
            return {"status": "error", "error_code": "MISSING_FIELD", "message": f"{missing} is required"}

        yacht_id = params["yacht_id"]
        user_id = params.get("user_id")
        shopping_list_id = params["shopping_list_id"]

        try:
            qty = float(params["quantity_requested"])
            if qty <= 0:
                return {"status": "error", "error_code": "VALIDATION_FAILED",
                        "message": "quantity_requested must be > 0"}
        except (ValueError, TypeError):
            return {"status": "error", "error_code": "VALIDATION_FAILED",
                    "message": "quantity_requested must be a number"}

        try:
            # Verify list exists, is draft, belongs to this yacht
            sl_r = self.db.table("pms_shopping_lists").select(
                "id, status, name, list_number, currency"
            ).eq("id", shopping_list_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()

            if not sl_r or not sl_r.data:
                return {"status": "error", "error_code": "NOT_FOUND", "message": "Shopping list not found"}

            sl = sl_r.data
            if sl["status"] not in ("draft", "submitted"):
                return {"status": "error", "error_code": "INVALID_STATE",
                        "message": f"Cannot add items to a list in status '{sl['status']}'"}

            # If part_id provided, auto-fill from catalogue
            part_id = params.get("part_id")
            part_number = params.get("part_number")
            unit = params.get("unit")
            estimated_unit_price = params.get("unit_price") or params.get("estimated_unit_price")
            manufacturer = params.get("manufacturer")

            if part_id:
                p_r = self.db.table("pms_parts").select(
                    "id, name, part_number, unit, manufacturer"
                ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if p_r and p_r.data:
                    p = p_r.data
                    part_number = part_number or p.get("part_number")
                    unit = unit or p.get("unit")
                    manufacturer = manufacturer or p.get("manufacturer")

            is_candidate = part_id is None

            item_r = self.db.table("pms_shopping_list_items").insert({
                "yacht_id": yacht_id,
                "shopping_list_id": shopping_list_id,
                "part_id": part_id,
                "part_name": params["part_name"].strip(),
                "part_number": part_number,
                "manufacturer": manufacturer,
                "unit": unit,
                "quantity_requested": qty,
                "estimated_unit_price": float(estimated_unit_price) if estimated_unit_price else None,
                "preferred_supplier": params.get("preferred_supplier"),
                "urgency": params.get("urgency", "normal"),
                "required_by_date": params.get("required_by_date"),
                "source_type": params.get("source_type", "manual_add"),
                "source_work_order_id": params.get("source_work_order_id"),
                "source_notes": params.get("source_notes"),
                "is_candidate_part": is_candidate,
                "status": "candidate",
                "created_by": user_id,
                "requested_by": user_id,
                "created_at": _now(),
                "updated_at": _now(),
                "is_seed": False,
            }).execute()

            if not item_r.data:
                return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add item"}

            item = item_r.data[0]

            # Recalculate estimated_total on the list
            self._recalc_total(yacht_id, shopping_list_id)

            # Open candidate follow-up if no catalogue part
            if is_candidate:
                self._open_candidate_followup(yacht_id, item["id"], params["part_name"], user_id)

            return {
                "status": "success",
                "action": "add_item_to_list",
                "result": {
                    "item_id": item["id"],
                    "shopping_list_id": shopping_list_id,
                    "list_number": sl["list_number"],
                    "part_name": params["part_name"],
                    "quantity_requested": qty,
                    "is_candidate_part": is_candidate,
                },
                "message": f"Item added to {sl['list_number']}",
            }

        except Exception as exc:
            logger.error(f"[sl_v2] add_item_to_list failed: {exc}", exc_info=True)
            return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}

    # =========================================================================
    # update_list_item
    # =========================================================================

    async def update_list_item(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Edit a line item in a DRAFT list (qty, price, notes, supplier, urgency).
        Only the requester (or HOD) can update. Locked once list is submitted.
        """
        missing = _require(params, "yacht_id", "item_id")
        if missing:
            return {"status": "error", "error_code": "MISSING_FIELD", "message": f"{missing} is required"}

        yacht_id = params["yacht_id"]
        user_id = params.get("user_id")
        item_id = params["item_id"]

        try:
            item_r = self.db.table("pms_shopping_list_items").select(
                "id, shopping_list_id, status, created_by, part_name"
            ).eq("id", item_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()

            if not item_r or not item_r.data:
                return {"status": "error", "error_code": "NOT_FOUND", "message": "Item not found"}

            item = item_r.data
            if item["status"] not in ("candidate", "under_review"):
                return {"status": "error", "error_code": "INVALID_STATE",
                        "message": f"Cannot edit item in status '{item['status']}'"}

            # Check the parent list is still draft/submitted
            if item.get("shopping_list_id"):
                sl_r = self.db.table("pms_shopping_lists").select("status").eq(
                    "id", item["shopping_list_id"]).maybe_single().execute()
                if sl_r and sl_r.data and sl_r.data["status"] not in ("draft", "submitted"):
                    return {"status": "error", "error_code": "INVALID_STATE",
                            "message": "Cannot edit items on an approved or converted list"}

            updates: Dict[str, Any] = {"updated_by": user_id, "updated_at": _now()}

            for field in ("quantity_requested",):
                if params.get(field) is not None:
                    updates[field] = float(params[field])
            # accept unit_price (frontend name) or estimated_unit_price (DB name)
            raw_price = params.get("unit_price") or params.get("estimated_unit_price")
            if raw_price is not None:
                updates["estimated_unit_price"] = float(raw_price)

            for field in ("preferred_supplier", "urgency", "required_by_date",
                          "source_notes", "unit", "part_number"):
                if params.get(field) is not None:
                    updates[field] = params[field]

            self.db.table("pms_shopping_list_items").update(updates).eq(
                "id", item_id).eq("yacht_id", yacht_id).execute()

            if item.get("shopping_list_id"):
                self._recalc_total(yacht_id, item["shopping_list_id"])

            return {
                "status": "success",
                "action": "update_list_item",
                "result": {"item_id": item_id, "updated_fields": list(updates.keys())},
                "message": f"Item updated",
            }

        except Exception as exc:
            logger.error(f"[sl_v2] update_list_item failed: {exc}", exc_info=True)
            return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}

    # =========================================================================
    # delete_list_item
    # =========================================================================

    async def delete_list_item(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Soft-delete a line item from a DRAFT or SUBMITTED list.
        Once ordered, items are locked.
        """
        missing = _require(params, "yacht_id", "item_id")
        if missing:
            return {"status": "error", "error_code": "MISSING_FIELD", "message": f"{missing} is required"}

        yacht_id = params["yacht_id"]
        user_id = params.get("user_id")
        item_id = params["item_id"]

        try:
            item_r = self.db.table("pms_shopping_list_items").select(
                "id, shopping_list_id, status, part_name"
            ).eq("id", item_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()

            if not item_r or not item_r.data:
                return {"status": "error", "error_code": "NOT_FOUND", "message": "Item not found"}

            item = item_r.data
            if item["status"] in ("ordered", "partially_fulfilled", "fulfilled", "installed"):
                return {"status": "error", "error_code": "INVALID_STATE",
                        "message": "Cannot delete item that has been ordered or received"}

            now = _now()
            self.db.table("pms_shopping_list_items").update({
                "deleted_at": now,
                "deleted_by": user_id,
                "deletion_reason": params.get("reason", "Removed from shopping list"),
                "updated_at": now,
            }).eq("id", item_id).eq("yacht_id", yacht_id).execute()

            if item.get("shopping_list_id"):
                self._recalc_total(yacht_id, item["shopping_list_id"])

            return {
                "status": "success",
                "action": "delete_list_item",
                "result": {"item_id": item_id, "part_name": item["part_name"]},
                "message": f"'{item['part_name']}' removed from list",
            }

        except Exception as exc:
            logger.error(f"[sl_v2] delete_list_item failed: {exc}", exc_info=True)
            return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}

    # =========================================================================
    # submit_shopping_list
    # =========================================================================

    async def submit_shopping_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a DRAFT list for HOD approval.
        DRAFT → SUBMITTED. Notifies all HOD-role users on the vessel.
        Must have at least one non-deleted item.
        """
        missing = _require(params, "yacht_id", "shopping_list_id")
        if missing:
            return {"status": "error", "error_code": "MISSING_FIELD", "message": f"{missing} is required"}

        yacht_id = params["yacht_id"]
        user_id = params.get("user_id")
        shopping_list_id = params["shopping_list_id"]

        try:
            sl_r = self.db.table("pms_shopping_lists").select(
                "id, status, name, list_number, created_by, department"
            ).eq("id", shopping_list_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()

            if not sl_r or not sl_r.data:
                return {"status": "error", "error_code": "NOT_FOUND", "message": "Shopping list not found"}

            sl = sl_r.data
            if sl["status"] != "draft":
                return {"status": "error", "error_code": "INVALID_STATE",
                        "message": f"List is already '{sl['status']}' — only DRAFT lists can be submitted"}

            # Must have at least one item
            item_count_r = self.db.table("pms_shopping_list_items").select(
                "id", count="exact"
            ).eq("shopping_list_id", shopping_list_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").execute()

            count = item_count_r.count if item_count_r.count is not None else len(item_count_r.data or [])
            if count == 0:
                return {"status": "error", "error_code": "VALIDATION_FAILED",
                        "message": "Cannot submit an empty shopping list — add items first"}

            now = _now()
            self.db.table("pms_shopping_lists").update({
                "status": "submitted",
                "submitted_at": now,
                "submitted_by": user_id,
            }).eq("id", shopping_list_id).eq("yacht_id", yacht_id).execute()

            _ledger(self.db, yacht_id=yacht_id, user_id=user_id, entity_id=shopping_list_id,
                    event_type="shopping_list.submitted", action="submit_shopping_list",
                    summary=f"{sl['list_number']} submitted for HOD approval ({count} items)",
                    new_state={"status": "submitted", "item_count": count})

            # Notify all HOD-role users on this vessel
            self._notify_hods(
                yacht_id=yacht_id,
                triggered_by=user_id,
                shopping_list_id=shopping_list_id,
                list_number=sl["list_number"],
                name=sl["name"],
                item_count=count,
                idem_suffix="submitted",
            )

            return {
                "status": "success",
                "action": "submit_shopping_list",
                "result": {
                    "shopping_list_id": shopping_list_id,
                    "list_number": sl["list_number"],
                    "status": "submitted",
                    "item_count": count,
                },
                "message": f"{sl['list_number']} submitted for approval",
            }

        except Exception as exc:
            logger.error(f"[sl_v2] submit_shopping_list failed: {exc}", exc_info=True)
            return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}

    # =========================================================================
    # hod_review_list_item
    # =========================================================================

    async def hod_review_list_item(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        HOD approves or rejects a single line item on a SUBMITTED list.

        Required: yacht_id, item_id, decision ('approved' | 'rejected')
        If rejected: rejection_reason required
        If approved: quantity_approved optional (defaults to quantity_requested)

        This is the primary HOD action — replaces the old per-item approve/reject
        requiring two status transitions. HOD sees the full list and acts on each
        row in one gesture.
        """
        missing = _require(params, "yacht_id", "item_id", "decision")
        if missing:
            return {"status": "error", "error_code": "MISSING_FIELD", "message": f"{missing} is required"}

        yacht_id = params["yacht_id"]
        user_id = params.get("user_id")
        item_id = params["item_id"]
        decision = params["decision"]

        if decision not in ("approved", "rejected"):
            return {"status": "error", "error_code": "VALIDATION_FAILED",
                    "message": "decision must be 'approved' or 'rejected'"}

        if decision == "rejected" and not params.get("rejection_reason", "").strip():
            return {"status": "error", "error_code": "VALIDATION_FAILED",
                    "message": "rejection_reason is required when rejecting an item"}

        try:
            item_r = self.db.table("pms_shopping_list_items").select(
                "id, status, part_name, quantity_requested, shopping_list_id, requested_by, is_candidate_part"
            ).eq("id", item_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()

            if not item_r or not item_r.data:
                return {"status": "error", "error_code": "NOT_FOUND", "message": "Item not found"}

            item = item_r.data
            if item["status"] in ("ordered", "partially_fulfilled", "fulfilled", "installed"):
                return {"status": "error", "error_code": "INVALID_STATE",
                        "message": f"Cannot review item in status '{item['status']}'"}

            now = _now()

            if decision == "approved":
                qty_approved = float(params.get("quantity_approved") or item["quantity_requested"])
                self.db.table("pms_shopping_list_items").update({
                    "status": "approved",
                    "approved_by": user_id,
                    "approved_at": now,
                    "quantity_approved": qty_approved,
                    "approval_notes": params.get("approval_notes"),
                    "updated_by": user_id,
                    "updated_at": now,
                }).eq("id", item_id).eq("yacht_id", yacht_id).execute()

            else:  # rejected
                self.db.table("pms_shopping_list_items").update({
                    "status": "rejected",
                    "rejected_by": user_id,
                    "rejected_at": now,
                    "rejection_reason": params["rejection_reason"].strip(),
                    "rejection_notes": params.get("rejection_notes"),
                    "updated_by": user_id,
                    "updated_at": now,
                }).eq("id", item_id).eq("yacht_id", yacht_id).execute()

                # Close any open candidate follow-up
                if item.get("is_candidate_part"):
                    self._close_followup(yacht_id, item_id, item["part_name"], user_id,
                                         item.get("requested_by") or user_id, "rejected")

            # Recalc list total (rejected items don't contribute)
            if item.get("shopping_list_id"):
                self._recalc_total(yacht_id, item["shopping_list_id"])

            return {
                "status": "success",
                "action": "hod_review_list_item",
                "result": {
                    "item_id": item_id,
                    "part_name": item["part_name"],
                    "decision": decision,
                },
                "message": f"'{item['part_name']}' {decision}",
            }

        except Exception as exc:
            logger.error(f"[sl_v2] hod_review_list_item failed: {exc}", exc_info=True)
            return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}

    # =========================================================================
    # approve_shopping_list
    # =========================================================================

    async def approve_shopping_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        HOD / Captain marks the entire list as HOD_APPROVED.
        All items still in 'candidate' or 'under_review' are auto-approved
        (HOD has had the chance to reject individually via hod_review_list_item).
        SUBMITTED → HOD_APPROVED.
        Notifies Purser / Captain.
        """
        missing = _require(params, "yacht_id", "shopping_list_id")
        if missing:
            return {"status": "error", "error_code": "MISSING_FIELD", "message": f"{missing} is required"}

        yacht_id = params["yacht_id"]
        user_id = params.get("user_id")
        shopping_list_id = params["shopping_list_id"]

        try:
            sl_r = self.db.table("pms_shopping_lists").select(
                "id, status, name, list_number, submitted_by, created_by"
            ).eq("id", shopping_list_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()

            if not sl_r or not sl_r.data:
                return {"status": "error", "error_code": "NOT_FOUND", "message": "Shopping list not found"}

            sl = sl_r.data
            if sl["status"] not in ("submitted", "draft"):
                return {"status": "error", "error_code": "INVALID_STATE",
                        "message": f"List is '{sl['status']}' — only submitted lists can be approved"}

            now = _now()

            # Auto-approve any items still in candidate/under_review
            # (HOD chose not to explicitly reject them — that means approved)
            self.db.table("pms_shopping_list_items").update({
                "status": "approved",
                "approved_by": user_id,
                "approved_at": now,
                "updated_by": user_id,
                "updated_at": now,
            }).eq("shopping_list_id", shopping_list_id).eq("yacht_id", yacht_id).in_(
                "status", ["candidate", "under_review"]
            ).is_("deleted_at", "null").execute()

            # Count outcomes
            items_r = self.db.table("pms_shopping_list_items").select(
                "status", count="exact"
            ).eq("shopping_list_id", shopping_list_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").execute()

            items = items_r.data or []
            approved_count = sum(1 for i in items if i["status"] == "approved")
            rejected_count = sum(1 for i in items if i["status"] == "rejected")

            # Recalc total (only approved items)
            self._recalc_total(yacht_id, shopping_list_id)

            # Mark list approved
            self.db.table("pms_shopping_lists").update({
                "status": "hod_approved",
                "approved_by": user_id,
                "approved_at": now,
            }).eq("id", shopping_list_id).eq("yacht_id", yacht_id).execute()

            _ledger(self.db, yacht_id=yacht_id, user_id=user_id, entity_id=shopping_list_id,
                    event_type="shopping_list.hod_approved", action="approve_shopping_list",
                    summary=(f"{sl['list_number']} approved by HOD: "
                             f"{approved_count} approved, {rejected_count} rejected"),
                    new_state={"status": "hod_approved",
                               "approved_count": approved_count,
                               "rejected_count": rejected_count})

            # Notify requester + Purser/Captain-role users
            requester_id = sl.get("submitted_by") or sl.get("created_by")
            if requester_id and requester_id != user_id:
                _notify(self.db, yacht_id=yacht_id, user_id=requester_id,
                        notification_type="shopping_list.hod_approved",
                        title=f"{sl['list_number']} approved",
                        body=(f"Your shopping list '{sl['name']}' has been approved "
                              f"({approved_count} items, {rejected_count} rejected)."),
                        entity_id=shopping_list_id,
                        cta_action_id="export_shopping_list_pdf",
                        cta_payload={"shopping_list_id": shopping_list_id},
                        priority="high",
                        idem_key=f"sl_approved:{shopping_list_id}:{requester_id}")

            # Notify purser/captain to convert to PO
            self._notify_purser_captain(
                yacht_id=yacht_id,
                triggered_by=user_id,
                shopping_list_id=shopping_list_id,
                list_number=sl["list_number"],
                name=sl["name"],
                approved_count=approved_count,
            )

            return {
                "status": "success",
                "action": "approve_shopping_list",
                "result": {
                    "shopping_list_id": shopping_list_id,
                    "list_number": sl["list_number"],
                    "status": "hod_approved",
                    "approved_count": approved_count,
                    "rejected_count": rejected_count,
                },
                "message": (f"{sl['list_number']} approved — "
                            f"{approved_count} items ready for purchase order"),
            }

        except Exception as exc:
            logger.error(f"[sl_v2] approve_shopping_list failed: {exc}", exc_info=True)
            return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _recalc_total(self, yacht_id: str, shopping_list_id: str) -> None:
        """Recalculate estimated_total on the list from approved+candidate items."""
        try:
            items_r = self.db.table("pms_shopping_list_items").select(
                "quantity_requested, quantity_approved, estimated_unit_price, status"
            ).eq("shopping_list_id", shopping_list_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").execute()

            total = 0.0
            for item in (items_r.data or []):
                if item["status"] == "rejected":
                    continue
                qty = float(item.get("quantity_approved") or item.get("quantity_requested") or 0)
                price = float(item.get("estimated_unit_price") or 0)
                total += qty * price

            self.db.table("pms_shopping_lists").update({
                "estimated_total": round(total, 2),
            }).eq("id", shopping_list_id).eq("yacht_id", yacht_id).execute()

        except Exception as exc:
            logger.warning(f"[sl_v2] _recalc_total failed (non-critical): {exc}")

    def _notify_hods(self, yacht_id: str, triggered_by: str, shopping_list_id: str,
                     list_number: str, name: str, item_count: int, idem_suffix: str) -> None:
        """Notify all HOD-role users on the vessel."""
        try:
            roles_r = self.db.table("auth_users_roles").select(
                "user_id"
            ).eq("yacht_id", yacht_id).in_(
                "role", list(HOD_ROLES)
            ).eq("is_active", True).neq("user_id", triggered_by).execute()

            for row in (roles_r.data or []):
                _notify(self.db, yacht_id=yacht_id, user_id=row["user_id"],
                        notification_type="shopping_list.submitted_for_approval",
                        title=f"Shopping list needs your approval",
                        body=f"{list_number} '{name}' — {item_count} items awaiting review.",
                        entity_id=shopping_list_id,
                        cta_action_id="approve_shopping_list",
                        cta_payload={"shopping_list_id": shopping_list_id},
                        priority="normal",
                        idem_key=f"sl_{idem_suffix}:{shopping_list_id}:{row['user_id']}")
        except Exception as exc:
            logger.warning(f"[sl_v2] _notify_hods failed (non-critical): {exc}")

    def _notify_purser_captain(self, yacht_id: str, triggered_by: str,
                                shopping_list_id: str, list_number: str,
                                name: str, approved_count: int) -> None:
        """Notify purser + captain that an approved list is ready to convert to PO."""
        try:
            roles_r = self.db.table("auth_users_roles").select(
                "user_id"
            ).eq("yacht_id", yacht_id).in_(
                "role", ["purser", "captain", "manager"]
            ).eq("is_active", True).neq("user_id", triggered_by).execute()

            for row in (roles_r.data or []):
                _notify(self.db, yacht_id=yacht_id, user_id=row["user_id"],
                        notification_type="shopping_list.ready_for_po",
                        title=f"{list_number} approved — ready for PO",
                        body=(f"'{name}' approved by HOD. "
                              f"{approved_count} items ready to convert to Purchase Order."),
                        entity_id=shopping_list_id,
                        cta_action_id="convert_to_po",
                        cta_payload={"shopping_list_id": shopping_list_id},
                        priority="high",
                        idem_key=f"sl_ready_po:{shopping_list_id}:{row['user_id']}")
        except Exception as exc:
            logger.warning(f"[sl_v2] _notify_purser_captain failed (non-critical): {exc}")

    def _open_candidate_followup(self, yacht_id: str, item_id: str,
                                  part_name: str, requester_id: str) -> None:
        """Mirrors ShoppingListHandlers._open_candidate_followup for V2 items."""
        try:
            idem_base = f"sl_candidate:{item_id}"
            now = _now()
            self.db.table("ledger_events").insert({
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "event_type": "shopping_list.candidate_captured",
                "entity_type": "shopping_list",
                "entity_id": item_id,
                "action": "add_item_to_list",
                "user_id": requester_id,
                "change_summary": f"Candidate '{part_name}' captured — promote to catalogue after ordering.",
                "new_state": {"is_candidate_part": True},
                "metadata": {"requires_followup": True, "followup_target": "promote_candidate_to_part"},
                "proof_hash": "n/a",
                "event_timestamp": now,
                "created_at": now,
            }).execute()
            _notify(self.db, yacht_id=yacht_id, user_id=requester_id,
                    notification_type="shopping_list.candidate_followup",
                    title="Candidate part needs catalogue entry",
                    body=(f"'{part_name}' was added without a catalogue link. "
                          "Promote it to the Parts Catalogue after it is received."),
                    entity_id=item_id,
                    cta_action_id="promote_candidate_to_part",
                    cta_payload={"item_id": item_id},
                    idem_key=f"{idem_base}:open")
        except Exception as exc:
            logger.warning(f"[sl_v2] _open_candidate_followup failed: {exc}")

    def _close_followup(self, yacht_id: str, item_id: str, part_name: str,
                         user_id: str, requester_id: str, outcome: str) -> None:
        """Dismiss open candidate follow-up notification."""
        try:
            idem_base = f"sl_candidate:{item_id}"
            self.db.table("pms_notifications").update({
                "dismissed_at": _now(),
            }).eq("yacht_id", yacht_id).eq("idempotency_key", f"{idem_base}:open").execute()
        except Exception as exc:
            logger.warning(f"[sl_v2] _close_followup failed: {exc}")


# =============================================================================
# Factory
# =============================================================================

def get_shopping_list_v2_handlers(supabase_client) -> "ShoppingListV2Handlers":
    return ShoppingListV2Handlers(supabase_client)
