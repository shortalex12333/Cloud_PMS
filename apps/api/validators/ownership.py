"""
CelesteOS API - Ownership Validation Library
============================================

Centralized ownership validation for all handlers.

Security invariants enforced:
1. Every foreign ID in payload must be ownership-validated
2. Validation uses: SELECT id FROM <table> WHERE id=:id AND yacht_id=:yacht_id
3. Not found returns 404 (not 403) to prevent enumeration
4. All queries are yacht-scoped even when RLS exists (defense in depth)

Usage:
    from validators.ownership import OwnershipValidator, ensure_owned

    # Class-based (recommended for multiple validations)
    validator = OwnershipValidator(supabase_client, yacht_id)
    equipment = validator.validate("equipment", equipment_id)
    parts = validator.validate_multiple("part", part_ids)

    # Function-based (single validation)
    equipment = ensure_owned(supabase_client, "pms_equipment", equipment_id, yacht_id)
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
import hashlib

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """
    Raised when entity is not found or not owned by yacht.

    Returns 404 (not 403) to prevent enumeration attacks.
    """

    def __init__(self, entity_type: str, entity_id: str, message: str = None):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.message = message or f"{entity_type} not found"
        super().__init__(self.message)


class OwnershipValidationError(Exception):
    """
    Raised when ownership validation fails due to system error.

    Returns 500 - validation could not be completed.
    """

    def __init__(self, entity_type: str, entity_id: str, reason: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.reason = reason
        super().__init__(f"Ownership validation failed for {entity_type}/{entity_id}: {reason}")


# Entity type to table mapping
# IMPORTANT: Update this when adding new entity types
ENTITY_TABLE_MAP = {
    # PMS Core
    "equipment": "pms_equipment",
    "fault": "pms_faults",
    "work_order": "pms_work_orders",
    "part": "pms_parts",
    "note": "pms_notes",
    "attachment": "pms_attachments",
    "checklist": "pms_checklists",
    "checklist_item": "pms_checklist_items",
    "worklist_task": "pms_worklist_tasks",
    "purchase_order": "pms_purchase_orders",
    "supplier": "pms_suppliers",

    # Documents
    "document": "documents",
    "doc_metadata": "doc_metadata",

    # Email
    "email_thread": "email_threads",
    "email_message": "email_messages",

    # Handover
    "handover": "handovers",
    "handover_item": "handover_items",

    # Inventory
    "inventory_item": "pms_inventory_items",
    "inventory_transaction": "pms_inventory_transactions",

    # Entity Links
    "entity_link": "pms_entity_links",

    # Warranty
    "warranty_claim": "pms_warranty_claims",
}

# Safe fields to return (no sensitive data)
SAFE_RETURN_FIELDS = {
    "pms_equipment": "id, equipment_id, label, category, yacht_id",
    "pms_faults": "id, fault_id, equipment_id, status, yacht_id",
    "pms_work_orders": "id, wo_id, status, yacht_id",
    "pms_parts": "id, part_number, description, yacht_id",
    "documents": "id, filename, yacht_id",
    "doc_metadata": "id, filename, yacht_id",
    "pms_notes": "id, entity_type, entity_id, yacht_id",
    "pms_attachments": "id, filename, entity_type, entity_id, yacht_id",
    "pms_checklists": "id, name, yacht_id",
    "pms_checklist_items": "id, checklist_id, yacht_id",
    "pms_worklist_tasks": "id, yacht_id",
    "email_threads": "id, subject, yacht_id",
    "email_messages": "id, thread_id, yacht_id",
    "handovers": "id, yacht_id",
    "handover_items": "id, handover_id, yacht_id",
    "pms_purchase_orders": "id, po_number, yacht_id",
    "pms_suppliers": "id, name, yacht_id",
    "pms_inventory_items": "id, yacht_id",
    "pms_inventory_transactions": "id, yacht_id",
    "pms_entity_links": "id, yacht_id",
    "pms_warranty_claims": "id, yacht_id",
}


class OwnershipValidator:
    """
    Centralized ownership validation for yacht-scoped entities.

    All validation queries include WHERE yacht_id = :yacht_id
    to enforce tenant isolation even when RLS exists.
    """

    def __init__(self, db_client: Any, yacht_id: str):
        """
        Initialize validator with database client and yacht context.

        Args:
            db_client: Supabase client for the tenant database
            yacht_id: UUID of the yacht (from ctx.yacht_id)
        """
        if not db_client:
            raise ValueError("db_client is required")
        if not yacht_id:
            raise ValueError("yacht_id is required")

        self.db = db_client
        self.yacht_id = yacht_id

    def _get_table_name(self, entity_type: str) -> str:
        """Resolve entity type to table name."""
        if entity_type in ENTITY_TABLE_MAP:
            return ENTITY_TABLE_MAP[entity_type]
        # Allow direct table names for flexibility
        if entity_type.startswith("pms_") or entity_type in ["documents", "doc_metadata"]:
            return entity_type
        raise ValueError(f"Unknown entity type: {entity_type}")

    def _get_select_fields(self, table_name: str) -> str:
        """Get safe fields to select for a table."""
        return SAFE_RETURN_FIELDS.get(table_name, "id, yacht_id")

    def validate(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """
        Validate that entity exists and belongs to yacht.

        Args:
            entity_type: Type of entity (e.g., "equipment", "fault")
            entity_id: UUID of the entity

        Returns:
            Dict with safe entity fields

        Raises:
            NotFoundError: Entity not found or not owned (404)
            OwnershipValidationError: Validation failed (500)
        """
        if not entity_id:
            raise NotFoundError(entity_type, "", "Entity ID is required")

        table_name = self._get_table_name(entity_type)
        select_fields = self._get_select_fields(table_name)

        try:
            result = (
                self.db.table(table_name)
                .select(select_fields)
                .eq("id", entity_id)
                .eq("yacht_id", self.yacht_id)
                .execute()
            )

            if not result.data or len(result.data) == 0:
                # Log for security monitoring (no sensitive data)
                logger.warning(
                    f"[OwnershipValidator] Entity not found: "
                    f"type={entity_type}, id={entity_id[:8]}..., yacht={self.yacht_id[:8]}..."
                )
                raise NotFoundError(entity_type, entity_id)

            logger.debug(
                f"[OwnershipValidator] Validated: "
                f"type={entity_type}, id={entity_id[:8]}..."
            )
            return result.data[0]

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"[OwnershipValidator] Validation error: "
                f"type={entity_type}, id={entity_id[:8]}..., error={e}"
            )
            raise OwnershipValidationError(entity_type, entity_id, str(e))

    def validate_multiple(
        self, entity_type: str, entity_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple entities of the same type.

        All entities must be owned by the yacht - partial success is not allowed.

        Args:
            entity_type: Type of entities
            entity_ids: List of entity UUIDs

        Returns:
            List of dicts with safe entity fields

        Raises:
            NotFoundError: Any entity not found or not owned (404)
            OwnershipValidationError: Validation failed (500)
        """
        if not entity_ids:
            return []

        # Deduplicate
        unique_ids = list(set(entity_ids))

        table_name = self._get_table_name(entity_type)
        select_fields = self._get_select_fields(table_name)

        try:
            result = (
                self.db.table(table_name)
                .select(select_fields)
                .in_("id", unique_ids)
                .eq("yacht_id", self.yacht_id)
                .execute()
            )

            found_ids = {row["id"] for row in (result.data or [])}
            missing_ids = set(unique_ids) - found_ids

            if missing_ids:
                # Log first missing ID for security monitoring
                first_missing = list(missing_ids)[0]
                logger.warning(
                    f"[OwnershipValidator] Batch validation failed: "
                    f"type={entity_type}, missing={len(missing_ids)}, "
                    f"first_missing={first_missing[:8]}..."
                )
                raise NotFoundError(entity_type, first_missing, f"{len(missing_ids)} entities not found")

            return result.data

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"[OwnershipValidator] Batch validation error: "
                f"type={entity_type}, count={len(unique_ids)}, error={e}"
            )
            raise OwnershipValidationError(entity_type, unique_ids[0], str(e))

    def validate_pairs(
        self, entity_pairs: List[Tuple[str, str]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Validate multiple entities of different types.

        Args:
            entity_pairs: List of (entity_type, entity_id) tuples

        Returns:
            Dict mapping "type:id" to entity data

        Raises:
            NotFoundError: Any entity not found (404)
        """
        results = {}
        for entity_type, entity_id in entity_pairs:
            key = f"{entity_type}:{entity_id}"
            results[key] = self.validate(entity_type, entity_id)
        return results


# ============================================================================
# Convenience Functions (for single validations)
# ============================================================================


def ensure_owned(
    db_client: Any,
    table_name: str,
    record_id: str,
    yacht_id: str,
    select_fields: str = "id, yacht_id",
) -> Dict[str, Any]:
    """
    Ensure a record exists and is owned by the yacht.

    Direct function for simple cases. For multiple validations,
    use OwnershipValidator class instead.

    Args:
        db_client: Supabase client
        table_name: Database table name
        record_id: UUID of the record
        yacht_id: UUID of the yacht
        select_fields: Fields to return (default: id, yacht_id)

    Returns:
        Dict with requested fields

    Raises:
        NotFoundError: Record not found or not owned (404)
    """
    if not record_id:
        raise NotFoundError(table_name, "", "Record ID is required")
    if not yacht_id:
        raise NotFoundError(table_name, record_id, "Yacht ID is required")

    try:
        result = (
            db_client.table(table_name)
            .select(select_fields)
            .eq("id", record_id)
            .eq("yacht_id", yacht_id)
            .execute()
        )

        if not result.data or len(result.data) == 0:
            raise NotFoundError(table_name, record_id)

        return result.data[0]

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"[ensure_owned] Error: table={table_name}, id={record_id[:8]}..., error={e}")
        raise OwnershipValidationError(table_name, record_id, str(e))


def ensure_all_owned(
    db_client: Any,
    table_name: str,
    record_ids: List[str],
    yacht_id: str,
    select_fields: str = "id, yacht_id",
) -> List[Dict[str, Any]]:
    """
    Ensure all records exist and are owned by the yacht.

    Args:
        db_client: Supabase client
        table_name: Database table name
        record_ids: List of record UUIDs
        yacht_id: UUID of the yacht
        select_fields: Fields to return

    Returns:
        List of dicts with requested fields

    Raises:
        NotFoundError: Any record not found or not owned (404)
    """
    if not record_ids:
        return []
    if not yacht_id:
        raise NotFoundError(table_name, record_ids[0], "Yacht ID is required")

    unique_ids = list(set(record_ids))

    try:
        result = (
            db_client.table(table_name)
            .select(select_fields)
            .in_("id", unique_ids)
            .eq("yacht_id", yacht_id)
            .execute()
        )

        found_ids = {row["id"] for row in (result.data or [])}
        missing_ids = set(unique_ids) - found_ids

        if missing_ids:
            first_missing = list(missing_ids)[0]
            raise NotFoundError(table_name, first_missing, f"{len(missing_ids)} records not found")

        return result.data

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"[ensure_all_owned] Error: table={table_name}, count={len(unique_ids)}, error={e}")
        raise OwnershipValidationError(table_name, unique_ids[0], str(e))


def hash_for_audit(data: Any) -> str:
    """
    Create SHA256 hash of data for audit logging.

    Used to log payload fingerprints without exposing sensitive data.
    """
    import json
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]
