"""
Prepare Module
==============
Entity → Capability mapping from prepare-module branch.

Components:
- capability_composer - Maps entities to capabilities, parallel execution
- lane_enforcer - Enforces lane contracts (NO_LLM, RULES_ONLY, GPT)
"""

from .capability_composer import (
    compose_search,
    plan_capabilities,
    CapabilityPlan,
    ComposedResponse,
    MergeStrategy,
    ENTITY_TO_SEARCH_COLUMN,
)
from .lane_enforcer import (
    Lane,
    LaneCapabilities,
    LaneViolationError,
    LANE_CAPABILITIES,
)

__all__ = [
    'compose_search',
    'plan_capabilities',
    'CapabilityPlan',
    'ComposedResponse',
    'MergeStrategy',
    'ENTITY_TO_SEARCH_COLUMN',
    'Lane',
    'LaneCapabilities',
    'LaneViolationError',
    'LANE_CAPABILITIES',
]
