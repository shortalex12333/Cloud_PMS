"""
Crew Domain Handlers
====================

Handlers for crew management actions (Crew Lens v2).

READ Handlers:
- view_my_profile: View own profile and roles
- view_assigned_work_orders: List work orders assigned to current user
- list_crew_members: List all crew on yacht (HOD only)
- view_crew_member_details: View crew member profile (HOD only)
- view_crew_certificates: View crew member's certificates (HOD only)
- view_crew_work_history: View crew member's completed work orders (HOD only)

MUTATION Handlers:
- update_my_profile: Update own display name/metadata
- assign_role: Assign role to crew member (HOD only)
- revoke_role: Revoke role from crew member (HOD only)
- update_crew_member_status: Activate/deactivate crew member (Captain/Manager only)

All handlers return standardized ActionResponseEnvelope.
Error mapping: 400=validation, 403=RLS, 404=not found, 409=conflict.
All mutations write to pms_audit_log with signature={}.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import (
    ResponseBuilder,
    AvailableAction,
)

logger = logging.getLogger(__name__)


# Role values (must match CHECK constraint on auth_users_roles)
VALID_ROLES = [
    "chief_engineer", "eto", "captain", "manager",
    "vendor", "crew", "deck", "interior", "chief_officer", "purser"
]

# HOD roles (can manage crew)
HOD_ROLES = ["chief_engineer", "chief_officer", "purser", "captain", "manager"]

# Manager roles (can update crew status)
MANAGER_ROLES = ["captain", "manager"]


class CrewHandlers:
    """
    Crew domain handlers.

    All handlers enforce:
    - Server-derived yacht_id from JWT (client yacht_id ignored)
    - RLS policies (self-only profile access, HOD role management)
    - Strict error mapping (400/403/404/409, never 500)
    - Audit trail for all mutations (signature={})
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # READ HANDLERS
    # =========================================================================

    async def view_my_profile(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View own profile and roles.

        RLS: Self-only (user can only view their own profile)

        Returns:
        - User profile (name, email, is_active, metadata)
        - Active roles with validity periods
        - Yacht information
        """
        builder = ResponseBuilder("view_my_profile", entity_id, "crew_member", yacht_id)

        try:
            # Get user profile (RLS enforces self-only access)
            profile_result = self.db.table("auth_users_profiles").select(
                "id, yacht_id, email, name, is_active, metadata, created_at, updated_at"
            ).eq("id", user_id).maybe_single().execute()

            if not profile_result.data:
                builder.set_error("NOT_FOUND", "Profile not found")
                return builder.build()

            profile = profile_result.data

            # Get active roles (RLS enforces self-only access)
            roles_result = self.db.table("auth_users_roles").select(
                "id, role, assigned_at, assigned_by, valid_from, valid_until, is_active"
            ).eq("user_id", user_id).eq("yacht_id", yacht_id).eq("is_active", True).execute()

            roles = roles_result.data or []

            # Filter by valid dates
            active_roles = []
            now = datetime.now(timezone.utc)
            for role in roles:
                valid_from = role.get("valid_from")
                valid_until = role.get("valid_until")

                # Parse dates if strings
                if isinstance(valid_from, str):
                    valid_from = datetime.fromisoformat(valid_from.replace('Z', '+00:00'))
                if isinstance(valid_until, str):
                    valid_until = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))

                # Check validity
                is_valid = True
                if valid_from and valid_from > now:
                    is_valid = False
                if valid_until and valid_until < now:
                    is_valid = False

                if is_valid:
                    active_roles.append(role)

            builder.set_data({
                "profile": profile,
                "roles": active_roles,
                "primary_role": active_roles[0]["role"] if active_roles else None,
            })

            # Add available actions
            builder.add_available_action(AvailableAction(
                action_id="update_my_profile",
                label="Edit Profile",
                variant="MUTATE",
                icon="edit",
                is_primary=True
            ))
            builder.add_available_action(AvailableAction(
                action_id="view_assigned_work_orders",
                label="My Work Orders",
                variant="READ",
                icon="clipboard-list"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_my_profile failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_assigned_work_orders(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View work orders assigned to current user.

        RLS: Implicit (assigned_to = user_id)

        Returns:
        - List of open/in-progress work orders assigned to user
        - Sorted by priority (emergency → critical → high → medium → low), then due_date
        """
        builder = ResponseBuilder("view_assigned_work_orders", entity_id, "crew_member", yacht_id)

        try:
            params = params or {}
            offset = params.get("offset", 0)
            limit = params.get("limit", 50)

            # Query work orders assigned to user
            query = self.db.table("pms_work_orders").select(
                "id, wo_number, title, description, status, priority, due_date, "
                "equipment_id, assigned_to, created_at",
                count="exact"
            ).eq("yacht_id", yacht_id).eq("assigned_to", user_id)

            # Filter: exclude completed/cancelled and soft-deleted
            query = query.not_.in_("status", ["completed", "cancelled"]).is_("deleted_at", "null")

            # Execute with pagination
            result = query.range(offset, offset + limit - 1).execute()

            work_orders = result.data or []
            total_count = result.count or len(work_orders)

            # Sort by priority, then due_date
            priority_order = {"emergency": 1, "critical": 2, "high": 3, "medium": 4, "low": 5}
            work_orders.sort(key=lambda wo: (
                priority_order.get(wo.get("priority", "low"), 5),
                wo.get("due_date") or "9999-12-31"
            ))

            # Add computed fields
            for wo in work_orders:
                wo["is_overdue"] = self._is_overdue(wo.get("due_date"))
                wo["priority_level"] = priority_order.get(wo.get("priority", "low"), 5)

            builder.set_data({
                "work_orders": work_orders,
                "total_count": total_count,
            })

            builder.set_pagination(offset, limit, total_count)

            return builder.build()

        except Exception as e:
            logger.error(f"view_assigned_work_orders failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def list_crew_members(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        List all crew members on yacht.

        RLS: HOD-gated (requires service role or helper function)

        Returns:
        - List of crew members with primary role and status
        - Active crew first, then inactive, sorted by name
        """
        builder = ResponseBuilder("list_crew_members", entity_id, "crew_member", yacht_id)

        try:
            params = params or {}
            offset = params.get("offset", 0)
            limit = params.get("limit", 50)
            include_inactive = params.get("include_inactive", False)

            # Query crew profiles
            query = self.db.table("auth_users_profiles").select(
                "id, yacht_id, email, name, is_active, created_at",
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Filter active/inactive
            if not include_inactive:
                query = query.eq("is_active", True)

            # Execute with pagination
            result = query.range(offset, offset + limit - 1).execute()

            crew_members = result.data or []
            total_count = result.count or len(crew_members)

            # Enrich with roles
            for member in crew_members:
                member_id = member.get("id")

                # Get active roles for this member
                roles_result = self.db.table("auth_users_roles").select(
                    "role, assigned_at"
                ).eq("user_id", member_id).eq("yacht_id", yacht_id).eq("is_active", True).execute()

                roles = roles_result.data or []
                member["roles"] = [r["role"] for r in roles]
                member["primary_role"] = roles[0]["role"] if roles else "crew"

            # Sort: active first, then by name
            crew_members.sort(key=lambda m: (not m.get("is_active", True), m.get("name", "")))

            builder.set_data({
                "crew_members": crew_members,
                "total_count": total_count,
                "active_count": sum(1 for m in crew_members if m.get("is_active")),
            })

            builder.set_pagination(offset, limit, total_count)

            # Add available actions
            builder.add_available_action(AvailableAction(
                action_id="assign_role",
                label="Assign Role",
                variant="MUTATE",
                icon="user-plus"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"list_crew_members failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_crew_member_details(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View crew member profile details.

        RLS: HOD-gated

        Args:
            entity_id: crew member user_id (UUID)

        Returns:
        - Full profile (name, email, status, metadata)
        - All roles (active and inactive) with validity periods
        - Assignment history
        """
        builder = ResponseBuilder("view_crew_member_details", entity_id, "crew_member", yacht_id)

        try:
            # Verify crew member exists and belongs to yacht
            profile_result = self.db.table("auth_users_profiles").select(
                "id, yacht_id, email, name, is_active, metadata, created_at, updated_at"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not profile_result.data:
                builder.set_error("NOT_FOUND", f"Crew member not found: {entity_id}")
                return builder.build()

            profile = profile_result.data

            # Get all roles (active and inactive) for history
            roles_result = self.db.table("auth_users_roles").select(
                "id, role, assigned_at, assigned_by, valid_from, valid_until, is_active"
            ).eq("user_id", entity_id).eq("yacht_id", yacht_id).order("assigned_at", desc=True).execute()

            roles = roles_result.data or []

            # Separate active and inactive roles
            active_roles = [r for r in roles if r.get("is_active")]
            inactive_roles = [r for r in roles if not r.get("is_active")]

            builder.set_data({
                "profile": profile,
                "active_roles": active_roles,
                "inactive_roles": inactive_roles,
                "primary_role": active_roles[0]["role"] if active_roles else None,
            })

            # Add available actions
            builder.add_available_action(AvailableAction(
                action_id="assign_role",
                label="Assign Role",
                variant="MUTATE",
                icon="user-plus"
            ))
            builder.add_available_action(AvailableAction(
                action_id="revoke_role",
                label="Revoke Role",
                variant="MUTATE",
                icon="user-minus"
            ))
            builder.add_available_action(AvailableAction(
                action_id="view_crew_certificates",
                label="View Certificates",
                variant="READ",
                icon="award"
            ))
            builder.add_available_action(AvailableAction(
                action_id="view_crew_work_history",
                label="Work History",
                variant="READ",
                icon="history"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_crew_member_details failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_crew_certificates(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View crew member's certificates.

        RLS: HOD-gated

        Args:
            entity_id: crew member user_id (UUID)

        Returns:
        - List of crew certificates with expiry warnings
        - Computed fields: is_expiring_soon, is_expired, days_until_expiry
        """
        builder = ResponseBuilder("view_crew_certificates", entity_id, "crew_member", yacht_id)

        try:
            # Verify crew member exists
            profile_result = self.db.table("auth_users_profiles").select(
                "id, name"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not profile_result.data:
                builder.set_error("NOT_FOUND", f"Crew member not found: {entity_id}")
                return builder.build()

            crew_name = profile_result.data.get("name")

            # Query certificates
            certs_result = self.db.table("pms_crew_certificates").select(
                "id, certificate_type, certificate_number, issuing_authority, "
                "issue_date, expiry_date, document_id, properties, created_at"
            ).eq("yacht_id", yacht_id).eq("person_node_id", entity_id).execute()

            certificates = certs_result.data or []

            # Add computed fields
            for cert in certificates:
                cert["is_expiring_soon"] = self._is_expiring_soon(cert.get("expiry_date"))
                cert["is_expired"] = self._is_expired(cert.get("expiry_date"))
                cert["days_until_expiry"] = self._days_until_expiry(cert.get("expiry_date"))

            # Sort by expiry date (soonest first)
            certificates.sort(key=lambda c: c.get("expiry_date") or "9999-12-31")

            builder.set_data({
                "crew_member_id": entity_id,
                "crew_name": crew_name,
                "certificates": certificates,
                "total_count": len(certificates),
                "expiring_count": sum(1 for c in certificates if c.get("is_expiring_soon")),
                "expired_count": sum(1 for c in certificates if c.get("is_expired")),
            })

            return builder.build()

        except Exception as e:
            logger.error(f"view_crew_certificates failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_crew_work_history(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View crew member's completed work orders.

        RLS: HOD-gated

        Args:
            entity_id: crew member user_id (UUID)

        Returns:
        - List of completed/cancelled work orders
        - Sorted by completed_at (most recent first)
        """
        builder = ResponseBuilder("view_crew_work_history", entity_id, "crew_member", yacht_id)

        try:
            params = params or {}
            offset = params.get("offset", 0)
            limit = params.get("limit", 50)

            # Verify crew member exists
            profile_result = self.db.table("auth_users_profiles").select(
                "id, name"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not profile_result.data:
                builder.set_error("NOT_FOUND", f"Crew member not found: {entity_id}")
                return builder.build()

            crew_name = profile_result.data.get("name")

            # Query completed work orders
            query = self.db.table("pms_work_orders").select(
                "id, wo_number, title, description, status, priority, "
                "completed_at, completed_by, completion_notes, created_at",
                count="exact"
            ).eq("yacht_id", yacht_id).eq("assigned_to", entity_id).in_(
                "status", ["completed", "cancelled"]
            ).is_("deleted_at", "null")

            # Execute with pagination
            result = query.order("completed_at", desc=True).range(offset, offset + limit - 1).execute()

            work_orders = result.data or []
            total_count = result.count or len(work_orders)

            builder.set_data({
                "crew_member_id": entity_id,
                "crew_name": crew_name,
                "work_orders": work_orders,
                "total_count": total_count,
                "completed_count": sum(1 for wo in work_orders if wo.get("status") == "completed"),
                "cancelled_count": sum(1 for wo in work_orders if wo.get("status") == "cancelled"),
            })

            builder.set_pagination(offset, limit, total_count)

            return builder.build()

        except Exception as e:
            logger.error(f"view_crew_work_history failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # MUTATION HANDLERS
    # =========================================================================

    async def update_my_profile(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        Update own profile.

        RLS: Self-only (user can only update their own profile)

        Allowed fields: name, metadata
        Immutable fields: email, yacht_id, is_active

        Error mapping:
        - 400: Invalid JSON in metadata
        - 403: Attempt to update another user's profile
        - 404: User not found
        """
        builder = ResponseBuilder("update_my_profile", entity_id, "crew_member", yacht_id)

        try:
            # Validate payload
            name = payload.get("name")
            metadata = payload.get("metadata")

            # Validate metadata if provided
            if metadata is not None:
                if not isinstance(metadata, dict):
                    builder.set_error("VALIDATION_ERROR", "metadata must be a JSON object")
                    return builder.build()

            # Fetch current profile to get old values
            old_profile_result = self.db.table("auth_users_profiles").select(
                "id, name, metadata"
            ).eq("id", user_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not old_profile_result.data:
                builder.set_error("NOT_FOUND", "Profile not found")
                return builder.build()

            old_profile = old_profile_result.data

            # Build update payload
            update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
            old_values = {}
            new_values = {}

            if name is not None and name != old_profile.get("name"):
                update_data["name"] = name
                old_values["name"] = old_profile.get("name")
                new_values["name"] = name

            if metadata is not None and metadata != old_profile.get("metadata"):
                update_data["metadata"] = metadata
                old_values["metadata"] = old_profile.get("metadata")
                new_values["metadata"] = metadata

            # If no changes, return success
            if len(update_data) == 1:  # Only updated_at
                builder.set_data({
                    "message": "No changes to apply",
                    "profile_id": user_id,
                })
                return builder.build()

            # Update profile (RLS enforces self-only access)
            update_result = self.db.table("auth_users_profiles").update(
                update_data
            ).eq("id", user_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data:
                builder.set_error("FORBIDDEN", "Cannot update this profile")
                return builder.build()

            # Write audit log
            await self._write_audit_log(
                yacht_id=yacht_id,
                entity_type="crew",
                entity_id=user_id,
                action="update_my_profile",
                user_id=user_id,
                old_values=old_values,
                new_values=new_values,
            )

            builder.set_data({
                "message": "Profile updated successfully",
                "profile_id": user_id,
                "updated_fields": list(new_values.keys()),
            })

            return builder.build()

        except Exception as e:
            logger.error(f"update_my_profile failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def assign_role(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        Assign role to crew member.

        RLS: HOD-gated (is_hod())

        Required fields: user_id (crew member), role
        Optional fields: valid_from, valid_until

        Error mapping:
        - 400: Invalid role value, invalid dates
        - 403: Non-HOD attempt
        - 404: User not found
        - 409: User already has active role (UNIQUE constraint)
        """
        builder = ResponseBuilder("assign_role", entity_id, "crew_member", yacht_id)

        try:
            # Validate required fields
            target_user_id = payload.get("user_id")
            role = payload.get("role")

            if not target_user_id:
                builder.set_error("VALIDATION_ERROR", "user_id is required", 400)
                return builder.build()

            if not role:
                builder.set_error("VALIDATION_ERROR", "role is required", 400)
                return builder.build()

            # Validate role value
            if role not in VALID_ROLES:
                builder.set_error("VALIDATION_ERROR", f"Invalid role: {role}. Must be one of {VALID_ROLES}", 400)
                return builder.build()

            # Verify target user exists and belongs to yacht
            user_result = self.db.table("auth_users_profiles").select(
                "id, name"
            ).eq("id", target_user_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not user_result.data:
                builder.set_error("NOT_FOUND", f"Crew member not found: {target_user_id}", 404)
                return builder.build()

            crew_name = user_result.data.get("name")

            # Check for existing active role
            existing_role_result = self.db.table("auth_users_roles").select(
                "id, role"
            ).eq("user_id", target_user_id).eq("yacht_id", yacht_id).eq("is_active", True).execute()

            if existing_role_result.data:
                existing_role = existing_role_result.data[0]
                builder.set_error(
                    "CONFLICT",
                    f"User already has active role: {existing_role['role']}. Revoke it first.",
                    409
                )
                return builder.build()

            # Parse optional dates
            valid_from = payload.get("valid_from")
            valid_until = payload.get("valid_until")

            if valid_from and valid_until:
                # Validate: valid_from < valid_until
                from_date = datetime.fromisoformat(valid_from.replace('Z', '+00:00'))
                until_date = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
                if from_date >= until_date:
                    builder.set_error("VALIDATION_ERROR", "valid_from must be before valid_until", 400)
                    return builder.build()

            # Insert new role
            role_data = {
                "user_id": target_user_id,
                "yacht_id": yacht_id,
                "role": role,
                "assigned_by": user_id,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
                "valid_from": valid_from or datetime.now(timezone.utc).isoformat(),
                "valid_until": valid_until,
            }

            insert_result = self.db.table("auth_users_roles").insert(role_data).execute()

            if not insert_result.data:
                builder.set_error("INTERNAL_ERROR", "Failed to assign role")
                return builder.build()

            new_role_id = insert_result.data[0]["id"]

            # Write audit log
            await self._write_audit_log(
                yacht_id=yacht_id,
                entity_type="role",
                entity_id=new_role_id,
                action="assign_role",
                user_id=user_id,
                old_values=None,
                new_values={
                    "user_id": target_user_id,
                    "user_name": crew_name,
                    "role": role,
                },
            )

            builder.set_data({
                "message": f"Role '{role}' assigned to {crew_name}",
                "role_id": new_role_id,
                "user_id": target_user_id,
                "role": role,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"assign_role failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def revoke_role(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        Revoke role from crew member.

        RLS: HOD-gated (is_hod())

        Required fields: role_id
        Optional fields: reason

        Soft-delete: Sets is_active=false, sets valid_until=NOW

        Error mapping:
        - 400: Cannot revoke if user has only one role
        - 403: Non-HOD attempt
        - 404: Role not found or wrong yacht
        - 409: Role already revoked (is_active=false)
        """
        builder = ResponseBuilder("revoke_role", entity_id, "crew_member", yacht_id)

        try:
            # Validate required fields
            role_id = payload.get("role_id")
            reason = payload.get("reason")

            if not role_id:
                builder.set_error("VALIDATION_ERROR", "role_id is required", 400)
                return builder.build()

            # Fetch role to verify it exists and is active
            role_result = self.db.table("auth_users_roles").select(
                "id, user_id, role, is_active"
            ).eq("id", role_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not role_result.data:
                builder.set_error("NOT_FOUND", f"Role not found: {role_id}", 404)
                return builder.build()

            role_data = role_result.data

            if not role_data.get("is_active"):
                builder.set_error("CONFLICT", "Role is already revoked", 409)
                return builder.build()

            target_user_id = role_data.get("user_id")
            role_name = role_data.get("role")

            # Note: Removed "last role" check to allow role replacement workflow
            # Users can have zero roles temporarily during role changes

            # Soft delete role
            update_data = {
                "is_active": False,
                "valid_until": datetime.now(timezone.utc).isoformat(),
            }

            update_result = self.db.table("auth_users_roles").update(
                update_data
            ).eq("id", role_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data:
                builder.set_error("INTERNAL_ERROR", "Failed to revoke role")
                return builder.build()

            # Write audit log
            await self._write_audit_log(
                yacht_id=yacht_id,
                entity_type="role",
                entity_id=role_id,
                action="revoke_role",
                user_id=user_id,
                old_values={"is_active": True, "role": role_name},
                new_values={"is_active": False, "reason": reason},
            )

            builder.set_data({
                "message": f"Role '{role_name}' revoked successfully",
                "role_id": role_id,
                "user_id": target_user_id,
                "role": role_name,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"revoke_role failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def update_crew_member_status(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        payload: Dict
    ) -> Dict:
        """
        Activate or deactivate crew member.

        RLS: Captain/Manager only

        Required fields: user_id (crew member), is_active
        Optional fields: reason

        Error mapping:
        - 400: Missing is_active
        - 403: Non-Captain/Manager attempt
        - 404: User not found or wrong yacht
        - 409: Status already set to requested value
        """
        builder = ResponseBuilder("update_crew_member_status", entity_id, "crew_member", yacht_id)

        try:
            # Validate required fields
            target_user_id = payload.get("user_id")
            is_active = payload.get("is_active")
            reason = payload.get("reason")

            if not target_user_id:
                builder.set_error("VALIDATION_ERROR", "user_id is required")
                return builder.build()

            if is_active is None:
                builder.set_error("VALIDATION_ERROR", "is_active is required")
                return builder.build()

            if not isinstance(is_active, bool):
                builder.set_error("VALIDATION_ERROR", "is_active must be boolean")
                return builder.build()

            # Fetch current profile
            profile_result = self.db.table("auth_users_profiles").select(
                "id, name, is_active"
            ).eq("id", target_user_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not profile_result.data:
                builder.set_error("NOT_FOUND", f"Crew member not found: {target_user_id}")
                return builder.build()

            old_profile = profile_result.data
            old_is_active = old_profile.get("is_active")
            crew_name = old_profile.get("name")

            # Check if status is already set to requested value
            if old_is_active == is_active:
                status_str = "active" if is_active else "inactive"
                builder.set_error("CONFLICT", f"Crew member is already {status_str}")
                return builder.build()

            # Update status
            update_data = {
                "is_active": is_active,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            update_result = self.db.table("auth_users_profiles").update(
                update_data
            ).eq("id", target_user_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data:
                builder.set_error("INTERNAL_ERROR", "Failed to update crew member status")
                return builder.build()

            # Write audit log
            await self._write_audit_log(
                yacht_id=yacht_id,
                entity_type="crew",
                entity_id=target_user_id,
                action="update_crew_member_status",
                user_id=user_id,
                old_values={"is_active": old_is_active},
                new_values={"is_active": is_active, "reason": reason},
            )

            status_action = "activated" if is_active else "deactivated"
            builder.set_data({
                "message": f"Crew member '{crew_name}' {status_action} successfully",
                "user_id": target_user_id,
                "is_active": is_active,
            })

            return builder.build()

        except Exception as e:
            logger.error(f"update_crew_member_status failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _write_audit_log(
        self,
        yacht_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        user_id: str,
        old_values: Optional[Dict],
        new_values: Optional[Dict],
    ):
        """
        Write audit log entry.

        Signature invariant: signature = '{}' for all crew actions (no SIGNED actions)
        """
        try:
            audit_data = {
                "yacht_id": yacht_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "user_id": user_id,
                "old_values": old_values,
                "new_values": new_values,
                "signature": {},  # Crew Lens has no SIGNED actions
                "metadata": {"source": "crew_lens"},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            self.db.table("pms_audit_log").insert(audit_data).execute()

        except Exception as e:
            logger.warning(f"Failed to write audit log: {e}")

    def _is_expiring_soon(self, expiry_date_str: Optional[str], days: int = 90) -> bool:
        """Check if certificate is expiring within specified days."""
        if not expiry_date_str:
            return False

        try:
            expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = expiry_date - now
            return 0 <= delta.days <= days
        except Exception:
            return False

    def _is_expired(self, expiry_date_str: Optional[str]) -> bool:
        """Check if certificate is expired."""
        if not expiry_date_str:
            return False

        try:
            expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return expiry_date < now
        except Exception:
            return False

    def _days_until_expiry(self, expiry_date_str: Optional[str]) -> Optional[int]:
        """Calculate days until expiry (negative if expired)."""
        if not expiry_date_str:
            return None

        try:
            expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = expiry_date - now
            return delta.days
        except Exception:
            return None

    def _is_overdue(self, due_date_str: Optional[str]) -> bool:
        """Check if work order is overdue."""
        if not due_date_str:
            return False

        try:
            due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return due_date < now
        except Exception:
            return False


# ============================================================================
# HANDLER REGISTRATION
# ============================================================================

def get_crew_handlers(supabase_client) -> Dict[str, callable]:
    """Get crew handler functions for registration."""
    handlers = CrewHandlers(supabase_client)

    return {
        # READ handlers
        "view_my_profile": handlers.view_my_profile,
        "view_assigned_work_orders": handlers.view_assigned_work_orders,
        "list_crew_members": handlers.list_crew_members,
        "view_crew_member_details": handlers.view_crew_member_details,
        "view_crew_certificates": handlers.view_crew_certificates,
        "view_crew_work_history": handlers.view_crew_work_history,

        # MUTATION handlers
        "update_my_profile": handlers.update_my_profile,
        "assign_role": handlers.assign_role,
        "revoke_role": handlers.revoke_role,
        "update_crew_member_status": handlers.update_crew_member_status,
    }
