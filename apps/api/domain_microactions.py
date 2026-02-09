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

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re


# HOTFIX 2026-02-09: Force rebuild to activate Shopping List entity extraction
# Shopping List compound anchors are present in COMPOUND_ANCHORS (lines 912-931)
# This constant forces Python bytecode recompilation to load the fix
# UPDATED: 2026-02-09 17:00 UTC - Version bump .002 to FORCE Render rebuild
ENTITY_EXTRACTION_VERSION = "2026.02.09.002"  # MUST ACTIVATE Shopping List + Parts
# Next deployment MUST load shopping_list patterns or issue is Render config


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
            allowed_roles=['crew', 'deckhand', 'steward', 'chef', 'bosun', 'engineer', 'eto',
                          'chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager']
        ),
        MicroactionDef(
            action='view_part_usage',
            label='Usage History',
            side_effect='read_only',
            requires_confirm=False,
            prefill_fields=['part_id'],
            allowed_roles=['engineer', 'eto', 'chief_engineer', 'chief_officer', 'captain', 'manager']
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
# COMPOUND ANCHORS (determine domain with high confidence)
# =============================================================================
# Only compound patterns anchor a domain. Single keywords are demoted.
# Each pattern returns (domain, confidence) when matched.

COMPOUND_ANCHORS: Dict[str, List[str]] = {
    # hours_of_rest compounds - require multi-word context
    # Includes abbreviations: hrs, hor
    'hours_of_rest': [
        # Core patterns
        r'\bcrew\s+rest\b',
        r'\brest\s+hours?\b',
        r'\brest\s+hrs\b',  # abbreviation
        r'\bhours?[\s-]+of[\s-]+rest\b',  # matches "hours of rest" and "hours-of-rest"
        r'\bwork\s+hours?\b',
        r'\bwork\s+hrs\b',  # abbreviation
        r'\brest\s+violations?\b',
        r'\brest\s+records?\b',
        r'\brest\s+recordz\b',  # common typo - but search handles fuzzy
        r'\brest\s+compliance\b',
        # Monthly sign-off patterns
        r'\bmonthly\s+sign[- ]?off',
        r'\bmonthly\s+(hours?|hrs|record)',
        r'\bsign[- ]?off.*hours?\b',
        r'\bsign\s+monthly\b',
        r'\bsign\s+(my\s+)?monthly',
        # Log/update patterns with abbreviations
        r'\blog\s+(my\s+)?(hours?|hrs|rest)\b',
        r'\brecord\s+(my\s+)?(hours?|hrs|rest)\b',
        r'\benter\s+(my\s+)?(hours?|hrs|rest)\b',
        r'\bupdate\s+(my\s+)?(hours?|hrs|rest)\b',
        # Abbreviations with context
        r'\bhor\s+\w+',  # "hor records", "hor violations"
        r'\bhor\b',  # Standalone abbreviation
        r'\bh\.o\.r\b',
        r'\bhrs\s+of\s+rest\b',
        # Compliance
        r'\bmlc\s+compliance\b',
        r'\bfatigue\s+management\b',
        # Acknowledge patterns
        r'\back(nowledge)?\s+(rest\s+)?violation',
    ],
    # receiving compounds - status + delivery/receiving
    'receiving': [
        r'\b(accepted?|approved?)\s+deliver',
        r'\b(rejected?|declined?)\s+deliver',
        r'\bdraft\s+deliver',
        r'\bpending\s+deliver',
        r'\breceiving\s+(draft|accepted|rejected|pending)\b',
        r'\bdeliveries?\s+(this|last|today|yesterday)',
        r'\bshipments?\s+(from|to|this|last)',
        r'\bgoods\s+received\b',
        r'\bsupplier\s+delivery\b',
        r'\binbound\s+shipment',
    ],
    # equipment compounds - specific equipment types or equipment + context
    'equipment': [
        r'\bmain\s+engine\b',
        r'\bgenerator\s*[#]?\d*\b',
        r'\bwatermaker\b',
        r'\bwater\s+maker\b',
        r'\bradar\b',
        r'\bflybridge\b',
        r'\bfly\s+bridge\b',
        r'\bhvac\b',
        r'\bpump\s*[#]?\d*\b',
        r'\bboiler\b',
        r'\bcompressor\b',
        r'\bautopilot\b',
        r'\bthruster\b',
        r'\bstabilizer\b',
        r'\bchiller\b',
        r'\bwinch\b',
        r'\bcrane\b',
        r'\bdavit\b',
        r'\bequipment\s+(status|details|info|list)\b',
    ],
    # part/inventory compounds - brand + part type or part-specific patterns
    'part': [
        r'\b(racor|caterpillar|volvo|mtu|yanmar|northern\s+lights|cummins|kohler)\b.*\b(filter|part|element|belt|seal)\b',
        r'\b(filter|part|element|belt|seal).*\b(racor|caterpillar|volvo|mtu|yanmar)\b',
        r'\bpart\s+number\b',
        r'\bpart\s+#?\s*[A-Z0-9-]+\b',
        r'\bspare\s+parts?\b',
        r'\b[A-Z]{2,}-\d{3,}',  # Part number patterns like CAT-12345
        r'\blow\s+stock\b',
        r'\breorder\s+(point|level)\b',
        r'\bstock\s+levels?\b',
        r'\binventory\s+(count|check|level)\b',
        r'\b(oil|fuel|air|water|hydraulic)\s+filter\b',
        # Common part types (Inventory Lens - align with term_classifier.py)
        r'\bfilters?\b',
        r'\bbearings?\b',
        r'\bgaskets?\b',
        r'\bseals?\b',
        r'\bo-rings?\b',
        r'\bbelts?\b',
        r'\bhoses?\b',
        r'\bfittings?\b',
        r'\bvalves?\b',
    ],
    # work_order compounds
    'work_order': [
        r'\bwork\s+order\b',
        r'\bworkorder\b',
        r'\bwo\s*[-#]?\s*\d*\b',
        r'\bmaintenance\s+(task|schedule|order)\b',
        r'\boverdue\s+(work|task|maintenance)\b',
        r'\bopen\s+work\s+orders?\b',
        r'\bcreate\s+work\s+order\b',
        r'\bpreventive\s+maintenance\b',
        r'\bcorrective\s+maintenance\b',
    ],
    # document compounds
    'document': [
        r'\bmanual\b',  # "manual" alone is strong signal for document
        r'\bprocedure\b',
        r'\bdocumentation\b',
        r'\bsafety\s+procedures?\b',
        r'\boperating\s+instructions?\b',
        r'\btechnical\s+doc',
        r'\bsop\b',
        r'\bschematic\b',
        r'\bdrawing\b',
    ],
    # fault compounds
    'fault': [
        r'\bopen\s+faults?\b',
        r'\bcritical\s+faults?\b',
        r'\bfault\s+(code|history|report|log)\b',
        r'\bequipment\s+fault\b',
        r'\breport\s+fault\b',
        r'\blog\s+fault\b',
        r'\bactive\s+faults?\b',
        r'\bresolved\s+faults?\b',
    ],
    # certificate compounds
    'certificate': [
        r'\bcertificate\s+(expir|renew|valid)',
        r'\bexpiring\s+cert',
        r'\bcrew\s+cert',
        r'\btraining\s+cert',
        r'\blicense\s+expir',
    ],
    # crew compounds
    'crew': [
        r'\bcrew\s+(member|profile|list|roster)\b',
        r'\bseafarer\s+(document|cert|info)\b',
        r'\bcrew\s+cert',
    ],
    # checklist compounds
    'checklist': [
        r'\bchecklist\b',
        r'\bcheck\s+list\b',
        r'\binspection\s+(form|checklist)\b',
        r'\bdeparture\s+checklist\b',
        r'\barrival\s+checklist\b',
    ],
    # handover compounds
    'handover': [
        r'\bhandover\b',
        r'\bhand\s+over\b',
        r'\bturnover\s+(report|notes)\b',
        r'\bshift\s+handover\b',
    ],
    # purchase compounds
    'purchase': [
        r'\bpurchase\s+order\b',
        r'\bpo\s*[-#]?\s*\d+\b',
        r'\bcreate\s+purchase\b',
        r'\bapprove\s+purchase\b',
    ],
    # shopping_list compounds - FIX 2026-02-08: Added shopping list domain anchors
    # HOTFIX 2026-02-09: Force rebuild - Version 2026.02.09.001
    # This enables Shopping List entity extraction (queries like "shopping list", "candidate parts")
    'shopping_list': [
        # Primary shopping list patterns
        r'\bshopping\s+list\b',
        r'\bbuy\s+list\b',
        r'\bpurchase\s+list\b',
        r'\border\s+list\b',
        # Requisition patterns (not followed by document/manual)
        r'\brequisition(?!\s+(?:form|document|manual))\b',
        r'\breq\s+list\b',
        r'\bspare\s+parts\s+list\b',
        r'\bparts\s+list(?!\s+(?:manual|document|pdf|file))\b',  # "parts list" but not "parts list manual"
        # Procurement patterns
        r'\bprocurement\s+(?:items?|list|requests?)\b',
        r'\brequested\s+parts?\b',
        r'\bparts?\s+request(?:s|ed)?\b',
        r'\bparts?\s+requisition\b',
        # Approval status in shopping list context
        r'\b(candidate|pending|approved|rejected)\s+(?:items?|parts?|list)\b',
        r'\bcandidate\s+parts?\b',
        r'\bpending\s+approval\s+list\b',
        # Shopping list specific actions
        r'\bapprove\s+(?:shopping|requisition|procurement)\b',
        r'\breject\s+(?:shopping|requisition|procurement)\b',
        r'\bpromote\s+(?:candidate|item)\s+to\s+part\b',
    ],
}

# =============================================================================
# SINGLETON KEYWORDS (weak signals - do NOT anchor domain alone)
# =============================================================================
# These words are too vague to determine domain by themselves.
# They may appear in many contexts and should not force a domain match.

SINGLETON_KEYWORDS = {
    # Generic action words
    'warning', 'warnings', 'alert', 'alerts',
    'crew', 'staff', 'team',
    'work', 'working',
    'rest', 'hrs', 'hours',  # alone without compound
    'check', 'show', 'view', 'list', 'find',
    'status', 'update', 'log',
    # Generic equipment words
    'engine', 'pump', 'system', 'machine',
    # Generic status words
    'open', 'closed', 'pending', 'completed',
    # Generic nouns
    'order', 'item', 'record', 'document',
}

# =============================================================================
# LEGACY DOMAIN KEYWORDS (kept for boost scoring, not primary detection)
# =============================================================================
# Maps keywords → (domain, boost_value)
# Used for ranking boost in fusion, NOT for domain detection

DOMAIN_KEYWORDS: Dict[str, tuple] = {
    # Hours of Rest
    'hours of rest': ('hours_of_rest', 0.30),
    'hor': ('hours_of_rest', 0.30),
    'rest hours': ('hours_of_rest', 0.25),
    'rest record': ('hours_of_rest', 0.25),
    'work hours': ('hours_of_rest', 0.20),
    'mlc': ('hours_of_rest', 0.20),
    'sign off': ('hours_of_rest', 0.20),

    # Equipment (specific types only)
    'watermaker': ('equipment', 0.30),
    'generator': ('equipment', 0.25),
    'radar': ('equipment', 0.30),
    'flybridge': ('equipment', 0.25),
    'hvac': ('equipment', 0.25),
    'boiler': ('equipment', 0.25),

    # Work Order
    'work order': ('work_order', 0.30),
    'workorder': ('work_order', 0.30),
    'maintenance': ('work_order', 0.20),

    # Fault
    'fault': ('fault', 0.30),
    'faults': ('fault', 0.30),

    # Document
    'manual': ('document', 0.35),
    'procedure': ('document', 0.20),
    'sop': ('document', 0.25),

    # Receiving
    'delivery': ('receiving', 0.30),
    'deliveries': ('receiving', 0.30),
    'shipment': ('receiving', 0.25),
    'receiving': ('receiving', 0.30),
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
    # Plurals → singular (EXCEPT parts/inventory which need plural for action registry)
    'parts': 'parts',  # Keep plural for action registry consistency (Inventory Lens)
    'part': 'parts',   # Normalize singular to plural (Inventory Lens)
    'inventory': 'parts',  # Normalize inventory to parts (Inventory Lens)
    'documents': 'document',
    'certificates': 'certificate',
    'faults': 'fault',
    'equipments': 'equipment',  # grammatically wrong but users type it
    'work_orders': 'work_order',
    'handovers': 'handover',
    'checklists': 'checklist',
    # Variants → canonical
    'crew': 'crew',  # collective noun
    'receiving': 'receiving',  # gerund
    'purchase': 'purchase',
    'shopping_list': 'shopping_list',
    'hours_of_rest': 'hours_of_rest',
}


def normalize_domain(domain: str) -> str:
    """Normalize domain to canonical form (singular for most, plural for parts/inventory)."""
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
    Detect domain from query using compound anchors.

    "No Magic Booster" Philosophy:
    - Only compound anchors (multi-word patterns) can anchor a domain
    - Singleton keywords (warning, crew, work) do NOT anchor domain alone
    - Returns (domain, confidence) where confidence determines mode:
      - confidence >= 0.6 → focused mode
      - confidence < 0.6 → explore mode (domain=None)

    Returns: (domain, confidence) or None if no anchor matches
    """
    query_lower = query.lower()

    # Check each domain's compound patterns
    matches = []
    for domain, patterns in COMPOUND_ANCHORS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                matches.append((domain, pattern))
                break  # One match per domain is enough

    if not matches:
        # No compound anchor matched - check if query is vague
        # Return None to indicate explore mode
        return None

    if len(matches) == 1:
        # Single domain matched with high confidence
        domain = normalize_domain(matches[0][0])
        return (domain, 0.9)

    # Multiple domains matched - need disambiguation
    # Priority order based on specificity
    # FIX 2026-02-08: Added shopping_list with high priority (after receiving, before hours_of_rest)
    priority = ['work_order', 'receiving', 'shopping_list', 'hours_of_rest', 'equipment', 'part', 'fault', 'document', 'certificate', 'crew', 'checklist', 'handover', 'purchase']
    for p in priority:
        for domain, _ in matches:
            if domain == p:
                return (normalize_domain(domain), 0.7)  # Lower confidence due to ambiguity

    # Fallback to first match with medium confidence
    return (normalize_domain(matches[0][0]), 0.6)


def detect_domain_with_confidence(query: str) -> Tuple[Optional[str], float]:
    """
    Detect domain and confidence from query.

    Returns: (domain, confidence) tuple
    - domain: The detected domain or None if vague/ambiguous
    - confidence: 0.0-1.0 score indicating detection certainty

    Confidence thresholds:
    - 0.9: Strong compound anchor match (single domain)
    - 0.7: Compound match with some ambiguity (multiple domains)
    - 0.6: Weak match or fallback
    - 0.0: No match (explore mode)
    """
    result = detect_domain_from_query(query)
    if result is None:
        return (None, 0.0)
    return result


def is_vague_query(query: str) -> bool:
    """
    Check if query is too vague to assign a domain.
    Vague = only singleton keywords, no compound anchors.
    """
    query_lower = query.lower()

    # Check if any compound anchor matches
    for domain, patterns in COMPOUND_ANCHORS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return False  # Has a compound anchor, not vague

    # Check if it's just singleton words
    words = set(re.findall(r'\b\w+\b', query_lower))
    stopwords = {'me', 'my', 'the', 'a', 'an', 'for', 'to', 'of', 'and', 'or', 'in', 'on', 'at', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'please', 'all', 'this', 'that', 'these', 'those', 'i'}
    meaningful_words = words - stopwords

    # If most words are singleton keywords or very short, it's vague
    if len(meaningful_words) <= 2:
        return True

    # Check how many words are singletons
    singleton_count = sum(1 for w in meaningful_words if w in SINGLETON_KEYWORDS)
    if singleton_count >= len(meaningful_words) * 0.7:
        return True

    return False


def detect_intent_from_query(query: str) -> str:
    """
    Detect intent from query text.

    Returns: intent string (default: 'READ')
    """
    result = detect_intent_with_confidence(query)
    return result[0]


# Adjective status words that mean READ + filter, not mutation
STATUS_ADJECTIVES = {
    'accepted', 'approved', 'rejected', 'draft', 'pending',
    'compliant', 'non-compliant', 'violation', 'overdue',
    'open', 'closed', 'completed', 'in progress',
}


def detect_intent_with_confidence(query: str) -> Tuple[str, float]:
    """
    Detect intent from query text with confidence score.

    Key rule: Adjective status words (accepted, draft, pending) followed by
    a noun → READ intent + status filter, NOT mutation intent.

    Returns: (intent, confidence) tuple
    """
    query_lower = query.lower()

    # Rule 1: Status adjective + noun pattern → READ with high confidence
    # Examples: "accepted deliveries", "draft receiving", "pending orders"
    status_adjective_pattern = r'\b(accepted|approved|rejected|draft|pending|open|closed|completed|overdue)\s+\w+'
    if re.search(status_adjective_pattern, query_lower):
        return ('READ', 0.95)

    # Rule 2: Acknowledge patterns → APPROVE (must check BEFORE violation rule)
    # "acknowledge rest violation", "ack violation" - user wants to acknowledge, not just view
    if re.search(r'\back(nowledge)?\s+\w+', query_lower):
        return ('APPROVE', 0.90)

    # Rule 2a: "view/show sign-off" → READ (viewing sign-off status, not signing)
    if re.search(r'\b(view|show|list|check)\s+(my\s+)?(monthly\s+)?sign[-\s]?off', query_lower):
        return ('READ', 0.90)

    # Rule 2b: Compliance/violation patterns (without acknowledge) → READ
    if re.search(r'\b(compliance|compliant|violation|non-compliant)', query_lower):
        return ('READ', 0.90)

    # Rule 3: Explicit mutation intents with explicit verbs
    explicit_mutations = {
        'CREATE': [
            r'\bcreate\s+\w+',
            r'\badd\s+(new\s+)?\w+',
            r'\bnew\s+\w+\s+(order|task|fault|item)',
            # Hours of rest logging - expanded patterns
            r'\blog\b.*\b(hours?|hrs|rest)\b',  # "log my hours", "log hrs", "i need to log rest"
            r'\b(log|record|enter)\s+(my\s+)?(hours?|hrs|rest)',  # "log my hours", "record hours"
            r'\bneed\s+to\s+log\b',  # "i need to log rest today"
            r'\breport\s+(a\s+)?(fault|issue)',
        ],
        'UPDATE': [
            r'\bupdate\s+(my\s+)?\w+',
            r'\bedit\s+\w+',
            r'\bmodify\s+\w+',
            r'\bchange\s+\w+',
            r'\bcorrect\s+\w+',
        ],
        'APPROVE': [
            # Sign-off patterns - expanded
            r'\bsign\s*off\b',
            r'\bsign[-\s]?off\s+\w+',
            r'\bsignoff\b',
            # Sign + monthly/hours/record patterns
            r'\bsign\b.*\b(monthly|hours?|hrs|record)\b',  # "sign monthly hours", "sign my monthly record"
            r'\bpls\s+sign\b',  # "pls sign my monthly hrs"
            r'\bwho\s+needs?\s+to\s+sign\b',  # "who needs to sign their monthly hours"
            r'\bapprove\s+\w+',
            r'\baccept\s+(the\s+)?(delivery|order)',  # verb accept, not adjective
            # Acknowledge patterns
            r'\back(nowledge)?\s+\w+',  # "acknowledge rest violation", "ack violation"
        ],
        'DELETE': [
            r'\bdelete\s+\w+',
            r'\bremove\s+\w+',
            r'\bcancel\s+\w+',
        ],
        'EXPORT': [
            r'\bexport\s+\w+',
            r'\bdownload\s+\w+',
            r'\bprint\s+\w+',
            r'\bgenerate\s+report',
        ],
    }

    for intent, patterns in explicit_mutations.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                return (intent, 0.85)

    # Rule 4: Question patterns → READ
    if re.search(r'^(what|where|how|when|which|who|show|find|list|check|see)\b', query_lower):
        return ('READ', 0.85)

    # Rule 5: "details" or "manual" or similar → READ
    if re.search(r'\b(details|manual|info|information|status|history)\b', query_lower):
        if not re.search(r'\b(create|add|new|update|edit)\b', query_lower):
            return ('READ', 0.80)

    # Default to READ with lower confidence
    return ('READ', 0.70)


def extract_filters_from_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Extract structured filters from query for p_filters parameter.

    Returns dict with filter keys or None if no filters detected.
    Supports:
    - status: accepted, draft, rejected, pending
    - compliance_state: compliant, violation
    """
    query_lower = query.lower()
    filters = {}

    # Status filters for receiving domain
    if re.search(r'\b(accepted?|approved?)\s+(deliver|receiving)', query_lower):
        filters['status'] = 'accepted'
    elif re.search(r'\bdraft\s+(deliver|receiving)', query_lower):
        filters['status'] = 'draft'
    elif re.search(r'\b(rejected?|declined?)\s+(deliver|receiving)', query_lower):
        filters['status'] = 'rejected'
    elif re.search(r'\bpending\s+(deliver|receiving)', query_lower):
        filters['status'] = 'pending'

    # Compliance filters for hours_of_rest domain
    if re.search(r'\bviolation', query_lower):
        filters['compliance_state'] = 'violation'
    elif re.search(r'\bnon[- ]?compliant', query_lower):
        filters['compliance_state'] = 'violation'
    elif re.search(r'\bcompliant\b', query_lower):
        filters['compliance_state'] = 'compliant'

    # Work order / fault status
    if re.search(r'\bopen\s+(work\s+orders?|faults?|tasks?)', query_lower):
        filters['status'] = 'open'
    elif re.search(r'\bclosed\s+(work\s+orders?|faults?|tasks?)', query_lower):
        filters['status'] = 'closed'
    elif re.search(r'\boverdue\s+(work\s+orders?|tasks?|maintenance)', query_lower):
        filters['status'] = 'overdue'

    return filters if filters else None


def get_detection_context(query: str) -> Dict[str, Any]:
    """
    Get full detection context for API response.

    Returns a dict with:
    - domain: detected domain or None
    - domain_confidence: 0.0-1.0
    - intent: detected intent
    - intent_confidence: 0.0-1.0
    - mode: 'focused' or 'explore'
    - filters: extracted filters or None
    - is_vague: whether query is too vague for domain assignment
    """
    # Detect domain with confidence
    domain, domain_confidence = detect_domain_with_confidence(query)

    # Detect intent with confidence
    intent, intent_confidence = detect_intent_with_confidence(query)

    # Extract filters
    filters = extract_filters_from_query(query)

    # Determine mode based on confidence threshold
    CONFIDENCE_THRESHOLD = 0.4  # Lowered from 0.6 to reduce accidental explore mode
    if domain and domain_confidence >= CONFIDENCE_THRESHOLD:
        mode = 'focused'
    else:
        mode = 'explore'
        # If below threshold, set domain to None for explore mode
        if domain_confidence < CONFIDENCE_THRESHOLD:  # Below 0.4 → explore mode
            domain = None
            domain_confidence = 0.0

    # Check if query is vague
    vague = is_vague_query(query)

    return {
        'domain': domain,
        'domain_confidence': domain_confidence,
        'intent': intent,
        'intent_confidence': intent_confidence,
        'mode': mode,
        'filters': filters,
        'is_vague': vague,
    }


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


# HOTFIX 2026-02-09: Module load verification - This prints when module is imported
# Check Render logs for this message to confirm new code loaded
print(f"[ENTITY_EXTRACTION_LOADED] v{ENTITY_EXTRACTION_VERSION} | shopping_list_patterns={len(COMPOUND_ANCHORS.get('shopping_list', []))}")
