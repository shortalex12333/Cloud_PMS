"""
Context Navigation Schemas

Pydantic models for situational continuity API contracts.
Based on schemas from: /docs/15_situational_continuity_layer/schemas/
"""

from pydantic import BaseModel, Field, UUID4
from typing import List, Dict, Any, Optional
from datetime import datetime


class NavigationContextCreate(BaseModel):
    """Request to create a new navigation context when opening an artifact from search."""
    yacht_id: UUID4
    user_id: UUID4
    artefact_type: str
    artefact_id: UUID4


class NavigationContext(BaseModel):
    """Navigation context state (persisted in DB for audit only)."""
    id: UUID4
    yacht_id: UUID4
    created_by_user_id: UUID4
    created_at: datetime
    ended_at: Optional[datetime] = None
    active_anchor_type: str
    active_anchor_id: UUID4
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    temporal_bias: str = "now"  # now | recent | historical


class RelatedRequest(BaseModel):
    """Request to get related artifacts (deterministic expansion only)."""
    situation_id: UUID4
    anchor_type: str
    anchor_id: UUID4
    tenant_id: UUID4
    user_id: UUID4
    allowed_domains: List[str]  # e.g., ["inventory", "work_orders", "faults"]


class RelatedItem(BaseModel):
    """Single related artifact item."""
    artefact_type: str
    artefact_id: UUID4
    title: str
    subtitle: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RelatedGroup(BaseModel):
    """Domain-grouped related artifacts."""
    domain: str  # inventory | work_orders | faults | shopping | documents | manuals | emails | certificates | history
    items: List[RelatedItem]


class RelatedResponse(BaseModel):
    """Response containing domain-grouped related artifacts."""
    situation_id: UUID4
    anchor_type: str
    anchor_id: UUID4
    groups: List[RelatedGroup]


class AddRelatedRequest(BaseModel):
    """Request to add an explicit user relation."""
    yacht_id: UUID4
    user_id: UUID4
    from_artefact_type: str
    from_artefact_id: UUID4
    to_artefact_type: str
    to_artefact_id: UUID4


class AddRelatedResponse(BaseModel):
    """Response after adding a relation."""
    relation_id: UUID4
    created_at: datetime


# TODO: Implement in Phase 4
