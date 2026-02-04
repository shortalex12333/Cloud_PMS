#!/usr/bin/env python3
"""
F1 Search - Core Types

Single source of truth for user context that flows through the entire search pipeline.
Every function that touches the DB MUST receive UserContext to enforce RLS.

See: apps/api/docs/F1_SEARCH/RLS_CLAIMS_SPEC.md
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class UserContext:
    """
    Immutable user context that flows through the search pipeline.

    CRITICAL: org_id is required for RLS enforcement. If omitted, queries will
    return empty results or fail RLS policy checks.

    Fields:
        user_id: Authenticated user's UUID
        org_id: Organization UUID - REQUIRED for RLS (search_index.org_id filter)
        yacht_id: Optional yacht UUID for yacht-scoped queries
        role: User's role (e.g., 'admin', 'crew', 'captain')
        locale: Optional locale for i18n (e.g., 'en-US', 'de-DE')

    Usage:
        ctx = UserContext(
            user_id="abc-123",
            org_id="org-456",  # MUST be present
            yacht_id="yacht-789",
            role="captain"
        )

        # Pass to every DB-touching function
        results = await hyper_search(query, ctx)
    """
    user_id: str
    org_id: str  # REQUIRED - RLS will fail without this
    yacht_id: Optional[str] = None
    role: str = "crew"  # Default to least-privileged role
    locale: Optional[str] = None

    def __post_init__(self):
        """Validate required fields."""
        if not self.user_id:
            raise ValueError("UserContext.user_id is required")
        if not self.org_id:
            raise ValueError("UserContext.org_id is required for RLS enforcement")
        if not self.role:
            raise ValueError("UserContext.role is required")

    @property
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization and DB params."""
        return asdict(self)

    def to_jwt_claims(self) -> Dict[str, str]:
        """
        Convert to JWT claims format expected by Supabase RLS policies.

        Maps to: current_setting('request.jwt.claims', true)::jsonb
        """
        claims = {
            "sub": self.user_id,
            "org_id": self.org_id,
            "role": self.role,
        }
        if self.yacht_id:
            claims["yacht_id"] = self.yacht_id
        if self.locale:
            claims["locale"] = self.locale
        return claims

    @classmethod
    def from_jwt(cls, claims: Dict[str, Any]) -> "UserContext":
        """
        Create UserContext from JWT claims dict.

        Args:
            claims: JWT payload with 'sub', 'org_id', 'role', optional 'yacht_id'

        Raises:
            ValueError: If required claims are missing
        """
        user_id = claims.get("sub") or claims.get("user_id")
        org_id = claims.get("org_id")

        if not user_id:
            raise ValueError("JWT claims missing 'sub' or 'user_id'")
        if not org_id:
            raise ValueError("JWT claims missing 'org_id' - RLS will fail")

        return cls(
            user_id=str(user_id),
            org_id=str(org_id),
            yacht_id=claims.get("yacht_id"),
            role=claims.get("role", "crew"),
            locale=claims.get("locale"),
        )


# Type alias for search budget configuration
@dataclass(frozen=True)
class SearchBudget:
    """
    Time and resource budgets for search operations.

    See: apps/api/docs/F1_SEARCH/LATENCY_SLOS_AND_BUDGETS.md
    """
    max_rewrites: int = 3
    rewrite_budget_ms: int = 150
    db_timeout_ms: int = 120
    global_timeout_ms: int = 500
    vector_dim: int = 384

    # Concurrency caps
    global_concurrency_cap: int = 8
    per_domain_cap: int = 2


# Default budget instance
DEFAULT_BUDGET = SearchBudget()
