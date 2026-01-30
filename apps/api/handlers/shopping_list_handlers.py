"""
Shopping List Domain Handlers
==============================

Handlers for shopping list actions (Shopping List Lens v1).

MUTATION Handlers:
- create_shopping_list_item: Add item to shopping list (All Crew)
- approve_shopping_list_item: Approve item for ordering (HoD only)
- reject_shopping_list_item: Reject item (HoD only)
- promote_candidate_to_part: Add candidate to parts catalog (Engineers only)

READ Handlers:
- view_shopping_list_history: View state change timeline (All Crew)

All handlers return standardized ActionResponseEnvelope.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import (
    ResponseBuilder,
    AvailableAction,
    Severity,
)

logger = logging.getLogger(__name__)


# Shopping list status flow
SHOPPING_LIST_STATUS_FLOW = {
    "candidate": ["under_review", "approved"],  # Initial state
    "under_review": ["approved", "rejected"],    # Being reviewed
    "approved": ["ordered"],                     # Approved for ordering
    "ordered": ["partially_fulfilled", "fulfilled"],  # On order
    "partially_fulfilled": ["fulfilled"],        # Some received
    "fulfilled": ["installed"],                  # All received
    "installed": [],                             # Terminal state (success)
    "rejected": [],                              # Terminal state (denied)
}

# Source types
SOURCE_TYPES = [
    "inventory_low", "inventory_oos", "work_order_usage",
    "receiving_missing", "receiving_damaged", "manual_add"
]

# Urgency levels
URGENCY_LEVELS = ["low", "normal", "high", "critical"]


class ShoppingListHandlers:
    """
    Shopping List domain handlers.

    CRITICAL PATTERNS:
    1. Yacht Isolation: EVERY query MUST filter by yacht_id
    2. State Machine: Enforce valid transitions via SHOPPING_LIST_STATUS_FLOW
    3. HoD Gating: approve/reject require is_hod() check
    4. Audit Signature: {} for non-signed actions (all shopping list actions)
    5. Error Mapping: 4xx for client errors, NEVER 500
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # MUTATION HANDLERS
    # =========================================================================

    async def create_shopping_list_item(
        self,
        entity_id: str,  # Will be None for new items
        yacht_id: str,
        params: Dict
    ) -> Dict:
        """
        Create new shopping list item.

        Allowed Roles: All Crew (crew, chief_engineer, chief_officer, captain, manager)

        Tables Written:
        - pms_shopping_list_items (INSERT)
        - pms_shopping_list_state_history (INSERT via trigger)
        - pms_audit_log (INSERT)

        Required Fields:
        - part_name (text, NOT NULL)
        - quantity_requested (numeric, > 0)
        - source_type (enum)

        Optional Fields:
        - part_id (uuid) - if existing part
        - part_number (text)
        - manufacturer (text)
        - unit (text)
        - preferred_supplier (text)
        - estimated_unit_price (numeric)
        - urgency (enum: low, normal, high, critical)
        - required_by_date (date)
        - source_work_order_id (uuid)
        - source_receiving_id (uuid)
        - source_notes (text)

        Returns:
        - 200 + item_id on success
        - 400 if validation fails
        - 404 if part_id not found
        - 403 if user not authorized
        """
        builder = ResponseBuilder(
            "create_shopping_list_item",
            entity_id,
            "shopping_list_item",
            yacht_id
        )

        try:
            # ============================================================
            # VALIDATION & AUTH
            # ============================================================

            user_id = params.get("user_id")
            if not user_id:
                builder.set_error("UNAUTHORIZED", "User not authenticated", 401)
                return builder.build()

            # Get user profile (yacht isolation check)
            user_result = self.db.table("auth_users_profiles").select(
                "id, name"
            ).eq("id", user_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not user_result or not user_result.data:
                logger.warning(f"Yacht isolation breach attempt: user {user_id} != yacht {yacht_id}")
                builder.set_error("FORBIDDEN", "Access denied", 403)
                return builder.build()

            user = user_result.data

            # ============================================================
            # FIELD VALIDATION
            # ============================================================

            # Required: part_name
            part_name = params.get("part_name", "").strip()
            if not part_name:
                builder.set_error("VALIDATION_FAILED", "part_name is required", 400)
                return builder.build()

            # Required: quantity_requested (must be > 0)
            try:
                quantity_requested = float(params.get("quantity_requested", 0))
                if quantity_requested <= 0:
                    builder.set_error("VALIDATION_FAILED", "quantity_requested must be greater than 0", 400)
                    return builder.build()
            except (ValueError, TypeError):
                builder.set_error("VALIDATION_FAILED", "quantity_requested must be a valid number", 400)
                return builder.build()

            # Required: source_type (enum validation)
            source_type = params.get("source_type", "manual_add")
            if source_type not in SOURCE_TYPES:
                builder.set_error(
                    "VALIDATION_FAILED",
                    f"source_type must be one of: {', '.join(SOURCE_TYPES)}",
                    400
                )
                return builder.build()

            # Optional: urgency (enum validation if provided)
            urgency = params.get("urgency")
            if urgency and urgency not in URGENCY_LEVELS:
                builder.set_error(
                    "VALIDATION_FAILED",
                    f"urgency must be one of: {', '.join(URGENCY_LEVELS)}",
                    400
                )
                return builder.build()

            # Optional: part_id (must exist if provided)
            part_id = params.get("part_id")
            part_number = params.get("part_number")
            manufacturer = params.get("manufacturer")
            is_candidate_part = True  # Default: candidate (not in catalog)

            if part_id:
                # Validate part exists
                part_result = self.db.table("pms_parts").select(
                    "id, part_name, part_number, manufacturer"
                ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not part_result or not part_result.data:
                    builder.set_error("NOT_FOUND", f"Part not found: {part_id}", 404)
                    return builder.build()

                # Use part details if not provided
                part = part_result.data
                part_name = part_name or part.get("part_name")
                part_number = part_number or part.get("part_number")
                manufacturer = manufacturer or part.get("manufacturer")
                is_candidate_part = False  # Existing part

            # ============================================================
            # INSERT SHOPPING LIST ITEM (via RPC)
            # ============================================================
            # NOTE: Using RPC function with SECURITY DEFINER to bypass RLS
            #       TENANT Supabase cannot verify JWTs from MASTER, so auth.uid() = NULL
            #       RPC validates user_id against auth_users_roles before INSERT

            # Prepare RPC parameters
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

            # Call RPC function (SECURITY DEFINER bypasses RLS)
            try:
                insert_result = self.db.rpc("rpc_insert_shopping_list_item", rpc_params).execute()
            except Exception as e:
                logger.error(f"Failed to insert shopping list item via RPC: {e}", exc_info=True)
                builder.set_error("EXECUTION_FAILED", f"Failed to create shopping list item: {str(e)}", 500)
                return builder.build()

            if not insert_result.data or len(insert_result.data) == 0:
                builder.set_error("EXECUTION_FAILED", "Failed to create shopping list item", 500)
                return builder.build()

            # Extract new_item_id from RPC result
            new_item_id = insert_result.data[0]["id"]

            # Timestamp for audit log
            now = datetime.now(timezone.utc).isoformat()

            # ============================================================
            # AUDIT LOG
            # ============================================================

            audit_payload = {
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
                "signature": {},  # Non-signed action
                "metadata": {"source": "shopping_list_lens"},
                "created_at": now,
            }

            try:
                self.db.table("pms_audit_log").insert(audit_payload).execute()
            except Exception as audit_err:
                logger.warning(f"Audit log insert failed (non-critical): {audit_err}")

            # ============================================================
            # RESPONSE
            # ============================================================

            builder.set_data({
                "shopping_list_item_id": new_item_id,
                "part_name": part_name,
                "quantity_requested": quantity_requested,
                "status": "candidate",
                "is_candidate_part": is_candidate_part,
                "created_at": now,
            })

            # Add available follow-up actions
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
        entity_id: str,  # shopping_list_item_id
        yacht_id: str,
        params: Dict
    ) -> Dict:
        """
        Approve shopping list item for ordering.

        Allowed Roles: HoD only (chief_engineer, chief_officer, captain, manager)

        Tables Written:
        - pms_shopping_list_items (UPDATE status, approved_by, approved_at, quantity_approved)
        - pms_shopping_list_state_history (INSERT via trigger)
        - pms_audit_log (INSERT)

        Required Fields:
        - quantity_approved (numeric, > 0)

        Optional Fields:
        - approval_notes (text)

        State Transition:
        - candidate → approved
        - under_review → approved

        Returns:
        - 200 + updated item on success
        - 400 if invalid state transition or validation fails
        - 404 if item not found
        - 403 if user not HoD
        """
        builder = ResponseBuilder(
            "approve_shopping_list_item",
            entity_id,
            "shopping_list_item",
            yacht_id
        )

        try:
            # ============================================================
            # AUTH & HOD CHECK
            # ============================================================

            user_id = params.get("user_id")
            if not user_id:
                builder.set_error("UNAUTHORIZED", "User not authenticated", 401)
                return builder.build()

            # Get user profile (yacht + role check)
            user_result = self.db.table("auth_users_profiles").select(
                "id, name, yacht_id"
            ).eq("id", user_id).maybe_single().execute()

            if not user_result or not user_result.data or user_result.data["yacht_id"] != yacht_id:
                logger.warning(f"Yacht isolation breach attempt: user {user_id} != yacht {yacht_id}")
                builder.set_error("FORBIDDEN", "Access denied", 403)
                return builder.build()

            user = user_result.data

            # ============================================================
            # ROLE CHECK: Only HoD can approve
            # ============================================================
            # NOTE: Handlers use service key which bypasses RLS, so we must check roles explicitly
            is_hod_result = self.db.rpc("is_hod", {"p_user_id": user_id, "p_yacht_id": yacht_id}).execute()

            if not is_hod_result or not is_hod_result.data:
                logger.warning(f"Non-HoD attempted approve: user={user_id}, yacht={yacht_id}")
                builder.set_error(
                    "FORBIDDEN",
                    "Only HoD (chief engineer, chief officer, captain, manager) can approve shopping list items",
                    403
                )
                return builder.build()

            # ============================================================
            # FETCH ITEM & VALIDATE STATE
            # ============================================================

            item_result = self.db.table("pms_shopping_list_items").select(
                "id, part_name, quantity_requested, status, created_by, rejected_at"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not item_result or not item_result.data:
                builder.set_error("NOT_FOUND", f"Shopping list item not found: {entity_id}", 404)
                return builder.build()

            item = item_result.data

            # Check if item has been rejected (marked by rejected_at, not status)
            if item.get("rejected_at"):
                builder.set_error(
                    "INVALID_STATE",
                    "Cannot approve a rejected item",
                    400
                )
                return builder.build()

            # Check valid transition (candidate or under_review → approved)
            if item["status"] not in ("candidate", "under_review"):
                builder.set_error(
                    "INVALID_STATE",
                    f"Cannot approve item with status '{item['status']}'. Expected: candidate or under_review.",
                    400
                )
                return builder.build()

            # ============================================================
            # FIELD VALIDATION
            # ============================================================

            # Required: quantity_approved (must be > 0)
            try:
                quantity_approved = float(params.get("quantity_approved", 0))
                if quantity_approved <= 0:
                    builder.set_error("VALIDATION_FAILED", "quantity_approved must be greater than 0", 400)
                    return builder.build()
            except (ValueError, TypeError):
                builder.set_error("VALIDATION_FAILED", "quantity_approved must be a valid number", 400)
                return builder.build()

            # Optional: approval_notes
            approval_notes = params.get("approval_notes")

            # ============================================================
            # UPDATE ITEM (Handle state machine: candidate → under_review → approved)
            # ============================================================

            now = datetime.now(timezone.utc).isoformat()

            # If item is in 'candidate' status, first transition to 'under_review'
            if item["status"] == "candidate":
                intermediate_payload = {
                    "status": "under_review",
                    "updated_by": user_id,
                    "updated_at": now,
                }

                intermediate_result = self.db.table("pms_shopping_list_items").update(
                    intermediate_payload
                ).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

                if not intermediate_result or not intermediate_result.data or len(intermediate_result.data) == 0:
                    builder.set_error(
                        "FORBIDDEN",
                        "Only HoD can modify shopping list items",
                        403
                    )
                    return builder.build()

            # Now transition to 'approved' (works from both 'candidate' → 'under_review' → 'approved' or direct 'under_review' → 'approved')
            update_payload = {
                "status": "approved",
                "quantity_approved": quantity_approved,
                "approved_by": user_id,
                "approved_at": now,
                "approval_notes": approval_notes,
                "updated_by": user_id,
                "updated_at": now,
            }

            # Update (RLS enforces is_hod() check)
            update_result = self.db.table("pms_shopping_list_items").update(
                update_payload
            ).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data or len(update_result.data) == 0:
                # RLS likely blocked (user not HoD)
                builder.set_error(
                    "FORBIDDEN",
                    "Only HoD can approve shopping list items",
                    403
                )
                return builder.build()

            # ============================================================
            # AUDIT LOG
            # ============================================================

            audit_payload = {
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": "shopping_list_item",
                "entity_id": entity_id,
                "action": "approve_shopping_list_item",
                "user_id": user_id,
                "old_values": {
                    "status": item["status"],
                    "quantity_requested": item["quantity_requested"],
                },
                "new_values": {
                    "status": "approved",
                    "quantity_approved": quantity_approved,
                    "approved_by": user_id,
                },
                "signature": {},  # Non-signed action
                "metadata": {"source": "shopping_list_lens"},
                "created_at": now,
            }

            try:
                self.db.table("pms_audit_log").insert(audit_payload).execute()
            except Exception as audit_err:
                logger.warning(f"Audit log insert failed (non-critical): {audit_err}")

            # ============================================================
            # RESPONSE
            # ============================================================

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
        entity_id: str,  # shopping_list_item_id
        yacht_id: str,
        params: Dict
    ) -> Dict:
        """
        Reject shopping list item.

        Allowed Roles: HoD only (chief_engineer, chief_officer, captain, manager)

        Tables Written:
        - pms_shopping_list_items (UPDATE status, rejected_by, rejected_at, rejection_reason)
        - pms_shopping_list_state_history (INSERT via trigger)
        - pms_audit_log (INSERT)

        Required Fields:
        - rejection_reason (text, NOT NULL)

        Optional Fields:
        - rejection_notes (text)

        State Transition:
        - candidate → rejected (terminal)
        - under_review → rejected (terminal)

        Returns:
        - 200 + updated item on success
        - 400 if invalid state transition or validation fails
        - 404 if item not found
        - 403 if user not HoD
        """
        builder = ResponseBuilder(
            "reject_shopping_list_item",
            entity_id,
            "shopping_list_item",
            yacht_id
        )

        try:
            # ============================================================
            # AUTH & HOD CHECK
            # ============================================================

            user_id = params.get("user_id")
            if not user_id:
                builder.set_error("UNAUTHORIZED", "User not authenticated", 401)
                return builder.build()

            # Get user profile (yacht + role check)
            user_result = self.db.table("auth_users_profiles").select(
                "id, name, yacht_id"
            ).eq("id", user_id).maybe_single().execute()

            if not user_result or not user_result.data or user_result.data["yacht_id"] != yacht_id:
                logger.warning(f"Yacht isolation breach attempt: user {user_id} != yacht {yacht_id}")
                builder.set_error("FORBIDDEN", "Access denied", 403)
                return builder.build()

            user = user_result.data

            # ============================================================
            # ROLE CHECK: Only HoD can reject
            # ============================================================
            # NOTE: Handlers use service key which bypasses RLS, so we must check roles explicitly
            is_hod_result = self.db.rpc("is_hod", {"p_user_id": user_id, "p_yacht_id": yacht_id}).execute()

            if not is_hod_result or not is_hod_result.data:
                logger.warning(f"Non-HoD attempted reject: user={user_id}, yacht={yacht_id}")
                builder.set_error(
                    "FORBIDDEN",
                    "Only HoD (chief engineer, chief officer, captain, manager) can reject shopping list items",
                    403
                )
                return builder.build()

            # ============================================================
            # FETCH ITEM & VALIDATE STATE
            # ============================================================

            item_result = self.db.table("pms_shopping_list_items").select(
                "id, part_name, quantity_requested, status, created_by, rejected_at"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not item_result or not item_result.data:
                builder.set_error("NOT_FOUND", f"Shopping list item not found: {entity_id}", 404)
                return builder.build()

            item = item_result.data

            # Check if already rejected (marked by rejected_at, not status)
            if item.get("rejected_at"):
                builder.set_error(
                    "INVALID_STATE",
                    "Item is already rejected",
                    400
                )
                return builder.build()

            if item["status"] not in ("candidate", "under_review"):
                builder.set_error(
                    "INVALID_STATE",
                    f"Cannot reject item with status '{item['status']}'. Expected: candidate or under_review.",
                    400
                )
                return builder.build()

            # ============================================================
            # FIELD VALIDATION
            # ============================================================

            # Required: rejection_reason
            rejection_reason = params.get("rejection_reason", "").strip()
            if not rejection_reason:
                builder.set_error("VALIDATION_FAILED", "rejection_reason is required", 400)
                return builder.build()

            # Optional: rejection_notes
            rejection_notes = params.get("rejection_notes")

            # ============================================================
            # UPDATE ITEM (Rejection does NOT change status, just sets rejected_at)
            # ============================================================

            now = datetime.now(timezone.utc).isoformat()

            update_payload = {
                # NOTE: Status stays as-is (candidate or under_review)
                # Rejection is marked by rejected_at field, not status
                "rejected_by": user_id,
                "rejected_at": now,
                "rejection_reason": rejection_reason,
                "rejection_notes": rejection_notes,
                "updated_by": user_id,
                "updated_at": now,
            }

            # Update (RLS enforces is_hod() check)
            update_result = self.db.table("pms_shopping_list_items").update(
                update_payload
            ).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data or len(update_result.data) == 0:
                # RLS likely blocked (user not HoD)
                builder.set_error(
                    "FORBIDDEN",
                    "Only HoD can reject shopping list items",
                    403
                )
                return builder.build()

            # ============================================================
            # AUDIT LOG
            # ============================================================

            audit_payload = {
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": "shopping_list_item",
                "entity_id": entity_id,
                "action": "reject_shopping_list_item",
                "user_id": user_id,
                "old_values": {
                    "status": item["status"],
                },
                "new_values": {
                    "status": "rejected",
                    "rejection_reason": rejection_reason,
                    "rejected_by": user_id,
                },
                "signature": {},  # Non-signed action
                "metadata": {"source": "shopping_list_lens"},
                "created_at": now,
            }

            try:
                self.db.table("pms_audit_log").insert(audit_payload).execute()
            except Exception as audit_err:
                logger.warning(f"Audit log insert failed (non-critical): {audit_err}")

            # ============================================================
            # RESPONSE
            # ============================================================

            builder.set_data({
                "shopping_list_item_id": entity_id,
                "part_name": item["part_name"],
                "status": item["status"],  # Status remains unchanged (candidate or under_review)
                "rejected": True,  # Add flag to indicate item is rejected
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
        entity_id: str,  # shopping_list_item_id
        yacht_id: str,
        params: Dict
    ) -> Dict:
        """
        Promote candidate item to parts catalog.

        Allowed Roles: Engineers only (chief_engineer, manager)

        Tables Written:
        - pms_parts (INSERT - new part created)
        - pms_shopping_list_items (UPDATE candidate_promoted_to_part_id, promoted_by, promoted_at)
        - pms_audit_log (INSERT)

        Business Rules:
        - Only items with is_candidate_part=true can be promoted
        - Creates new part in pms_parts with initial quantity=0
        - Links shopping list item to new part

        Returns:
        - 200 + new part_id on success
        - 400 if item is not a candidate or already promoted
        - 404 if item not found
        - 403 if user not engineer
        """
        builder = ResponseBuilder(
            "promote_candidate_to_part",
            entity_id,
            "shopping_list_item",
            yacht_id
        )

        try:
            # ============================================================
            # AUTH & ROLE CHECK
            # ============================================================

            user_id = params.get("user_id")
            if not user_id:
                builder.set_error("UNAUTHORIZED", "User not authenticated", 401)
                return builder.build()

            # Get user profile (yacht + role check)
            user_result = self.db.table("auth_users_profiles").select(
                "id, name, yacht_id"
            ).eq("id", user_id).maybe_single().execute()

            if not user_result or not user_result.data or user_result.data["yacht_id"] != yacht_id:
                logger.warning(f"Yacht isolation breach attempt: user {user_id} != yacht {yacht_id}")
                builder.set_error("FORBIDDEN", "Access denied", 403)
                return builder.build()

            user = user_result.data

            # ============================================================
            # ROLE CHECK: Only engineers can promote
            # ============================================================
            # NOTE: Handlers use service key which bypasses RLS, so we must check roles explicitly
            is_engineer_result = self.db.rpc("is_engineer", {"p_user_id": user_id, "p_yacht_id": yacht_id}).execute()

            if not is_engineer_result or not is_engineer_result.data:
                logger.warning(f"Non-engineer attempted promote: user={user_id}, yacht={yacht_id}")
                builder.set_error(
                    "FORBIDDEN",
                    "Only engineers (chief engineer, ETO, engineer, manager) can promote candidates to parts catalog",
                    403
                )
                return builder.build()

            # ============================================================
            # FETCH ITEM & VALIDATE
            # ============================================================

            item_result = self.db.table("pms_shopping_list_items").select(
                "id, part_name, part_number, manufacturer, unit, is_candidate_part, candidate_promoted_to_part_id"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not item_result or not item_result.data:
                builder.set_error("NOT_FOUND", f"Shopping list item not found: {entity_id}", 404)
                return builder.build()

            item = item_result.data

            # Check if item is a candidate
            if not item.get("is_candidate_part"):
                builder.set_error(
                    "INVALID_STATE",
                    "Item is not a candidate part (already in catalog)",
                    400
                )
                return builder.build()

            # Check if already promoted
            if item.get("candidate_promoted_to_part_id"):
                builder.set_error(
                    "INVALID_STATE",
                    f"Item already promoted to part: {item['candidate_promoted_to_part_id']}",
                    400
                )
                return builder.build()

            # ============================================================
            # CREATE NEW PART
            # ============================================================

            new_part_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            part_payload = {
                "id": new_part_id,
                "yacht_id": yacht_id,
                "name": item["part_name"],  # Column is 'name' not 'part_name'
                "part_number": item.get("part_number"),
                "manufacturer": item.get("manufacturer"),
                "unit": item.get("unit"),
                "quantity_on_hand": 0,  # Initial quantity
                # NOTE: created_by column doesn't exist in pms_parts table
                "created_at": now,
                "updated_at": now,
            }

            # Insert part (RLS enforces yacht isolation)
            part_insert_result = self.db.table("pms_parts").insert(part_payload).execute()

            if not part_insert_result.data or len(part_insert_result.data) == 0:
                builder.set_error("EXECUTION_FAILED", "Failed to create part", 500)
                return builder.build()

            # ============================================================
            # UPDATE SHOPPING LIST ITEM
            # ============================================================

            update_payload = {
                "part_id": new_part_id,  # Link to new part
                "is_candidate_part": False,  # No longer a candidate
                "candidate_promoted_to_part_id": new_part_id,
                "promoted_by": user_id,
                "promoted_at": now,
                "updated_by": user_id,
                "updated_at": now,
            }

            update_result = self.db.table("pms_shopping_list_items").update(
                update_payload
            ).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data or len(update_result.data) == 0:
                # Rollback part creation (manual cleanup)
                try:
                    self.db.table("pms_parts").delete().eq("id", new_part_id).execute()
                except Exception:
                    logger.error(f"Failed to rollback part creation: {new_part_id}")

                builder.set_error("EXECUTION_FAILED", "Failed to update shopping list item", 500)
                return builder.build()

            # ============================================================
            # AUDIT LOG
            # ============================================================

            audit_payload = {
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": "shopping_list_item",
                "entity_id": entity_id,
                "action": "promote_candidate_to_part",
                "user_id": user_id,
                "old_values": {
                    "is_candidate_part": True,
                    "part_id": None,
                },
                "new_values": {
                    "is_candidate_part": False,
                    "part_id": new_part_id,
                    "part_name": item["part_name"],
                },
                "signature": {},  # Non-signed action
                "metadata": {"source": "shopping_list_lens", "new_part_id": new_part_id},
                "created_at": now,
            }

            try:
                self.db.table("pms_audit_log").insert(audit_payload).execute()
            except Exception as audit_err:
                logger.warning(f"Audit log insert failed (non-critical): {audit_err}")

            # ============================================================
            # RESPONSE
            # ============================================================

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

    # =========================================================================
    # READ HANDLERS
    # =========================================================================

    async def view_shopping_list_history(
        self,
        entity_id: str,  # shopping_list_item_id
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View state change timeline for shopping list item.

        Allowed Roles: All Crew (read-only)

        Tables Read:
        - pms_shopping_list_state_history
        - auth_users_profiles (for user names)

        Returns:
        - 200 + timeline of state changes
        - 404 if item not found
        """
        builder = ResponseBuilder(
            "view_shopping_list_history",
            entity_id,
            "shopping_list_item",
            yacht_id
        )

        try:
            params = params or {}

            # ============================================================
            # FETCH STATE HISTORY
            # ============================================================

            history_result = self.db.table("pms_shopping_list_state_history").select(
                """
                id,
                previous_state,
                new_state,
                transition_reason,
                transition_notes,
                changed_by,
                changed_at,
                related_order_id,
                related_receiving_event_id,
                metadata
                """
            ).eq("shopping_list_item_id", entity_id).eq(
                "yacht_id", yacht_id
            ).order("changed_at", desc=True).execute()

            if not history_result or not history_result.data:
                # No history found (possibly item doesn't exist or no state changes yet)
                # Check if item exists
                item_result = self.db.table("pms_shopping_list_items").select(
                    "id"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not item_result or not item_result.data:
                    builder.set_error("NOT_FOUND", f"Shopping list item not found: {entity_id}", 404)
                    return builder.build()

                # Item exists but no history yet
                builder.set_data({
                    "shopping_list_item_id": entity_id,
                    "history": [],
                    "message": "No state changes recorded yet"
                })
                return builder.build()

            # ============================================================
            # ENRICH HISTORY WITH USER NAMES
            # ============================================================

            history = history_result.data
            user_ids = list(set([h["changed_by"] for h in history if h.get("changed_by")]))

            # Fetch user names
            user_map = {}
            if user_ids:
                users_result = self.db.table("auth_users_profiles").select(
                    "id, name"
                ).in_("id", user_ids).execute()

                if users_result.data:
                    user_map = {u["id"]: u["name"] for u in users_result.data}

            # Add user names to history
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
# HANDLER FACTORY
# =============================================================================

def get_shopping_list_handlers(supabase_client):
    """Factory function to create shopping list handlers."""
    return ShoppingListHandlers(supabase_client)
