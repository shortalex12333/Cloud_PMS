# routes/handlers/__init__.py
#
# Phase 4 dispatch table — action name → handler function.
# Imported by p0_actions_routes.py as _ACTION_HANDLERS.
#
# NOT the same as apps/api/handlers/ (domain business logic classes).
# This directory: thin dispatch functions registered by action name.
# apps/api/handlers/: stateful handler classes instantiated per request.
#
# Activation pattern: uncomment an import to activate its domain cluster.
# The uncomment IS the deployment gate — a bad handler file fails at
# import time (loud failure, safe to roll back).
#
# Current state: All Phase 4 domains active (92 actions registered).

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
