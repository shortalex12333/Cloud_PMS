# handlers/__init__.py
#
# Merges all domain handler registries into a single HANDLERS dict.
# The dispatcher imports this at module level.
#
# Activation pattern: each task uncomments its import + adds to HANDLERS.
# The uncomment IS the deployment gate — if the handler file has bugs,
# the import fails at startup (safe, visible failure).
#
# Current state: All Phase 4 domains active.

from .work_order_handler import HANDLERS as WO_HANDLERS
from .purchase_order_handler import HANDLERS as PO_HANDLERS
from .receiving_handler import HANDLERS as REC_HANDLERS
from .crew_handler import HANDLERS as CREW_HANDLERS
from .hours_of_rest_handler import HANDLERS as HOR_HANDLERS
from .certificate_handler import HANDLERS as CERT_HANDLERS
from .document_handler import HANDLERS as DOC_HANDLERS
from .handover_handler import HANDLERS as HAND_HANDLERS
from .shopping_handler import HANDLERS as SHOP_HANDLERS
from .pm_handler import HANDLERS as PM_HANDLERS

HANDLERS: dict = {
    **WO_HANDLERS, **PO_HANDLERS, **REC_HANDLERS,
    **CREW_HANDLERS, **HOR_HANDLERS,
    **CERT_HANDLERS, **DOC_HANDLERS, **HAND_HANDLERS,
    **SHOP_HANDLERS, **PM_HANDLERS,
}
