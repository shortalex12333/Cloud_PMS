"""
Retrieval Plan - Data Structures
=================================

Immutable data structures for query execution plans.
Built by PrepareModule, executed by downstream handlers.

A RetrievalPlan is:
    - Deterministic (same input → same plan)
    - Explainable (includes human-readable explanation)
    - Testable (can be serialized and compared)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class RetrievalPath(Enum):
    """
    Locked retrieval paths. Determines execution strategy.
    """
    SQL_ONLY = "sql"                # Pure SQL, no embeddings
    VECTOR_ONLY = "vector"          # Semantic search only
    HYBRID = "hybrid"               # SQL filters + vector ranking
    EMAIL_INBOX = "email_inbox"     # Special: inbox scan (SQL, date-bounded)
    EMAIL_SEARCH = "email_search"   # Special: email semantic search


@dataclass
class TimeWindow:
    """
    Time bounds for retrieval.
    """
    days: int = 90
    start: Optional[datetime] = None
    end: Optional[datetime] = None

    def to_interval(self) -> str:
        """PostgreSQL interval string."""
        return f"{self.days} days"

    def get_start(self) -> datetime:
        """Get start datetime."""
        if self.start:
            return self.start
        return datetime.utcnow() - timedelta(days=self.days)

    def get_end(self) -> datetime:
        """Get end datetime."""
        return self.end or datetime.utcnow()


@dataclass
class ParameterizedQuery:
    """
    SQL query with parameters. Never string concatenation.
    """
    sql: str
    params: Dict[str, Any] = field(default_factory=dict)
    domain: str = ""  # Which domain this query targets

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sql': self.sql[:200] + '...' if len(self.sql) > 200 else self.sql,
            'params': {k: str(v)[:50] for k, v in self.params.items()},
            'domain': self.domain,
        }


@dataclass
class VectorQuery:
    """
    Vector similarity search specification.
    """
    table: str                          # Target table
    column: str                         # Embedding column
    input_text: str                     # Text to embed
    input_embedding: Optional[List[float]] = None  # Pre-computed embedding
    top_k: int = 20                     # Max results
    threshold: float = 0.7              # Minimum similarity
    filters: Dict[str, Any] = field(default_factory=dict)  # Additional SQL filters

    def to_dict(self) -> Dict[str, Any]:
        return {
            'table': self.table,
            'column': self.column,
            'input_text': self.input_text[:100] if self.input_text else None,
            'top_k': self.top_k,
            'threshold': self.threshold,
            'filters': self.filters,
        }


@dataclass
class RetrievalPlan:
    """
    Complete retrieval plan. Built by PrepareModule.

    This is the contract between orchestration and execution.
    Execution layer ONLY executes what's in this plan.
    """
    # Routing
    path: RetrievalPath
    allowed_scopes: List[str]

    # Bounds
    time_window: TimeWindow
    row_limits: Dict[str, int] = field(default_factory=dict)  # Per-domain limits

    # Required filters (always applied)
    must_filters: Dict[str, Any] = field(default_factory=dict)  # yacht_id, entity_ids, etc.

    # Queries to execute
    sql_queries: List[ParameterizedQuery] = field(default_factory=list)
    vector_queries: List[VectorQuery] = field(default_factory=list)

    # Ranking
    ranking_recipe: str = "global_search"  # Key into RANKING_RECIPES

    # Explanation (for trust + debugging)
    explain: str = ""
    explain_details: Dict[str, Any] = field(default_factory=dict)

    # Trace
    plan_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_sql_only(self) -> bool:
        return self.path in (RetrievalPath.SQL_ONLY, RetrievalPath.EMAIL_INBOX)

    def is_vector_involved(self) -> bool:
        return self.path in (RetrievalPath.VECTOR_ONLY, RetrievalPath.HYBRID, RetrievalPath.EMAIL_SEARCH)

    def get_trust_payload(self) -> Dict[str, Any]:
        """
        Small payload for frontend trust display.
        Shows what was searched and why.
        """
        return {
            'path': self.path.value,
            'scopes': self.allowed_scopes,
            'time_window_days': self.time_window.days,
            'used_vector': self.is_vector_involved(),
            'explain': self.explain,
        }

    def get_debug_payload(self) -> Dict[str, Any]:
        """
        Full debug payload. Server-side or debug=true.
        """
        return {
            'plan_id': self.plan_id,
            'path': self.path.value,
            'allowed_scopes': self.allowed_scopes,
            'time_window': {
                'days': self.time_window.days,
                'start': self.time_window.get_start().isoformat(),
                'end': self.time_window.get_end().isoformat(),
            },
            'row_limits': self.row_limits,
            'must_filters': {k: str(v) for k, v in self.must_filters.items()},
            'sql_queries': [q.to_dict() for q in self.sql_queries],
            'vector_queries': [q.to_dict() for q in self.vector_queries],
            'ranking_recipe': self.ranking_recipe,
            'explain': self.explain,
            'explain_details': self.explain_details,
            'created_at': self.created_at.isoformat(),
        }


# Default row limits per domain
DEFAULT_ROW_LIMITS = {
    'emails': 50,
    'email_attachments': 20,
    'work_orders': 30,
    'equipment': 30,
    'parts': 30,
    'faults': 20,
    'documents': 20,
    'document_chunks': 50,
}
