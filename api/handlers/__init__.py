"""
Action Handlers Package
=======================

Domain-specific handlers organized by group:
- Group 1: equipment_handlers.py (6 READ handlers)
- Group 2: inventory_handlers.py (6 READ handlers)
- Group 3: work_order_handlers.py (4 READ handlers)
- Group 4: fault_handlers.py (5 READ handlers)
- Group 5: document_handlers.py (2 READ handlers + file access)
- Group 6: other_handlers.py (16 READ handlers - handover, hours, fleet, etc.)
- Group 7: mutate_handlers.py (15 MUTATE handlers)

Total: 54 handlers
"""

# Group 1: Equipment
from .equipment_handlers import EquipmentHandlers, get_equipment_handlers

# Group 2: Inventory
from .inventory_handlers import InventoryHandlers, get_inventory_handlers

# Group 3: Work Orders
from .work_order_handlers import WorkOrderHandlers, get_work_order_handlers

# Group 4: Faults/Diagnostics
from .fault_handlers import FaultHandlers, get_fault_handlers

# Group 5: Documents
from .document_handlers import DocumentHandlers, get_document_handlers

# Group 6: Other (Handover, Hours of Rest, Fleet, etc.)
from .other_handlers import (
    HandoverHandlers,
    HoursOfRestHandlers,
    PurchasingHandlers,
    ChecklistHandlers,
    ShipyardHandlers,
    FleetHandlers,
    PredictiveHandlers,
    MobileHandlers,
    get_handover_handlers,
    get_hours_of_rest_handlers,
    get_purchasing_handlers,
    get_checklist_handlers,
    get_shipyard_handlers,
    get_fleet_handlers,
    get_predictive_handlers,
    get_mobile_handlers,
    get_all_other_handlers,
)

# Group 7: MUTATE handlers
from .mutate_handlers import (
    EquipmentMutateHandlers,
    InventoryMutateHandlers,
    WorkOrderMutateHandlers,
    FaultMutateHandlers,
    HoursOfRestMutateHandlers,
    ChecklistMutateHandlers,
    get_equipment_mutate_handlers,
    get_inventory_mutate_handlers,
    get_work_order_mutate_handlers,
    get_fault_mutate_handlers,
    get_hours_of_rest_mutate_handlers,
    get_checklist_mutate_handlers,
    get_all_mutate_handlers,
)


def get_all_handlers(supabase_client):
    """
    Get ALL handlers (READ + MUTATE) for registration.

    Returns dict mapping action_id -> handler function.
    """
    handlers = {}

    # READ handlers
    handlers.update(get_equipment_handlers(supabase_client))
    handlers.update(get_inventory_handlers(supabase_client))
    handlers.update(get_work_order_handlers(supabase_client))
    handlers.update(get_fault_handlers(supabase_client))
    handlers.update(get_document_handlers(supabase_client))
    handlers.update(get_all_other_handlers(supabase_client))

    # MUTATE handlers
    handlers.update(get_all_mutate_handlers(supabase_client))

    return handlers


__all__ = [
    # Group 1
    "EquipmentHandlers",
    "get_equipment_handlers",

    # Group 2
    "InventoryHandlers",
    "get_inventory_handlers",

    # Group 3
    "WorkOrderHandlers",
    "get_work_order_handlers",

    # Group 4
    "FaultHandlers",
    "get_fault_handlers",

    # Group 5
    "DocumentHandlers",
    "get_document_handlers",

    # Group 6
    "HandoverHandlers",
    "HoursOfRestHandlers",
    "PurchasingHandlers",
    "ChecklistHandlers",
    "ShipyardHandlers",
    "FleetHandlers",
    "PredictiveHandlers",
    "MobileHandlers",
    "get_handover_handlers",
    "get_hours_of_rest_handlers",
    "get_purchasing_handlers",
    "get_checklist_handlers",
    "get_shipyard_handlers",
    "get_fleet_handlers",
    "get_predictive_handlers",
    "get_mobile_handlers",
    "get_all_other_handlers",

    # Group 7
    "EquipmentMutateHandlers",
    "InventoryMutateHandlers",
    "WorkOrderMutateHandlers",
    "FaultMutateHandlers",
    "HoursOfRestMutateHandlers",
    "ChecklistMutateHandlers",
    "get_equipment_mutate_handlers",
    "get_inventory_mutate_handlers",
    "get_work_order_mutate_handlers",
    "get_fault_mutate_handlers",
    "get_hours_of_rest_mutate_handlers",
    "get_checklist_mutate_handlers",
    "get_all_mutate_handlers",

    # Master function
    "get_all_handlers",
]
