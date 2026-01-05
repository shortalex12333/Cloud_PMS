"""
Response Contracts - Canonical enums and schemas for API responses

This module defines the single source of truth for:
- Lane values
- Lane reason values
- Execution strategy values
- Trace schema
- Security event flags

All API responses MUST use these canonical values.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


# =============================================================================
# LANE ENUMS
# =============================================================================

class Lane(str, Enum):
    """Processing lanes for query routing"""
    BLOCKED = "BLOCKED"      # Query rejected (security, vague, off-domain)
    UNKNOWN = "UNKNOWN"      # Uncertain intent, needs clarification
    NO_LLM = "NO_LLM"        # Direct lookup, no LLM needed
    RULES_ONLY = "RULES_ONLY"  # Pattern-based, no LLM needed
    GPT = "GPT"              # Requires LLM understanding


class LaneReason(str, Enum):
    """Canonical reasons for lane assignment"""
    # BLOCKED reasons
    PASTE_DUMP = "paste_dump"                  # Code/log paste detected
    TOO_VAGUE = "too_vague"                    # Query too short/generic
    INJECTION_DETECTED = "injection_detected"  # Security: prompt injection
    DOMAIN_DRIFT = "domain_drift"              # Off-domain query detected
    NON_DOMAIN = "non_domain"                  # Non-maritime/PMS query

    # NO_LLM reasons
    DIRECT_LOOKUP = "direct_lookup"            # Exact code/ID lookup
    SIMPLE_LOOKUP = "simple_lookup"            # Known entity simple search
    FORCED_MODE = "forced_mode"                # User forced lookup mode

    # RULES_ONLY reasons
    COMMAND_PATTERN = "command_pattern"        # Matches action command pattern
    IMPLICIT_ACTION = "implicit_action"        # Implicit action detected
    ELLIPTICAL = "elliptical"                  # Shorthand/elliptical query

    # UNKNOWN reasons
    NO_CLEAR_PATTERN = "no_clear_pattern"      # No matching pattern found
    AMBIGUOUS = "ambiguous"                    # Multiple interpretations possible

    # GPT reasons
    PROBLEM_WORDS = "problem_words"            # Contains problem indicators
    TEMPORAL_CONTEXT = "temporal_context"      # Time-sensitive query
    COMPLEX_QUERY = "complex_query"            # Multi-entity or complex
    DIAGNOSTIC = "diagnostic"                  # Diagnostic/troubleshooting query


# =============================================================================
# EXECUTION STRATEGY ENUMS
# =============================================================================

class ExecutionStrategy(str, Enum):
    """SQL execution strategies"""
    WAVE_SEARCH = "wave_search"        # EXACT → ILIKE → TRIGRAM waves
    VECTOR_RPC = "vector_rpc"          # Vector similarity via RPC
    TEXT_FALLBACK = "text_fallback"    # ILIKE text search fallback
    UNION_RPC = "union_rpc"            # Combined RPC (future)
    BBWS = "bbws"                      # Batched Biased Wave Search
    GRAPHRAG = "graphrag"              # Graph RAG with GPT


class WaveType(str, Enum):
    """SQL wave types"""
    EXACT = "EXACT"
    ILIKE = "ILIKE"
    TRIGRAM = "TRIGRAM"
    VECTOR = "VECTOR"


# =============================================================================
# SECURITY TELEMETRY
# =============================================================================

class SecurityEventType(str, Enum):
    """Security event types for telemetry"""
    INJECTION_ATTEMPT = "injection_attempt"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    PATH_TRAVERSAL = "path_traversal"
    CODE_PASTE = "code_paste"
    JAILBREAK = "jailbreak"
    RATE_LIMIT = "rate_limit"


@dataclass
class SecurityEvent:
    """Security event for telemetry logging"""
    event_type: SecurityEventType
    detected_pattern: str
    query_hash: str  # SHA256 of query (not the query itself)
    blocked: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type.value,
            "detected_pattern": self.detected_pattern,
            "query_hash": self.query_hash,
            "blocked": self.blocked,
            "timestamp": self.timestamp.isoformat()
        }


# =============================================================================
# TRACE SCHEMA
# =============================================================================

@dataclass
class WaveTrace:
    """Trace for a single wave execution"""
    wave: WaveType
    tables_queried: List[str]
    rows_returned: int
    latency_ms: float
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "wave": self.wave.value,
            "tables_queried": self.tables_queried,
            "rows_returned": self.rows_returned,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error
        }


@dataclass
class ExecutionTrace:
    """Complete execution trace for a search request"""
    request_id: str
    lane: Lane
    lane_reason: LaneReason
    strategy: ExecutionStrategy
    waves: List[WaveTrace]
    total_latency_ms: float
    result_count: int
    early_exit: bool
    security_event: Optional[SecurityEvent] = None

    def to_dict(self) -> Dict:
        result = {
            "request_id": self.request_id,
            "lane": self.lane.value,
            "lane_reason": self.lane_reason.value,
            "strategy": self.strategy.value,
            "waves": [w.to_dict() for w in self.waves],
            "total_latency_ms": round(self.total_latency_ms, 2),
            "result_count": self.result_count,
            "early_exit": self.early_exit,
        }
        if self.security_event:
            result["security_event"] = self.security_event.to_dict()
        return result


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

@dataclass
class SearchMeta:
    """Metadata for search response"""
    yacht_id: str
    user_id: str
    user_role: str
    query: str
    intent: str
    lane: Lane
    lane_reason: LaneReason
    strategy: ExecutionStrategy
    latency_ms: int
    trace: Optional[ExecutionTrace] = None

    def to_dict(self) -> Dict:
        result = {
            "yacht_id": self.yacht_id,
            "user_id": self.user_id,
            "user_role": self.user_role,
            "query": self.query,
            "intent": self.intent,
            "lane": self.lane.value,
            "lane_reason": self.lane_reason.value,
            "strategy": self.strategy.value,
            "latency_ms": self.latency_ms,
        }
        if self.trace:
            result["trace"] = self.trace.to_dict()
        return result


# =============================================================================
# LANE REASON MAPPING (for backwards compatibility)
# =============================================================================

# Map old reason strings to canonical enums
LEGACY_REASON_MAP = {
    "paste_dump": LaneReason.PASTE_DUMP,
    "too_vague": LaneReason.TOO_VAGUE,
    "injection_detected": LaneReason.INJECTION_DETECTED,
    "domain_drift": LaneReason.DOMAIN_DRIFT,
    "non_domain": LaneReason.NON_DOMAIN,
    "direct_lookup_pattern": LaneReason.DIRECT_LOOKUP,
    "simple_lookup": LaneReason.SIMPLE_LOOKUP,
    "forced_mode": LaneReason.FORCED_MODE,
    "command_pattern": LaneReason.COMMAND_PATTERN,
    "implicit_action": LaneReason.IMPLICIT_ACTION,
    "elliptical_shorthand": LaneReason.ELLIPTICAL,
    "no_clear_pattern": LaneReason.NO_CLEAR_PATTERN,
    "problem_words": LaneReason.PROBLEM_WORDS,
    "temporal_context": LaneReason.TEMPORAL_CONTEXT,
    "complex_query": LaneReason.COMPLEX_QUERY,
}


def normalize_lane_reason(reason: str) -> LaneReason:
    """Convert legacy reason string to canonical enum"""
    if isinstance(reason, LaneReason):
        return reason
    return LEGACY_REASON_MAP.get(reason, LaneReason.NO_CLEAR_PATTERN)


def normalize_lane(lane: str) -> Lane:
    """Convert lane string to canonical enum"""
    if isinstance(lane, Lane):
        return lane
    try:
        return Lane(lane)
    except ValueError:
        return Lane.UNKNOWN


# =============================================================================
# VALIDATION
# =============================================================================

def validate_routing_response(response: Dict) -> List[str]:
    """
    Validate a routing response against the contract.
    Returns list of validation errors (empty if valid).
    """
    errors = []

    # Check required fields
    if "lane" not in response:
        errors.append("Missing required field: lane")
    elif response["lane"] not in [l.value for l in Lane]:
        errors.append(f"Invalid lane value: {response['lane']}")

    if "lane_reason" not in response:
        errors.append("Missing required field: lane_reason")
    elif response["lane_reason"] not in [r.value for r in LaneReason]:
        errors.append(f"Invalid lane_reason value: {response['lane_reason']}")

    return errors


# =============================================================================
# TEST HELPERS
# =============================================================================

def get_all_lane_values() -> List[str]:
    """Get all valid lane values for testing"""
    return [l.value for l in Lane]


def get_all_lane_reasons() -> List[str]:
    """Get all valid lane_reason values for testing"""
    return [r.value for r in LaneReason]


def get_lane_reasons_for_lane(lane: Lane) -> List[LaneReason]:
    """Get valid reasons for a specific lane"""
    mapping = {
        Lane.BLOCKED: [
            LaneReason.PASTE_DUMP,
            LaneReason.TOO_VAGUE,
            LaneReason.INJECTION_DETECTED,
            LaneReason.DOMAIN_DRIFT,
            LaneReason.NON_DOMAIN,
        ],
        Lane.NO_LLM: [
            LaneReason.DIRECT_LOOKUP,
            LaneReason.SIMPLE_LOOKUP,
            LaneReason.FORCED_MODE,
        ],
        Lane.RULES_ONLY: [
            LaneReason.COMMAND_PATTERN,
            LaneReason.IMPLICIT_ACTION,
            LaneReason.ELLIPTICAL,
        ],
        Lane.UNKNOWN: [
            LaneReason.NO_CLEAR_PATTERN,
            LaneReason.AMBIGUOUS,
        ],
        Lane.GPT: [
            LaneReason.PROBLEM_WORDS,
            LaneReason.TEMPORAL_CONTEXT,
            LaneReason.COMPLEX_QUERY,
            LaneReason.DIAGNOSTIC,
        ],
    }
    return mapping.get(lane, [])
