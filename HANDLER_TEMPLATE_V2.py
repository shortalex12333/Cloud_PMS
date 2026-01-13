"""
{CLUSTER_NAME} Domain Mutation Handlers
========================================

Group {CLUSTER_ID}: {CLUSTER_NAME} CLUSTER

Handlers:
- {action_1}_execute: {brief description}
- {action_2}_execute: {brief description}

PATTERN FREEZE: Follows commit_receiving_session pattern.
DO NOT simplify G0 guards.
"""

from datetime import datetime, timezone
from typing import Dict, Optional
import logging
import uuid

from action_response_schema import ResponseBuilder, AvailableAction, Severity

logger = logging.getLogger(__name__)


class {ClusterName}MutationHandlers:
    """
    {Cluster name} mutation handlers.

    LOCKED PATTERNS (G0 - DO NOT MODIFY):
    1. Yacht Isolation (G0.1)
    2. Authentication (G0.2)
    3. Role Check (G0.3)
    4. Audit Trail (G0.6)
    5. Situation Context (G0.9) - MUTATE_HIGH only
    """

    def __init__(self, supabase_client):
        self.db = supabase_client


    async def {action_name}_execute(
        self,
        entity_id: str,
        yacht_id: str,  # NEVER trust - always validate
        params: Dict
    ) -> Dict:
        """
        {Action description}

        Classification: {READ | MUTATE_LOW | MUTATE_MEDIUM | MUTATE_HIGH}
        Tables: {table1, table2, ...}
        """

        # ==============================================================
        # GUARDS DECLARATION (Required by CI)
        # ==============================================================
        GUARDS = {
            "G0.1": True,           # Yacht isolation
            "G0.2": True,           # Authentication
            "G0.3": True,           # Role check
            "G0.4": "conditional",  # Transactions (if multi-table)
            "G0.5": False,          # Idempotency (not needed)
            "G0.6": True,           # Audit trail
            "G0.7": False,          # State machine (not applicable)
            "G0.8": False,          # Signature (not required)
            "G0.9": True            # Situation ID (if MUTATE_HIGH)
        }

        builder = ResponseBuilder("{action_name}", entity_id, "{entity_type}", yacht_id)

        try:
            # ==========================================================
            # G0.2: AUTHENTICATION GATE
            # ==========================================================
            user_id = params.get("user_id")
            if not user_id:
                return builder.error("UNAUTHORIZED", "Not authenticated")

            # ==========================================================
            # G0.1: YACHT ISOLATION (CRITICAL)
            # ==========================================================
            user = await self.db.table("user_profiles").select(
                "yacht_id, role, full_name"
            ).eq("id", user_id).single().execute()

            if not user.data or user.data["yacht_id"] != yacht_id:
                logger.critical(
                    f"SECURITY: Yacht breach by {user_id}. "
                    f"Attempted: {yacht_id}, Actual: {user.data['yacht_id'] if user.data else None}"
                )
                return builder.error("FORBIDDEN", "Access denied")

            # ==========================================================
            # G0.3: ROLE-BASED ACCESS CONTROL
            # ==========================================================
            allowed_roles = ["{role1}", "{role2}", "{role3}"]  # From catalog

            if user.data["role"] not in allowed_roles:
                return builder.error(
                    "FORBIDDEN",
                    f"Role '{user.data['role']}' cannot {action_name}"
                )

            # ==========================================================
            # G0.9: SITUATION CONTEXT (if MUTATE_HIGH)
            # ==========================================================
            # UNCOMMENT FOR MUTATE_HIGH:
            # situation_id = params.get("situation_id")
            # if not situation_id:
            #     return builder.error(
            #         "VALIDATION_FAILED",
            #         "situation_id required for MUTATE_HIGH actions"
            #     )

            # ==========================================================
            # G1.3: INPUT VALIDATION
            # ==========================================================
            required_fields = ["{field1}", "{field2}"]
            missing = [f for f in required_fields if not params.get(f)]
            if missing:
                return builder.error("VALIDATION_FAILED", f"Missing: {', '.join(missing)}")

            # Validate data types, ranges, etc.
            # if params.get("{quantity}") and params["{quantity}"] <= 0:
            #     return builder.error("VALIDATION_FAILED", "Quantity must be > 0")

            # ==========================================================
            # G1.7: FOREIGN KEY VALIDATION
            # ==========================================================
            # Validate referenced entities exist
            # if params.get("{related_id}"):
            #     related = await self.db.table("{related_table}").select("id").eq(
            #         "id", params["{related_id}"]
            #     ).eq("yacht_id", yacht_id).single().execute()
            #
            #     if not related.data:
            #         return builder.error("NOT_FOUND", f"{Related} not found")

            # ==========================================================
            # EXECUTE MUTATION
            # ==========================================================
            logger.info(f"Executing {action_name} for {entity_type} {entity_id}")

            # G0.4: TRANSACTION (if multi-table)
            # async with self.db.transaction():
            #     ... mutations

            # Example: UPDATE
            # updated_at = datetime.now(timezone.utc).isoformat()
            # result = await self.db.table("{table}").update({
            #     "{field}": params["{field}"],
            #     "updated_at": updated_at
            # }).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

            # Example: INSERT
            # new_id = str(uuid.uuid4())
            # result = await self.db.table("{table}").insert({
            #     "id": new_id,
            #     "yacht_id": yacht_id,  # ALWAYS set
            #     "{field}": params["{field}"],
            #     "created_by": user_id,
            #     "created_by_name": user.data["full_name"],
            #     "created_at": datetime.now(timezone.utc).isoformat()
            # }).execute()

            # ==========================================================
            # G0.6: AUDIT TRAIL (MANDATORY)
            # ==========================================================
            await self.db.table("pms_audit_log").insert({
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "action": "{action_name}",
                "entity_type": "{entity_type}",
                "entity_id": entity_id,
                "user_id": user_id,
                "user_name": user.data["full_name"],
                "user_role": user.data["role"],
                # "old_values": old_values,  # For UPDATE
                "new_values": {"{field}": params["{field}"]},
                "changes_summary": f"{user.data['full_name']} {action_description}",
                "risk_level": "{low|medium|high}",
                # "situation_id": situation_id,  # If MUTATE_HIGH
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()

            logger.info(f"Success: {action_name} for {entity_type} {entity_id}")

            # ==========================================================
            # RESPONSE
            # ==========================================================
            builder.set_data({
                "entity_id": entity_id,
                # Add result fields
            })

            # G3.2: Follow-up actions
            # builder.add_action(AvailableAction(
            #     action_id="view_{entity_type}",
            #     label="View {Entity}",
            #     entity_type="{entity_type}",
            #     entity_id=entity_id
            # ))

            builder.set_message(f"{Entity} updated successfully", Severity.SUCCESS)

        except Exception as e:
            logger.error(f"{action_name} failed: {e}", exc_info=True)
            builder.set_error("EXECUTION_FAILED", str(e))

        return builder.build()


# Export
def get_{cluster_name}_mutation_handlers(supabase_client):
    return {ClusterName}MutationHandlers(supabase_client)
