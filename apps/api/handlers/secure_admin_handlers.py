"""
CelesteOS API - Secure Admin Handlers
======================================

@secure_action-wrapped admin handlers for membership lifecycle management.

Security invariants enforced:
1. All handlers have @secure_action marker for CI contract tests
2. ADMIN action group requires idempotency key
3. 2-person rule: approver MUST differ from inviter for privileged roles
4. yacht_id injected from context (never trusted from payload)
5. Audit logging on all outcomes with inviter/approver IDs

Actions:
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

from typing import Any, Dict, Callable, List
import logging
from datetime import datetime, timezone

from middleware.action_security import (
    secure_action,
    ActionContext,
    ActionSecurityError,
    build_audit_entry,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ROLE DEFINITIONS
# ============================================================================

# Roles that can perform admin actions
ADMIN_ROLES = ["captain", "manager"]

# Roles allowed for read-only admin views
ADMIN_READ_ROLES = ["captain", "manager", "chief_engineer", "hod"]

# Privileged roles requiring 2-person approval (inviter != approver)
PRIVILEGED_ROLES = {"captain", "manager", "chief_engineer"}


# ============================================================================
# ERROR CLASSES
# ============================================================================


class TwoPersonRuleViolation(ActionSecurityError):
    """Raised when 2-person rule is violated for privileged role assignment."""
    def __init__(self, inviter_id: str, approver_id: str, role: str):
        super().__init__(
            "TWO_PERSON_RULE",
            f"Privileged role '{role}' requires different approver than inviter",
            status_code=403,
        )
        self.inviter_id = inviter_id
        self.approver_id = approver_id
        self.role = role


class SelfEscalationError(ActionSecurityError):
    """Raised when user attempts to escalate their own role."""
    def __init__(self, user_id: str, target_role: str):
        super().__init__(
            "SELF_ESCALATION",
            "Cannot assign privileged role to yourself",
            status_code=403,
        )
        self.user_id = user_id
        self.target_role = target_role


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

    def _log_admin_audit(
        client,
        event_type: str,
        ctx: ActionContext,
        target_user_id: str = None,
        details: Dict = None,
        outcome: str = "allowed",
    ):
        """Log admin action to security_events table."""
        try:
            client.table("security_events").insert({
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

    # ========================================================================
    # INVITE USER
    # ========================================================================

    @secure_action(
        action_id="admin_invite_user",
        action_group="ADMIN",
        required_roles=ADMIN_ROLES,
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
        """
        if not email:
            raise ActionSecurityError("VALIDATION_ERROR", "Email is required", 400)
        if not role_requested:
            raise ActionSecurityError("VALIDATION_ERROR", "role_requested is required", 400)

        # Log attempt
        _log_admin_audit(
            master_client,
            "admin_invite_attempt",
            ctx,
            details={"role_requested": role_requested},
            outcome="attempt",
        )

        try:
            # Check for existing user
            user_result = master_client.auth.admin.list_users()
            existing_user = next(
                (u for u in user_result if u.email == email),
                None
            )
            target_user_id = existing_user.id if existing_user else None

            # Check for existing membership
            if target_user_id:
                existing = master_client.table("memberships").select("id, status").eq(
                    "user_id", target_user_id
                ).eq("yacht_id", ctx.yacht_id).execute()

                if existing.data:
                    status = existing.data[0]["status"]
                    if status in ["ACTIVE", "INVITED"]:
                        raise ActionSecurityError(
                            "ALREADY_MEMBER",
                            f"User already has {status} membership",
                            409,
                        )

            # Create membership
            membership_data = {
                "user_id": target_user_id,
                "yacht_id": ctx.yacht_id,
                "status": "INVITED",
                "invited_by": ctx.user_id,  # Track inviter for 2-person rule
                "role_requested": role_requested,
                "notes": notes,
                "valid_until": valid_until,
                "idempotency_key": ctx.idempotency_key,
            }

            result = master_client.table("memberships").insert(membership_data).execute()

            if not result.data:
                raise ActionSecurityError("INSERT_FAILED", "Failed to create membership", 500)

            membership = result.data[0]

            # Log success with inviter
            _log_admin_audit(
                master_client,
                "admin_invite_success",
                ctx,
                target_user_id=target_user_id,
                details={
                    "membership_id": membership["id"],
                    "role_requested": role_requested,
                    "inviter_id": ctx.user_id,
                },
                outcome="allowed",
            )

            return {
                "membership_id": membership["id"],
                "status": "INVITED",
                "email": email,
                "user_exists": target_user_id is not None,
            }

        except ActionSecurityError:
            raise
        except Exception as e:
            _log_admin_audit(
                master_client,
                "admin_invite_error",
                ctx,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    # ========================================================================
    # APPROVE MEMBERSHIP (with 2-person rule)
    # ========================================================================

    @secure_action(
        action_id="admin_approve_membership",
        action_group="ADMIN",
        required_roles=ADMIN_ROLES,
    )
    async def secure_approve_membership(
        ctx: ActionContext,
        membership_id: str = None,
        role_override: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Approve membership and provision TENANT records.

        ENFORCES 2-PERSON RULE: approver MUST differ from inviter
        for privileged role assignments.
        """
        if not membership_id:
            raise ActionSecurityError("VALIDATION_ERROR", "membership_id is required", 400)

        # Get membership with inviter info
        result = master_client.table("memberships").select("*").eq(
            "id", membership_id
        ).eq("yacht_id", ctx.yacht_id).execute()

        if not result.data:
            raise ActionSecurityError("NOT_FOUND", "Membership not found", 404)

        membership = result.data[0]

        # Validate state transition
        current_status = membership["status"]
        if current_status not in ["INVITED", "ACCEPTED", "PROVISIONED"]:
            raise ActionSecurityError(
                "INVALID_STATUS",
                f"Cannot approve membership in {current_status} status",
                400,
            )

        # Determine final role
        role = role_override or membership.get("role_requested") or "crew"

        # =====================================================================
        # ENFORCE 2-PERSON RULE FOR PRIVILEGED ROLES
        # =====================================================================
        if role in PRIVILEGED_ROLES:
            inviter_id = membership.get("invited_by")
            if inviter_id == ctx.user_id:
                # Log denial with both IDs
                _log_admin_audit(
                    master_client,
                    "admin_approve_denied_2person",
                    ctx,
                    target_user_id=membership["user_id"],
                    details={
                        "membership_id": membership_id,
                        "role": role,
                        "inviter_id": inviter_id,
                        "approver_id": ctx.user_id,
                        "reason": "2-person rule violation",
                    },
                    outcome="denied",
                )
                raise TwoPersonRuleViolation(inviter_id, ctx.user_id, role)

        user_id = membership["user_id"]
        if not user_id:
            raise ActionSecurityError(
                "USER_NOT_REGISTERED",
                "User has not registered yet. Wait for user to accept invite.",
                400,
            )

        # Log attempt with approver
        _log_admin_audit(
            master_client,
            "admin_approve_attempt",
            ctx,
            target_user_id=user_id,
            details={
                "membership_id": membership_id,
                "role": role,
                "inviter_id": membership.get("invited_by"),
                "approver_id": ctx.user_id,
            },
            outcome="attempt",
        )

        try:
            # Provision TENANT records
            # Create/update auth_users_profiles
            tenant_client.table("auth_users_profiles").upsert(
                {"id": user_id, "user_id": user_id, "yacht_id": ctx.yacht_id},
                on_conflict="id"
            ).execute()

            # Create/update auth_users_roles
            tenant_client.table("auth_users_roles").upsert(
                {
                    "user_id": user_id,
                    "yacht_id": ctx.yacht_id,
                    "role": role,
                    "is_active": True,
                    "valid_from": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="user_id,yacht_id"
            ).execute()

            # Update membership to ACTIVE
            master_client.table("memberships").update({
                "status": "ACTIVE",
                "approved_by": ctx.user_id,  # Track approver for audit
                "approved_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", membership_id).execute()

            # Log success with both inviter and approver
            _log_admin_audit(
                master_client,
                "admin_approve_success",
                ctx,
                target_user_id=user_id,
                details={
                    "membership_id": membership_id,
                    "role": role,
                    "inviter_id": membership.get("invited_by"),
                    "approver_id": ctx.user_id,
                },
                outcome="allowed",
            )

            return {
                "membership_id": membership_id,
                "status": "ACTIVE",
                "user_id": user_id,
                "role": role,
            }

        except ActionSecurityError:
            raise
        except Exception as e:
            _log_admin_audit(
                master_client,
                "admin_approve_error",
                ctx,
                target_user_id=user_id,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    # ========================================================================
    # CHANGE ROLE
    # ========================================================================

    @secure_action(
        action_id="admin_change_role",
        action_group="ADMIN",
        required_roles=ADMIN_ROLES,
    )
    async def secure_change_role(
        ctx: ActionContext,
        target_user_id: str = None,
        new_role: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Change user's role on TENANT.

        Prevents self-escalation to privileged roles.
        """
        if not target_user_id:
            raise ActionSecurityError("VALIDATION_ERROR", "target_user_id is required", 400)
        if not new_role:
            raise ActionSecurityError("VALIDATION_ERROR", "new_role is required", 400)

        # Prevent self-role-change to privileged
        if target_user_id == ctx.user_id and new_role in PRIVILEGED_ROLES:
            _log_admin_audit(
                master_client,
                "admin_change_role_denied_self",
                ctx,
                target_user_id=target_user_id,
                details={"new_role": new_role, "reason": "self-escalation"},
                outcome="denied",
            )
            raise SelfEscalationError(ctx.user_id, new_role)

        # Get current role
        current_result = tenant_client.table("auth_users_roles").select("role").eq(
            "user_id", target_user_id
        ).eq("yacht_id", ctx.yacht_id).eq("is_active", True).execute()

        old_role = current_result.data[0]["role"] if current_result.data else None

        # Log attempt
        _log_admin_audit(
            master_client,
            "admin_change_role_attempt",
            ctx,
            target_user_id=target_user_id,
            details={"old_role": old_role, "new_role": new_role},
            outcome="attempt",
        )

        try:
            # Update role
            tenant_client.table("auth_users_roles").update({
                "role": new_role,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("user_id", target_user_id).eq("yacht_id", ctx.yacht_id).execute()

            # Clear tenant cache (auth middleware)
            try:
                from middleware.auth import clear_tenant_cache
                clear_tenant_cache(target_user_id)
            except ImportError:
                pass

            # Clear response/streaming cache for user (SECURITY: role changed = cache invalid)
            try:
                from services.cache import clear_cache_for_user
                import asyncio
                asyncio.create_task(clear_cache_for_user(target_user_id, ctx.yacht_id))
            except ImportError:
                pass

            # Log success
            _log_admin_audit(
                master_client,
                "admin_change_role_success",
                ctx,
                target_user_id=target_user_id,
                details={"old_role": old_role, "new_role": new_role, "cache_cleared": True},
                outcome="allowed",
            )

            return {
                "user_id": target_user_id,
                "old_role": old_role,
                "new_role": new_role,
                "cache_cleared": True,
            }

        except Exception as e:
            _log_admin_audit(
                master_client,
                "admin_change_role_error",
                ctx,
                target_user_id=target_user_id,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    # ========================================================================
    # REVOKE MEMBERSHIP
    # ========================================================================

    @secure_action(
        action_id="admin_revoke_membership",
        action_group="ADMIN",
        required_roles=ADMIN_ROLES,
    )
    async def secure_revoke_membership(
        ctx: ActionContext,
        target_user_id: str = None,
        reason: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Revoke user's membership (terminal state)."""
        if not target_user_id:
            raise ActionSecurityError("VALIDATION_ERROR", "target_user_id is required", 400)

        # Prevent self-revocation
        if target_user_id == ctx.user_id:
            raise ActionSecurityError("SELF_REVOCATION", "Cannot revoke your own membership", 403)

        _log_admin_audit(
            master_client,
            "admin_revoke_attempt",
            ctx,
            target_user_id=target_user_id,
            details={"reason": reason},
            outcome="attempt",
        )

        try:
            # Update membership
            master_client.table("memberships").update({
                "status": "REVOKED",
                "notes": reason,
            }).eq("user_id", target_user_id).eq("yacht_id", ctx.yacht_id).execute()

            # Deactivate TENANT role
            tenant_client.table("auth_users_roles").update({
                "is_active": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("user_id", target_user_id).eq("yacht_id", ctx.yacht_id).execute()

            # Clear tenant cache (auth middleware)
            try:
                from middleware.auth import clear_tenant_cache
                clear_tenant_cache(target_user_id)
            except ImportError:
                pass

            # Clear response/streaming cache for user (SECURITY: revoked = cache invalid)
            try:
                from services.cache import clear_cache_for_user
                import asyncio
                asyncio.create_task(clear_cache_for_user(target_user_id, ctx.yacht_id))
            except ImportError:
                pass

            _log_admin_audit(
                master_client,
                "admin_revoke_success",
                ctx,
                target_user_id=target_user_id,
                details={"reason": reason, "cache_cleared": True},
                outcome="allowed",
            )

            return {"user_id": target_user_id, "status": "REVOKED", "cache_cleared": True}

        except Exception as e:
            _log_admin_audit(
                master_client,
                "admin_revoke_error",
                ctx,
                target_user_id=target_user_id,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    # ========================================================================
    # FREEZE YACHT
    # ========================================================================

    @secure_action(
        action_id="admin_freeze_yacht",
        action_group="ADMIN",
        required_roles=ADMIN_ROLES,
    )
    async def secure_freeze_yacht(
        ctx: ActionContext,
        freeze: bool = None,
        reason: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Freeze or unfreeze yacht (kill switch)."""
        if freeze is None:
            raise ActionSecurityError("VALIDATION_ERROR", "freeze parameter is required", 400)

        _log_admin_audit(
            master_client,
            "admin_freeze_attempt",
            ctx,
            details={"freeze": freeze, "reason": reason},
            outcome="attempt",
        )

        try:
            master_client.table("fleet_registry").update({
                "is_frozen": freeze,
            }).eq("yacht_id", ctx.yacht_id).execute()

            # Clear cache for all users on this yacht
            try:
                from services.cache import clear_cache_for_yacht
                import asyncio
                asyncio.create_task(clear_cache_for_yacht(ctx.yacht_id))
            except ImportError:
                pass

            _log_admin_audit(
                master_client,
                "admin_freeze_success" if freeze else "admin_unfreeze_success",
                ctx,
                details={"freeze": freeze, "reason": reason},
                outcome="allowed",
            )

            return {"yacht_id": ctx.yacht_id, "is_frozen": freeze}

        except Exception as e:
            _log_admin_audit(
                master_client,
                "admin_freeze_error",
                ctx,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    # ========================================================================
    # GLOBAL INCIDENT MODE (System-wide kill switch)
    # ========================================================================
    # NOTE: These handlers are GLOBAL and affect ALL yachts.
    # They should only be used by platform administrators during security incidents.

    @secure_action(
        action_id="admin_enable_incident_mode",
        action_group="ADMIN",
        required_roles=ADMIN_ROLES,  # In production, restrict to system admins only
    )
    async def secure_enable_incident_mode(
        ctx: ActionContext,
        reason: str = None,
        disable_streaming: bool = True,
        disable_signed_urls: bool = False,
        disable_writes: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Enable global incident mode (affects ALL yachts).

        SECURITY: This is the global kill switch. When enabled:
        - MUTATE/SIGNED/ADMIN actions blocked (if disable_writes=True)
        - Streaming disabled (if disable_streaming=True)
        - Signed URL generation disabled (if disable_signed_urls=True)

        WARNING: This affects ALL tenants across the platform.
        Only use during confirmed security incidents.
        """
        if not reason:
            raise ActionSecurityError(
                "VALIDATION_ERROR",
                "reason is required for incident mode",
                400,
            )

        _log_admin_audit(
            master_client,
            "incident_mode_enable_attempt",
            ctx,
            details={
                "reason": reason,
                "disable_streaming": disable_streaming,
                "disable_signed_urls": disable_signed_urls,
                "disable_writes": disable_writes,
            },
            outcome="attempt",
        )

        try:
            # Update system_flags table (singleton row with id=1)
            master_client.table("system_flags").upsert({
                "id": 1,
                "incident_mode": True,
                "disable_streaming": disable_streaming,
                "disable_signed_urls": disable_signed_urls,
                "disable_writes": disable_writes,
                "incident_reason": reason,
                "incident_started_at": datetime.now(timezone.utc).isoformat(),
                "incident_started_by": ctx.user_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, on_conflict="id").execute()

            # Clear system flags cache immediately
            try:
                from middleware.auth import clear_system_flags_cache
                clear_system_flags_cache()
            except ImportError:
                pass

            _log_admin_audit(
                master_client,
                "incident_mode_enabled",
                ctx,
                details={
                    "reason": reason,
                    "disable_streaming": disable_streaming,
                    "disable_signed_urls": disable_signed_urls,
                    "disable_writes": disable_writes,
                },
                outcome="allowed",
            )

            logger.critical(
                f"[INCIDENT] Global incident mode ENABLED by {ctx.user_id}: {reason}"
            )

            return {
                "incident_mode": True,
                "reason": reason,
                "disable_streaming": disable_streaming,
                "disable_signed_urls": disable_signed_urls,
                "disable_writes": disable_writes,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "started_by": ctx.user_id,
            }

        except Exception as e:
            _log_admin_audit(
                master_client,
                "incident_mode_enable_error",
                ctx,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    @secure_action(
        action_id="admin_disable_incident_mode",
        action_group="ADMIN",
        required_roles=ADMIN_ROLES,  # In production, restrict to system admins only
    )
    async def secure_disable_incident_mode(
        ctx: ActionContext,
        resolution_notes: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Disable global incident mode (restore normal operations).

        SECURITY: Only use this when the incident has been resolved.
        """
        _log_admin_audit(
            master_client,
            "incident_mode_disable_attempt",
            ctx,
            details={"resolution_notes": resolution_notes},
            outcome="attempt",
        )

        try:
            # Get current state first
            current = master_client.table("system_flags").select("*").eq("id", 1).execute()

            started_at = None
            started_by = None
            if current.data:
                started_at = current.data[0].get("incident_started_at")
                started_by = current.data[0].get("incident_started_by")

            # Update system_flags table
            master_client.table("system_flags").upsert({
                "id": 1,
                "incident_mode": False,
                "disable_streaming": False,
                "disable_signed_urls": False,
                "disable_writes": False,
                "incident_reason": None,
                "incident_started_at": None,
                "incident_started_by": None,
                "incident_ended_at": datetime.now(timezone.utc).isoformat(),
                "incident_ended_by": ctx.user_id,
                "resolution_notes": resolution_notes,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, on_conflict="id").execute()

            # Clear system flags cache immediately
            try:
                from middleware.auth import clear_system_flags_cache
                clear_system_flags_cache()
            except ImportError:
                pass

            _log_admin_audit(
                master_client,
                "incident_mode_disabled",
                ctx,
                details={
                    "resolution_notes": resolution_notes,
                    "incident_started_at": started_at,
                    "incident_started_by": started_by,
                },
                outcome="allowed",
            )

            logger.critical(
                f"[INCIDENT] Global incident mode DISABLED by {ctx.user_id}: {resolution_notes}"
            )

            return {
                "incident_mode": False,
                "disabled_by": ctx.user_id,
                "disabled_at": datetime.now(timezone.utc).isoformat(),
                "resolution_notes": resolution_notes,
            }

        except Exception as e:
            _log_admin_audit(
                master_client,
                "incident_mode_disable_error",
                ctx,
                details={"error": str(e)},
                outcome="error",
            )
            raise

    @secure_action(
        action_id="admin_get_system_flags",
        action_group="READ",
        required_roles=ADMIN_READ_ROLES,
    )
    async def secure_get_system_flags(
        ctx: ActionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        """Get current system flags including incident mode status."""
        result = master_client.table("system_flags").select("*").eq("id", 1).execute()

        if not result.data:
            return {
                "incident_mode": False,
                "disable_streaming": False,
                "disable_signed_urls": False,
                "disable_writes": False,
                "incident_reason": None,
            }

        flags = result.data[0]
        return {
            "incident_mode": flags.get("incident_mode", False),
            "disable_streaming": flags.get("disable_streaming", False),
            "disable_signed_urls": flags.get("disable_signed_urls", False),
            "disable_writes": flags.get("disable_writes", False),
            "incident_reason": flags.get("incident_reason"),
            "incident_started_at": flags.get("incident_started_at"),
            "incident_started_by": flags.get("incident_started_by"),
        }

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
        """List memberships for the yacht."""
        query = master_client.table("memberships").select(
            "id, user_id, status, role_requested, invited_by, approved_by, created_at"
        ).eq("yacht_id", ctx.yacht_id)

        if status_filter:
            query = query.eq("status", status_filter)

        result = query.range(offset, offset + limit - 1).execute()

        return {
            "memberships": result.data or [],
            "total": len(result.data or []),
        }

    # ========================================================================
    # GET MEMBERSHIP (READ)
    # ========================================================================

    @secure_action(
        action_id="admin_get_membership",
        action_group="READ",
        required_roles=ADMIN_READ_ROLES,
    )
    async def secure_get_membership(
        ctx: ActionContext,
        membership_id: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Get single membership details."""
        if not membership_id:
            raise ActionSecurityError("VALIDATION_ERROR", "membership_id is required", 400)

        result = master_client.table("memberships").select("*").eq(
            "id", membership_id
        ).eq("yacht_id", ctx.yacht_id).execute()

        if not result.data:
            raise ActionSecurityError("NOT_FOUND", "Membership not found", 404)

        return result.data[0]

    # ========================================================================
    # RETURN HANDLERS
    # ========================================================================

    return {
        # Membership management
        "admin_invite_user": secure_invite_user,
        "admin_approve_membership": secure_approve_membership,
        "admin_change_role": secure_change_role,
        "admin_revoke_membership": secure_revoke_membership,
        "admin_list_memberships": secure_list_memberships,
        "admin_get_membership": secure_get_membership,
        # Yacht freeze (per-yacht kill switch)
        "admin_freeze_yacht": secure_freeze_yacht,
        # Global incident mode (platform-wide kill switch)
        "admin_enable_incident_mode": secure_enable_incident_mode,
        "admin_disable_incident_mode": secure_disable_incident_mode,
        "admin_get_system_flags": secure_get_system_flags,
    }


__all__ = [
    'get_secure_admin_handlers',
    'ADMIN_ROLES',
    'ADMIN_READ_ROLES',
    'PRIVILEGED_ROLES',
    'TwoPersonRuleViolation',
    'SelfEscalationError',
]
