# handlers/__init__.py
#
# Merges all domain handler registries into a single HANDLERS dict.
# The dispatcher imports this at module level.
#
# Activation pattern: each task uncomments its import + adds to HANDLERS.
# The uncomment IS the deployment gate — if the handler file has bugs,
# the import fails at startup (safe, visible failure).
#
# Current state: HANDLERS is empty — all actions fall through to legacy elif chain.

# from .work_order_handler import HANDLERS as WO_HANDLERS       # activate in Task 2
# from .purchase_order_handler import HANDLERS as PO_HANDLERS   # activate in Task 3
# from .receiving_handler import HANDLERS as REC_HANDLERS        # activate in Task 3
# from .crew_handler import HANDLERS as CREW_HANDLERS            # activate in Task 4
# from .hours_of_rest_handler import HANDLERS as HOR_HANDLERS    # activate in Task 4
# from .certificate_handler import HANDLERS as CERT_HANDLERS     # activate in Task 5
# from .document_handler import HANDLERS as DOC_HANDLERS         # activate in Task 5
# from .handover_handler import HANDLERS as HAND_HANDLERS        # activate in Task 5
# from .shopping_handler import HANDLERS as SHOP_HANDLERS        # activate in Task 5
# from .pm_handler import HANDLERS as PM_HANDLERS                # activate in Task 5

HANDLERS: dict = {}
