"""
TABLE_CAPABILITIES v1 - Contract-Driven Execution Layer
========================================================

This registry defines the EXACT mapping from:
  intent → capability_class → tables → searchable_columns → match_types

RULES:
1. Every capability must have at least one table with yacht_id column
2. Every column referenced must exist in schema_snapshot.json
3. Match types must be one of: exact, ilike, trigram, numeric_range, date_range, rpc, vector
4. No joins in v1 - single table queries only
5. yacht_id is ALWAYS required in WHERE clause (enforced at execution)

VALIDATION:
  Run: python -m api.table_capabilities --validate
  This checks all columns exist in docs/schema_snapshot.json
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


class MatchType(Enum):
    """How to match a search term against a column."""
    EXACT = "exact"           # WHERE col = $value (case-sensitive)
    ILIKE = "ilike"           # WHERE col ILIKE '%' || $value || '%'
    TRIGRAM = "trigram"       # WHERE col % $value (requires pg_trgm)
    NUMERIC_RANGE = "numeric_range"  # WHERE col >= $min AND col <= $max
    DATE_RANGE = "date_range"        # WHERE col >= $start AND col <= $end
    RPC = "rpc"               # Call a Supabase RPC function
    VECTOR = "vector"         # Vector similarity search (requires pgvector)


class CapabilityStatus(Enum):
    """Whether this capability can be used in production."""
    ACTIVE = "active"         # Table has data, ready to use
    EMPTY = "empty"           # Table exists but has no data
    MISSING = "missing"       # Table doesn't exist in schema
    DEPRECATED = "deprecated" # Capability is being phased out


@dataclass
class SearchableColumn:
    """A column that can be searched, with its match strategy."""
    name: str
    match_types: List[MatchType]
    description: str = ""
    # If true, this column is the primary search target for this capability
    is_primary: bool = False
    # For numeric/date ranges, the min/max bounds
    bounds: Optional[Dict[str, Any]] = None


@dataclass
class TableSpec:
    """Specification for a table in a capability."""
    name: str
    yacht_id_column: str = "yacht_id"  # Column name for yacht isolation
    primary_key: str = "id"
    searchable_columns: List[SearchableColumn] = field(default_factory=list)
    # Columns to include in response (SELECT clause)
    response_columns: List[str] = field(default_factory=list)
    # For RPC-based tables, the function name
    rpc_function: Optional[str] = None


@dataclass
class Capability:
    """A capability class that maps intent to execution."""
    name: str
    description: str
    status: CapabilityStatus
    tables: List[TableSpec]
    # Entity types that trigger this capability (from extraction)
    entity_triggers: List[str] = field(default_factory=list)
    # Actions that can be taken on results
    available_actions: List[str] = field(default_factory=list)
    # Why this capability is blocked (if status != ACTIVE)
    blocked_reason: Optional[str] = None


# =============================================================================
# CAPABILITY REGISTRY v1
# =============================================================================

TABLE_CAPABILITIES: Dict[str, Capability] = {

    # =========================================================================
    # ACTIVE CAPABILITIES (tables have data)
    # =========================================================================

    "part_by_part_number_or_name": Capability(
        name="part_by_part_number_or_name",
        description="Search for parts by part number, name, manufacturer, or category",
        status=CapabilityStatus.ACTIVE,
        entity_triggers=["PART_NUMBER", "PART_NAME", "MANUFACTURER"],
        available_actions=["receive_part", "consume_part", "view_details", "check_stock", "order_part"],
        tables=[
            TableSpec(
                name="pms_parts",
                yacht_id_column="yacht_id",
                primary_key="id",
                searchable_columns=[
                    SearchableColumn(
                        name="part_number",
                        match_types=[MatchType.ILIKE, MatchType.EXACT],  # ILIKE first for partial matches
                        description="Manufacturer part number (e.g., ENG-0008-103)",
                        is_primary=True,
                    ),
                    SearchableColumn(
                        name="name",
                        match_types=[MatchType.ILIKE, MatchType.TRIGRAM],
                        description="Part name (e.g., Fuel Injector Nozzle)",
                        is_primary=True,
                    ),
                    SearchableColumn(
                        name="manufacturer",
                        match_types=[MatchType.ILIKE],
                        description="Manufacturer name (e.g., MTU, Caterpillar)",
                    ),
                    SearchableColumn(
                        name="category",
                        match_types=[MatchType.EXACT, MatchType.ILIKE],
                        description="Part category (e.g., Interior, Engine)",
                    ),
                    SearchableColumn(
                        name="description",
                        match_types=[MatchType.ILIKE, MatchType.TRIGRAM],
                        description="Part description text",
                    ),
                ],
                response_columns=[
                    "id", "part_number", "name", "manufacturer",
                    "category", "description", "model_compatibility"
                ],
            ),
        ],
    ),

    "inventory_by_location": Capability(
        name="inventory_by_location",
        description="Search inventory stock by location, quantity, or reorder status",
        status=CapabilityStatus.ACTIVE,
        entity_triggers=["LOCATION", "STOCK_QUERY"],
        available_actions=["view_stock", "reorder", "transfer_stock", "adjust_quantity"],
        tables=[
            # NOTE: v_inventory VIEW may not exist on all deployments
            # Fallback to pms_parts which is confirmed to exist
            TableSpec(
                name="pms_parts",  # CONFIRMED EXISTS - use parts table directly
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
                        name="category",
                        match_types=[MatchType.EXACT, MatchType.ILIKE],
                        description="Part category",
                    ),
                    SearchableColumn(
                        name="description",
                        match_types=[MatchType.ILIKE, MatchType.TRIGRAM],
                        description="Part description text",
                    ),
                ],
                response_columns=[
                    "id", "part_number", "name", "manufacturer",
                    "category", "description", "model_compatibility"
                ],
            ),
        ],
    ),

    "fault_by_fault_code": Capability(
        name="fault_by_fault_code",
        description="Search fault codes by code, name, symptoms, or equipment type",
        status=CapabilityStatus.ACTIVE,
        entity_triggers=["FAULT_CODE", "SYMPTOM", "EQUIPMENT_TYPE"],
        available_actions=["view_details", "start_diagnostic", "log_fault", "view_resolution"],
        tables=[
            TableSpec(
                name="search_fault_code_catalog",
                yacht_id_column="yacht_id",
                primary_key="id",
                searchable_columns=[
                    SearchableColumn(
                        name="code",
                        match_types=[MatchType.ILIKE, MatchType.EXACT],  # ILIKE first for partial/case-insensitive
                        description="Fault code (e.g., 1234, E047)",
                        is_primary=True,
                    ),
                    SearchableColumn(
                        name="name",
                        match_types=[MatchType.ILIKE, MatchType.TRIGRAM],
                        description="Fault name (e.g., Low Fuel Pressure)",
                        is_primary=True,
                    ),
                    SearchableColumn(
                        name="equipment_type",
                        match_types=[MatchType.ILIKE],
                        description="Equipment type (e.g., Caterpillar 3208)",
                    ),
                    SearchableColumn(
                        name="manufacturer",
                        match_types=[MatchType.ILIKE],
                        description="Equipment manufacturer",
                    ),
                    SearchableColumn(
                        name="severity",
                        match_types=[MatchType.EXACT],
                        description="Severity level (warning, critical, etc.)",
                    ),
                ],
                response_columns=[
                    "id", "code", "name", "equipment_type", "manufacturer",
                    "severity", "symptoms", "causes", "diagnostic_steps",
                    "resolution_steps", "related_parts"
                ],
            ),
        ],
    ),

    "documents_search": Capability(
        name="documents_search",
        description="Search document chunks by content or metadata",
        status=CapabilityStatus.ACTIVE,
        entity_triggers=["DOCUMENT_QUERY", "MANUAL_SEARCH", "PROCEDURE_SEARCH"],
        available_actions=["view_document", "download_pdf", "extract_procedure"],
        tables=[
            TableSpec(
                name="search_document_chunks",
                yacht_id_column="yacht_id",
                primary_key="id",
                # NOTE: unified_search_v2 requires embeddings (not available in fallback)
                # Use unified_search_simple for text-only search fallback
                # rpc_function="unified_search_simple" can be enabled if needed
                # Using SQL fallback with ILIKE on content column for now
                searchable_columns=[
                    SearchableColumn(
                        name="content",
                        match_types=[MatchType.ILIKE],
                        description="Document text content",
                        is_primary=True,
                    ),
                    SearchableColumn(
                        name="section_title",
                        match_types=[MatchType.ILIKE],
                        description="Document section title",
                    ),
                    SearchableColumn(
                        name="doc_type",
                        match_types=[MatchType.EXACT],
                        description="Document type classification",
                    ),
                    SearchableColumn(
                        name="system_tag",
                        match_types=[MatchType.EXACT, MatchType.ILIKE],
                        description="System tag for filtering",
                    ),
                ],
                response_columns=[
                    "id", "document_id", "content", "section_title",
                    "page_number", "doc_type", "system_tag",
                    "metadata"
                ],
            ),
        ],
    ),

    # =========================================================================
    # GRAPH CAPABILITIES (for entity resolution)
    # =========================================================================

    "graph_node_search": Capability(
        name="graph_node_search",
        description="Search knowledge graph nodes by label or type",
        status=CapabilityStatus.ACTIVE,
        entity_triggers=["ENTITY_LOOKUP", "SYSTEM_NAME", "COMPONENT_NAME"],
        available_actions=["view_node", "view_connections", "expand_graph"],
        tables=[
            TableSpec(
                name="graph_nodes",
                yacht_id_column="yacht_id",
                primary_key="id",
                searchable_columns=[
                    SearchableColumn(
                        name="label",
                        match_types=[MatchType.ILIKE, MatchType.TRIGRAM],
                        description="Node label (e.g., fuel_system)",
                        is_primary=True,
                    ),
                    SearchableColumn(
                        name="normalized_label",
                        match_types=[MatchType.EXACT, MatchType.ILIKE],
                        description="Normalized/canonical label",
                    ),
                    SearchableColumn(
                        name="node_type",
                        match_types=[MatchType.EXACT],
                        description="Node type (system, component, part, etc.)",
                    ),
                ],
                response_columns=[
                    "id", "label", "normalized_label", "node_type",
                    "properties", "confidence", "extraction_source"
                ],
            ),
        ],
    ),

    # =========================================================================
    # BLOCKED CAPABILITIES (tables empty or missing)
    # =========================================================================

    "work_order_by_id": Capability(
        name="work_order_by_id",
        description="Search work orders by ID, status, or equipment",
        status=CapabilityStatus.ACTIVE,
        blocked_reason=None,
        entity_triggers=["WORK_ORDER_ID", "WO_NUMBER"],
        available_actions=["view_details", "update_status", "assign_crew", "close_order"],
        tables=[
            TableSpec(
                name="pms_work_orders",
                yacht_id_column="yacht_id",
                primary_key="id",
                searchable_columns=[
                    SearchableColumn(
                        name="wo_number",
                        match_types=[MatchType.EXACT],
                        description="Work order number",
                        is_primary=True,
                    ),
                    SearchableColumn(
                        name="status",
                        match_types=[MatchType.EXACT],
                        description="Work order status",
                    ),
                ],
                response_columns=["id", "wo_number", "status", "title", "description"],
            ),
        ],
    ),

    "equipment_by_name_or_model": Capability(
        name="equipment_by_name_or_model",
        description="Search equipment by name, model, or manufacturer",
        status=CapabilityStatus.ACTIVE,
        blocked_reason=None,
        entity_triggers=["EQUIPMENT_NAME", "MODEL_NUMBER"],
        available_actions=["view_details", "view_maintenance", "log_hours"],
        tables=[
            TableSpec(
                name="pms_equipment",
                yacht_id_column="yacht_id",
                primary_key="id",
                searchable_columns=[
                    SearchableColumn(
                        name="name",
                        match_types=[MatchType.ILIKE, MatchType.TRIGRAM],
                        description="Equipment name",
                        is_primary=True,
                    ),
                    SearchableColumn(
                        name="model",
                        match_types=[MatchType.ILIKE],
                        description="Equipment model",
                    ),
                ],
                response_columns=["id", "name", "model", "manufacturer", "serial_number"],
            ),
        ],
    ),

    # =========================================================================
    # EMAIL TRANSPORT LAYER - Evidence Search
    # =========================================================================

    "email_threads_search": Capability(
        name="email_threads_search",
        description="Search email threads by subject (supporting evidence for operational objects)",
        status=CapabilityStatus.ACTIVE,
        blocked_reason=None,
        entity_triggers=["EMAIL_SUBJECT", "EMAIL_SEARCH"],
        available_actions=["view_thread", "link_to_object"],
        tables=[
            TableSpec(
                name="email_threads",
                yacht_id_column="yacht_id",
                primary_key="id",
                searchable_columns=[
                    SearchableColumn(
                        name="latest_subject",
                        match_types=[MatchType.ILIKE, MatchType.TRIGRAM],
                        description="Email thread subject line",
                        is_primary=True,
                    ),
                ],
                response_columns=[
                    "id", "latest_subject", "message_count", "has_attachments",
                    "source", "first_message_at", "last_activity_at"
                ],
            ),
        ],
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_active_capabilities() -> Dict[str, Capability]:
    """Return only capabilities that are ACTIVE (have data)."""
    return {
        k: v for k, v in TABLE_CAPABILITIES.items()
        if v.status == CapabilityStatus.ACTIVE
    }


def get_capability_for_entity(entity_type: str) -> Optional[Capability]:
    """Find the capability that handles a given entity type."""
    for cap in TABLE_CAPABILITIES.values():
        if entity_type in cap.entity_triggers:
            if cap.status == CapabilityStatus.ACTIVE:
                return cap
    return None


def get_tables_for_capability(capability_name: str) -> List[str]:
    """Get list of table names for a capability."""
    cap = TABLE_CAPABILITIES.get(capability_name)
    if not cap:
        return []
    return [t.name for t in cap.tables]


def validate_against_schema(schema_path: str = "docs/schema_snapshot.json") -> Dict[str, Any]:
    """
    Validate TABLE_CAPABILITIES against the live schema snapshot.
    Returns a dict with validation results.
    """
    import json
    import os

    # Find schema file relative to this file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base_dir, schema_path)

    if not os.path.exists(full_path):
        return {
            "valid": False,
            "error": f"Schema file not found: {full_path}",
            "missing_tables": [],
            "missing_columns": [],
        }

    with open(full_path) as f:
        schema = json.load(f)

    schema_tables = schema.get("tables", {})

    results = {
        "valid": True,
        "missing_tables": [],
        "missing_columns": [],
        "validated_capabilities": [],
        "blocked_capabilities": [],
    }

    for cap_name, cap in TABLE_CAPABILITIES.items():
        if cap.status != CapabilityStatus.ACTIVE:
            results["blocked_capabilities"].append({
                "name": cap_name,
                "status": cap.status.value,
                "reason": cap.blocked_reason,
            })
            continue

        cap_valid = True
        for table_spec in cap.tables:
            table_name = table_spec.name

            # Check table exists
            if table_name not in schema_tables:
                results["missing_tables"].append({
                    "capability": cap_name,
                    "table": table_name,
                })
                cap_valid = False
                continue

            schema_columns = set(schema_tables[table_name].get("columns", {}).keys())

            # Check yacht_id column exists
            if table_spec.yacht_id_column not in schema_columns:
                results["missing_columns"].append({
                    "capability": cap_name,
                    "table": table_name,
                    "column": table_spec.yacht_id_column,
                    "type": "yacht_id",
                })
                cap_valid = False

            # Check searchable columns exist
            for col in table_spec.searchable_columns:
                if col.name not in schema_columns:
                    results["missing_columns"].append({
                        "capability": cap_name,
                        "table": table_name,
                        "column": col.name,
                        "type": "searchable",
                    })
                    cap_valid = False

            # Check response columns exist
            for col_name in table_spec.response_columns:
                if col_name not in schema_columns:
                    results["missing_columns"].append({
                        "capability": cap_name,
                        "table": table_name,
                        "column": col_name,
                        "type": "response",
                    })
                    cap_valid = False

        if cap_valid:
            results["validated_capabilities"].append(cap_name)
        else:
            results["valid"] = False

    return results


# =============================================================================
# CLI VALIDATION
# =============================================================================

if __name__ == "__main__":
    import sys
    import json

    if "--validate" in sys.argv:
        print("=" * 60)
        print("TABLE_CAPABILITIES VALIDATION")
        print("=" * 60)

        results = validate_against_schema()

        print(f"\nValid: {results['valid']}")
        print(f"Validated capabilities: {len(results['validated_capabilities'])}")
        print(f"Blocked capabilities: {len(results['blocked_capabilities'])}")

        if results["validated_capabilities"]:
            print("\n✓ Active capabilities:")
            for cap in results["validated_capabilities"]:
                print(f"  - {cap}")

        if results["blocked_capabilities"]:
            print("\n⚠ Blocked capabilities:")
            for cap in results["blocked_capabilities"]:
                print(f"  - {cap['name']}: {cap['status']} ({cap['reason']})")

        if results["missing_tables"]:
            print("\n✗ Missing tables:")
            for item in results["missing_tables"]:
                print(f"  - {item['capability']}: table '{item['table']}' not in schema")

        if results["missing_columns"]:
            print("\n✗ Missing columns:")
            for item in results["missing_columns"]:
                print(f"  - {item['capability']}.{item['table']}: column '{item['column']}' ({item['type']})")

        print()
        sys.exit(0 if results["valid"] else 1)

    else:
        print("Usage: python -m api.table_capabilities --validate")
        print("\nAvailable capabilities:")
        for name, cap in TABLE_CAPABILITIES.items():
            status_icon = "✓" if cap.status == CapabilityStatus.ACTIVE else "✗"
            print(f"  {status_icon} {name}: {cap.description}")
