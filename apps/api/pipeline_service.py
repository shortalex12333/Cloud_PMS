"""
Pipeline V1 FastAPI Service
===========================

Unified search pipeline deployment for Render.

Endpoints:
- POST /search - Main search endpoint (text → entities → results → actions)
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
# Updated: 2026-01-13 - trigger redeploy for tenant routing
GIT_COMMIT = os.environ.get("RENDER_GIT_COMMIT", os.environ.get("GIT_COMMIT", "dev"))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

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
    title="CelesteOS Pipeline V1",
    description="Unified search pipeline: Extract → Prepare → Execute → Actions",
    version="1.0.0",
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

logger.info("✅ [Pipeline] Rate limiting enabled")

# ============================================================================
# P0 ACTIONS ROUTES
# ============================================================================

try:
    from routes.p0_actions_routes import router as p0_actions_router
    app.include_router(p0_actions_router)
    logger.info("✅ P0 Actions routes registered at /v1/actions/*")
except Exception as e:
    logger.error(f"❌ Failed to register P0 Actions routes: {e}")
    logger.error("P0 Actions will not be available via API")

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
_supabase_client = None
_supabase_client_errors = 0

def get_supabase_client(force_new: bool = False):
    """
    Lazy-load Supabase client with connection recovery.

    If the client is stale (>3 consecutive errors), recreate it.
    This handles connection pool exhaustion and timeout issues.
    """
    global _supabase_client, _supabase_client_errors

    # Force recreation if too many errors (connection might be stale)
    if _supabase_client_errors >= 3:
        logger.warning(f"[Supabase] Resetting client after {_supabase_client_errors} consecutive errors")
        _supabase_client = None
        _supabase_client_errors = 0
        force_new = True

    if _supabase_client is None or force_new:
        try:
            from supabase import create_client
            url = os.environ.get("SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
            key = os.environ.get("SUPABASE_SERVICE_KEY", "")
            if not key:
                logger.warning("SUPABASE_SERVICE_KEY not set")
                return None
            _supabase_client = create_client(url, key)
            _supabase_client_errors = 0  # Reset error count on successful creation
            logger.info("[Supabase] Client created/recreated successfully")
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            return None
    return _supabase_client

def mark_supabase_error():
    """Track consecutive Supabase errors for connection recovery."""
    global _supabase_client_errors
    _supabase_client_errors += 1
    logger.warning(f"[Supabase] Error count: {_supabase_client_errors}")

def reset_supabase_error_count():
    """Reset error count after successful operation."""
    global _supabase_client_errors
    if _supabase_client_errors > 0:
        _supabase_client_errors = 0

# ============================================================================
# TENANT CLIENT FACTORY (Per-Yacht DB Routing)
# ============================================================================

_tenant_clients: Dict[str, Any] = {}

def get_tenant_client(tenant_key_alias: str):
    """
    Get or create Supabase client for a specific tenant.

    Loads credentials from environment variables:
        {tenant_key_alias}_SUPABASE_URL
        {tenant_key_alias}_SUPABASE_SERVICE_KEY

    Args:
        tenant_key_alias: e.g., 'yTEST_YACHT_001'

    Returns:
        Supabase client for the tenant's database

    Raises:
        ValueError: If tenant credentials not found in environment
    """
    global _tenant_clients

    if tenant_key_alias in _tenant_clients:
        return _tenant_clients[tenant_key_alias]

    url_key = f'{tenant_key_alias}_SUPABASE_URL'
    key_key = f'{tenant_key_alias}_SUPABASE_SERVICE_KEY'

    tenant_url = os.environ.get(url_key)
    tenant_key = os.environ.get(key_key)

    if not tenant_url or not tenant_key:
        logger.error(f"[TenantClient] Missing credentials for {tenant_key_alias}")
        logger.error(f"[TenantClient] Expected env vars: {url_key}, {key_key}")
        raise ValueError(f'Missing credentials for tenant {tenant_key_alias}')

    try:
        from supabase import create_client
        client = create_client(tenant_url, tenant_key)
        _tenant_clients[tenant_key_alias] = client
        logger.info(f"[TenantClient] Created client for {tenant_key_alias}")
        return client
    except Exception as e:
        logger.error(f"[TenantClient] Failed to create client for {tenant_key_alias}: {e}")
        raise

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
        "version": "1.0.0",
        "api": "pipeline_v1"
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


@app.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Main search endpoint with JWT authentication.

    Flow: JWT verify → Tenant lookup → Query → Extract entities → Execute SQL → Actions

    Auth:
        - JWT verified using MASTER_SUPABASE_JWT_SECRET
        - Tenant (yacht_id) looked up from MASTER DB user_accounts
        - Request routed to tenant's per-yacht Supabase DB
    """
    start = time.time()

    # Get yacht_id from auth context (override request body if present)
    yacht_id = auth['yacht_id']
    tenant_key_alias = auth['tenant_key_alias']

    logger.info(f"[search] user={auth['user_id'][:8]}..., yacht={yacht_id}, tenant={tenant_key_alias}")

    # Get tenant-specific Supabase client
    try:
        client = get_tenant_client(tenant_key_alias)
    except ValueError as e:
        logger.error(f"[search] Tenant client error: {e}")
        raise HTTPException(status_code=500, detail="Tenant configuration error")

    try:
        from pipeline_v1 import Pipeline

        pipeline = Pipeline(client, yacht_id)
        response = pipeline.search(request.query, limit=request.limit)

        return SearchResponse(
            success=response.success,
            query=request.query,
            results=response.results,
            total_count=response.total_count,
            available_actions=response.available_actions,
            entities=[
                Entity(**e) for e in response.extraction.get("entities", [])
            ],
            plans=response.prepare.get("plans", []),
            timing_ms={
                "extraction": response.extraction_ms,
                "prepare": response.prepare_ms,
                "execute": response.execute_ms,
                "total": response.total_ms,
            },
            results_by_domain=response.results_by_domain,
            error=response.error,
        )

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/search")
@limiter.limit("100/minute")
async def webhook_search(
    request: Request,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Webhook endpoint for frontend search requests with JWT auth.

    Auth:
        - JWT verified using MASTER_SUPABASE_JWT_SECRET
        - Tenant (yacht_id) looked up from MASTER DB user_accounts
        - Request routed to tenant's per-yacht Supabase DB

    ALWAYS returns structured JSON - never raw 500 errors.
    """
    # Generate request_id for tracing
    request_id = str(uuid.uuid4())[:8]

    try:
        body = await request.json()
        query = body.get('query', '')
        limit = body.get('limit', 20)

        # Get yacht_id from JWT auth context (not from request body)
        yacht_id = auth['yacht_id']
        tenant_key_alias = auth['tenant_key_alias']

        logger.info(f"[webhook/search:{request_id}] user={auth['user_id'][:8]}..., yacht={yacht_id}, query='{query}'")

        # Validate required fields - return 400 JSON, not raw error
        if not query:
            logger.warning(f"[webhook/search:{request_id}] Missing query field")
            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "request_id": request_id,
                    "error_code": "MISSING_QUERY",
                    "message": "Missing required field: query",
                    "results": [],
                    "total_count": 0
                }
            )

        # Get tenant-specific Supabase client
        try:
            client = get_tenant_client(tenant_key_alias)
        except ValueError as e:
            logger.error(f"[webhook/search:{request_id}] Tenant client error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "request_id": request_id,
                    "error_code": "TENANT_CONFIG_ERROR",
                    "message": "Tenant configuration error",
                    "results": [],
                    "total_count": 0
                }
            )

        # Execute search with tenant's DB
        from pipeline_v1 import Pipeline
        pipeline = Pipeline(client, yacht_id)
        response = pipeline.search(query, limit=limit)

        # Frontend expects newline-delimited JSON for streaming parser
        import json

        response_data = {
            "success": response.success,
            "query": query,
            "results": response.results,
            "total_count": response.total_count,
            "available_actions": response.available_actions,
            "entities": response.extraction.get("entities", []),
            "plans": response.prepare.get("plans", []),
            "timing_ms": {
                "extraction": response.extraction_ms,
                "prepare": response.prepare_ms,
                "execute": response.execute_ms,
                "total": response.total_ms,
            },
            "results_by_domain": response.results_by_domain,
            "error": response.error,
            "request_id": request_id,
            "ok": response.success,
        }

        json_str = json.dumps(response_data) + "\n"
        logger.info(f"[webhook/search:{request_id}] Success: {response.success}, results: {response.total_count}")

        # Reset error count on success (connection is healthy)
        reset_supabase_error_count()

        return Response(content=json_str, media_type="application/json")

    except HTTPException as he:
        # Track errors for connection recovery
        if he.status_code >= 500:
            mark_supabase_error()

        logger.error(f"[webhook/search:{request_id}] HTTPException: {he.detail}")
        return JSONResponse(
            status_code=he.status_code,
            content={
                "ok": False,
                "request_id": request_id,
                "error_code": "HTTP_ERROR",
                "message": str(he.detail),
                "results": [],
                "total_count": 0
            }
        )
    except Exception as e:
        # Track errors for connection recovery
        mark_supabase_error()

        # CRITICAL: Never return raw 500 - always return structured JSON
        error_tb = traceback.format_exc()
        logger.error(f"[webhook/search:{request_id}] PIPELINE_INTERNAL_ERROR: {e}\n{error_tb}")

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "request_id": request_id,
                "error_code": "PIPELINE_INTERNAL",
                "message": f"Search failed: {str(e)}",
                "error_type": type(e).__name__,
                "results": [],
                "total_count": 0
            }
        )

@app.post("/extract", response_model=ExtractResponse)
@limiter.limit("100/minute")
async def extract(request: ExtractRequest):
    """
    Entity extraction only (no database query).

    Useful for testing extraction in isolation.
    """
    start = time.time()

    extractor = get_extractor()
    if not extractor:
        raise HTTPException(status_code=503, detail="Extractor not available")

    try:
        result = extractor.extract(request.query)

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


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
