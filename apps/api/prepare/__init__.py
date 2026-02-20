"""
Prepare Module
==============
Entity → Capability mapping from prepare-module branch.

Components:
- capability_composer - Maps entities to capabilities, parallel execution
"""

from .capability_composer import (
    compose_search,
    plan_capabilities,
    CapabilityPlan,
    ComposedResponse,
    MergeStrategy,
    ENTITY_TO_SEARCH_COLUMN,
)

__all__ = [
    'compose_search',
    'plan_capabilities',
    'CapabilityPlan',
    'ComposedResponse',
    'MergeStrategy',
    'ENTITY_TO_SEARCH_COLUMN',
]
