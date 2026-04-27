# routes/handlers/__init__.py
#
# Phase 4 dispatch table — action name → handler function.
# Imported by p0_actions_routes.py as _ACTION_HANDLERS.
#
# handlers/ is the single source of truth for all domain logic.
# This file only imports and merges their HANDLERS dicts.

from handlers.work_order_phase4 import HANDLERS as WO_HANDLERS
from handlers.media_phase4 import HANDLERS as MEDIA_HANDLERS
from handlers.handover_handlers import HANDLERS as HAND_HANDLERS
from handlers.purchase_order_phase4 import HANDLERS as PO_HANDLERS
from handlers.receiving_handlers import HANDLERS as RECV_HANDLERS
from handlers.certificate_handlers import CERT_HANDLERS
from handlers.document_handler import HANDLERS as DOC_HANDLERS
from handlers.shopping_list_handlers import HANDLERS as SHOP_HANDLERS
from handlers.pm_handler import HANDLERS as PM_HANDLERS
from handlers.fault_handler import HANDLERS as FAULT_HANDLERS
from handlers.equipment_handler import HANDLERS as EQUIP_HANDLERS
from handlers.part_handlers import HANDLERS as PARTS_HANDLERS
from handlers.compliance_handler import HANDLERS as COMPLIANCE_HANDLERS
from handlers.hours_of_rest_handlers import HANDLERS as HOR_HANDLERS
from .internal_adapter import HANDLERS as ADAPTER_HANDLERS

HANDLERS: dict = {
    **WO_HANDLERS,
    **RECV_HANDLERS,
    **CERT_HANDLERS,
    **DOC_HANDLERS,
    **HAND_HANDLERS,
    **SHOP_HANDLERS,
    **HOR_HANDLERS,
    **PM_HANDLERS,
    **FAULT_HANDLERS,
    **EQUIP_HANDLERS,
    **PARTS_HANDLERS,
    **MEDIA_HANDLERS,
    **COMPLIANCE_HANDLERS,
    **PO_HANDLERS,
    **{k: v for k, v in ADAPTER_HANDLERS.items()
       if k not in WO_HANDLERS
       and k not in PO_HANDLERS
       and k not in RECV_HANDLERS
       and k not in CERT_HANDLERS
       and k not in DOC_HANDLERS
       and k not in HAND_HANDLERS
       and k not in SHOP_HANDLERS
       and k not in HOR_HANDLERS
       and k not in PM_HANDLERS
       and k not in FAULT_HANDLERS
       and k not in EQUIP_HANDLERS
       and k not in PARTS_P5_HANDLERS
       and k not in MEDIA_HANDLERS
       and k not in COMPLIANCE_HANDLERS
       and k not in PO_HANDLERS},
}
