"""
Result Normalizer v1 - Unified Response Shape
==============================================

Converts raw query results into a standardized response format.

OUTPUT CONTRACT:
Every result item has:
- source_table: str          # Which table the result came from
- primary_id: str            # UUID of the record
- title: str                 # Human-readable title
- snippet: str               # Summary/description text
- entities_matched: List[Dict]  # Which entities led to this result
- score_components: Dict     # Breakdown of relevance scoring
- actions: List[Dict]        # Available actions for this result

USAGE:
    from .result_normalizer import normalize_results

    normalized = normalize_results(
        query_result=result,
        entities_matched=[{"type": "PART_NUMBER", "value": "ENG-0008"}],
    )
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

from .table_capabilities import TABLE_CAPABILITIES, Capability
from .capability_executor import QueryResult


@dataclass
class NormalizedResult:
    """A single normalized result item."""
    source_table: str
    primary_id: str
    title: str
    snippet: str
    entities_matched: List[Dict[str, Any]] = field(default_factory=list)
    score_components: Dict[str, float] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    # Original row data for reference
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding raw_data."""
        return {
            "source_table": self.source_table,
            "primary_id": self.primary_id,
            "title": self.title,
            "snippet": self.snippet,
            "entities_matched": self.entities_matched,
            "score_components": self.score_components,
            "actions": self.actions,
        }


@dataclass
class NormalizedResponse:
    """Full normalized response from a capability query."""
    success: bool
    capability: str
    results: List[NormalizedResult]
    total_count: int
    query_type: str
    error: Optional[str] = None
    # Metadata for observability
    execution_time_ms: Optional[float] = None
    generated_query: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "capability": self.capability,
            "results": [r.to_dict() for r in self.results],
            "total_count": self.total_count,
            "query_type": self.query_type,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


# =============================================================================
# TABLE-SPECIFIC NORMALIZERS
# =============================================================================

def _normalize_pms_parts(
    row: Dict[str, Any],
    entities_matched: List[Dict[str, Any]],
    capability: Capability,
) -> NormalizedResult:
    """Normalize a row from pms_parts table."""
    title = row.get("name", "Unknown Part")
    part_num = row.get("part_number", "")
    manufacturer = row.get("manufacturer", "")

    if part_num:
        title = f"{title} ({part_num})"

    snippet_parts = []
    if manufacturer:
        snippet_parts.append(f"Manufacturer: {manufacturer}")
    if row.get("category"):
        snippet_parts.append(f"Category: {row['category']}")
    if row.get("description"):
        snippet_parts.append(row["description"][:200])

    snippet = " | ".join(snippet_parts) if snippet_parts else "No description available"

    # Build actions
    actions = []
    for action_name in capability.available_actions:
        actions.append({
            "id": action_name,
            "label": _action_label(action_name),
            "enabled": True,
        })

    return NormalizedResult(
        source_table="pms_parts",
        primary_id=row.get("id", ""),
        title=title,
        snippet=snippet,
        entities_matched=entities_matched,
        score_components={"exact_match": 1.0 if part_num in str(entities_matched) else 0.5},
        actions=actions,
        raw_data=row,
    )


def _normalize_v_inventory(
    row: Dict[str, Any],
    entities_matched: List[Dict[str, Any]],
    capability: Capability,
) -> NormalizedResult:
    """Normalize a row from v_inventory view."""
    name = row.get("name", "Unknown Item")
    location = row.get("location", "Unknown Location")
    quantity = row.get("quantity", 0)
    min_qty = row.get("min_quantity", 0)

    title = f"{name} @ {location}"

    # Build snippet
    snippet_parts = [f"Qty: {quantity}"]
    if row.get("part_number"):
        snippet_parts.append(f"P/N: {row['part_number']}")
    if row.get("equipment"):
        snippet_parts.append(f"Equipment: {row['equipment']}")
    if row.get("needs_reorder"):
        snippet_parts.append("⚠ NEEDS REORDER")

    snippet = " | ".join(snippet_parts)

    # Score based on stock status
    score = 0.5
    if row.get("needs_reorder"):
        score = 1.0  # High relevance if low stock
    elif quantity > min_qty * 2:
        score = 0.3  # Lower relevance if well-stocked

    actions = []
    for action_name in capability.available_actions:
        # Disable reorder if not needed
        enabled = True
        if action_name == "reorder" and not row.get("needs_reorder"):
            enabled = False
        actions.append({
            "id": action_name,
            "label": _action_label(action_name),
            "enabled": enabled,
        })

    return NormalizedResult(
        source_table="v_inventory",
        primary_id=row.get("stock_id", row.get("part_id", "")),
        title=title,
        snippet=snippet,
        entities_matched=entities_matched,
        score_components={"stock_status": score},
        actions=actions,
        raw_data=row,
    )


def _normalize_fault_code(
    row: Dict[str, Any],
    entities_matched: List[Dict[str, Any]],
    capability: Capability,
) -> NormalizedResult:
    """Normalize a row from search_fault_code_catalog."""
    code = row.get("code", "")
    name = row.get("name", "Unknown Fault")
    severity = row.get("severity", "unknown")

    title = f"[{code}] {name}"

    snippet_parts = []
    if row.get("equipment_type"):
        snippet_parts.append(f"Equipment: {row['equipment_type']}")
    if severity:
        snippet_parts.append(f"Severity: {severity.upper()}")
    if row.get("symptoms"):
        symptoms = row["symptoms"]
        if isinstance(symptoms, list):
            snippet_parts.append(f"Symptoms: {', '.join(symptoms[:3])}")

    snippet = " | ".join(snippet_parts) if snippet_parts else "No details available"

    # Score based on severity
    severity_scores = {"critical": 1.0, "warning": 0.7, "info": 0.3}
    score = severity_scores.get(severity.lower(), 0.5) if severity else 0.5

    actions = []
    for action_name in capability.available_actions:
        actions.append({
            "id": action_name,
            "label": _action_label(action_name),
            "enabled": True,
        })

    return NormalizedResult(
        source_table="search_fault_code_catalog",
        primary_id=row.get("id", ""),
        title=title,
        snippet=snippet,
        entities_matched=entities_matched,
        score_components={"severity": score, "code_match": 1.0},
        actions=actions,
        raw_data=row,
    )


def _normalize_document_chunk(
    row: Dict[str, Any],
    entities_matched: List[Dict[str, Any]],
    capability: Capability,
) -> NormalizedResult:
    """Normalize a row from search_document_chunks or RPC result."""
    # RPC returns different structure
    title = row.get("section_title") or row.get("title") or "Document"
    content = row.get("content") or row.get("text") or ""

    # Truncate content for snippet
    snippet = content[:300] + "..." if len(content) > 300 else content
    snippet = snippet.replace("\n", " ").strip()

    if row.get("page_number"):
        title = f"{title} (Page {row['page_number']})"

    actions = []
    for action_name in capability.available_actions:
        actions.append({
            "id": action_name,
            "label": _action_label(action_name),
            "enabled": True,
        })

    # Score from RPC or default
    score = row.get("similarity", row.get("score", 0.5))

    return NormalizedResult(
        source_table="search_document_chunks",
        primary_id=row.get("id", row.get("chunk_id", "")),
        title=title,
        snippet=snippet,
        entities_matched=entities_matched,
        score_components={"similarity": score},
        actions=actions,
        raw_data=row,
    )


def _normalize_graph_node(
    row: Dict[str, Any],
    entities_matched: List[Dict[str, Any]],
    capability: Capability,
) -> NormalizedResult:
    """Normalize a row from graph_nodes."""
    label = row.get("label", "Unknown")
    node_type = row.get("node_type", "entity")
    normalized_label = row.get("normalized_label", label)

    title = f"{label.replace('_', ' ').title()} ({node_type})"

    snippet_parts = [f"Type: {node_type}"]
    if row.get("extraction_source"):
        snippet_parts.append(f"Source: {row['extraction_source']}")
    if row.get("confidence"):
        snippet_parts.append(f"Confidence: {row['confidence']}")

    snippet = " | ".join(snippet_parts)

    actions = []
    for action_name in capability.available_actions:
        actions.append({
            "id": action_name,
            "label": _action_label(action_name),
            "enabled": True,
        })

    return NormalizedResult(
        source_table="graph_nodes",
        primary_id=row.get("id", ""),
        title=title,
        snippet=snippet,
        entities_matched=entities_matched,
        score_components={"confidence": float(row.get("confidence", 0.5))},
        actions=actions,
        raw_data=row,
    )


def _normalize_generic(
    row: Dict[str, Any],
    table_name: str,
    entities_matched: List[Dict[str, Any]],
    capability: Capability,
) -> NormalizedResult:
    """Generic normalizer for unknown tables."""
    # Try common title fields
    title = (
        row.get("name") or
        row.get("title") or
        row.get("label") or
        row.get("code") or
        str(row.get("id", "Unknown"))[:50]
    )

    # Try common description fields
    snippet = (
        row.get("description") or
        row.get("content") or
        row.get("text") or
        row.get("snippet") or
        "No description available"
    )
    if len(snippet) > 300:
        snippet = snippet[:300] + "..."

    actions = []
    for action_name in capability.available_actions:
        actions.append({
            "id": action_name,
            "label": _action_label(action_name),
            "enabled": True,
        })

    return NormalizedResult(
        source_table=table_name,
        primary_id=str(row.get("id", "")),
        title=str(title),
        snippet=snippet,
        entities_matched=entities_matched,
        score_components={"generic": 0.5},
        actions=actions,
        raw_data=row,
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _action_label(action_id: str) -> str:
    """Convert action ID to human-readable label."""
    labels = {
        "view_details": "View Details",
        "check_stock": "Check Stock",
        "order_part": "Order Part",
        "view_stock": "View Stock",
        "reorder": "Reorder",
        "transfer_stock": "Transfer Stock",
        "adjust_quantity": "Adjust Quantity",
        "start_diagnostic": "Start Diagnostic",
        "log_fault": "Log Fault",
        "view_resolution": "View Resolution",
        "view_document": "View Document",
        "download_pdf": "Download PDF",
        "extract_procedure": "Extract Procedure",
        "view_node": "View Node",
        "view_connections": "View Connections",
        "expand_graph": "Expand Graph",
    }
    return labels.get(action_id, action_id.replace("_", " ").title())


# Mapping of table names to normalizer functions
TABLE_NORMALIZERS = {
    "pms_parts": _normalize_pms_parts,
    "v_inventory": _normalize_v_inventory,
    "search_fault_code_catalog": _normalize_fault_code,
    "search_document_chunks": _normalize_document_chunk,
    "graph_nodes": _normalize_graph_node,
}


# =============================================================================
# MAIN NORMALIZATION FUNCTION
# =============================================================================

def normalize_results(
    query_result: QueryResult,
    entities_matched: Optional[List[Dict[str, Any]]] = None,
) -> NormalizedResponse:
    """
    Normalize a QueryResult into standardized response format.

    Args:
        query_result: Result from CapabilityExecutor
        entities_matched: Entities that triggered this search

    Returns:
        NormalizedResponse with standardized results
    """
    if not query_result.success:
        return NormalizedResponse(
            success=False,
            capability=query_result.capability_name,
            results=[],
            total_count=0,
            query_type=query_result.query_type,
            error=query_result.error,
            execution_time_ms=query_result.execution_time_ms,
            generated_query=query_result.generated_query,
        )

    entities = entities_matched or []

    # Get capability for actions
    capability = TABLE_CAPABILITIES.get(query_result.capability_name)
    if not capability:
        return NormalizedResponse(
            success=False,
            capability=query_result.capability_name,
            results=[],
            total_count=0,
            query_type="error",
            error=f"Unknown capability: {query_result.capability_name}",
        )

    # Get appropriate normalizer
    normalizer = TABLE_NORMALIZERS.get(query_result.table_name, None)

    # Normalize each row
    normalized_results = []
    for row in query_result.rows:
        if normalizer:
            result = normalizer(row, entities, capability)
        else:
            result = _normalize_generic(row, query_result.table_name, entities, capability)
        normalized_results.append(result)

    return NormalizedResponse(
        success=True,
        capability=query_result.capability_name,
        results=normalized_results,
        total_count=query_result.row_count,
        query_type=query_result.query_type,
        execution_time_ms=query_result.execution_time_ms,
        generated_query=query_result.generated_query,
    )


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    import os
    import json

    print("=" * 60)
    print("RESULT NORMALIZER TEST")
    print("=" * 60)

    try:
        from supabase import create_client
        from .capability_executor import CapabilityExecutor
    except ImportError as e:
        print(f"Import error: {e}")
        sys.exit(1)

    SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    executor = CapabilityExecutor(client, TEST_YACHT_ID)

    # Test normalization for each capability
    test_cases = [
        ("part_by_part_number_or_name", {"name": "fuel"}, [{"type": "PART_NAME", "value": "fuel"}]),
        ("inventory_by_location", {"location": "Yacht"}, [{"type": "LOCATION", "value": "Yacht"}]),
        ("fault_by_fault_code", {"code": "1234"}, [{"type": "FAULT_CODE", "value": "1234"}]),
    ]

    for cap_name, search_terms, entities in test_cases:
        print(f"\n{'='*40}")
        print(f"Capability: {cap_name}")
        print(f"{'='*40}")

        result = executor.execute(cap_name, search_terms, limit=2)
        normalized = normalize_results(result, entities)

        print(f"Success: {normalized.success}")
        print(f"Total: {normalized.total_count}")

        for i, r in enumerate(normalized.results):
            print(f"\n  Result {i+1}:")
            print(f"    source_table: {r.source_table}")
            print(f"    primary_id: {r.primary_id[:20]}...")
            print(f"    title: {r.title}")
            print(f"    snippet: {r.snippet[:80]}...")
            print(f"    entities_matched: {r.entities_matched}")
            print(f"    score_components: {r.score_components}")
            print(f"    actions: {[a['id'] for a in r.actions]}")
