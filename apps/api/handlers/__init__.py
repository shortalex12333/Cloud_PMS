"""
Handlers Module
===============
All action handlers: P0, P1, P2, P3, and Situations.
"""

# P0 Action Handlers
from .work_order_mutation_handlers import WorkOrderMutationHandlers
from .inventory_handlers import InventoryHandlers
from .handover_handlers import HandoverHandlers
from .manual_handlers import ManualHandlers

# P1 Action Handlers
from .p1_purchasing_handlers import P1PurchasingHandlers, get_p1_purchasing_handlers
from .p1_compliance_handlers import P1ComplianceHandlers, get_p1_compliance_handlers

# P2 Action Handlers
from .p2_mutation_light_handlers import P2MutationLightHandlers, get_p2_mutation_light_handlers

# P3 Read-Only Handlers
from .p3_read_only_handlers import P3ReadOnlyHandlers, get_p3_read_only_handlers

# Certificate Handlers (Certificate Lens v2)
# Import is optional - may fail if schema_mapping is missing certificate functions
try:
    from .certificate_handlers import CertificateHandlers, get_certificate_handlers
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Certificate handlers not available: {e}")
    CertificateHandlers = None
    get_certificate_handlers = None

# Email Handlers (Email Lens)
from .email_handlers import EmailHandlers, get_email_handlers

# Situation State Machines
from .situation_handlers import (
    SituationManager,
    FaultSituation,
    WorkOrderSituation,
    EquipmentSituation,
    PartSituation,
    DocumentSituation,
    HandoverSituation,
    PurchaseSituation,
    ReceivingSituation,
    ComplianceSituation,
    get_situation_handlers
)

__all__ = [
    # P0 Action Handlers
    'WorkOrderMutationHandlers',
    'InventoryHandlers',
    'HandoverHandlers',
    'ManualHandlers',

    # P1 Action Handlers
    'P1PurchasingHandlers',
    'P1ComplianceHandlers',
    'get_p1_purchasing_handlers',
    'get_p1_compliance_handlers',

    # P2 Action Handlers
    'P2MutationLightHandlers',
    'get_p2_mutation_light_handlers',

    # P3 Read-Only Handlers
    'P3ReadOnlyHandlers',
    'get_p3_read_only_handlers',

    # Certificate Handlers
    'CertificateHandlers',
    'get_certificate_handlers',

    # Email Handlers
    'EmailHandlers',
    'get_email_handlers',

    # Situation State Machines
    'SituationManager',
    'FaultSituation',
    'WorkOrderSituation',
    'EquipmentSituation',
    'PartSituation',
    'DocumentSituation',
    'HandoverSituation',
    'PurchaseSituation',
    'ReceivingSituation',
    'ComplianceSituation',
    'get_situation_handlers',
]
