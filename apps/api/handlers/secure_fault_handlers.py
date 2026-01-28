"""
Secure Fault Mutation Handlers
===============================

Wraps fault_mutation_handlers with @secure_action decorator for
security enforcement (Phase 2).

Security invariants enforced:
1. Yacht context from auth (never payload)
2. Ownership validation for fault_id
3. Idempotency for all MUTATE actions
4. Yacht freeze blocks mutations
5. Role-based access control

Usage:
    from handlers.secure_fault_handlers import get_secure_fault_handlers
    handlers = get_secure_fault_handlers(supabase_client)
"""

from typing import Dict, Optional, Any
import logging

from middleware.action_security import (
    secure_action,
    ActionContext,
    build_audit_entry,
)
from handlers.fault_mutation_handlers import (
    FaultMutationHandlers,
    map_severity,
    infer_severity_from_text,
    VALID_SEVERITIES,
    STATUS_TRANSITIONS,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ROLE DEFINITIONS
# ============================================================================

# Roles allowed for each action
CREW_ROLES = ["crew", "hod", "chief_engineer", "captain", "manager", "purser"]
HOD_ROLES = ["hod", "chief_engineer", "captain", "manager"]
CAPTAIN_ROLES = ["captain", "manager"]


# ============================================================================
# SECURED HANDLER WRAPPERS
# ============================================================================

def create_secure_fault_handlers(db_client) -> Dict[str, Any]:
    """
    Create secured fault handlers with @secure_action decorator.

    Args:
        db_client: Supabase client for TENANT DB

    Returns:
        Dict of action_name -> secured handler function
    """
    # Create underlying handler instance
    handlers = FaultMutationHandlers(db_client)

    # =========================================================================
    # REPORT FAULT (crew can report)
    # =========================================================================

    @secure_action(
        action_id="report_fault",
        action_group="MUTATE",
        required_roles=CREW_ROLES,
        validate_entities=["equipment_id"],  # Optional, validates if provided
    )
    async def report_fault(ctx: ActionContext, **params):
        """Report a new fault (secured wrapper)."""
        return await handlers.report_fault_execute(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            title=params.get("title"),
            severity=params.get("severity", "minor"),
            description=params.get("description", ""),
            equipment_id=params.get("equipment_id"),
            signature=params.get("signature"),
        )

    @secure_action(
        action_id="report_fault_prefill",
        action_group="READ",
        required_roles=CREW_ROLES,
        validate_entities=["equipment_id"],
    )
    async def report_fault_prefill(ctx: ActionContext, **params):
        """Pre-fill fault report form (secured wrapper)."""
        return await handlers.report_fault_prefill(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            equipment_id=params.get("equipment_id"),
            query_text=params.get("query_text"),
        )

    @secure_action(
        action_id="report_fault_preview",
        action_group="READ",
        required_roles=CREW_ROLES,
        validate_entities=["equipment_id"],
    )
    async def report_fault_preview(ctx: ActionContext, **params):
        """Preview fault report (secured wrapper)."""
        return await handlers.report_fault_preview(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            title=params.get("title"),
            severity=params.get("severity"),
            equipment_id=params.get("equipment_id"),
            description=params.get("description", ""),
        )

    # =========================================================================
    # ACKNOWLEDGE FAULT (HOD/captain only)
    # =========================================================================

    @secure_action(
        action_id="acknowledge_fault",
        action_group="MUTATE",
        required_roles=HOD_ROLES,
        validate_entities=["fault_id"],
    )
    async def acknowledge_fault(ctx: ActionContext, **params):
        """Acknowledge a fault (secured wrapper)."""
        return await handlers.acknowledge_fault_execute(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            fault_id=params["fault_id"],
            notes=params.get("notes"),
            signature=params.get("signature"),
        )

    # =========================================================================
    # CLOSE FAULT (HOD/captain only)
    # =========================================================================

    @secure_action(
        action_id="close_fault",
        action_group="MUTATE",
        required_roles=HOD_ROLES,
        validate_entities=["fault_id"],
    )
    async def close_fault(ctx: ActionContext, **params):
        """Close a fault (secured wrapper)."""
        return await handlers.close_fault_execute(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            fault_id=params["fault_id"],
            resolution_notes=params.get("resolution_notes"),
            signature=params.get("signature"),
        )

    # =========================================================================
    # UPDATE FAULT (HOD/captain only)
    # =========================================================================

    @secure_action(
        action_id="update_fault",
        action_group="MUTATE",
        required_roles=HOD_ROLES,
        validate_entities=["fault_id"],
    )
    async def update_fault(ctx: ActionContext, **params):
        """Update fault details (secured wrapper)."""
        return await handlers.update_fault_execute(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            fault_id=params["fault_id"],
            severity=params.get("severity"),
            status=params.get("status"),
            title=params.get("title"),
            description=params.get("description"),
            signature=params.get("signature"),
        )

    # =========================================================================
    # REOPEN FAULT (HOD/captain only)
    # =========================================================================

    @secure_action(
        action_id="reopen_fault",
        action_group="MUTATE",
        required_roles=HOD_ROLES,
        validate_entities=["fault_id"],
    )
    async def reopen_fault(ctx: ActionContext, **params):
        """Reopen a closed fault (secured wrapper)."""
        return await handlers.reopen_fault_execute(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            fault_id=params["fault_id"],
            reason=params.get("reason", ""),
            signature=params.get("signature"),
        )

    # =========================================================================
    # MARK FALSE ALARM (HOD/captain only)
    # =========================================================================

    @secure_action(
        action_id="mark_fault_false_alarm",
        action_group="MUTATE",
        required_roles=HOD_ROLES,
        validate_entities=["fault_id"],
    )
    async def mark_fault_false_alarm(ctx: ActionContext, **params):
        """Mark fault as false alarm (secured wrapper)."""
        return await handlers.mark_fault_false_alarm_execute(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            fault_id=params["fault_id"],
            reason=params.get("reason"),
            signature=params.get("signature"),
        )

    # =========================================================================
    # ADD FAULT PHOTO (crew can add)
    # =========================================================================

    @secure_action(
        action_id="add_fault_photo",
        action_group="MUTATE",
        required_roles=CREW_ROLES,
        validate_entities=["fault_id"],
    )
    async def add_fault_photo(ctx: ActionContext, **params):
        """Add photo to fault (secured wrapper)."""
        return await handlers.add_fault_photo_execute(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            fault_id=params["fault_id"],
            photo_url=params["photo_url"],
            caption=params.get("caption"),
            signature=params.get("signature"),
        )

    # =========================================================================
    # ADD FAULT NOTE (crew can add)
    # =========================================================================

    @secure_action(
        action_id="add_fault_note",
        action_group="MUTATE",
        required_roles=CREW_ROLES,
        validate_entities=["fault_id"],
    )
    async def add_fault_note(ctx: ActionContext, **params):
        """Add note to fault (secured wrapper)."""
        return await handlers.add_fault_note_execute(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            fault_id=params["fault_id"],
            text=params["text"],
            signature=params.get("signature"),
        )

    # =========================================================================
    # DIAGNOSE FAULT (HOD/captain only)
    # =========================================================================

    @secure_action(
        action_id="diagnose_fault",
        action_group="MUTATE",
        required_roles=HOD_ROLES,
        validate_entities=["fault_id"],
    )
    async def diagnose_fault(ctx: ActionContext, **params):
        """Add diagnosis to fault (secured wrapper)."""
        return await handlers.diagnose_fault_execute(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            fault_id=params["fault_id"],
            diagnosis=params["diagnosis"],
            recommended_action=params.get("recommended_action"),
            signature=params.get("signature"),
        )

    # =========================================================================
    # CREATE WORK ORDER FROM FAULT (SIGNED - captain/manager only)
    # =========================================================================

    @secure_action(
        action_id="create_work_order_from_fault_prepare",
        action_group="READ",
        required_roles=CAPTAIN_ROLES,
        validate_entities=["fault_id"],
    )
    async def create_work_order_from_fault_prepare(ctx: ActionContext, **params):
        """Prepare work order from fault (secured wrapper)."""
        return await handlers.create_work_order_from_fault_prepare(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            fault_id=params["fault_id"],
            title=params.get("title"),
            priority=params.get("priority"),
            assigned_to=params.get("assigned_to"),
        )

    @secure_action(
        action_id="create_work_order_from_fault_commit",
        action_group="SIGNED",
        required_roles=CAPTAIN_ROLES,
        validate_entities=[],  # Validated via staged mutation
    )
    async def create_work_order_from_fault_commit(ctx: ActionContext, **params):
        """Commit work order from fault (secured wrapper)."""
        return await handlers.create_work_order_from_fault_commit(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            idempotency_token=params["idempotency_token"],
            signature=params["signature"],
            override_duplicate=params.get("override_duplicate", False),
        )

    @secure_action(
        action_id="create_work_order_from_fault",
        action_group="SIGNED",
        required_roles=CAPTAIN_ROLES,
        validate_entities=["fault_id"],
    )
    async def create_work_order_from_fault(ctx: ActionContext, **params):
        """Create work order from fault (secured wrapper)."""
        return await handlers.create_work_order_from_fault_execute(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            fault_id=params["fault_id"],
            signature=params["signature"],
            title=params.get("title"),
            priority=params.get("priority"),
            assigned_to=params.get("assigned_to"),
            override_duplicate=params.get("override_duplicate", False),
        )

    # Return all secured handlers
    return {
        # report_fault
        "report_fault_prefill": report_fault_prefill,
        "report_fault_preview": report_fault_preview,
        "report_fault": report_fault,

        # acknowledge_fault
        "acknowledge_fault": acknowledge_fault,

        # close_fault
        "close_fault": close_fault,

        # update_fault
        "update_fault": update_fault,

        # reopen_fault
        "reopen_fault": reopen_fault,

        # mark_fault_false_alarm
        "mark_fault_false_alarm": mark_fault_false_alarm,

        # add_fault_photo
        "add_fault_photo": add_fault_photo,

        # add_fault_note
        "add_fault_note": add_fault_note,

        # diagnose_fault
        "diagnose_fault": diagnose_fault,

        # create_work_order_from_fault (SIGNED - two-phase)
        "create_work_order_from_fault_prepare": create_work_order_from_fault_prepare,
        "create_work_order_from_fault_commit": create_work_order_from_fault_commit,
        "create_work_order_from_fault": create_work_order_from_fault,
    }


def get_secure_fault_handlers(db_client) -> Dict[str, Any]:
    """
    Get secured fault mutation handlers.

    This is the recommended entry point for production use.
    All handlers have @secure_action decorator applied.

    Args:
        db_client: Supabase client for TENANT DB

    Returns:
        Dict of action_name -> secured handler function
    """
    return create_secure_fault_handlers(db_client)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'get_secure_fault_handlers',
    'create_secure_fault_handlers',
    # Re-export utilities from original module
    'map_severity',
    'infer_severity_from_text',
    'VALID_SEVERITIES',
    'STATUS_TRANSITIONS',
]
