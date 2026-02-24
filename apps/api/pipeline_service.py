"""
F1 Search Pipeline Service
==========================

F1 Search Pipeline deployment for Render.
Uses RRF (Reciprocal Rank Fusion) scoring - no hard tier walls.

Primary Search Endpoint:
- GET /api/f1/search/stream - SSE streaming search (F1 architecture)

Legacy Endpoints (Utility):
- POST /search - Direct search (admin/testing)
- POST /extract - Entity extraction only
- GET /health - Health check
- GET /capabilities - List active capabilities

Deployment:
- Render: uvicorn api.pipeline_service:app --host 0.0.0.0 --port $PORT
"""

from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import asyncio
import time
import logging
import os
import sys
import uuid
import traceback
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Git commit for /version endpoint
# Updated: 2026-02-20 - F1 Search Pipeline Hardening
# Version: 2026.02.20.001 - Surgical Strike: Removed pipeline_v1 hard tier scoring
GIT_COMMIT = os.environ.get("RENDER_GIT_COMMIT", os.environ.get("GIT_COMMIT", "dev"))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
DEPLOY_TIMESTAMP = "2026-02-20T12:00:00Z"  # F1 Hardening

# Setup path for imports
from pathlib import Path
_api_dir = Path(__file__).parent
if str(_api_dir) not in sys.path:
    sys.path.insert(0, str(_api_dir))

# Import auth middleware for JWT validation + tenant lookup
from middleware.auth import get_authenticated_user, lookup_tenant_for_user

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="CelesteOS F1 Search Pipeline",
    description="F1 Search Pipeline: RRF scoring, no hard tiers",
    version="2026.02.20.001",
)

# ============================================================================
# CORS CONFIGURATION (Production-Grade)
# ============================================================================
# SECURITY:
# - Bearer token auth (Authorization header) = allow_credentials=False
# - No cookies = no CSRF risk
# - Explicit stable domains only (no preview URLs)
# - Verify ALLOWED_ORIGINS matches actual deployments

import os
import logging

# Parse and normalize origins from env var
ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "https://auth.celeste7.ai,https://app.celeste7.ai,https://api.celeste7.ai,https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app,http://localhost:3000,http://localhost:8000"
)

# Normalize: strip whitespace, remove empties, deduplicate
ALLOWED_ORIGINS = list(dict.fromkeys([
    origin.strip()
    for origin in ALLOWED_ORIGINS_STR.split(",")
    if origin.strip()  # Drop empty strings
]))

# Log normalized origins on startup for verification
logger.info(f"✅ [Pipeline] CORS ALLOWED_ORIGINS (normalized): {ALLOWED_ORIGINS}")
if len(ALLOWED_ORIGINS) == 0:
    logger.error("❌ [Pipeline] CRITICAL: No allowed origins configured!")

# WARNING: Never add *.vercel.app preview URLs to production CORS
# Preview URLs change constantly and create maintenance burden
# Production is the only execution surface

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,  # Bearer tokens in headers, no cookies
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",        # JWT bearer token
        "Content-Type",
        "X-Request-Id",
        "X-Yacht-Signature",
    ],
    expose_headers=["X-Request-Id"],  # Allow client to read request ID
    max_age=3600,  # Cache preflight for 1 hour
)

# Middleware to add Vary: Origin for CDN cache correctness
# IMPORTANT: Append to existing Vary header, don't overwrite
@app.middleware("http")
async def add_vary_origin(request, call_next):
    response = await call_next(request)

    # Get existing Vary header
    existing_vary = response.headers.get("Vary", "")

    # Only add Origin if not already present
    if existing_vary:
        # Split on comma, normalize, check if Origin is present
        vary_values = [v.strip() for v in existing_vary.split(",")]
        if "Origin" not in vary_values:
            response.headers["Vary"] = f"{existing_vary}, Origin"
    else:
        response.headers["Vary"] = "Origin"

    return response

# ============================================================================
# RATE LIMITING CONFIGURATION
# ============================================================================

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Per-org rate limiting for F1 search (Redis-backed)
try:
    from middleware.rate_limit import OrgRateLimitMiddleware
    app.add_middleware(OrgRateLimitMiddleware)
    logger.info("✅ [Pipeline] Org rate limiting middleware added (F1 search)")
except Exception as e:
    logger.warning(f"⚠️ [Pipeline] Org rate limiting not available: {e}")

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException with structured error response"""
    # If detail is already a structured error dict (has error_code), return it directly
    # This prevents double-wrapping errors from receiving handlers
    if isinstance(exc.detail, dict) and "error_code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    # Otherwise wrap in standard format
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with 500 response"""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(f"Request path: {request.url}")
    logger.error(f"Exception type: {type(exc).__name__}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url)
        }
    )

logger.info("✅ [Pipeline] Rate limiting enabled")
logger.info("✅ [Pipeline] Exception handlers registered")

# ============================================================================
# P0 ACTIONS ROUTES
# ============================================================================

_p0_import_error = None  # Store import error for debug endpoint

try:
    from routes.p0_actions_routes import router as p0_actions_router
    app.include_router(p0_actions_router)
    logger.info("✅ P0 Actions routes registered at /v1/actions/*")
    logger.info(f"   Router prefix: {p0_actions_router.prefix}, routes: {len(p0_actions_router.routes)}")
except Exception as e:
    import traceback
    _p0_import_error = traceback.format_exc()
    logger.error(f"❌ Failed to register P0 Actions routes: {e}")
    logger.error(f"   Full traceback:\n{_p0_import_error}")
    logger.error("P0 Actions will not be available via API")

# ============================================================================
# LEDGER ROUTES
# ============================================================================

try:
    from routes.ledger_routes import router as ledger_router
    app.include_router(ledger_router)
    logger.info("✅ Ledger routes registered at /v1/ledger/*")
except Exception as e:
    logger.error(f"❌ Failed to register Ledger routes: {e}")
    logger.error("Ledger endpoints will not be available")

# ============================================================================
# EMAIL TRANSPORT LAYER ROUTES
# ============================================================================

try:
    from routes.email import router as email_router
    app.include_router(email_router)
    logger.info("✅ Email Transport Layer routes registered at /email/*")
except Exception as e:
    logger.error(f"❌ Failed to register Email routes: {e}")
    logger.error("Email endpoints will not be available")

# ============================================================================
# CONTEXT NAVIGATION ROUTES (Situational Continuity Layer)
# ============================================================================

try:
    from routes.context_navigation_routes import router as context_nav_router
    app.include_router(context_nav_router, prefix="/api/context", tags=["context-nav"])
    logger.info("✅ Context Navigation routes registered at /api/context/*")
except Exception as e:
    logger.error(f"❌ Failed to register Context Navigation routes: {e}")
    logger.error("Context Navigation endpoints will not be available")

# ============================================================================
# OAUTH AUTHENTICATION ROUTES
# ============================================================================

try:
    from routes.auth_routes import router as auth_router
    app.include_router(auth_router)
    logger.info("✅ OAuth Auth routes registered at /auth/*")
except Exception as e:
    logger.error(f"❌ Failed to register Auth routes: {e}")
    logger.error("OAuth endpoints will not be available")

# ============================================================================
# ORCHESTRATED SEARCH ROUTES (Search Orchestration Layer)
# ============================================================================

try:
    from routes.orchestrated_search_routes import router as orchestrated_search_router
    app.include_router(orchestrated_search_router)
    logger.info("✅ Orchestrated Search routes registered at /v2/search/*")
except Exception as e:
    logger.error(f"❌ Failed to register Orchestrated Search routes: {e}")
    logger.error("V2 Search endpoints will not be available")

# ============================================================================
# DECISION ENGINE ROUTES (Phase 11 - Policy Layer)
# ============================================================================

try:
    from routes.decisions_routes import router as decisions_router
    app.include_router(decisions_router)
    logger.info("✅ Decision Engine routes registered at /v1/decisions/*")
except Exception as e:
    logger.error(f"❌ Failed to register Decision Engine routes: {e}")
    logger.error("Decision Engine endpoints will not be available")

# ============================================================================
# CERTIFICATE ROUTES (Certificate Lens v2)
# ============================================================================

try:
    from routes.certificate_routes import router as certificate_router
    app.include_router(certificate_router, prefix="/api/v1/certificates", tags=["certificates"])
    logger.info("✅ Certificate routes registered at /api/v1/certificates/*")
except Exception as e:
    logger.error(f"❌ Failed to register Certificate routes: {e}")
    logger.error("Certificate endpoints will not be available")

# ============================================================================
# PART LENS ROUTES (Part Lens v2)
# ============================================================================

try:
    from routes.part_routes import router as part_routes_router
    app.include_router(part_routes_router)
    logger.info("✅ Part Lens v2 routes registered at /v1/parts/*")
except Exception as e:
    logger.error(f"❌ Failed to register Part Lens routes: {e}")
    logger.error("Part Lens endpoints will not be available")

# ============================================================================
# FAULT LENS V1 ROUTES (Phase 7-8)
# ============================================================================

try:
    from routes.fault_routes import router as fault_routes_router
    app.include_router(fault_routes_router, prefix="/v1/faults", tags=["faults"])
    logger.info("✅ Fault Lens v1 routes registered at /v1/faults/*")
except Exception as e:
    logger.error(f"❌ Failed to register Fault Lens routes: {e}")
    logger.error("Fault Lens endpoints will not be available")

# ============================================================================
# SHOW RELATED ROUTES (Work Order Lens P1)
# ============================================================================

try:
    from routes.related_routes import router as related_router
    app.include_router(related_router)
    logger.info("✅ Show Related routes registered at /v1/related/*")
except Exception as e:
    logger.error(f"❌ Failed to register Show Related routes: {e}")
    logger.error("Show Related endpoints will not be available")

try:
    from routes.search_streaming import router as search_streaming_router
    app.include_router(search_streaming_router)
    logger.info("✅ Streaming Search routes registered at /api/search/stream")
except Exception as e:
    logger.error(f"❌ Failed to register Streaming Search routes: {e}")
    logger.error("Streaming Search endpoints will not be available")

# ============================================================================
# F1 SEARCH STREAMING (Phase 0 - Parallel with Prepare)
# ============================================================================

try:
    from routes.f1_search_streaming import router as f1_search_router
    app.include_router(f1_search_router)
    logger.info("✅ F1 Search Streaming routes registered at /api/f1/search/*")
except Exception as e:
    logger.error(f"❌ Failed to register F1 Search routes: {e}")
    logger.error("F1 Search endpoints will not be available")

# ============================================================================
# RECEIVING UPLOAD PROXY (Receiving Lens v1)
# ============================================================================

try:
    from routes.receiving_upload import router as receiving_upload_router
    app.include_router(receiving_upload_router)
    logger.info("✅ Receiving Upload Proxy registered at /api/receiving/*")
except Exception as e:
    logger.error(f"❌ Failed to register Receiving Upload Proxy: {e}")
    logger.error("Receiving image upload endpoints will not be available")

# ============================================================================
# RAG ANSWER ENDPOINT
# ============================================================================

try:
    from routes.rag_endpoint import router as rag_router
    app.include_router(rag_router)
    logger.info("✅ RAG endpoint registered at /api/rag/*")
except Exception as e:
    logger.error(f"❌ Failed to register RAG endpoint: {e}")
    logger.error("RAG answer endpoints will not be available")

try:
    from routes.document_routes import router as document_router
    app.include_router(document_router)
    logger.info("✅ Document routes registered at /v1/documents/*")
except Exception as e:
    logger.error(f"❌ Failed to register document routes: {e}")
    logger.error("Document link/unlink endpoints will not be available")

# ============================================================================
# HOURS OF REST ROUTES (Crew Compliance - MLC 2006 & STCW)
# ============================================================================

try:
    from routes.hours_of_rest_routes import router as hor_router
    app.include_router(hor_router)
    logger.info("✅ Hours of Rest routes registered at /v1/hours-of-rest/*")
except Exception as e:
    logger.error(f"❌ Failed to register Hours of Rest routes: {e}")
    logger.error("Hours of Rest endpoints will not be available")

# ============================================================================
# HANDOVER EXPORT ROUTES (Phase 14 - Editable Workflow)
# ============================================================================

try:
    from routes.handover_export_routes import router as handover_export_router
    app.include_router(handover_export_router)
    logger.info("✅ Handover Export routes registered at /v1/handover/*")
except Exception as e:
    logger.error(f"❌ Failed to register Handover Export routes: {e}")
    logger.error("Handover Export endpoints will not be available")

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    yacht_id: Optional[str] = Field(None, description="UUID of the yacht (optional - derived from JWT)")
    limit: int = Field(default=20, ge=1, le=100, description="Max results per capability")

class ExtractRequest(BaseModel):
    query: str = Field(..., description="Text to extract entities from")

class Entity(BaseModel):
    type: str
    value: str
    confidence: float = 0.8
    extraction_type: Optional[str] = None  # Backend extraction type (PART_NUMBER, EQUIPMENT_NAME, etc.)

class SearchContext(BaseModel):
    """Context info from domain/intent detection with confidence scores."""
    domain: Optional[str] = None
    domain_confidence: float = 0.0
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    mode: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    is_vague: bool = False

class MicroAction(BaseModel):
    """Action button returned from action surfacing."""
    action: str
    label: str
    side_effect: str
    requires_confirm: bool
    prefill: Dict[str, Any] = {}

class SearchResponse(BaseModel):
    success: bool
    query: str
    results: List[Dict[str, Any]]
    total_count: int
    available_actions: List[Dict[str, Any]]
    entities: List[Entity]
    plans: List[Dict[str, Any]]
    timing_ms: Dict[str, float]
    results_by_domain: Dict[str, Any] = {}
    error: Optional[str] = None
    # NEW: Action surfacing fields
    context: Optional[SearchContext] = None
    actions: List[MicroAction] = []

class ExtractResponse(BaseModel):
    success: bool
    entities: List[Entity]
    unknown_terms: List[str]
    timing_ms: float

class HealthResponse(BaseModel):
    status: str
    version: str
    pipeline_ready: bool

# ============================================================================
# LAZY LOADERS
# ============================================================================

_pipeline = None
_extractor = None

# Import centralized Supabase client factory from integrations/supabase.py
# This consolidates all Supabase client creation in one place with:
# - Error recovery (auto-reconnect after 3 consecutive errors)
# - 5-second HTTP timeout for defense in depth
# - Tenant-specific client caching
from integrations.supabase import (
    get_supabase_client,
    get_tenant_client,
    mark_supabase_error,
    reset_supabase_error_count,
)

def get_extractor():
    """Lazy-load extraction orchestrator."""
    global _extractor
    if _extractor is None:
        try:
            from extraction.orchestrator import ExtractionOrchestrator
            logger.info("Initializing ExtractionOrchestrator...")
            _extractor = ExtractionOrchestrator()
            logger.info("✅ ExtractionOrchestrator initialized successfully")
        except Exception as e:
            import traceback
            logger.error(f"❌ Failed to load extractor: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return None
    return _extractor

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Minimal health check - no Pydantic, no dependencies."""
    return {"status": "ok"}


@app.get("/", response_model=HealthResponse)
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    pipeline_ready = get_supabase_client() is not None
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        pipeline_ready=pipeline_ready,
    )


@app.get("/version")
async def version():
    """Version endpoint - returns git commit and environment."""
    return {
        "git_commit": GIT_COMMIT,
        "environment": ENVIRONMENT,
        "version": "2026.02.20.001",
        "api": "f1_search",
        "deploy_timestamp": DEPLOY_TIMESTAMP,
        "critical_fixes": [
            "F1 Search Hardening: Removed /webhook/search legacy route",
            "F1 Search Hardening: Deleted pipeline_v1.py hard tier scoring",
            "F1 Search Hardening: Deleted result_ranker.py EXACT_ID=1000 walls"
        ]
    }


# ============================================================================
# BOOTSTRAP ENDPOINT (Frontend Auth Context)
# ============================================================================

class BootstrapResponse(BaseModel):
    """Response from /v1/bootstrap endpoint."""
    yacht_id: Optional[str] = None
    yacht_name: Optional[str] = None
    tenant_key_alias: Optional[str] = None
    role: str = "member"
    status: str = "PENDING"
    user_id: Optional[str] = None
    email: Optional[str] = None


@app.post("/v1/bootstrap", response_model=BootstrapResponse)
@app.get("/v1/bootstrap", response_model=BootstrapResponse)
async def bootstrap(
    auth: dict = Depends(get_authenticated_user)
):
    """
    Bootstrap endpoint for frontend auth context.

    This endpoint replaces direct Supabase RPC calls to get_my_bootstrap().
    The frontend (Vercel) cannot call MASTER DB directly - it only has
    TENANT credentials. This endpoint runs on Render which HAS MASTER credentials.

    Flow:
    1. Frontend sends JWT to Render
    2. Render validates JWT using MASTER_SUPABASE_JWT_SECRET
    3. Render looks up user's tenant from MASTER DB (via get_authenticated_user)
    4. Returns bootstrap data to frontend

    Returns:
        {
            "yacht_id": "uuid",
            "yacht_name": "M/Y Vessel Name",
            "tenant_key_alias": "y85fe1119...",
            "role": "chief_engineer",
            "status": "ACTIVE",
            "user_id": "uuid",
            "email": "user@example.com"
        }

    Note: get_authenticated_user() already does the tenant lookup from MASTER DB.
    If it succeeds, user is active and has a yacht assignment.
    """
    logger.info(f"[bootstrap] user={auth['user_id'][:8]}..., yacht={auth['yacht_id']}")

    return BootstrapResponse(
        yacht_id=auth['yacht_id'],
        yacht_name=auth.get('yacht_name'),
        tenant_key_alias=auth['tenant_key_alias'],
        role=auth.get('role', 'member'),
        status='ACTIVE',  # get_authenticated_user only returns active users
        user_id=auth['user_id'],
        email=auth.get('email'),
    )


@app.post("/debug/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Main search endpoint with JWT authentication.

    Flow: JWT verify → Tenant lookup → f1_search_fusion(with p_filters) → Actions → Surface

    Auth:
        - JWT verified using MASTER_SUPABASE_JWT_SECRET
        - Tenant (yacht_id) looked up from MASTER DB user_accounts
        - Request routed to tenant's per-yacht Supabase DB

    Returns:
        - results: Search results from f1_search_fusion with structured filters
        - context: Domain/intent/mode from action_surfacing
        - actions: Microaction buttons filtered by role
    """
    import json
    start = time.time()

    # Get yacht_id from auth context (override request body if present)
    yacht_id = auth['yacht_id']
    tenant_key_alias = auth['tenant_key_alias']
    role = auth.get('role', 'crew')

    logger.info(f"[search] user={auth['user_id'][:8]}..., yacht={yacht_id}, tenant={tenant_key_alias}, role={role}")

    # Get tenant-specific Supabase client
    try:
        client = get_tenant_client(tenant_key_alias)
    except ValueError as e:
        logger.error(f"[search] Tenant client error: {e}")
        raise HTTPException(status_code=500, detail="Tenant configuration error")

    try:
        from services.action_surfacing import surface_actions_for_query, get_fusion_params_for_query
        from rag.context_builder import generate_query_embedding
        from services.domain_microactions import get_detection_context

        # Get detection context (domain, intent, mode with confidence scores)
        detection_ctx = get_detection_context(request.query)
        logger.info(f"[search] detection: domain={detection_ctx['domain']}, conf={detection_ctx['domain_confidence']:.2f}, intent={detection_ctx['intent']}, mode={detection_ctx['mode']}")

        # Get fusion params for domain-aware search (includes p_filters)
        fusion_params = get_fusion_params_for_query(request.query)
        logger.info(f"[search] fusion_params: {fusion_params}")

        # Generate query embedding for vector search
        embedding_start = time.time()
        query_embedding = generate_query_embedding(request.query)
        embedding_ms = (time.time() - embedding_start) * 1000

        # Build vector literal for PostgreSQL
        vec_literal = None
        if query_embedding:
            vec_literal = '[' + ','.join(str(x) for x in query_embedding) + ']'

        # Extract filter params
        p_domain = fusion_params.get('p_domain')
        p_mode = fusion_params.get('p_mode', 'explore')
        p_domain_boost = fusion_params.get('p_domain_boost', 0.25)
        p_filters = fusion_params.get('p_filters')

        # Call f1_search_fusion with structured filters
        # Note: Supabase RPC accepts dict for jsonb, handles serialization
        # F1 OPTIMIZATION: Pass reduced candidate counts from fusion_params
        fusion_start = time.time()
        rpc_params = {
            'p_yacht_id': yacht_id,
            'p_query_text': request.query,
            'p_query_embedding': vec_literal,
            'p_role': role,
            'p_lens': 'default',
            'p_domain': p_domain,
            'p_mode': p_mode,
            'p_domain_boost': p_domain_boost,
            'p_limit': request.limit,
            'p_offset': 0,
            'p_debug': False,
            'p_filters': p_filters,  # Pass dict directly, not JSON string
        }
        # Add F1 optimization params if present
        if 'p_m_text' in fusion_params:
            rpc_params['p_m_text'] = fusion_params['p_m_text']
        if 'p_m_vec' in fusion_params:
            rpc_params['p_m_vec'] = fusion_params['p_m_vec']
        if 'p_m_trgm' in fusion_params:
            rpc_params['p_m_trgm'] = fusion_params['p_m_trgm']

        result = client.rpc('f1_search_fusion', rpc_params).execute()
        fusion_ms = (time.time() - fusion_start) * 1000

        # Process results
        results = []
        if result.data:
            for row in result.data:
                results.append({
                    'object_id': row.get('object_id'),
                    'object_type': row.get('object_type'),
                    'payload': row.get('payload', {}),
                    'score': row.get('final_score', 0),
                })

        # Surface actions based on query and results
        action_data = surface_actions_for_query(
            query=request.query,
            role=role,
            search_results=results,
            yacht_id=yacht_id
        )

        # Build context from detection with confidence scores
        context = SearchContext(
            domain=detection_ctx['domain'],
            domain_confidence=detection_ctx['domain_confidence'],
            intent=detection_ctx['intent'],
            intent_confidence=detection_ctx['intent_confidence'],
            mode=detection_ctx['mode'],
            filters=detection_ctx['filters'],
            is_vague=detection_ctx['is_vague']
        )

        # Build microaction list
        actions = [
            MicroAction(
                action=a['action'],
                label=a['label'],
                side_effect=a['side_effect'],
                requires_confirm=a['requires_confirm'],
                prefill=a.get('prefill', {})
            )
            for a in action_data.get('actions', [])
        ]

        total_ms = (time.time() - start) * 1000

        return SearchResponse(
            success=True,
            query=request.query,
            results=results,
            total_count=len(results),
            available_actions=[],  # Deprecated, use actions field
            entities=[],  # Extraction disabled for f1_search_fusion path
            plans=[],
            timing_ms={
                "embedding": embedding_ms,
                "fusion": fusion_ms,
                "total": total_ms,
            },
            results_by_domain={},
            error=None,
            # Action surfacing fields
            context=context,
            actions=actions,
        )

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract", response_model=ExtractResponse)
@limiter.limit("100/minute")
async def extract(extract_request: ExtractRequest, request: Request):
    """
    Entity extraction only (no database query).

    Useful for testing extraction in isolation.
    """
    start = time.time()

    extractor = get_extractor()
    if not extractor:
        raise HTTPException(status_code=503, detail="Extractor not available")

    try:
        result = await extractor.extract(extract_request.query)

        # Normalize entities
        entities = []
        raw_entities = result.get("entities", {})

        if isinstance(raw_entities, dict):
            for entity_type, values in raw_entities.items():
                if not isinstance(values, list):
                    values = [values]
                for value in values:
                    entities.append(Entity(
                        type=entity_type.upper(),
                        value=value,
                        confidence=0.8,
                    ))

        elapsed = (time.time() - start) * 1000

        return ExtractResponse(
            success=True,
            entities=entities,
            unknown_terms=result.get("unknown_term", []),
            timing_ms=elapsed,
        )

    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/capabilities")
async def list_capabilities():
    """List all active capabilities and their entity triggers."""
    try:
        from execute.table_capabilities import get_active_capabilities, TABLE_CAPABILITIES

        active = get_active_capabilities()

        return {
            "active_count": len(active),
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "entity_triggers": cap.entity_triggers,
                    "available_actions": cap.available_actions,
                }
                for cap in active.values()
            ],
            "blocked": [
                {
                    "name": name,
                    "reason": cap.blocked_reason,
                }
                for name, cap in TABLE_CAPABILITIES.items()
                if name not in active
            ],
        }

    except Exception as e:
        logger.error(f"Failed to list capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/entity-types")
async def list_entity_types():
    """List supported entity types and their capability mappings."""
    try:
        from prepare.capability_composer import ENTITY_TO_SEARCH_COLUMN

        return {
            "count": len(ENTITY_TO_SEARCH_COLUMN),
            "mappings": {
                entity_type: {
                    "capability": cap_name,
                    "search_column": col_name,
                }
                for entity_type, (cap_name, col_name) in ENTITY_TO_SEARCH_COLUMN.items()
            },
        }

    except Exception as e:
        logger.error(f"Failed to list entity types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENTITY FETCHING ENDPOINT
# ============================================================================

@app.get("/v1/entity/fault/{fault_id}")
async def get_fault_entity(
    fault_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Fetch fault by ID for entity viewer (ContextPanel)."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']

        # Use tenant-specific client for multi-tenant isolation
        supabase = get_tenant_client(tenant_key)

        response = supabase.table('pms_faults').select('*').eq('id', fault_id).eq('yacht_id', yacht_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Fault not found")

        data = response.data
        return {
            "id": data.get('id'),
            "title": data.get('title') or data.get('fault_code', 'Unknown Fault'),
            "description": data.get('description', ''),
            "severity": data.get('severity', 'medium'),
            "equipment_id": data.get('equipment_id'),
            "equipment_name": data.get('equipment_name'),
            "reported_at": data.get('reported_at') or data.get('detected_at'),
            "reporter": data.get('reporter') or data.get('reported_by', 'System'),
            "status": data.get('status'),
            "has_work_order": data.get('has_work_order', False),
            "ai_diagnosis": data.get('ai_diagnosis'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch fault {fault_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _is_user_hod(user_id: str, yacht_id: str, supabase) -> bool:
    """
    Check if user has Head of Department (HOD) role.

    HOD roles include: chief_engineer, chief_officer, captain, purser

    Args:
        user_id: User UUID
        yacht_id: Yacht UUID
        supabase: Supabase client

    Returns:
        True if user is HOD, False otherwise
    """
    try:
        # Query auth_users_roles table for HOD roles
        result = supabase.table('auth_users_roles').select('role').eq(
            'user_id', user_id
        ).eq(
            'yacht_id', yacht_id
        ).eq(
            'is_active', True
        ).in_(
            'role', ['chief_engineer', 'chief_officer', 'captain', 'purser']
        ).maybe_single().execute()

        return bool(result.data)
    except Exception as e:
        logger.warning(f"Failed to check HOD status for user {user_id}: {e}")
        return False


def _determine_available_actions(
    work_order: Dict,
    user_role: str,
    is_hod: bool
) -> List[Dict]:
    """
    Determine which actions are available based on work order state.

    Business Rules:
    - status=planned: Can start, cancel
    - status=in_progress: Can add part, add note, complete (HOD only)
    - status=completed: Can reopen
    - status=cancelled: No actions

    Args:
        work_order: Work order data dict
        user_role: User's role (from JWT)
        is_hod: Whether user is Head of Department

    Returns:
        List of available action dicts (max 6 per lens convention)
    """
    actions = []
    status = work_order.get('status', '').lower()

    # Status: planned - can start or cancel
    if status == 'planned':
        actions.append({
            "name": "Start Work Order",
            "endpoint": "/v1/actions/work_order/start",
            "requires_signature": False,
            "method": "POST"
        })
        actions.append({
            "name": "Cancel",
            "endpoint": "/v1/actions/work_order/cancel",
            "requires_signature": False,
            "method": "POST"
        })

    # Status: in_progress - can add parts/notes, complete (HOD only)
    elif status == 'in_progress':
        actions.append({
            "name": "Add Part",
            "endpoint": "/v1/actions/work_order/add_part",
            "requires_signature": False,
            "method": "POST"
        })
        actions.append({
            "name": "Add Note",
            "endpoint": "/v1/actions/work_order/add_note",
            "requires_signature": False,
            "method": "POST"
        })

        # Only HOD can complete work orders
        if is_hod:
            actions.append({
                "name": "Complete",
                "endpoint": "/v1/actions/work_order/complete",
                "requires_signature": True,  # HOD signature required
                "method": "POST"
            })

    # Status: completed - can reopen
    elif status == 'completed':
        actions.append({
            "name": "Reopen",
            "endpoint": "/v1/actions/work_order/reopen",
            "requires_signature": False,
            "method": "POST"
        })

    # Status: cancelled - no actions available
    # (actions list remains empty)

    # Max 6 actions per lens (from planning docs)
    return actions[:6]


@app.get("/v1/entity/work_order/{work_order_id}")
async def get_work_order_entity(
    work_order_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Fetch work order by ID with ALL related data for entity viewer (ContextPanel).

    Returns enriched work order with:
    - Main work order details
    - Notes (from pms_work_order_notes)
    - Parts used (from pms_work_order_parts with joined part details)
    - Checklist items (from pms_work_order_checklist)
    - Audit history (from pms_audit_log)
    - Available actions (state-dependent action buttons)

    Empty arrays [] are returned when no related data exists,
    enabling frontend to show empty states with CTAs.
    """
    try:
        yacht_id = auth['yacht_id']
        user_id = auth['user_id']
        user_role = auth.get('role', 'crew')

        # Use local get_supabase_client (uses DEFAULT_YACHT_CODE env var)
        supabase = get_supabase_client()
        if not supabase:
            raise HTTPException(status_code=500, detail="Database connection unavailable")

        # 1. Fetch main work order
        # Try both 'id' and 'work_order_id' columns for compatibility
        response = supabase.table('pms_work_orders').select('*').eq('id', work_order_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not response.data:
            # Fallback: try work_order_id column
            response = supabase.table('pms_work_orders').select('*').eq('work_order_id', work_order_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Work order not found")

        data = response.data
        wo_id = data.get('id') or data.get('work_order_id')

        # 2. Fetch notes
        notes_response = supabase.table('pms_work_order_notes').select(
            'id, note_text, note_type, created_by, created_at'
        ).eq('work_order_id', wo_id).order('created_at', desc=True).execute()
        notes = notes_response.data if notes_response.data else []

        # 3. Fetch parts with joined part details
        parts_response = supabase.table('pms_work_order_parts').select(
            'id, part_id, quantity, notes, created_at, pms_parts(id, name, part_number, location)'
        ).eq('work_order_id', wo_id).execute()
        parts = parts_response.data if parts_response.data else []

        # 4. Fetch checklist items
        try:
            checklist_response = supabase.table('pms_work_order_checklist').select(
                'id, title, description, is_completed, completed_by, completed_at, sequence'
            ).eq('work_order_id', wo_id).order('sequence').execute()
            checklist = checklist_response.data if checklist_response.data else []
        except Exception:
            # Table might not exist in all environments
            checklist = []

        # 5. Fetch audit history
        audit_response = supabase.table('pms_audit_log').select(
            'id, action, old_values, new_values, user_id, created_at'
        ).eq('entity_type', 'work_order').eq('entity_id', wo_id).eq('yacht_id', yacht_id).order('created_at', desc=True).limit(50).execute()
        audit_history = audit_response.data if audit_response.data else []

        # 6. Determine available actions based on work order state and user role
        is_hod = await _is_user_hod(user_id, yacht_id, supabase)
        available_actions = _determine_available_actions(
            work_order=data,
            user_role=user_role,
            is_hod=is_hod
        )

        # 7. Build enriched response
        return {
            # Core work order data
            "id": wo_id,
            "wo_number": data.get('wo_number'),
            "title": data.get('title', 'Untitled Work Order'),
            "description": data.get('description', ''),
            "status": data.get('status', 'pending'),
            "priority": data.get('priority', 'medium'),
            "type": data.get('type') or data.get('work_order_type'),

            # Related equipment
            "equipment_id": data.get('equipment_id'),
            "equipment_name": data.get('equipment_name'),

            # Assignment
            "assigned_to": data.get('assigned_to'),
            "assigned_to_name": data.get('assigned_to_name'),

            # Dates
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
            "due_date": data.get('due_date'),
            "completed_at": data.get('completed_at'),
            "completed_by": data.get('completed_by'),

            # Related fault (if created from fault)
            "fault_id": data.get('fault_id'),

            # === ENRICHED DATA (empty arrays if none exist) ===
            "notes": notes,
            "parts": parts,
            "checklist": checklist,
            "audit_history": audit_history,

            # Counts for quick display
            "notes_count": len(notes),
            "parts_count": len(parts),
            "checklist_count": len(checklist),
            "checklist_completed": len([c for c in checklist if c.get('is_completed')]),

            # === AVAILABLE ACTIONS (state-dependent) ===
            "available_actions": available_actions,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch work order {work_order_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/entity/equipment/{equipment_id}")
async def get_equipment_entity(
    equipment_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Fetch equipment by ID for entity viewer (ContextPanel)."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']

        # Use tenant-specific client for multi-tenant isolation
        supabase = get_tenant_client(tenant_key)

        # Fixed: Use correct column name 'id' not 'equipment_id'
        response = supabase.table('pms_equipment').select('*').eq('id', equipment_id).eq('yacht_id', yacht_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Equipment not found")

        data = response.data
        # Fixed: Map to actual database column names
        metadata = data.get('metadata') or {}
        return {
            "id": data.get('id'),
            "name": data.get('name', 'Unknown Equipment'),
            "equipment_type": data.get('system_type') or metadata.get('category', 'General'),
            "manufacturer": data.get('manufacturer'),
            "model": data.get('model'),
            "serial_number": data.get('serial_number'),
            "location": data.get('location', 'Unknown'),
            "status": metadata.get('status', 'operational'),
            "criticality": data.get('criticality'),
            "installation_date": data.get('installed_date'),
            "last_maintenance": metadata.get('last_maintenance'),
            "next_maintenance": metadata.get('next_maintenance'),
            "description": data.get('description'),
            "attention_flag": data.get('attention_flag'),
            "attention_reason": data.get('attention_reason'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch equipment {equipment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/entity/part/{part_id}")
async def get_part_entity(
    part_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Fetch part by ID for entity viewer (ContextPanel)."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']

        # Use tenant-specific client for multi-tenant isolation
        supabase = get_tenant_client(tenant_key)

        # Fixed: Use correct column name 'id' not 'part_id'
        response = supabase.table('pms_parts').select('*').eq('id', part_id).eq('yacht_id', yacht_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Part not found")

        data = response.data
        # Fixed: Map to actual database column names
        metadata = data.get('metadata') or {}
        return {
            "id": data.get('id'),
            "part_name": data.get('name', 'Unknown Part'),
            "part_number": data.get('part_number', ''),
            "stock_quantity": data.get('quantity_on_hand', 0),
            "min_stock_level": data.get('minimum_quantity') or data.get('min_level', 0),
            "location": data.get('location', 'Unknown'),
            "unit_cost": metadata.get('unit_cost'),
            "supplier": metadata.get('supplier'),
            "category": data.get('category'),
            "unit": data.get('unit'),
            "manufacturer": data.get('manufacturer'),
            "description": data.get('description'),
            "last_counted_at": data.get('last_counted_at'),
            "last_counted_by": data.get('last_counted_by'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch part {part_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/entity/receiving/{receiving_id}")
async def get_receiving_entity(
    receiving_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Fetch receiving by ID for entity viewer (DeepLinkHandler).

    Returns receiving data with status field required for getReceivingActions().
    """
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']

        # Get TENANT supabase client
        # Use tenant-specific client for multi-tenant isolation
        supabase = get_tenant_client(tenant_key)

        # Fetch receiving from pms_receiving
        response = supabase.table('pms_receiving') \
            .select('*') \
            .eq('id', receiving_id) \
            .eq('yacht_id', yacht_id) \
            .single() \
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Receiving not found")

        data = response.data

        # Return data compatible with ReceivingCard
        return {
            "id": data.get('id'),
            "vendor_name": data.get('vendor_name'),
            "vendor_reference": data.get('vendor_reference'),
            "received_date": data.get('received_date'),
            "status": data.get('status', 'draft'),  # CRITICAL: Required for getReceivingActions()
            "total": data.get('total'),
            "currency": data.get('currency'),
            "notes": data.get('notes'),
            "received_by": data.get('received_by'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch receiving {receiving_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EMAIL LENS ENDPOINTS
# ============================================================================

@app.get("/v1/email/threads")
@limiter.limit("60/minute")
async def get_email_threads(
    request: Request,
    page: int = 1,
    limit: int = 20,
    query: str = "",
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get email threads for inbox view.

    Returns paginated email threads with metadata.
    Per doctrine: metadata only, no bodies stored.
    """
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']

        # Use tenant-specific client for multi-tenant isolation
        supabase = get_tenant_client(tenant_key)

        offset = (page - 1) * limit

        # Build query
        threads_query = supabase.table('email_threads').select(
            'id, provider_conversation_id, latest_subject, message_count, has_attachments, source, first_message_at, last_activity_at, created_at'
        ).eq('yacht_id', yacht_id).order(
            'last_activity_at', desc=True
        ).range(offset, offset + limit - 1)

        # Apply search filter if query provided
        if query and len(query.strip()) > 0:
            threads_query = threads_query.ilike('latest_subject', f'%{query}%')

        result = threads_query.execute()
        threads = result.data if result.data else []

        # Check if there are more results
        has_more = len(threads) == limit

        return {
            "threads": threads,
            "page": page,
            "limit": limit,
            "has_more": has_more,
            "query": query,
        }

    except Exception as e:
        logger.error(f"Failed to fetch email threads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/email/thread/{thread_id}")
async def get_email_thread(
    thread_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get single email thread with messages.

    Returns thread metadata and message list.
    Per doctrine: no bodies stored, content fetched on-demand from Graph.
    """
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']

        # Use tenant-specific client for multi-tenant isolation
        supabase = get_tenant_client(tenant_key)

        # Get thread
        thread_result = supabase.table('email_threads').select(
            'id, provider_conversation_id, latest_subject, message_count, has_attachments, participant_hashes, source, first_message_at, last_activity_at, last_inbound_at, last_outbound_at, created_at'
        ).eq('id', thread_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Email thread not found")

        thread = thread_result.data

        # Get messages in thread
        messages_result = supabase.table('email_messages').select(
            'id, provider_message_id, internet_message_id, direction, from_display_name, subject, sent_at, received_at, has_attachments, attachments, folder'
        ).eq('thread_id', thread_id).eq('yacht_id', yacht_id).order(
            'sent_at', desc=False
        ).execute()

        messages = messages_result.data if messages_result.data else []

        return {
            "thread": thread,
            "messages": messages,
            "message_count": len(messages),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch email thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/email/thread/{thread_id}/links")
async def get_thread_links(
    thread_id: str,
    min_confidence: float = 0.5,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get linked entities for an email thread.

    Returns work orders, equipment, parts linked to this thread.
    """
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']

        # Use tenant-specific client for multi-tenant isolation
        supabase = get_tenant_client(tenant_key)

        # Get linked objects
        links_result = supabase.table('email_links').select(
            'id, object_type, object_id, confidence, suggested_reason, suggested_at, accepted_at, is_active'
        ).eq('thread_id', thread_id).eq('yacht_id', yacht_id).eq(
            'is_active', True
        ).execute()

        links = links_result.data if links_result.data else []

        return {
            "thread_id": thread_id,
            "links": links,
            "count": len(links),
        }

    except Exception as e:
        logger.error(f"Failed to fetch thread links {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LinkEmailRequest(BaseModel):
    """Request body for linking email to entity."""
    object_type: str = Field(..., description="Type: work_order, equipment, part, fault")
    object_id: str = Field(..., description="ID of the entity to link")
    confidence: str = Field("user_confirmed", description="Confidence level")


@app.post("/v1/email/thread/{thread_id}/link")
async def link_email_to_entity(
    thread_id: str,
    link_request: LinkEmailRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Link email thread to an entity (work order, equipment, part, fault).

    Per doctrine: linking is a conscious act, all changes ledgered.
    """
    try:
        yacht_id = auth['yacht_id']
        user_id = auth['user_id']
        tenant_key = auth['tenant_key_alias']

        from datetime import datetime, timezone
        # Use tenant-specific client for multi-tenant isolation
        supabase = get_tenant_client(tenant_key)

        # Validate thread exists
        thread_result = supabase.table('email_threads').select(
            'id, latest_subject'
        ).eq('id', thread_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Email thread not found")

        thread = thread_result.data

        # Check for existing active link
        existing_result = supabase.table('email_links').select(
            'id'
        ).eq('thread_id', thread_id).eq('object_type', link_request.object_type).eq(
            'object_id', link_request.object_id
        ).eq('is_active', True).maybe_single().execute()

        if existing_result.data:
            raise HTTPException(status_code=409, detail="Link already exists")

        # Create link
        now = datetime.now(timezone.utc).isoformat()
        link_data = {
            "yacht_id": yacht_id,
            "thread_id": thread_id,
            "object_type": link_request.object_type,
            "object_id": link_request.object_id,
            "confidence": link_request.confidence,
            "suggested_reason": "manual",
            "suggested_at": now,
            "accepted_at": now if link_request.confidence == "user_confirmed" else None,
            "accepted_by": user_id if link_request.confidence == "user_confirmed" else None,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        result = supabase.table('email_links').insert(link_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create link")

        link = result.data[0]

        # Log to audit
        try:
            supabase.table('pms_audit_log').insert({
                "yacht_id": yacht_id,
                "action": "link_email",
                "entity_type": "email_link",
                "entity_id": link["id"],
                "user_id": user_id,
                "old_values": None,
                "new_values": {
                    "thread_id": thread_id,
                    "object_type": link_request.object_type,
                    "object_id": link_request.object_id,
                },
                "signature": {},
                "metadata": {"source": "lens", "lens": "email"},
                "created_at": now,
            }).execute()
        except Exception as audit_err:
            logger.warning(f"Failed to create audit log: {audit_err}")

        return {
            "status": "success",
            "link_id": link["id"],
            "thread_id": thread_id,
            "object_type": link_request.object_type,
            "object_id": link_request.object_id,
            "message": f"Linked email to {link_request.object_type}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to link email {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/email/search")
@limiter.limit("60/minute")
async def search_emails(
    request: Request,
    q: str = "",
    limit: int = 50,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Search emails by query string.

    Searches across email threads and messages by subject.
    Returns metadata only (no bodies per doctrine).
    """
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']

        # Use tenant-specific client for multi-tenant isolation
        supabase = get_tenant_client(tenant_key)

        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 50

        if not q or len(q.strip()) < 2:
            return {
                "results": [],
                "query": q,
                "count": 0,
            }

        # Search in email_messages for better results
        messages_result = supabase.table('email_messages').select(
            'id, thread_id, subject, from_display_name, sent_at, has_attachments, body_preview'
        ).eq('yacht_id', yacht_id).ilike(
            'subject', f'%{q}%'
        ).order('sent_at', desc=True).limit(limit).execute()

        messages = messages_result.data if messages_result.data else []

        # Transform to search results
        results = []
        seen_threads = set()
        for msg in messages:
            if msg['thread_id'] not in seen_threads:
                seen_threads.add(msg['thread_id'])
                results.append({
                    "thread_id": msg['thread_id'],
                    "message_id": msg['id'],
                    "subject": msg['subject'],
                    "from_display_name": msg['from_display_name'],
                    "sent_at": msg['sent_at'],
                    "has_attachments": msg['has_attachments'],
                    "preview_text": msg.get('body_preview', ''),
                })

        return {
            "results": results,
            "query": q,
            "count": len(results),
        }

    except Exception as e:
        logger.error(f"Failed to search emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DIRECT TABLE QUERY ENDPOINT
# ============================================================================

class QueryRequest(BaseModel):
    """Request body for direct table queries."""
    table: str = Field(..., description="Table name to query")
    select: str = Field("*", description="Columns to select")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filter conditions")
    limit: int = Field(50, description="Maximum rows to return")
    offset: int = Field(0, description="Offset for pagination")
    order_by: Optional[str] = Field(None, description="Column to order by")
    order_desc: bool = Field(True, description="Order descending")


# Allowed tables for direct query (security whitelist)
QUERYABLE_TABLES = {
    'pms_equipment', 'pms_faults', 'pms_work_orders', 'pms_parts',
    'pms_notes', 'pms_attachments', 'pms_audit_log', 'pms_handover',
    'pms_purchase_orders', 'pms_suppliers', 'pms_worklist_tasks',
    'documents', 'email_threads', 'email_messages', 'email_links'
}


@app.post("/v1/query")
@limiter.limit("100/minute")
async def direct_query(
    request: Request,
    query_request: QueryRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Direct table query endpoint for fetching data.

    Security:
    - Only whitelisted tables can be queried
    - All queries are yacht_id scoped (RLS enforced)
    - Rate limited to 100 requests/minute
    """
    try:
        yacht_id = auth.get("yacht_id")
        tenant_key_alias = auth.get("tenant_key_alias")
        table = query_request.table

        # Security: only allow whitelisted tables
        if table not in QUERYABLE_TABLES:
            raise HTTPException(
                status_code=400,
                detail=f"Table '{table}' is not queryable. Allowed: {', '.join(sorted(QUERYABLE_TABLES))}"
            )

        # Get tenant client
        supabase = get_tenant_client(tenant_key_alias)

        # Build query
        query = supabase.table(table).select(query_request.select)

        # Apply yacht_id filter (mandatory for RLS)
        query = query.eq('yacht_id', yacht_id)

        # Apply additional filters
        if query_request.filters:
            for col, val in query_request.filters.items():
                if col != 'yacht_id':  # Already applied
                    query = query.eq(col, val)

        # Apply ordering
        if query_request.order_by:
            query = query.order(query_request.order_by, desc=query_request.order_desc)

        # Apply pagination
        query = query.range(query_request.offset, query_request.offset + query_request.limit - 1)

        # Execute
        result = query.execute()

        return {
            "success": True,
            "table": table,
            "data": result.data or [],
            "count": len(result.data or [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/v1/query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# ============================================================================
# DOCUMENT STREAMING ENDPOINT
# ============================================================================

def normalize_storage_path(storage_path: str, bucket: str = 'documents') -> str:
    """
    Normalize storage path for Supabase Storage API.

    Database stores: "documents/yacht_id/folder/file.pdf"
    API expects:     "yacht_id/folder/file.pdf"

    Args:
        storage_path: Path from database
        bucket: Bucket name to strip

    Returns:
        Normalized path without bucket prefix
    """
    prefix = f"{bucket}/"
    if storage_path.startswith(prefix):
        return storage_path[len(prefix):]
    return storage_path


@app.post("/v1/documents/{document_id}/sign")
@limiter.limit("60/minute")
async def sign_document_url(
    document_id: str,
    request: Request,
    auth: dict = Depends(get_authenticated_user),
    x_yacht_signature: str = Header(None, alias='X-Yacht-Signature')
):
    """
    Generate short-lived signed URL for document access.

    Security (Production-Grade for Yacht Fleet):
    - Validates JWT using MASTER_SUPABASE_JWT_SECRET
    - Tenant lookup from MASTER DB user_accounts
    - Enforces yacht_id isolation (user can only access their yacht's docs)
    - Verifies document ownership (document belongs to yacht)
    - Rate limited to prevent bulk download attacks
    - Audit logged for compliance (ISM Code, insurance requirements)
    - Short TTL (10 min) reduces leak window while allowing normal workflow

    Workflow:
    - Engineer opens document → frontend calls this endpoint
    - Gets signed URL (valid 10 min)
    - Fetches PDF once → converts to blob → works for hours
    - If page reloaded/memory evicted → calls this again

    Returns:
    - signed_url: Supabase Storage signed URL (10 min TTL)
    - expires_at: Unix timestamp when URL expires
    - document_id: Original document ID for client tracking
    - size_bytes: File size for progress indication
    """
    user_id = auth['user_id']
    yacht_id = auth['yacht_id']
    tenant_key_alias = auth['tenant_key_alias']
    ip_address = request.client.host if request.client else 'unknown'

    logger.info(f"[sign_document] user={user_id[:8]}..., yacht={yacht_id}, doc={document_id[:8]}..., ip={ip_address}")

    # Get tenant-specific Supabase client
    try:
        supabase = get_tenant_client(tenant_key_alias)
    except ValueError as e:
        logger.error(f"[sign_document] Tenant client error: {e}")
        raise HTTPException(500, detail="Tenant configuration error")

    # 1. Query doc_metadata with yacht isolation
    try:
        response = supabase.table('doc_metadata') \
            .select('id, filename, storage_path, content_type, yacht_id') \
            .eq('id', document_id) \
            .eq('yacht_id', yacht_id) \
            .single() \
            .execute()

        if not response.data:
            logger.warning(f"[sign_document] Document not found or access denied: {document_id}")

            # Audit: Log access denial
            try:
                supabase.table('audit_log').insert({
                    'action': 'document_sign_denied',
                    'entity_type': 'document',
                    'entity_id': document_id,
                    'user_id': user_id,
                    'yacht_id': yacht_id,
                    'old_values': None,
                    'new_values': {'reason': 'not_found_or_wrong_yacht'},
                    'signature': {
                        'user_id': user_id,
                        'timestamp': time.time(),
                        'ip_address': ip_address,
                    },
                }).execute()
            except Exception as audit_err:
                logger.error(f"[sign_document] Audit log failed: {audit_err}")

            raise HTTPException(404, detail="Document not found")

        doc = response.data
        logger.info(f"[sign_document] Access granted: {doc.get('filename')}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[sign_document] Database query failed: {e}")
        raise HTTPException(500, detail="Failed to query document metadata")

    # 2. Extract and normalize storage path
    storage_path = doc.get('storage_path', '')
    if not storage_path:
        raise HTTPException(404, detail="Document has no storage path")

    # Normalize path (remove bucket prefix if present)
    storage_path = normalize_storage_path(storage_path, bucket='documents')

    # 3. Generate short-lived signed URL (10 minutes)
    # Why 10 min: Balances security (short leak window) with UX (normal workflow)
    # - Engineer opens PDF, fetches once, converts to blob
    # - Blob stays in memory for hours (no re-fetch needed)
    # - 10 min allows: open, get interrupted, come back, re-open
    # - If >10 min away, simple re-search is reasonable
    TTL_SECONDS = 600  # 10 minutes

    try:
        signed_data = supabase.storage.from_('documents').create_signed_url(
            storage_path,
            TTL_SECONDS
        )

        if not signed_data or 'signedURL' not in signed_data:
            logger.error(f"[sign_document] create_signed_url returned invalid data: {signed_data}")
            raise HTTPException(500, detail="Failed to generate signed URL")

        signed_url = signed_data['signedURL']
        expires_at = int(time.time()) + TTL_SECONDS

        logger.info(f"[sign_document] Signed URL generated, expires in {TTL_SECONDS}s")

    except Exception as e:
        logger.error(f"[sign_document] Failed to create signed URL: {e}")
        raise HTTPException(500, detail="Failed to generate signed URL")

    # 4. Audit log: Document access (compliance requirement for yachts)
    try:
        supabase.table('audit_log').insert({
            'action': 'document_sign',
            'entity_type': 'document',
            'entity_id': document_id,
            'user_id': user_id,
            'yacht_id': yacht_id,
            'old_values': None,
            'new_values': {
                'filename': doc.get('filename'),
                'ttl_seconds': TTL_SECONDS,
                'storage_path': storage_path[:100],  # Truncate for privacy
                'signed_at': time.time(),
            },
            'signature': {
                'user_id': user_id,
                'timestamp': time.time(),
                'ip_address': ip_address,
            },
        }).execute()
        logger.info(f"[sign_document] Audit logged")
    except Exception as audit_err:
        # Don't fail request if audit fails, but log it
        logger.error(f"[sign_document] Audit log failed: {audit_err}")

    # 5. Get file size for client progress indication (optional, best effort)
    size_bytes = None
    try:
        file_info = supabase.storage.from_('documents').list(
            path=storage_path.rsplit('/', 1)[0],
            search=storage_path.rsplit('/', 1)[1]
        )
        if file_info and len(file_info) > 0:
            size_bytes = file_info[0].get('metadata', {}).get('size')
    except Exception as size_err:
        logger.debug(f"[sign_document] Could not get file size: {size_err}")

    # 6. Return signed URL + metadata
    return {
        "signed_url": signed_url,
        "expires_at": expires_at,
        "document_id": document_id,
        "filename": doc.get('filename'),
        "content_type": doc.get('content_type'),
        "size_bytes": size_bytes,
        "ttl_seconds": TTL_SECONDS,
    }


@app.get("/v1/documents/{document_id}/stream")
@limiter.limit("60/minute")
async def stream_document(
    request: Request,
    document_id: str,
    auth: dict = Depends(get_authenticated_user),
    x_yacht_signature: str = Header(None, alias='X-Yacht-Signature')
):
    """
    Stream document from Supabase Storage.

    Security:
    - Validates JWT using MASTER_SUPABASE_JWT_SECRET
    - Tenant lookup from MASTER DB
    - Enforces yacht_id isolation
    - Verifies document ownership

    Returns:
    - File bytes with proper Content-Type
    - Content-Disposition header for inline viewing
    """
    user_id = auth['user_id']
    yacht_id = auth['yacht_id']
    tenant_key_alias = auth['tenant_key_alias']

    logger.info(f"[stream_document] user={user_id[:8]}..., yacht={yacht_id}, doc={document_id[:8]}...")

    # Get tenant-specific Supabase client
    try:
        supabase = get_tenant_client(tenant_key_alias)
    except ValueError as e:
        logger.error(f"[stream_document] Tenant client error: {e}")
        raise HTTPException(500, detail="Tenant configuration error")

    # 1. Query doc_metadata with yacht isolation
    try:
        response = supabase.table('doc_metadata') \
            .select('*') \
            .eq('id', document_id) \
            .eq('yacht_id', yacht_id) \
            .single() \
            .execute()

        if not response.data:
            logger.warning(f"[stream_document] Document not found: {document_id}")
            raise HTTPException(404, detail="Document not found")

        doc = response.data
        logger.info(f"[stream_document] Found document: {doc.get('filename')}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[stream_document] Database query failed: {e}")
        raise HTTPException(500, detail="Failed to query document metadata")

    # 2. Extract correct storage path (strip 'documents/' prefix if present)
    storage_path = doc.get('storage_path', '')
    if not storage_path:
        raise HTTPException(404, detail="Document has no storage path")

    # Normalize path (remove bucket prefix if present)
    storage_path = normalize_storage_path(storage_path, bucket='documents')

    logger.info(f"[stream_document] Storage path: {storage_path[:50]}...")

    # 3. Download from Supabase Storage
    try:
        file_bytes = supabase.storage.from_('documents').download(storage_path)
        logger.info(f"[stream_document] Downloaded {len(file_bytes)} bytes")
    except Exception as e:
        logger.error(f"[stream_document] Storage download failed: {e}")
        raise HTTPException(404, detail=f"File not found in storage")

    # 4. Detect content type
    filename = doc.get('filename', 'document')
    content_type = doc.get('content_type')

    # Fallback content type detection from filename
    if not content_type:
        if filename.lower().endswith('.pdf'):
            content_type = 'application/pdf'
        elif filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            content_type = 'image/png' if filename.lower().endswith('.png') else 'image/jpeg'
        elif filename.lower().endswith('.txt'):
            content_type = 'text/plain'
        else:
            content_type = 'application/octet-stream'

    # 5. Return file stream
    logger.info(f"[stream_document] Streaming {filename} ({content_type})")

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=3600",
            "X-Document-Id": document_id,
        }
    )


# ============================================================================
# DEBUG ENDPOINTS
# ============================================================================

@app.get("/debug/extractor")
async def debug_extractor():
    """Debug endpoint to check extractor initialization."""
    import traceback
    import sys

    return {
        "python_version": sys.version,
        "sys_path": sys.path[:5],  # First 5 paths
        "cwd": os.getcwd(),
        "extractor_status": {
            "loaded": _extractor is not None,
            "attempt_result": None if _extractor else try_load_extractor_debug()
        }
    }

def try_load_extractor_debug():
    """Try to load extractor and return detailed error."""
    import traceback
    try:
        from extraction.orchestrator import ExtractionOrchestrator
        ExtractionOrchestrator()
        return {"success": True}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }


@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to check registered routes and import status."""
    import traceback as tb

    # Collect all registered route prefixes
    route_prefixes = set()
    route_count = 0
    for route in app.routes:
        route_count += 1
        if hasattr(route, 'path'):
            prefix = route.path.split('/')[1] if '/' in route.path else route.path
            route_prefixes.add(prefix)

    # Try to import p0_actions_routes and report any errors
    p0_status = {"loaded": False, "error": None}
    try:
        from routes.p0_actions_routes import router as test_router
        p0_status["loaded"] = True
        p0_status["prefix"] = test_router.prefix
        p0_status["route_count"] = len(test_router.routes)
    except Exception as e:
        p0_status["error"] = str(e)
        p0_status["traceback"] = tb.format_exc()

    # Check certificate handlers import
    cert_status = {"loaded": False, "error": None}
    try:
        from handlers.certificate_handlers import get_certificate_handlers
        cert_status["loaded"] = True
    except Exception as e:
        cert_status["error"] = str(e)
        cert_status["traceback"] = tb.format_exc()

    # List all actual route paths
    all_paths = []
    for route in app.routes:
        if hasattr(route, 'path'):
            all_paths.append(route.path)

    return {
        "total_routes": route_count,
        "route_prefixes": sorted(list(route_prefixes)),
        "has_v1_actions": "v1" in route_prefixes,
        "startup_import_error": _p0_import_error,
        "all_paths": sorted(all_paths),
        "p0_actions_status": p0_status,
        "certificate_handlers_status": cert_status,
        "env_vars": {
            "DEFAULT_YACHT_CODE": os.environ.get("DEFAULT_YACHT_CODE", "NOT_SET"),
            "has_supabase_url": bool(os.environ.get("SUPABASE_URL")),
            "has_supabase_key": bool(os.environ.get("SUPABASE_SERVICE_KEY")),
        }
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
