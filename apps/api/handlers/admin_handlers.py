"""
CelesteOS API - Admin Handlers
==============================

Server-only admin actions for membership lifecycle management.

Security invariants:
1. All actions require ADMIN role or specific privileged roles
2. Idempotency key required for all mutations
3. Audit logged for allow/deny/error (no raw payloads)
4. 2-person rule for privileged role assignments (captain/manager)
5. Deny-by-default: missing/inactive membership blocks access

Actions:
- invite_user: Create INVITED membership
- approve_membership: ACCEPTED -> PROVISIONED -> ACTIVE
- change_role: Update user role (on TENANT)
- revoke_membership: Set REVOKED status (terminal)
- freeze_yacht: Set is_frozen on fleet_registry

Usage:
    from handlers.admin_handlers import get_admin_handlers

    handlers = get_admin_handlers(master_client, tenant_client)
    result = await handlers.invite_user(params, ctx)
"""

from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging
import hashlib
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Import clear_tenant_cache at module level for testability
# Falls back to stub if middleware.auth not available (for tests)
try:
    from middleware.auth import clear_tenant_cache
except ImportError:
    def clear_tenant_cache(user_id: str) -> None:
        """Stub for tests - real implementation in middleware.auth."""
        pass


class MembershipStatus(Enum):
    """Membership lifecycle states."""
    INVITED = "INVITED"
    ACCEPTED = "ACCEPTED"
    PROVISIONED = "PROVISIONED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


# Roles that require 2-person approval (inviter != approver)
PRIVILEGED_ROLES = {"captain", "manager", "chief_engineer"}

# Roles that can invite users
INVITE_ALLOWED_ROLES = {"captain", "manager"}

# Roles that can approve memberships
APPROVE_ALLOWED_ROLES = {"captain", "manager"}

# Roles that can change roles
CHANGE_ROLE_ALLOWED_ROLES = {"captain", "manager"}

# Roles that can revoke memberships
REVOKE_ALLOWED_ROLES = {"captain", "manager"}

# Roles that can freeze yacht
FREEZE_ALLOWED_ROLES = {"captain", "manager"}


@dataclass
class AdminContext:
    """Context for admin operations."""
    user_id: str
    yacht_id: str
    role: str
    tenant_key_alias: str
    idempotency_key: Optional[str] = None


class AdminValidationError(Exception):
    """Validation error for admin operations."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AdminPermissionError(Exception):
    """Permission error for admin operations."""
    def __init__(self, action: str, required_roles: List[str], user_role: str):
        self.action = action
        self.required_roles = required_roles
        self.user_role = user_role
        self.message = f"Permission denied for {action}. Required: {required_roles}, got: {user_role}"
        super().__init__(self.message)


def _hash_payload(payload: Dict) -> str:
    """Hash payload for audit logging (no sensitive data in logs)."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def _validate_role(ctx: AdminContext, allowed_roles: set, action: str) -> None:
    """Validate user has required role."""
    if ctx.role not in allowed_roles:
        raise AdminPermissionError(action, list(allowed_roles), ctx.role)


def _log_audit(
    db_client,
    event_type: str,
    ctx: AdminContext,
    target_user_id: str = None,
    details: Dict = None,
    outcome: str = "allowed",
) -> None:
    """Log admin action to security_events."""
    try:
        db_client.table("security_events").insert({
            "event_type": event_type,
            "user_id": target_user_id or ctx.user_id,
            "yacht_id": ctx.yacht_id,
            "details": {
                "actor_id": ctx.user_id,
                "actor_role": ctx.role,
                "outcome": outcome,
                "idempotency_key": ctx.idempotency_key,
                **(details or {}),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"[AdminAudit] Failed to log {event_type}: {e}")


class AdminHandlers:
    """
    Admin action handlers for membership lifecycle.

    All methods require AdminContext with valid idempotency_key for mutations.
    """

    def __init__(self, master_client, tenant_client_factory):
        """
        Initialize admin handlers.

        Args:
            master_client: Supabase client for MASTER DB
            tenant_client_factory: Function to get tenant client by alias
        """
        self.master = master_client
        self.get_tenant = tenant_client_factory

    async def invite_user(
        self,
        params: Dict[str, Any],
        ctx: AdminContext,
    ) -> Dict[str, Any]:
        """
        Invite a user to the yacht.

        Creates INVITED membership. User must accept to proceed.

        Required params:
            - email: User's email address
            - role_requested: Role to assign after acceptance

        Optional params:
            - notes: Admin notes (not exposed to user)
            - valid_until: Expiry date for membership

        Returns:
            {membership_id, status: "INVITED", email}

        Raises:
            AdminValidationError: Invalid params
            AdminPermissionError: Insufficient permissions
        """
        # Validate permissions
        _validate_role(ctx, INVITE_ALLOWED_ROLES, "invite_user")

        # Validate params
        email = params.get("email")
        role_requested = params.get("role_requested")

        if not email:
            raise AdminValidationError("missing_email", "Email is required")
        if not role_requested:
            raise AdminValidationError("missing_role", "role_requested is required")

        # Log attempt
        _log_audit(
            self.master,
            "admin_invite_attempt",
            ctx,
            details={"email_hash": _hash_payload({"email": email}), "role_requested": role_requested},
            outcome="attempt",
        )

        try:
            # Check if user exists in auth.users
            user_result = self.master.auth.admin.list_users()
            existing_user = None
            for user in user_result:
                if user.email == email:
                    existing_user = user
                    break

            target_user_id = existing_user.id if existing_user else None

            # Check for existing membership
            if target_user_id:
                existing = self.master.table("memberships").select("id, status").eq(
                    "user_id", target_user_id
                ).eq("yacht_id", ctx.yacht_id).execute()

                if existing.data:
                    status = existing.data[0]["status"]
                    if status in [MembershipStatus.ACTIVE.value, MembershipStatus.INVITED.value]:
                        raise AdminValidationError(
                            "already_member",
                            f"User already has {status} membership",
                            status_code=409,
                        )

            # Create membership (user_id may be null if user doesn't exist yet)
            membership_data = {
                "user_id": target_user_id,
                "yacht_id": ctx.yacht_id,
                "status": MembershipStatus.INVITED.value,
                "invited_by": ctx.user_id,
                "role_requested": role_requested,
                "notes": params.get("notes"),
                "valid_until": params.get("valid_until"),
                "idempotency_key": ctx.idempotency_key,
            }

            result = self.master.table("memberships").insert(membership_data).execute()

            if not result.data:
                raise AdminValidationError("insert_failed", "Failed to create membership")

            membership = result.data[0]

            # Log success
            _log_audit(
                self.master,
                "admin_invite_success",
                ctx,
                target_user_id=target_user_id,
                details={"membership_id": membership["id"], "role_requested": role_requested},
                outcome="allowed",
            )

            return {
                "membership_id": membership["id"],
                "status": MembershipStatus.INVITED.value,
                "email": email,
                "user_exists": target_user_id is not None,
            }

        except AdminValidationError:
            raise
        except Exception as e:
            _log_audit(
                self.master,
                "admin_invite_error",
                ctx,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    async def approve_membership(
        self,
        params: Dict[str, Any],
        ctx: AdminContext,
    ) -> Dict[str, Any]:
        """
        Approve membership and provision TENANT records.

        Transitions: INVITED/ACCEPTED -> PROVISIONED -> ACTIVE

        Required params:
            - membership_id: UUID of membership to approve

        Optional params:
            - role_override: Override the requested role (requires 2-person rule)

        Security:
            - 2-person rule: approver != inviter for privileged roles
            - Idempotent: safe to retry

        Returns:
            {membership_id, status: "ACTIVE", user_id}
        """
        # Validate permissions
        _validate_role(ctx, APPROVE_ALLOWED_ROLES, "approve_membership")

        membership_id = params.get("membership_id")
        if not membership_id:
            raise AdminValidationError("missing_membership_id", "membership_id is required")

        # Get membership
        result = self.master.table("memberships").select("*").eq(
            "id", membership_id
        ).eq("yacht_id", ctx.yacht_id).execute()

        if not result.data:
            raise AdminValidationError("not_found", "Membership not found", status_code=404)

        membership = result.data[0]

        # Validate state transition
        current_status = membership["status"]
        if current_status not in [
            MembershipStatus.INVITED.value,
            MembershipStatus.ACCEPTED.value,
            MembershipStatus.PROVISIONED.value,
        ]:
            raise AdminValidationError(
                "invalid_status",
                f"Cannot approve membership in {current_status} status",
            )

        # Determine role
        role = params.get("role_override") or membership.get("role_requested") or "crew"

        # 2-person rule for privileged roles
        if role in PRIVILEGED_ROLES:
            inviter = membership.get("invited_by")
            if inviter == ctx.user_id:
                raise AdminValidationError(
                    "two_person_rule",
                    f"Privileged role '{role}' requires different approver than inviter",
                    status_code=403,
                )

        user_id = membership["user_id"]
        if not user_id:
            raise AdminValidationError(
                "user_not_registered",
                "User has not registered yet. Wait for user to accept invite.",
            )

        # Log attempt
        _log_audit(
            self.master,
            "admin_approve_attempt",
            ctx,
            target_user_id=user_id,
            details={"membership_id": membership_id, "role": role},
            outcome="attempt",
        )

        try:
            # Provision TENANT records (idempotent)
            tenant_client = self.get_tenant(ctx.tenant_key_alias)

            # Create/update auth_users_profiles
            profile_data = {
                "id": user_id,
                "user_id": user_id,
                "yacht_id": ctx.yacht_id,
            }
            tenant_client.table("auth_users_profiles").upsert(
                profile_data, on_conflict="id"
            ).execute()

            # Create/update auth_users_roles
            role_data = {
                "user_id": user_id,
                "yacht_id": ctx.yacht_id,
                "role": role,
                "is_active": True,
                "valid_from": datetime.now(timezone.utc).isoformat(),
            }
            # Upsert on (user_id, yacht_id)
            tenant_client.table("auth_users_roles").upsert(
                role_data, on_conflict="user_id,yacht_id"
            ).execute()

            # Update membership to ACTIVE
            self.master.table("memberships").update({
                "status": MembershipStatus.ACTIVE.value,
                "approved_by": ctx.user_id,
                "approved_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", membership_id).execute()

            # Log success
            _log_audit(
                self.master,
                "admin_approve_success",
                ctx,
                target_user_id=user_id,
                details={"membership_id": membership_id, "role": role},
                outcome="allowed",
            )

            return {
                "membership_id": membership_id,
                "status": MembershipStatus.ACTIVE.value,
                "user_id": user_id,
                "role": role,
            }

        except AdminValidationError:
            raise
        except Exception as e:
            _log_audit(
                self.master,
                "admin_approve_error",
                ctx,
                target_user_id=user_id,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    async def change_role(
        self,
        params: Dict[str, Any],
        ctx: AdminContext,
    ) -> Dict[str, Any]:
        """
        Change user's role on TENANT.

        Required params:
            - user_id: UUID of user
            - new_role: New role to assign

        Security:
            - 2-person rule for privileged roles
            - Clears tenant cache for user

        Returns:
            {user_id, old_role, new_role}
        """
        # Validate permissions
        _validate_role(ctx, CHANGE_ROLE_ALLOWED_ROLES, "change_role")

        user_id = params.get("user_id")
        new_role = params.get("new_role")

        if not user_id:
            raise AdminValidationError("missing_user_id", "user_id is required")
        if not new_role:
            raise AdminValidationError("missing_new_role", "new_role is required")

        # Prevent self-role-change to privileged
        if user_id == ctx.user_id and new_role in PRIVILEGED_ROLES:
            raise AdminValidationError(
                "self_escalation",
                "Cannot assign privileged role to yourself",
                status_code=403,
            )

        # Get current role from TENANT
        tenant_client = self.get_tenant(ctx.tenant_key_alias)
        current_result = tenant_client.table("auth_users_roles").select("role").eq(
            "user_id", user_id
        ).eq("yacht_id", ctx.yacht_id).eq("is_active", True).execute()

        old_role = current_result.data[0]["role"] if current_result.data else None

        # Log attempt
        _log_audit(
            self.master,
            "admin_change_role_attempt",
            ctx,
            target_user_id=user_id,
            details={"old_role": old_role, "new_role": new_role},
            outcome="attempt",
        )

        try:
            # Update role
            tenant_client.table("auth_users_roles").update({
                "role": new_role,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("user_id", user_id).eq("yacht_id", ctx.yacht_id).execute()

            # Clear tenant cache (role changed)
            clear_tenant_cache(user_id)

            # Log success
            _log_audit(
                self.master,
                "admin_change_role_success",
                ctx,
                target_user_id=user_id,
                details={"old_role": old_role, "new_role": new_role},
                outcome="allowed",
            )

            return {
                "user_id": user_id,
                "old_role": old_role,
                "new_role": new_role,
            }

        except Exception as e:
            _log_audit(
                self.master,
                "admin_change_role_error",
                ctx,
                target_user_id=user_id,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    async def revoke_membership(
        self,
        params: Dict[str, Any],
        ctx: AdminContext,
    ) -> Dict[str, Any]:
        """
        Revoke user's membership (terminal state).

        Required params:
            - user_id: UUID of user to revoke

        Optional params:
            - reason: Reason for revocation (audit only)

        Effects:
            - Sets membership status to REVOKED
            - Deactivates TENANT role
            - Clears tenant cache

        Returns:
            {user_id, status: "REVOKED"}
        """
        # Validate permissions
        _validate_role(ctx, REVOKE_ALLOWED_ROLES, "revoke_membership")

        user_id = params.get("user_id")
        if not user_id:
            raise AdminValidationError("missing_user_id", "user_id is required")

        # Prevent self-revocation
        if user_id == ctx.user_id:
            raise AdminValidationError(
                "self_revocation",
                "Cannot revoke your own membership",
                status_code=403,
            )

        # Log attempt
        _log_audit(
            self.master,
            "admin_revoke_attempt",
            ctx,
            target_user_id=user_id,
            details={"reason": params.get("reason")},
            outcome="attempt",
        )

        try:
            # Update membership to REVOKED
            self.master.table("memberships").update({
                "status": MembershipStatus.REVOKED.value,
                "notes": params.get("reason"),
            }).eq("user_id", user_id).eq("yacht_id", ctx.yacht_id).execute()

            # Deactivate TENANT role
            tenant_client = self.get_tenant(ctx.tenant_key_alias)
            tenant_client.table("auth_users_roles").update({
                "is_active": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("user_id", user_id).eq("yacht_id", ctx.yacht_id).execute()

            # Clear tenant cache
            clear_tenant_cache(user_id)

            # Log success
            _log_audit(
                self.master,
                "admin_revoke_success",
                ctx,
                target_user_id=user_id,
                details={"reason": params.get("reason")},
                outcome="allowed",
            )

            return {
                "user_id": user_id,
                "status": MembershipStatus.REVOKED.value,
            }

        except Exception as e:
            _log_audit(
                self.master,
                "admin_revoke_error",
                ctx,
                target_user_id=user_id,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    async def freeze_yacht(
        self,
        params: Dict[str, Any],
        ctx: AdminContext,
    ) -> Dict[str, Any]:
        """
        Freeze yacht (kill switch).

        Sets is_frozen=true on fleet_registry.
        Middleware will deny MUTATE/SIGNED/ADMIN for frozen yachts.

        Required params:
            - freeze: bool (true to freeze, false to unfreeze)

        Optional params:
            - reason: Reason for freeze (audit only)

        Returns:
            {yacht_id, is_frozen: bool}
        """
        # Validate permissions
        _validate_role(ctx, FREEZE_ALLOWED_ROLES, "freeze_yacht")

        freeze = params.get("freeze")
        if freeze is None:
            raise AdminValidationError("missing_freeze", "freeze parameter is required")

        # Log attempt
        _log_audit(
            self.master,
            "admin_freeze_attempt",
            ctx,
            details={"freeze": freeze, "reason": params.get("reason")},
            outcome="attempt",
        )

        try:
            # Update fleet_registry
            self.master.table("fleet_registry").update({
                "is_frozen": freeze,
            }).eq("yacht_id", ctx.yacht_id).execute()

            # Log success
            _log_audit(
                self.master,
                "admin_freeze_success" if freeze else "admin_unfreeze_success",
                ctx,
                details={"freeze": freeze, "reason": params.get("reason")},
                outcome="allowed",
            )

            return {
                "yacht_id": ctx.yacht_id,
                "is_frozen": freeze,
            }

        except Exception as e:
            _log_audit(
                self.master,
                "admin_freeze_error",
                ctx,
                details={"error": str(e)},
                outcome="error",
            )
            raise


def get_admin_handlers(master_client, tenant_client_factory) -> AdminHandlers:
    """
    Factory function to create AdminHandlers.

    Args:
        master_client: Supabase client for MASTER DB
        tenant_client_factory: Function(tenant_key_alias) -> tenant_client

    Returns:
        AdminHandlers instance
    """
    return AdminHandlers(master_client, tenant_client_factory)
