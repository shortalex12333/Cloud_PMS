"""
Capability Executor v1 - SQL/RPC Generator with yacht_id Enforcement
=====================================================================

This module generates and executes queries based on TABLE_CAPABILITIES.

SECURITY:
1. yacht_id is ALWAYS required - queries without yacht_id will fail
2. All user input is parameterized - no string interpolation in SQL
3. Only columns declared in TABLE_CAPABILITIES can be searched

USAGE:
    from api.capability_executor import CapabilityExecutor

    executor = CapabilityExecutor(supabase_client, yacht_id)
    results = executor.execute(
        capability_name="part_by_part_number_or_name",
        search_terms={"part_number": "ENG-0008-103"}
    )
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .table_capabilities import (
    TABLE_CAPABILITIES,
    CapabilityStatus,
    MatchType,
    Capability,
    TableSpec,
    SearchableColumn,
    get_active_capabilities,
)

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Raised when query execution fails."""
    pass


class SecurityError(Exception):
    """Raised when a security constraint is violated."""
    pass


@dataclass
class QueryResult:
    """Result from executing a capability query."""
    success: bool
    capability_name: str
    table_name: str
    rows: List[Dict[str, Any]]
    row_count: int
    query_type: str  # "sql" or "rpc"
    error: Optional[str] = None
    # For debugging/observability
    generated_query: Optional[str] = None
    execution_time_ms: Optional[float] = None


class CapabilityExecutor:
    """
    Generates and executes queries based on TABLE_CAPABILITIES registry.

    All queries are yacht_id isolated - no cross-yacht data access.
    """

    def __init__(self, supabase_client, yacht_id: str):
        """
        Initialize executor with Supabase client and yacht_id.

        Args:
            supabase_client: Supabase client instance
            yacht_id: UUID of the yacht (REQUIRED for all queries)
        """
        if not yacht_id:
            raise SecurityError("yacht_id is required for all queries")

        # Validate yacht_id format (UUID)
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, yacht_id.lower()):
            raise SecurityError(f"Invalid yacht_id format: {yacht_id}")

        self.client = supabase_client
        self.yacht_id = yacht_id
        self._active_capabilities = get_active_capabilities()

    def execute(
        self,
        capability_name: str,
        search_terms: Dict[str, Any],
        limit: int = 20,
        offset: int = 0,
    ) -> QueryResult:
        """
        Execute a query for a capability with given search terms.

        Args:
            capability_name: Name of the capability (e.g., "part_by_part_number_or_name")
            search_terms: Dict of column_name -> search_value
            limit: Max rows to return (default 20, max 100)
            offset: Pagination offset

        Returns:
            QueryResult with rows or error
        """
        import time
        start_time = time.time()

        # Validate capability exists and is active
        if capability_name not in self._active_capabilities:
            if capability_name in TABLE_CAPABILITIES:
                cap = TABLE_CAPABILITIES[capability_name]
                return QueryResult(
                    success=False,
                    capability_name=capability_name,
                    table_name="",
                    rows=[],
                    row_count=0,
                    query_type="blocked",
                    error=f"Capability '{capability_name}' is {cap.status.value}: {cap.blocked_reason}",
                )
            return QueryResult(
                success=False,
                capability_name=capability_name,
                table_name="",
                rows=[],
                row_count=0,
                query_type="unknown",
                error=f"Unknown capability: {capability_name}",
            )

        capability = self._active_capabilities[capability_name]

        # Enforce limit bounds
        limit = min(max(1, limit), 100)

        # Execute against first table (v1 = single table)
        table_spec = capability.tables[0]

        try:
            if table_spec.rpc_function:
                result = self._execute_rpc(capability, table_spec, search_terms, limit)
            else:
                result = self._execute_sql(capability, table_spec, search_terms, limit, offset)

            result.execution_time_ms = (time.time() - start_time) * 1000
            return result

        except Exception as e:
            error_msg = str(e)
            # Log detailed error for debugging
            logger.error(
                f"[CapabilityExecutor] EXECUTE FAILED: "
                f"capability={capability_name}, table={table_spec.name}, "
                f"search_terms={search_terms}, error={error_msg}"
            )

            # Check for common table-not-found patterns
            if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
                error_msg = f"Table '{table_spec.name}' does not exist in database. {error_msg}"
            elif "column" in error_msg.lower() and "does not exist" in error_msg.lower():
                error_msg = f"Column not found in table '{table_spec.name}'. {error_msg}"

            return QueryResult(
                success=False,
                capability_name=capability_name,
                table_name=table_spec.name,
                rows=[],
                row_count=0,
                query_type="error",
                error=error_msg,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _execute_sql(
        self,
        capability: Capability,
        table_spec: TableSpec,
        search_terms: Dict[str, Any],
        limit: int,
        offset: int,
    ) -> QueryResult:
        """Execute a SQL query via Supabase client."""

        logger.debug(
            f"[CapabilityExecutor] _execute_sql: table={table_spec.name}, "
            f"capability={capability.name}, search_terms={search_terms}"
        )

        # Validate search terms against declared columns
        searchable_cols = {col.name: col for col in table_spec.searchable_columns}
        for col_name in search_terms.keys():
            if col_name not in searchable_cols:
                raise SecurityError(
                    f"Column '{col_name}' is not searchable in capability '{capability.name}'"
                )

        # Build query
        query = self.client.table(table_spec.name)

        # SELECT only declared response columns
        if table_spec.response_columns:
            query = query.select(",".join(table_spec.response_columns))
        else:
            query = query.select("*")

        # ALWAYS filter by yacht_id first
        query = query.eq(table_spec.yacht_id_column, self.yacht_id)

        # Apply search filters
        query_description = f"SELECT FROM {table_spec.name} WHERE {table_spec.yacht_id_column}={self.yacht_id}"

        for col_name, search_value in search_terms.items():
            if search_value is None:
                continue

            col_spec = searchable_cols[col_name]
            query, filter_desc = self._apply_filter(query, col_spec, search_value)
            query_description += f" AND {filter_desc}"

        # Apply pagination
        query = query.limit(limit).offset(offset)
        query_description += f" LIMIT {limit} OFFSET {offset}"

        # Execute
        response = query.execute()

        # Tag results with metadata for domain grouping
        rows = response.data or []
        for row in rows:
            row['_capability'] = capability.name
            row['_source_table'] = table_spec.name

        return QueryResult(
            success=True,
            capability_name=capability.name,
            table_name=table_spec.name,
            rows=rows,
            row_count=len(rows),
            query_type="sql",
            generated_query=query_description,
        )

    def _execute_rpc(
        self,
        capability: Capability,
        table_spec: TableSpec,
        search_terms: Dict[str, Any],
        limit: int,
    ) -> QueryResult:
        """Execute an RPC (stored procedure) call."""

        # Get the primary search term for the RPC
        primary_cols = [c for c in table_spec.searchable_columns if c.is_primary]
        if not primary_cols:
            primary_cols = table_spec.searchable_columns[:1]

        # Find the search value
        search_text = None
        for col in primary_cols:
            if col.name in search_terms:
                search_text = search_terms[col.name]
                break

        if not search_text:
            # Use any provided search term
            search_text = next(iter(search_terms.values()), "")

        # Build RPC params (specific to unified_search_v2)
        rpc_params = {
            "search_query": str(search_text),
            "p_yacht_id": self.yacht_id,
            "result_limit": limit,
        }

        query_description = f"RPC {table_spec.rpc_function}(query='{search_text}', yacht_id={self.yacht_id})"

        # Execute RPC
        response = self.client.rpc(table_spec.rpc_function, rpc_params).execute()

        # RPC returns different structure, normalize it
        rows = response.data or []

        return QueryResult(
            success=True,
            capability_name=capability.name,
            table_name=table_spec.name,
            rows=rows,
            row_count=len(rows),
            query_type="rpc",
            generated_query=query_description,
        )

    def _generate_smart_pattern(self, value: str) -> str:
        """
        Generate flexible ILIKE pattern for better matching.

        Examples:
            "turbo gasket" → "%turbo%gasket%"
            "MID 128" → "%MID%128%"
            "fuel filter" → "%fuel%filter%"
        """
        if not isinstance(value, str):
            return f"%{value}%"

        # Remove extra spaces, normalize punctuation
        normalized = re.sub(r'[\s\-_]+', ' ', value).strip()
        tokens = normalized.split()

        if len(tokens) > 1:
            # Multi-token: "turbo gasket" → "%turbo%gasket%"
            # This matches "Turbocharger Gasket Set", "Turbo Seal Gasket", etc.
            return f"%{'%'.join(tokens)}%"
        else:
            # Single token: "MTU" → "%MTU%"
            return f"%{value}%"

    def _apply_filter(
        self,
        query,
        col_spec: SearchableColumn,
        value: Any,
    ) -> Tuple[Any, str]:
        """
        Apply appropriate filter based on column's match types.

        Returns (modified_query, filter_description)
        """
        col_name = col_spec.name

        # Use first available match type
        match_type = col_spec.match_types[0]

        if match_type == MatchType.EXACT:
            return query.eq(col_name, value), f"{col_name}='{value}'"

        elif match_type == MatchType.ILIKE:
            # Case-insensitive pattern match with smart tokenization
            pattern = self._generate_smart_pattern(value)
            return query.ilike(col_name, pattern), f"{col_name} ILIKE '{pattern}'"

        elif match_type == MatchType.TRIGRAM:
            # Supabase doesn't have direct trigram support via client
            # Fall back to ilike with smart patterns
            pattern = self._generate_smart_pattern(value)
            return query.ilike(col_name, pattern), f"{col_name} ILIKE '{pattern}' (trigram fallback)"

        elif match_type == MatchType.NUMERIC_RANGE:
            if isinstance(value, dict):
                if "min" in value:
                    query = query.gte(col_name, value["min"])
                if "max" in value:
                    query = query.lte(col_name, value["max"])
                return query, f"{col_name} BETWEEN {value.get('min', '*')} AND {value.get('max', '*')}"
            else:
                # Single value = exact match
                return query.eq(col_name, value), f"{col_name}={value}"

        elif match_type == MatchType.DATE_RANGE:
            if isinstance(value, dict):
                if "start" in value:
                    query = query.gte(col_name, value["start"])
                if "end" in value:
                    query = query.lte(col_name, value["end"])
                return query, f"{col_name} BETWEEN {value.get('start', '*')} AND {value.get('end', '*')}"
            else:
                return query.eq(col_name, value), f"{col_name}='{value}'"

        else:
            # Default to exact match
            return query.eq(col_name, value), f"{col_name}='{value}'"


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def execute_capability_search(
    supabase_client,
    yacht_id: str,
    capability_name: str,
    search_terms: Dict[str, Any],
    limit: int = 20,
) -> QueryResult:
    """
    One-shot function to execute a capability search.

    Example:
        result = execute_capability_search(
            client,
            yacht_id="85fe1119-...",
            capability_name="part_by_part_number_or_name",
            search_terms={"part_number": "ENG-0008-103"}
        )
    """
    executor = CapabilityExecutor(supabase_client, yacht_id)
    return executor.execute(capability_name, search_terms, limit)


def find_capability_for_query(entities: List[Dict[str, Any]]) -> Optional[str]:
    """
    Given extracted entities, find the best capability to execute.

    Args:
        entities: List of {"type": "PART_NUMBER", "value": "ENG-0008"}

    Returns:
        Capability name or None
    """
    from .table_capabilities import get_capability_for_entity

    for entity in entities:
        entity_type = entity.get("type", "")
        cap = get_capability_for_entity(entity_type)
        if cap:
            return cap.name

    return None


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    import os

    print("=" * 60)
    print("CAPABILITY EXECUTOR TEST")
    print("=" * 60)

    # Check for Supabase connection
    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase not installed")
        sys.exit(1)

    SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    executor = CapabilityExecutor(client, TEST_YACHT_ID)

    print(f"\nTesting against yacht: {TEST_YACHT_ID}")
    print()

    # Test each active capability
    test_cases = [
        ("part_by_part_number_or_name", {"name": "fuel"}),
        ("inventory_by_location", {"location": "Yacht"}),
        ("fault_by_fault_code", {"code": "1234"}),
        ("graph_node_search", {"node_type": "system"}),
    ]

    for cap_name, search_terms in test_cases:
        print(f"\n--- {cap_name} ---")
        print(f"Search: {search_terms}")
        result = executor.execute(cap_name, search_terms, limit=3)
        print(f"Success: {result.success}")
        print(f"Rows: {result.row_count}")
        print(f"Query: {result.generated_query}")
        if result.rows:
            print(f"First row keys: {list(result.rows[0].keys())[:5]}...")
        if result.error:
            print(f"Error: {result.error}")
