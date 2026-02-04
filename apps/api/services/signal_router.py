#!/usr/bin/env python3
"""
F1 Search - Signal Router

Maps extraction signals to search targets in 0ms.
NO network calls. NO DB calls. Pure CPU mapping only.

Flow: Extraction (signals) → Signal Router (this) → DB RPC (hyper_search)

See: apps/api/docs/F1_SEARCH/SIGNAL_ROUTER_SPEC.md
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import uuid

from .types import UserContext, SearchBudget, DEFAULT_BUDGET


@dataclass
class SearchTarget:
    """A single search target (shard + domain combination)."""
    shard: str      # 'exact', 'text', 'vector'
    domain: str     # 'parts', 'inventory', 'manuals', 'work_orders', 'documents'
    budget_ms: int  # Time budget for this target


@dataclass
class RoutePlan:
    """
    Complete route plan for a search query.

    Contains targets to query, concurrency policy, and user context.
    """
    search_id: str
    targets: List[SearchTarget]
    policy: Dict[str, int]
    user_context: Dict[str, Any]
    raw_query: Optional[str] = None
    entity_types: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "search_id": self.search_id,
            "targets": [asdict(t) for t in self.targets],
            "policy": self.policy,
            "user_context": self.user_context,
            "raw_query": self.raw_query,
            "entity_types": self.entity_types,
        }


# Entity type to target mapping
# Each entity type maps to a list of (shard, domain, budget_ms) tuples
ENTITY_TARGET_MAP: Dict[str, List[tuple]] = {
    # Parts-related entities
    "PartNumber": [
        ("exact", "parts", 40),
        ("exact", "inventory", 40),
        ("text", "parts", 40),
        ("vector", "parts", 120),
    ],
    "part_number": [  # Lowercase variant from regex_extractor
        ("exact", "parts", 40),
        ("exact", "inventory", 40),
        ("text", "parts", 40),
        ("vector", "parts", 120),
    ],
    "PART_NUMBER": [  # Uppercase variant
        ("exact", "parts", 40),
        ("exact", "inventory", 40),
        ("text", "parts", 40),
        ("vector", "parts", 120),
    ],
    "brand": [
        ("text", "parts", 40),
        ("vector", "parts", 120),
    ],
    "BRAND": [
        ("text", "parts", 40),
        ("vector", "parts", 120),
    ],
    "equipment_brand": [
        ("text", "parts", 40),
        ("vector", "parts", 120),
    ],
    "manufacturer": [
        ("text", "parts", 40),
        ("vector", "parts", 120),
    ],

    # Asset/Equipment entities
    "AssetAlias": [
        ("text", "manuals", 40),
        ("text", "work_orders", 40),
        ("vector", "manuals", 120),
    ],
    "equipment": [
        ("text", "parts", 40),
        ("text", "manuals", 40),
        ("vector", "manuals", 120),
    ],
    "EQUIPMENT": [
        ("text", "parts", 40),
        ("text", "manuals", 40),
        ("vector", "manuals", 120),
    ],

    # Symptom/Fault entities
    "Symptom": [
        ("text", "manuals", 40),
        ("text", "work_orders", 40),
        ("vector", "manuals", 120),
    ],
    "symptom": [
        ("text", "manuals", 40),
        ("text", "work_orders", 40),
        ("vector", "manuals", 120),
    ],
    "fault_code": [
        ("exact", "work_orders", 40),
        ("text", "manuals", 40),
        ("vector", "manuals", 120),
    ],

    # Work order entities
    "work_order_id": [
        ("exact", "work_orders", 40),
        ("text", "work_orders", 40),
    ],
    "work_order_status": [
        ("text", "work_orders", 40),
    ],

    # Document entities
    "document_id": [
        ("exact", "documents", 40),
        ("text", "documents", 40),
    ],
    "document_type": [
        ("text", "documents", 40),
        ("vector", "documents", 120),
    ],

    # Location entities
    "location_on_board": [
        ("text", "inventory", 40),
        ("text", "parts", 40),
    ],
    "LOCATION": [
        ("text", "inventory", 40),
        ("text", "parts", 40),
    ],

    # Inventory entities
    "stock_status": [
        ("text", "inventory", 40),
    ],
    "STOCK_STATUS": [
        ("text", "inventory", 40),
    ],

    # Shopping list entities
    "shopping_list_term": [
        ("text", "shopping_list", 40),
    ],
    "approval_status": [
        ("text", "shopping_list", 40),
    ],

    # Receiving entities
    "po_number": [
        ("exact", "receiving", 40),
        ("text", "receiving", 40),
    ],
    "PO_NUMBER": [
        ("exact", "receiving", 40),
        ("text", "receiving", 40),
    ],

    # Crew entities
    "REST_COMPLIANCE": [
        ("text", "crew_hours", 40),
    ],
    "WARNING_SEVERITY": [
        ("text", "crew_warnings", 40),
    ],
}

# Default targets when no entities are recognized
DEFAULT_TARGETS: List[tuple] = [
    ("text", "manuals", 40),
    ("text", "parts", 40),
    ("vector", "manuals", 120),
]


def build_route_plan(
    signals: Dict[str, Any],
    ctx: UserContext,
    budget: SearchBudget = DEFAULT_BUDGET,
    search_id: Optional[str] = None,
) -> RoutePlan:
    """
    Build a route plan from extraction signals.

    GUARDRAILS:
    - NO network calls
    - NO DB calls
    - Pure CPU mapping only (0ms target)

    Args:
        signals: Extraction output containing 'entities' list and optional 'raw_query'
        ctx: UserContext for RLS (passed through to targets)
        budget: Optional custom budget (defaults to DEFAULT_BUDGET)
        search_id: Optional search ID (generated if not provided)

    Returns:
        RoutePlan with targets, policy, and user context
    """
    # Generate search_id if not provided
    if not search_id:
        search_id = str(uuid.uuid4())

    entities = signals.get("entities", [])
    raw_query = signals.get("raw_query") or signals.get("query")

    # Collect targets from entity types
    targets: List[SearchTarget] = []
    seen: set = set()  # Dedupe (shard, domain) pairs
    entity_types: List[str] = []

    for entity in entities:
        # Handle both dict and object forms
        if isinstance(entity, dict):
            entity_type = entity.get("type") or entity.get("entity_type")
        else:
            entity_type = getattr(entity, "type", None) or getattr(entity, "entity_type", None)

        if not entity_type:
            continue

        entity_types.append(entity_type)

        # Look up targets for this entity type
        target_specs = ENTITY_TARGET_MAP.get(entity_type, [])

        for shard, domain, budget_ms in target_specs:
            key = (shard, domain)
            if key not in seen:
                seen.add(key)
                targets.append(SearchTarget(
                    shard=shard,
                    domain=domain,
                    budget_ms=budget_ms,
                ))

    # Apply default targets if none found
    if not targets:
        for shard, domain, budget_ms in DEFAULT_TARGETS:
            targets.append(SearchTarget(
                shard=shard,
                domain=domain,
                budget_ms=budget_ms,
            ))

    # Build policy from budget
    policy = {
        "global_concurrency_cap": budget.global_concurrency_cap,
        "per_domain_cap": budget.per_domain_cap,
        "global_timeout_ms": budget.global_timeout_ms,
        "db_timeout_ms": budget.db_timeout_ms,
    }

    return RoutePlan(
        search_id=search_id,
        targets=targets,
        policy=policy,
        user_context=ctx.dict,
        raw_query=raw_query,
        entity_types=entity_types if entity_types else None,
    )


def get_target_count(signals: Dict[str, Any]) -> int:
    """
    Quick count of targets that would be generated (for diagnostics).

    NO network calls. NO DB calls.
    """
    entities = signals.get("entities", [])
    seen: set = set()

    for entity in entities:
        if isinstance(entity, dict):
            entity_type = entity.get("type") or entity.get("entity_type")
        else:
            entity_type = getattr(entity, "type", None)

        if not entity_type:
            continue

        target_specs = ENTITY_TARGET_MAP.get(entity_type, [])
        for shard, domain, _ in target_specs:
            seen.add((shard, domain))

    return len(seen) if seen else len(DEFAULT_TARGETS)
