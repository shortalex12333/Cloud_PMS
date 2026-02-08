"""
Orchestrated Search Routes
===========================

New search endpoint using the Search Orchestration Layer.
Provides deterministic, explainable query routing.

Endpoints:
    POST /v2/search - Orchestrated search with full plan visibility
    POST /v2/search/plan - Get plan only (no execution)
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import time

# Auth middleware
from middleware.auth import get_authenticated_user

# Orchestration layer
from orchestration import (
    SearchOrchestrator,
    SurfaceState,
    SurfaceContext,
    RetrievalPlan,
)
from orchestration.executor import PlanExecutor

# Action registry for action suggestions
from action_router.registry import get_actions_for_domain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["search-v2"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class OrchestatedSearchRequest(BaseModel):
    """Request for orchestrated search."""
    query_text: str = Field(default="", description="Search query text (may be empty for inbox)")
    surface_state: str = Field(default="search", description="UI surface state")
    open_entity_type: Optional[str] = Field(None, description="Type of open entity")
    open_entity_id: Optional[str] = Field(None, description="ID of open entity")
    open_thread_id: Optional[str] = Field(None, description="ID of open email thread")
    direction_bias: str = Field(default="inbound", description="Email direction bias")
    debug: bool = Field(default=False, description="Include debug payload")


class TrustPayload(BaseModel):
    """Trust payload shown to user."""
    path: str
    scopes: List[str]
    time_window_days: int
    used_vector: bool
    explain: str


class ContextMetadata(BaseModel):
    """Context metadata for frontend adaptation."""
    domain: Optional[str] = None
    domain_confidence: Optional[float] = None
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    mode: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


class OrchestatedSearchResponse(BaseModel):
    """Response from orchestrated search."""
    success: bool
    request_id: str
    results: List[Dict[str, Any]]
    results_by_domain: Dict[str, List[Dict[str, Any]]]
    total_count: int
    context: Optional[ContextMetadata] = None
    actions: Optional[List[Dict[str, Any]]] = None
    trust: TrustPayload
    timing_ms: Dict[str, float]
    debug: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PlanOnlyResponse(BaseModel):
    """Response for plan-only endpoint."""
    success: bool
    request_id: str
    plan: Dict[str, Any]
    classification: Dict[str, Any]


# =============================================================================
# LAZY LOADERS
# =============================================================================

_orchestrator = None


def get_orchestrator() -> SearchOrchestrator:
    """Lazy-load the search orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        # Try to load with existing components
        try:
            from intent_parser import IntentParser
            intent_parser = IntentParser()
        except Exception as e:
            logger.warning(f"Could not load IntentParser: {e}")
            intent_parser = None

        try:
            from extraction.orchestrator import ExtractionOrchestrator
            entity_extractor = ExtractionOrchestrator()
        except Exception as e:
            logger.warning(f"Could not load ExtractionOrchestrator: {e}")
            entity_extractor = None

        _orchestrator = SearchOrchestrator(
            intent_parser=intent_parser,
            entity_extractor=entity_extractor,
        )
        logger.info("✅ SearchOrchestrator initialized")

    return _orchestrator


def get_tenant_client(tenant_key_alias: str):
    """Get tenant-specific Supabase client."""
    import os
    from supabase import create_client

    url = os.environ.get(f'{tenant_key_alias}_SUPABASE_URL')
    key = os.environ.get(f'{tenant_key_alias}_SUPABASE_SERVICE_KEY')

    if not url or not key:
        raise ValueError(f'Missing credentials for tenant {tenant_key_alias}')

    return create_client(url, key)


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/search", response_model=OrchestatedSearchResponse)
async def orchestrated_search(
    request: OrchestatedSearchRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Orchestrated search endpoint.

    Uses the Search Orchestration Layer to:
    1. Classify query terms
    2. Build deterministic RetrievalPlan
    3. Execute queries
    4. Return results with trust payload

    The trust payload explains WHY results were returned.
    """
    start_time = time.time()

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    tenant_key_alias = auth['tenant_key_alias']

    logger.info(f"[v2/search] user={user_id[:8]}..., yacht={yacht_id}, "
                f"query='{request.query_text[:50] if request.query_text else '(empty)'}', "
                f"surface={request.surface_state}")

    try:
        # Parse surface state
        try:
            surface_state = SurfaceState(request.surface_state)
        except ValueError:
            surface_state = SurfaceState.SEARCH

        # Get orchestrator
        orchestrator = get_orchestrator()

        # Orchestrate (classify + prepare)
        orchestration_start = time.time()
        result = orchestrator.orchestrate(
            surface_state=surface_state,
            yacht_id=yacht_id,
            user_id=user_id,
            query_text=request.query_text,
            open_entity_type=request.open_entity_type,
            open_entity_id=request.open_entity_id,
            open_thread_id=request.open_thread_id,
            email_direction_bias=request.direction_bias,
            debug_mode=request.debug,
        )
        orchestration_time = (time.time() - orchestration_start) * 1000

        # Get tenant client and execute
        execute_start = time.time()
        client = get_tenant_client(tenant_key_alias)
        executor = PlanExecutor(client, yacht_id)
        execution_result = await executor.execute(result.plan)
        execute_time = (time.time() - execute_start) * 1000

        total_time = (time.time() - start_time) * 1000

        # Build response
        trust_payload = result.get_trust_payload()

        # Extract primary domain from allowed_scopes
        primary_domain = result.classification.allowed_scopes[0] if result.classification.allowed_scopes else None

        # Build context metadata
        context_metadata = ContextMetadata(
            domain=primary_domain,
            domain_confidence=0.9,  # High confidence from deterministic classification
            intent=result.intent_family or "READ",
            intent_confidence=0.95 if result.intent_family else 0.8,
            mode=result.plan.path.value,
            filters={
                'time_window_days': result.plan.time_window.days,
                'scopes': result.classification.allowed_scopes,
            },
        )

        # Get action suggestions filtered by domain and role
        # Normalize inventory → parts as per requirements
        action_suggestions = []
        if primary_domain:
            normalized_domain = "parts" if primary_domain == "inventory" else primary_domain
            user_role = auth.get('role')
            if user_role:
                action_suggestions = get_actions_for_domain(normalized_domain, user_role)

        response = OrchestatedSearchResponse(
            success=True,
            request_id=result.request_id,
            results=execution_result.results,
            results_by_domain=execution_result.results_by_domain,
            total_count=execution_result.total_count,
            context=context_metadata,
            actions=action_suggestions,
            trust=TrustPayload(
                path=trust_payload['path'],
                scopes=trust_payload['scopes'],
                time_window_days=trust_payload['time_window_days'],
                used_vector=trust_payload['used_vector'],
                explain=trust_payload['explain'],
            ),
            timing_ms={
                'orchestration': round(orchestration_time, 1),
                'execution': round(execute_time, 1),
                'total': round(total_time, 1),
            },
        )

        # Add debug payload if requested
        if request.debug:
            response.debug = result.get_debug_payload()

        logger.info(f"[v2/search] request_id={result.request_id}, "
                    f"results={execution_result.total_count}, "
                    f"path={result.plan.path.value}, "
                    f"time={total_time:.1f}ms")

        return response

    except Exception as e:
        logger.error(f"[v2/search] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/plan", response_model=PlanOnlyResponse)
async def get_search_plan(
    request: OrchestatedSearchRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get search plan without execution.

    Useful for:
    - Debugging query classification
    - Understanding retrieval routing
    - Testing orchestration layer

    Returns the RetrievalPlan that WOULD be executed.
    """
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']

    try:
        surface_state = SurfaceState(request.surface_state)
    except ValueError:
        surface_state = SurfaceState.SEARCH

    orchestrator = get_orchestrator()

    result = orchestrator.orchestrate(
        surface_state=surface_state,
        yacht_id=yacht_id,
        user_id=user_id,
        query_text=request.query_text,
        open_entity_type=request.open_entity_type,
        open_entity_id=request.open_entity_id,
        open_thread_id=request.open_thread_id,
        email_direction_bias=request.direction_bias,
        debug_mode=True,  # Always include full details for plan endpoint
    )

    return PlanOnlyResponse(
        success=True,
        request_id=result.request_id,
        plan=result.plan.get_debug_payload(),
        classification=result.classification.to_dict(),
    )


@router.get("/search/health")
async def search_health():
    """Health check for orchestrated search."""
    try:
        orchestrator = get_orchestrator()
        return {
            "status": "healthy",
            "orchestrator_ready": orchestrator is not None,
            "has_intent_parser": orchestrator.intent_parser is not None,
            "has_entity_extractor": orchestrator.entity_extractor is not None,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
