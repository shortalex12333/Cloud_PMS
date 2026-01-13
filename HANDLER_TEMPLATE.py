"""
{CLUSTER_NAME} Domain Mutation Handlers
========================================

Group {CLUSTER_ID}: {CLUSTER_NAME} CLUSTER

Mutation handlers for {cluster_description} actions.

G0 COMPLIANCE CHECKLIST (MANDATORY - DO NOT SKIP):
✅ G0.1: Yacht isolation (A2) - CRITICAL SECURITY
✅ G0.2: Authentication gate (A1)
✅ G0.3: Role-based access (A3)
□ G0.4: Atomic transactions (T1) [if multi-table mutation]
□ G0.5: Idempotency (T2) [if MUTATE_HIGH or financial]
✅ G0.6: Audit trail (S3) - ALL mutations
□ G0.7: State machine (B1) [if state-based entity]
□ G0.8: Signature (if required by action catalog)

G1 COMPLIANCE (Required with explicit waiver if missing):
□ G1.1: Concurrency control (C1) - Row locks/version checks
□ G1.2: Deduplication checks (B3) - Prevent duplicate creation
□ G1.3: Input schema validation (D1-D6) - Strict validation
□ G1.4: SQL injection prevention (D2) - Parameterized queries only
□ G1.5: XSS prevention (D3) - Sanitize user input
□ G1.6: Immutability enforcement (B5) - Cannot modify committed records
□ G1.7: Referential integrity (I2, I5) - Validate foreign keys exist
□ G1.8: Sensitive data redaction (S2) - Never log secrets
□ G1.9: Rate limiting (C3) - Prevent abuse
□ G1.10: Compensating actions - Preserve history instead of destructive updates
□ G1.11: SECURITY DEFINER locked - Privileged functions check permissions internally

G2 COMPLIANCE (Recommended - track as tech debt if missing):
□ G2.1: Structured metrics (M1) - Performance tracking
□ G2.2: Query timeouts (P1) - Prevent runaway queries
□ G2.3: Result set limits (P2) - Prevent memory overflow
□ G2.4: Retry policy + DLQ (T3) - Handle transient failures
□ G2.5: Partial failure reporting (H1) - Per-row errors
□ G2.6: Background job isolation - Long tasks don't block API
□ G2.7: Health checks (M2) - System monitoring
□ G2.8: Action tracing (M3) - Distributed tracing

Handlers:
- {action_1_name}_execute: {brief description}
- {action_2_name}_prefill: {brief description}
- {action_2_name}_preview: {brief description}
- {action_2_name}_execute: {brief description}

All handlers return standardized ActionResponseEnvelope.

PATTERN FREEZE: This handler follows the pattern from commit_receiving_session.
DO NOT simplify or deviate without architectural review.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action_response_schema import (
    ResponseBuilder,
    FileReference,
    AvailableAction,
    SignedUrlGenerator,
    Severity
)

logger = logging.getLogger(__name__)


class {ClusterName}MutationHandlers:
    """
    {Cluster name} domain MUTATION handlers.

    CRITICAL PATTERNS (DO NOT MODIFY):
    1. Yacht Isolation (G0.1): EVERY query MUST filter by yacht_id derived from user profile
    2. Authentication (G0.2): EVERY handler validates user_id exists
    3. RBAC (G0.3): EVERY handler checks role against allowed list
    4. Audit Trail (G0.6): EVERY MUTATE action creates pms_audit_log entry
    5. [Add cluster-specific patterns here]
    """

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None


    async def {action_name}_execute(
        self,
        entity_id: str,  # Entity ID (or None for CREATE operations)
        yacht_id: str,   # NEVER trust this - always validate against user's yacht
        params: Dict
    ) -> Dict:
        """
        {Action description from catalog}

        Tables: {list affected tables}
        Classification: {READ | MUTATE_LOW | MUTATE_MEDIUM | MUTATE_HIGH}
        Guard Rails: {G0.X, G1.Y from catalog}

        Args:
            entity_id: {Entity type} ID (UUID)
            yacht_id: User's yacht ID (VALIDATED, not trusted)
            params:
                user_id: UUID (from auth.uid())
                user_role: string (from user_profiles)
                user_name: string (from user_profiles)
                {other required params}

        Returns:
            ActionResponseEnvelope with:
            - success: boolean
            - data: {result data}
            - follow_up_actions: {suggested next actions}
        """
        builder = ResponseBuilder(
            "{action_name}",
            entity_id,
            "{entity_type}",
            yacht_id
        )

        try:
            # ============================================================
            # G0 GUARD RAILS - MANDATORY (DO NOT SKIP)
            # ============================================================

            # G0.2: Authentication Gate
            user_id = params.get("user_id")
            if not user_id or user_id == "undefined":
                builder.set_error("UNAUTHORIZED", "User not authenticated")
                return builder.build()

            # G0.1: Yacht Isolation (CRITICAL SECURITY BOUNDARY)
            user_result = await self.db.table("user_profiles").select(
                "yacht_id, role, full_name"
            ).eq("id", user_id).single().execute()

            if not user_result.data:
                builder.set_error("UNAUTHORIZED", "User profile not found")
                return builder.build()

            user = user_result.data

            # CRITICAL: Validate yacht_id matches user's yacht
            if user["yacht_id"] != yacht_id:
                logger.critical(
                    f"SECURITY VIOLATION: Yacht isolation breach attempt by {user_id}. "
                    f"Attempted yacht: {yacht_id}, User yacht: {user['yacht_id']}"
                )
                builder.set_error("FORBIDDEN", "Access denied")
                return builder.build()

            # G0.3: Role-Based Access Control
            # REPLACE WITH ACTUAL ALLOWED ROLES FROM ACTION CATALOG
            allowed_roles = ["chief_engineer", "captain", "admin"]

            if user["role"] not in allowed_roles:
                builder.set_error(
                    "FORBIDDEN",
                    f"Role '{user['role']}' cannot perform {action_name}. "
                    f"Required: {', '.join(allowed_roles)}"
                )
                return builder.build()

            # G0.4: Conditional Permissions (if applicable)
            # Example: 2nd Engineer has value limits
            # if user["role"] == "2nd_engineer" and total_value > 1000:
            #     builder.set_error("FORBIDDEN", "2nd Engineer limited to $1000")
            #     return builder.build()

            # ============================================================
            # G1 GUARD RAILS - CRITICAL SAFETY
            # ============================================================

            # G1.3: Input Validation - Required Fields
            required_fields = ["field1", "field2"]  # Replace with actual fields
            missing = [f for f in required_fields if not params.get(f)]
            if missing:
                builder.set_error(
                    "VALIDATION_FAILED",
                    f"Missing required fields: {', '.join(missing)}"
                )
                return builder.build()

            # G1.3: Input Validation - Data Types & Ranges
            # Example: Quantity must be > 0
            # if params.get("quantity") and params["quantity"] <= 0:
            #     builder.set_error("VALIDATION_FAILED", "Quantity must be > 0")
            #     return builder.build()

            # G1.3: Input Validation - String Length Limits
            # if len(params.get("description", "")) > 5000:
            #     builder.set_error("VALIDATION_FAILED", "Description too long (max 5000)")
            #     return builder.build()

            # G1.4: Enum Validation
            # valid_statuses = ["draft", "active", "completed"]
            # if params.get("status") not in valid_statuses:
            #     builder.set_error("VALIDATION_FAILED", f"Invalid status: {params['status']}")
            #     return builder.build()

            # G1.7: Foreign Key Validation - Validate entities exist in same yacht
            # if params.get("part_id"):
            #     part = await self.db.table("parts").select("id").eq(
            #         "id", params["part_id"]
            #     ).eq("yacht_id", yacht_id).single().execute()
            #
            #     if not part.data:
            #         builder.set_error("NOT_FOUND", f"Part not found: {params['part_id']}")
            #         return builder.build()

            # ============================================================
            # FETCH ENTITY (if updating existing)
            # ============================================================

            # For UPDATE/DELETE operations, fetch existing entity first
            # entity_result = await self.db.table("{table_name}").select("*").eq(
            #     "id", entity_id
            # ).eq("yacht_id", yacht_id).single().execute()
            #
            # if not entity_result.data:
            #     builder.set_error("NOT_FOUND", f"{entity_type} not found: {entity_id}")
            #     return builder.build()
            #
            # entity = entity_result.data

            # ============================================================
            # STATE VALIDATION (G0.7 if applicable)
            # ============================================================

            # VALID_TRANSITIONS = {
            #     'draft': ['active', 'cancelled'],
            #     'active': ['completed', 'cancelled'],
            #     'completed': [],  # Terminal
            #     'cancelled': []   # Terminal
            # }
            #
            # current_status = entity["status"]
            # new_status = params.get("status")
            #
            # if new_status and new_status not in VALID_TRANSITIONS.get(current_status, []):
            #     builder.set_error(
            #         "INVALID_STATE",
            #         f"Cannot transition from {current_status} to {new_status}"
            #     )
            #     return builder.build()

            # ============================================================
            # IMMUTABILITY CHECK (G1.6 if applicable)
            # ============================================================

            # IMMUTABLE_STATES = ["committed", "closed"]
            # if entity.get("status") in IMMUTABLE_STATES:
            #     builder.set_error(
            #         "IMMUTABLE",
            #         f"Cannot modify {entity_type} in {entity['status']} state"
            #     )
            #     return builder.build()

            # ============================================================
            # CONCURRENCY CONTROL (G1.1 if needed)
            # ============================================================

            # Optimistic locking with version field
            # expected_version = params.get("version")
            # if entity.get("version") != expected_version:
            #     builder.set_error(
            #         "CONFLICT",
            #         "Entity was modified by another user. Please refresh and try again."
            #     )
            #     return builder.build()

            # ============================================================
            # SIGNATURE VALIDATION (G0.8 if required)
            # ============================================================

            # signature_data = params.get("signature_data")
            # if signature_required and not signature_data:
            #     builder.set_error(
            #         "SIGNATURE_REQUIRED",
            #         f"Signature required for {action_name}"
            #     )
            #     return builder.build()

            # ============================================================
            # EXECUTE MUTATION (G0.4 - Atomic if multi-table)
            # ============================================================

            logger.info(
                f"Executing {action_name} for {entity_type} {entity_id} "
                f"by {user['full_name']} ({user['role']})"
            )

            # Track old values for audit (G0.6)
            # old_values = {k: entity.get(k) for k in ["field1", "field2", "status"]}

            # BEGIN TRANSACTION (implicit in Supabase, explicit with async context)
            # For multi-table operations:
            # async with self.db.transaction():

            # Example: UPDATE operation
            # updated_at = datetime.now(timezone.utc).isoformat()
            #
            # update_result = await self.db.table("{table_name}").update({
            #     "field1": params["field1"],
            #     "field2": params["field2"],
            #     "updated_at": updated_at,
            #     "version": entity.get("version", 0) + 1  # Increment version
            # }).eq("id", entity_id).eq("yacht_id", yacht_id).execute()
            #
            # if not update_result.data:
            #     builder.set_error("EXECUTION_FAILED", "Update failed")
            #     return builder.build()
            #
            # updated_entity = update_result.data[0]

            # Example: INSERT operation (CREATE)
            # new_id = str(uuid.uuid4())
            # created_at = datetime.now(timezone.utc).isoformat()
            #
            # insert_result = await self.db.table("{table_name}").insert({
            #     "id": new_id,
            #     "yacht_id": yacht_id,  # ALWAYS set yacht_id
            #     "field1": params["field1"],
            #     "field2": params["field2"],
            #     "created_by": user_id,
            #     "created_by_name": user["full_name"],
            #     "created_by_role": user["role"],
            #     "created_at": created_at
            # }).execute()
            #
            # if not insert_result.data:
            #     builder.set_error("EXECUTION_FAILED", "Insert failed")
            #     return builder.build()
            #
            # new_entity = insert_result.data[0]

            # COMMIT TRANSACTION (implicit on success)

            # ============================================================
            # CREATE AUDIT LOG (G0.6 - MANDATORY FOR ALL MUTATIONS)
            # ============================================================

            # new_values = {
            #     "field1": params["field1"],
            #     "field2": params["field2"],
            #     "status": updated_entity.get("status")
            # }
            #
            # changes_summary = (
            #     f"User {user['full_name']} ({user['role']}) updated {entity_type} {entity_id}. "
            #     f"Changed: {', '.join(new_values.keys())}"
            # )
            #
            # await self.db.table("pms_audit_log").insert({
            #     "id": str(uuid.uuid4()),
            #     "yacht_id": yacht_id,
            #     "action": "{action_name}",
            #     "entity_type": "{entity_type}",
            #     "entity_id": entity_id or new_id,
            #     "user_id": user_id,
            #     "user_name": user["full_name"],
            #     "user_role": user["role"],
            #     "old_values": old_values,  # For UPDATE operations
            #     "new_values": new_values,
            #     "changes_summary": changes_summary,
            #     "risk_level": "{low | medium | high}",  # From action catalog
            #     "signature": signature_data.get("signature") if signature_data else None,
            #     "created_at": datetime.now(timezone.utc).isoformat()
            # }).execute()

            logger.info(
                f"Successfully executed {action_name} for {entity_type} {entity_id}"
            )

            # ============================================================
            # BUILD SUCCESS RESPONSE
            # ============================================================

            builder.set_data({
                "entity_id": entity_id,
                # Include relevant updated fields
                # "field1": updated_entity["field1"],
                # "status": updated_entity["status"],
                # "updated_at": updated_entity["updated_at"]
            })

            # Add follow-up actions (G3.2 - UX enhancement)
            # builder.add_action(AvailableAction(
            #     action_id="view_{entity_type}",
            #     label=f"View {Entity Type}",
            #     entity_type="{entity_type}",
            #     entity_id=entity_id
            # ))

            # Add success message (G3.4 - UX feedback)
            builder.set_message(
                f"{Entity type} updated successfully",
                Severity.SUCCESS
            )

        except Exception as e:
            logger.error(
                f"{action_name} failed for {entity_type} {entity_id}: {e}",
                exc_info=True
            )
            builder.set_error("EXECUTION_FAILED", str(e))

        return builder.build()


# Export handler class
def get_{cluster_name}_mutation_handlers(supabase_client):
    """Factory function to create {cluster name} mutation handlers"""
    return {ClusterName}MutationHandlers(supabase_client)
