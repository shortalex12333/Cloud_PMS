"""
Decision Engine Routes
======================

Phase 11.1: Exposes Decision Engine as /v1/decisions endpoint.

Policy Sources:
- E017_TRIGGER_CONTRACTS.yaml
- E018_THRESHOLD_MODEL.md (confidence scoring)
- E019_STATE_GUARDS.yaml (state machine)

Returns ActionDecision[] with confidence, reasons, and breakdown.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import logging
import time

# Import auth middleware
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from middleware.auth import get_authenticated_user
from services.decision_engine import evaluate_decisions, get_decision_engine
from services.decision_audit_service import get_decision_audit_service

# Import centralized Supabase client factory
from integrations.supabase import get_tenant_client

logger = logging.getLogger(__name__)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class EntityInput(BaseModel):
    """Entity context for decision evaluation."""
    type: str = Field(..., description="Entity type: work_order, fault, equipment")
    id: Optional[str] = Field(None, description="Entity UUID if resolved")
    name: Optional[str] = Field(None, description="Entity name/title")
    status: Optional[str] = Field(None, description="Entity status")
    has_work_order: Optional[bool] = Field(None, description="For faults: has associated WO")
    has_checklist: Optional[bool] = Field(None, description="For work orders: has checklist")
    has_manual: Optional[bool] = Field(None, description="For equipment: has manual")
    acknowledged: Optional[bool] = Field(None, description="For faults: has been acknowledged")


class DecisionRequest(BaseModel):
    """Request body for /v1/decisions endpoint."""
    detected_intents: List[str] = Field(
        default_factory=list,
        description="Detected user intents: diagnose, repair, close, view, etc."
    )
    entities: List[EntityInput] = Field(
        default_factory=list,
        description="Entity context for decision evaluation"
    )
    situation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional situation flags"
    )
    environment: str = Field(
        default="at_sea",
        description="Environment: at_sea, shipyard, port"
    )
    include_blocked: bool = Field(
        default=True,
        description="Include blocked/not-allowed actions in response"
    )


class ConfidenceBreakdownResponse(BaseModel):
    """Confidence breakdown per E018."""
    intent: float
    entity: float
    situation: float


class BlockedByResponse(BaseModel):
    """Block reason."""
    type: str
    detail: str


class ActionDecisionResponse(BaseModel):
    """Single action decision."""
    action: str
    allowed: bool
    tier: str
    confidence: float
    reasons: List[str]
    breakdown: ConfidenceBreakdownResponse
    blocked_by: Optional[BlockedByResponse] = None
    explanation: str


class DecisionResponse(BaseModel):
    """Response from /v1/decisions endpoint."""
    execution_id: str
    yacht_id: str
    user_id: str
    user_role: str
    decisions: List[ActionDecisionResponse]
    allowed_count: int
    blocked_count: int
    timing_ms: float


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/v1/decisions", tags=["decisions"])


@router.post("", response_model=DecisionResponse)
@router.post("/", response_model=DecisionResponse)
async def get_decisions(
    request: DecisionRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Evaluate all 30 actions and return decisions.

    This endpoint implements:
    - E017: Trigger contracts (requires/forbidden)
    - E018: Confidence scoring (intent 0.4 + entity 0.4 + situation 0.2)
    - E019: State guards (mutual exclusion)

    Returns ActionDecision[] for all actions in the registry.
    UI uses this to render action buttons - UI does NOT make decisions.
    """
    start_time = time.time()

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', 'member')

    logger.info(
        f"[decisions] user={user_id[:8]}..., yacht={yacht_id}, "
        f"intents={request.detected_intents}, "
        f"entities={[e.type for e in request.entities]}"
    )

    try:
        # Convert entities to dicts (only include non-None values)
        entities_list = []
        for e in request.entities:
            entity_dict = {"type": e.type}
            # Only add optional fields if they have values (not None)
            if e.id is not None:
                entity_dict["id"] = e.id
            if e.name is not None:
                entity_dict["name"] = e.name
            if e.status is not None:
                entity_dict["status"] = e.status
            if e.has_work_order is not None:
                entity_dict["has_work_order"] = e.has_work_order
            if e.has_checklist is not None:
                entity_dict["has_checklist"] = e.has_checklist
            if e.has_manual is not None:
                entity_dict["has_manual"] = e.has_manual
            if e.acknowledged is not None:
                entity_dict["acknowledged"] = e.acknowledged
            entities_list.append(entity_dict)

        # Evaluate decisions
        result = evaluate_decisions(
            yacht_id=yacht_id,
            user_id=user_id,
            user_role=user_role,
            detected_intents=request.detected_intents,
            entities=entities_list,
            situation=request.situation,
            environment=request.environment,
        )

        # Filter out blocked if requested
        decisions = result["decisions"]
        if not request.include_blocked:
            decisions = [d for d in decisions if d["allowed"]]

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[decisions] execution_id={result['execution_id'][:8]}..., "
            f"allowed={result['allowed_count']}, blocked={result['blocked_count']}, "
            f"timing={elapsed_ms:.1f}ms"
        )

        # Log decisions to audit table (async, non-blocking)
        try:
            tenant_key_alias = auth.get('tenant_key_alias')
            if tenant_key_alias:
                client = get_tenant_client(tenant_key_alias)
                audit_service = get_decision_audit_service(client)
                audit_service.log_decisions(
                    execution_id=result["execution_id"],
                    yacht_id=yacht_id,
                    user_id=user_id,
                    user_role=user_role,
                    detected_intents=request.detected_intents,
                    entities=entities_list,
                    situation=request.situation,
                    environment=request.environment,
                    decisions=result["decisions"],
                )
        except Exception as audit_error:
            # Don't fail the request if audit logging fails
            logger.warning(f"[decisions] Audit logging failed: {audit_error}")

        return DecisionResponse(
            execution_id=result["execution_id"],
            yacht_id=yacht_id,
            user_id=user_id,
            user_role=user_role,
            decisions=decisions,
            allowed_count=result["allowed_count"],
            blocked_count=result["blocked_count"],
            timing_ms=round(elapsed_ms, 2),
        )

    except Exception as e:
        logger.error(f"[decisions] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Decision evaluation failed: {str(e)}")


@router.get("/health")
async def decisions_health():
    """Health check for decision engine."""
    try:
        engine = get_decision_engine()
        contract_count = len(engine.trigger_contracts)
        return {
            "status": "healthy",
            "trigger_contracts_loaded": contract_count,
            "state_guards_loaded": bool(engine.state_guards),
        }
    except Exception as e:
        logger.error(f"[decisions/health] Error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
