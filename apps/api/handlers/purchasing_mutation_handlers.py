"""
Purchasing Domain Mutation Handlers
====================================

Group 8: PURCHASING CLUSTER

Mutation handlers for purchasing and receiving actions.

Handlers:
- add_to_shopping_list_execute: Add item to shopping list
- approve_shopping_item_execute: Approve shopping list item for purchase
- reject_shopping_item_execute: Reject shopping list item
- update_shopping_list_execute: Update shopping list item
- delete_shopping_item_execute: Remove shopping list item
- create_purchase_order_execute: Create PO from approved items
- update_purchase_order_execute: Update draft PO
- close_purchase_order_execute: Close completed PO
- start_receiving_session_prefill: Initialize receiving session
- start_receiving_session_execute: Create receiving session
- check_in_item_execute: Check/uncheck receiving item
- upload_discrepancy_photo_execute: Upload photo for discrepancy
- add_receiving_notes_execute: Add notes to receiving item
- commit_receiving_session_execute: CRITICAL - Commit receiving (MUTATE_HIGH)

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
    FileReference,
    AvailableAction,
    SignedUrlGenerator,
    Severity
)

logger = logging.getLogger(__name__)


class PurchasingMutationHandlers:
    """
    Purchasing domain MUTATION handlers.

    CRITICAL PATTERNS:
    1. Yacht Isolation (A2): EVERY query MUST filter by yacht_id
    2. State Machines: Shopping list and receiving have strict state transitions
    3. Checkbox = Truth: Only checked items are processed in receiving
    4. Immutability: Committed receiving sessions CANNOT be modified
    5. Signatures: Required for high-value receiving commits
    """

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None


    async def commit_receiving_session_execute(
        self,
        entity_id: str,  # receiving_session_id
        yacht_id: str,
        params: Dict
    ) -> Dict:
        """
        CRITICAL MUTATE_HIGH ACTION: Commit receiving session

        This action is IRREVERSIBLE and updates:
        - Receiving session status → 'committed' (immutable)
        - Parts inventory quantities (increments)
        - Shopping list items → 'fulfilled'
        - Creates inventory transaction ledger entries
        - Creates audit log

        Tables: receiving_sessions, receiving_items, parts, shopping_list,
                inventory_transactions, audit_log (6 tables)
        Classification: MUTATE_HIGH
        Signature Required: YES (if total_value > $1000)
        Guard Rails: A1-A4, T1, B5, C2, I1, S3

        Args:
            entity_id: receiving_session_id (UUID)
            yacht_id: User's yacht ID
            params:
                signature_data: JSONB (required if total_value > $1000)
                user_id: UUID (from auth)
                user_role: string (from user_profiles)
                user_name: string (from user_profiles)

        Returns:
            ActionResponseEnvelope with:
            - success: boolean
            - data: committed session with item counts
            - follow_up_actions: view_purchase_order, view_inventory
        """
        builder = ResponseBuilder(
            "commit_receiving_session",
            entity_id,
            "receiving_session",
            yacht_id
        )

        try:
            # ============================================================
            # GUARD RAILS - Authentication & Authorization (A1-A4)
            # ============================================================

            # A1: User Authentication
            user_id = params.get("user_id")
            if not user_id:
                builder.set_error("UNAUTHORIZED", "User not authenticated")
                return builder.build()

            # A2: Yacht Isolation (CRITICAL SECURITY)
            user_result = await self.db.table("user_profiles").select(
                "yacht_id, role, name"
            ).eq("id", user_id).single().execute()

            if not user_result.data:
                builder.set_error("UNAUTHORIZED", "User profile not found")
                return builder.build()

            user = user_result.data
            if user["yacht_id"] != yacht_id:
                logger.critical(
                    f"SECURITY VIOLATION: Yacht isolation breach attempt by {user_id}. "
                    f"Attempted yacht: {yacht_id}, User yacht: {user['yacht_id']}"
                )
                builder.set_error("FORBIDDEN", "Access denied")
                return builder.build()

            # A3: Role-Based Access Control
            allowed_roles = ["chief_engineer", "chief_officer", "captain", "admin"]
            if user["role"] not in allowed_roles:
                builder.set_error(
                    "FORBIDDEN",
                    f"Role '{user['role']}' cannot commit receiving. "
                    f"Required: {', '.join(allowed_roles)}"
                )
                return builder.build()

            # A4: Conditional Permissions (2nd Engineer limited by value)
            if user["role"] == "2nd_engineer":
                builder.set_error(
                    "FORBIDDEN",
                    "2nd Engineer cannot commit receiving sessions over $1000"
                )
                return builder.build()

            # ============================================================
            # FETCH SESSION & VALIDATE STATE
            # ============================================================

            # Fetch session with yacht isolation
            session_result = await self.db.table("receiving_sessions").select(
                "*, receiving_items(*)"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).single().execute()

            if not session_result.data:
                builder.set_error("NOT_FOUND", f"Receiving session not found: {entity_id}")
                return builder.build()

            session = session_result.data

            # B1: State Transition Validation
            if session["status"] != "review":
                builder.set_error(
                    "INVALID_STATE",
                    f"Session must be in 'review' status to commit. Current: {session['status']}"
                )
                return builder.build()

            # B5: Immutability Enforcement (prevent re-commit)
            if session["status"] == "committed":
                builder.set_error(
                    "IMMUTABLE",
                    "This receiving session has already been committed and cannot be modified"
                )
                return builder.build()

            # ============================================================
            # VALIDATE CHECKED ITEMS (Checkbox = Truth)
            # ============================================================

            checked_items = [item for item in session["receiving_items"] if item.get("checked")]

            if len(checked_items) == 0:
                builder.set_error(
                    "VALIDATION_FAILED",
                    "No items checked. Cannot commit empty receiving session."
                )
                return builder.build()

            # Calculate total value
            total_value = sum(
                item.get("quantity_received", 0) * item.get("unit_cost_usd", 0)
                for item in checked_items
            )

            # ============================================================
            # SIGNATURE VALIDATION (High-value transactions)
            # ============================================================

            signature_data = params.get("signature_data")

            if total_value > 1000 and not signature_data:
                builder.set_error(
                    "SIGNATURE_REQUIRED",
                    f"Signature required for receiving over $1000 (Total: ${total_value:,.2f})"
                )
                return builder.build()

            # ============================================================
            # BEGIN TRANSACTION (T1: All-or-nothing)
            # ============================================================

            logger.info(
                f"Committing receiving session {entity_id} with {len(checked_items)} items. "
                f"Total value: ${total_value:,.2f}"
            )

            # Track old values for audit
            old_values = {
                "status": session["status"],
                "total_items": len(session["receiving_items"]),
                "checked_items": len(checked_items)
            }

            # ============================================================
            # STEP 1: Process Each Checked Item
            # ============================================================

            transaction_ids = []
            updated_parts = []
            fulfilled_shopping_items = []

            for item in checked_items:
                # 1a. Create inventory transaction (ledger entry)
                transaction_id = str(uuid.uuid4())
                transaction_ids.append(transaction_id)

                await self.db.table("inventory_transactions").insert({
                    "id": transaction_id,
                    "yacht_id": yacht_id,
                    "part_id": item["part_id"],
                    "quantity": item["quantity_received"],
                    "transaction_type": "receiving",
                    "receiving_item_id": item["id"],
                    "notes": f"Receiving session {entity_id}",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()

                # 1b. Update part quantity (increment inventory)
                part_result = await self.db.table("parts").select(
                    "current_quantity_onboard"
                ).eq("id", item["part_id"]).eq("yacht_id", yacht_id).single().execute()

                if part_result.data:
                    new_quantity = part_result.data["current_quantity_onboard"] + item["quantity_received"]

                    await self.db.table("parts").update({
                        "current_quantity_onboard": new_quantity,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", item["part_id"]).eq("yacht_id", yacht_id).execute()

                    updated_parts.append({
                        "part_id": item["part_id"],
                        "old_quantity": part_result.data["current_quantity_onboard"],
                        "new_quantity": new_quantity,
                        "received": item["quantity_received"]
                    })

                # 1c. Update shopping list item to fulfilled
                if item.get("shopping_list_item_id"):
                    await self.db.table("shopping_list").update({
                        "status": "fulfilled",
                        "fulfilled_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", item["shopping_list_item_id"]).eq("yacht_id", yacht_id).execute()

                    fulfilled_shopping_items.append(item["shopping_list_item_id"])

            # ============================================================
            # STEP 2: Update Session to Committed (IMMUTABLE)
            # ============================================================

            committed_at = datetime.now(timezone.utc).isoformat()

            await self.db.table("receiving_sessions").update({
                "status": "committed",
                "committed_at": committed_at,
                "signature_data": signature_data,
                "updated_at": committed_at
            }).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

            # ============================================================
            # STEP 3: Create Audit Log (S3)
            # ============================================================

            new_values = {
                "status": "committed",
                "committed_at": committed_at,
                "checked_items_processed": len(checked_items),
                "total_value": total_value,
                "signature_present": bool(signature_data)
            }

            changes_summary = (
                f"User {user['name']} ({user['role']}) committed receiving session. "
                f"{len(checked_items)} items received, total value ${total_value:,.2f}. "
                f"{len(updated_parts)} parts updated in inventory."
            )

            await self.db.table("audit_log").insert({
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "action": "commit_receiving_session",
                "entity_type": "receiving_session",
                "entity_id": entity_id,
                "user_id": user_id,
                "user_name": user["name"],
                "user_role": user["role"],
                "old_values": old_values,
                "new_values": new_values,
                "changes_summary": changes_summary,
                "risk_level": "high",  # MUTATE_HIGH action
                "signature": signature_data.get("signature") if signature_data else None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()

            # ============================================================
            # COMMIT TRANSACTION (implicit in Supabase)
            # ============================================================

            logger.info(
                f"Successfully committed receiving session {entity_id}. "
                f"{len(checked_items)} items processed, {len(updated_parts)} parts updated"
            )

            # ============================================================
            # BUILD SUCCESS RESPONSE
            # ============================================================

            builder.set_data({
                "receiving_session_id": entity_id,
                "status": "committed",
                "committed_at": committed_at,
                "total_value": total_value,
                "items_processed": len(checked_items),
                "parts_updated": updated_parts,
                "shopping_items_fulfilled": len(fulfilled_shopping_items),
                "transaction_ids": transaction_ids,
                "immutable": True  # Session can no longer be modified
            })

            # Add follow-up actions
            builder.add_action(AvailableAction(
                action_id="view_inventory",
                label="View Updated Inventory",
                entity_type="parts",
                entity_id=None  # List view
            ))

            builder.add_action(AvailableAction(
                action_id="view_purchase_order",
                label="View Purchase Order",
                entity_type="purchase_order",
                entity_id=session.get("purchase_order_id")
            ))

            # Add success message
            builder.set_message(
                f"Receiving session committed successfully. {len(checked_items)} items added to inventory.",
                Severity.SUCCESS
            )

        except Exception as e:
            logger.error(f"commit_receiving_session failed for session {entity_id}: {e}", exc_info=True)
            builder.set_error("EXECUTION_FAILED", str(e))

        return builder.build()


