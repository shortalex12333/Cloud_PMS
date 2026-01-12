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
GIT_COMMIT = os.environ.get("RENDER_GIT_COMMIT", os.environ.get("GIT_COMMIT", "dev"))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# Setup path for imports
from pathlib import Path
_api_dir = Path(__file__).parent
if str(_api_dir) not in sys.path:
    sys.path.insert(0, str(_api_dir))

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
    "https://auth.celeste7.ai,https://app.celeste7.ai,https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app,http://localhost:3000,http://localhost:8000"
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
# Use staging.celeste7.ai for pre-production testing instead

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
# REQUEST/RESPONSE MODELS
# ============================================================================

class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    yacht_id: str = Field(..., description="UUID of the yacht")
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

def get_supabase_client():
    """Lazy-load Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
            url = os.environ.get("SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
            key = os.environ.get("SUPABASE_SERVICE_KEY", "")
            if not key:
                logger.warning("SUPABASE_SERVICE_KEY not set")
                return None
            _supabase_client = create_client(url, key)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            return None
    return _supabase_client

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

@app.post("/search", response_model=SearchResponse)
@limiter.limit("100/minute")
async def search(request: SearchRequest):
    """
    Main search endpoint.

    Flow: Query → Extract entities → Map to capabilities → Execute SQL → Attach actions
    """
    start = time.time()

    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=503, detail="Database connection not available")

    try:
        from pipeline_v1 import Pipeline

        pipeline = Pipeline(client, request.yacht_id)
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
async def webhook_search(request: Request):
    """
    Webhook endpoint for frontend search requests.

    Accepts frontend payload format with auth and context.
    Extracts yacht_id from auth payload and routes to pipeline.

    ALWAYS returns structured JSON - never raw 500 errors.
    """
    # Generate request_id for tracing
    request_id = str(uuid.uuid4())[:8]

    try:
        body = await request.json()
        query = body.get('query', '')
        logger.info(f"[webhook/search:{request_id}] Received query: '{query}' | payload_keys: {list(body.keys())}")

        # Extract data from frontend format
        auth = body.get('auth', {})
        yacht_id = auth.get('yacht_id')
        limit = body.get('limit', 20)

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
        if not yacht_id:
            logger.warning(f"[webhook/search:{request_id}] Missing yacht_id in auth")
            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "request_id": request_id,
                    "error_code": "MISSING_YACHT_ID",
                    "message": "Missing required field: auth.yacht_id",
                    "results": [],
                    "total_count": 0
                }
            )

        logger.info(f"[webhook/search:{request_id}] yacht_id={yacht_id[:8]}..., query='{query}'")

        # Call main search logic
        search_request = SearchRequest(
            query=query,
            yacht_id=yacht_id,
            limit=limit
        )

        result = await search(search_request)

        # Frontend expects newline-delimited JSON for streaming parser
        # Send as single line with newline terminator
        import json

        response_data = result.model_dump()
        response_data["request_id"] = request_id
        response_data["ok"] = response_data.get("success", False)

        json_str = json.dumps(response_data) + "\n"
        logger.info(f"[webhook/search:{request_id}] Success: {response_data.get('success')}, results: {response_data.get('total_count', 0)}")
        return Response(content=json_str, media_type="application/json")

    except HTTPException as he:
        # Re-raise HTTP exceptions but log them
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


async def validate_jwt_simple(authorization: str = Header(None, alias='Authorization')):
    """
    Simple JWT validation for document access.

    Returns dict with user_id and yacht_id extracted from JWT.
    For now, this is a simplified version - full validation should use middleware.auth
    """
    if not authorization:
        raise HTTPException(401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="Invalid Authorization header format")

    token = authorization.replace("Bearer ", "")

    try:
        import jwt

        # Get JWT secret from environment
        jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "")
        if not jwt_secret:
            logger.warning("SUPABASE_JWT_SECRET not set - JWT validation disabled")
            # In development, extract yacht_id from token without validation
            # WARNING: This is insecure! Only for development.
            payload = jwt.decode(token, options={"verify_signature": False})
        else:
            # Production: Validate JWT signature
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_exp": True}
            )

        user_id = payload.get("sub") or payload.get("user_id")

        # yacht_id might be in user_metadata or directly in payload
        yacht_id = payload.get("yacht_id")
        if not yacht_id:
            user_metadata = payload.get("user_metadata", {})
            yacht_id = user_metadata.get("yacht_id") or user_metadata.get("yachtId")

        if not yacht_id:
            logger.warning(f"No yacht_id found in JWT payload: {list(payload.keys())}")
            raise HTTPException(403, detail="No yacht_id in token")

        return {
            "user_id": user_id,
            "yacht_id": yacht_id,
            "role": payload.get("role", "crew"),
            "email": payload.get("email", ""),
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid JWT: {e}")
        raise HTTPException(401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(401, detail="Authentication failed")


@app.post("/v1/documents/{document_id}/sign")
@limiter.limit("60/minute")
async def sign_document_url(
    document_id: str,
    request: Request,
    auth: dict = Depends(validate_jwt_simple),
    x_yacht_signature: str = Header(None, alias='X-Yacht-Signature')
):
    """
    Generate short-lived signed URL for document access.

    Security (Production-Grade for Yacht Fleet):
    - Validates JWT (user authentication)
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
    ip_address = request.client.host if request.client else 'unknown'

    logger.info(f"[sign_document] user={user_id[:8]}..., yacht={yacht_id[:8]}..., doc={document_id[:8]}..., ip={ip_address}")

    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(503, detail="Database connection not available")

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
    auth: dict = Depends(validate_jwt_simple),
    x_yacht_signature: str = Header(None, alias='X-Yacht-Signature')
):
    """
    Stream document from Supabase Storage.

    Security:
    - Validates JWT
    - Enforces yacht_id isolation
    - Verifies document ownership

    Returns:
    - File bytes with proper Content-Type
    - Content-Disposition header for inline viewing
    """
    user_id = auth['user_id']
    yacht_id = auth['yacht_id']

    logger.info(f"[stream_document] user={user_id[:8]}..., yacht={yacht_id[:8]}..., doc={document_id[:8]}...")

    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(503, detail="Database connection not available")

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
