# routes/handlers/__init__.py
#
# Phase 4 dispatch table — action name → handler function.
# Imported by p0_actions_routes.py as _ACTION_HANDLERS.
#
# handlers/ is the single source of truth for all domain logic.
# This file only imports and merges their HANDLERS dicts.
#
# Migration state (2026-04-27):
#   WO domain  -> fully in handlers/work_order_phase4.py
#   Media      -> fully in handlers/media_phase4.py
#   Handover   -> fully in handlers/handover_handlers.py
#   All others -> still in routes/handlers/{domain}_handler.py

from handlers.work_order_phase4 import HANDLERS as WO_HANDLERS
from handlers.media_phase4 import HANDLERS as MEDIA_HANDLERS
from handlers.handover_handlers import HANDLERS as HAND_HANDLERS
from handlers.purchase_order_phase4 import HANDLERS as PO_HANDLERS
from .receiving_handler import HANDLERS as REC_HANDLERS
from .certificate_phase4_handler import HANDLERS as CERT_HANDLERS
from .document_handler import HANDLERS as DOC_HANDLERS
from .shopping_handler import HANDLERS as SHOP_HANDLERS
from .pm_handler import HANDLERS as PM_HANDLERS
from .fault_handler import HANDLERS as FAULT_HANDLERS
from .equipment_handler import HANDLERS as EQUIP_HANDLERS
from .parts_handler_p5 import HANDLERS as PARTS_P5_HANDLERS
from .compliance_handler import HANDLERS as COMPLIANCE_HANDLERS
from .internal_adapter import HANDLERS as ADAPTER_HANDLERS

HANDLERS: dict = {
    **WO_HANDLERS,
    **REC_HANDLERS,
    **CERT_HANDLERS,
    **DOC_HANDLERS,
    **HAND_HANDLERS,
    **SHOP_HANDLERS,
    **PM_HANDLERS,
    **FAULT_HANDLERS,
    **EQUIP_HANDLERS,
    **PARTS_P5_HANDLERS,
    **MEDIA_HANDLERS,
    **COMPLIANCE_HANDLERS,
    **PO_HANDLERS,
    **{k: v for k, v in ADAPTER_HANDLERS.items()
       if k not in WO_HANDLERS
       and k not in PO_HANDLERS
       and k not in REC_HANDLERS
       and k not in CERT_HANDLERS
       and k not in DOC_HANDLERS
       and k not in HAND_HANDLERS
       and k not in SHOP_HANDLERS
       and k not in PM_HANDLERS
       and k not in FAULT_HANDLERS
       and k not in EQUIP_HANDLERS
       and k not in PARTS_P5_HANDLERS
       and k not in MEDIA_HANDLERS
       and k not in COMPLIANCE_HANDLERS
       and k not in PO_HANDLERS},
}
