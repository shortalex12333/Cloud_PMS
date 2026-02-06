"""
Action Surfacing Layer
======================

Integrates search results with microaction buttons.

Flow:
1. Worker 1 (Detective) detects {intent, domain, entity} from query
2. Worker 2 (Sniper) calls f1_search_fusion with domain boost
3. This layer surfaces relevant microaction buttons with prefill

Usage:
    from action_surfacing import surface_actions_for_query

    result = await surface_actions_for_query(
        query="show me hours of rest",
        role="crew",
        yacht_id="...",
        search_results=[...]  # From f1_search_fusion
    )

    # Returns:
    {
        "domain": "hours_of_rest",
        "intent": "READ",
        "mode": "explore",
        "domain_boost": 0.30,
        "actions": [
            {
                "action": "view_hours_of_rest",
                "label": "View Hours of Rest",
                "side_effect": "read_only",
                "requires_confirm": false,
                "prefill": {
                    "crew_id": "uuid-from-top-result"
                }
            },
            ...
        ]
    }
"""

from typing import Dict, List, Optional, Any
from domain_microactions import (
    detect_domain_from_query,
    detect_intent_from_query,
    get_microactions_for_query,
    DOMAIN_KEYWORDS,
)


def surface_actions_for_query(
    query: str,
    role: str,
    search_results: Optional[List[Dict[str, Any]]] = None,
    yacht_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Surface microaction buttons for a query with prefill from search results.

    Args:
        query: User query text
        role: User role (crew, engineer, hod, captain, admin)
        search_results: Results from f1_search_fusion (for prefill)
        yacht_id: Yacht ID (for security validation)

    Returns:
        Dict with domain, intent, mode, domain_boost, and actions
    """
    # Detect domain and intent
    domain_result = detect_domain_from_query(query)
    intent = detect_intent_from_query(query)

    # Part number detection - if query contains a part number pattern, set domain=part
    part_number_match = PART_NUMBER_PATTERN.search(query)
    if part_number_match and not domain_result:
        domain_result = ('part', 0.25)

    if domain_result:
        domain, domain_boost = domain_result
    else:
        domain = None
        domain_boost = 0.0

    # Determine mode based on intent and domain
    # Explicit domain queries → focused mode
    # Exploratory queries → explore mode
    if domain and intent in ('READ', 'UPDATE', 'DELETE', 'EXPORT', 'APPROVE'):
        mode = 'focused'
    else:
        mode = 'explore'

    # Get top result for prefill
    entity_id = None
    entity_name = None
    entity_data = None

    if search_results and len(search_results) > 0:
        top_result = search_results[0]
        entity_id = str(top_result.get('object_id', ''))

        # Extract name from payload
        payload = top_result.get('payload', {})
        if isinstance(payload, dict):
            entity_name = (
                payload.get('name') or
                payload.get('title') or
                payload.get('part_number') or
                payload.get('equipment_name') or
                payload.get('description', '')[:50]
            )
            entity_data = payload

    # Get microactions filtered by role
    actions = get_microactions_for_query(
        query=query,
        role=role,
        entity_id=entity_id,
        entity_name=entity_name,
        entity_data=entity_data
    )

    return {
        'domain': domain,
        'intent': intent,
        'mode': mode,
        'domain_boost': domain_boost,
        'actions': actions,
        'top_entity': {
            'id': entity_id,
            'name': entity_name,
            'type': search_results[0].get('object_type') if search_results else None
        } if entity_id else None
    }


import re

# Part number pattern: 2+ uppercase letters, optional separator, digit, 3+ more alphanumeric/dashes
# Examples: FLT-0170-576, ABC123, MTU-123-456
PART_NUMBER_PATTERN = re.compile(r'\b[A-Z]{2,}[- ]?\d[\dA-Z\-]{3,}\b', re.IGNORECASE)


def get_fusion_params_for_query(query: str) -> Dict[str, Any]:
    """
    Get f1_search_fusion parameters based on query analysis.

    Returns parameters to pass to the fusion function:
    - p_domain: detected domain
    - p_mode: 'focused' or 'explore'
    - p_domain_boost: boost value

    Usage:
        params = get_fusion_params_for_query("show me hours of rest")
        results = f1_search_fusion(
            yacht_id,
            query,
            embedding,
            role,
            lens,
            **params  # domain, mode, domain_boost
        )
    """
    q = (query or "").lower()
    domain_result = detect_domain_from_query(q)
    intent = detect_intent_from_query(q)

    # Part number detection - if query contains a part number pattern, set domain=parts
    part_number_match = PART_NUMBER_PATTERN.search(query)
    if part_number_match and not domain_result:
        domain_result = ('parts', 0.25)

    if domain_result:
        domain, domain_boost = domain_result
        # Normalize 'parts' → 'part' for consistency
        if domain == 'parts':
            domain = 'part'
    else:
        return {
            'p_domain': None,
            'p_mode': 'explore',
            'p_domain_boost': 0.0
        }

    # Determine mode
    if intent in ('READ', 'UPDATE', 'DELETE', 'EXPORT', 'APPROVE', 'REJECT'):
        mode = 'focused'
    else:
        mode = 'explore'

    # Build structured filters (p_filters) from query terms
    p_filters: Dict[str, Any] = {}

    # Status filters for receiving
    # Note: "accepted deliveries" means status=accepted (adjective), not APPROVE action
    if any(tok in q for tok in [' draft ', ' status:draft', 'status draft', ' in draft', 'draft status']):
        p_filters['status'] = 'draft'
    elif any(tok in q for tok in [' in progress', 'in-progress', 'status:in_progress']):
        p_filters['status'] = 'in_progress'
    elif any(tok in q for tok in [' rejected', 'status:rejected']):
        p_filters['status'] = 'rejected'
    elif any(tok in q for tok in ['accepted deliveries', 'accepted receiving', 'accepted shipment', ' approved', 'status:approved']):
        p_filters['status'] = 'accepted'

    # Compliance filters for hours_of_rest
    if any(tok in q for tok in [' violation', 'violations', 'non-compliant', 'non compliant']):
        p_filters['compliance_state'] = 'violation'
    elif any(tok in q for tok in [' compliant', 'compliance ok']):
        p_filters['compliance_state'] = 'compliant'

    # Item content filter for receiving line items (best-effort)
    # e.g., "fuel filter elements", "oil filter", "gasket"
    for kw in ['fuel filter', 'filter element', 'oil filter', 'gasket', 'element']:
        if kw in q:
            p_filters['item_contains'] = kw
            break

    params = {
        'p_domain': domain,
        'p_mode': mode,
        'p_domain_boost': domain_boost,
    }

    if p_filters:
        params['p_filters'] = p_filters

    return params


# =============================================================================
# API INTEGRATION HELPERS
# =============================================================================

def build_action_response(
    query: str,
    role: str,
    search_results: List[Dict[str, Any]],
    include_debug: bool = False
) -> Dict[str, Any]:
    """
    Build complete response with search results + actions.

    This is what the API returns to the frontend.
    """
    action_data = surface_actions_for_query(
        query=query,
        role=role,
        search_results=search_results
    )

    response = {
        'results': search_results,
        'actions': action_data['actions'],
        'context': {
            'domain': action_data['domain'],
            'intent': action_data['intent'],
            'mode': action_data['mode'],
        }
    }

    if include_debug:
        response['debug'] = {
            'domain_boost': action_data['domain_boost'],
            'top_entity': action_data['top_entity']
        }

    return response


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    # Test the action surfacing
    test_queries = [
        ("show me hours of rest", "crew"),
        ("update stock for filter ABC-123", "engineer"),
        ("reduce inventory for pump seal", "engineer"),
        ("create work order for generator", "hod"),
        ("view equipment manual", "crew"),
        ("approve purchase order", "captain"),
        ("export compliance report", "captain"),
    ]

    print("=" * 70)
    print(" Action Surfacing Tests")
    print("=" * 70)

    for query, role in test_queries:
        result = surface_actions_for_query(query, role)

        print(f"\nQuery: \"{query}\"")
        print(f"Role: {role}")
        print(f"Domain: {result['domain']}")
        print(f"Intent: {result['intent']}")
        print(f"Mode: {result['mode']}")
        print(f"Boost: {result['domain_boost']}")
        print(f"Actions ({len(result['actions'])}):")
        for action in result['actions'][:3]:  # Show first 3
            print(f"  - [{action['label']}] → {action['action']}")

        print("-" * 40)
