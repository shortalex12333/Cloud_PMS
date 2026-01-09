"""
Schema Mapping: Table Name Resolution
======================================

Maps logical table names to physical table names following organizational structure.

NAMING CONVENTION: pms_ prefix for operational/transactional tables
- Separates PMS (Planned Maintenance System) data from other systems
- Matches organizational structure confirmed from actual Supabase database
- Makes table purpose clear

DATABASE AUDIT RESULTS (2026-01-09):
- ✓ pms_equipment EXISTS (full schema - USE THIS)
- ✓ pms_faults EXISTS
- ✓ pms_parts EXISTS (needs inventory columns - added in migration 03)
- ✓ pms_work_orders EXISTS (needs completion columns - added in migration 03)
- ✓ pms_work_order_parts EXISTS
- ❌ equipment EXISTS (legacy/simplified - DEPRECATED, use pms_equipment)
- ❌ pms_audit_log DOES NOT EXIST (created in migration 04)
- ❌ pms_part_usage DOES NOT EXIST (created in migration 04)
- ❌ pms_work_order_notes DOES NOT EXIST (created in migration 04)
- ❌ pms_handover DOES NOT EXIST (created in migration 04)
"""

from typing import Dict, Any

# Table name mapping with pms_ prefix for operational tables
# CONFIRMED from actual Supabase database (2026-01-09)
TABLE_MAP = {
    "equipment": "pms_equipment",           # CONFIRMED: Use pms_equipment (not legacy 'equipment')
    "faults": "pms_faults",                 # CONFIRMED: Exists
    "work_orders": "pms_work_orders",       # CONFIRMED: Exists
    "parts": "pms_parts",                   # CONFIRMED: Exists (columns added in migration 03)
    "work_order_notes": "pms_work_order_notes",  # CREATED in migration 04
    "work_order_parts": "pms_work_order_parts",  # CONFIRMED: Exists
    "part_usage": "pms_part_usage",         # CREATED in migration 04
    "audit_log": "pms_audit_log",           # CREATED in migration 04
    "handover": "pms_handover",             # CREATED in migration 04
}


def get_table(logical_name: str) -> str:
    """
    Resolve logical table name to physical table name.

    Args:
        logical_name: Logical name like 'work_orders', 'parts', 'equipment'

    Returns:
        Physical table name like 'pms_work_orders', 'pms_parts', 'pms_equipment'

    Example:
        >>> get_table("work_orders")
        'pms_work_orders'
        >>> get_table("parts")
        'pms_parts'
        >>> get_table("document_chunks")  # Not in map - returns as-is
        'document_chunks'
    """
    return TABLE_MAP.get(logical_name, logical_name)


# Placeholder functions for normalization (handlers expect these)
# TODO: Implement proper normalization once schema is finalized

def map_equipment_select() -> str:
    """Return SELECT clause for equipment queries."""
    return "*"


def normalize_equipment(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize equipment data from database format to API format."""
    return data


def map_work_order_select() -> str:
    """Return SELECT clause for work order queries."""
    return "*"


def normalize_work_order(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize work order data from database format to API format."""
    return data


def map_parts_select() -> str:
    """Return SELECT clause for parts queries."""
    return "*"


def normalize_part(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize part data from database format to API format."""
    return data


def map_faults_select() -> str:
    """Return SELECT clause for faults queries."""
    return "*"


def normalize_fault(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize fault data from database format to API format."""
    return data


__all__ = [
    "get_table",
    "map_equipment_select",
    "normalize_equipment",
    "map_work_order_select",
    "normalize_work_order",
    "map_parts_select",
    "normalize_part",
    "map_faults_select",
    "normalize_fault",
]
