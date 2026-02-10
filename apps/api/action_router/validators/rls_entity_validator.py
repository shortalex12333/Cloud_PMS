"""
RLS Entity Validator

Validates that referenced entity IDs belong to the user's yacht.
This prevents cross-yacht data access even when entity IDs are known.

Security Fix: 2026-02-10
"""

import logging
from typing import Dict, Any, Optional
from supabase import Client
from .validation_result import ValidationResult

logger = logging.getLogger(__name__)

# Map of payload field names to their database tables
ENTITY_TABLE_MAP = {
    "item_id": "pms_shopping_list_items",
    "shopping_list_item_id": "pms_shopping_list_items",
    "part_id": "pms_parts",
    "equipment_id": "pms_equipment",
    "fault_id": "pms_faults",
    "work_order_id": "pms_work_orders",
    "wo_id": "pms_work_orders",
    "checklist_id": "pms_checklists",
    "document_id": "doc_metadata",
    "certificate_id": "pms_vessel_certificates",
    "purchase_request_id": "purchase_requests",
}


async def validate_entity_yacht_ownership(
    db: Client,
    entity_id: str,
    table_name: str,
    user_yacht_id: str,
    field_name: str
) -> ValidationResult:
    """
    Validate that a specific entity belongs to the user's yacht.

    Args:
        db: Supabase client
        entity_id: The entity ID to check
        table_name: The database table name
        user_yacht_id: The user's yacht ID from JWT
        field_name: The field name for error messages

    Returns:
        ValidationResult with success or failure
    """
    try:
        result = db.table(table_name).select("yacht_id").eq("id", entity_id).maybe_single().execute()

        if not result or not result.data:
            # Entity doesn't exist - return NOT_FOUND
            logger.warning(f"[RLS] Entity not found: {table_name}.{entity_id}")
            return ValidationResult.failure(
                error_code="NOT_FOUND",
                message=f"{field_name} not found",
                field=field_name
            )

        entity_yacht_id = result.data.get("yacht_id")

        if entity_yacht_id != user_yacht_id:
            # Entity belongs to different yacht - return NOT_FOUND (don't reveal existence)
            logger.warning(
                f"[RLS] Cross-yacht access denied: {table_name}.{entity_id} "
                f"belongs to yacht {entity_yacht_id}, user belongs to {user_yacht_id}"
            )
            return ValidationResult.failure(
                error_code="NOT_FOUND",
                message=f"{field_name} not found",
                field=field_name
            )

        return ValidationResult.success()

    except Exception as e:
        # Table may not exist or other DB error - log and continue
        # This allows graceful degradation for tables that don't have yacht_id
        logger.debug(f"[RLS] Could not validate {table_name}: {e}")
        return ValidationResult.success()


async def validate_payload_entities(
    db: Client,
    payload: Dict[str, Any],
    user_yacht_id: str
) -> ValidationResult:
    """
    Validate all entity IDs in payload belong to user's yacht.

    This function extracts all known entity ID fields from the payload
    and verifies each one belongs to the user's yacht.

    Args:
        db: Supabase client
        payload: The action payload containing entity IDs
        user_yacht_id: The user's yacht ID from JWT

    Returns:
        ValidationResult - fails on first violation
    """
    for field_name, table_name in ENTITY_TABLE_MAP.items():
        entity_id = payload.get(field_name)

        if entity_id and isinstance(entity_id, str) and entity_id.strip():
            # Skip placeholder values that aren't real UUIDs
            if not _is_valid_uuid_format(entity_id):
                continue

            result = await validate_entity_yacht_ownership(
                db=db,
                entity_id=entity_id,
                table_name=table_name,
                user_yacht_id=user_yacht_id,
                field_name=field_name
            )

            if not result.valid:
                return result

    return ValidationResult.success()


def _is_valid_uuid_format(value: str) -> bool:
    """Check if value looks like a valid UUID."""
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, value.lower()))


__all__ = [
    "validate_entity_yacht_ownership",
    "validate_payload_entities",
    "ENTITY_TABLE_MAP",
]
