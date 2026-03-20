"""
Universal Handlers — shared cross-entity operations.

soft_delete_entity: One handler for all delete/archive/suspend/revoke/void/cancel
operations across every entity type. Sets deleted_at + deleted_by, enforces
yacht isolation.
"""

from datetime import datetime, timezone
from typing import Dict, Any
import logging

from integrations.supabase import get_supabase_client

logger = logging.getLogger(__name__)

# Maps entity_type → (table_name, id_column)
ENTITY_TABLE_MAP: Dict[str, tuple] = {
    "work_order":      ("pms_work_orders",        "id"),
    "equipment":       ("pms_equipment",           "id"),
    "fault":           ("pms_faults",              "id"),
    "part":            ("pms_parts",               "id"),
    "document":        ("doc_metadata",            "id"),
    "certificate":     ("pms_vessel_certificates", "id"),
    "purchase_order":  ("pms_purchase_orders",     "id"),
    "warranty":        ("pms_warranty_claims",      "id"),
    "receiving":       ("pms_receiving",            "id"),
    "shopping_list":   ("pms_shopping_list_items",  "id"),
    "handover_export": ("handover_exports",         "id"),
    "hours_of_rest":   ("pms_hours_of_rest",        "id"),
}


async def soft_delete_entity(params: dict) -> dict:
    """
    Universal soft-delete: sets deleted_at + deleted_by on any entity.

    Required params:
        - yacht_id: UUID
        - entity_id: UUID
        - entity_type: str (key in ENTITY_TABLE_MAP)
        - user_id: UUID (from JWT)

    Optional params:
        - reason: str
    """
    entity_type = params.get("entity_type")
    entity_id = params.get("entity_id")
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    reason = params.get("reason", "")

    if entity_type not in ENTITY_TABLE_MAP:
        raise ValueError(f"Unknown entity_type: {entity_type}")
    if not entity_id:
        raise ValueError("entity_id is required")

    table, id_col = ENTITY_TABLE_MAP[entity_type]
    supabase = get_supabase_client()

    # 1. Verify entity exists + yacht isolation
    check = supabase.table(table).select(id_col).eq(
        id_col, entity_id
    ).eq("yacht_id", yacht_id).execute()

    if not check.data:
        raise ValueError(f"{entity_type} {entity_id} not found or access denied")

    # 2. SET deleted_at + deleted_by
    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        "deleted_at": now,
        "deleted_by": user_id,
    }

    result = supabase.table(table).update(update_data).eq(
        id_col, entity_id
    ).eq("yacht_id", yacht_id).execute()

    if not result.data:
        raise Exception(f"Failed to soft-delete {entity_type} {entity_id}")

    # 3. Audit log
    try:
        import uuid as uuid_lib
        supabase.table("pms_audit_log").insert({
            "id": str(uuid_lib.uuid4()),
            "yacht_id": yacht_id,
            "action": f"soft_delete_{entity_type}",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "old_values": {"deleted_at": None},
            "new_values": {"deleted_at": now, "reason": reason},
            "signature": {},
            "created_at": now,
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for soft_delete {entity_type}/{entity_id}: {e}")

    return {
        "status": "success",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "deleted_at": now,
        "deleted_by": user_id,
    }
