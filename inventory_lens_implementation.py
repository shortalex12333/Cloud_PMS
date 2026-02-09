# ============================================================================
# INVENTORY ITEM LENS - COMPLETE BACKEND IMPLEMENTATION
# ============================================================================

"""
File 1: apps/api/prepare/capability_composer.py

Add these entity type mappings to ENTITY_TO_SEARCH_COLUMN dictionary (line 113):
"""

# EXISTING (keep these):
"LOCATION": ("inventory_by_location", "location"),
"STOCK_QUERY": ("inventory_by_location", "name"),

# ADD THESE NEW INVENTORY ENTITY TYPES:
"STOCK_STATUS": ("inventory_by_stock_status", "quantity_on_hand"),  # Low/Out of stock searches
"REORDER_NEEDED": ("inventory_by_stock_status", "quantity_on_hand"),  # Parts below minimum
"CRITICAL_PART": ("inventory_by_location", "is_critical"),  # Critical parts flag
"RECENT_USAGE": ("inventory_by_recent_usage", "used_at"),  # Recently consumed parts
"PART_CATEGORY": ("inventory_by_location", "category"),  # Category-based inventory search
"LOW_STOCK": ("inventory_by_stock_status", "quantity_on_hand"),  # Alias for stock status
"OUT_OF_STOCK": ("inventory_by_stock_status", "quantity_on_hand"),  # Alias for stock status

# ============================================================================
# File 2: apps/api/execute/table_capabilities.py
#
# Update the existing inventory_by_location capability and add new one:
# ============================================================================

"inventory_by_location": Capability(
    name="inventory_by_location",
    description="Search inventory stock by location, category, or critical status",
    status=CapabilityStatus.ACTIVE,
    entity_triggers=[
        "LOCATION",
        "STOCK_QUERY",
        "CRITICAL_PART",  # NEW
        "PART_CATEGORY",   # NEW
    ],
    available_actions=[
        "check_stock_level",
        "log_part_usage",
        "receive_part",
        "consume_part",
        "transfer_part",
        "adjust_stock_quantity",
        "create_shopping_list_item"
    ],
    tables=[
        TableSpec(
            name="pms_parts",
            yacht_id_column="yacht_id",
            primary_key="id",
            searchable_columns=[
                SearchableColumn(
                    name="name",
                    match_types=[MatchType.ILIKE, MatchType.TRIGRAM],
                    description="Part name",
                    is_primary=True,
                ),
                SearchableColumn(
                    name="location",
                    match_types=[MatchType.ILIKE, MatchType.EXACT],
                    description="Storage location (e.g., Engine Room, Deck Store)",
                ),
                SearchableColumn(
                    name="category",
                    match_types=[MatchType.EXACT, MatchType.ILIKE],
                    description="Part category",
                ),
                SearchableColumn(
                    name="part_number",
                    match_types=[MatchType.ILIKE, MatchType.EXACT],
                    description="Part number",
                ),
                SearchableColumn(
                    name="manufacturer",
                    match_types=[MatchType.ILIKE],
                    description="Part manufacturer",
                ),
                SearchableColumn(
                    name="description",
                    match_types=[MatchType.ILIKE, MatchType.TRIGRAM],
                    description="Part description text",
                ),
            ],
            response_columns=[
                "id", "part_number", "name", "manufacturer",
                "category", "description", "model_compatibility",
                "quantity_on_hand", "minimum_quantity", "location",
                "unit", "last_counted_at", "last_counted_by"
            ],
        ),
    ],
),

# NEW CAPABILITY FOR STOCK STATUS SEARCHES
"inventory_by_stock_status": Capability(
    name="inventory_by_stock_status",
    description="Search inventory by stock status (low stock, out of stock, reorder needed)",
    status=CapabilityStatus.ACTIVE,
    entity_triggers=[
        "STOCK_STATUS",
        "REORDER_NEEDED",
        "LOW_STOCK",
        "OUT_OF_STOCK",
    ],
    available_actions=[
        "check_stock_level",
        "create_shopping_list_item",
        "receive_part",
        "adjust_stock_quantity",
    ],
    tables=[
        TableSpec(
            name="pms_parts",
            yacht_id_column="yacht_id",
            primary_key="id",
            # Special handling: Filter WHERE quantity_on_hand <= minimum_quantity
            # This is handled in capability_executor with custom SQL generation
            searchable_columns=[
                SearchableColumn(
                    name="quantity_on_hand",
                    match_types=[MatchType.NUMERIC_RANGE],
                    description="Current stock quantity",
                    is_primary=True,
                ),
                SearchableColumn(
                    name="minimum_quantity",
                    match_types=[MatchType.NUMERIC_RANGE],
                    description="Minimum stock threshold",
                ),
                SearchableColumn(
                    name="name",
                    match_types=[MatchType.ILIKE],
                    description="Part name for filtering",
                ),
                SearchableColumn(
                    name="category",
                    match_types=[MatchType.EXACT, MatchType.ILIKE],
                    description="Part category",
                ),
            ],
            response_columns=[
                "id", "part_number", "name", "manufacturer",
                "category", "quantity_on_hand", "minimum_quantity",
                "location", "unit", "last_counted_at"
            ],
        ),
    ],
),

# NEW CAPABILITY FOR RECENT USAGE
"inventory_by_recent_usage": Capability(
    name="inventory_by_recent_usage",
    description="Search parts by recent usage/consumption",
    status=CapabilityStatus.ACTIVE,
    entity_triggers=["RECENT_USAGE"],
    available_actions=[
        "check_stock_level",
        "view_part_details",
        "log_part_usage",
    ],
    tables=[
        TableSpec(
            name="pms_part_usage",
            yacht_id_column="yacht_id",
            primary_key="id",
            searchable_columns=[
                SearchableColumn(
                    name="used_at",
                    match_types=[MatchType.DATE_RANGE],
                    description="Date part was used",
                    is_primary=True,
                ),
                SearchableColumn(
                    name="usage_reason",
                    match_types=[MatchType.EXACT, MatchType.ILIKE],
                    description="Reason for usage",
                ),
            ],
            response_columns=[
                "id", "part_id", "quantity", "used_at", "used_by",
                "usage_reason", "work_order_id", "equipment_id", "notes"
            ],
        ),
    ],
),

# ============================================================================
# File 3: apps/api/pipeline_v1.py
#
# Add entity type translation for Inventory Lens (around line 240)
# ============================================================================

def _translate_entity_types_for_frontend(self, entities: List[Dict]) -> List[Dict]:
    """
    Translate Lens extraction types to frontend domain types.

    Maps backend normalized types to frontend-expected types.
    Preserves original extraction_type for debugging.
    """
    BACKEND_TO_FRONTEND = {
        # Parts & Inventory → 'part' or 'inventory' based on context
        'PART_NUMBER': 'part',
        'PART_NAME': 'part',
        'MANUFACTURER': 'part',

        # Inventory-specific → 'inventory'
        'LOCATION': 'inventory',
        'STOCK_QUERY': 'inventory',
        'STOCK_STATUS': 'inventory',
        'REORDER_NEEDED': 'inventory',
        'CRITICAL_PART': 'inventory',
        'RECENT_USAGE': 'inventory',
        'PART_CATEGORY': 'inventory',
        'LOW_STOCK': 'inventory',
        'OUT_OF_STOCK': 'inventory',

        # Equipment
        'EQUIPMENT_NAME': 'equipment',
        'MODEL_NUMBER': 'equipment',
        'SYSTEM_NAME': 'equipment',
        'COMPONENT_NAME': 'equipment',
        'EQUIPMENT_TYPE': 'equipment',

        # Faults
        'FAULT_CODE': 'fault',
        'SYMPTOM': 'fault',

        # Work Orders
        'WORK_ORDER_ID': 'work_order',
        'WO_NUMBER': 'work_order',

        # Documents
        'DOCUMENT_QUERY': 'document',
        'MANUAL_SEARCH': 'document',
        'PROCEDURE_SEARCH': 'document',
        'EMAIL_SUBJECT': 'email_thread',
        'EMAIL_SEARCH': 'email_thread',
    }

    for entity in entities:
        extraction_type = entity.get('type', '')
        entity['extraction_type'] = extraction_type  # Preserve original for debugging
        entity['type'] = BACKEND_TO_FRONTEND.get(extraction_type, extraction_type)
        entity['display_type'] = entity['type']  # Add display_type for UI

    return entities

# Insert this function call in the search pipeline (around line 280):
# After entity extraction, before returning response:

# Stage 2: Translate entity types for frontend compatibility
entities_translated = self._translate_entity_types_for_frontend(
    extracted_result.get('entities', [])
)

# ============================================================================
# File 4: apps/api/execute/capability_executor.py
#
# Add special handling for stock status searches
# ============================================================================

def _build_stock_status_query(
    self,
    table_name: str,
    entity_type: str,
    entity_value: str,
    yacht_id: str,
    limit: int
) -> str:
    """
    Build custom query for stock status searches.

    Handles: LOW_STOCK, OUT_OF_STOCK, REORDER_NEEDED, STOCK_STATUS
    """
    base_query = f"""
        SELECT id, part_number, name, manufacturer, category,
               quantity_on_hand, minimum_quantity, location, unit,
               last_counted_at, last_counted_by
        FROM {table_name}
        WHERE yacht_id = '{yacht_id}'
    """

    if entity_type == 'OUT_OF_STOCK':
        base_query += " AND quantity_on_hand = 0"
    elif entity_type in ('LOW_STOCK', 'REORDER_NEEDED'):
        base_query += " AND quantity_on_hand > 0 AND quantity_on_hand <= minimum_quantity"
    elif entity_type == 'STOCK_STATUS':
        # Parse entity_value: "low", "out", "critical"
        if entity_value.lower() in ('low', 'low stock'):
            base_query += " AND quantity_on_hand > 0 AND quantity_on_hand <= minimum_quantity"
        elif entity_value.lower() in ('out', 'out of stock', 'zero'):
            base_query += " AND quantity_on_hand = 0"
        elif entity_value.lower() in ('critical', 'urgent'):
            base_query += " AND quantity_on_hand = 0"

    base_query += f" ORDER BY quantity_on_hand ASC, name ASC LIMIT {limit}"

    return base_query
