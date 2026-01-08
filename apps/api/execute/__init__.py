"""
Execute Module
==============
SQL execution layer from prepare-module + deploy/microactions branches.

Components:
- capability_executor - Secure SQL generation with yacht_id enforcement
- table_capabilities - Capability registry (entity → table → columns)
- capability_observability - Metrics and tracing
- result_normalizer - Normalize results across capabilities
"""

from .capability_executor import (
    CapabilityExecutor,
    QueryResult,
    ExecutionError,
    SecurityError,
)
from .table_capabilities import (
    TABLE_CAPABILITIES,
    Capability,
    TableSpec,
    SearchableColumn,
    CapabilityStatus,
    MatchType,
    get_capability_for_entity,
    get_active_capabilities,
)
from .capability_observability import (
    log_search_request,
    log_from_composed_response,
    determine_outcome,
)
from .result_normalizer import (
    normalize_results,
    NormalizedResult,
    NormalizedResponse,
)

__all__ = [
    'CapabilityExecutor',
    'QueryResult',
    'ExecutionError',
    'SecurityError',
    'TABLE_CAPABILITIES',
    'Capability',
    'TableSpec',
    'SearchableColumn',
    'CapabilityStatus',
    'MatchType',
    'get_capability_for_entity',
    'get_active_capabilities',
    'log_search_request',
    'log_from_composed_response',
    'determine_outcome',
    'normalize_results',
    'NormalizedResult',
    'NormalizedResponse',
]
