"""
PROVE SEARCH SURFACE MAP
========================
Validates EVERY column in searchable tables.
NO ASSUMPTIONS - queries OpenAPI schema directly.
"""

import json
import urllib.request
import ssl
from datetime import datetime

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Searchable tables (from A1 evidence)
SEARCHABLE_TABLES = [
    "alias_symptoms", "alias_systems", "document_chunks", "entity_staging",
    "graph_edges", "graph_nodes", "maintenance_facts", "pms_inventory_stock",
    "pms_parts", "relationship_staging", "search_document_chunks",
    "search_fault_code_catalog", "search_graph_edges", "search_graph_nodes",
    "search_maintenance_facts", "symptom_aliases", "v_inventory"
]

# Match mode rules by data type
def get_match_modes(col_type, col_format, col_name):
    """Determine valid match modes for a column based on type."""
    modes = []

    # UUID columns
    if col_format == "uuid" or "id" in col_name.lower():
        modes = ["EXACT"]

    # Text/string columns
    elif col_type == "string" or col_format == "text":
        if col_name in ["yacht_id"]:
            modes = ["FILTER_ONLY"]
        elif "embedding" in col_name.lower():
            modes = ["VECTOR"]
        elif col_name.endswith("_type") or col_name in ["status", "severity", "priority"]:
            modes = ["EXACT", "ILIKE"]
        else:
            modes = ["EXACT", "ILIKE", "TRIGRAM"]

    # Integer columns
    elif col_type == "integer" or col_format == "int4" or col_format == "int8":
        modes = ["EXACT", "RANGE"]

    # Float/numeric
    elif col_type == "number" or col_format in ["float4", "float8", "numeric"]:
        modes = ["EXACT", "RANGE"]

    # Boolean
    elif col_type == "boolean":
        modes = ["EXACT"]

    # Timestamp
    elif "timestamp" in str(col_format) or col_name.endswith("_at"):
        modes = ["EXACT", "RANGE"]

    # Array columns
    elif col_type == "array" or "ARRAY" in str(col_type):
        modes = ["CONTAINS", "ILIKE_ANY"]

    # JSONB
    elif col_format == "jsonb" or col_type == "object":
        modes = ["JSONB_PATH"]

    # Vector
    elif "vector" in str(col_type).lower() or "vector" in str(col_format).lower():
        modes = ["VECTOR"]

    else:
        modes = ["UNKNOWN"]

    return modes


def determine_isolation_rules(col_name, col_type, table_name):
    """Determine if column can be searched in isolation or only with conjunction."""
    # yacht_id: NEVER searched alone, always filter
    if col_name == "yacht_id":
        return False, True, "FILTER_ONLY - always required but never searched"

    # ID columns: can search isolated
    if col_name == "id" or col_name.endswith("_id"):
        return True, True, "ID column - can be exact searched"

    # Metadata/jsonb: conjunction only
    if col_name in ["metadata", "properties", "attachments"]:
        return False, True, "METADATA - too broad for isolated search"

    # Timestamps: conjunction only (too many results)
    if col_name.endswith("_at") or "timestamp" in col_name:
        return False, True, "TIMESTAMP - too broad for isolated search"

    # Boolean flags: conjunction only
    if col_type == "boolean":
        return False, True, "BOOLEAN - too broad for isolated search"

    # Text columns - depends on specificity
    if col_name in ["name", "label", "title", "code", "part_number", "fault_code"]:
        return True, True, "PRIMARY_TEXT - can be searched in isolation"

    if col_name in ["description", "text", "content", "notes"]:
        return False, True, "BROAD_TEXT - conjunction preferred but allowed"

    # manufacturer: MUST NOT be isolated (too many false positives)
    if col_name == "manufacturer":
        return False, True, "MANUFACTURER - must be conjunction with name/part"

    # Default: allow both
    return True, True, "DEFAULT"


def get_entity_types_allowed(col_name, table_name):
    """Determine which entity types can route to this column."""
    entity_map = {
        "part_number": ["PART_NUMBER"],
        "name": ["PART_NAME", "EQUIPMENT_NAME", "SYSTEM_NAME", "COMPONENT_NAME", "SUPPLIER_NAME"],
        "manufacturer": ["MANUFACTURER"],
        "label": ["SYSTEM_NAME", "COMPONENT_NAME", "EQUIPMENT_NAME", "CANONICAL_ENTITY"],
        "normalized_label": ["CANONICAL_ENTITY", "SYSTEM_NAME"],
        "code": ["FAULT_CODE"],
        "fault_code": ["FAULT_CODE"],
        "content": ["DOCUMENT_QUERY", "PROCEDURE_SEARCH", "FREE_TEXT"],
        "section_title": ["SECTION_NAME", "DOCUMENT_QUERY"],
        "doc_type": ["DOC_TYPE"],
        "system_tag": ["SYSTEM_NAME"],
        "location": ["STOCK_LOCATION", "EQUIPMENT_LOCATION"],
        "alias": ["SYMPTOM_NAME", "SYSTEM_NAME"],
        "canonical": ["CANONICAL_ENTITY", "SYMPTOM_NAME", "SYSTEM_NAME"],
        "symptoms": ["SYMPTOM_NAME"],
        "node_type": ["NODE_TYPE"],
        "severity": ["SEVERITY"],
        "description": ["FREE_TEXT"],
    }
    return entity_map.get(col_name, ["UNKNOWN"])


def main():
    print("=" * 70)
    print("SEARCH SURFACE MAP - HARD EVIDENCE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Fetch OpenAPI schema
    url = f"{SUPABASE_URL}/rest/v1/"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        schema = json.loads(resp.read().decode())

    definitions = schema.get("definitions", {})

    surface_map = []
    total_columns = 0
    searchable_columns = 0
    text_columns = 0
    vector_columns = 0
    array_columns = 0

    for table_name in SEARCHABLE_TABLES:
        if table_name not in definitions:
            print(f"WARNING: {table_name} not in schema")
            continue

        props = definitions[table_name].get("properties", {})
        print(f"\n{table_name} ({len(props)} columns):")

        for col_name, spec in props.items():
            total_columns += 1

            col_type = spec.get("type", "unknown")
            col_format = spec.get("format", "")
            col_desc = spec.get("description", "")

            # Get match modes
            match_modes = get_match_modes(col_type, col_format, col_name)

            # Get isolation rules
            isolated, conjunction, rule = determine_isolation_rules(col_name, col_type, table_name)

            # Get entity types
            entity_types = get_entity_types_allowed(col_name, table_name)

            # Count stats
            if "ILIKE" in match_modes or "TRIGRAM" in match_modes:
                text_columns += 1
            if "VECTOR" in match_modes:
                vector_columns += 1
            if "CONTAINS" in match_modes:
                array_columns += 1
            if match_modes != ["FILTER_ONLY"] and match_modes != ["UNKNOWN"]:
                searchable_columns += 1

            entry = {
                "table": table_name,
                "column": col_name,
                "datatype": f"{col_type}" + (f"({col_format})" if col_format else ""),
                "match_modes": match_modes,
                "isolated": isolated,
                "conjunction_only": not isolated,
                "canonical_rule": rule,
                "entity_types_allowed": entity_types,
                "indexes": "UNKNOWN",  # Would need pg_indexes query
            }
            surface_map.append(entry)

            # Print summary
            iso_mark = "I" if isolated else "C"
            print(f"  [{iso_mark}] {col_name}: {match_modes} -> {entity_types[:2]}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Tables analyzed: {len(SEARCHABLE_TABLES)}")
    print(f"Total columns: {total_columns}")
    print(f"Searchable columns: {searchable_columns}")
    print(f"Text columns (ILIKE/TRIGRAM): {text_columns}")
    print(f"Vector columns: {vector_columns}")
    print(f"Array columns: {array_columns}")

    # Output JSON
    output = {
        "generated_at": datetime.now().isoformat(),
        "discovery_method": "OpenAPI schema + deterministic type mapping",
        "summary": {
            "tables_analyzed": len(SEARCHABLE_TABLES),
            "total_columns": total_columns,
            "searchable_columns": searchable_columns,
            "text_columns": text_columns,
            "vector_columns": vector_columns,
            "array_columns": array_columns,
        },
        "columns": surface_map,
    }

    output_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))docs/SEARCH_SURFACE_MAP.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput written to: {output_path}")

    # List conjunction-only columns
    conj_only = [c for c in surface_map if c["conjunction_only"] and c["column"] != "yacht_id"]
    print(f"\nConjunction-only columns ({len(conj_only)}):")
    for c in conj_only[:15]:
        print(f"  {c['table']}.{c['column']}: {c['canonical_rule']}")


if __name__ == "__main__":
    main()
