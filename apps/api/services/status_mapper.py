"""
Status Mapper Service

Provides canonical status sets for consistent status comparisons across the codebase.
Avoids hardcoded string comparisons and centralizes status definitions.

Usage:
    from services.status_mapper import StatusMapper

    if status in StatusMapper.WO_ACTIVE:
        # Work order is active

    canonical = StatusMapper.normalize_wo_status(raw_status)
"""

from typing import FrozenSet, Optional


class StatusMapper:
    """Canonical status sets for PMS entities."""

    # ==========================================================================
    # Work Order Statuses
    # ==========================================================================

    WO_ACTIVE: FrozenSet[str] = frozenset({
        'scheduled',
        'in_progress',
        'pending',
        'open',
        'on_hold',
    })

    WO_CLOSED: FrozenSet[str] = frozenset({
        'completed',
        'cancelled',
        'closed',
        'void',
    })

    WO_ALL: FrozenSet[str] = WO_ACTIVE | WO_CLOSED

    # ==========================================================================
    # Fault Statuses
    # ==========================================================================

    FAULT_OPEN: FrozenSet[str] = frozenset({
        'open',
        'investigating',
        'in_progress',
        'monitoring',
    })

    FAULT_RESOLVED: FrozenSet[str] = frozenset({
        'resolved',
        'closed',
        'false_alarm',
    })

    FAULT_ALL: FrozenSet[str] = FAULT_OPEN | FAULT_RESOLVED

    # ==========================================================================
    # Equipment Statuses
    # ==========================================================================

    EQUIPMENT_OPERATIONAL: FrozenSet[str] = frozenset({
        'operational',
        'active',
        'running',
    })

    EQUIPMENT_DOWN: FrozenSet[str] = frozenset({
        'down',
        'maintenance',
        'repair',
        'offline',
    })

    EQUIPMENT_ALL: FrozenSet[str] = EQUIPMENT_OPERATIONAL | EQUIPMENT_DOWN

    # ==========================================================================
    # Certificate Statuses
    # ==========================================================================

    CERT_VALID: FrozenSet[str] = frozenset({
        'valid',
        'active',
        'current',
    })

    CERT_EXPIRED: FrozenSet[str] = frozenset({
        'expired',
        'lapsed',
        'invalid',
    })

    CERT_PENDING: FrozenSet[str] = frozenset({
        'pending',
        'renewal_pending',
        'awaiting_approval',
    })

    CERT_ALL: FrozenSet[str] = CERT_VALID | CERT_EXPIRED | CERT_PENDING

    # ==========================================================================
    # Normalization Methods
    # ==========================================================================

    @classmethod
    def normalize_wo_status(cls, raw: Optional[str]) -> Optional[str]:
        """
        Normalize a work order status to canonical form.

        Returns None if status is unrecognized.
        """
        if not raw:
            return None

        normalized = raw.lower().strip().replace(' ', '_')

        # Map common variations
        mappings = {
            'inprogress': 'in_progress',
            'in-progress': 'in_progress',
            'onhold': 'on_hold',
            'on-hold': 'on_hold',
            'done': 'completed',
            'finished': 'completed',
            'canceled': 'cancelled',
        }

        return mappings.get(normalized, normalized)

    @classmethod
    def is_wo_active(cls, status: Optional[str]) -> bool:
        """Check if work order status indicates it's active."""
        if not status:
            return False
        normalized = cls.normalize_wo_status(status)
        return normalized in cls.WO_ACTIVE

    @classmethod
    def is_wo_closed(cls, status: Optional[str]) -> bool:
        """Check if work order status indicates it's closed."""
        if not status:
            return False
        normalized = cls.normalize_wo_status(status)
        return normalized in cls.WO_CLOSED

    @classmethod
    def is_equipment_operational(cls, status: Optional[str]) -> bool:
        """Check if equipment is operational."""
        if not status:
            return False
        return status.lower().strip() in cls.EQUIPMENT_OPERATIONAL

    @classmethod
    def is_fault_open(cls, status: Optional[str]) -> bool:
        """Check if fault is still open/active."""
        if not status:
            return False
        return status.lower().strip() in cls.FAULT_OPEN


# Convenience exports for direct import
WO_ACTIVE = StatusMapper.WO_ACTIVE
WO_CLOSED = StatusMapper.WO_CLOSED
FAULT_OPEN = StatusMapper.FAULT_OPEN
EQUIPMENT_OPERATIONAL = StatusMapper.EQUIPMENT_OPERATIONAL
