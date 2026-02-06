"""
Domain Microactions Registry
============================

Hardcoded mapping from (domain, intent) → microaction buttons.

This drives the action surfacing layer:
1. Worker 1 (Detective) detects {intent, domain, entity}
2. This registry maps (domain, intent) → available actions
3. Actions are filtered by role via /v1/actions/list
4. Prefill is built from NER output + top search result

Intents:
- READ: View/display data
- CREATE: Add new record
- UPDATE: Modify existing record
- DELETE: Remove record
- EXPORT: Download/print
- APPROVE: Sign off / confirm
- REJECT: Decline / cancel

Domains (from card types):
- hours_of_rest, inventory, parts, equipment, work_order, fault,
- document, certificate, handover, checklist, purchase, crew
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class MicroactionDef:
    """Definition of a microaction button."""
    action: str           # Action ID (e.g., 'view_hours_of_rest')
    label: str            # Button label (e.g., 'View Hours of Rest')
    side_effect: str      # 'read_only' | 'mutation' | 'mutation_heavy'
    requires_confirm: bool
    prefill_fields: List[str]  # Fields to prefill from NER/search
    allowed_roles: List[str]   # Roles that can see this action


# =============================================================================
# DOMAIN MICROACTIONS REGISTRY
# =============================================================================
# Key: (domain, intent)
# Value: List of MicroactionDef (multiple buttons per intent possible)

DOMAIN_MICROACTIONS: Dict[tuple, List[MicroactionDef]] = {

    # =========================================================================
    # HOURS OF REST
    # =========================================================================
    ('hours_of_rest', 'READ'): [
        MicroactionDef(
            action='view_hours_of_rest',
            label='View Hours of Rest',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['crew_id', 'date_range'],
            allowed_roles=['crew', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_compliance_status',
            label='Check Compliance',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['crew_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],
    ('hours_of_rest', 'UPDATE'): [
        MicroactionDef(
            action='update_hours_of_rest',
            label='Update Hours',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['crew_id', 'record_id', 'date'],
            allowed_roles=['crew', 'hod', 'captain', 'admin']
        ),
    ],
    ('hours_of_rest', 'EXPORT'): [
        MicroactionDef(
            action='export_hours_of_rest',
            label='Export Logs',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['crew_id', 'date_range', 'format'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],
    ('hours_of_rest', 'APPROVE'): [
        MicroactionDef(
            action='sign_hours_of_rest',
            label='Sign Off Hours',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['crew_id', 'record_id', 'date'],
            allowed_roles=['hod', 'captain']
        ),
    ],

    # =========================================================================
    # INVENTORY / PARTS
    # =========================================================================
    ('inventory', 'READ'): [
        MicroactionDef(
            action='view_inventory_item',
            label='View Details',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['item_id', 'item_name'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_stock_levels',
            label='Stock Levels',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['item_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_part_location',
            label='View Location',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['item_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('inventory', 'UPDATE'): [
        MicroactionDef(
            action='edit_inventory_quantity',
            label='Adjust Quantity',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['item_id', 'item_name', 'current_qty', 'operation'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('inventory', 'CREATE'): [
        MicroactionDef(
            action='add_part',
            label='Add Part',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['part_name', 'category', 'location'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='create_reorder',
            label='Create Reorder',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['item_id', 'item_name', 'quantity'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('inventory', 'DELETE'): [
        MicroactionDef(
            action='delete_part',
            label='Delete Part',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['item_id', 'item_name'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],

    ('parts', 'READ'): [
        MicroactionDef(
            action='view_part_details',
            label='View Part',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['part_id', 'part_number'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_part_usage',
            label='Usage History',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['part_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # EQUIPMENT
    # =========================================================================
    ('equipment', 'READ'): [
        MicroactionDef(
            action='view_equipment',
            label='View Equipment',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['equipment_id', 'equipment_name'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_maintenance_history',
            label='Maintenance History',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['equipment_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_equipment_parts',
            label='View Parts',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['equipment_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_linked_faults',
            label='View Faults',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['equipment_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_equipment_manual',
            label='Open Manual',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['equipment_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('equipment', 'UPDATE'): [
        MicroactionDef(
            action='add_equipment_note',
            label='Add Note',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['equipment_id', 'note_text'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # WORK ORDER
    # =========================================================================
    ('work_order', 'READ'): [
        MicroactionDef(
            action='view_work_order',
            label='View Work Order',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['work_order_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_work_order_history',
            label='View History',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['work_order_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_work_order_checklist',
            label='Show Checklist',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['work_order_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('work_order', 'CREATE'): [
        MicroactionDef(
            action='create_work_order',
            label='Create Work Order',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['equipment_id', 'title', 'description', 'priority'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('work_order', 'UPDATE'): [
        MicroactionDef(
            action='update_work_order_status',
            label='Update Status',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['work_order_id', 'new_status'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='add_work_order_note',
            label='Add Note',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['work_order_id', 'note_text'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='add_work_order_photo',
            label='Add Photo',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['work_order_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='add_parts_to_work_order',
            label='Add Parts',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['work_order_id', 'part_ids'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='assign_work_order',
            label='Assign Task',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['work_order_id', 'assignee_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='edit_work_order_details',
            label='Edit Work Order',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['work_order_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # FAULT
    # =========================================================================
    ('fault', 'READ'): [
        MicroactionDef(
            action='view_fault',
            label='View Fault',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['fault_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_fault_history',
            label='View History',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['fault_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('fault', 'UPDATE'): [
        MicroactionDef(
            action='add_fault_note',
            label='Add Note',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['fault_id', 'note_text'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='add_fault_photo',
            label='Add Photo',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['fault_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # DOCUMENT
    # =========================================================================
    ('document', 'READ'): [
        MicroactionDef(
            action='open_document',
            label='Open Document',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['document_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='open_document_page',
            label='Open Page',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['document_id', 'page_number'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='search_document_pages',
            label='Search Within Document',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['document_id', 'search_term'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='summarise_document_section',
            label='Summarise Section',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['document_id', 'section'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_linked_entities',
            label='View Linked Items',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['document_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('document', 'UPDATE'): [
        MicroactionDef(
            action='update_document',
            label='Update Document',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['document_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='add_document_tags',
            label='Add Tags',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['document_id', 'tags'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='replace_document_version',
            label='Replace Version',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['document_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],
    ('document', 'DELETE'): [
        MicroactionDef(
            action='delete_document',
            label='Delete Document',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['document_id'],
            allowed_roles=['admin']
        ),
        MicroactionDef(
            action='archive_document',
            label='Archive Document',
            side_effect='mutation',
            requires_confirm=True,
            prefill_fields=['document_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # CERTIFICATE
    # =========================================================================
    ('certificate', 'READ'): [
        MicroactionDef(
            action='view_certificate',
            label='View Certificate',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['certificate_id'],
            allowed_roles=['crew', 'hod', 'captain', 'admin']
        ),
    ],
    ('certificate', 'CREATE'): [
        MicroactionDef(
            action='upload_certificate_document',
            label='Upload Certificate',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['certificate_type', 'expiry_date'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],
    ('certificate', 'UPDATE'): [
        MicroactionDef(
            action='update_certificate_metadata',
            label='Update Info',
            side_effect='mutation',
            requires_confirm=True,
            prefill_fields=['certificate_id', 'expiry_date'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # HANDOVER
    # =========================================================================
    ('handover', 'READ'): [
        MicroactionDef(
            action='export_handover',
            label='Export PDF',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['handover_id'],
            allowed_roles=['crew', 'hod', 'captain', 'admin']
        ),
    ],
    ('handover', 'UPDATE'): [
        MicroactionDef(
            action='add_to_handover',
            label='Add to Handover',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['handover_id', 'item_id', 'item_type'],
            allowed_roles=['crew', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='add_document_to_handover',
            label='Add Document',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['handover_id', 'document_id'],
            allowed_roles=['crew', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='edit_handover_section',
            label='Edit Section',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['handover_id', 'section_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # PURCHASE
    # =========================================================================
    ('purchase', 'READ'): [
        MicroactionDef(
            action='view_purchase_order',
            label='View Purchase Order',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['purchase_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('purchase', 'CREATE'): [
        MicroactionDef(
            action='create_purchase_request',
            label='Create Purchase',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['item_id', 'quantity', 'supplier_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='add_item_to_purchase',
            label='Add Item',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['purchase_id', 'item_id', 'quantity'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('purchase', 'APPROVE'): [
        MicroactionDef(
            action='approve_purchase',
            label='Approve Purchase',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['purchase_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],
    ('purchase', 'UPDATE'): [
        MicroactionDef(
            action='update_purchase_status',
            label='Update Status',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['purchase_id', 'new_status'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # SHOPPING LIST
    # =========================================================================
    ('shopping_list', 'CREATE'): [
        MicroactionDef(
            action='create_shopping_list_item',
            label='Add to Shopping List',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['item_name', 'quantity', 'category'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('shopping_list', 'APPROVE'): [
        MicroactionDef(
            action='approve_shopping_list_item',
            label='Approve Item',
            side_effect='mutation',
            requires_confirm=True,
            prefill_fields=['item_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],
    ('shopping_list', 'REJECT'): [
        MicroactionDef(
            action='reject_shopping_list_item',
            label='Reject Item',
            side_effect='mutation',
            requires_confirm=True,
            prefill_fields=['item_id', 'reason'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # CHECKLIST
    # =========================================================================
    ('checklist', 'READ'): [
        MicroactionDef(
            action='view_checklist',
            label='View Checklist',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['checklist_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('checklist', 'UPDATE'): [
        MicroactionDef(
            action='add_checklist_note',
            label='Add Note',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['checklist_id', 'note_text'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='add_checklist_photo',
            label='Add Photo',
            side_effect='mutation',
            requires_confirm=False,
            prefill_fields=['checklist_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # CREW
    # =========================================================================
    ('crew', 'READ'): [
        MicroactionDef(
            action='view_crew_profile',
            label='View Profile',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['crew_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_crew_certifications',
            label='View Certifications',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['crew_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],
    ('crew', 'UPDATE'): [
        MicroactionDef(
            action='update_crew_profile',
            label='Update Profile',
            side_effect='mutation',
            requires_confirm=True,
            prefill_fields=['crew_id'],
            allowed_roles=['hod', 'captain', 'admin']
        ),
    ],

    # =========================================================================
    # RECEIVING / DELIVERIES
    # =========================================================================
    ('receiving', 'READ'): [
        MicroactionDef(
            action='view_receiving',
            label='View Delivery',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['receiving_id', 'vendor_name'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
        MicroactionDef(
            action='view_receiving_items',
            label='View Items',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['receiving_id'],
            allowed_roles=['crew', 'engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('receiving', 'UPDATE'): [
        MicroactionDef(
            action='update_receiving',
            label='Update Delivery',
            side_effect='mutation',
            requires_confirm=True,
            prefill_fields=['receiving_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('receiving', 'APPROVE'): [
        MicroactionDef(
            action='accept_receiving',
            label='Accept Delivery',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['receiving_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],
    ('receiving', 'REJECT'): [
        MicroactionDef(
            action='reject_receiving',
            label='Reject Delivery',
            side_effect='mutation_heavy',
            requires_confirm=True,
            prefill_fields=['receiving_id'],
            allowed_roles=['engineer', 'hod', 'captain', 'admin']
        ),
    ],
}


# =============================================================================
# DOMAIN KEYWORDS (for detection + domain boost in fusion)
# =============================================================================
# Maps keywords → (domain, boost_value)
# Used to detect domain from query and apply ranking boost

DOMAIN_KEYWORDS: Dict[str, tuple] = {
    # Hours of Rest - expanded with abbreviations and variants
    'hours of rest': ('hours_of_rest', 0.30),
    'hour of rest': ('hours_of_rest', 0.30),
    'hours-of-rest': ('hours_of_rest', 0.30),
    'hours_of_rest': ('hours_of_rest', 0.30),
    'hor': ('hours_of_rest', 0.30),
    'h.o.r': ('hours_of_rest', 0.30),
    'rest hours': ('hours_of_rest', 0.25),
    'rest-hours': ('hours_of_rest', 0.25),
    'rest_hours': ('hours_of_rest', 0.25),
    'rest hrs': ('hours_of_rest', 0.25),
    'rest period': ('hours_of_rest', 0.20),
    'rest record': ('hours_of_rest', 0.25),
    'rest records': ('hours_of_rest', 0.25),
    'work hours': ('hours_of_rest', 0.20),
    'work rest': ('hours_of_rest', 0.20),
    'fatigue': ('hours_of_rest', 0.15),
    'compliance': ('hours_of_rest', 0.15),
    'mlc': ('hours_of_rest', 0.20),
    'sign off': ('hours_of_rest', 0.20),
    'signoff': ('hours_of_rest', 0.20),
    'sign-off': ('hours_of_rest', 0.20),
    'monthly sign': ('hours_of_rest', 0.20),
    'log hours': ('hours_of_rest', 0.25),
    'log hrs': ('hours_of_rest', 0.25),
    'my hours': ('hours_of_rest', 0.20),
    'my hrs': ('hours_of_rest', 0.20),

    # Inventory / Parts - core terms
    'inventory': ('inventory', 0.30),
    'stock': ('inventory', 0.25),
    'stock level': ('inventory', 0.30),
    'stock levels': ('inventory', 0.30),
    'in stock': ('inventory', 0.25),
    'out of stock': ('inventory', 0.30),
    'parts': ('parts', 0.30),
    'part': ('parts', 0.25),
    'spare': ('parts', 0.20),
    'spares': ('parts', 0.20),
    'consumable': ('inventory', 0.20),
    'reorder': ('inventory', 0.20),
    # Parts - specific types
    'filter': ('parts', 0.25),
    'gasket': ('parts', 0.25),
    'bearing': ('parts', 0.25),
    'seal': ('parts', 0.25),
    'belt': ('parts', 0.25),
    'impeller': ('parts', 0.25),
    'injector': ('parts', 0.25),
    'turbocharger': ('parts', 0.25),
    'alternator': ('parts', 0.25),
    'antenna': ('parts', 0.25),
    # Parts - manufacturers (lower boost, secondary signal)
    'mtu': ('parts', 0.20),
    'volvo penta': ('parts', 0.20),
    'volvo': ('parts', 0.15),
    'caterpillar': ('parts', 0.20),
    'cat': ('parts', 0.15),
    'cummins': ('parts', 0.20),
    'kohler': ('parts', 0.20),
    'grundfos': ('parts', 0.20),
    'racor': ('parts', 0.20),
    'fleetguard': ('parts', 0.20),
    'mann': ('parts', 0.15),
    'parker': ('parts', 0.15),
    'parker hannifin': ('parts', 0.20),
    'raymarine': ('parts', 0.20),
    'furuno': ('parts', 0.20),
    'garmin': ('parts', 0.20),
    'survitec': ('parts', 0.20),

    # Equipment - core terms
    'equipment': ('equipment', 0.30),
    'machine': ('equipment', 0.20),
    'system': ('equipment', 0.15),
    'engine': ('equipment', 0.25),
    'generator': ('equipment', 0.25),
    'pump': ('equipment', 0.20),
    'compressor': ('equipment', 0.20),
    # Equipment - specific types
    'watermaker': ('equipment', 0.30),
    'water maker': ('equipment', 0.30),
    'radar': ('equipment', 0.30),
    'flybridge': ('equipment', 0.25),
    'fly bridge': ('equipment', 0.25),
    'autopilot': ('equipment', 0.25),
    'thruster': ('equipment', 0.25),
    'stabilizer': ('equipment', 0.25),
    'boiler': ('equipment', 0.25),
    'chiller': ('equipment', 0.25),
    'hvac': ('equipment', 0.25),
    'hydraulic': ('equipment', 0.20),
    'anchor': ('equipment', 0.20),
    'winch': ('equipment', 0.25),
    'crane': ('equipment', 0.25),
    'davit': ('equipment', 0.25),
    'tender': ('equipment', 0.20),

    # Work Order
    'work order': ('work_order', 0.30),
    'workorder': ('work_order', 0.30),
    'wo': ('work_order', 0.25),
    'task': ('work_order', 0.20),
    'job': ('work_order', 0.20),
    'maintenance': ('work_order', 0.20),

    # Fault
    'fault': ('fault', 0.30),
    'faults': ('fault', 0.30),
    'error': ('fault', 0.20),
    'failure': ('fault', 0.25),
    'alarm': ('fault', 0.20),
    'warning': ('fault', 0.20),
    'issue': ('fault', 0.15),

    # Document - boost manual higher so "watermaker manual" → document
    'document': ('document', 0.30),
    'documents': ('document', 0.30),
    'doc': ('document', 0.25),
    'manual': ('document', 0.35),  # Higher boost so "X manual" → document
    'manuals': ('document', 0.35),
    'procedure': ('document', 0.20),
    'sop': ('document', 0.25),
    'drawing': ('document', 0.20),
    'schematic': ('document', 0.20),

    # Certificate
    'certificate': ('certificate', 0.30),
    'cert': ('certificate', 0.25),
    'certification': ('certificate', 0.25),
    'expiry': ('certificate', 0.20),
    'license': ('certificate', 0.20),

    # Handover
    'handover': ('handover', 0.30),
    'hand over': ('handover', 0.30),
    'turnover': ('handover', 0.25),
    'shift': ('handover', 0.15),

    # Purchase
    'purchase': ('purchase', 0.30),
    'purchase order': ('purchase', 0.30),
    'po': ('purchase', 0.25),
    'order': ('purchase', 0.20),
    'supplier': ('purchase', 0.20),

    # Shopping List
    'shopping list': ('shopping_list', 0.30),
    'shopping': ('shopping_list', 0.25),
    'requisition': ('shopping_list', 0.20),

    # Checklist
    'checklist': ('checklist', 0.30),
    'check list': ('checklist', 0.30),
    'inspection': ('checklist', 0.20),

    # Crew
    'crew': ('crew', 0.30),
    'crew member': ('crew', 0.30),
    'seafarer': ('crew', 0.25),
    'staff': ('crew', 0.20),

    # Receiving / Deliveries (MVP1 - added for ranking tests)
    'receiving': ('receiving', 0.30),
    'received': ('receiving', 0.25),
    'receive': ('receiving', 0.25),
    'delivery': ('receiving', 0.30),
    'deliveries': ('receiving', 0.30),
    'shipment': ('receiving', 0.25),
    'shipments': ('receiving', 0.25),
    'arrival': ('receiving', 0.20),
    'arrived': ('receiving', 0.20),
    'vendor': ('receiving', 0.20),
    'supplier delivery': ('receiving', 0.30),
    'goods received': ('receiving', 0.30),
    'package': ('receiving', 0.20),
    'packages': ('receiving', 0.20),
    'inbound': ('receiving', 0.25),
}


# =============================================================================
# INTENT KEYWORDS (for intent detection)
# =============================================================================
# Maps keywords → intent

INTENT_KEYWORDS: Dict[str, str] = {
    # READ
    'show': 'READ',
    'view': 'READ',
    'display': 'READ',
    'get': 'READ',
    'find': 'READ',
    'search': 'READ',
    'look up': 'READ',
    'lookup': 'READ',
    'check': 'READ',
    'see': 'READ',
    'list': 'READ',
    'what is': 'READ',
    'where is': 'READ',

    # CREATE
    'create': 'CREATE',
    'add': 'CREATE',
    'new': 'CREATE',
    'insert': 'CREATE',
    'make': 'CREATE',
    'generate': 'CREATE',

    # UPDATE
    'update': 'UPDATE',
    'edit': 'UPDATE',
    'modify': 'UPDATE',
    'change': 'UPDATE',
    'adjust': 'UPDATE',
    'reduce': 'UPDATE',
    'increase': 'UPDATE',
    'decrease': 'UPDATE',
    'set': 'UPDATE',
    'correct': 'UPDATE',
    'fix': 'UPDATE',

    # DELETE
    'delete': 'DELETE',
    'remove': 'DELETE',
    'archive': 'DELETE',
    'discard': 'DELETE',

    # EXPORT
    'export': 'EXPORT',
    'download': 'EXPORT',
    'print': 'EXPORT',
    'pdf': 'EXPORT',
    'excel': 'EXPORT',
    'report': 'EXPORT',

    # APPROVE
    'approve': 'APPROVE',
    'sign': 'APPROVE',
    'confirm': 'APPROVE',
    'accept': 'APPROVE',
    'authorize': 'APPROVE',

    # REJECT
    'reject': 'REJECT',
    'decline': 'REJECT',
    'deny': 'REJECT',
    'cancel': 'REJECT',
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# =============================================================================
# CANONICAL DOMAIN NORMALIZATION
# =============================================================================
# Maps plural/variant domain names to canonical singular form

DOMAIN_CANONICAL: Dict[str, str] = {
    # Plurals → singular
    'parts': 'part',
    'documents': 'document',
    'certificates': 'certificate',
    'faults': 'fault',
    'equipments': 'equipment',  # grammatically wrong but users type it
    'work_orders': 'work_order',
    'handovers': 'handover',
    'checklists': 'checklist',
    # Variants → canonical
    'inventory': 'inventory',  # keep as-is (no singular "inventorie")
    'crew': 'crew',  # collective noun
    'receiving': 'receiving',  # gerund
    'purchase': 'purchase',
    'shopping_list': 'shopping_list',
    'hours_of_rest': 'hours_of_rest',
}


def normalize_domain(domain: str) -> str:
    """Normalize domain to canonical singular form."""
    return DOMAIN_CANONICAL.get(domain, domain)


def normalize_for_detection(query: str) -> str:
    """
    Normalize query for domain detection.

    - Replace separators with spaces
    - Expand common abbreviations
    - Lowercase
    """
    import re

    query = query.lower()

    # Replace separators with spaces
    query = re.sub(r'[_\-|]', ' ', query)

    # Collapse whitespace
    query = re.sub(r'\s+', ' ', query)

    # Expand abbreviations
    abbreviations = {
        'hrs': 'hours',
        'hr': 'hour',
        'w/o': 'work order',
        'w.o.': 'work order',
        'wo': 'work order',
        'inv': 'inventory',
        'equip': 'equipment',
        'eqpt': 'equipment',
        'prt': 'part',
        'prts': 'parts',
        'cert': 'certificate',
        'certs': 'certificates',
        'doc': 'document',
        'docs': 'documents',
    }

    for abbrev, expansion in abbreviations.items():
        pattern = r'\b' + re.escape(abbrev) + r'\b'
        query = re.sub(pattern, expansion, query)

    return query.strip()


def detect_domain_from_query(query: str) -> Optional[tuple]:
    """
    Detect domain and boost from query text.

    Fix 5: Uses normalization for better detection of abbreviations and variants.
    Fix 6: Returns highest-boost match, not first match by length.

    Returns: (domain, boost) or None
    """
    # Normalize first
    query_normalized = normalize_for_detection(query)

    # Collect all matching keywords and their boost values
    matches = []

    for keyword, (domain, boost) in DOMAIN_KEYWORDS.items():
        if keyword in query_normalized:
            matches.append((domain, boost, keyword))

    # Also check original query for edge cases
    if not matches:
        query_lower = query.lower()
        for keyword, (domain, boost) in DOMAIN_KEYWORDS.items():
            if keyword in query_lower:
                matches.append((domain, boost, keyword))

    if not matches:
        return None

    # Return the highest-boost match
    # This ensures "watermaker 1 manual" → document (0.35) not equipment (0.30)
    matches.sort(key=lambda x: x[1], reverse=True)
    best_domain, best_boost, _ = matches[0]

    # Normalize to canonical form (parts → part, documents → document, etc.)
    best_domain = normalize_domain(best_domain)

    return (best_domain, best_boost)


def detect_intent_from_query(query: str) -> str:
    """
    Detect intent from query text.

    Returns: intent string (default: 'READ')
    """
    import re
    query_lower = query.lower()

    # Contextual rules: "accepted/approved/rejected" followed by a noun = status filter (READ)
    # Examples: "accepted deliveries", "approved records", "rejected items"
    status_adjective_pattern = r'\b(accepted|approved|rejected|draft|pending)\s+(deliveries|delivery|records|items|orders|receiving|shipments?)\b'
    if re.search(status_adjective_pattern, query_lower):
        return 'READ'

    # "details" or "documents" alone implies READ
    if re.search(r'\bdetails\b', query_lower) and not re.search(r'\b(create|add|new)\b', query_lower):
        return 'READ'
    if re.search(r'\bdocuments?\b', query_lower) and not re.search(r'\b(create|add|new|upload)\b', query_lower):
        return 'READ'

    # Check longest matches first
    sorted_keywords = sorted(INTENT_KEYWORDS.keys(), key=len, reverse=True)

    for keyword in sorted_keywords:
        if keyword in query_lower:
            return INTENT_KEYWORDS[keyword]

    return 'READ'  # Default intent


def get_microactions_for_query(
    query: str,
    role: str,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    entity_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Get microaction buttons for a query, filtered by role.

    Args:
        query: User query text
        role: User role (crew, engineer, hod, captain, admin)
        entity_id: ID of the top entity from search (for prefill)
        entity_name: Name of the top entity (for prefill)
        entity_data: Additional entity data from search result (for prefill)

    Returns:
        List of microaction button definitions with prefill
    """
    # Detect domain and intent
    domain_result = detect_domain_from_query(query)
    if not domain_result:
        return []

    domain, _ = domain_result
    intent = detect_intent_from_query(query)

    # Normalize domain to canonical form, then check microaction mappings
    # Microactions are keyed by ('parts', 'READ') but domain may be 'part'
    # So we need to check both the canonical form and the original DOMAIN_MICROACTIONS keys
    canonical_domain = normalize_domain(domain)

    # Map canonical → microaction key (some microactions use plural form)
    microaction_domain_map = {
        'part': 'parts',  # DOMAIN_MICROACTIONS uses ('parts', intent)
    }
    normalized_domain = microaction_domain_map.get(canonical_domain, canonical_domain)

    # Get microactions for (domain, intent)
    key = (normalized_domain, intent)
    if key not in DOMAIN_MICROACTIONS:
        # Fallback to READ if specific intent not found
        key = (normalized_domain, 'READ')
        if key not in DOMAIN_MICROACTIONS:
            return []

    microactions = DOMAIN_MICROACTIONS[key]

    # Filter by role
    allowed_actions = [
        ma for ma in microactions
        if role in ma.allowed_roles
    ]

    # Build response with prefill
    result = []
    for ma in allowed_actions:
        prefill = {}

        # Build prefill from entity data
        if entity_id:
            # Map common prefill fields
            field_mapping = {
                'item_id': entity_id,
                'part_id': entity_id,
                'equipment_id': entity_id,
                'work_order_id': entity_id,
                'fault_id': entity_id,
                'document_id': entity_id,
                'certificate_id': entity_id,
                'handover_id': entity_id,
                'purchase_id': entity_id,
                'checklist_id': entity_id,
                'crew_id': entity_id,
                'record_id': entity_id,
                'receiving_id': entity_id,
            }

            for field in ma.prefill_fields:
                if field in field_mapping:
                    prefill[field] = field_mapping[field]

        if entity_name:
            name_fields = ['item_name', 'part_name', 'equipment_name', 'part_number']
            for field in ma.prefill_fields:
                if field in name_fields:
                    prefill[field] = entity_name

        if entity_data:
            # Pull additional prefill from entity data
            for field in ma.prefill_fields:
                if field not in prefill and field in entity_data:
                    prefill[field] = entity_data[field]

        result.append({
            'action': ma.action,
            'label': ma.label,
            'side_effect': ma.side_effect,
            'requires_confirm': ma.requires_confirm,
            'prefill': prefill,
        })

    return result


def get_domain_boost_for_object_type(query: str, object_type: str) -> float:
    """
    Get domain boost for a specific object type based on query.

    Used in fusion scoring: if query matches a domain keyword,
    boost results of matching object types.

    Returns: boost value (0.0 to 0.3)
    """
    domain_result = detect_domain_from_query(query)
    if not domain_result:
        return 0.0

    domain, boost = domain_result

    # Map domains to object types
    domain_to_object_types = {
        'hours_of_rest': ['hours_of_rest'],
        'inventory': ['inventory', 'part', 'parts', 'receiving'],
        'parts': ['part', 'parts', 'inventory'],
        'equipment': ['equipment'],
        'work_order': ['work_order', 'work_order_note'],
        'fault': ['fault'],
        'document': ['document'],
        'certificate': ['certificate'],
        'handover': ['handover', 'handover_item'],
        'purchase': ['purchase_order', 'shopping_item'],
        'shopping_list': ['shopping_item'],
        'checklist': ['checklist'],
        'crew': ['crew', 'crew_member'],
    }

    # Check if object_type matches domain
    matching_types = domain_to_object_types.get(domain, [])
    if object_type in matching_types:
        return boost

    return 0.0
