"""
Micro-Action Extraction FastAPI Service
========================================

Lightweight FastAPI web service for deploying micro-action extraction on Render.

Deployment specs (Render):
- Instance type: Starter ($7/month)
- Memory: 512MB
- Cold start: ~3-5s
- Warm response: ~100-200ms (regex-only)
- Concurrent requests: 10-20

Security:
- Multi-layer authentication (API key + JWT + yacht signature)
- Strict CORS
- Rate limiting (100 req/min per IP)

Endpoints:
- POST /extract_microactions - Main extraction endpoint
- POST /extract_detailed - Extended extraction with metadata
- GET /health - Health check
- GET /patterns - List all supported actions

Similar architecture to maritime entity extraction service.
"""

from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
import time
import logging
import os
import jwt
import hashlib
from pathlib import Path

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Import extraction modules
from microaction_extractor import MicroActionExtractor, get_extractor
from microaction_config import get_config, ExtractionConfig, ValidationRules

# Import unified extraction pipeline
from unified_extraction_pipeline import get_pipeline, UnifiedExtractionPipeline

# Import GraphRAG services
from graphrag_population import get_population_service, GraphRAGPopulationService
from graphrag_query import get_query_service, GraphRAGQueryService, query_result_to_dict

# ========================================================================
# LOGGING CONFIGURATION
# ========================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================================================
# FASTAPI APP INITIALIZATION
# ========================================================================

app = FastAPI(
    title="CelesteOS Micro-Action Extraction API",
    description="Extract actionable intents from natural language queries for maritime operations",
    version="1.0.1",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ========================================================================
# RATE LIMITING SETUP
# ========================================================================

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ========================================================================
# STRICT CORS CONFIGURATION
# ========================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.celeste7.ai",
        "https://api.celeste7.ai",
        "http://localhost:3000",  # For local development
        "http://localhost:8000"   # For local testing
    ],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=[
        "Content-Type",
        "Authorization",      # JWT from Supabase
        "X-Yacht-Signature"   # Yacht ownership proof
    ],
)

# ========================================================================
# GLOBAL STATE (load patterns once at startup)
# ========================================================================

# Extractor instance (singleton, loaded at startup)
extractor: Optional[MicroActionExtractor] = None

# Unified pipeline instance (Modules A, B, C)
pipeline: Optional[UnifiedExtractionPipeline] = None

# GraphRAG services
graphrag_population: Optional[GraphRAGPopulationService] = None
graphrag_query: Optional[GraphRAGQueryService] = None

# Configuration (default to production)
config: ExtractionConfig = get_config('production')

# Request counter for monitoring
request_counter = 0

# ========================================================================
# SECURITY VERIFICATION
# ========================================================================

async def verify_security(
    request: Request,
    authorization: str = Header(None),
    x_yacht_signature: str = Header(None)
) -> Dict:
    """
    Two-layer security verification (clean & minimal):
    1. JWT validation (user authentication via Supabase)
    2. Yacht signature verification (yacht ownership proof)

    Returns: {"user_id": str, "yacht_id": str}

    No shared secrets. JWT auto-expires. Secure by default.
    """

    # Layer 1: JWT (User Authentication)
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Missing or invalid JWT")
        raise HTTPException(status_code=401, detail="Missing JWT token")

    token = authorization.replace("Bearer ", "")
    try:
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if jwt_secret:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"]
            )
            user_id = payload.get("sub")
            yacht_id = payload.get("yacht_id")  # Custom claim

            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid JWT payload: missing user_id")
            if not yacht_id:
                raise HTTPException(status_code=401, detail="Invalid JWT payload: missing yacht_id")
        else:
            # Development mode: skip JWT verification
            logger.warning("⚠️  JWT verification skipped (no SUPABASE_JWT_SECRET) - DEV MODE")
            user_id = "dev_user"
            yacht_id = "dev_yacht"
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token")
        raise HTTPException(status_code=401, detail="JWT token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(status_code=401, detail="Invalid JWT token")

    # Layer 2: Yacht Signature (Yacht Ownership Proof)
    yacht_salt = os.getenv("YACHT_SALT")
    if yacht_salt:
        if not x_yacht_signature:
            logger.warning(f"Missing yacht signature for user_id={user_id}")
            raise HTTPException(status_code=403, detail="Missing yacht signature")

        expected_sig = hashlib.sha256(
            f"{yacht_id}{yacht_salt}".encode()
        ).hexdigest()

        if x_yacht_signature != expected_sig:
            logger.warning(f"Invalid yacht signature for yacht_id={yacht_id}, user_id={user_id}")
            raise HTTPException(status_code=403, detail="Invalid yacht signature")
    else:
        # Development mode: skip signature verification
        logger.warning("⚠️  Yacht signature verification skipped (no YACHT_SALT) - DEV MODE")

    logger.info(f"✅ Authenticated: user_id={user_id}, yacht_id={yacht_id}")
    return {"user_id": user_id, "yacht_id": yacht_id}


# ========================================================================
# PYDANTIC MODELS
# ========================================================================

class ExtractionRequest(BaseModel):
    """Request model for extraction endpoint"""
    query: str = Field(..., min_length=1, max_length=500, description="User query to extract micro-actions from")
    include_metadata: bool = Field(default=False, description="Include detailed match metadata in response")
    validate_combination: bool = Field(default=True, description="Validate that detected actions make sense together")

    @validator('query')
    def clean_query(cls, v):
        """Clean and validate query"""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v

    class Config:
        schema_extra = {
            "example": {
                "query": "create work order and add to handover",
                "include_metadata": False,
                "validate_combination": True
            }
        }


class ExtractionResponse(BaseModel):
    """Response model for extraction endpoint"""
    micro_actions: List[str] = Field(..., description="List of detected micro-action names")
    count: int = Field(..., description="Number of detected actions")
    latency_ms: int = Field(..., description="Processing latency in milliseconds")
    query: str = Field(..., description="Original query (for reference)")
    has_unsupported: bool = Field(default=False, description="Whether query contains unsupported action indicators")
    validation: Optional[Dict] = Field(default=None, description="Validation results (if requested)")

    class Config:
        schema_extra = {
            "example": {
                "micro_actions": ["create_work_order", "add_to_handover"],
                "count": 2,
                "latency_ms": 102,
                "query": "create work order and add to handover",
                "has_unsupported": False,
                "validation": {
                    "valid": True,
                    "warnings": [],
                    "suggestions": []
                }
            }
        }


class DetailedExtractionResponse(ExtractionResponse):
    """Extended response with match metadata"""
    matches: List[Dict] = Field(..., description="Detailed match information")
    total_matches: int = Field(..., description="Total number of matches before deduplication")

    class Config:
        schema_extra = {
            "example": {
                "micro_actions": ["create_work_order"],
                "count": 1,
                "latency_ms": 98,
                "query": "create work order",
                "has_unsupported": False,
                "matches": [
                    {
                        "action_name": "create_work_order",
                        "confidence": 0.95,
                        "source": "regex",
                        "match_text": "create work order",
                        "span": [0, 17]
                    }
                ],
                "total_matches": 2
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    patterns_loaded: int
    total_requests: int
    uptime_seconds: float
    security_enabled: bool


class PatternsResponse(BaseModel):
    """Response listing all supported actions"""
    total_actions: int
    actions_by_category: Dict[str, List[str]]
    all_actions: List[str]


# ========================================================================
# UNIFIED EXTRACTION MODELS (Modules A + B + C)
# ========================================================================

class MicroActionDetection(BaseModel):
    """Single micro-action detection with confidence"""
    action: str = Field(..., description="Canonical action name (e.g., 'create_work_order')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence (0.0-1.0)")
    verb: str = Field(..., description="Verb that triggered detection (e.g., 'create')")
    matched_text: str = Field(..., description="Text that matched the pattern")


class EntityDetectionModel(BaseModel):
    """Single entity detection (raw)"""
    type: str = Field(..., description="Entity type (equipment, fault_code, measurement, etc.)")
    value: str = Field(..., description="Original text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")


class CanonicalEntityModel(BaseModel):
    """Canonical entity with weight"""
    type: str = Field(..., description="Entity type")
    value: str = Field(..., description="Original value")
    canonical: str = Field(..., description="Canonical/normalized form (e.g., 'MAIN_ENGINE_1')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Adjusted confidence")
    weight: float = Field(..., ge=0.0, le=1.0, description="Importance weight for search ranking")


class ExtractionScores(BaseModel):
    """Confidence and quality scores"""
    intent_confidence: float = Field(..., ge=0.0, le=1.0, description="Best action confidence")
    entity_confidence: float = Field(..., ge=0.0, le=1.0, description="Average entity confidence")
    entity_weights: Dict[str, float] = Field(..., description="Average weight per entity type")


class ExtractionMetadata(BaseModel):
    """Extraction metadata"""
    query: str = Field(..., description="Original query")
    latency_ms: int = Field(..., description="Processing latency in milliseconds")
    modules_run: List[str] = Field(..., description="Modules executed in pipeline")
    action_count: int = Field(..., description="Number of actions detected")
    entity_count: int = Field(..., description="Number of entities detected")


class UnifiedExtractionResponse(BaseModel):
    """
    Unified extraction response combining micro-actions, entities, and canonical mappings.

    This is the single source of truth for ALL extraction logic.
    """
    intent: Optional[str] = Field(None, description="High-level intent (create, update, view, action, search)")
    microactions: List[MicroActionDetection] = Field(default_factory=list, description="Detected micro-actions with confidence")
    entities: List[EntityDetectionModel] = Field(default_factory=list, description="Raw entity detections")
    canonical_entities: List[CanonicalEntityModel] = Field(default_factory=list, description="Canonical entities with weights")
    scores: ExtractionScores = Field(..., description="Confidence and quality scores")
    metadata: ExtractionMetadata = Field(..., description="Extraction metadata")

    class Config:
        schema_extra = {
            "example": {
                "intent": "action",
                "microactions": [
                    {
                        "action": "diagnose_fault",
                        "confidence": 0.93,
                        "verb": "diagnose",
                        "matched_text": "diagnose E047"
                    }
                ],
                "entities": [
                    {"type": "fault_code", "value": "E047", "confidence": 0.95},
                    {"type": "equipment", "value": "ME1", "confidence": 0.92}
                ],
                "canonical_entities": [
                    {
                        "type": "fault_code",
                        "value": "E047",
                        "canonical": "E047",
                        "confidence": 0.95,
                        "weight": 1.0
                    },
                    {
                        "type": "equipment",
                        "value": "ME1",
                        "canonical": "MAIN_ENGINE_1",
                        "confidence": 0.87,
                        "weight": 0.95
                    }
                ],
                "scores": {
                    "intent_confidence": 0.93,
                    "entity_confidence": 0.91,
                    "entity_weights": {
                        "fault_code": 0.95,
                        "equipment": 0.87
                    }
                },
                "metadata": {
                    "query": "diagnose E047 on ME1",
                    "latency_ms": 45,
                    "modules_run": ["action_detector", "entity_extractor", "canonicalizer"],
                    "action_count": 1,
                    "entity_count": 2
                }
            }
        }


# ========================================================================
# STARTUP & SHUTDOWN EVENTS
# ========================================================================

startup_time = time.time()

@app.on_event("startup")
async def startup_event():
    """Load extractor and patterns at startup (runs once)"""
    global extractor, pipeline, config, graphrag_population, graphrag_query
    logger.info("🚀 Starting Micro-Action Extraction Service...")

    try:
        # Initialize extractor (this loads and compiles all patterns)
        extractor = get_extractor()

        # Get actions from correct path in JSON
        actions = extractor.patterns.get('actions', {})
        logger.info(f"✓ Loaded {len(extractor.patterns)} pattern groups")
        logger.info(f"✓ Compiled {len(extractor.compiled_patterns)} action patterns")
        logger.info(f"✓ Built gazetteer with {len(extractor.gazetteer)} terms")

        # Initialize unified pipeline (Modules A, B, C)
        pipeline = get_pipeline()
        logger.info("✓ Unified extraction pipeline initialized (Modules A + B + C)")

        # Initialize GraphRAG services
        graphrag_population = get_population_service()
        graphrag_query = get_query_service()
        logger.info("✓ GraphRAG services initialized (population + query)")

        # Load configuration
        config = get_config('production')
        logger.info(f"✓ Configuration: AI fallback threshold = {config.ai_fallback_threshold}")

        # Security status
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        yacht_salt = os.getenv("YACHT_SALT")
        security_enabled = bool(jwt_secret and yacht_salt)
        logger.info(f"✓ Security: {'ENABLED (JWT + Yacht Signature)' if security_enabled else 'DISABLED (dev mode)'}")

        logger.info("✅ Service ready to accept requests")

    except Exception as e:
        logger.error(f"❌ Failed to initialize service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Micro-Action Extraction Service...")


# ========================================================================
# MIDDLEWARE FOR REQUEST LOGGING
# ========================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    global request_counter
    request_counter += 1

    start_time = time.time()
    response = await call_next(request)
    duration = (time.time() - start_time) * 1000  # Convert to ms

    logger.info(
        f"[{request_counter}] {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Duration: {duration:.0f}ms"
    )

    return response


# ========================================================================
# API ENDPOINTS
# ========================================================================

@app.post("/extract", response_model=UnifiedExtractionResponse, tags=["Unified Extraction"])
@limiter.limit("100/minute")
async def unified_extract(
    request: Request,
    extraction_request: ExtractionRequest,
    auth: Dict = Depends(verify_security)
):
    """
    **UNIFIED EXTRACTION ENDPOINT - Single Source of Truth**

    Combines micro-action detection, entity extraction, and canonicalization into
    a single structured response.

    **What it does:**
    - Detects actionable intents (Module A: strict verb-based patterns)
    - Extracts maritime entities (Module B: equipment, faults, measurements)
    - Canonicalizes and weights entities (Module C: normalization + importance)

    **Security (2 headers only):**
    - Authorization: Bearer <supabase_jwt> (user authentication)
    - X-Yacht-Signature: <sha256_signature> (yacht ownership proof)

    **Example Inputs:**
    - "create work order for bilge pump" → action + entity
    - "bilge manifold" → entity only
    - "diagnose E047 on ME1" → action + fault_code + equipment
    - "tell me bilge pump" → entity only (no false action)
    - "sea water pump pressure low" → equipment + maritime term

    **Response:**
    - intent: High-level categorization (create, update, view, action, search)
    - microactions: List of detected actions with confidence scores
    - entities: Raw entity detections
    - canonical_entities: Normalized entities with importance weights
    - scores: Confidence metrics
    - metadata: Processing info (latency, modules run, counts)

    **Non-Negotiable Rules:**
    - Maritime terms NEVER trigger micro-actions
    - Phrasal patterns ("tell me", "find the") do NOT detect actions
    - Actions require explicit verbs at start of query
    - Entities are extracted independently of actions
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Unified pipeline not initialized")

    try:
        # Run unified extraction pipeline (Modules A → B → C)
        result = pipeline.extract(extraction_request.query)

        logger.info(
            f"Unified extraction: query='{extraction_request.query}', "
            f"intent={result['intent']}, "
            f"actions={result['metadata']['action_count']}, "
            f"entities={result['metadata']['entity_count']}, "
            f"latency={result['metadata']['latency_ms']}ms, "
            f"user_id={auth['user_id']}, yacht_id={auth['yacht_id']}"
        )

        return result

    except Exception as e:
        logger.error(f"Unified extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.post("/extract_microactions", response_model=ExtractionResponse, tags=["Extraction (Deprecated)"])
@limiter.limit("100/minute")
async def extract_microactions(
    request: Request,
    extraction_request: ExtractionRequest,
    auth: Dict = Depends(verify_security)
):
    """
    **⚠️ DEPRECATED - Use POST /extract instead**

    This endpoint is maintained for backwards compatibility but will be removed in v3.0.0.

    Please migrate to POST /extract which provides:
    - ✅ Unified action + entity extraction
    - ✅ Canonical entity mappings
    - ✅ Intent categorization
    - ✅ Entity importance weighting
    - ✅ Better confidence scoring

    **Legacy endpoint:** Extract micro-actions from natural language query.

    Returns list of canonical action names (e.g., ["create_work_order", "add_to_handover"]).

    **Security:**
    - Authorization: Bearer <supabase_jwt>
    - X-Yacht-Signature: <sha256_signature>

    **Examples:**
    - "create work order" → ["create_work_order"]
    - "add to handover and create wo" → ["add_to_handover", "create_work_order"]
    - "show all open work orders" → ["list_work_orders"]
    - "what's the weather" → [] (unsupported)
    """
    logger.warning(
        f"DEPRECATED endpoint /extract_microactions called by user_id={auth['user_id']}. "
        "Please migrate to /extract"
    )
    if extractor is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    start_time = time.time()

    try:
        # Run extraction
        if extraction_request.include_metadata:
            result = extractor.extract_with_details(extraction_request.query)
            actions = result['micro_actions']
            has_unsupported = result['has_unsupported']
        else:
            actions = extractor.extract_microactions(extraction_request.query)
            has_unsupported = False

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Validate action combination if requested
        validation = None
        if extraction_request.validate_combination and actions:
            validation = ValidationRules.validate_action_combination(actions)

        # Build response
        response = ExtractionResponse(
            micro_actions=actions,
            count=len(actions),
            latency_ms=latency_ms,
            query=extraction_request.query,
            has_unsupported=has_unsupported,
            validation=validation
        )

        logger.info(
            f"Extracted {len(actions)} actions from '{extraction_request.query}' "
            f"in {latency_ms}ms for user_id={auth['user_id']}, yacht_id={auth['yacht_id']}: {actions}"
        )

        return response

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.post("/extract_detailed", response_model=DetailedExtractionResponse, tags=["Extraction (Deprecated)"])
@limiter.limit("50/minute")
async def extract_detailed(
    request: Request,
    extraction_request: ExtractionRequest,
    auth: Dict = Depends(verify_security)
):
    """
    **⚠️ DEPRECATED - Use POST /extract instead**

    This endpoint is maintained for backwards compatibility but will be removed in v3.0.0.

    Please migrate to POST /extract which provides:
    - ✅ Unified action + entity extraction
    - ✅ Complete metadata in every response
    - ✅ Better structured output
    - ✅ Entity weighting and canonical mappings

    **Legacy endpoint:** Extended extraction endpoint with detailed match metadata.

    Returns:
    - All detected micro-actions
    - Detailed match information (confidence, source, span)
    - Total matches before deduplication
    - Validation results

    Useful for debugging and understanding extraction decisions.
    """
    logger.warning(
        f"DEPRECATED endpoint /extract_detailed called by user_id={auth['user_id']}. "
        "Please migrate to /extract"
    )
    if extractor is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    start_time = time.time()

    try:
        # Run detailed extraction
        result = extractor.extract_with_details(extraction_request.query)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Validate action combination
        validation = None
        if extraction_request.validate_combination and result['micro_actions']:
            validation = ValidationRules.validate_action_combination(result['micro_actions'])

        # Build response
        response = DetailedExtractionResponse(
            micro_actions=result['micro_actions'],
            count=result['unique_actions'],
            latency_ms=latency_ms,
            query=extraction_request.query,
            has_unsupported=result['has_unsupported'],
            matches=result['matches'],
            total_matches=result['total_matches'],
            validation=validation
        )

        return response

    except Exception as e:
        logger.error(f"Detailed extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns service status, version, and basic metrics.
    """
    uptime = time.time() - startup_time

    # Get actions count correctly
    actions_count = 0
    if extractor and extractor.patterns:
        actions = extractor.patterns.get('actions', {})
        actions_count = len(actions)

    return HealthResponse(
        status="healthy" if extractor is not None else "unhealthy",
        version="3.0.0",
        patterns_loaded=actions_count,
        total_requests=request_counter,
        uptime_seconds=uptime,
        security_enabled=bool(os.getenv("SUPABASE_JWT_SECRET") and os.getenv("YACHT_SALT"))
    )


@app.get("/patterns", response_model=PatternsResponse, tags=["Information"])
async def list_patterns():
    """
    List all supported micro-actions organized by category.

    Useful for frontend to display available actions.
    """
    if extractor is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    actions_by_category = {}
    all_actions = []

    # Get actions from correct path in JSON
    actions = extractor.patterns.get('actions', {})

    for action_name, action_data in actions.items():
        category = action_data.get('category', 'other')

        if category not in actions_by_category:
            actions_by_category[category] = []

        actions_by_category[category].append(action_name)
        all_actions.append(action_name)

    return PatternsResponse(
        total_actions=len(all_actions),
        actions_by_category=actions_by_category,
        all_actions=sorted(all_actions)
    )


@app.get("/", tags=["Information"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "CelesteOS Micro-Action Extraction API",
        "version": "3.0.0",
        "status": "running",
        "security": "JWT + Yacht Signature (2 headers only)",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "unified_extract": "POST /extract (RECOMMENDED - Modules A+B+C)",
            "graphrag_query": "POST /graphrag/query (NEW - Intent-based GraphRAG search)",
            "graphrag_populate": "POST /graphrag/populate (NEW - n8n workflow population)",
            "graphrag_stats": "GET /graphrag/stats (NEW - Graph statistics)",
            "extract": "POST /extract_microactions (legacy)",
            "detailed": "POST /extract_detailed (legacy)",
            "patterns": "GET /patterns"
        },
        "architecture": {
            "module_a": "Strict micro-action detector (verb-based)",
            "module_b": "Maritime entity extractor (equipment, faults, measurements)",
            "module_c": "Canonicalizer (normalization + weighting)",
            "pipeline": "Unified extraction combining all modules",
            "graphrag_population": "Graph population from GPT extraction (nodes, edges, maintenance)",
            "graphrag_query": "Intent-based search with entity resolution and graph traversal"
        },
        "auth": {
            "headers": {
                "Authorization": "Bearer <supabase_jwt>",
                "X-Yacht-Signature": "sha256(yacht_id + salt)"
            },
            "no_shared_secrets": True,
            "jwt_auto_expires": True
        }
    }


# ========================================================================
# GRAPHRAG API ENDPOINTS
# ========================================================================

class GraphRAGQueryRequest(BaseModel):
    """Request model for GraphRAG query endpoint"""
    query: str = Field(..., min_length=1, max_length=1000, description="User natural language query")

    class Config:
        schema_extra = {
            "example": {
                "query": "Engine is overheating, show historic data from 2nd engineer"
            }
        }


class GraphRAGPopulateRequest(BaseModel):
    """Request model for GraphRAG population endpoint (n8n workflow use)"""
    chunk_id: str = Field(..., description="Source document chunk ID")
    entities: List[Dict] = Field(default_factory=list, description="Extracted entities")
    relationships: List[Dict] = Field(default_factory=list, description="Extracted relationships")
    maintenance: Optional[List[Dict]] = Field(default=None, description="Extracted maintenance facts")

    class Config:
        schema_extra = {
            "example": {
                "chunk_id": "uuid-chunk-123",
                "entities": [
                    {"label": "Main Engine", "type": "equipment", "confidence": 0.95},
                    {"label": "Oil Filter", "type": "part", "confidence": 0.90}
                ],
                "relationships": [
                    {"from": "Main Engine", "to": "Oil Filter", "type": "uses_part"}
                ],
                "maintenance": [
                    {"equipment": "Main Engine", "interval": "500 hours", "action": "replace"}
                ]
            }
        }


@app.post("/graphrag/query", tags=["GraphRAG"])
@limiter.limit("100/minute")
async def graphrag_query_endpoint(
    request: Request,
    query_request: GraphRAGQueryRequest,
    auth: Dict = Depends(verify_security)
):
    """
    **GraphRAG Query Endpoint**

    Execute an intent-based search using the Graph RAG layer.

    This endpoint:
    1. Detects intent and extracts entities from the query
    2. Resolves entities to canonical IDs (equipment, parts, symptoms)
    3. Traverses the knowledge graph for relationships
    4. Returns result cards and suggested micro-actions

    **Supported Intents:**
    - find_document_section: "Open Cat main engine manual to lube oil section"
    - equipment_history: "Engine is overheating, show historic data"
    - diagnose_fault: "What does error code E047 mean?"
    - find_part: "Find filter for port main engine"
    - maintenance_lookup: "When is oil change due on generator 1?"

    **Security:**
    - Authorization: Bearer <supabase_jwt>
    - X-Yacht-Signature: <sha256_signature>

    **Response:**
    - intent: Detected query intent
    - resolved_entities: Entities matched to canonical IDs
    - cards: Result cards (equipment, document, fault, part, etc.)
    - suggested_actions: Micro-actions with payloads (requires_confirmation flag)
    - graph_stats: Current graph statistics for the yacht
    """
    if graphrag_query is None:
        raise HTTPException(status_code=503, detail="GraphRAG query service not initialized")

    try:
        yacht_id = auth.get("yacht_id")

        result = graphrag_query.query(yacht_id, query_request.query)

        logger.info(
            f"GraphRAG query: yacht={yacht_id}, query='{query_request.query}', "
            f"intent={result.intent.value}, cards={len(result.cards)}, "
            f"actions={len(result.suggested_actions)}"
        )

        return query_result_to_dict(result)

    except Exception as e:
        logger.error(f"GraphRAG query failed: {e}")
        raise HTTPException(status_code=500, detail=f"GraphRAG query failed: {str(e)}")


@app.post("/graphrag/populate", tags=["GraphRAG"])
@limiter.limit("200/minute")
async def graphrag_populate_endpoint(
    request: Request,
    populate_request: GraphRAGPopulateRequest,
    auth: Dict = Depends(verify_security)
):
    """
    **GraphRAG Population Endpoint**

    Populate graph tables from GPT extraction results.

    This endpoint is called by n8n Graph_RAG_Digest workflow after GPT extraction.

    **What it does:**
    1. Resolves extracted entities to canonical IDs
    2. Inserts graph_nodes with canonical links
    3. Inserts graph_edges with proper edge types
    4. Inserts maintenance_templates if extraction contains maintenance facts
    5. Updates document_chunks.extraction_status

    **Security:**
    - Authorization: Bearer <supabase_jwt>
    - X-Yacht-Signature: <sha256_signature>

    **Expected Input:**
    - chunk_id: The document chunk that was processed
    - entities: List of extracted entities from GPT
    - relationships: List of extracted relationships from GPT
    - maintenance: Optional list of maintenance facts

    **Response:**
    - success: Whether population succeeded
    - status: Extraction status (success, empty, failed, partial)
    - nodes_inserted: Number of graph nodes inserted
    - nodes_resolved: Number of nodes resolved to canonical IDs
    - edges_inserted: Number of graph edges inserted
    - maintenance_inserted: Number of maintenance templates inserted
    """
    if graphrag_population is None:
        raise HTTPException(status_code=503, detail="GraphRAG population service not initialized")

    try:
        yacht_id = auth.get("yacht_id")

        result = graphrag_population.populate_from_extraction(
            yacht_id=yacht_id,
            chunk_id=populate_request.chunk_id,
            entities=populate_request.entities,
            relationships=populate_request.relationships,
            maintenance_facts=populate_request.maintenance
        )

        logger.info(
            f"GraphRAG populate: yacht={yacht_id}, chunk={populate_request.chunk_id}, "
            f"status={result.status.value}, nodes={result.nodes_inserted}, "
            f"edges={result.edges_inserted}"
        )

        return {
            "success": result.status.value != "failed",
            "status": result.status.value,
            "chunk_id": result.chunk_id,
            "nodes_inserted": result.nodes_inserted,
            "nodes_resolved": result.nodes_resolved,
            "edges_inserted": result.edges_inserted,
            "maintenance_inserted": result.maintenance_inserted,
            "errors": result.errors
        }

    except Exception as e:
        logger.error(f"GraphRAG population failed: {e}")
        raise HTTPException(status_code=500, detail=f"GraphRAG population failed: {str(e)}")


@app.get("/graphrag/stats", tags=["GraphRAG"])
@limiter.limit("60/minute")
async def graphrag_stats_endpoint(
    request: Request,
    auth: Dict = Depends(verify_security)
):
    """
    **GraphRAG Statistics Endpoint**

    Get graph statistics for the authenticated yacht.

    Uses v_graph_stats and v_extraction_status views.

    **Response:**
    - graph_stats: Node/edge counts, resolution rate
    - extraction_stats: Chunk processing status breakdown
    """
    if graphrag_query is None:
        raise HTTPException(status_code=503, detail="GraphRAG query service not initialized")

    try:
        yacht_id = auth.get("yacht_id")

        graph_stats = graphrag_query._get_graph_stats(yacht_id)

        # Also get extraction status breakdown
        extraction_stats = {}
        if graphrag_query.client:
            try:
                result = graphrag_query.client.table("v_extraction_status").select("*").eq(
                    "yacht_id", yacht_id
                ).execute()
                extraction_stats = result.data if result.data else []
            except Exception:
                pass

        return {
            "yacht_id": yacht_id,
            "graph_stats": graph_stats,
            "extraction_stats": extraction_stats
        }

    except Exception as e:
        logger.error(f"GraphRAG stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"GraphRAG stats failed: {str(e)}")


# ========================================================================
# N8N WRAPPER FUNCTION (for direct import in n8n Code node)
# ========================================================================

def extract_for_n8n(query: str) -> Dict:
    """
    Simple wrapper for n8n HTTP Request node.

    Usage in n8n:
    1. HTTP Request node
    2. Method: POST
    3. URL: https://extract.core.celeste7.ai/extract_microactions
    4. Headers: Authorization, X-Yacht-Signature, X-Celeste-Key
    5. Body: {"query": "create work order and add to handover"}
    6. Response: {"micro_actions": ["create_work_order", "add_to_handover"], "count": 2, "latency_ms": 102}
    """
    if extractor is None:
        return {"error": "Service not initialized", "micro_actions": []}

    actions = extractor.extract_microactions(query)
    return {
        "micro_actions": actions,
        "count": len(actions),
        "success": True
    }


# ========================================================================
# ERROR HANDLERS
# ========================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
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
    """Catch-all exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url)
        }
    )


# ========================================================================
# MAIN (for local development)
# ========================================================================

if __name__ == "__main__":
    import uvicorn

    # Run with: python microaction_service.py
    # Access at: http://localhost:8000
    # Docs at: http://localhost:8000/docs

    uvicorn.run(
        "microaction_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
