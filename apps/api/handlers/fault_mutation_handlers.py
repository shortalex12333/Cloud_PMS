"""
Fault Mutation Handlers
========================

MUTATE actions for faults (Fault Lens v1 - Binding Brief 2026-01-27).

Actions:
- report_fault (crew/HOD/captain)
- acknowledge_fault (HOD/captain)
- close_fault (HOD/captain)
- update_fault (HOD/captain)
- add_fault_photo (crew/HOD/captain)
- add_fault_note (crew/HOD/captain)
- diagnose_fault (HOD/captain)
- reopen_fault (HOD/captain)
- mark_fault_false_alarm (HOD/captain)

Severity mapping: cosmetic|minor|major|critical|safety
- "medium" → "minor" (legacy compatibility)
- "high" → "major" (legacy compatibility)
- "low" → "cosmetic" (legacy compatibility)

Signature invariant: pms_audit_log.signature is NEVER NULL
- Non-signed actions: signature = {}
- Signed actions: signature = {pin_hash, totp_verified, signed_at, ...}
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
import logging
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import ResponseBuilder

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Valid severity values (DB enum)
VALID_SEVERITIES = ["cosmetic", "minor", "major", "critical", "safety"]

# Severity mapping for legacy/alternative values
SEVERITY_MAPPING = {
    "low": "cosmetic",
    "medium": "minor",
    "high": "major",
    # These map to themselves
    "cosmetic": "cosmetic",
    "minor": "minor",
    "major": "major",
    "critical": "critical",
    "safety": "safety",
}

# Symptom-based severity inference (PR #3: binding brief)
# "overheating/leak/alarm/shutdown" → major
# "scratch/paint" → cosmetic
# "fire/smoke/flood/loss of steering" → critical
SYMPTOM_SEVERITY_KEYWORDS = {
    "critical": [
        "fire", "smoke", "flood", "flooding", "loss of steering",
        "steering failure", "total failure", "emergency", "sinking",
        "ingress", "water ingress", "abandon",
    ],
    "major": [
        "overheating", "overheat", "leak", "leaking", "alarm",
        "shutdown", "shut down", "not working", "failed", "failure",
        "broken", "malfunction", "inoperative", "disabled",
    ],
    "cosmetic": [
        "scratch", "scratched", "paint", "chip", "chipped", "dent",
        "stain", "discoloration", "faded", "worn", "aesthetic",
        "appearance", "cosmetic",
    ],
}

# Valid fault statuses
VALID_STATUSES = ["open", "investigating", "work_ordered", "resolved", "closed", "false_alarm"]

# Status transitions
STATUS_TRANSITIONS = {
    "open": ["investigating", "work_ordered", "resolved", "closed", "false_alarm"],
    "investigating": ["work_ordered", "resolved", "closed"],
    "work_ordered": ["resolved", "closed"],
    "resolved": ["closed", "open"],  # Can reopen
    "closed": ["open"],  # Can reopen
    "false_alarm": [],  # Terminal
}


# =============================================================================
# SEVERITY MAPPING HELPER
# =============================================================================

def map_severity(severity: str) -> str:
    """
    Map severity to valid DB enum value.

    Args:
        severity: Input severity (may be legacy value)

    Returns:
        Valid severity from VALID_SEVERITIES

    Raises:
        ValueError: If severity cannot be mapped
    """
    if not severity:
        return "minor"  # Default

    severity_lower = severity.lower().strip()

    if severity_lower in SEVERITY_MAPPING:
        return SEVERITY_MAPPING[severity_lower]

    raise ValueError(
        f"Invalid severity '{severity}'. "
        f"Valid values: {', '.join(VALID_SEVERITIES)}. "
        f"Mappings: low→cosmetic, medium→minor, high→major"
    )


def infer_severity_from_text(text: str) -> str:
    """
    Infer severity from symptom/description text.

    PR #3 Binding Brief mapping:
    - "fire/smoke/flood/loss of steering" → critical
    - "overheating/leak/alarm/shutdown" → major
    - "scratch/paint" → cosmetic
    - default → minor

    Returns:
        Inferred severity (never raises)
    """
    if not text:
        return "minor"

    text_lower = text.lower()

    # Check critical keywords first (highest priority)
    for keyword in SYMPTOM_SEVERITY_KEYWORDS["critical"]:
        if keyword in text_lower:
            return "critical"

    # Check major keywords
    for keyword in SYMPTOM_SEVERITY_KEYWORDS["major"]:
        if keyword in text_lower:
            return "major"

    # Check cosmetic keywords
    for keyword in SYMPTOM_SEVERITY_KEYWORDS["cosmetic"]:
        if keyword in text_lower:
            return "cosmetic"

    # Default to minor
    return "minor"


# =============================================================================
# FAULT MUTATION HANDLERS CLASS
# =============================================================================

class FaultMutationHandlers:
    """
    MUTATE handlers for fault actions.

    Implements Fault Lens v1 binding brief:
    - Crew: report_fault, add_fault_photo, add_fault_note
    - HOD + captain: all other mutations
    - Signature invariant enforced for audit log
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # REPORT FAULT
    # =========================================================================

    async def report_fault_prefill(
        self,
        equipment_id: Optional[str] = None,
        yacht_id: str = None,
        user_id: str = None,
        query_text: Optional[str] = None,
    ) -> Dict:
        """
        GET /v1/actions/prefill?action=report_fault&equipment_id={id}

        Pre-fill fault report form.

        Returns:
        - Equipment details if equipment_id provided
        - Default severity (minor)
        - Extracted entities from query_text
        - Recent faults for context
        """
        prefill_data = {
            "severity": "minor",  # Default per binding brief
            "status": "open",
        }

        # If equipment provided, fetch details
        if equipment_id and yacht_id:
            try:
                eq_result = self.db.table("pms_equipment").select(
                    "id, name, equipment_type, location, status"
                ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if eq_result.data:
                    equipment = eq_result.data
                    prefill_data["equipment"] = {
                        "id": equipment["id"],
                        "name": equipment["name"],
                        "type": equipment.get("equipment_type"),
                        "location": equipment.get("location"),
                        "status": equipment.get("status"),
                    }

                    # Fetch recent faults for this equipment
                    recent_faults = self.db.table("pms_faults").select(
                        "id, fault_code, title, severity, status, created_at"
                    ).eq("equipment_id", equipment_id).eq(
                        "yacht_id", yacht_id
                    ).order("created_at", desc=True).limit(5).execute()

                    if recent_faults.data:
                        prefill_data["recent_faults"] = recent_faults.data
                        prefill_data["recurrence_warning"] = len(recent_faults.data) > 2

            except Exception as e:
                logger.warning(f"Failed to fetch equipment for prefill: {e}")

        # Extract title from query_text if provided
        if query_text:
            prefill_data["title"] = query_text[:100]  # Truncate for title
            prefill_data["description"] = query_text

        return {
            "status": "success",
            "action": "report_fault",
            "prefill": prefill_data,
        }

    async def report_fault_preview(
        self,
        title: str,
        severity: str,
        equipment_id: Optional[str],
        description: str,
        yacht_id: str,
        user_id: str,
    ) -> Dict:
        """
        POST /v1/actions/preview (action=report_fault)

        Preview fault report before commit.

        Validates:
        - Equipment exists (if provided)
        - Severity is valid (maps legacy values)
        - Title is not empty

        Returns:
        - Preview of fault that will be created
        - Warning if critical/safety severity
        - Suggested work order if severity critical/safety
        """
        warnings = []
        suggestions = []

        # Map and validate severity
        try:
            mapped_severity = map_severity(severity)
        except ValueError as e:
            return {
                "status": "error",
                "error_code": "INVALID_SEVERITY",
                "message": str(e),
            }

        # Validate title
        if not title or len(title.strip()) == 0:
            return {
                "status": "error",
                "error_code": "TITLE_REQUIRED",
                "message": "Fault title is required",
            }

        # Validate equipment exists
        equipment_name = None
        if equipment_id:
            eq_result = self.db.table("pms_equipment").select(
                "id, name"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not eq_result.data:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}",
                }

            equipment_name = eq_result.data["name"]

        # Generate preview fault code
        preview_fault_code = f"FLT-{uuid.uuid4().hex[:8].upper()}"

        # Warnings for critical/safety faults
        if mapped_severity in ("critical", "safety"):
            warnings.append({
                "type": "severity_warning",
                "message": f"{mapped_severity.upper()} fault will be added to handover automatically",
            })
            suggestions.append({
                "action": "create_work_order_from_fault",
                "reason": "High severity faults typically require immediate work order",
            })

        preview = {
            "fault_code": preview_fault_code,
            "title": title,
            "description": description,
            "severity": mapped_severity,
            "status": "open",
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

        # Show severity mapping if applied
        if severity.lower() != mapped_severity:
            warnings.append({
                "type": "severity_mapped",
                "message": f"Severity '{severity}' mapped to '{mapped_severity}'",
            })

        return {
            "status": "success",
            "action": "report_fault",
            "preview": preview,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    async def report_fault_execute(
        self,
        yacht_id: str,
        user_id: str,
        title: str,
        severity: str,
        description: str,
        equipment_id: Optional[str] = None,
        signature: Optional[Dict] = None,
    ) -> Dict:
        """
        POST /v1/actions/execute (action=report_fault)

        Execute fault report.

        Creates:
        - Fault record (status=open)
        - Audit log entry (signature={} for non-signed)
        - Handover item (if severity=critical/safety)

        Returns:
        - fault_id
        - fault_code
        - next_actions
        """
        try:
            # Map severity
            try:
                mapped_severity = map_severity(severity)
            except ValueError as e:
                return {
                    "status": "error",
                    "error_code": "INVALID_SEVERITY",
                    "message": str(e),
                }

            # Validate equipment exists (if provided)
            equipment_name = None
            if equipment_id:
                eq_result = self.db.table("pms_equipment").select(
                    "id, name"
                ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not eq_result.data:
                    return {
                        "status": "error",
                        "error_code": "EQUIPMENT_NOT_FOUND",
                        "message": f"Equipment not found: {equipment_id}",
                    }

                equipment_name = eq_result.data["name"]

            # Generate fault code
            fault_code = f"FLT-{uuid.uuid4().hex[:8].upper()}"

            # Create fault record
            now = datetime.now(timezone.utc).isoformat()
            fault_data = {
                "yacht_id": yacht_id,
                "fault_code": fault_code,
                "title": title,
                "description": description,
                "severity": mapped_severity,
                "status": "open",
                "equipment_id": equipment_id,
                "detected_at": now,
                "metadata": {"reported_by": user_id},
                "created_at": now,
                "updated_at": now,
            }

            fault_result = self.db.table("pms_faults").insert(fault_data).execute()

            if not fault_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create fault",
                }

            fault = fault_result.data[0]

            # Create audit log entry (signature invariant: {} for non-signed)
            audit_log_id = await self._create_audit_log(
                yacht_id=yacht_id,
                action="report_fault",
                entity_type="fault",
                entity_id=fault["id"],
                user_id=user_id,
                new_values=fault_data,
                signature=signature or {},  # INVARIANT: never None
            )

            # If critical/safety, add to handover
            handover_item_id = None
            if mapped_severity in ("critical", "safety"):
                try:
                    handover_item_id = await self._add_to_handover(
                        yacht_id=yacht_id,
                        entity_type="fault",
                        entity_id=fault["id"],
                        summary=f"{mapped_severity.upper()}: {title}",
                        priority="urgent" if mapped_severity == "safety" else "high",
                        user_id=user_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to add fault to handover: {e}")

            # Build response
            result = {
                "fault": {
                    "id": fault["id"],
                    "fault_code": fault["fault_code"],
                    "title": fault["title"],
                    "description": fault.get("description"),
                    "severity": fault["severity"],
                    "status": fault["status"],
                    "equipment_id": fault.get("equipment_id"),
                    "equipment_name": equipment_name,
                    "detected_at": fault["detected_at"],
                    "created_at": fault["created_at"],
                },
                "audit_log_id": audit_log_id,
                "handover_item_id": handover_item_id,
                "next_actions": [
                    "add_fault_note",
                    "add_fault_photo",
                    "view_fault_detail",
                ],
            }

            message = f"✓ {fault_code} reported"
            if handover_item_id:
                message += " (added to handover)"

            return {
                "status": "success",
                "action": "report_fault",
                "result": result,
                "message": message,
            }

        except Exception as e:
            logger.error(f"report_fault_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # ACKNOWLEDGE FAULT
    # =========================================================================

    async def acknowledge_fault_execute(
        self,
        yacht_id: str,
        user_id: str,
        fault_id: str,
        notes: Optional[str] = None,
        signature: Optional[Dict] = None,
    ) -> Dict:
        """
        Acknowledge a fault (HOD/captain only).

        Transitions fault from 'open' to 'investigating'.
        """
        try:
            # Get current fault
            fault = self.db.table("pms_faults").select(
                "*"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Fault not found: {fault_id}",
                }

            old_fault = fault.data
            old_status = old_fault.get("status")

            # Validate status transition
            if old_status not in ("open",):
                return {
                    "status": "error",
                    "error_code": "INVALID_STATUS",
                    "message": f"Cannot acknowledge fault with status '{old_status}'. Must be 'open'.",
                }

            # Update fault
            now = datetime.now(timezone.utc).isoformat()
            update_data = {
                "status": "investigating",
                "acknowledged_at": now,
                "acknowledged_by": user_id,
                "updated_at": now,
            }

            if notes:
                update_data["metadata"] = {
                    **(old_fault.get("metadata") or {}),
                    "acknowledgement_notes": notes,
                }

            result = self.db.table("pms_faults").update(update_data).eq(
                "id", fault_id
            ).eq("yacht_id", yacht_id).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "UPDATE_FAILED",
                    "message": "Failed to acknowledge fault",
                }

            # Audit log (signature invariant: {} for non-signed)
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="acknowledge_fault",
                entity_type="fault",
                entity_id=fault_id,
                user_id=user_id,
                old_values={"status": old_status},
                new_values={"status": "investigating", "notes": notes},
                signature=signature or {},
            )

            # Send notification to reporter
            await self._notify_fault_acknowledged(
                yacht_id=yacht_id,
                fault_id=fault_id,
                fault_code=old_fault.get("fault_code"),
                acknowledged_by=user_id,
            )

            return {
                "status": "success",
                "action": "acknowledge_fault",
                "result": {
                    "fault_id": fault_id,
                    "fault_code": old_fault.get("fault_code"),
                    "old_status": old_status,
                    "new_status": "investigating",
                },
                "message": f"✓ {old_fault.get('fault_code')} acknowledged",
            }

        except Exception as e:
            logger.error(f"acknowledge_fault failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # CLOSE FAULT
    # =========================================================================

    async def close_fault_execute(
        self,
        yacht_id: str,
        user_id: str,
        fault_id: str,
        resolution_notes: Optional[str] = None,
        signature: Optional[Dict] = None,
    ) -> Dict:
        """
        Close a fault (HOD/captain only).

        Transitions fault to 'closed'.
        """
        try:
            # Get current fault
            fault = self.db.table("pms_faults").select(
                "*"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Fault not found: {fault_id}",
                }

            old_fault = fault.data
            old_status = old_fault.get("status")

            # Validate status transition
            allowed = STATUS_TRANSITIONS.get(old_status, [])
            if "closed" not in allowed:
                return {
                    "status": "error",
                    "error_code": "INVALID_STATUS",
                    "message": f"Cannot close fault with status '{old_status}'.",
                }

            # Update fault
            now = datetime.now(timezone.utc).isoformat()
            update_data = {
                "status": "closed",
                "resolved_at": now,
                "resolved_by": user_id,
                "updated_at": now,
            }

            if resolution_notes:
                update_data["metadata"] = {
                    **(old_fault.get("metadata") or {}),
                    "resolution_notes": resolution_notes,
                }

            result = self.db.table("pms_faults").update(update_data).eq(
                "id", fault_id
            ).eq("yacht_id", yacht_id).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "UPDATE_FAILED",
                    "message": "Failed to close fault",
                }

            # Audit log (signature invariant: {} for non-signed)
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="close_fault",
                entity_type="fault",
                entity_id=fault_id,
                user_id=user_id,
                old_values={"status": old_status},
                new_values={"status": "closed", "resolution_notes": resolution_notes},
                signature=signature or {},
            )

            # Send notification
            await self._notify_fault_closed(
                yacht_id=yacht_id,
                fault_id=fault_id,
                fault_code=old_fault.get("fault_code"),
                closed_by=user_id,
            )

            return {
                "status": "success",
                "action": "close_fault",
                "result": {
                    "fault_id": fault_id,
                    "fault_code": old_fault.get("fault_code"),
                    "old_status": old_status,
                    "new_status": "closed",
                },
                "message": f"✓ {old_fault.get('fault_code')} closed",
            }

        except Exception as e:
            logger.error(f"close_fault failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # UPDATE FAULT
    # =========================================================================

    async def update_fault_execute(
        self,
        yacht_id: str,
        user_id: str,
        fault_id: str,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        signature: Optional[Dict] = None,
    ) -> Dict:
        """
        Update fault details (HOD/captain only).
        """
        try:
            # Get current fault
            fault = self.db.table("pms_faults").select(
                "*"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Fault not found: {fault_id}",
                }

            old_fault = fault.data

            # Build update data
            update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
            old_values = {}
            new_values = {}

            # Map and validate severity if provided
            if severity is not None:
                try:
                    mapped_severity = map_severity(severity)
                    old_values["severity"] = old_fault.get("severity")
                    new_values["severity"] = mapped_severity
                    update_data["severity"] = mapped_severity
                except ValueError as e:
                    return {
                        "status": "error",
                        "error_code": "INVALID_SEVERITY",
                        "message": str(e),
                    }

            # Validate status transition if provided
            if status is not None:
                if status not in VALID_STATUSES:
                    return {
                        "status": "error",
                        "error_code": "INVALID_STATUS",
                        "message": f"Invalid status '{status}'. Valid: {', '.join(VALID_STATUSES)}",
                    }

                old_status = old_fault.get("status")
                allowed = STATUS_TRANSITIONS.get(old_status, [])
                if status != old_status and status not in allowed:
                    return {
                        "status": "error",
                        "error_code": "INVALID_TRANSITION",
                        "message": f"Cannot transition from '{old_status}' to '{status}'.",
                    }

                old_values["status"] = old_status
                new_values["status"] = status
                update_data["status"] = status

            if title is not None:
                old_values["title"] = old_fault.get("title")
                new_values["title"] = title
                update_data["title"] = title

            if description is not None:
                old_values["description"] = old_fault.get("description")
                new_values["description"] = description
                update_data["description"] = description

            if len(new_values) == 0:
                return {
                    "status": "error",
                    "error_code": "NO_CHANGES",
                    "message": "No fields to update",
                }

            # Update fault
            result = self.db.table("pms_faults").update(update_data).eq(
                "id", fault_id
            ).eq("yacht_id", yacht_id).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "UPDATE_FAILED",
                    "message": "Failed to update fault",
                }

            # Audit log (signature invariant)
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="update_fault",
                entity_type="fault",
                entity_id=fault_id,
                user_id=user_id,
                old_values=old_values,
                new_values=new_values,
                signature=signature or {},
            )

            return {
                "status": "success",
                "action": "update_fault",
                "result": {
                    "fault_id": fault_id,
                    "fault_code": old_fault.get("fault_code"),
                    "updated_fields": list(new_values.keys()),
                },
                "message": f"✓ {old_fault.get('fault_code')} updated",
            }

        except Exception as e:
            logger.error(f"update_fault failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # REOPEN FAULT
    # =========================================================================

    async def reopen_fault_execute(
        self,
        yacht_id: str,
        user_id: str,
        fault_id: str,
        reason: str,
        signature: Optional[Dict] = None,
    ) -> Dict:
        """
        Reopen a closed/resolved fault (HOD/captain only).
        """
        try:
            if not reason:
                return {
                    "status": "error",
                    "error_code": "REASON_REQUIRED",
                    "message": "Reason is required for reopening a fault",
                }

            # Get current fault
            fault = self.db.table("pms_faults").select(
                "*"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Fault not found: {fault_id}",
                }

            old_fault = fault.data
            old_status = old_fault.get("status")

            # Validate status transition
            allowed = STATUS_TRANSITIONS.get(old_status, [])
            if "open" not in allowed:
                return {
                    "status": "error",
                    "error_code": "INVALID_STATUS",
                    "message": f"Cannot reopen fault with status '{old_status}'.",
                }

            # Update fault
            now = datetime.now(timezone.utc).isoformat()
            update_data = {
                "status": "open",
                "resolved_at": None,
                "resolved_by": None,
                "updated_at": now,
                "metadata": {
                    **(old_fault.get("metadata") or {}),
                    "reopen_reason": reason,
                    "reopened_at": now,
                    "reopened_by": user_id,
                },
            }

            result = self.db.table("pms_faults").update(update_data).eq(
                "id", fault_id
            ).eq("yacht_id", yacht_id).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "UPDATE_FAILED",
                    "message": "Failed to reopen fault",
                }

            # Audit log (signature invariant)
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="reopen_fault",
                entity_type="fault",
                entity_id=fault_id,
                user_id=user_id,
                old_values={"status": old_status},
                new_values={"status": "open", "reason": reason},
                signature=signature or {},
            )

            return {
                "status": "success",
                "action": "reopen_fault",
                "result": {
                    "fault_id": fault_id,
                    "fault_code": old_fault.get("fault_code"),
                    "old_status": old_status,
                    "new_status": "open",
                },
                "message": f"✓ {old_fault.get('fault_code')} reopened",
            }

        except Exception as e:
            logger.error(f"reopen_fault failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # MARK FALSE ALARM
    # =========================================================================

    async def mark_fault_false_alarm_execute(
        self,
        yacht_id: str,
        user_id: str,
        fault_id: str,
        reason: Optional[str] = None,
        signature: Optional[Dict] = None,
    ) -> Dict:
        """
        Mark fault as false alarm (HOD/captain only).

        Terminal state - cannot be reopened.
        """
        try:
            # Get current fault
            fault = self.db.table("pms_faults").select(
                "*"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Fault not found: {fault_id}",
                }

            old_fault = fault.data
            old_status = old_fault.get("status")

            # Can only mark as false alarm from open/investigating
            if old_status not in ("open", "investigating"):
                return {
                    "status": "error",
                    "error_code": "INVALID_STATUS",
                    "message": f"Cannot mark fault as false alarm with status '{old_status}'.",
                }

            # Update fault
            now = datetime.now(timezone.utc).isoformat()
            update_data = {
                "status": "false_alarm",
                "resolved_at": now,
                "resolved_by": user_id,
                "updated_at": now,
                "metadata": {
                    **(old_fault.get("metadata") or {}),
                    "false_alarm_reason": reason,
                    "marked_false_alarm_at": now,
                    "marked_false_alarm_by": user_id,
                },
            }

            result = self.db.table("pms_faults").update(update_data).eq(
                "id", fault_id
            ).eq("yacht_id", yacht_id).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "UPDATE_FAILED",
                    "message": "Failed to mark fault as false alarm",
                }

            # Audit log (signature invariant)
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="mark_fault_false_alarm",
                entity_type="fault",
                entity_id=fault_id,
                user_id=user_id,
                old_values={"status": old_status},
                new_values={"status": "false_alarm", "reason": reason},
                signature=signature or {},
            )

            return {
                "status": "success",
                "action": "mark_fault_false_alarm",
                "result": {
                    "fault_id": fault_id,
                    "fault_code": old_fault.get("fault_code"),
                    "old_status": old_status,
                    "new_status": "false_alarm",
                },
                "message": f"✓ {old_fault.get('fault_code')} marked as false alarm",
            }

        except Exception as e:
            logger.error(f"mark_fault_false_alarm failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # ADD FAULT PHOTO
    # =========================================================================

    async def add_fault_photo_execute(
        self,
        yacht_id: str,
        user_id: str,
        fault_id: str,
        photo_url: str,
        caption: Optional[str] = None,
        signature: Optional[Dict] = None,
    ) -> Dict:
        """
        Add photo to fault (crew/HOD/captain).
        """
        try:
            # Verify fault exists
            fault = self.db.table("pms_faults").select(
                "id, fault_code"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Fault not found: {fault_id}",
                }

            # CRITICAL FIX: Use pms_attachments table (NOT pms_fault_attachments which doesn't exist)
            # pms_attachments is the polymorphic table for all entity attachments
            now = datetime.now(timezone.utc).isoformat()
            attachment_data = {
                "yacht_id": yacht_id,
                "entity_type": "fault",
                "entity_id": fault_id,
                "storage_path": photo_url,
                "filename": photo_url.split("/")[-1] if "/" in photo_url else photo_url,
                "original_filename": photo_url.split("/")[-1] if "/" in photo_url else photo_url,
                "mime_type": "image/jpeg",  # Assume JPEG, can be enhanced
                "category": "photo",  # Default category for fault photos
                "description": caption,  # Map caption to description field
                "uploaded_by": user_id,
                "uploaded_at": now,
                "metadata": {
                    "fault_code": fault.data.get("fault_code"),
                    "action": "add_fault_photo"
                }
            }

            result = self.db.table("pms_attachments").insert(attachment_data).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to add photo",
                }

            attachment = result.data[0]

            # Audit log (signature invariant)
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_fault_photo",
                entity_type="fault",
                entity_id=fault_id,
                user_id=user_id,
                new_values={"attachment_id": attachment["id"], "photo_url": photo_url},
                signature=signature or {},
            )

            return {
                "status": "success",
                "action": "add_fault_photo",
                "result": {
                    "fault_id": fault_id,
                    "fault_code": fault.data.get("fault_code"),
                    "attachment_id": attachment["id"],
                    "photo_url": photo_url,
                },
                "message": "✓ Photo added",
            }

        except Exception as e:
            logger.error(f"add_fault_photo failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # ADD FAULT NOTE
    # =========================================================================

    async def add_fault_note_execute(
        self,
        yacht_id: str,
        user_id: str,
        fault_id: str,
        text: str,
        signature: Optional[Dict] = None,
    ) -> Dict:
        """
        Add note to fault (crew/HOD/captain).
        """
        try:
            if not text or len(text.strip()) == 0:
                return {
                    "status": "error",
                    "error_code": "TEXT_REQUIRED",
                    "message": "Note text is required",
                }

            # Verify fault exists
            fault = self.db.table("pms_faults").select(
                "id, fault_code"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Fault not found: {fault_id}",
                }

            # Create note record
            now = datetime.now(timezone.utc).isoformat()
            note_data = {
                "yacht_id": yacht_id,
                "entity_type": "fault",
                "entity_id": fault_id,
                "text": text,
                "author_id": user_id,
                "created_at": now,
            }

            result = self.db.table("pms_fault_notes").insert(note_data).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to add note",
                }

            note = result.data[0]

            # Audit log (signature invariant)
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_fault_note",
                entity_type="fault",
                entity_id=fault_id,
                user_id=user_id,
                new_values={"note_id": note["id"], "text": text[:100]},  # Truncate for audit
                signature=signature or {},
            )

            return {
                "status": "success",
                "action": "add_fault_note",
                "result": {
                    "fault_id": fault_id,
                    "fault_code": fault.data.get("fault_code"),
                    "note_id": note["id"],
                },
                "message": "✓ Note added",
            }

        except Exception as e:
            logger.error(f"add_fault_note failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # DIAGNOSE FAULT
    # =========================================================================

    async def diagnose_fault_execute(
        self,
        yacht_id: str,
        user_id: str,
        fault_id: str,
        diagnosis: str,
        recommended_action: Optional[str] = None,
        signature: Optional[Dict] = None,
    ) -> Dict:
        """
        Add diagnosis to fault (HOD/captain).
        """
        try:
            if not diagnosis or len(diagnosis.strip()) == 0:
                return {
                    "status": "error",
                    "error_code": "DIAGNOSIS_REQUIRED",
                    "message": "Diagnosis text is required",
                }

            # Get current fault
            fault = self.db.table("pms_faults").select(
                "*"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Fault not found: {fault_id}",
                }

            old_fault = fault.data

            # Update fault with diagnosis
            now = datetime.now(timezone.utc).isoformat()
            update_data = {
                "status": "investigating" if old_fault.get("status") == "open" else old_fault.get("status"),
                "updated_at": now,
                "metadata": {
                    **(old_fault.get("metadata") or {}),
                    "diagnosis": diagnosis,
                    "recommended_action": recommended_action,
                    "diagnosed_at": now,
                    "diagnosed_by": user_id,
                },
            }

            result = self.db.table("pms_faults").update(update_data).eq(
                "id", fault_id
            ).eq("yacht_id", yacht_id).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "UPDATE_FAILED",
                    "message": "Failed to add diagnosis",
                }

            # Audit log (signature invariant)
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="diagnose_fault",
                entity_type="fault",
                entity_id=fault_id,
                user_id=user_id,
                new_values={
                    "diagnosis": diagnosis[:200],
                    "recommended_action": recommended_action,
                },
                signature=signature or {},
            )

            return {
                "status": "success",
                "action": "diagnose_fault",
                "result": {
                    "fault_id": fault_id,
                    "fault_code": old_fault.get("fault_code"),
                    "diagnosis": diagnosis,
                    "recommended_action": recommended_action,
                },
                "message": f"✓ Diagnosis added to {old_fault.get('fault_code')}",
            }

        except Exception as e:
            logger.error(f"diagnose_fault failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    # =========================================================================
    # CREATE WORK ORDER FROM FAULT (SIGNED - Two-Phase)
    # =========================================================================

    async def create_work_order_from_fault_prepare(
        self,
        yacht_id: str,
        user_id: str,
        fault_id: str,
        title: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> Dict:
        """
        PREPARE phase for create_work_order_from_fault.

        Creates staged mutation with preview data and TTL.
        Returns idempotency_token for commit phase.

        This is the first phase of the two-phase signed flow.
        """
        import hashlib
        try:
            # Validate fault exists and get details
            fault = self.db.table("pms_faults").select(
                "id, fault_code, title, description, severity, status, equipment_id, metadata"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault.data:
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": f"Fault not found: {fault_id}",
                }

            fault_data = fault.data

            # Check if fault already has a work order
            existing_wo = self.db.table("pms_work_orders").select(
                "id, wo_number"
            ).eq("fault_id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            warnings = []
            if existing_wo.data:
                warnings.append({
                    "type": "existing_wo",
                    "message": f"Fault already has work order {existing_wo.data.get('wo_number')}",
                    "existing_wo_id": existing_wo.data["id"],
                })

            # Build proposed payload
            wo_title = title or f"WO: {fault_data.get('title', fault_data.get('fault_code'))}"
            proposed = {
                "fault_id": fault_id,
                "fault_code": fault_data.get("fault_code"),
                "title": wo_title,
                "description": fault_data.get("description"),
                "priority": priority or self._map_severity_to_priority(fault_data.get("severity", "minor")),
                "equipment_id": fault_data.get("equipment_id"),
                "assigned_to": assigned_to,
            }

            # Create snapshot for validation
            snapshot = {
                "fault_id": fault_id,
                "fault_status": fault_data.get("status"),
                "fault_severity": fault_data.get("severity"),
            }
            preview_hash = hashlib.sha256(str(snapshot).encode()).hexdigest()

            # Create staged mutation with TTL (10 minutes)
            now = datetime.now(timezone.utc)
            expires_at = now + __import__('datetime').timedelta(minutes=10)

            staged_data = {
                "action_id": "create_work_order_from_fault",
                "user_id": user_id,
                "yacht_id": yacht_id,
                "entity_id": fault_id,
                "entity_type": "fault",
                "preview_hash": preview_hash,
                "payload_snapshot": snapshot,
                "proposed_payload": proposed,
                "unresolved_fields": [] if assigned_to else ["assigned_to"],
                "warnings": [w.get("message") for w in warnings],
                "requires_signature": True,
                "signature_role": "captain,manager",
                "expires_at": expires_at.isoformat(),
                "created_at": now.isoformat(),
            }

            staged_result = self.db.table("pms_staged_mutations").insert(staged_data).execute()

            if not staged_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create staged mutation",
                }

            staged = staged_result.data[0]

            return {
                "status": "success",
                "action": "create_work_order_from_fault",
                "phase": "prepare",
                "result": {
                    "idempotency_token": staged.get("idempotency_token"),
                    "preview": proposed,
                    "preview_hash": preview_hash,
                    "warnings": warnings,
                    "unresolved_fields": staged_data["unresolved_fields"],
                    "requires_signature": True,
                    "signature_roles": ["captain", "manager"],
                    "expires_at": expires_at.isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"create_wo_from_fault_prepare failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    async def create_work_order_from_fault_commit(
        self,
        yacht_id: str,
        user_id: str,
        idempotency_token: str,
        signature: Dict,
        override_duplicate: bool = False,
    ) -> Dict:
        """
        COMMIT phase for create_work_order_from_fault.

        Validates signature and creates work order + entity link.
        Requires canonical signature JSON with required fields.

        PR #3 signature requirements:
        - signed_at (required)
        - user_id (required)
        - role_at_signing (required: captain or manager)
        - signature_type (required: "pin_totp")
        - signature_hash (required)
        """
        try:
            # Validate signature structure
            sig_errors = self._validate_signature(signature)
            if sig_errors:
                return {
                    "status": "error",
                    "error_code": "INVALID_SIGNATURE",
                    "message": "Signature validation failed",
                    "details": sig_errors,
                }

            # Check signature role
            role_at_signing = signature.get("role_at_signing")
            if role_at_signing not in ("captain", "manager"):
                return {
                    "status": "error",
                    "error_code": "INVALID_SIGNATURE_ROLE",
                    "message": f"Signature requires captain or manager role, got '{role_at_signing}'",
                }

            # Get staged mutation
            staged = self.db.table("pms_staged_mutations").select(
                "*"
            ).eq("idempotency_token", idempotency_token).eq(
                "user_id", user_id
            ).eq("yacht_id", yacht_id).is_("consumed_at", "null").maybe_single().execute()

            if not staged.data:
                return {
                    "status": "error",
                    "error_code": "STAGED_NOT_FOUND",
                    "message": "Staged mutation not found or expired",
                }

            staged_data = staged.data

            # Check expiry
            expires_at = datetime.fromisoformat(staged_data["expires_at"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires_at:
                return {
                    "status": "error",
                    "error_code": "STAGED_EXPIRED",
                    "message": "Staged mutation has expired. Please prepare again.",
                }

            proposed = staged_data.get("proposed_payload", {})
            fault_id = proposed.get("fault_id")

            # Check for duplicate WO (unless override)
            if not override_duplicate:
                existing_wo = self.db.table("pms_work_orders").select(
                    "id, wo_number"
                ).eq("fault_id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if existing_wo.data:
                    return {
                        "status": "error",
                        "error_code": "DUPLICATE_WO",
                        "message": f"Fault already has work order {existing_wo.data.get('wo_number')}",
                        "existing_wo_id": existing_wo.data["id"],
                    }

            # Create work order
            now = datetime.now(timezone.utc).isoformat()
            wo_data = {
                "yacht_id": yacht_id,
                "fault_id": fault_id,
                "title": proposed.get("title"),
                "description": proposed.get("description"),
                "priority": proposed.get("priority", "medium"),
                "status": "open",
                "equipment_id": proposed.get("equipment_id"),
                "assigned_to": proposed.get("assigned_to"),
                "created_by": user_id,
                "created_at": now,
                "updated_at": now,
            }

            wo_result = self.db.table("pms_work_orders").insert(wo_data).execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create work order",
                }

            work_order = wo_result.data[0]

            # Create entity link (fault → work_order)
            link_data = {
                "yacht_id": yacht_id,
                "source_entity_type": "fault",
                "source_entity_id": fault_id,
                "target_entity_type": "work_order",
                "target_entity_id": work_order["id"],
                "link_type": "resolved_by",
                "created_by": user_id,
                "created_at": now,
            }

            self.db.table("pms_entity_links").insert(link_data).execute()

            # Update fault status to work_ordered
            self.db.table("pms_faults").update({
                "status": "work_ordered",
                "updated_at": now,
            }).eq("id", fault_id).eq("yacht_id", yacht_id).execute()

            # Create audit log with SIGNATURE (signature invariant enforced)
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="create_work_order_from_fault",
                entity_type="work_order",
                entity_id=work_order["id"],
                user_id=user_id,
                new_values={
                    "work_order_id": work_order["id"],
                    "fault_id": fault_id,
                    "title": proposed.get("title"),
                },
                signature=signature,  # SIGNED action - signature is NOT {}
                metadata={
                    "source": "lens",
                    "lens": "faults",
                    "staged_mutation_id": staged_data["id"],
                },
            )

            # Mark staged mutation as consumed
            self.db.table("pms_staged_mutations").update({
                "consumed_at": now,
            }).eq("id", staged_data["id"]).execute()

            # Notify HOD of new work order
            await self._notify_work_order_created(
                yacht_id=yacht_id,
                work_order_id=work_order["id"],
                wo_number=work_order.get("wo_number"),
                fault_code=proposed.get("fault_code"),
                created_by=user_id,
            )

            return {
                "status": "success",
                "action": "create_work_order_from_fault",
                "phase": "commit",
                "result": {
                    "work_order_id": work_order["id"],
                    "wo_number": work_order.get("wo_number"),
                    "fault_id": fault_id,
                    "fault_code": proposed.get("fault_code"),
                    "fault_status": "work_ordered",
                },
                "message": f"✓ Work order created from fault {proposed.get('fault_code')}",
            }

        except Exception as e:
            logger.error(f"create_wo_from_fault_commit failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            }

    async def create_work_order_from_fault_execute(
        self,
        yacht_id: str,
        user_id: str,
        fault_id: str,
        signature: Dict,
        title: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
        override_duplicate: bool = False,
    ) -> Dict:
        """
        Execute create_work_order_from_fault (combined prepare + commit).

        For direct execution without separate prepare phase.
        Signature is still required.
        """
        # Validate signature first
        sig_errors = self._validate_signature(signature)
        if sig_errors:
            return {
                "status": "error",
                "error_code": "INVALID_SIGNATURE",
                "message": "Signature validation failed",
                "details": sig_errors,
            }

        # Check signature role
        role_at_signing = signature.get("role_at_signing")
        if role_at_signing not in ("captain", "manager"):
            return {
                "status": "error",
                "error_code": "INVALID_SIGNATURE_ROLE",
                "message": f"Signature requires captain or manager role, got '{role_at_signing}'",
            }

        # Prepare phase
        prepare_result = await self.create_work_order_from_fault_prepare(
            yacht_id=yacht_id,
            user_id=user_id,
            fault_id=fault_id,
            title=title,
            priority=priority,
            assigned_to=assigned_to,
        )

        if prepare_result.get("status") != "success":
            return prepare_result

        # Commit phase
        idempotency_token = prepare_result["result"]["idempotency_token"]
        return await self.create_work_order_from_fault_commit(
            yacht_id=yacht_id,
            user_id=user_id,
            idempotency_token=idempotency_token,
            signature=signature,
            override_duplicate=override_duplicate,
        )

    def _validate_signature(self, signature: Dict) -> List[str]:
        """
        Validate canonical signature JSON structure.

        Required fields per PR #3:
        - signed_at
        - user_id
        - role_at_signing
        - signature_type (must be "pin_totp")
        - signature_hash
        """
        if not signature:
            return ["Signature is required"]

        errors = []
        required = ["signed_at", "user_id", "role_at_signing", "signature_type", "signature_hash"]

        for field in required:
            if field not in signature:
                errors.append(f"Missing required field: {field}")

        if signature.get("signature_type") and signature.get("signature_type") != "pin_totp":
            errors.append(f"Invalid signature_type: {signature.get('signature_type')}. Must be 'pin_totp'")

        return errors

    def _map_severity_to_priority(self, severity: str) -> str:
        """Map fault severity to work order priority."""
        mapping = {
            "cosmetic": "low",
            "minor": "medium",
            "major": "high",
            "critical": "critical",
            "safety": "critical",
        }
        return mapping.get(severity, "medium")

    async def _notify_work_order_created(
        self,
        yacht_id: str,
        work_order_id: str,
        wo_number: str,
        fault_code: str,
        created_by: str,
    ) -> None:
        """Notify HOD when work order is created from fault."""
        try:
            # Get HOD users for this yacht (engineering department)
            # This would query the user roles - simplified for now
            idempotency_key = f"wo:{work_order_id}:created:{datetime.now(timezone.utc).date()}"

            # For now, notify the fault reporter
            fault = self.db.table("pms_faults").select(
                "metadata"
            ).eq("fault_code", fault_code).eq("yacht_id", yacht_id).maybe_single().execute()

            if fault.data:
                reported_by = (fault.data.get("metadata") or {}).get("reported_by")
                if reported_by and reported_by != created_by:
                    self.db.rpc("upsert_notification", {
                        "p_yacht_id": yacht_id,
                        "p_user_id": reported_by,
                        "p_notification_type": "wo_created_from_fault",
                        "p_title": f"Work order {wo_number} created",
                        "p_body": f"A work order has been created for fault {fault_code}",
                        "p_priority": "normal",
                        "p_entity_type": "work_order",
                        "p_entity_id": work_order_id,
                        "p_cta_action_id": "view_work_order_detail",
                        "p_cta_payload": {"work_order_id": work_order_id},
                        "p_idempotency_key": idempotency_key,
                    }).execute()

        except Exception as e:
            logger.warning(f"Failed to send WO created notification: {e}")

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _create_audit_log(
        self,
        yacht_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        signature: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create audit log entry.

        SIGNATURE INVARIANT: signature is NEVER NULL
        - Non-signed actions: signature = {}
        - Signed actions: signature = {pin_hash, totp_verified, signed_at, ...}

        PR #3 metadata requirements:
        - source: 'lens'
        - lens: 'faults'
        - action, entity_type, entity_id
        - session_id (if available)
        - ip_address (if available)
        """
        try:
            # INVARIANT: signature is NEVER NULL
            if signature is None:
                signature = {}

            # Build enhanced metadata per PR #3
            audit_metadata = {
                "source": "lens",
                "lens": "faults",
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
            }

            # Merge with any provided metadata
            if metadata:
                audit_metadata.update(metadata)

            # Add session/IP if provided
            if session_id:
                audit_metadata["session_id"] = session_id
            if ip_address:
                audit_metadata["ip_address"] = ip_address

            audit_data = {
                "yacht_id": yacht_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "old_values": old_values,
                "new_values": new_values,
                "signature": signature,  # INVARIANT: never None
                "metadata": audit_metadata,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            result = self.db.table("pms_audit_log").insert(audit_data).execute()

            if result.data:
                return result.data[0]["id"]
            else:
                logger.warning("Audit log creation returned no data")
                return None

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}", exc_info=True)
            return None

    async def _add_to_handover(
        self,
        yacht_id: str,
        entity_type: str,
        entity_id: str,
        summary: str,
        priority: str,
        user_id: str,
    ) -> Optional[str]:
        """Add item to active handover (for critical/safety faults)."""
        try:
            # Get active handover for this yacht
            handover_result = self.db.table("handovers").select(
                "id"
            ).eq("yacht_id", yacht_id).eq("status", "active").maybe_single().execute()

            if not handover_result.data:
                logger.warning(f"No active handover found for yacht {yacht_id}")
                return None

            handover_id = handover_result.data["id"]

            # Create handover item
            handover_item_data = {
                "yacht_id": yacht_id,
                "handover_id": handover_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "summary": summary,
                "priority": priority,
                "status": "pending",
                "added_by": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            item_result = self.db.table("handover_items").insert(handover_item_data).execute()

            if item_result.data:
                return item_result.data[0]["id"]
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to add to handover: {e}", exc_info=True)
            return None

    async def _notify_fault_acknowledged(
        self,
        yacht_id: str,
        fault_id: str,
        fault_code: str,
        acknowledged_by: str,
    ) -> None:
        """Send notification when fault is acknowledged."""
        try:
            # Get fault reporter from metadata
            fault = self.db.table("pms_faults").select(
                "metadata"
            ).eq("id", fault_id).maybe_single().execute()

            if not fault.data:
                return

            reported_by = (fault.data.get("metadata") or {}).get("reported_by")
            if not reported_by:
                return

            # Create notification using upsert_notification function
            idempotency_key = f"fault:{fault_id}:acknowledged:{datetime.now(timezone.utc).date()}"

            self.db.rpc("upsert_notification", {
                "p_yacht_id": yacht_id,
                "p_user_id": reported_by,
                "p_notification_type": "fault_acknowledged",
                "p_title": f"Fault {fault_code} acknowledged",
                "p_body": "Your fault report has been acknowledged and is being investigated.",
                "p_priority": "normal",
                "p_entity_type": "fault",
                "p_entity_id": fault_id,
                "p_cta_action_id": "view_fault_detail",
                "p_cta_payload": {"fault_id": fault_id},
                "p_idempotency_key": idempotency_key,
            }).execute()

        except Exception as e:
            logger.warning(f"Failed to send acknowledgement notification: {e}")

    async def _notify_fault_closed(
        self,
        yacht_id: str,
        fault_id: str,
        fault_code: str,
        closed_by: str,
    ) -> None:
        """Send notification when fault is closed."""
        try:
            # Get fault reporter from metadata
            fault = self.db.table("pms_faults").select(
                "metadata"
            ).eq("id", fault_id).maybe_single().execute()

            if not fault.data:
                return

            reported_by = (fault.data.get("metadata") or {}).get("reported_by")
            if not reported_by:
                return

            # Create notification
            idempotency_key = f"fault:{fault_id}:closed:{datetime.now(timezone.utc).date()}"

            self.db.rpc("upsert_notification", {
                "p_yacht_id": yacht_id,
                "p_user_id": reported_by,
                "p_notification_type": "fault_closed",
                "p_title": f"Fault {fault_code} closed",
                "p_body": "Your fault report has been resolved and closed.",
                "p_priority": "normal",
                "p_entity_type": "fault",
                "p_entity_id": fault_id,
                "p_cta_action_id": "view_fault_detail",
                "p_cta_payload": {"fault_id": fault_id},
                "p_idempotency_key": idempotency_key,
            }).execute()

        except Exception as e:
            logger.warning(f"Failed to send closed notification: {e}")


# =============================================================================
# HANDLER REGISTRATION
# =============================================================================

def get_fault_mutation_handlers(supabase_client) -> Dict[str, callable]:
    """Get fault mutation handler functions for registration."""
    handlers = FaultMutationHandlers(supabase_client)

    return {
        # report_fault
        "report_fault_prefill": handlers.report_fault_prefill,
        "report_fault_preview": handlers.report_fault_preview,
        "report_fault": handlers.report_fault_execute,

        # acknowledge_fault
        "acknowledge_fault": handlers.acknowledge_fault_execute,

        # close_fault
        "close_fault": handlers.close_fault_execute,

        # update_fault
        "update_fault": handlers.update_fault_execute,

        # reopen_fault
        "reopen_fault": handlers.reopen_fault_execute,

        # mark_fault_false_alarm
        "mark_fault_false_alarm": handlers.mark_fault_false_alarm_execute,

        # add_fault_photo
        "add_fault_photo": handlers.add_fault_photo_execute,

        # add_fault_note
        "add_fault_note": handlers.add_fault_note_execute,

        # diagnose_fault
        "diagnose_fault": handlers.diagnose_fault_execute,

        # create_work_order_from_fault (SIGNED - two-phase)
        "create_work_order_from_fault_prepare": handlers.create_work_order_from_fault_prepare,
        "create_work_order_from_fault_commit": handlers.create_work_order_from_fault_commit,
        "create_work_order_from_fault": handlers.create_work_order_from_fault_execute,
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "FaultMutationHandlers",
    "get_fault_mutation_handlers",
    "map_severity",
    "infer_severity_from_text",
    "VALID_SEVERITIES",
    "SEVERITY_MAPPING",
    "STATUS_TRANSITIONS",
    "SYMPTOM_SEVERITY_KEYWORDS",
]
