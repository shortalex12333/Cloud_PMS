"""
CelesteOS API - Secure Admin Handlers
======================================

@secure_action-wrapped admin handlers for membership lifecycle management.

Security invariants enforced:
1. All handlers have @secure_action marker for CI contract tests
2. ADMIN action group requires idempotency key
3. Role validation via decorator
4. yacht_id injected from context (never trusted from payload)
5. Audit logging on all outcomes

Actions wrapped:
- admin_invite_user: Create INVITED membership
- admin_approve_membership: Approve and provision user
- admin_change_role: Update user role on TENANT
- admin_revoke_membership: Set REVOKED status (terminal)
- admin_freeze_yacht: Set is_frozen flag
- admin_list_memberships: List yacht memberships (READ)
- admin_get_membership: Get single membership (READ)

Usage:
    from handlers.secure_admin_handlers import get_secure_admin_handlers

    handlers = get_secure_admin_handlers(tenant_client, master_client)
    result = await handlers["admin_invite_user"](db, auth, idempotency_key=key, **params)
"""

from typing import Any, Dict, Callable, Optional
import logging
import os

from middleware.action_security import (
    secure_action,
    ActionContext,
    ActionSecurityError,
    build_audit_entry,
)
from handlers.admin_handlers import (
    AdminHandlers,
    AdminContext,
    AdminValidationError,
    AdminPermissionError,
    MembershipStatus,
    INVITE_ALLOWED_ROLES,
    APPROVE_ALLOWED_ROLES,
    CHANGE_ROLE_ALLOWED_ROLES,
    REVOKE_ALLOWED_ROLES,
    FREEZE_ALLOWED_ROLES,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ROLE DEFINITIONS
# ============================================================================

# Admin actions require privileged roles
ADMIN_ROLES = ["captain", "manager", "chief_engineer"]

# Read-only admin views may allow broader access
ADMIN_READ_ROLES = ["captain", "manager", "chief_engineer", "hod"]


# ============================================================================
# SECURE ADMIN HANDLERS
# ============================================================================


def get_secure_admin_handlers(
    tenant_client,
    master_client,
) -> Dict[str, Callable]:
    """
    Get secure admin handler functions.

    Args:
        tenant_client: Supabase client for TENANT DB
        master_client: Supabase client for MASTER DB (for memberships)

    Returns:
        Dict mapping action_id to secured handler function
    """
    # Create tenant client factory for AdminHandlers
    def get_tenant(alias: str):
        return tenant_client

    # Initialize AdminHandlers
    admin_handlers = AdminHandlers(master_client, get_tenant)

    # ========================================================================
    # INVITE USER
    # ========================================================================

    @secure_action(
        action_id="admin_invite_user",
        action_group="ADMIN",
        required_roles=list(INVITE_ALLOWED_ROLES),
    )
    async def secure_invite_user(
        ctx: ActionContext,
        email: str = None,
        role_requested: str = None,
        notes: str = None,
        valid_until: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Invite a user to the yacht.

        Creates INVITED membership. Requires captain/manager role.

        Args:
            ctx: ActionContext with user/yacht/role
            email: User's email address
            role_requested: Role to assign after acceptance
            notes: Admin notes (optional)
            valid_until: Expiry date (optional)

        Returns:
            {membership_id, status, email, user_exists}
        """
        # Create AdminContext from ActionContext
        admin_ctx = AdminContext(
            user_id=ctx.user_id,
            yacht_id=ctx.yacht_id,
            role=ctx.role,
            tenant_key_alias=ctx.tenant_key_alias,
            idempotency_key=ctx.idempotency_key,
        )

        params = {
            "email": email,
            "role_requested": role_requested,
            "notes": notes,
            "valid_until": valid_until,
        }

        try:
            result = await admin_handlers.invite_user(params, admin_ctx)
            return result
        except AdminValidationError as e:
            # Map to ActionSecurityError for consistent API
            raise ActionSecurityError(e.code, e.message, e.status_code)
        except AdminPermissionError as e:
            raise ActionSecurityError("PERMISSION_DENIED", e.message, 403)

    # ========================================================================
    # APPROVE MEMBERSHIP
    # ========================================================================

    @secure_action(
        action_id="admin_approve_membership",
        action_group="ADMIN",
        required_roles=list(APPROVE_ALLOWED_ROLES),
        validate_entities=["membership_id"],
        entity_type_mapping={"membership_id": "memberships"},
    )
    async def secure_approve_membership(
        ctx: ActionContext,
        membership_id: str = None,
        role_override: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Approve membership and provision TENANT records.

        Transitions: INVITED/ACCEPTED -> PROVISIONED -> ACTIVE
        Enforces 2-person rule for privileged roles.

        Args:
            ctx: ActionContext
            membership_id: UUID of membership to approve
            role_override: Override requested role (optional)

        Returns:
            {membership_id, status, user_id, role}
        """
        admin_ctx = AdminContext(
            user_id=ctx.user_id,
            yacht_id=ctx.yacht_id,
            role=ctx.role,
            tenant_key_alias=ctx.tenant_key_alias,
            idempotency_key=ctx.idempotency_key,
        )

        params = {
            "membership_id": membership_id,
            "role_override": role_override,
        }

        try:
            result = await admin_handlers.approve_membership(params, admin_ctx)
            return result
        except AdminValidationError as e:
            raise ActionSecurityError(e.code, e.message, e.status_code)
        except AdminPermissionError as e:
            raise ActionSecurityError("PERMISSION_DENIED", e.message, 403)

    # ========================================================================
    # CHANGE ROLE
    # ========================================================================

    @secure_action(
        action_id="admin_change_role",
        action_group="ADMIN",
        required_roles=list(CHANGE_ROLE_ALLOWED_ROLES),
    )
    async def secure_change_role(
        ctx: ActionContext,
        target_user_id: str = None,
        new_role: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Change user's role on TENANT.

        Enforces 2-person rule for privileged roles.
        Clears tenant cache for affected user.

        Args:
            ctx: ActionContext
            target_user_id: UUID of user to change role for
            new_role: New role to assign

        Returns:
            {user_id, old_role, new_role}
        """
        admin_ctx = AdminContext(
            user_id=ctx.user_id,
            yacht_id=ctx.yacht_id,
            role=ctx.role,
            tenant_key_alias=ctx.tenant_key_alias,
            idempotency_key=ctx.idempotency_key,
        )

        # Map target_user_id to user_id for underlying handler
        params = {
            "user_id": target_user_id,
            "new_role": new_role,
        }

        try:
            result = await admin_handlers.change_role(params, admin_ctx)
            return result
        except AdminValidationError as e:
            raise ActionSecurityError(e.code, e.message, e.status_code)
        except AdminPermissionError as e:
            raise ActionSecurityError("PERMISSION_DENIED", e.message, 403)

    # ========================================================================
    # REVOKE MEMBERSHIP
    # ========================================================================

    @secure_action(
        action_id="admin_revoke_membership",
        action_group="ADMIN",
        required_roles=list(REVOKE_ALLOWED_ROLES),
    )
    async def secure_revoke_membership(
        ctx: ActionContext,
        target_user_id: str = None,
        reason: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Revoke user's membership (terminal state).

        Effects:
        - Sets membership status to REVOKED
        - Deactivates TENANT role
        - Clears tenant cache

        Args:
            ctx: ActionContext
            target_user_id: UUID of user to revoke
            reason: Reason for revocation (audit only)

        Returns:
            {user_id, status: "REVOKED"}
        """
        admin_ctx = AdminContext(
            user_id=ctx.user_id,
            yacht_id=ctx.yacht_id,
            role=ctx.role,
            tenant_key_alias=ctx.tenant_key_alias,
            idempotency_key=ctx.idempotency_key,
        )

        params = {
            "user_id": target_user_id,
            "reason": reason,
        }

        try:
            result = await admin_handlers.revoke_membership(params, admin_ctx)
            return result
        except AdminValidationError as e:
            raise ActionSecurityError(e.code, e.message, e.status_code)
        except AdminPermissionError as e:
            raise ActionSecurityError("PERMISSION_DENIED", e.message, 403)

    # ========================================================================
    # FREEZE YACHT
    # ========================================================================

    @secure_action(
        action_id="admin_freeze_yacht",
        action_group="ADMIN",
        required_roles=list(FREEZE_ALLOWED_ROLES),
    )
    async def secure_freeze_yacht(
        ctx: ActionContext,
        freeze: bool = None,
        reason: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Freeze or unfreeze yacht (kill switch).

        Sets is_frozen on fleet_registry.
        Middleware will deny MUTATE/SIGNED/ADMIN for frozen yachts.

        Args:
            ctx: ActionContext
            freeze: True to freeze, False to unfreeze
            reason: Reason for freeze (audit only)

        Returns:
            {yacht_id, is_frozen}
        """
        admin_ctx = AdminContext(
            user_id=ctx.user_id,
            yacht_id=ctx.yacht_id,
            role=ctx.role,
            tenant_key_alias=ctx.tenant_key_alias,
            idempotency_key=ctx.idempotency_key,
        )

        params = {
            "freeze": freeze,
            "reason": reason,
        }

        try:
            result = await admin_handlers.freeze_yacht(params, admin_ctx)
            return result
        except AdminValidationError as e:
            raise ActionSecurityError(e.code, e.message, e.status_code)
        except AdminPermissionError as e:
            raise ActionSecurityError("PERMISSION_DENIED", e.message, 403)

    # ========================================================================
    # LIST MEMBERSHIPS (READ)
    # ========================================================================

    @secure_action(
        action_id="admin_list_memberships",
        action_group="READ",
        required_roles=ADMIN_READ_ROLES,
    )
    async def secure_list_memberships(
        ctx: ActionContext,
        status_filter: str = None,
        limit: int = 50,
        offset: int = 0,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        List memberships for the yacht.

        Read-only action, no idempotency required.

        Args:
            ctx: ActionContext
            status_filter: Filter by status (optional)
            limit: Max results (default 50)
            offset: Pagination offset

        Returns:
            {memberships: [...], total: int}
        """
        # Query memberships from MASTER
        query = admin_handlers.master.table("memberships").select(
            "id, user_id, status, role_requested, invited_by, approved_by, created_at"
        ).eq("yacht_id", ctx.yacht_id)

        if status_filter:
            query = query.eq("status", status_filter)

        result = query.range(offset, offset + limit - 1).execute()

        # Get total count
        count_result = admin_handlers.master.table("memberships").select(
            "id", count="exact"
        ).eq("yacht_id", ctx.yacht_id).execute()

        return {
            "memberships": result.data if result.data else [],
            "total": count_result.count if hasattr(count_result, 'count') else len(result.data or []),
        }

    # ========================================================================
    # GET MEMBERSHIP (READ)
    # ========================================================================

    @secure_action(
        action_id="admin_get_membership",
        action_group="READ",
        required_roles=ADMIN_READ_ROLES,
        validate_entities=["membership_id"],
        entity_type_mapping={"membership_id": "memberships"},
    )
    async def secure_get_membership(
        ctx: ActionContext,
        membership_id: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get single membership details.

        Read-only action with ownership validation.

        Args:
            ctx: ActionContext
            membership_id: UUID of membership

        Returns:
            Membership object
        """
        result = admin_handlers.master.table("memberships").select("*").eq(
            "id", membership_id
        ).eq("yacht_id", ctx.yacht_id).execute()

        if not result.data:
            raise ActionSecurityError("NOT_FOUND", "Membership not found", 404)

        return result.data[0]

    # ========================================================================
    # RETURN HANDLERS DICT
    # ========================================================================

    return {
        "admin_invite_user": secure_invite_user,
        "admin_approve_membership": secure_approve_membership,
        "admin_change_role": secure_change_role,
        "admin_revoke_membership": secure_revoke_membership,
        "admin_freeze_yacht": secure_freeze_yacht,
        "admin_list_memberships": secure_list_memberships,
        "admin_get_membership": secure_get_membership,
    }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'get_secure_admin_handlers',
    'ADMIN_ROLES',
    'ADMIN_READ_ROLES',
]
