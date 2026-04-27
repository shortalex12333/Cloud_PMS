"""
Shopping List Domain Handlers
==============================

Single source of truth for all shopping list domain actions.
All 21 actions resolve in 2 hops: routes/handlers/__init__.py → this file.

V1 (per-item) actions operate on pms_shopping_list_items directly.
V2 (list-document) actions operate on pms_shopping_lists documents.

Phase 4 calling convention: (payload, context, yacht_id, user_id, user_context, db_client) -> dict
"""

import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import HTTPException
from actions.action_response_schema import ResponseBuilder, AvailableAction
from handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

SOURCE_TYPES = [
    "inventory_low", "inventory_oos", "work_order_usage",
    "receiving_missing", "receiving_damaged", "manual_add"
]

URGENCY_LEVELS = ["low", "normal", "high", "critical"]

DEPARTMENTS = ["engine", "deck", "galley", "interior", "bridge", "general"]

HOD_ROLES = {"chief_engineer", "chief_officer", "captain", "manager"}

_DELETE_ITEM_ROLES = ["chief_engineer", "chief_officer", "captain", "manager"]
_MARK_ORDERED_ROLES = ["chief_engineer", "captain", "manager"]

# Statuses that lock an item against deletion or modification
_LOCKED_STATUSES = ("ordered", "partially_fulfilled", "fulfilled", "installed")


# =============================================================================
# MODULE-LEVEL HELPERS — shared by both V1 and V2 classes
# =============================================================================

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
        logger.warning(f"[shopping] notification failed (non-critical): {exc}")


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
        logger.warning(f"[shopping] ledger write failed (non-critical): {exc}")


def _open_candidate_followup(db, *, yacht_id: str, item_id: str,
                              part_name: str, requester_id: str, action: str) -> None:
    """Write ledger + notification when a candidate part item is created."""
    try:
        idem_base = f"sl_candidate:{item_id}"
        now = _now()
        db.table("ledger_events").insert({
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "event_type": "shopping_list.candidate_captured",
            "entity_type": "shopping_list",
            "entity_id": item_id,
            "action": action,
            "user_id": requester_id,
            "change_summary": f"Candidate '{part_name}' captured — promote to catalogue after ordering.",
            "new_state": {"is_candidate_part": True},
            "metadata": {"requires_followup": True, "followup_target": "promote_candidate_to_part"},
            "proof_hash": "n/a",
            "event_timestamp": now,
            "created_at": now,
        }).execute()
        _notify(db, yacht_id=yacht_id, user_id=requester_id,
                notification_type="shopping_list.candidate_followup",
                title="Candidate part needs catalogue entry",
                body=(f"'{part_name}' was added without a catalogue link. "
                      "Promote it to the Parts Catalogue after it is received."),
                entity_id=item_id,
                cta_action_id="promote_candidate_to_part",
                cta_payload={"item_id": item_id},
                idem_key=f"{idem_base}:open")
    except Exception as exc:
        logger.warning(f"[shopping] _open_candidate_followup failed (non-critical): {exc}")


def _close_candidate_followup(db, *, yacht_id: str, item_id: str, part_name: str,
                               user_id: str, requester_id: str, outcome: str) -> None:
    """Dismiss open candidate follow-up and notify requester of outcome."""
    try:
        idem_base = f"sl_candidate:{item_id}"
        now = _now()
        db.table("ledger_events").insert({
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "event_type": f"shopping_list.candidate_{outcome}",
            "entity_type": "shopping_list",
            "entity_id": item_id,
            "action": "promote_candidate_to_part" if outcome == "promoted" else "reject_shopping_list_item",
            "user_id": user_id,
            "change_summary": f"Candidate '{part_name}' {outcome} — follow-up closed.",
            "new_state": {"requires_followup": False, "outcome": outcome},
            "metadata": {"requires_followup": False},
            "proof_hash": "n/a",
            "event_timestamp": now,
            "created_at": now,
        }).execute()
        db.table("pms_notifications").update({
            "dismissed_at": now,
        }).eq("yacht_id", yacht_id).eq("idempotency_key", f"{idem_base}:open").execute()
        if requester_id:
            title = ("Part promoted to catalogue" if outcome == "promoted"
                     else "Shopping list item rejected")
            body = (f"'{part_name}' has been added to the Parts Catalogue." if outcome == "promoted"
                    else f"'{part_name}' was rejected from the shopping list.")
            _notify(db, yacht_id=yacht_id, user_id=requester_id,
                    notification_type=f"shopping_list.candidate_{outcome}",
                    title=title, body=body,
                    entity_id=item_id,
                    idem_key=f"{idem_base}:{outcome}")
    except Exception as exc:
        logger.warning(f"[shopping] _close_candidate_followup failed (non-critical): {exc}")


# =============================================================================
# V1 — PER-ITEM HANDLERS (pms_shopping_list_items)
# Internal implementation class. Not called directly by the router.
# =============================================================================

class ShoppingListHandlers:
    """
    Shopping List V1 per-item handlers.

    CRITICAL PATTERNS:
    1. Yacht Isolation: EVERY query MUST filter by yacht_id
    2. HoD Gating: approve/reject require is_hod() check
    3. Audit Signature: {} for non-signed actions
    4. Error Mapping: 4xx for client errors, NEVER 500
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def create_shopping_list_item(
        self,
        entity_id: str,
        yacht_id: str,
        params: Dict
    ) -> Dict:
        builder = ResponseBuilder(
            "create_shopping_list_item",
            entity_id,
            "shopping_list_item",
            yacht_id
        )

        try:
            user_id = params.get("user_id")
            if not user_id:
                builder.set_error("UNAUTHORIZED", "User not authenticated", 401)
                return builder.build()

            user_result = self.db.table("auth_users_profiles").select(
                "id, name"
            ).eq("id", user_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not user_result or not user_result.data:
                logger.warning(f"Yacht isolation breach attempt: user {user_id} != yacht {yacht_id}")
                builder.set_error("FORBIDDEN", "Access denied", 403)
                return builder.build()

            part_name = params.get("part_name", "").strip()
            if not part_name:
                builder.set_error("VALIDATION_FAILED", "part_name is required", 400)
                return builder.build()

            try:
                quantity_requested = float(params.get("quantity_requested", 0))
                if quantity_requested <= 0:
                    builder.set_error("VALIDATION_FAILED", "quantity_requested must be greater than 0", 400)
                    return builder.build()
            except (ValueError, TypeError):
                builder.set_error("VALIDATION_FAILED", "quantity_requested must be a valid number", 400)
                return builder.build()

            source_type = params.get("source_type", "manual_add")
            if source_type not in SOURCE_TYPES:
                builder.set_error(
                    "VALIDATION_FAILED",
                    f"source_type must be one of: {', '.join(SOURCE_TYPES)}",
                    400
                )
                return builder.build()

            urgency = params.get("urgency")
            if urgency and urgency not in URGENCY_LEVELS:
                builder.set_error(
                    "VALIDATION_FAILED",
                    f"urgency must be one of: {', '.join(URGENCY_LEVELS)}",
                    400
                )
                return builder.build()

            part_id = params.get("part_id")
            part_number = params.get("part_number")
            manufacturer = params.get("manufacturer")
            is_candidate_part = True

            if part_id:
                part_result = self.db.table("pms_parts").select(
                    "id, name, part_number, manufacturer"
                ).eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()

                if not part_result or not part_result.data or len(part_result.data) == 0:
                    builder.set_error("NOT_FOUND", f"Part not found: {part_id}")
                    return builder.build()

                part = part_result.data[0]
                part_name = part_name or part.get("name")
                part_number = part_number or part.get("part_number")
                manufacturer = manufacturer or part.get("manufacturer")
                is_candidate_part = False

            rpc_params = {
                "p_user_id": user_id,
                "p_yacht_id": yacht_id,
                "p_part_name": part_name,
                "p_quantity_requested": float(quantity_requested),
                "p_source_type": source_type,
                "p_urgency": urgency,
                "p_part_id": part_id,
                "p_part_number": part_number,
                "p_manufacturer": manufacturer,
                "p_requested_by": user_id,
                "p_source_notes": params.get("source_notes"),
            }

            insert_result = None
            rpc_returned_204 = False
            try:
                insert_result = self.db.rpc("rpc_insert_shopping_list_item", rpc_params).execute()
            except Exception as e:
                error_str = str(e).lower()
                if "204" in error_str or "missing response" in error_str or "postgrest" in error_str:
                    logger.info(f"[create_shopping_list_item] RPC returned 204 — insert succeeded, falling back to SELECT")
                    rpc_returned_204 = True
                else:
                    logger.error(f"Failed to insert shopping list item via RPC: {e}", exc_info=True)
                    builder.set_error("EXECUTION_FAILED", f"Failed to create shopping list item: {str(e)}", 500)
                    return builder.build()

            if rpc_returned_204 or not insert_result or not insert_result.data or len(insert_result.data) == 0:
                fallback = self.db.table("pms_shopping_list_items").select("id").eq(
                    "yacht_id", yacht_id
                ).eq("part_name", part_name).eq("requested_by", user_id).order(
                    "created_at", desc=True
                ).limit(1).execute()
                if fallback.data and len(fallback.data) > 0:
                    new_item_id = fallback.data[0]["id"]
                else:
                    builder.set_error("EXECUTION_FAILED", "Failed to create shopping list item", 500)
                    return builder.build()
            else:
                new_item_id = insert_result.data[0]["id"]

            now = datetime.now(timezone.utc).isoformat()

            try:
                self.db.table("pms_audit_log").insert({
                    "id": str(uuid.uuid4()),
                    "yacht_id": yacht_id,
                    "entity_type": "shopping_list_item",
                    "entity_id": new_item_id,
                    "action": "create_shopping_list_item",
                    "user_id": user_id,
                    "old_values": None,
                    "new_values": {
                        "part_name": part_name,
                        "quantity_requested": quantity_requested,
                        "status": "candidate",
                        "source_type": source_type,
                        "is_candidate_part": is_candidate_part,
                    },
                    "signature": {},
                    "metadata": {"source": "shopping_list_lens"},
                    "created_at": now,
                }).execute()
            except Exception as audit_err:
                logger.warning(f"Audit log insert failed (non-critical): {audit_err}")

            if is_candidate_part:
                _open_candidate_followup(
                    self.db,
                    yacht_id=yacht_id,
                    item_id=new_item_id,
                    part_name=part_name,
                    requester_id=user_id,
                    action="create_shopping_list_item",
                )

            builder.set_data({
                "shopping_list_item_id": new_item_id,
                "part_name": part_name,
                "quantity_requested": quantity_requested,
                "status": "candidate",
                "is_candidate_part": is_candidate_part,
                "created_at": now,
            })

            builder.add_available_action(AvailableAction(
                action_id="view_shopping_list_history",
                label="View History",
                variant="READ",
                icon="history"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"create_shopping_list_item failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e), 500)
            return builder.build()

    async def approve_shopping_list_item(
        self,
        entity_id: str,
        yacht_id: str,
        params: Dict
    ) -> Dict:
        builder = ResponseBuilder(
            "approve_shopping_list_item",
            entity_id,
            "shopping_list_item",
            yacht_id
        )

        try:
            user_id = params.get("user_id")
            if not user_id:
                builder.set_error("UNAUTHORIZED", "User not authenticated", 401)
                return builder.build()

            user_result = self.db.table("auth_users_profiles").select(
                "id, name, yacht_id"
            ).eq("id", user_id).maybe_single().execute()

            if not user_result or not user_result.data or user_result.data["yacht_id"] != yacht_id:
                logger.warning(f"Yacht isolation breach attempt: user {user_id} != yacht {yacht_id}")
                builder.set_error("FORBIDDEN", "Access denied", 403)
                return builder.build()

            is_hod_result = self.db.rpc("is_hod", {"p_user_id": user_id, "p_yacht_id": yacht_id}).execute()

            if not is_hod_result or not is_hod_result.data:
                logger.warning(f"Non-HoD attempted approve: user={user_id}, yacht={yacht_id}")
                builder.set_error(
                    "FORBIDDEN",
                    "Only HoD (chief engineer, chief officer, captain, manager) can approve shopping list items",
                    403
                )
                return builder.build()

            item_result = self.db.table("pms_shopping_list_items").select(
                "id, part_name, quantity_requested, status, created_by, rejected_at"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not item_result or not item_result.data:
                builder.set_error("NOT_FOUND", f"Shopping list item not found: {entity_id}")
                return builder.build()

            item = item_result.data

            if item.get("rejected_at"):
                builder.set_error("INVALID_STATE", "Cannot approve a rejected item", 400)
                return builder.build()

            if item["status"] not in ("candidate", "under_review"):
                builder.set_error(
                    "INVALID_STATE",
                    f"Cannot approve item with status '{item['status']}'. Expected: candidate or under_review.",
                    400
                )
                return builder.build()

            try:
                quantity_approved = float(params.get("quantity_approved", 0))
                if quantity_approved <= 0:
                    builder.set_error("VALIDATION_FAILED", "quantity_approved must be greater than 0", 400)
                    return builder.build()
            except (ValueError, TypeError):
                builder.set_error("VALIDATION_FAILED", "quantity_approved must be a valid number", 400)
                return builder.build()

            approval_notes = params.get("approval_notes")
            now = datetime.now(timezone.utc).isoformat()

            if item["status"] == "candidate":
                intermediate_result = self.db.table("pms_shopping_list_items").update({
                    "status": "under_review",
                    "updated_by": user_id,
                    "updated_at": now,
                }).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

                if not intermediate_result or not intermediate_result.data or len(intermediate_result.data) == 0:
                    builder.set_error("FORBIDDEN", "Only HoD can modify shopping list items", 403)
                    return builder.build()

            update_result = self.db.table("pms_shopping_list_items").update({
                "status": "approved",
                "quantity_approved": quantity_approved,
                "approved_by": user_id,
                "approved_at": now,
                "approval_notes": approval_notes,
                "updated_by": user_id,
                "updated_at": now,
            }).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data or len(update_result.data) == 0:
                builder.set_error("FORBIDDEN", "Only HoD can approve shopping list items", 403)
                return builder.build()

            try:
                self.db.table("pms_audit_log").insert({
                    "id": str(uuid.uuid4()),
                    "yacht_id": yacht_id,
                    "entity_type": "shopping_list_item",
                    "entity_id": entity_id,
                    "action": "approve_shopping_list_item",
                    "user_id": user_id,
                    "old_values": {"status": item["status"], "quantity_requested": item["quantity_requested"]},
                    "new_values": {"status": "approved", "quantity_approved": quantity_approved, "approved_by": user_id},
                    "signature": {},
                    "metadata": {"source": "shopping_list_lens"},
                    "created_at": now,
                }).execute()
            except Exception as audit_err:
                logger.warning(f"Audit log insert failed (non-critical): {audit_err}")

            builder.set_data({
                "shopping_list_item_id": entity_id,
                "part_name": item["part_name"],
                "status": "approved",
                "quantity_approved": quantity_approved,
                "approved_at": now,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"approve_shopping_list_item failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e), 500)
            return builder.build()

    async def reject_shopping_list_item(
        self,
        entity_id: str,
        yacht_id: str,
        params: Dict
    ) -> Dict:
        builder = ResponseBuilder(
            "reject_shopping_list_item",
            entity_id,
            "shopping_list_item",
            yacht_id
        )

        try:
            user_id = params.get("user_id")
            if not user_id:
                builder.set_error("UNAUTHORIZED", "User not authenticated", 401)
                return builder.build()

            user_result = self.db.table("auth_users_profiles").select(
                "id, name, yacht_id"
            ).eq("id", user_id).maybe_single().execute()

            if not user_result or not user_result.data or user_result.data["yacht_id"] != yacht_id:
                logger.warning(f"Yacht isolation breach attempt: user {user_id} != yacht {yacht_id}")
                builder.set_error("FORBIDDEN", "Access denied", 403)
                return builder.build()

            is_hod_result = self.db.rpc("is_hod", {"p_user_id": user_id, "p_yacht_id": yacht_id}).execute()

            if not is_hod_result or not is_hod_result.data:
                logger.warning(f"Non-HoD attempted reject: user={user_id}, yacht={yacht_id}")
                builder.set_error(
                    "FORBIDDEN",
                    "Only HoD (chief engineer, chief officer, captain, manager) can reject shopping list items",
                    403
                )
                return builder.build()

            item_result = self.db.table("pms_shopping_list_items").select(
                "id, part_name, quantity_requested, status, created_by, requested_by, is_candidate_part, rejected_at"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not item_result or not item_result.data:
                builder.set_error("NOT_FOUND", f"Shopping list item not found: {entity_id}")
                return builder.build()

            item = item_result.data

            if item.get("rejected_at"):
                builder.set_error("INVALID_STATE", "Item is already rejected", 400)
                return builder.build()

            if item["status"] not in ("candidate", "under_review"):
                builder.set_error(
                    "INVALID_STATE",
                    f"Cannot reject item with status '{item['status']}'. Expected: candidate or under_review.",
                    400
                )
                return builder.build()

            rejection_reason = params.get("rejection_reason", "").strip()
            if not rejection_reason:
                builder.set_error("VALIDATION_FAILED", "rejection_reason is required", 400)
                return builder.build()

            rejection_notes = params.get("rejection_notes")
            now = datetime.now(timezone.utc).isoformat()

            update_result = self.db.table("pms_shopping_list_items").update({
                "rejected_by": user_id,
                "rejected_at": now,
                "rejection_reason": rejection_reason,
                "rejection_notes": rejection_notes,
                "updated_by": user_id,
                "updated_at": now,
            }).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data or len(update_result.data) == 0:
                builder.set_error("FORBIDDEN", "Only HoD can reject shopping list items", 403)
                return builder.build()

            try:
                self.db.table("pms_audit_log").insert({
                    "id": str(uuid.uuid4()),
                    "yacht_id": yacht_id,
                    "entity_type": "shopping_list_item",
                    "entity_id": entity_id,
                    "action": "reject_shopping_list_item",
                    "user_id": user_id,
                    "old_values": {"status": item["status"]},
                    "new_values": {"status": "rejected", "rejection_reason": rejection_reason, "rejected_by": user_id},
                    "signature": {},
                    "metadata": {"source": "shopping_list_lens"},
                    "created_at": now,
                }).execute()
            except Exception as audit_err:
                logger.warning(f"Audit log insert failed (non-critical): {audit_err}")

            if item.get("is_candidate_part"):
                _close_candidate_followup(
                    self.db,
                    yacht_id=yacht_id,
                    item_id=entity_id,
                    part_name=item["part_name"],
                    user_id=user_id,
                    requester_id=item.get("requested_by") or item.get("created_by") or user_id,
                    outcome="rejected",
                )

            builder.set_data({
                "shopping_list_item_id": entity_id,
                "part_name": item["part_name"],
                "status": item["status"],
                "rejected": True,
                "rejection_reason": rejection_reason,
                "rejected_at": now,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"reject_shopping_list_item failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e), 500)
            return builder.build()

    async def promote_candidate_to_part(
        self,
        entity_id: str,
        yacht_id: str,
        params: Dict
    ) -> Dict:
        builder = ResponseBuilder(
            "promote_candidate_to_part",
            entity_id,
            "shopping_list_item",
            yacht_id
        )

        try:
            user_id = params.get("user_id")
            if not user_id:
                builder.set_error("UNAUTHORIZED", "User not authenticated", 401)
                return builder.build()

            user_result = self.db.table("auth_users_profiles").select(
                "id, name, yacht_id"
            ).eq("id", user_id).maybe_single().execute()

            if not user_result or not user_result.data or user_result.data["yacht_id"] != yacht_id:
                logger.warning(f"Yacht isolation breach attempt: user {user_id} != yacht {yacht_id}")
                builder.set_error("FORBIDDEN", "Access denied", 403)
                return builder.build()

            is_engineer_result = self.db.rpc("is_engineer", {"p_user_id": user_id, "p_yacht_id": yacht_id}).execute()

            if not is_engineer_result or not is_engineer_result.data:
                logger.warning(f"Non-engineer attempted promote: user={user_id}, yacht={yacht_id}")
                builder.set_error(
                    "FORBIDDEN",
                    "Only engineers (chief engineer, ETO, engineer, manager) can promote candidates to parts catalog",
                    403
                )
                return builder.build()

            item_result = self.db.table("pms_shopping_list_items").select(
                "id, part_name, part_number, manufacturer, unit, is_candidate_part, candidate_promoted_to_part_id, requested_by"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not item_result or not item_result.data:
                builder.set_error("NOT_FOUND", f"Shopping list item not found: {entity_id}")
                return builder.build()

            item = item_result.data

            if not item.get("is_candidate_part"):
                builder.set_error("INVALID_STATE", "Item is not a candidate part (already in catalog)", 400)
                return builder.build()

            if item.get("candidate_promoted_to_part_id"):
                builder.set_error(
                    "INVALID_STATE",
                    f"Item already promoted to part: {item['candidate_promoted_to_part_id']}",
                    400
                )
                return builder.build()

            new_part_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            part_insert_result = self.db.table("pms_parts").insert({
                "id": new_part_id,
                "yacht_id": yacht_id,
                "name": item["part_name"],
                "part_number": item.get("part_number"),
                "manufacturer": item.get("manufacturer"),
                "unit": item.get("unit"),
                "quantity_on_hand": 0,
                "created_at": now,
                "updated_at": now,
            }).execute()

            if not part_insert_result.data or len(part_insert_result.data) == 0:
                builder.set_error("EXECUTION_FAILED", "Failed to create part", 500)
                return builder.build()

            update_result = self.db.table("pms_shopping_list_items").update({
                "part_id": new_part_id,
                "is_candidate_part": False,
                "candidate_promoted_to_part_id": new_part_id,
                "promoted_by": user_id,
                "promoted_at": now,
                "updated_by": user_id,
                "updated_at": now,
            }).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data or len(update_result.data) == 0:
                try:
                    self.db.table("pms_parts").delete().eq("id", new_part_id).execute()
                except Exception:
                    logger.error(f"Failed to rollback part creation: {new_part_id}")
                builder.set_error("EXECUTION_FAILED", "Failed to update shopping list item", 500)
                return builder.build()

            try:
                self.db.table("pms_audit_log").insert({
                    "id": str(uuid.uuid4()),
                    "yacht_id": yacht_id,
                    "entity_type": "shopping_list_item",
                    "entity_id": entity_id,
                    "action": "promote_candidate_to_part",
                    "user_id": user_id,
                    "old_values": {"is_candidate_part": True, "part_id": None},
                    "new_values": {"is_candidate_part": False, "part_id": new_part_id, "part_name": item["part_name"]},
                    "signature": {},
                    "metadata": {"source": "shopping_list_lens", "new_part_id": new_part_id},
                    "created_at": now,
                }).execute()
            except Exception as audit_err:
                logger.warning(f"Audit log insert failed (non-critical): {audit_err}")

            _close_candidate_followup(
                self.db,
                yacht_id=yacht_id,
                item_id=entity_id,
                part_name=item["part_name"],
                user_id=user_id,
                requester_id=item.get("requested_by") or user_id,
                outcome="promoted",
            )

            builder.set_data({
                "shopping_list_item_id": entity_id,
                "part_id": new_part_id,
                "part_name": item["part_name"],
                "promoted_at": now,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"promote_candidate_to_part failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e), 500)
            return builder.build()

    async def view_shopping_list_history(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        builder = ResponseBuilder(
            "view_shopping_list_history",
            entity_id,
            "shopping_list_item",
            yacht_id
        )

        try:
            params = params or {}

            history_result = self.db.table("pms_shopping_list_state_history").select(
                "id, previous_state, new_state, transition_reason, transition_notes, "
                "changed_by, changed_at, related_order_id, related_receiving_event_id, metadata"
            ).eq("shopping_list_item_id", entity_id).eq(
                "yacht_id", yacht_id
            ).order("changed_at", desc=True).execute()

            if not history_result or not history_result.data:
                item_result = self.db.table("pms_shopping_list_items").select(
                    "id"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not item_result or not item_result.data:
                    builder.set_error("NOT_FOUND", f"Shopping list item not found: {entity_id}")
                    return builder.build()

                builder.set_data({
                    "shopping_list_item_id": entity_id,
                    "history": [],
                    "message": "No state changes recorded yet"
                })
                return builder.build()

            history = history_result.data
            user_ids = list(set([h["changed_by"] for h in history if h.get("changed_by")]))

            user_map = {}
            if user_ids:
                users_result = self.db.table("auth_users_profiles").select(
                    "id, name"
                ).in_("id", user_ids).execute()

                if users_result.data:
                    user_map = {u["id"]: u["name"] for u in users_result.data}

            for entry in history:
                entry["changed_by_name"] = user_map.get(entry["changed_by"], "Unknown")

            builder.set_data({
                "shopping_list_item_id": entity_id,
                "history": history,
                "total_changes": len(history),
            })

            return builder.build()

        except Exception as e:
            logger.error(f"view_shopping_list_history failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e), 500)
            return builder.build()


# =============================================================================
# V2 — LIST-DOCUMENT HANDLERS (pms_shopping_lists)
# Internal implementation class. Not called directly by the router.
# =============================================================================

class ShoppingListV2Handlers:
    """
    Shopping List V2 document-level handlers.
    Operates on pms_shopping_lists (the list header), not individual items.

    Lifecycle: DRAFT → SUBMITTED → HOD_APPROVED → (convert_to_po → converted_to_po)
    """

    def __init__(self, db):
        self.db = db

    async def create_shopping_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

    async def add_item_to_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            sl_r = self.db.table("pms_shopping_lists").select(
                "id, status, name, list_number, currency"
            ).eq("id", shopping_list_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()

            if not sl_r or not sl_r.data:
                return {"status": "error", "error_code": "NOT_FOUND", "message": "Shopping list not found"}

            sl = sl_r.data
            if sl["status"] not in ("draft", "submitted"):
                return {"status": "error", "error_code": "INVALID_STATE",
                        "message": f"Cannot add items to a list in status '{sl['status']}'"}

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

            self._recalc_total(yacht_id, shopping_list_id)

            if is_candidate:
                _open_candidate_followup(
                    self.db,
                    yacht_id=yacht_id,
                    item_id=item["id"],
                    part_name=params["part_name"],
                    requester_id=user_id,
                    action="add_item_to_list",
                )

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

    async def update_list_item(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
                "message": "Item updated",
            }

        except Exception as exc:
            logger.error(f"[sl_v2] update_list_item failed: {exc}", exc_info=True)
            return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}

    async def delete_list_item(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            if item["status"] in _LOCKED_STATUSES:
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

    async def submit_shopping_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

    async def hod_review_list_item(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            if item["status"] in _LOCKED_STATUSES:
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

            else:
                self.db.table("pms_shopping_list_items").update({
                    "status": "rejected",
                    "rejected_by": user_id,
                    "rejected_at": now,
                    "rejection_reason": params["rejection_reason"].strip(),
                    "rejection_notes": params.get("rejection_notes"),
                    "updated_by": user_id,
                    "updated_at": now,
                }).eq("id", item_id).eq("yacht_id", yacht_id).execute()

                if item.get("is_candidate_part"):
                    _close_candidate_followup(
                        self.db,
                        yacht_id=yacht_id,
                        item_id=item_id,
                        part_name=item["part_name"],
                        user_id=user_id,
                        requester_id=item.get("requested_by") or user_id,
                        outcome="rejected",
                    )

            if item.get("shopping_list_id"):
                self._recalc_total(yacht_id, item["shopping_list_id"])

            return {
                "status": "success",
                "action": "hod_review_list_item",
                "result": {"item_id": item_id, "part_name": item["part_name"], "decision": decision},
                "message": f"'{item['part_name']}' {decision}",
            }

        except Exception as exc:
            logger.error(f"[sl_v2] hod_review_list_item failed: {exc}", exc_info=True)
            return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}

    async def approve_shopping_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

            self.db.table("pms_shopping_list_items").update({
                "status": "approved",
                "approved_by": user_id,
                "approved_at": now,
                "updated_by": user_id,
                "updated_at": now,
            }).eq("shopping_list_id", shopping_list_id).eq("yacht_id", yacht_id).in_(
                "status", ["candidate", "under_review"]
            ).is_("deleted_at", "null").execute()

            items_r = self.db.table("pms_shopping_list_items").select(
                "status", count="exact"
            ).eq("shopping_list_id", shopping_list_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").execute()

            items = items_r.data or []
            approved_count = sum(1 for i in items if i["status"] == "approved")
            rejected_count = sum(1 for i in items if i["status"] == "rejected")

            self._recalc_total(yacht_id, shopping_list_id)

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

    def _recalc_total(self, yacht_id: str, shopping_list_id: str) -> None:
        """Recalculate estimated_total on the list from non-rejected items."""
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
                        title="Shopping list needs your approval",
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


# =============================================================================
# PHASE 4 — INTERNAL DISPATCH HELPERS
# Eliminates copy-paste across V1 and V2 wrapper functions.
# =============================================================================

async def _v1_dispatch(
    method_name: str,
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    h = ShoppingListHandlers(db_client)
    entity_id = (payload.get("item_id") or payload.get("shopping_list_item_id")
                 or context.get("shopping_list_item_id"))
    params = {
        "user_id": user_id,
        "user_role": user_context.get("role"),
        "user_name": user_context.get("name", "Unknown"),
        **context,
        **payload,
    }
    return await getattr(h, method_name)(entity_id=entity_id, yacht_id=yacht_id, params=params)


async def _v2_dispatch(
    method_name: str,
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    h = ShoppingListV2Handlers(db_client)
    params = {"yacht_id": yacht_id, "user_id": user_id, **context, **payload}
    return await getattr(h, method_name)(params)


def _soft_delete_list(
    db_client, *, list_id: str, yacht_id: str, user_id: str, extra: dict = None,
) -> None:
    update = {"deleted_at": _now(), "deleted_by": user_id, **(extra or {})}
    db_client.table("pms_shopping_lists").update(update).eq(
        "id", list_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").execute()


# =============================================================================
# PHASE 4 — V1 WRAPPER FUNCTIONS
# These are the router-callable functions. Phase 4 signature throughout.
# V1 class methods above are internal implementation details.
# =============================================================================

async def delete_shopping_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    user_role = user_context.get("role", "")
    if user_role not in _DELETE_ITEM_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' is not authorized to perform 'delete_shopping_item'",
        )

    item_id = payload.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")

    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, str(item_id), re.IGNORECASE):
        raise HTTPException(status_code=400, detail="item_id must be a valid UUID")

    try:
        check = db_client.table("pms_shopping_list_items").select(
            "id, status"
        ).eq("id", item_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not check or not check.data:
            raise HTTPException(status_code=404, detail="Shopping list item not found")

        # Prevent deletion of items that are in-flight through the supply chain
        item_status = check.data.get("status", "")
        if item_status in _LOCKED_STATUSES:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete item with status '{item_status}'"
            )

        db_client.table("pms_shopping_list_items").delete().eq(
            "id", item_id).eq("yacht_id", yacht_id).execute()

        return {
            "status": "success",
            "success": True,
            "item_id": item_id,
            "message": "Shopping list item deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "does not exist" in error_str.lower() or "42P01" in error_str:
            raise HTTPException(status_code=404, detail="Shopping list feature not available")
        if "immutable" in error_str.lower() or "finance transactions" in error_str.lower():
            raise HTTPException(status_code=409, detail="Cannot delete: item is linked to a finance transaction.")
        raise HTTPException(status_code=500, detail=f"Database error: {error_str}")


async def create_shopping_list_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v1_dispatch("create_shopping_list_item", payload, context, yacht_id, user_id, user_context, db_client)


async def approve_shopping_list_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v1_dispatch("approve_shopping_list_item", payload, context, yacht_id, user_id, user_context, db_client)


async def reject_shopping_list_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v1_dispatch("reject_shopping_list_item", payload, context, yacht_id, user_id, user_context, db_client)


async def promote_candidate_to_part(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v1_dispatch("promote_candidate_to_part", payload, context, yacht_id, user_id, user_context, db_client)


async def view_shopping_list_history(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v1_dispatch("view_shopping_list_history", payload, context, yacht_id, user_id, user_context, db_client)


async def mark_shopping_list_ordered(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    user_role = user_context.get("role", "")
    if user_role not in _MARK_ORDERED_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' is not authorized to perform 'mark_shopping_list_ordered'",
        )

    item_id = (payload.get("item_id") or payload.get("shopping_list_item_id")
               or context.get("shopping_list_item_id") or context.get("shopping_list_id"))
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")

    update_data = {"status": "ordered", "updated_at": datetime.now(timezone.utc).isoformat()}
    upd = db_client.table("pms_shopping_list_items").update(update_data).eq(
        "id", item_id).eq("yacht_id", yacht_id).execute()

    if upd.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="status_change",
                entity_type="shopping_list_item", entity_id=item_id, action="mark_shopping_list_ordered",
                user_role=user_context.get("role"), change_summary="Shopping list item marked as ordered",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record mark_shopping_list_ordered: {ledger_err}")
        return {"status": "success", "message": "Shopping list item marked as ordered"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED",
                "message": "Failed to mark shopping list item as ordered"}


# =============================================================================
# PHASE 4 — V2 WRAPPER FUNCTIONS
# =============================================================================

async def create_shopping_list(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v2_dispatch("create_shopping_list", payload, context, yacht_id, user_id, user_context, db_client)


async def add_item_to_list(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v2_dispatch("add_item_to_list", payload, context, yacht_id, user_id, user_context, db_client)


async def update_list_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v2_dispatch("update_list_item", payload, context, yacht_id, user_id, user_context, db_client)


async def delete_list_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v2_dispatch("delete_list_item", payload, context, yacht_id, user_id, user_context, db_client)


async def submit_shopping_list(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v2_dispatch("submit_shopping_list", payload, context, yacht_id, user_id, user_context, db_client)


async def hod_review_list_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v2_dispatch("hod_review_list_item", payload, context, yacht_id, user_id, user_context, db_client)


async def approve_shopping_list(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    return await _v2_dispatch("approve_shopping_list", payload, context, yacht_id, user_id, user_context, db_client)


async def add_shopping_list_photo(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    item_id = payload.get("item_id")
    storage_path = payload.get("storage_path")
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")
    if not storage_path:
        raise HTTPException(status_code=400, detail="storage_path is required")
    try:
        now = _now()
        row = db_client.table("pms_attachments").insert({
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "entity_type": "shopping_list",
            "entity_id": item_id,
            "uploaded_by": user_id,
            "storage_path": storage_path,
            "storage_bucket": "pms-shopping-list-photos",
            "file_name": payload.get("file_name", "photo"),
            "file_type": payload.get("file_type", "image"),
            "created_at": now,
        }).execute()
        return {
            "status": "success",
            "action": "add_shopping_list_photo",
            "result": row.data[0] if row.data else {},
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[shopping] add_shopping_list_photo failed: {exc}", exc_info=True)
        return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}


# =============================================================================
# PHASE 4 — UTILITY FUNCTIONS
# =============================================================================

async def submit_list(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    """Transition a single item from candidate → under_review (V1 item-level submit)."""
    item_id = (payload.get("item_id") or payload.get("entity_id")
               or context.get("item_id") or context.get("entity_id"))
    if not item_id:
        raise ValueError("item_id or entity_id is required")

    item = db_client.table("pms_shopping_list_items").select("id, status").eq(
        "id", item_id).eq("yacht_id", yacht_id).limit(1).execute()

    if not item.data:
        raise ValueError(f"Shopping list item {item_id} not found")

    if item.data[0]["status"] != "candidate":
        raise ValueError(f"Cannot submit: item is '{item.data[0]['status']}', expected 'candidate'")

    db_client.table("pms_shopping_list_items").update({
        "status": "under_review",
        "updated_at": _now(),
        "updated_by": user_id,
    }).eq("id", item_id).eq("yacht_id", yacht_id).execute()

    return {"status": "success", "item_id": item_id, "new_status": "under_review"}


async def convert_to_po(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    """Create a Purchase Order from approved shopping list items."""
    shopping_list_id = payload.get("shopping_list_id") or context.get("shopping_list_id")

    query = db_client.table("pms_shopping_list_items").select(
        "id, part_name, part_number, manufacturer, quantity_requested, quantity_approved, unit, part_id"
    ).eq("yacht_id", yacht_id).eq("status", "approved").is_("deleted_at", "null")

    if shopping_list_id:
        query = query.eq("shopping_list_id", shopping_list_id)
    else:
        item_ids = payload.get("item_ids")
        if item_ids:
            query = query.in_("id", item_ids)

    items = (query.execute()).data or []
    if not items:
        raise ValueError("No approved shopping list items found")

    year = datetime.now(timezone.utc).year
    existing = db_client.table("pms_purchase_orders").select("po_number").eq(
        "yacht_id", yacht_id
    ).like("po_number", f"PO-{year}-%").execute()
    _nums = [int(r["po_number"].rsplit("-", 1)[-1]) for r in (existing.data or [])
             if r.get("po_number", "").count("-") >= 2]
    po_number = f"PO-{year}-{max(_nums, default=0) + 1:03d}"

    po_id = str(uuid.uuid4())
    po_data = {
        "id": po_id, "yacht_id": yacht_id, "po_number": po_number,
        "status": "draft", "ordered_by": user_id,
        "created_at": _now(), "updated_at": _now(),
    }
    if shopping_list_id:
        po_data["source_shopping_list_id"] = shopping_list_id
    if payload.get("supplier_id"):
        po_data["supplier_id"] = payload["supplier_id"]

    db_client.table("pms_purchase_orders").insert(po_data).execute()

    for line_number, item in enumerate(items, start=1):
        db_client.table("pms_purchase_order_items").insert({
            "id": str(uuid.uuid4()), "yacht_id": yacht_id,
            "purchase_order_id": po_id, "part_id": item.get("part_id"),
            "description": item["part_name"],
            "quantity_ordered": int(item.get("quantity_approved") or item["quantity_requested"]),
            "shopping_list_item_id": item["id"],
        }).execute()
        db_client.table("pms_shopping_list_items").update({
            "status": "ordered", "order_id": po_id, "order_line_number": line_number,
            "updated_at": _now(), "updated_by": user_id,
        }).eq("id", item["id"]).eq("yacht_id", yacht_id).execute()

    if shopping_list_id:
        try:
            db_client.table("pms_shopping_lists").update({
                "status": "converted_to_po", "converted_to_po_id": po_id,
                "converted_at": _now(),
            }).eq("id", shopping_list_id).eq("yacht_id", yacht_id).execute()
        except Exception as sl_err:
            logger.warning(f"[convert_to_po] Shopping list status update failed: {sl_err}")

    try:
        db_client.table("ledger_events").insert(build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="create",
            entity_type="purchase_order", entity_id=po_id, action="convert_to_po",
            user_role=user_context.get("role"), change_summary=f"PO {po_number} created from shopping list ({len(items)} items)",
        )).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[convert_to_po] Ledger write failed (non-fatal): {ledger_err}")

    return {
        "status": "success", "po_id": po_id, "po_number": po_number,
        "items_ordered": len(items), "source_shopping_list_id": shopping_list_id,
    }


async def archive_list(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    list_id = (payload.get("shopping_list_id") or payload.get("entity_id")
               or context.get("shopping_list_id"))
    if not list_id:
        raise HTTPException(status_code=400, detail="shopping_list_id is required")
    _soft_delete_list(db_client, list_id=list_id, yacht_id=yacht_id, user_id=user_id, extra={"status": "archived"})
    return {"status": "success", "shopping_list_id": list_id, "archived": True}


async def delete_list(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Any,
) -> dict:
    list_id = (payload.get("shopping_list_id") or payload.get("entity_id")
               or context.get("shopping_list_id"))
    if not list_id:
        raise HTTPException(status_code=400, detail="shopping_list_id is required")
    _soft_delete_list(db_client, list_id=list_id, yacht_id=yacht_id, user_id=user_id)
    return {"status": "success", "shopping_list_id": list_id, "deleted": True}


# Aliases — same function, different action name registered in frontend
add_list_item = create_shopping_list_item
approve_list = approve_shopping_list_item


# =============================================================================
# HANDLERS DICT — all 21 shopping domain actions
# =============================================================================

HANDLERS: Dict[str, Any] = {
    # V1 — per-item operations
    "delete_shopping_item": delete_shopping_item,
    "create_shopping_list_item": create_shopping_list_item,
    "approve_shopping_list_item": approve_shopping_list_item,
    "reject_shopping_list_item": reject_shopping_list_item,
    "promote_candidate_to_part": promote_candidate_to_part,
    "view_shopping_list_history": view_shopping_list_history,
    "mark_shopping_list_ordered": mark_shopping_list_ordered,
    # V2 — list-document operations
    "create_shopping_list": create_shopping_list,
    "add_item_to_list": add_item_to_list,
    "update_list_item": update_list_item,
    "delete_list_item": delete_list_item,
    "submit_shopping_list": submit_shopping_list,
    "hod_review_list_item": hod_review_list_item,
    "approve_shopping_list": approve_shopping_list,
    "add_shopping_list_photo": add_shopping_list_photo,
    # Utility / state transitions
    "submit_list": submit_list,
    "convert_to_po": convert_to_po,
    "archive_list": archive_list,
    "delete_list": delete_list,
    # Aliases
    "add_list_item": add_list_item,
    "approve_list": approve_list,
}
