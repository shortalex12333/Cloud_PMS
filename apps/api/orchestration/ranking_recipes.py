"""
Ranking Recipes - Concrete Weight Configurations
==================================================

Deterministic ranking weights. No ML, no black box.
Each recipe is a set of weights that sum to 1.0.

Recipes are selected based on surface state and query type.
"""

from typing import Dict, Any

# =============================================================================
# LOCKED RANKING RECIPES
# =============================================================================
# Each recipe defines weights for different scoring signals.
# Weights MUST sum to 1.0 for each recipe.
# These are deterministic - same input always produces same ranking.

RANKING_RECIPES: Dict[str, Dict[str, float]] = {
    # -------------------------------------------------------------------------
    # Global Search (default)
    # -------------------------------------------------------------------------
    # Used for general search bar queries across all domains.
    "global_search": {
        "similarity": 0.35,         # Vector similarity score
        "entity_overlap": 0.25,     # Exact entity ID matches
        "recency": 0.20,            # Newer items ranked higher
        "exact_match_boost": 0.20,  # Exact text matches (part numbers, WO IDs)
    },

    # -------------------------------------------------------------------------
    # Email Search
    # -------------------------------------------------------------------------
    # Used when searching within email surface.
    "email_search": {
        "similarity": 0.30,         # Subject/meta embedding similarity
        "sender_match": 0.20,       # Sender address/name match
        "subject_match": 0.20,      # Subject line keyword match
        "recency": 0.15,            # Newer emails first
        "thread_cohesion": 0.15,    # Same conversation_id boost
    },

    # -------------------------------------------------------------------------
    # Email Inbox (no query)
    # -------------------------------------------------------------------------
    # System-triggered inbox fetch. No semantic search.
    "email_inbox": {
        "recency": 0.60,            # Most recent first
        "unread_boost": 0.25,       # Unread emails surface higher
        "has_attachments": 0.10,    # Emails with attachments
        "priority_flag": 0.05,      # High importance flag
    },

    # -------------------------------------------------------------------------
    # Entity Context
    # -------------------------------------------------------------------------
    # When viewing a specific entity (WO, equipment, etc.)
    "entity_context": {
        "entity_relation": 0.40,    # Direct FK relationship to open entity
        "recency": 0.25,            # Recent activity
        "similarity": 0.20,         # Semantic similarity to entity
        "same_system": 0.15,        # Same equipment system
    },

    # -------------------------------------------------------------------------
    # Document Search
    # -------------------------------------------------------------------------
    # Searching for documents/manuals.
    "document_search": {
        "similarity": 0.40,         # Semantic match to query
        "doc_type_match": 0.20,     # Correct document type (manual, schematic)
        "equipment_match": 0.20,    # Related to mentioned equipment
        "recency": 0.10,            # More recent versions
        "page_relevance": 0.10,     # Specific page/section match
    },

    # -------------------------------------------------------------------------
    # Fault Diagnosis
    # -------------------------------------------------------------------------
    # When diagnosing a fault or symptom.
    "fault_diagnosis": {
        "symptom_match": 0.35,      # Symptom pattern match
        "equipment_match": 0.25,    # Same equipment
        "similarity": 0.20,         # Semantic similarity
        "recurrence": 0.15,         # Has happened before
        "severity": 0.05,           # Higher severity first
    },

    # -------------------------------------------------------------------------
    # Work Order History
    # -------------------------------------------------------------------------
    # Viewing work order history for equipment.
    "work_order_history": {
        "equipment_match": 0.35,    # Same equipment
        "recency": 0.30,            # Most recent first
        "status_priority": 0.20,    # Open > In Progress > Closed
        "similarity": 0.15,         # Semantic match
    },
}


def get_ranking_recipe(recipe_name: str) -> Dict[str, float]:
    """
    Get ranking weights by recipe name.
    Falls back to global_search if not found.
    """
    return RANKING_RECIPES.get(recipe_name, RANKING_RECIPES["global_search"])


def validate_recipe(recipe: Dict[str, float]) -> bool:
    """
    Validate that recipe weights sum to 1.0 (within tolerance).
    """
    total = sum(recipe.values())
    return abs(total - 1.0) < 0.01


def get_recipe_for_surface(surface_state: str, has_query: bool = True) -> str:
    """
    Select appropriate ranking recipe based on surface state.
    """
    mapping = {
        'search': 'global_search',
        'email_inbox': 'email_inbox' if not has_query else 'email_search',
        'email_open': 'email_search',
        'email_search': 'email_search',
        'entity_open': 'entity_context',
        'doc_open': 'document_search',
    }
    return mapping.get(surface_state, 'global_search')


# =============================================================================
# SCORING THRESHOLDS
# =============================================================================
# Used for link suggestions, action gating, etc.

SCORE_THRESHOLDS = {
    # Email link scoring (from linking ladder)
    'link_auto_confirm': 130,       # L1 hard match - auto-link
    'link_strong_suggest': 100,     # Strong suggestion
    'link_weak_suggest': 70,        # Weak suggestion
    'link_no_suggest': 69,          # Below this, don't suggest
    'link_ambiguous_gap': 15,       # If top1 - top2 < this, ambiguous

    # Search result thresholds
    'vector_min_similarity': 0.70,  # Minimum cosine similarity
    'exact_match_boost': 50,        # Points for exact ID match
    'recency_max_boost': 30,        # Max points for recency (decays over time)
}


# =============================================================================
# RECENCY DECAY
# =============================================================================

def calculate_recency_score(days_ago: int, max_days: int = 90) -> float:
    """
    Calculate recency score (0.0 to 1.0).
    More recent = higher score.
    Linear decay over max_days.
    """
    if days_ago <= 0:
        return 1.0
    if days_ago >= max_days:
        return 0.0
    return 1.0 - (days_ago / max_days)
