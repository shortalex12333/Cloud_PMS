"""
Status Mapper
=============
Maps source PMS status values to CelesteOS canonical status values.
Each domain has its own valid statuses.
"""

from typing import Optional

# =============================================================================
# REAL PRODUCTION ENUM VALUES (verified against tenant DB 2026-04-01)
# =============================================================================
# work_order_status ENUM:  planned, in_progress, completed, deferred, cancelled, closed
# work_order_priority ENUM: routine, important, critical, emergency
# work_order_type ENUM:    scheduled, corrective, unplanned, preventive
# fault_severity ENUM:     low, medium, high, critical
# equipment.status:        plain text (no enum) — flexible
# faults.status:           plain text (no enum) — flexible
# certificates.status:     plain text (no enum) — flexible
# =============================================================================

CANONICAL_STATUSES = {
    "equipment": {"operational", "degraded", "failed", "maintenance", "decommissioned"},
    "work_orders": {"planned", "in_progress", "completed", "deferred", "cancelled", "closed"},
    "work_orders_priority": {"routine", "important", "critical", "emergency"},
    "work_orders_type": {"scheduled", "corrective", "unplanned", "preventive"},
    "faults_severity": {"low", "medium", "high", "critical"},
    "faults": set(),  # plain text, flexible
    "parts": set(),
    "certificates": {"valid", "expired", "suspended", "pending_renewal"},
}

# Mapping tables: {source: {domain.field: {source_value: celeste_value}}}
STATUS_MAP = {
    "idea_yacht": {
        "equipment": {
            "ACTIVE": "operational",
            "INACTIVE": "decommissioned",
            "MAINTENANCE": "maintenance",
            "FAILED": "failed",
            "DEGRADED": "degraded",
        },
        "work_orders": {
            # IDEA statuses → work_order_status ENUM
            "COMPLETED": "completed",
            "OPEN": "planned",        # IDEA "OPEN" → "planned" (not "open" — enum doesn't have "open")
            "IN_PROGRESS": "in_progress",
            "PENDING": "planned",
            "CANCELLED": "cancelled",
            "CLOSED": "closed",
            "DEFERRED": "deferred",
        },
        "work_orders_priority": {
            # IDEA priorities → work_order_priority ENUM
            "HIGH": "important",      # no "high" in enum — map to "important"
            "NORMAL": "routine",      # no "normal" — map to "routine"
            "CRITICAL": "critical",
            "LOW": "routine",
            "URGENT": "emergency",
            "EMERGENCY": "emergency",
        },
        "work_orders_type": {
            # IDEA WO types → work_order_type ENUM
            "PM": "scheduled",
            "CM": "corrective",
            "INSP": "preventive",
            "EMERGENCY": "unplanned",
        },
        "faults": {},  # plain text — pass through
        "faults_severity": {
            "CRITICAL": "critical",
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
        },
        "certificates": {
            "VALID": "valid",
            "EXPIRED": "expired",
            "SUSPENDED": "suspended",
        },
    },
    "seahub": {
        "equipment": {
            "active": "operational",
            "inactive": "decommissioned",
            "maintenance": "maintenance",
        },
        "work_orders": {
            "open": "planned",
            "completed": "completed",
            "in_progress": "in_progress",
            "overdue": "planned",
        },
        "work_orders_priority": {
            "high": "important",
            "normal": "routine",
            "critical": "critical",
            "low": "routine",
        },
        "work_orders_type": {
            "planned": "scheduled",
            "corrective": "corrective",
            "inspection": "preventive",
        },
        "faults": {},
        "faults_severity": {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
        },
        "certificates": {
            "valid": "valid",
            "expired": "expired",
        },
    },
    "sealogical": {
        "equipment": {
            "Active": "operational",
            "Inactive": "decommissioned",
            "Under Maintenance": "maintenance",
        },
        "work_orders": {
            "Open": "planned",
            "Completed": "completed",
            "In Progress": "in_progress",
        },
        "certificates": {
            "Valid": "valid",
            "Expired": "expired",
        },
    },
}


def map_status(value: str, domain: str, source: str = "generic") -> str:
    """
    Map a source status value to CelesteOS canonical status.
    Returns the mapped value, or the original value lowercased if no mapping found.
    """
    if not value:
        return value

    source_map = STATUS_MAP.get(source, {}).get(domain, {})

    # Try exact match
    mapped = source_map.get(value)
    if mapped:
        return mapped

    # Try case-insensitive
    value_lower = value.strip().lower()
    for src_val, target_val in source_map.items():
        if src_val.lower() == value_lower:
            return target_val

    # Check if already a valid canonical value
    canonical = CANONICAL_STATUSES.get(domain, set())
    if value_lower in canonical:
        return value_lower

    # Return lowercased original — will be flagged as warning in dry-run
    return value_lower
