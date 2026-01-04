"""
BUILD COMPLETE SEARCH SURFACE REGISTRY
======================================
Exhaustive mapping of:
- Every table with yacht_id
- Every column with data type
- Entity types that COULD match each column
- Term variants users might input
- Intents each column serves
- Current routing vs required routing

This is the FOUNDATION before we can prove SQL works.
"""

import os
import sys
import json
import httpx
from datetime import datetime
from typing import Dict, List, Any, Set
from dataclasses import dataclass, asdict, field

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


# =============================================================================
# ENTITY TYPE DEFINITIONS
# =============================================================================
# All possible entity types a user query could contain

ENTITY_TYPES = {
    # Identifiers (exact match candidates)
    "PART_NUMBER": {
        "description": "Part number like ENG-0008-103",
        "patterns": [r"^[A-Z]{2,4}-\d{3,5}-\d{2,4}$", r"^\d{5,10}$"],
        "examples": ["ENG-0008-103", "PMP-0018-280", "12345678"],
        "match_modes": ["EXACT", "ILIKE"],
    },
    "FAULT_CODE": {
        "description": "Fault/error code like E047, F-123",
        "patterns": [r"^[EFWAC]-?\d{2,4}$", r"^ERR-?\d+$", r"^FAULT-?\d+$"],
        "examples": ["E047", "F-123", "ERR001", "FAULT47"],
        "match_modes": ["EXACT", "ILIKE"],
    },
    "SERIAL_NUMBER": {
        "description": "Equipment serial number",
        "patterns": [r"^SN[-_]?\d+$", r"^[A-Z]{2,3}\d{6,10}$"],
        "examples": ["SN-12345", "ABC1234567"],
        "match_modes": ["EXACT", "ILIKE"],
    },
    "WORK_ORDER_ID": {
        "description": "Work order identifier",
        "patterns": [r"^WO[-_]?\d+$", r"^\d{6,}$"],
        "examples": ["WO-12345", "WO123456"],
        "match_modes": ["EXACT"],
    },

    # Names (ILIKE/TRIGRAM candidates)
    "PART_NAME": {
        "description": "Part name like 'Fuel Filter', 'Glow Plug'",
        "patterns": [],  # Free text
        "examples": ["Fuel Filter", "Glow Plug", "Impeller"],
        "match_modes": ["ILIKE", "TRIGRAM"],
    },
    "EQUIPMENT_NAME": {
        "description": "Equipment name like 'Main Engine', 'Generator 1'",
        "patterns": [],
        "examples": ["Main Engine", "Generator 1", "Watermaker"],
        "match_modes": ["ILIKE", "TRIGRAM"],
    },
    "SYSTEM_NAME": {
        "description": "System name like 'Electrical System', 'Fuel System'",
        "patterns": [],
        "examples": ["Electrical System", "Fuel System", "HVAC"],
        "match_modes": ["ILIKE", "TRIGRAM"],
    },
    "COMPONENT_NAME": {
        "description": "Component name",
        "patterns": [],
        "examples": ["Turbocharger", "Heat Exchanger", "Injector"],
        "match_modes": ["ILIKE", "TRIGRAM"],
    },
    "MANUFACTURER": {
        "description": "Manufacturer/brand name",
        "patterns": [],
        "examples": ["Caterpillar", "Cummins", "Kohler", "Garmin"],
        "match_modes": ["ILIKE", "TRIGRAM"],
    },
    "SUPPLIER_NAME": {
        "description": "Supplier/vendor name",
        "patterns": [],
        "examples": ["Marine Parts Direct", "West Marine"],
        "match_modes": ["ILIKE", "TRIGRAM"],
    },
    "SYMPTOM_NAME": {
        "description": "Symptom description like 'vibration', 'overheating'",
        "patterns": [],
        "examples": ["vibration", "overheating", "smoke", "noise"],
        "match_modes": ["ILIKE", "TRIGRAM", "VECTOR"],
    },

    # Locations
    "STOCK_LOCATION": {
        "description": "Inventory storage location",
        "patterns": [],
        "examples": ["Engine Room", "Lazarette", "Agent - Palma"],
        "match_modes": ["EXACT", "ILIKE"],
    },
    "EQUIPMENT_LOCATION": {
        "description": "Where equipment is installed",
        "patterns": [],
        "examples": ["Engine Room", "Flybridge", "Forepeak"],
        "match_modes": ["ILIKE"],
    },

    # Status/Enum values
    "STATUS": {
        "description": "Status values like 'open', 'closed', 'pending'",
        "patterns": [],
        "examples": ["open", "closed", "pending", "in_progress", "completed"],
        "match_modes": ["EXACT"],
    },
    "PRIORITY": {
        "description": "Priority levels",
        "patterns": [],
        "examples": ["high", "medium", "low", "critical", "urgent"],
        "match_modes": ["EXACT"],
    },
    "SEVERITY": {
        "description": "Severity levels for faults",
        "patterns": [],
        "examples": ["critical", "warning", "info", "error"],
        "match_modes": ["EXACT"],
    },

    # Document-related
    "DOCUMENT_QUERY": {
        "description": "Free text search in documents",
        "patterns": [],
        "examples": ["oil change procedure", "wiring diagram", "troubleshooting"],
        "match_modes": ["ILIKE", "TRIGRAM", "VECTOR"],
    },
    "SECTION_NAME": {
        "description": "Document section title",
        "patterns": [],
        "examples": ["Maintenance", "Safety", "Specifications"],
        "match_modes": ["ILIKE"],
    },
    "DOC_TYPE": {
        "description": "Document type",
        "patterns": [],
        "examples": ["manual", "procedure", "schematic", "certificate"],
        "match_modes": ["EXACT"],
    },

    # Graph/Canonical
    "CANONICAL_ENTITY": {
        "description": "Normalized entity label",
        "patterns": [],
        "examples": ["MAIN_ENGINE", "FUEL_SYSTEM", "BOW_THRUSTER"],
        "match_modes": ["EXACT", "ILIKE"],
    },
    "NODE_TYPE": {
        "description": "Graph node type",
        "patterns": [],
        "examples": ["equipment", "system", "component", "symptom"],
        "match_modes": ["EXACT"],
    },

    # Catch-all
    "FREE_TEXT": {
        "description": "Any unclassified text query",
        "patterns": [],
        "examples": ["anything"],
        "match_modes": ["ILIKE", "TRIGRAM", "VECTOR"],
    },
    "UNKNOWN": {
        "description": "Unrecognized query type",
        "patterns": [],
        "examples": [],
        "match_modes": ["ILIKE", "TRIGRAM"],
    },
}


# =============================================================================
# INTENT DEFINITIONS
# =============================================================================
# What the user is trying to accomplish

INTENTS = {
    "LOOKUP_PART": "Find a specific part by number or name",
    "LOOKUP_EQUIPMENT": "Find equipment by name or serial",
    "LOOKUP_FAULT": "Find fault code meaning and resolution",
    "CHECK_STOCK": "Check inventory levels and locations",
    "FIND_PROCEDURE": "Find maintenance procedure or manual",
    "DIAGNOSE_SYMPTOM": "Diagnose based on symptom description",
    "FIND_SUPPLIER": "Find supplier for a part",
    "CHECK_STATUS": "Check work order or maintenance status",
    "BROWSE_SYSTEM": "Explore a system's components",
    "FREE_SEARCH": "General search without specific intent",
}


# =============================================================================
# COLUMN SPEC BUILDER
# =============================================================================

@dataclass
class ColumnSpec:
    """Complete specification for a searchable column."""
    table: str
    column: str
    data_type: str
    is_nullable: bool
    sample_values: List[str]
    row_count: int

    # Search configuration
    entity_types_allowed: List[str] = field(default_factory=list)
    match_modes_allowed: List[str] = field(default_factory=list)
    intents_served: List[str] = field(default_factory=list)
    term_variants: List[str] = field(default_factory=list)

    # Routing rules
    isolated_ok: bool = True  # Can be searched alone
    conjunction_only: bool = False  # Only with another term
    normalizers: List[str] = field(default_factory=list)

    # Current state
    currently_routed_by: List[str] = field(default_factory=list)  # Entity types that route here now
    routing_gap: List[str] = field(default_factory=list)  # Entity types that SHOULD route here


@dataclass
class TableSpec:
    """Complete specification for a searchable table."""
    table_name: str
    has_yacht_id: bool
    primary_key: str
    row_count: int
    columns: List[ColumnSpec] = field(default_factory=list)


class SearchSurfaceBuilder:
    """Builds the complete search surface registry."""

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.headers = {
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}"
        }
        self.tables: Dict[str, TableSpec] = {}

    def get_all_tables(self) -> List[str]:
        """Get all tables from OpenAPI schema."""
        r = self.client.get(f"{SUPABASE_URL}/rest/v1/", headers=self.headers)
        if r.status_code == 200:
            try:
                schema = r.json()
                self._openapi_schema = schema  # Cache for later
                if "paths" in schema:
                    # Swagger/OpenAPI paths look like "/table_name"
                    tables = []
                    for path in schema["paths"].keys():
                        if path != "/" and not path.startswith("/rpc/"):
                            tables.append(path.strip("/"))
                    return tables
                elif "definitions" in schema:
                    return list(schema["definitions"].keys())
            except Exception as e:
                print(f"  Error parsing schema: {e}")
        return []

    def get_table_schema(self, table: str) -> Dict:
        """Get column info for a table from cached OpenAPI schema."""
        if hasattr(self, '_openapi_schema') and self._openapi_schema:
            definitions = self._openapi_schema.get("definitions", {})
            if table in definitions:
                return {"definitions": {table: definitions[table]}}
        return {}

    def get_row_count(self, table: str) -> int:
        """Get row count for yacht_id filtered table."""
        r = self.client.get(
            f"{SUPABASE_URL}/rest/v1/{table}?select=count&yacht_id=eq.{TEST_YACHT_ID}",
            headers={**self.headers, "Prefer": "count=exact"}
        )
        if r.status_code == 200:
            count_header = r.headers.get("content-range", "")
            if "/" in count_header:
                try:
                    return int(count_header.split("/")[1])
                except:
                    pass
        return 0

    def get_sample_values(self, table: str, column: str, limit: int = 5) -> List[str]:
        """Get sample values from a column."""
        r = self.client.get(
            f"{SUPABASE_URL}/rest/v1/{table}?select={column}&yacht_id=eq.{TEST_YACHT_ID}&limit={limit}",
            headers=self.headers
        )
        if r.status_code == 200:
            data = r.json()
            return [str(row.get(column, "")) for row in data if row.get(column)]
        return []

    def infer_entity_types(self, table: str, column: str, data_type: str, samples: List[str]) -> List[str]:
        """Infer which entity types could match this column."""
        entity_types = []
        col_lower = column.lower()
        table_lower = table.lower()

        # By column name patterns
        if "part_number" in col_lower or col_lower == "part_no":
            entity_types.extend(["PART_NUMBER", "FREE_TEXT"])
        if col_lower in ["name", "title", "label"]:
            if "part" in table_lower:
                entity_types.extend(["PART_NAME", "FREE_TEXT"])
            elif "equipment" in table_lower:
                entity_types.extend(["EQUIPMENT_NAME", "FREE_TEXT"])
            elif "supplier" in table_lower:
                entity_types.extend(["SUPPLIER_NAME", "FREE_TEXT"])
            else:
                entity_types.extend(["FREE_TEXT"])
        if "description" in col_lower or "desc" == col_lower:
            entity_types.extend(["FREE_TEXT", "DOCUMENT_QUERY"])
        if "serial" in col_lower:
            entity_types.extend(["SERIAL_NUMBER", "FREE_TEXT"])
        if col_lower in ["code", "fault_code", "error_code"]:
            entity_types.extend(["FAULT_CODE", "FREE_TEXT"])
        if "location" in col_lower:
            if "stock" in table_lower or "inventory" in table_lower:
                entity_types.extend(["STOCK_LOCATION", "FREE_TEXT"])
            else:
                entity_types.extend(["EQUIPMENT_LOCATION", "FREE_TEXT"])
        if col_lower in ["status", "state"]:
            entity_types.extend(["STATUS"])
        if col_lower in ["priority"]:
            entity_types.extend(["PRIORITY"])
        if col_lower in ["severity"]:
            entity_types.extend(["SEVERITY"])
        if "manufacturer" in col_lower or "brand" in col_lower:
            entity_types.extend(["MANUFACTURER", "FREE_TEXT"])
        if col_lower in ["content", "body", "text"]:
            entity_types.extend(["DOCUMENT_QUERY", "FREE_TEXT"])
        if "section" in col_lower or "chapter" in col_lower:
            entity_types.extend(["SECTION_NAME", "FREE_TEXT"])
        if col_lower in ["doc_type", "document_type", "type"]:
            if "document" in table_lower or "doc" in table_lower:
                entity_types.extend(["DOC_TYPE"])
        if col_lower in ["alias", "synonym"]:
            entity_types.extend(["SYMPTOM_NAME", "FREE_TEXT"])
        if col_lower in ["canonical", "normalized_label"]:
            entity_types.extend(["CANONICAL_ENTITY"])
        if col_lower in ["node_type", "entity_type"]:
            entity_types.extend(["NODE_TYPE"])
        if "system" in col_lower:
            entity_types.extend(["SYSTEM_NAME", "FREE_TEXT"])
        if "equipment" in col_lower:
            entity_types.extend(["EQUIPMENT_NAME", "FREE_TEXT"])
        if "category" in col_lower:
            entity_types.extend(["FREE_TEXT"])

        # If text type and no specific match, allow FREE_TEXT
        if data_type in ["text", "character varying", "varchar"] and not entity_types:
            entity_types.append("FREE_TEXT")

        return list(set(entity_types))

    def infer_match_modes(self, data_type: str, entity_types: List[str]) -> List[str]:
        """Infer allowed match modes based on data type and entity types."""
        modes = []

        if data_type in ["text", "character varying", "varchar"]:
            # Check entity types for guidance
            has_identifier = any(e in entity_types for e in ["PART_NUMBER", "FAULT_CODE", "SERIAL_NUMBER"])
            has_name = any(e in entity_types for e in ["PART_NAME", "EQUIPMENT_NAME", "SYSTEM_NAME", "MANUFACTURER"])
            has_document = any(e in entity_types for e in ["DOCUMENT_QUERY"])

            if has_identifier:
                modes.extend(["EXACT", "ILIKE"])
            if has_name:
                modes.extend(["ILIKE", "TRIGRAM"])
            if has_document:
                modes.extend(["ILIKE", "TRIGRAM", "VECTOR"])
            if not modes:
                modes.extend(["ILIKE"])

        elif data_type in ["integer", "bigint", "smallint", "numeric", "decimal"]:
            modes.append("EXACT")
            modes.append("RANGE")

        elif data_type in ["boolean"]:
            modes.append("EXACT")

        elif data_type in ["uuid"]:
            modes.append("EXACT")

        elif data_type in ["timestamp", "timestamptz", "date"]:
            modes.append("RANGE")

        return list(set(modes))

    def infer_intents(self, table: str, column: str, entity_types: List[str]) -> List[str]:
        """Infer which user intents this column serves."""
        intents = []
        table_lower = table.lower()
        col_lower = column.lower()

        if "part" in table_lower:
            intents.append("LOOKUP_PART")
            if "stock" in col_lower or "quantity" in col_lower:
                intents.append("CHECK_STOCK")
        if "equipment" in table_lower:
            intents.append("LOOKUP_EQUIPMENT")
        if "fault" in table_lower or "fault_code" in col_lower:
            intents.append("LOOKUP_FAULT")
        if "inventory" in table_lower:
            intents.append("CHECK_STOCK")
        if "document" in table_lower or "chunk" in table_lower:
            intents.append("FIND_PROCEDURE")
        if "symptom" in table_lower or "alias" in col_lower:
            intents.append("DIAGNOSE_SYMPTOM")
        if "supplier" in table_lower:
            intents.append("FIND_SUPPLIER")
        if "work_order" in table_lower:
            intents.append("CHECK_STATUS")
        if "graph" in table_lower or "node" in table_lower:
            intents.append("BROWSE_SYSTEM")

        # All text columns serve free search
        if "FREE_TEXT" in entity_types:
            intents.append("FREE_SEARCH")

        return list(set(intents))

    def infer_term_variants(self, column: str, entity_types: List[str], samples: List[str]) -> List[str]:
        """Infer what term variants users might input for this column."""
        variants = []

        if "PART_NUMBER" in entity_types:
            variants.extend([
                "with_dashes (ENG-0008-103)",
                "without_dashes (ENG0008103)",
                "lowercase (eng-0008-103)",
                "partial (0008-103)"
            ])
        if "FAULT_CODE" in entity_types:
            variants.extend([
                "with_prefix (E047)",
                "without_prefix (047)",
                "with_dash (E-047)",
                "spelled_out (error 47)"
            ])
        if "EQUIPMENT_NAME" in entity_types or "SYSTEM_NAME" in entity_types:
            variants.extend([
                "canonical (MAIN_ENGINE)",
                "natural (main engine)",
                "abbreviated (ME, gen)",
                "misspelled (engien)"
            ])
        if "STOCK_LOCATION" in entity_types:
            variants.extend([
                "full_name (Engine Room)",
                "abbreviated (ER)",
                "lowercase (engine room)"
            ])
        if "DOCUMENT_QUERY" in entity_types:
            variants.extend([
                "natural_question (how to change oil)",
                "keywords (oil change procedure)",
                "partial_phrase (oil change)"
            ])

        # Add samples as concrete examples
        for s in samples[:3]:
            if s:
                variants.append(f"actual: {s}")

        return variants

    def infer_normalizers(self, entity_types: List[str]) -> List[str]:
        """Infer what normalizers should be applied."""
        normalizers = []

        if "PART_NUMBER" in entity_types:
            normalizers.extend(["strip_dashes", "uppercase"])
        if "FAULT_CODE" in entity_types:
            normalizers.extend(["strip_prefix", "uppercase"])
        if any(e in entity_types for e in ["EQUIPMENT_NAME", "SYSTEM_NAME", "CANONICAL_ENTITY"]):
            normalizers.extend(["underscore_to_space", "lowercase"])
        if "STOCK_LOCATION" in entity_types:
            normalizers.extend(["expand_abbreviations"])

        return list(set(normalizers))

    def get_current_routing(self, table: str, column: str) -> List[str]:
        """Check which entity types currently route to this column in ENTITY_SOURCE_MAP."""
        # Import current routing
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from api.search_planner import ENTITY_SOURCE_MAP

            routing = []
            for entity_type, sources in ENTITY_SOURCE_MAP.items():
                for source in sources:
                    if source.table == table and source.column == column:
                        routing.append(entity_type)
            return list(set(routing))
        except Exception as e:
            return []

    def build_column_spec(self, table: str, column: str, data_type: str, is_nullable: bool) -> ColumnSpec:
        """Build complete specification for a column."""
        # Get sample values
        samples = self.get_sample_values(table, column)

        # Infer everything
        entity_types = self.infer_entity_types(table, column, data_type, samples)
        match_modes = self.infer_match_modes(data_type, entity_types)
        intents = self.infer_intents(table, column, entity_types)
        term_variants = self.infer_term_variants(column, entity_types, samples)
        normalizers = self.infer_normalizers(entity_types)

        # Get current routing
        current_routing = self.get_current_routing(table, column)

        # Calculate routing gap
        routing_gap = [e for e in entity_types if e not in current_routing]

        # Determine isolation rules
        isolated_ok = True
        conjunction_only = False
        if column.lower() in ["status", "priority", "severity", "type"]:
            conjunction_only = True
            isolated_ok = False

        # Get row count for this specific column (non-null values)
        r = self.client.get(
            f"{SUPABASE_URL}/rest/v1/{table}?select=count&{column}=not.is.null&yacht_id=eq.{TEST_YACHT_ID}",
            headers={**self.headers, "Prefer": "count=exact"}
        )
        row_count = 0
        if r.status_code == 200:
            count_header = r.headers.get("content-range", "")
            if "/" in count_header:
                try:
                    row_count = int(count_header.split("/")[1])
                except:
                    pass

        return ColumnSpec(
            table=table,
            column=column,
            data_type=data_type,
            is_nullable=is_nullable,
            sample_values=samples,
            row_count=row_count,
            entity_types_allowed=entity_types,
            match_modes_allowed=match_modes,
            intents_served=intents,
            term_variants=term_variants,
            isolated_ok=isolated_ok,
            conjunction_only=conjunction_only,
            normalizers=normalizers,
            currently_routed_by=current_routing,
            routing_gap=routing_gap
        )

    def build_table_spec(self, table: str) -> TableSpec:
        """Build complete specification for a table."""
        if not table or table.startswith("_"):
            return None

        # Get schema
        schema = self.get_table_schema(table)
        if not schema:
            return None

        print(f"  Processing {table}...")

        # Check if has yacht_id
        definitions = schema.get("definitions", {})
        table_def = definitions.get(table, {})
        properties = table_def.get("properties", {})

        has_yacht_id = "yacht_id" in properties
        if not has_yacht_id:
            return None  # Skip tables without yacht_id

        # Get primary key
        pk = "id"  # Default
        required = table_def.get("required", [])
        if "id" in required:
            pk = "id"

        # Get row count
        row_count = self.get_row_count(table)

        # Build column specs for text columns
        columns = []
        for col_name, col_info in properties.items():
            # Skip system columns
            if col_name in ["id", "yacht_id", "created_at", "updated_at"]:
                continue

            data_type = col_info.get("type", "")
            format_ = col_info.get("format", "")

            # Map to PostgreSQL types
            if format_ == "uuid":
                pg_type = "uuid"
            elif format_ in ["timestamp", "date-time"]:
                pg_type = "timestamp"
            elif data_type == "integer":
                pg_type = "integer"
            elif data_type == "number":
                pg_type = "numeric"
            elif data_type == "boolean":
                pg_type = "boolean"
            elif data_type == "string":
                pg_type = "text"
            elif data_type == "array":
                pg_type = "array"
            else:
                pg_type = data_type or "text"

            is_nullable = col_name not in required

            col_spec = self.build_column_spec(table, col_name, pg_type, is_nullable)
            columns.append(col_spec)

        return TableSpec(
            table_name=table,
            has_yacht_id=has_yacht_id,
            primary_key=pk,
            row_count=row_count,
            columns=columns
        )

    def build_registry(self) -> Dict:
        """Build the complete search surface registry."""
        print("Building complete search surface registry...")
        print("=" * 60)

        # Get all tables
        tables = self.get_all_tables()
        print(f"Found {len(tables)} tables")

        # Build specs for each table
        for table in sorted(tables):
            spec = self.build_table_spec(table)
            if spec:
                self.tables[table] = spec

        print(f"\nProcessed {len(self.tables)} tables with yacht_id")

        # Generate summary
        total_columns = sum(len(t.columns) for t in self.tables.values())
        text_columns = sum(
            1 for t in self.tables.values()
            for c in t.columns
            if c.data_type in ["text", "character varying", "varchar"]
        )
        columns_with_data = sum(
            1 for t in self.tables.values()
            for c in t.columns
            if c.row_count > 0
        )
        columns_with_routing_gap = sum(
            1 for t in self.tables.values()
            for c in t.columns
            if c.routing_gap
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tables": len(self.tables),
                "total_columns": total_columns,
                "text_columns": text_columns,
                "columns_with_data": columns_with_data,
                "columns_with_routing_gap": columns_with_routing_gap,
            },
            "entity_types": ENTITY_TYPES,
            "intents": INTENTS,
            "tables": {
                name: asdict(spec) for name, spec in self.tables.items()
            }
        }

    def close(self):
        self.client.close()


def main():
    print("=" * 60)
    print("SEARCH SURFACE REGISTRY BUILDER")
    print("=" * 60)
    print()

    builder = SearchSurfaceBuilder()
    try:
        registry = builder.build_registry()

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        s = registry["summary"]
        print(f"Total Tables: {s['total_tables']}")
        print(f"Total Columns: {s['total_columns']}")
        print(f"Text Columns: {s['text_columns']}")
        print(f"Columns with Data: {s['columns_with_data']}")
        print(f"Columns with Routing Gap: {s['columns_with_routing_gap']}")

        # Print routing gaps
        print("\n" + "-" * 60)
        print("ROUTING GAPS (columns missing entity type routing)")
        print("-" * 60)
        for table_name, table_data in registry["tables"].items():
            for col in table_data["columns"]:
                if col["routing_gap"] and col["row_count"] > 0:
                    print(f"  {table_name}.{col['column']}:")
                    print(f"    Data Type: {col['data_type']}")
                    print(f"    Row Count: {col['row_count']}")
                    print(f"    Should Accept: {col['entity_types_allowed']}")
                    print(f"    Currently Routes: {col['currently_routed_by']}")
                    print(f"    MISSING: {col['routing_gap']}")
                    print()

        # Save registry
        output_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))docs/SEARCH_SURFACE_REGISTRY.json"
        with open(output_path, "w") as f:
            json.dump(registry, f, indent=2)
        print(f"\nRegistry saved to: {output_path}")

    finally:
        builder.close()


if __name__ == "__main__":
    main()
