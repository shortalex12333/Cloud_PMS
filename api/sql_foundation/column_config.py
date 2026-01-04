"""
SQL FOUNDATION — COLUMN CAPABILITY CONTRACT
============================================
This is the ONLY place column metadata lives.
If it's not declared here, it's not searchable.

Pilot tables: pms_parts, v_inventory, pms_faults, search_fault_code_catalog, graph_nodes
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from .operators import Operator

@dataclass
class ColumnCapability:
    """What a column can do."""
    name: str
    datatype: str
    operators: List[Operator]
    entity_types: List[str]
    isolated_ok: bool  # Can be queried alone
    conjunction_only: bool  # Requires another entity
    select_default: bool = True  # Include in default SELECT
    json_keys: Optional[List[str]] = None  # For JSONB columns

@dataclass
class TableCapability:
    """Complete capability declaration for a table."""
    name: str
    yacht_id_column: str
    primary_key: str
    columns: Dict[str, ColumnCapability]
    default_select: List[str]
    default_limit: int = 50
    default_order: Optional[str] = None
    required_filters: List[str] = field(default_factory=lambda: ["yacht_id"])

# =============================================================================
# PILOT TABLES — COMPLETE CAPABILITY DECLARATIONS
# =============================================================================

TABLES: Dict[str, TableCapability] = {}

# -----------------------------------------------------------------------------
# pms_parts (250 rows)
# -----------------------------------------------------------------------------
TABLES["pms_parts"] = TableCapability(
    name="pms_parts",
    yacht_id_column="yacht_id",
    primary_key="id",
    default_select=["id", "part_number", "name", "manufacturer", "category", "description"],
    default_limit=50,
    columns={
        "part_number": ColumnCapability(
            name="part_number",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE],
            entity_types=["PART_NUMBER"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "name": ColumnCapability(
            name="name",
            datatype="text",
            operators=[Operator.ILIKE, Operator.TRIGRAM],
            entity_types=["PART_NAME", "FREE_TEXT"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "manufacturer": ColumnCapability(
            name="manufacturer",
            datatype="text",
            operators=[Operator.ILIKE],
            entity_types=["MANUFACTURER"],
            isolated_ok=False,
            conjunction_only=True
        ),
        "description": ColumnCapability(
            name="description",
            datatype="text",
            operators=[Operator.ILIKE, Operator.TRIGRAM],
            entity_types=["DESCRIPTION", "FREE_TEXT"],
            isolated_ok=False,
            conjunction_only=True
        ),
        "category": ColumnCapability(
            name="category",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE],
            entity_types=["SYSTEM_NAME", "LOCATION"],
            isolated_ok=True,
            conjunction_only=False
        ),
    }
)

# -----------------------------------------------------------------------------
# pms_equipment (15 rows)
# -----------------------------------------------------------------------------
TABLES["pms_equipment"] = TableCapability(
    name="pms_equipment",
    yacht_id_column="yacht_id",
    primary_key="id",
    default_select=["id", "name", "code", "manufacturer", "serial_number", "system_type", "location"],
    default_limit=50,
    columns={
        "name": ColumnCapability(
            name="name",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE, Operator.TRIGRAM],
            entity_types=["EQUIPMENT_NAME", "FREE_TEXT"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "code": ColumnCapability(
            name="code",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE],
            entity_types=["EQUIPMENT_CODE"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "manufacturer": ColumnCapability(
            name="manufacturer",
            datatype="text",
            operators=[Operator.ILIKE],
            entity_types=["MANUFACTURER"],
            isolated_ok=False,
            conjunction_only=True
        ),
        "serial_number": ColumnCapability(
            name="serial_number",
            datatype="text",
            operators=[Operator.EXACT],
            entity_types=["SERIAL_NUMBER"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "system_type": ColumnCapability(
            name="system_type",
            datatype="text",
            operators=[Operator.EXACT],
            entity_types=["SYSTEM_NAME"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "location": ColumnCapability(
            name="location",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE],
            entity_types=["LOCATION"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "model": ColumnCapability(
            name="model",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE],
            entity_types=["MODEL"],
            isolated_ok=False,
            conjunction_only=True
        ),
        "criticality": ColumnCapability(
            name="criticality",
            datatype="text",
            operators=[Operator.EXACT],
            entity_types=["PRIORITY"],
            isolated_ok=True,
            conjunction_only=False
        ),
    }
)

# -----------------------------------------------------------------------------
# pms_faults (8 rows)
# -----------------------------------------------------------------------------
TABLES["pms_faults"] = TableCapability(
    name="pms_faults",
    yacht_id_column="yacht_id",
    primary_key="id",
    default_select=["id", "fault_code", "title", "severity", "description"],
    default_limit=50,
    columns={
        "fault_code": ColumnCapability(
            name="fault_code",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE],
            entity_types=["FAULT_CODE"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "title": ColumnCapability(
            name="title",
            datatype="text",
            operators=[Operator.ILIKE, Operator.TRIGRAM],
            entity_types=["SYMPTOM", "DESCRIPTION"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "description": ColumnCapability(
            name="description",
            datatype="text",
            operators=[Operator.ILIKE, Operator.TRIGRAM],
            entity_types=["DESCRIPTION", "FREE_TEXT"],
            isolated_ok=False,
            conjunction_only=True
        ),
        "severity": ColumnCapability(
            name="severity",
            datatype="text",
            operators=[Operator.EXACT],
            entity_types=["SEVERITY"],
            isolated_ok=True,
            conjunction_only=False
        ),
    }
)

# -----------------------------------------------------------------------------
# search_fault_code_catalog (2 rows)
# -----------------------------------------------------------------------------
TABLES["search_fault_code_catalog"] = TableCapability(
    name="search_fault_code_catalog",
    yacht_id_column="yacht_id",
    primary_key="id",
    default_select=["id", "code", "name", "severity", "symptoms", "causes"],
    default_limit=50,
    columns={
        "code": ColumnCapability(
            name="code",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE],
            entity_types=["FAULT_CODE"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "name": ColumnCapability(
            name="name",
            datatype="text",
            operators=[Operator.ILIKE],
            entity_types=["FAULT_CODE", "DESCRIPTION"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "severity": ColumnCapability(
            name="severity",
            datatype="text",
            operators=[Operator.EXACT],
            entity_types=["SEVERITY"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "symptoms": ColumnCapability(
            name="symptoms",
            datatype="text[]",
            operators=[Operator.ARRAY_ANY_ILIKE],
            entity_types=["SYMPTOM"],
            isolated_ok=False,
            conjunction_only=True
        ),
        "causes": ColumnCapability(
            name="causes",
            datatype="text[]",
            operators=[Operator.ARRAY_ANY_ILIKE],
            entity_types=["DESCRIPTION"],
            isolated_ok=False,
            conjunction_only=True
        ),
    }
)

# -----------------------------------------------------------------------------
# graph_nodes (106 rows)
# -----------------------------------------------------------------------------
TABLES["graph_nodes"] = TableCapability(
    name="graph_nodes",
    yacht_id_column="yacht_id",
    primary_key="id",
    default_select=["id", "label", "normalized_label", "node_type", "properties"],
    default_limit=50,
    columns={
        "label": ColumnCapability(
            name="label",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE, Operator.TRIGRAM],
            entity_types=["NODE_LABEL", "EQUIPMENT_NAME", "SYSTEM_NAME"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "normalized_label": ColumnCapability(
            name="normalized_label",
            datatype="text",
            operators=[Operator.EXACT],
            entity_types=["NODE_LABEL"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "node_type": ColumnCapability(
            name="node_type",
            datatype="text",
            operators=[Operator.EXACT],
            entity_types=["NODE_TYPE"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "properties": ColumnCapability(
            name="properties",
            datatype="jsonb",
            operators=[Operator.JSONB_PATH_ILIKE],
            entity_types=["MANUFACTURER"],
            isolated_ok=False,
            conjunction_only=True,
            json_keys=["manufacturer", "model"]
        ),
    }
)

# -----------------------------------------------------------------------------
# symptom_aliases (37 rows)
# -----------------------------------------------------------------------------
TABLES["symptom_aliases"] = TableCapability(
    name="symptom_aliases",
    yacht_id_column="yacht_id",
    primary_key="id",
    default_select=["id", "alias", "symptom_code"],
    default_limit=50,
    columns={
        "alias": ColumnCapability(
            name="alias",
            datatype="text",
            operators=[Operator.ILIKE, Operator.TRIGRAM],
            entity_types=["SYMPTOM", "FREE_TEXT"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "symptom_code": ColumnCapability(
            name="symptom_code",
            datatype="text",
            operators=[Operator.EXACT],
            entity_types=["SYMPTOM"],
            isolated_ok=True,
            conjunction_only=False
        ),
    }
)

# -----------------------------------------------------------------------------
# pms_suppliers (5 rows)
# -----------------------------------------------------------------------------
TABLES["pms_suppliers"] = TableCapability(
    name="pms_suppliers",
    yacht_id_column="yacht_id",
    primary_key="id",
    default_select=["id", "name", "contact_name", "email", "phone"],
    default_limit=50,
    columns={
        "name": ColumnCapability(
            name="name",
            datatype="text",
            operators=[Operator.ILIKE, Operator.TRIGRAM],
            entity_types=["SUPPLIER_NAME", "MANUFACTURER"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "contact_name": ColumnCapability(
            name="contact_name",
            datatype="text",
            operators=[Operator.ILIKE],
            entity_types=["CONTACT"],
            isolated_ok=False,
            conjunction_only=True
        ),
        "email": ColumnCapability(
            name="email",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE],
            entity_types=["CONTACT"],
            isolated_ok=True,
            conjunction_only=False
        ),
    }
)

# -----------------------------------------------------------------------------
# pms_work_orders (10 rows)
# -----------------------------------------------------------------------------
TABLES["pms_work_orders"] = TableCapability(
    name="pms_work_orders",
    yacht_id_column="yacht_id",
    primary_key="id",
    default_select=["id", "title", "status", "priority", "due_hours", "description"],
    default_limit=50,
    columns={
        "title": ColumnCapability(
            name="title",
            datatype="text",
            operators=[Operator.ILIKE, Operator.TRIGRAM],
            entity_types=["WORK_ORDER_TITLE", "FREE_TEXT"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "description": ColumnCapability(
            name="description",
            datatype="text",
            operators=[Operator.ILIKE, Operator.TRIGRAM],
            entity_types=["DESCRIPTION", "FREE_TEXT"],
            isolated_ok=False,
            conjunction_only=True
        ),
        "status": ColumnCapability(
            name="status",
            datatype="enum:work_order_status",  # Enum: pending, in_progress, completed, cancelled
            operators=[Operator.EXACT],
            entity_types=["STATUS"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "priority": ColumnCapability(
            name="priority",
            datatype="enum:work_order_priority",  # Enum: low, medium, high, critical
            operators=[Operator.EXACT],
            entity_types=["PRIORITY"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "due_hours": ColumnCapability(
            name="due_hours",
            datatype="integer",
            operators=[Operator.EXACT, Operator.RANGE],
            entity_types=["HOURS"],
            isolated_ok=True,
            conjunction_only=False
        ),
    }
)

# -----------------------------------------------------------------------------
# pms_purchase_orders (5 rows)
# -----------------------------------------------------------------------------
TABLES["pms_purchase_orders"] = TableCapability(
    name="pms_purchase_orders",
    yacht_id_column="yacht_id",
    primary_key="id",
    default_select=["id", "po_number", "status"],
    default_limit=50,
    columns={
        "po_number": ColumnCapability(
            name="po_number",
            datatype="text",
            operators=[Operator.EXACT, Operator.ILIKE],
            entity_types=["PO_NUMBER"],
            isolated_ok=True,
            conjunction_only=False
        ),
        "status": ColumnCapability(
            name="status",
            datatype="text",
            operators=[Operator.EXACT],
            entity_types=["STATUS"],
            isolated_ok=True,
            conjunction_only=False
        ),
    }
)

# =============================================================================
# ENTITY → COLUMN ROUTING
# =============================================================================
# Maps entity types to (table, column, operator) tuples
# This is the ONLY place entity routing is defined.

def get_columns_for_entity(entity_type: str) -> List[tuple]:
    """
    Get all (table, column, operators) that support an entity type.
    Returns list of (table_name, column_name, [operators], isolated_ok)
    """
    results = []
    for table_name, table in TABLES.items():
        for col_name, col in table.columns.items():
            if entity_type in col.entity_types:
                results.append((
                    table_name,
                    col_name,
                    col.operators,
                    col.isolated_ok,
                    col.conjunction_only
                ))
    return results

def get_table(name: str) -> Optional[TableCapability]:
    """Get table by name."""
    return TABLES.get(name)

def validate_column_operator(table: str, column: str, operator: Operator) -> bool:
    """Check if operator is allowed for column."""
    tbl = TABLES.get(table)
    if not tbl:
        return False
    col = tbl.columns.get(column)
    if not col:
        return False
    return operator in col.operators
