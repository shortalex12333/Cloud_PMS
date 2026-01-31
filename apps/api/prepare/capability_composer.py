"""
Capability Composer v1 - Multi-Entity Query Execution
======================================================

Handles queries that span multiple capabilities by:
1. Mapping entities to capabilities
2. Running capabilities in PARALLEL
3. Merging results at RESPONSE level (NOT SQL joins)

Example:
    Query: "impeller location main engine"
    Entities: [PART_NAME: impeller, LOCATION: main engine]
    Capabilities: [part_by_part_number_or_name, inventory_by_location]
    Execution: parallel
    Merge: by entities_matched intersection

NO SQL JOINS. Joins multiply failure modes.

USAGE:
    from api.capability_composer import compose_search

    response = compose_search(
        supabase_client=client,
        yacht_id="85fe1119-...",
        entities=[
            {"type": "PART_NAME", "value": "impeller"},
            {"type": "LOCATION", "value": "main engine"},
        ]
    )
"""

import time
import concurrent.futures
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from execute.table_capabilities import (
    TABLE_CAPABILITIES,
    CapabilityStatus,
    get_capability_for_entity,
    get_active_capabilities,
)
from execute.capability_executor import CapabilityExecutor, QueryResult
from execute.result_normalizer import (
    normalize_results,
    NormalizedResult,
    NormalizedResponse,
)


class MergeStrategy(Enum):
    """How to merge results from multiple capabilities."""
    UNION = "union"           # All results from all capabilities
    INTERSECTION = "intersection"  # Only results matching multiple entities
    RANKED = "ranked"         # Union with cross-capability boost


@dataclass
class CapabilityPlan:
    """Plan for executing a single capability."""
    capability_name: str
    entity_type: str
    entity_value: Any
    search_column: str
    blocked: bool = False
    blocked_reason: Optional[str] = None


@dataclass
class ComposedResponse:
    """Response from composed multi-capability search."""
    success: bool
    results: List[NormalizedResult]
    total_count: int
    # Observability fields
    capabilities_considered: List[str]
    capabilities_executed: List[str]
    capabilities_blocked: List[Dict[str, str]]  # [{name, reason}]
    capabilities_timed_out: List[Dict[str, str]]  # [{name, reason}] - NEW
    execution_times_ms: Dict[str, float]  # capability -> time
    rows_per_capability: Dict[str, int]  # capability -> count
    merge_strategy: str
    total_execution_time_ms: float
    partial_results: bool = False  # True if some capabilities timed out
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "results": [r.to_dict() for r in self.results],
            "total_count": self.total_count,
            "meta": {
                "capabilities_considered": self.capabilities_considered,
                "capabilities_executed": self.capabilities_executed,
                "capabilities_blocked": self.capabilities_blocked,
                "capabilities_timed_out": self.capabilities_timed_out,
                "execution_times_ms": self.execution_times_ms,
                "rows_per_capability": self.rows_per_capability,
                "merge_strategy": self.merge_strategy,
                "total_execution_time_ms": self.total_execution_time_ms,
                "partial_results": self.partial_results,
            },
            "error": self.error,
        }


# =============================================================================
# ENTITY TO CAPABILITY MAPPING
# =============================================================================

# Map entity types to search columns in their target capability
ENTITY_TO_SEARCH_COLUMN: Dict[str, Tuple[str, str]] = {
    # (entity_type) -> (capability_name, search_column)
    "PART_NUMBER": ("part_by_part_number_or_name", "part_number"),
    "PART_NAME": ("part_by_part_number_or_name", "name"),
    "MANUFACTURER": ("part_by_part_number_or_name", "manufacturer"),
    "LOCATION": ("inventory_by_location", "location"),
    "STOCK_QUERY": ("inventory_by_location", "name"),
    "FAULT_CODE": ("fault_by_fault_code", "code"),
    "SYMPTOM": ("fault_by_fault_code", "name"),
    "EQUIPMENT_TYPE": ("fault_by_fault_code", "equipment_type"),
    "DOCUMENT_QUERY": ("documents_search", "content"),
    "MANUAL_SEARCH": ("documents_search", "content"),
    "PROCEDURE_SEARCH": ("documents_search", "content"),
    "ENTITY_LOOKUP": ("graph_node_search", "label"),
    "SYSTEM_NAME": ("graph_node_search", "label"),
    "COMPONENT_NAME": ("graph_node_search", "label"),
    # Work Order Lens (multiple search strategies)
    "WORK_ORDER_ID": ("work_order_by_id", "wo_number"),
    "WO_NUMBER": ("work_order_by_id", "wo_number"),
    "WORK_ORDER_TITLE": ("work_order_by_id", "title"),
    "WORK_ORDER_DESCRIPTION": ("work_order_by_id", "description"),
    "WORK_ORDER_EQUIPMENT": ("work_order_by_id", "title"),
    # Equipment Lens
    "EQUIPMENT_NAME": ("equipment_by_name_or_model", "name"),
    "MODEL_NUMBER": ("equipment_by_name_or_model", "model"),
    # Email transport layer (evidence search)
    "EMAIL_SUBJECT": ("email_threads_search", "latest_subject"),
    "EMAIL_SEARCH": ("email_threads_search", "latest_subject"),
    # Crew Lens - Hours of Rest (only types that map to actual columns)
    "REST_COMPLIANCE": ("crew_hours_of_rest_search", "compliance_status"),
    "WARNING_SEVERITY": ("crew_warnings_search", "severity"),
    "WARNING_STATUS": ("crew_warnings_search", "status"),
    # Shopping List Lens (6 types)
    "SHOPPING_LIST_ITEM": ("shopping_list_by_item_or_status", "part_name"),
    "REQUESTED_PART": ("shopping_list_by_item_or_status", "part_name"),
    "REQUESTER_NAME": ("shopping_list_by_item_or_status", "requested_by"),
    "URGENCY_LEVEL": ("shopping_list_by_item_or_status", "urgency"),
    "APPROVAL_STATUS": ("shopping_list_by_item_or_status", "status"),
    "SOURCE_TYPE": ("shopping_list_by_item_or_status", "source_type"),
    # Receiving Lens (7 types)
    "PO_NUMBER": ("receiving_by_po_or_supplier", "vendor_reference"),
    "RECEIVING_ID": ("receiving_by_po_or_supplier", "id"),
    "SUPPLIER_NAME": ("receiving_by_po_or_supplier", "vendor_name"),
    "INVOICE_NUMBER": ("receiving_by_po_or_supplier", "vendor_reference"),
    "DELIVERY_DATE": ("receiving_by_po_or_supplier", "received_date"),
    "RECEIVER_NAME": ("receiving_by_po_or_supplier", "received_by"),
    "RECEIVING_STATUS": ("receiving_by_po_or_supplier", "status"),
}


def plan_capabilities(entities: List[Dict[str, Any]]) -> List[CapabilityPlan]:
    """
    Map entities to capability execution plans.

    Returns list of plans, some may be blocked.
    """
    plans = []
    active_caps = get_active_capabilities()

    for entity in entities:
        entity_type = entity.get("type", "")
        entity_value = entity.get("value", "")

        if not entity_type or not entity_value:
            continue

        # Look up capability and column
        mapping = ENTITY_TO_SEARCH_COLUMN.get(entity_type)
        if not mapping:
            # Unknown entity type - skip silently
            continue

        cap_name, search_col = mapping

        # Check if capability is active
        if cap_name not in active_caps:
            cap = TABLE_CAPABILITIES.get(cap_name)
            plans.append(CapabilityPlan(
                capability_name=cap_name,
                entity_type=entity_type,
                entity_value=entity_value,
                search_column=search_col,
                blocked=True,
                blocked_reason=cap.blocked_reason if cap else "Unknown capability",
            ))
        else:
            plans.append(CapabilityPlan(
                capability_name=cap_name,
                entity_type=entity_type,
                entity_value=entity_value,
                search_column=search_col,
                blocked=False,
            ))

    return plans


# =============================================================================
# PARALLEL EXECUTION
# =============================================================================

def execute_capability(
    executor: CapabilityExecutor,
    plan: CapabilityPlan,
    limit: int = 20,
) -> Tuple[str, QueryResult, float]:
    """
    Execute a single capability plan.
    Returns (capability_name, result, execution_time_ms)
    """
    start = time.time()

    search_terms = {plan.search_column: plan.entity_value}
    result = executor.execute(plan.capability_name, search_terms, limit=limit)

    elapsed = (time.time() - start) * 1000
    return (plan.capability_name, result, elapsed)


@dataclass
class TimeoutMeta:
    """Metadata about timeouts during execution."""
    timed_out_capabilities: List[str] = field(default_factory=list)
    timeout_reasons: Dict[str, str] = field(default_factory=dict)


def execute_plans_parallel(
    executor: CapabilityExecutor,
    plans: List[CapabilityPlan],
    limit_per_capability: int = 20,
    max_workers: int = 4,
    timeout_per_capability_ms: float = 5000.0,  # 5 second default
) -> Tuple[Dict[str, Tuple[QueryResult, float]], TimeoutMeta]:
    """
    Execute multiple capability plans in parallel with per-capability timeouts.

    Returns:
        - dict of capability_name -> (result, execution_time_ms)
        - TimeoutMeta with info about any timeouts

    IMPORTANT: One slow capability does NOT block others.
    Partial results are returned even if some capabilities timeout.
    """
    active_plans = [p for p in plans if not p.blocked]
    timeout_meta = TimeoutMeta()

    if not active_plans:
        return {}, timeout_meta

    results = {}
    timeout_seconds = timeout_per_capability_ms / 1000.0

    # Use thread pool for parallel HTTP requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(execute_capability, executor, plan, limit_per_capability): plan
            for plan in active_plans
        }

        # Wait for each with individual timeout
        for future in concurrent.futures.as_completed(futures, timeout=timeout_seconds * 2):
            plan = futures[future]
            try:
                # Per-capability timeout
                cap_name, result, elapsed = future.result(timeout=timeout_seconds)
                results[cap_name] = (result, elapsed)
            except concurrent.futures.TimeoutError:
                # This capability timed out - add to timeout metadata
                timeout_meta.timed_out_capabilities.append(plan.capability_name)
                timeout_meta.timeout_reasons[plan.capability_name] = (
                    f"Exceeded {timeout_per_capability_ms:.0f}ms timeout"
                )
                # Create timeout result
                timeout_result = QueryResult(
                    success=False,
                    capability_name=plan.capability_name,
                    table_name="",
                    rows=[],
                    row_count=0,
                    query_type="timeout",
                    error=f"Timeout after {timeout_per_capability_ms:.0f}ms",
                )
                results[plan.capability_name] = (timeout_result, timeout_per_capability_ms)
            except Exception as e:
                # Create error result
                error_result = QueryResult(
                    success=False,
                    capability_name=plan.capability_name,
                    table_name="",
                    rows=[],
                    row_count=0,
                    query_type="error",
                    error=str(e),
                )
                results[plan.capability_name] = (error_result, 0.0)

    return results, timeout_meta


# =============================================================================
# RESULT MERGING
# =============================================================================

def merge_results(
    results_by_capability: Dict[str, Tuple[QueryResult, float]],
    entities: List[Dict[str, Any]],
    strategy: MergeStrategy = MergeStrategy.UNION,
) -> List[NormalizedResult]:
    """
    Merge results from multiple capabilities.

    Strategies:
    - UNION: All results, deduplicated by primary_id
    - INTERSECTION: Only results matching entities from multiple capabilities
    - RANKED: Union with boost for cross-capability matches
    """
    all_normalized = []
    seen_ids: Set[str] = set()

    for cap_name, (result, _) in results_by_capability.items():
        if not result.success:
            continue

        # Find entities that triggered this capability
        cap_entities = [
            e for e in entities
            if ENTITY_TO_SEARCH_COLUMN.get(e.get("type", ""), ("", ""))[0] == cap_name
        ]

        normalized = normalize_results(result, cap_entities)

        for nr in normalized.results:
            # Deduplicate by primary_id
            if nr.primary_id and nr.primary_id not in seen_ids:
                seen_ids.add(nr.primary_id)
                all_normalized.append(nr)

    if strategy == MergeStrategy.RANKED:
        # Boost results that match entities from multiple capabilities
        # For now, just sort by score sum
        all_normalized.sort(
            key=lambda r: sum(r.score_components.values()),
            reverse=True
        )

    return all_normalized


# =============================================================================
# MAIN COMPOSITION FUNCTION
# =============================================================================

def compose_search(
    supabase_client,
    yacht_id: str,
    entities: List[Dict[str, Any]],
    limit_per_capability: int = 20,
    merge_strategy: MergeStrategy = MergeStrategy.UNION,
    timeout_per_capability_ms: float = 5000.0,  # 5 second default per capability
) -> ComposedResponse:
    """
    Execute a composed search across multiple capabilities.

    Args:
        supabase_client: Supabase client instance
        yacht_id: UUID of the yacht
        entities: List of extracted entities [{type, value}, ...]
        limit_per_capability: Max results per capability
        merge_strategy: How to merge results
        timeout_per_capability_ms: Max time per capability (default 5s)
            One slow capability does NOT block others.

    Returns:
        ComposedResponse with merged results and observability data.
        If some capabilities timeout, partial_results=True and
        capabilities_timed_out contains the timeout details.
    """
    total_start = time.time()

    # Plan execution
    plans = plan_capabilities(entities)

    if not plans:
        return ComposedResponse(
            success=True,
            results=[],
            total_count=0,
            capabilities_considered=[],
            capabilities_executed=[],
            capabilities_blocked=[],
            capabilities_timed_out=[],
            execution_times_ms={},
            rows_per_capability={},
            merge_strategy=merge_strategy.value,
            total_execution_time_ms=(time.time() - total_start) * 1000,
            partial_results=False,
            error="No capabilities matched the provided entities",
        )

    # Collect observability data
    considered = list(set(p.capability_name for p in plans))
    blocked = [
        {"name": p.capability_name, "reason": p.blocked_reason or "Unknown"}
        for p in plans if p.blocked
    ]

    # Create executor
    try:
        executor = CapabilityExecutor(supabase_client, yacht_id)
    except Exception as e:
        return ComposedResponse(
            success=False,
            results=[],
            total_count=0,
            capabilities_considered=considered,
            capabilities_executed=[],
            capabilities_blocked=blocked,
            capabilities_timed_out=[],
            execution_times_ms={},
            rows_per_capability={},
            merge_strategy=merge_strategy.value,
            total_execution_time_ms=(time.time() - total_start) * 1000,
            partial_results=False,
            error=str(e),
        )

    # Execute in parallel with per-capability timeouts
    results_by_cap, timeout_meta = execute_plans_parallel(
        executor, plans, limit_per_capability,
        timeout_per_capability_ms=timeout_per_capability_ms
    )

    # Build observability
    executed = [cap for cap, (result, _) in results_by_cap.items() if result.success]
    execution_times = {cap: time_ms for cap, (_, time_ms) in results_by_cap.items()}
    rows_per_cap = {
        cap: result.row_count
        for cap, (result, _) in results_by_cap.items()
    }

    # Build timeout info
    timed_out = [
        {"name": cap, "reason": timeout_meta.timeout_reasons.get(cap, "Timeout")}
        for cap in timeout_meta.timed_out_capabilities
    ]

    # Merge results (only successful capabilities contribute)
    merged = merge_results(results_by_cap, entities, merge_strategy)

    total_time = (time.time() - total_start) * 1000

    return ComposedResponse(
        success=True,
        results=merged,
        total_count=len(merged),
        capabilities_considered=considered,
        capabilities_executed=executed,
        capabilities_blocked=blocked,
        capabilities_timed_out=timed_out,
        execution_times_ms=execution_times,
        rows_per_capability=rows_per_cap,
        merge_strategy=merge_strategy.value,
        total_execution_time_ms=total_time,
        partial_results=len(timed_out) > 0,
    )


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    import os
    import json

    print("=" * 60)
    print("CAPABILITY COMPOSER TEST")
    print("=" * 60)

    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase not installed")
        sys.exit(1)

    SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Test cases for multi-entity queries
    test_cases = [
        {
            "name": "Single entity (part name)",
            "entities": [{"type": "PART_NAME", "value": "fuel"}],
        },
        {
            "name": "Two entities, same capability",
            "entities": [
                {"type": "PART_NAME", "value": "fuel"},
                {"type": "MANUFACTURER", "value": "MTU"},
            ],
        },
        {
            "name": "Two entities, different capabilities",
            "entities": [
                {"type": "PART_NAME", "value": "oil"},
                {"type": "LOCATION", "value": "Yacht"},
            ],
        },
        {
            "name": "Three entities across capabilities",
            "entities": [
                {"type": "PART_NAME", "value": "filter"},
                {"type": "LOCATION", "value": "Yacht"},
                {"type": "FAULT_CODE", "value": "1234"},
            ],
        },
        {
            "name": "Blocked capability (work order)",
            "entities": [
                {"type": "WORK_ORDER_ID", "value": "WO-123"},
            ],
        },
    ]

    for tc in test_cases:
        print(f"\n{'='*50}")
        print(f"Test: {tc['name']}")
        print(f"Entities: {tc['entities']}")
        print(f"{'='*50}")

        response = compose_search(
            client,
            TEST_YACHT_ID,
            tc["entities"],
            limit_per_capability=5,
        )

        print(f"Success: {response.success}")
        print(f"Results: {response.total_count}")
        print(f"Considered: {response.capabilities_considered}")
        print(f"Executed: {response.capabilities_executed}")
        print(f"Blocked: {response.capabilities_blocked}")
        print(f"Execution times: {response.execution_times_ms}")
        print(f"Rows per cap: {response.rows_per_capability}")
        print(f"Total time: {response.total_execution_time_ms:.1f}ms")

        if response.results:
            print(f"\nFirst result:")
            r = response.results[0]
            print(f"  table: {r.source_table}")
            print(f"  title: {r.title}")
            print(f"  entities_matched: {r.entities_matched}")
