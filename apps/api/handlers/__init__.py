"""
Handlers Module
===============
SQL handlers for specific entity types from frontend-microactions branch.
"""

from .equipment_handlers import get_equipment_handlers
from .inventory_handlers import get_inventory_handlers
from .work_order_handlers import get_work_order_handlers
from .fault_handlers import get_fault_handlers
from .list_handlers import get_list_handlers

__all__ = [
    'get_equipment_handlers',
    'get_inventory_handlers',
    'get_work_order_handlers',
    'get_fault_handlers',
    'get_list_handlers',
]
