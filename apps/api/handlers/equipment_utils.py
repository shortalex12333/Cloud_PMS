"""
Equipment Lens v2 - Utility Functions
======================================

Shared utilities for equipment handlers:
- Storage path validation
- Audit metadata extraction
- Status validation helpers
"""

from typing import Dict, Optional
from datetime import datetime, timezone
import re


# =============================================================================
# STORAGE PATH VALIDATION
# =============================================================================

def validate_storage_path_for_equipment(
    yacht_id: str,
    equipment_id: str,
    storage_path: str
) -> tuple[bool, Optional[str]]:
    """
    Validate storage path for equipment documents.

    Expected format: {yacht_id}/equipment/{equipment_id}/{filename}
    MUST NOT have "documents/" prefix.

    Args:
        yacht_id: Yacht UUID
        equipment_id: Equipment UUID
        storage_path: Full storage path to validate

    Returns:
        (is_valid, error_message)

    Examples:
        Valid: "85fe1119-b04c-41ac-80f1-829d23322598/equipment/abc123/manual.pdf"
        Invalid: "documents/85fe1119.../equipment/abc123/manual.pdf"
        Invalid: "other-yacht-id/equipment/abc123/manual.pdf"
    """
    # Check for invalid "documents/" prefix
    if storage_path.startswith("documents/"):
        return False, "Storage path must not include 'documents/' prefix"

    # Expected pattern: {yacht_id}/equipment/{equipment_id}/{filename}
    pattern = rf"^{re.escape(yacht_id)}/equipment/{re.escape(equipment_id)}/[^/]+$"

    if not re.match(pattern, storage_path):
        return False, f"Storage path must match pattern: {{yacht_id}}/equipment/{{equipment_id}}/{{filename}}"

    return True, None


# =============================================================================
# AUDIT METADATA EXTRACTION
# =============================================================================

def extract_audit_metadata(request_context: Optional[Dict] = None) -> Dict:
    """
    Extract required audit metadata from request context.

    Required keys:
    - source: always 'lens'
    - lens: always 'equipment'
    - session_id: from X-Session-Id header or "unknown"
    - ip_address: from X-Forwarded-For or remote_addr

    Args:
        request_context: Dict with headers, remote_addr, etc.

    Returns:
        Dict with audit metadata keys
    """
    context = request_context or {}
    headers = context.get("headers", {})

    # Extract session_id from header
    session_id = headers.get("x-session-id") or headers.get("X-Session-Id") or "unknown"

    # Extract IP address from X-Forwarded-For (first IP) or remote_addr
    forwarded_for = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take first IP if comma-separated
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = context.get("remote_addr") or context.get("remote_address") or "unknown"

    return {
        "source": "lens",
        "lens": "equipment",
        "session_id": session_id,
        "ip_address": ip_address,
    }


# =============================================================================
# STATUS VALIDATION
# =============================================================================

VALID_EQUIPMENT_STATUSES = [
    'operational',
    'degraded',
    'failed',
    'maintenance',
    'out_of_service',  # Requires WO
    'decommissioned',  # Terminal
]

TERMINAL_STATUSES = ['decommissioned']

OOS_STATUS = 'out_of_service'


def is_terminal_status(status: str) -> bool:
    """Check if status is terminal (cannot be changed)."""
    return status in TERMINAL_STATUSES


def requires_work_order(status: str) -> bool:
    """Check if status requires linked work order."""
    return status == OOS_STATUS


def validate_status_transition(
    from_status: str,
    to_status: str,
    linked_work_order_id: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate equipment status transition.

    Rules:
    - Cannot change from terminal status
    - out_of_service requires linked_work_order_id
    - Status must be valid

    Returns:
        (is_valid, error_message)
    """
    # Check valid status
    if to_status not in VALID_EQUIPMENT_STATUSES:
        return False, f"Invalid status: must be one of {VALID_EQUIPMENT_STATUSES}"

    # Check terminal status
    if is_terminal_status(from_status):
        return False, f"Cannot change status from terminal state '{from_status}'"

    # Check OOS requires WO
    if requires_work_order(to_status) and not linked_work_order_id:
        return False, f"Status '{OOS_STATUS}' requires linked_work_order_id"

    return True, None


# =============================================================================
# WORK ORDER VALIDATION
# =============================================================================

OPEN_WO_STATUSES = ['open', 'in_progress']


def validate_work_order_for_oos(
    db,
    work_order_id: str,
    equipment_id: str,
    yacht_id: str
) -> tuple[bool, Optional[str]]:
    """
    Validate work order can be used for out_of_service status.

    Requirements:
    - WO must exist
    - WO must be for same equipment and yacht
    - WO status must be in OPEN_WO_STATUSES

    Returns:
        (is_valid, error_message)
    """
    try:
        result = db.table("pms_work_orders").select(
            "id, equipment_id, yacht_id, status"
        ).eq("id", work_order_id).maybe_single().execute()

        if not result.data:
            return False, f"Work order {work_order_id} not found"

        wo = result.data

        # Check equipment match
        if wo.get("equipment_id") != equipment_id:
            return False, "Work order must be for this equipment"

        # Check yacht match
        if wo.get("yacht_id") != yacht_id:
            return False, "Work order must be for same yacht"

        # Check status is open
        if wo.get("status") not in OPEN_WO_STATUSES:
            return False, f"Work order must have status in {OPEN_WO_STATUSES}, got '{wo.get('status')}'"

        return True, None

    except Exception as e:
        return False, f"Error validating work order: {e}"


# =============================================================================
# PREPARE/EXECUTE HELPERS
# =============================================================================

def is_prepare_mode(params: Dict) -> bool:
    """Check if request is in prepare mode."""
    mode = params.get("context", {}).get("mode") or params.get("mode")
    confirm = params.get("confirm")

    # Prefer explicit mode
    if mode:
        return mode == "prepare"

    # Fallback: confirm=false means prepare, confirm=true means execute
    if confirm is not None:
        return not confirm

    # Default: prepare (safe default)
    return True


def is_execute_mode(params: Dict) -> bool:
    """Check if request is in execute mode."""
    return not is_prepare_mode(params)


def generate_confirmation_token(action: str, entity_id: str) -> str:
    """Generate idempotency token for prepare/execute flow."""
    import hashlib
    timestamp = datetime.now(timezone.utc).isoformat()
    data = f"{action}:{entity_id}:{timestamp}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]
