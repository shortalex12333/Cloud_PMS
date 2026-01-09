"""
Handlers Module
===============
P0 Action handlers and legacy SQL handlers.
"""

# P0 Action Handlers (new architecture)
from .work_order_mutation_handlers import WorkOrderMutationHandlers
from .inventory_handlers import InventoryHandlers
from .handover_handlers import HandoverHandlers
from .manual_handlers import ManualHandlers

# Legacy handlers (commented out to avoid import errors)
# from .equipment_handlers import get_equipment_handlers
# from .inventory_handlers import get_inventory_handlers
# from .work_order_handlers import get_work_order_handlers
# from .fault_handlers import get_fault_handlers
# from .list_handlers import get_list_handlers

__all__ = [
    # P0 Action Handlers
    'WorkOrderMutationHandlers',
    'InventoryHandlers',
    'HandoverHandlers',
    'ManualHandlers',

    # Legacy handlers (commented out)
    # 'get_equipment_handlers',
    # 'get_inventory_handlers',
    # 'get_work_order_handlers',
    # 'get_fault_handlers',
    # 'get_list_handlers',
]
