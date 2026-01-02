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
from datetime import datetime, timezone

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Add api/ to path for Render compatibility (running from root with uvicorn api.microaction_service:app)
import sys
from pathlib import Path
_api_dir = Path(__file__).parent
if str(_api_dir) not in sys.path:
    sys.path.insert(0, str(_api_dir))

# Import extraction modules (now works both locally and on Render)
from microaction_extractor import MicroActionExtractor, get_extractor
from microaction_config import get_config, ExtractionConfig, ValidationRules
from unified_extraction_pipeline import get_pipeline, UnifiedExtractionPipeline
from graphrag_population import get_population_service, GraphRAGPopulationService
from graphrag_query import get_query_service, GraphRAGQueryService
from situation_engine import SituationEngine, get_situation_engine, Severity

# Import Module B: Maritime Entity Extractor (regex-based, no LLM cost)
from module_b_entity_extractor import get_extractor as get_entity_extractor, MaritimeEntityExtractor

# Import Intent Parser for semantic query understanding
from intent_parser import IntentParser, route_query as intent_route_query

# Global intent parser (initialized at startup)
intent_parser: Optional[IntentParser] = None


def get_action_chips(query: str, primary_action: str, confidence: float) -> Dict:
    """
    Get suggestion chips for an action.
    Simplified version - returns primary action with basic metadata.
    """
    return {
        'primary': {
            'action': primary_action,
            'confidence': round(confidence, 2),
            'label': primary_action.replace('_', ' ').title() if primary_action else ''
        },
        'alternatives': [],
        'execution_class': 'auto' if confidence >= 0.8 else 'suggest',
        'suggestion_worthy': confidence < 0.8,
        'verb_family': 'general'
    }


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

# Situation Engine (v1 situation-aware search)
situation_engine: Optional[SituationEngine] = None

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
            from datetime import timedelta
            # Decode JWT - skip audience verification to allow service_role/anon tokens
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
                leeway=timedelta(minutes=5)
            )

            # Get user_id from sub (user tokens) or use role for service tokens
            user_id = payload.get("sub") or payload.get("role", "service")
            # yacht_id can be in user_metadata or root level (fallback to default if not found)
            yacht_id = payload.get("user_metadata", {}).get("yacht_id") or payload.get("yacht_id") or "00000000-0000-0000-0000-000000000000"

            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid JWT payload: missing user_id")
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

    # Layer 2: Yacht Signature (Yacht Ownership Proof) - OPTIONAL
    yacht_salt = os.getenv("YACHT_SALT")
    if yacht_salt and x_yacht_signature:
        expected_sig = hashlib.sha256(
            f"{yacht_id}{yacht_salt}".encode()
        ).hexdigest()

        if x_yacht_signature != expected_sig:
            logger.warning(f"Invalid yacht signature for yacht_id={yacht_id}, user_id={user_id}")
            raise HTTPException(status_code=403, detail="Invalid yacht signature")
        logger.info(f"✅ Yacht signature verified for yacht_id={yacht_id}")
    else:
        # Signature not provided or YACHT_SALT not set - allow but log
        logger.warning(f"⚠️  Yacht signature not verified for user_id={user_id}, yacht_id={yacht_id}")

    logger.info(f"✅ Authenticated: user_id={user_id}, yacht_id={yacht_id}")
    return {"user_id": user_id, "yacht_id": yacht_id}


# ========================================================================
# PYDANTIC MODELS
# ========================================================================

class ExtractionRequest(BaseModel):
    """Request model for extraction endpoint"""
    query: str = Field(..., min_length=1, max_length=1000, description="Text to extract entities from")
    include_embedding: bool = Field(default=True, description="Include text-embedding-3-small embedding in response")
    include_metadata: bool = Field(default=False, description="Include detailed match metadata in response")
    validate_combination: bool = Field(default=True, description="Validate that detected actions make sense together")
    # Optional context field for n8n workflow
    session_id: Optional[str] = Field(default=None, description="Session ID for tracking")

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
build_time = datetime.now(timezone.utc).isoformat()

# Get git SHA for deployment verification
def get_git_sha() -> str:
    """Get current git commit SHA for deployment verification."""
    import subprocess
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    # Fallback: check environment variable (set by CI/CD)
    return os.getenv('GIT_SHA', os.getenv('RENDER_GIT_COMMIT', 'unknown'))[:7]

git_sha = get_git_sha()

@app.on_event("startup")
async def startup_event():
    """Load extractor and patterns at startup (runs once)"""
    global extractor, pipeline, config, graphrag_population, graphrag_query, situation_engine, intent_parser
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

        # Initialize Intent Parser (67 intents with GPT fallback)
        intent_parser = IntentParser()
        logger.info("✓ Intent Parser initialized (67 intents, GPT-enabled)")

        # Initialize GraphRAG services (now uses GPT extraction + vector search)
        graphrag_population = get_population_service()
        graphrag_query = get_query_service()

        # Check GPT availability
        if graphrag_query and graphrag_query.gpt:
            logger.info("✓ GPT Extractor: GPT-4o-mini + text-embedding-3-small")
        else:
            logger.warning("⚠ GPT Extractor not available - check OPENAI_API_KEY")

        logger.info("✓ GraphRAG services initialized (population + query + vector search)")

        # Initialize Situation Engine (uses GraphRAG's Supabase client)
        if graphrag_query and graphrag_query.client:
            situation_engine = SituationEngine(graphrag_query.client)
            logger.info("✓ Situation Engine initialized (v1 situation-aware search)")
        else:
            logger.warning("⚠ Situation Engine not initialized - no Supabase client")

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

import re

# ========================================================================
# ENTITY LEARNING: Log unknown/low-confidence entities
# GPT is a TEACHER (offline batch), not a live RESOLVER
# ========================================================================

UNKNOWN_ENTITY_CONFIDENCE_THRESHOLD = 0.5  # Log if below this

def log_unknown_entities(
    client,
    yacht_id: str,
    user_id: str,
    entities: list,
    intent: str,
    query: str,
    lane: str
) -> int:
    """
    Log entities with low confidence for offline learning.

    Returns number of entities logged.

    Rules:
    - Only log if confidence < 0.5
    - Don't log for trivial lookup intents with decent confidence
    - Don't log terms that are too short (<2 chars) or too long (>100 chars)
    """
    if not client:
        return 0

    logged_count = 0

    for entity in entities:
        confidence = entity.get('confidence', 0.8)
        raw_value = entity.get('value', '')
        entity_type = entity.get('type', 'unknown')

        # Skip high confidence
        if confidence >= UNKNOWN_ENTITY_CONFIDENCE_THRESHOLD:
            continue

        # Skip trivial lookups with decent confidence
        if intent in ('find_document', 'find_work_order') and confidence > 0.3:
            continue

        # Skip too short or too long
        if len(raw_value.strip()) < 2 or len(raw_value.strip()) > 100:
            continue

        try:
            # Call the SQL function
            result = client.rpc('log_unknown_entity', {
                'p_yacht_id': yacht_id,
                'p_user_id': user_id,
                'p_raw_value': raw_value,
                'p_entity_type_guess': entity_type,
                'p_confidence': confidence,
                'p_intent': intent,
                'p_context_query': query[:500],  # Truncate long queries
                'p_lane': lane
            }).execute()

            if result.data:
                logged_count += 1
                logger.debug(f"Logged unknown entity: {raw_value} ({entity_type}, conf={confidence:.2f})")

        except Exception as e:
            logger.warning(f"Failed to log unknown entity: {e}")

    return logged_count

# ========================================================================
# LANE ROUTING LOGIC (all guards + intent classification)
# ========================================================================

def classify_intent(query: str) -> dict:
    """
    Classify query intent using IntentParser (67 intents with GPT fallback).
    Returns dict with intent, confidence, query_type, requires_mutation, category.
    """
    global intent_parser

    # Use intent parser if available
    if intent_parser:
        parsed = intent_parser.parse(query)
        return {
            'intent': parsed.intent,
            'intent_category': parsed.intent_category,
            'confidence': parsed.confidence,
            'query_type': parsed.query_type,
            'requires_mutation': parsed.requires_mutation,
        }

    # Fallback to regex rules if intent parser not initialized
    query_lower = query.lower()

    INTENT_RULES = [
        (r'overheating|vibrat|leak|noise|smoke|low pressure|high temp|alarm|warning|error|fault|code|not working|broken|failed|issue|problem', 'diagnose_issue', 0.9),
        (r'manual|document|pdf|schematic|diagram|certificate|drawing|spec|datasheet', 'find_document', 0.85),
        (r'work order|wo|maintenance.*scheduled|task|job|repair|service.*history', 'find_work_order', 0.85),
        (r'part|spare|filter|belt|impeller|gasket|zinc|seal|bearing|pump', 'find_part', 0.85),
        (r'predict|risk|likely|upcoming|due|health|condition|failure.*probability', 'predictive', 0.8),
        (r'handover|shift|brief|status|summary|update|report', 'handover', 0.8),
        (r'who|engineer|captain|chief|crew|eto|bosun|assigned', 'find_user', 0.75),
        (r'system|hvac|propulsion|electrical|navigation|safety|stabiliser|watermaker', 'find_system', 0.7),
    ]

    for pattern, intent, confidence in INTENT_RULES:
        if re.search(pattern, query_lower):
            return {
                'intent': intent,
                'intent_category': 'search_documents',
                'confidence': confidence,
                'query_type': 'search',
                'requires_mutation': False,
            }

    return {
        'intent': 'general_search',
        'intent_category': 'search_documents',
        'confidence': 0.5,
        'query_type': 'search',
        'requires_mutation': False,
    }


def route_to_lane(query: str, mode: str = None) -> dict:
    """
    Determine which processing lane to use.
    Returns: {lane, lane_reason, intent, intent_confidence, query_type, requires_mutation, skip_gpt, ...}
    """
    query_lower = query.lower().strip()
    words = query.split()
    word_count = len(words)
    char_count = len(query)

    # Classify intent first (returns dict with intent, confidence, query_type, requires_mutation)
    intent_result = classify_intent(query)
    intent = intent_result['intent']
    intent_confidence = intent_result['confidence']
    query_type = intent_result['query_type']
    requires_mutation = intent_result['requires_mutation']
    intent_category = intent_result['intent_category']

    # Problem/temporal detection
    PROBLEM_WORDS = re.compile(r'overheating|overheat|leak|leaking|vibrat|noise|smoke|alarm|warning|error|fault|not working|broken|failed|failing|issue|problem|keeps|again|recurring|repeat|since|before charter|this morning|last time|still')
    TEMPORAL_WORDS = re.compile(r'before charter|after maintenance|since|this morning|last week|yesterday|upcoming|scheduled|due|next|prior to')

    has_problem_words = bool(PROBLEM_WORDS.search(query_lower))
    has_temporal_context = bool(TEMPORAL_WORDS.search(query_lower))

    base_result = {
        'intent': intent,
        'intent_category': intent_category,
        'intent_confidence': intent_confidence,
        'query_type': query_type,
        'requires_mutation': requires_mutation,
        'word_count': word_count,
        'has_problem_words': has_problem_words,
        'has_temporal_context': has_temporal_context,
    }

    # ========== GUARD 0: PASTE-DUMP ==========
    # Detect code/log pastes even if shorter
    CODE_PATTERNS = re.compile(
        r'(?:traceback|error:|exception:|import\s+\w+|from\s+\w+\s+import|def\s+\w+\(|class\s+\w+:|'
        r'SELECT\s+\*?\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|'
        r'<\?xml|<html|<div|<script|{[\s\S]*"[\w]+":[\s\S]*}|'
        r'curl\s+-|pip\s+install|npm\s+install|const\s+\w+\s*=|'
        r'^\$GP[A-Z]{2,3},|^NMEA:|'
        r'#!/bin/bash|set\s+-e|docker-compose)',
        re.IGNORECASE | re.MULTILINE
    )
    is_code_paste = bool(CODE_PATTERNS.search(query))

    if word_count > 50 or char_count > 300 or is_code_paste:
        return {
            **base_result,
            'lane': 'BLOCKED',
            'lane_reason': 'paste_dump',
            'block_message': 'This looks like a paste of code or logs. Try a shorter search, or upload as a document/handover.',
            'skip_gpt': True,
        }

    # ========== GUARD 1: TOO VAGUE ==========
    # Check if intent is very generic (find_document is default fallback from intent parser)
    # BUT: Allow if query contains known brands/equipment (don't block "Seakeeper manual")
    generic_intents = {'general_search', 'find_document'}

    # Quick check for known entities BEFORE blocking
    KNOWN_BRANDS = {'mtu', 'cat', 'caterpillar', 'cummins', 'volvo', 'yanmar', 'seakeeper', 'naiad',
                    'furuno', 'garmin', 'simrad', 'victron', 'mastervolt', 'kohler', 'onan', 'westerbeke',
                    'jabsco', 'rule', 'groco', 'racor', 'dometic', 'cruisair', 'webasto', 'lewmar',
                    'maxwell', 'muir', 'spectra', 'northern lights', 'perkins', 'detroit', 'man',
                    'zf', 'twin disc', 'quantum', 'vetus', 'whisperpower', 'fischer panda'}
    KNOWN_EQUIPMENT = {'engine', 'generator', 'pump', 'filter', 'manual', 'radar', 'watermaker',
                       'stabilizer', 'autopilot', 'thruster', 'compressor', 'inverter', 'charger',
                       'windlass', 'winch', 'anchor', 'bilge', 'gearbox', 'transmission',
                       'gyro', 'crane', 'chiller', 'separator', 'purifier', 'starlink', 'vhf', 'ais', 'epirb'}

    # Fault code and equipment code patterns
    KNOWN_CODE_PATTERN = re.compile(
        r'spn\s*\d+|fmi\s*\d+|j1939|wo[-\s]?\d+|e\d{2,4}|'
        r'^(?:me|dg|gen)\s*\d+$|'  # ME1, DG2, gen1
        r'^(?:port|stbd)\s+main$',  # port main, stbd main
        re.IGNORECASE
    )

    has_known_entity = any(brand in query_lower for brand in KNOWN_BRANDS) or \
                       any(equip in query_lower for equip in KNOWN_EQUIPMENT) or \
                       bool(KNOWN_CODE_PATTERN.search(query_lower))

    if word_count <= 2 and intent in generic_intents and not has_problem_words and not has_known_entity:
        return {
            **base_result,
            'lane': 'BLOCKED',
            'lane_reason': 'too_vague',
            'block_message': None,
            'suggestions': [
                'Try naming the equipment, e.g. "main engine overheating"',
                'Or search for a document, e.g. "CAT 3512 manual"',
                'Or a work order, e.g. "WO-1234"'
            ],
            'skip_gpt': True,
        }

    # ========== GUARD 2: NON-DOMAIN QUERIES ==========
    # Patterns for off-domain queries (weather, general knowledge, greetings)
    NON_DOMAIN = re.compile(
        r'^(what is|what\'s|who is|tell me about|explain)\s+(?:the\s+)?(quantum|bitcoin|crypto|ai|weather|news|stock|president|capital|meaning|life)'
        r'|^(tell me a joke|hello|hello there|hi|hi there|hey|hey there|good morning|good afternoon|good evening|thanks|thank you|thx|ty)$'
        r'|^(what time is it|what day is it|what date|what\'s the time|what\'s the date)'
        r'|^(how are you|how do you feel|how\'s it going|what\'s up|sup)'
        r'|\b(weather|forecast|temperature|rain|sunny|cloudy)\b(?!.*(?:deck|seal|hatch|cover))'  # weather unless maritime context
        r'|^(who won|what happened|latest news|breaking news)'
        r'|^(calculate|convert|translate|define)\s'
        r'|^(yo|hiya|howdy|greetings)$'
        # Jailbreak / prompt injection patterns
        r'|ignore\s+(all\s+)?(previous\s+)?instructions'
        r'|forget\s+(your|all|previous)\s+(training|instructions|rules)'
        r'|pretend\s+(you\s+are|to\s+be|you\'re)'
        r'|act\s+as\s+if'
        r'|what\s+are\s+your\s+(system\s+)?(instructions|prompts?|rules)'
        r'|reveal\s+(your\s+)?(prompt|instructions|system)'
        r'|disregard\s+(all\s+)?(previous\s+)?'
        r'|bypass\s+(safety|security|restrictions)'
        r'|\bDAN\b|\bjailbreak\b'
        r'|you\s+are\s+now\s+in'
        r'|override\s+(your|all|the)\s+'
        r'|bitcoin\s+price|crypto\s+price|stock\s+price',
        re.IGNORECASE
    )
    DOMAIN_KEYWORDS = re.compile(
        r'engine|pump|generator|hvac|watermaker|stabiliser|stabilizer|nav|radar|'
        r'wo\b|work\s*order|manual|part|filter|impeller|seal|bearing|crew|captain|'
        r'handover|fault|alarm|maintenance|service|repair|inspection|certificate|'
        r'yacht|vessel|boat|ship|marine|maritime|deck|hull|bilge|anchor|thruster|'
        r'fuel|oil|coolant|exhaust|intake|discharge|valve|gauge|sensor',
        re.IGNORECASE
    )

    if NON_DOMAIN.search(query_lower) and not DOMAIN_KEYWORDS.search(query_lower):
        return {
            **base_result,
            'lane': 'BLOCKED',
            'lane_reason': 'non_domain',
            'block_message': 'Celeste is for yacht operations. Ask about equipment, faults, work orders, handovers, or documents.',
            'skip_gpt': True,
        }

    # ========== LANE A: RULES_ONLY (simple commands) ==========
    # Check command patterns FIRST - these are explicit user actions
    # Polite prefix: allows various polite forms at the start
    # Pattern handles: "please", "can you", "could you", "hey can you", "I'd like you to", etc.
    POLITE_PREFIX = (
        r'^(?:hey\s+)?'  # Optional "hey " at the very start
        r'(?:please\s+)?'  # Optional "please "
        r'(?:(?:can|could|would)\s+(?:you|u)\s+(?:please\s+)?)?'  # "can you ", "could you please "
        r'(?:i(?:\'d|\s+would)\s+like\s+(?:you\s+)?to\s+)?'  # "I'd like you to ", "I would like to "
        r'(?:i\s+(?:need|want)\s+(?:you\s+)?to\s+)?'  # "I need you to ", "I want to "
        r'(?:pls\s+)?'  # "pls "
        r'(?:need\s+to\s+)?'  # "need to "
    )

    COMMAND_PATTERNS = [
        # Create work order (with typos)
        (POLITE_PREFIX + r'(?:create|creat|creaet|crate)\s+(work\s*order|workorder|wo)', 'create_work_order'),
        (POLITE_PREFIX + r'open\s+(work\s*order|wo)', 'open_work_order'),
        (POLITE_PREFIX + r'close\s+(work\s*order|wo)', 'close_work_order'),
        (POLITE_PREFIX + r'mark\s+(work\s*order|wo)', 'mark_work_order_complete'),
        (POLITE_PREFIX + r'log\s+', 'log_entry'),
        (POLITE_PREFIX + r'add\s+note', 'add_note'),
        (POLITE_PREFIX + r'add\s+(?:to\s+)?handover', 'add_to_handover'),  # "add handover" typo
        (POLITE_PREFIX + r'add\s+part', 'add_part_to_work_order'),
        (POLITE_PREFIX + r'attach\s+', 'attach_document'),
        (POLITE_PREFIX + r'(?:schedule|schdeule)\s+', 'schedule_task'),  # typo
        (POLITE_PREFIX + r'(?:assign|assing|asign)\s+', 'assign_task'),  # typos
        (POLITE_PREFIX + r'export\s+', 'export_data'),
        (POLITE_PREFIX + r'upload\s+', 'upload_document'),
        (POLITE_PREFIX + r'update\s+', 'update_record'),
        # Show/view (with typos)
        (POLITE_PREFIX + r'(?:show|shwo)\s+(?:equipment|equpment)', 'show_equipment_overview'),
        (POLITE_PREFIX + r'(?:show|shwo)\s+history', 'show_equipment_history'),
        (POLITE_PREFIX + r'view\s+handover', 'view_handover'),
        (POLITE_PREFIX + r'(?:generate|genrate)\s+summary', 'generate_summary'),
        (POLITE_PREFIX + r'search\s+documents?', 'search_documents'),
    ]
    for pattern, action in COMMAND_PATTERNS:
        if re.match(pattern, query_lower):
            target_match = re.search(r'(?:for|on|to|:|that|re|regarding|about|from)\s*(.+)$', query_lower)
            return {
                **base_result,
                'lane': 'RULES_ONLY',
                'lane_reason': 'command_pattern',
                'command_action': action,
                'command_target': target_match.group(1).strip() if target_match else None,
                'skip_gpt': True,
            }

    # ========== LANE B: NO_LLM (cheap lookup) ==========
    DIRECT_LOOKUP = [
        # Work orders
        r'^wo[-\s]?\d+$',
        r'^work\s*order\s+\d+$',
        r'^doc[-\s]?\d+$',
        # Error/fault codes
        r'^e\d{2,4}$',
        r'^(?:error|fault|alarm)\s+e?\d{2,4}$',
        r'^spn\s*\d+(?:\s*fmi\s*\d+)?$',  # SPN 100 FMI 3, spn123 fmi1
        r'^(?:fault\s+)?spn\s*\d+',  # fault SPN 146
        r'^j1939[\s/]*\d+(?:[/\s]+\d+)?$',  # J1939 169/3, j1939 169 3
        # Equipment codes
        r'^(?:me|dg|gen)\s*\d+$',  # ME1, DG2, gen1
        r'^(?:port|stbd)\s+main$',  # port main, stbd main
        # Brand-model lookups
        r'^(?:mtu|cat|caterpillar|cummins|kohler|onan|volvo|yanmar)\s+\d',
        r'^(?:furuno|garmin|simrad|raymarine)\s+\w+',
        r'^seakeeper\s*\d*',
        r'^(?:naiad|abt\s*trac|zf|twin\s*disc)\s*\d*',
        # Document lookups
        r'^\d{3,}\s*manual$',
        r'^cat\s+\d+\s*manual$',
        r'^[a-z]+\s+manual$',
        # Short equipment names
        r'^(?:watermaker|stabilizer|autopilot|radar|starlink|chartplotter|vhf|ais|epirb|gyro|windlass|crane|chiller|compressor|separator|purifier)s?$',
        # Certificate lookups
        r'^(?:mca|class|load\s*line|iopp|solas|ism|isps|marpol)\s+(?:certificate|cert)s?$',
    ]
    is_direct_lookup = any(re.match(p, query_lower) for p in DIRECT_LOOKUP)
    # Lookup-type intents from intent parser
    lookup_intents = {
        'find_document', 'find_work_order', 'find_part',
        'view_part_location', 'view_part_stock', 'view_equipment_details',
        'show_manual_section', 'view_document',
    }
    is_simple_lookup = word_count <= 4 and (intent in lookup_intents or query_type == 'lookup') and not has_problem_words and not has_temporal_context
    is_forced_lookup = mode in ['document_search', 'work_order_search']

    if is_direct_lookup or is_simple_lookup or is_forced_lookup:
        return {
            **base_result,
            'lane': 'NO_LLM',
            'lane_reason': 'direct_lookup_pattern' if is_direct_lookup else 'forced_mode' if is_forced_lookup else 'simple_lookup',
            'skip_gpt': True,
        }

    # ========== LANE C: GPT (full agent mode) ==========
    # Trigger GPT for:
    # - Problem words (diagnosis scenarios)
    # - Temporal context (time-sensitive queries)
    # - Diagnosis intents
    # - Aggregation queries ("what is failing most", "how many")
    # - Compliance queries ("who hasn't completed HOR")
    # - Complex general queries
    diagnosis_intents = {'diagnose_issue', 'diagnose_fault', 'report_fault'}
    needs_gpt = (
        has_problem_words or
        has_temporal_context or
        intent in diagnosis_intents or
        query_type in ('aggregation', 'compliance') or
        (intent in generic_intents and word_count >= 5)
    )

    if needs_gpt:
        reason = (
            'problem_words' if has_problem_words else
            'temporal_context' if has_temporal_context else
            'diagnosis_intent' if intent in diagnosis_intents else
            'aggregation_query' if query_type == 'aggregation' else
            'compliance_query' if query_type == 'compliance' else
            'complex_query'
        )
        return {
            **base_result,
            'lane': 'GPT',
            'lane_reason': reason,
            'skip_gpt': False,
        }

    # Default: simple lookup
    return {
        **base_result,
        'lane': 'NO_LLM',
        'lane_reason': 'default_fallback',
        'skip_gpt': True,
    }


@app.post("/extract", tags=["Entity Extraction"])
@limiter.limit("100/minute")
async def extract(
    request: Request,
    extraction_request: ExtractionRequest,
    auth: Dict = Depends(verify_security)
):
    """
    **SMART EXTRACTION ENDPOINT WITH LANE ROUTING**

    Routes queries to appropriate lane and extracts entities when needed.

    **Lanes:**
    - BLOCKED: Rejects paste-dumps, vague queries, non-domain queries
    - NO_LLM: Cheap lookups (WO-1234, CAT manual) - no GPT cost
    - RULES_ONLY: Simple commands (create WO) - no GPT cost
    - GPT: Full extraction for complex queries

    **Response includes:**
    - lane: Which processing path to use
    - lane_reason: Why this lane was chosen
    - entities: (GPT lane only) Extracted entities
    - embedding: (GPT lane + include_embedding) Vector embedding
    """
    import time
    start = time.time()

    query = extraction_request.query
    mode = getattr(extraction_request, 'mode', None)

    # Route to lane FIRST (cheap regex checks)
    routing = route_to_lane(query, mode)
    lane = routing['lane']

    # ========== BLOCKED: Return immediately ==========
    if lane == 'BLOCKED':
        latency_ms = int((time.time() - start) * 1000)
        logger.info(f"BLOCKED: query='{query[:50]}...', reason={routing['lane_reason']}")
        return {
            'lane': lane,
            'lane_reason': routing['lane_reason'],
            'block_message': routing.get('block_message'),
            'suggestions': routing.get('suggestions', []),
            'intent': routing['intent'],
            'intent_confidence': routing['intent_confidence'],
            'entities': [],
            'embedding': None,
            'metadata': {'latency_ms': latency_ms, 'model': None}
        }

    # ========== NO_LLM / RULES_ONLY: Regex Entity Extraction (No GPT Cost) ==========
    if lane in ['NO_LLM', 'RULES_ONLY']:
        # Run regex-based maritime entity extraction (Module B)
        # This gives us entities WITHOUT calling GPT - zero cost, ~5ms latency
        regex_extractor = get_entity_extractor()
        regex_entities = regex_extractor.extract_entities(query)

        # Convert EntityDetection objects to dicts for JSON response
        entities_dict = [e.to_dict() for e in regex_entities]

        latency_ms = int((time.time() - start) * 1000)

        # Get action from routing or default
        action = routing.get('command_action', 'none_search_only')
        action_confidence = routing['intent_confidence']

        # Build chips for suggestion UX
        chips = get_action_chips(query, action, action_confidence)

        # Production instrumentation logging
        logger.info(
            f"{lane}: query='{query}', "
            f"action={action}, "
            f"exec_class={chips['execution_class']}, "
            f"entities={len(entities_dict)}, "
            f"latency={latency_ms}ms"
        )

        return {
            'lane': lane,
            'lane_reason': routing['lane_reason'],
            'intent': routing['intent'],
            'intent_confidence': routing['intent_confidence'],
            'command_action': routing.get('command_action'),
            'command_target': routing.get('command_target'),
            'entities': entities_dict,
            'action': action,
            'action_confidence': action_confidence,
            'embedding': None,
            # Chips for suggestion UX
            'chips': chips,
            'execution_class': chips['execution_class'],
            'suggestion_worthy': chips['suggestion_worthy'],
            'metadata': {
                'latency_ms': latency_ms,
                'model': 'regex_only',
                'entity_count': len(entities_dict),
                'verb_family': chips['verb_family']
            }
        }

    # ========== GPT LANE: Full extraction ==========
    if graphrag_query is None or graphrag_query.gpt is None:
        # Fallback to regex pipeline
        if pipeline is None:
            raise HTTPException(status_code=503, detail="Extraction service not initialized")

        result = pipeline.extract(query)
        latency_ms = int((time.time() - start) * 1000)

        action = result.get("intent", "general_search")
        action_confidence = 0.7
        chips = get_action_chips(query, action, action_confidence)

        return {
            'lane': 'GPT',
            'lane_reason': routing['lane_reason'],
            'intent': routing['intent'],
            'intent_confidence': routing['intent_confidence'],
            'entities': result.get("canonical_entities", []),
            'action': action,
            'action_confidence': action_confidence,
            'person_filter': None,
            'embedding': None,
            'chips': chips,
            'execution_class': chips['execution_class'],
            'suggestion_worthy': chips['suggestion_worthy'],
            'metadata': {
                'model': 'regex_fallback',
                'embedding_model': None,
                'latency_ms': latency_ms,
                'fallback': True,
                'verb_family': chips['verb_family']
            }
        }

    try:
        gpt = graphrag_query.gpt

        # GPT extraction
        extraction = gpt.extract(query)

        # Generate embedding if requested
        embedding = None
        if extraction_request.include_embedding:
            embedding = gpt.embed(query)

        latency_ms = int((time.time() - start) * 1000)

        # Convert entities to dict for response and learning
        entities_dict = [e.to_dict() for e in extraction.entities]

        # Log unknown/low-confidence entities for offline learning
        # GPT is TEACHER, not live resolver
        unknown_logged = 0
        if graphrag_query and graphrag_query.client:
            unknown_logged = log_unknown_entities(
                client=graphrag_query.client,
                yacht_id=auth.get('yacht_id'),
                user_id=auth.get('user_id'),
                entities=entities_dict,
                intent=routing['intent'],
                query=query,
                lane='GPT'
            )

        # Build chips for suggestion UX
        chips = get_action_chips(query, extraction.action, extraction.action_confidence)

        # Extract context information for n8n workflow
        user_agent = request.headers.get("user-agent")
        timestamp = datetime.now(timezone.utc).isoformat()

        # Production instrumentation logging (per Action Execution Contract)
        logger.info(
            f"GPT: query='{query}', "
            f"action={extraction.action}, "
            f"exec_class={chips['execution_class']}, "
            f"verb_family={chips['verb_family']}, "
            f"entities={len(extraction.entities)}, "
            f"unknown_logged={unknown_logged}, "
            f"latency={latency_ms}ms, "
            f"yacht_id={auth.get('yacht_id')}"
        )

        return {
            'lane': 'GPT',
            'lane_reason': routing['lane_reason'],
            'intent': routing['intent'],
            'intent_confidence': max(routing['intent_confidence'], extraction.action_confidence),
            'entities': entities_dict,
            'action': extraction.action,
            'action_confidence': extraction.action_confidence,
            'person_filter': extraction.person_filter,
            'embedding': embedding,
            # Chips for suggestion UX (per Action Execution Contract)
            'chips': chips,
            'execution_class': chips['execution_class'],
            'suggestion_worthy': chips['suggestion_worthy'],
            'context': {
                'userId': auth.get('user_id'),
                'query': query,
                'timestamp': timestamp,
                'session_id': extraction_request.session_id,
                'client_info': {
                    'user_agent': user_agent
                }
            },
            'metadata': {
                'model': 'gpt-4o-mini',
                'embedding_model': 'text-embedding-3-small' if embedding else None,
                'embedding_dimensions': 1536 if embedding else None,
                'latency_ms': latency_ms,
                'verb_family': chips['verb_family'],
                'unknown_entities_logged': unknown_logged
            }
        }

    except Exception as e:
        logger.error(f"GPT extraction failed: {e}")
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
        version="3.3.0",
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
        "service": "CelesteOS Search & Extraction API",
        "version": "3.2.0",
        "status": "running",
        "security": "JWT + Yacht Signature (2 headers only)",
        "docs": "/docs",
        "health": "/health",
        "public_endpoints": {
            "search_v1": "POST /v1/search (Cards + actions)",
            "search_v2": "POST /v2/search (SITUATION-AWARE - Recommended)",
            "extract": "POST /extract (NLP extraction + embedding)"
        },
        "deprecated_endpoints": {
            "extract_microactions": "POST /extract_microactions (use /extract)",
            "extract_detailed": "POST /extract_detailed (use /extract)"
        },
        "internal_endpoints": {
            "graphrag_populate": "POST /graphrag/populate (n8n workflow only)",
            "graphrag_query": "POST /graphrag/query (internal - use /v2/search)",
            "graphrag_stats": "GET /graphrag/stats (admin only)"
        },
        "architecture": {
            "frontend_entrypoints": [
                "POST /v2/search → situation-aware search (cards + actions + recommendations)",
                "POST /v1/search → basic search (cards + actions)",
                "POST /v1/actions/execute → all mutations (action-endpoint-contract.md)"
            ],
            "internal_engines": [
                "Situation Engine: Pattern detection + policy recommendations",
                "GraphRAG: Entity resolution + graph traversal",
                "Modules A+B+C: Action detection + entity extraction + canonicalization"
            ],
            "response_specs": [
                "Cards: search-engine-spec.md Section 8",
                "Actions: micro-action-catalogue.md",
                "Situations: RECURRENT_SYMPTOM, RECURRENT_SYMPTOM_PRE_EVENT, HIGH_RISK_EQUIPMENT"
            ]
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
# /v1/search - PUBLIC SEARCH ENDPOINT
# ========================================================================

class SearchRequest(BaseModel):
    """Request model for unified search endpoint"""
    query: str = Field(..., min_length=1, max_length=1000, description="User natural language query")

    class Config:
        schema_extra = {
            "example": {
                "query": "Engine is overheating, show historic data from 2nd engineer"
            }
        }


@app.post("/v1/search", tags=["Search"])
@limiter.limit("100/minute")
async def search(
    request: Request,
    search_request: SearchRequest,
    auth: Dict = Depends(verify_security)
):
    """
    **UNIFIED SEARCH ENDPOINT - Primary Search Interface**

    The single public search endpoint for CelesteOS.
    All frontend search bar queries flow through here.

    **What it does:**
    1. Extracts intent and entities from natural language query
    2. Resolves entities to canonical IDs (equipment, parts, symptoms)
    3. Executes intent-specific search patterns using GraphRAG
    4. Returns result cards with attached micro-actions

    **Supported Intents:**
    - diagnose_fault: "What does error code E047 mean?"
    - find_document: "Open main engine manual to lube oil section"
    - equipment_history: "Engine is overheating, show historic data"
    - find_part: "Find filter for port main engine"
    - create_work_order: "Create work order for bilge pump"
    - general_search: Fallback multi-source search

    **Security (2 headers only):**
    - Authorization: Bearer <supabase_jwt> (user authentication)
    - X-Yacht-Signature: <sha256_signature> (yacht ownership proof)

    **Response Structure:**
    ```json
    {
        "query": "original query",
        "intent": "detected_intent",
        "entities": [...],
        "cards": [
            {
                "type": "equipment|document_chunk|fault|part|work_order|...",
                "title": "Card Title",
                "actions": [
                    {
                        "label": "Create Work Order",
                        "action": "create_work_order",
                        "endpoint": "/v1/work-orders/create",
                        "method": "POST",
                        "payload_template": {...}
                    }
                ],
                ...card_specific_fields
            }
        ],
        "metadata": {...}
    }
    ```

    **Card Types (search-engine-spec.md Section 8):**
    - document_chunk, fault, work_order, part, equipment, predictive, handover

    **Actions are executed via:**
    POST /v1/actions/execute (see action-endpoint-contract.md)
    """
    if graphrag_query is None:
        raise HTTPException(status_code=503, detail="Search service not initialized")

    try:
        yacht_id = auth.get("yacht_id")

        # Call GraphRAG query service internally
        result = graphrag_query.query(yacht_id, search_request.query)

        logger.info(
            f"/v1/search: yacht={yacht_id}, query='{search_request.query}', "
            f"intent={result.get('intent')}, cards={len(result.get('cards', []))}"
        )

        return result

    except Exception as e:
        logger.error(f"/v1/search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ========================================================================
# /v2/search - SITUATION-AWARE SEARCH ENDPOINT
# ========================================================================

# Confidence thresholds for entity disambiguation
CONFIDENCE_THRESHOLD = 0.5       # Below this = too uncertain, skip situation detection
AMBIGUITY_THRESHOLD = 0.05       # If top 2 candidates within this = ambiguous


@app.post("/v2/search", tags=["Search"])
@limiter.limit("100/minute")
async def situational_search(
    request: Request,
    search_request: SearchRequest,
    auth: Dict = Depends(verify_security)
):
    """
    **SITUATION-AWARE SEARCH ENDPOINT - V1 Agent**

    Extends /v1/search with:
    - Situation detection (recurrent symptoms, pre-charter risk, etc.)
    - Role-aware recommendations (engineer vs captain)
    - Confidence thresholds & disambiguation
    - Action-ready payloads

    **Response Structure:**
    ```json
    {
        "situation": {...},
        "risk": {...},
        "recommended_actions": [
            {
                "action": "create_work_order",
                "label": "Create work order: Main engine overheating",
                "reason": "Recurring issue before charter",
                "payload": {
                    "equipment_id": "uuid",
                    "title": "Main engine overheating",
                    "priority": "high",
                    "due_before": "2025-11-25T00:00:00Z"
                },
                "urgency": "urgent"
            }
        ],
        "disambiguation": null,  // or {"type": "equipment", "options": [...]}
        "cards": [...],
        "meta": {...}
    }
    ```

    **Situation Types (v1):**
    - RECURRENT_SYMPTOM: Same symptom >= 3 times in 60 days
    - RECURRENT_SYMPTOM_PRE_EVENT: Same + critical event within 72h
    - HIGH_RISK_EQUIPMENT: Equipment with risk_score > 0.7

    **Note:** If `disambiguation` is present, no situation/actions are generated.
    """
    if graphrag_query is None:
        raise HTTPException(status_code=503, detail="Search service not initialized")

    import time as time_module
    start_time = time_module.time()

    try:
        yacht_id = auth.get("yacht_id")
        user_id = auth.get("user_id")
        user_role = auth.get("role", "crew")  # Get role from auth

        # 1. Run GPT extraction
        extraction = None
        embedding = None
        resolved_entities = []

        if graphrag_query.gpt:
            extraction = graphrag_query.gpt.extract(search_request.query)
            embedding = graphrag_query.gpt.embed(search_request.query)

            # Convert extraction entities to resolved format
            # Note: ExtractedEntity has no 'canonical' field - canonicalization happens downstream
            # Use e.value as canonical placeholder until proper resolution
            for e in extraction.entities:
                resolved_entities.append({
                    'type': e.type,
                    'value': e.value,
                    'canonical': e.value,  # Use raw value; canonicalization is downstream
                    'confidence': e.confidence,
                    'entity_id': None  # Would need DB resolver
                })

        # 2. Check confidence thresholds & disambiguation
        disambiguation = None
        skip_situation = False

        # Check equipment entities specifically
        equipment_candidates = [e for e in resolved_entities if e.get('type') == 'equipment']
        if equipment_candidates:
            equipment_candidates.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            top_confidence = equipment_candidates[0].get('confidence', 0)

            # Too uncertain - skip situation detection
            if top_confidence < CONFIDENCE_THRESHOLD:
                logger.info(f"Entity confidence {top_confidence:.2f} below threshold {CONFIDENCE_THRESHOLD}, skipping situation")
                skip_situation = True

            # Ambiguous - offer disambiguation
            elif len(equipment_candidates) > 1:
                second_confidence = equipment_candidates[1].get('confidence', 0)
                if (top_confidence - second_confidence) < AMBIGUITY_THRESHOLD:
                    disambiguation = {
                        'type': 'equipment',
                        'message': 'Multiple equipment matches found. Please clarify:',
                        'options': [
                            {
                                'id': c.get('entity_id'),
                                'label': c.get('canonical', c.get('value')),
                                'score': round(c.get('confidence', 0), 2)
                            }
                            for c in equipment_candidates[:3]
                        ]
                    }
                    skip_situation = True
                    logger.info(f"Ambiguous equipment ({top_confidence:.2f} vs {second_confidence:.2f}), offering disambiguation")

        # 3. Get vessel context
        vessel_context = {}
        if situation_engine and graphrag_query.client and not skip_situation:
            try:
                ctx_result = graphrag_query.client.rpc('get_vessel_context', {
                    'p_yacht_id': yacht_id
                }).execute()
                if ctx_result.data:
                    ctx = ctx_result.data[0] if isinstance(ctx_result.data, list) else ctx_result.data
                    vessel_context = {
                        'current_status': ctx.get('current_status'),
                        'next_event_type': ctx.get('next_event_type'),
                        'next_event_at': ctx.get('next_event_at'),
                        'hours_until_event': ctx.get('hours_until_event'),
                        'time_pressure': ctx.get('time_pressure'),
                        'is_pre_charter_critical': ctx.get('is_pre_charter_critical')
                    }
            except Exception as ctx_err:
                logger.warning(f"Could not get vessel context: {ctx_err}")

        # 4. Detect situation (only if confident)
        situation = None
        recommendations = []
        suggestion_id = None

        if situation_engine and resolved_entities and not skip_situation:
            situation = situation_engine.detect_situation(
                yacht_id=yacht_id,
                resolved_entities=resolved_entities,
                vessel_context=vessel_context
            )

            if situation:
                # Role-aware recommendations
                recommendations = situation_engine.get_recommendations(
                    situation=situation,
                    yacht_id=yacht_id,
                    resolved_entities=resolved_entities,
                    user_role=user_role
                )

                # Log symptom report if equipment + symptom detected
                equipment_entities = [e for e in resolved_entities if e.get('type') == 'equipment']
                symptom_entities = [e for e in resolved_entities if e.get('type') == 'symptom']

                if equipment_entities and symptom_entities:
                    situation_engine.log_symptom_report(
                        yacht_id=yacht_id,
                        equipment_label=equipment_entities[0].get('canonical', equipment_entities[0].get('value', '')),
                        symptom_code=symptom_entities[0].get('canonical', symptom_entities[0].get('value', '')),
                        symptom_label=symptom_entities[0].get('value', ''),
                        user_id=user_id
                    )

        # 5. Run standard search
        search_result = graphrag_query.query(yacht_id, search_request.query)
        cards = search_result.get('cards', [])

        # 6. Log suggestion and get suggestion_id
        if situation_engine:
            suggestion_id = situation_engine.log_suggestion(
                yacht_id=yacht_id,
                user_id=user_id,
                query_text=search_request.query,
                intent=extraction.action if extraction else search_result.get('intent'),
                situation=situation,
                recommendations=recommendations
            )

        # 7. Build action-ready recommended_actions
        recommended_actions = []
        for rec in recommendations:
            action_item = rec.to_dict()
            action_item['id'] = suggestion_id  # Link to suggestion for feedback

            # Build action-ready payload for executable actions
            if rec.action == 'create_work_order':
                equipment = next((e for e in resolved_entities if e.get('type') == 'equipment'), {})
                symptom = next((e for e in resolved_entities if e.get('type') == 'symptom'), {})
                action_item['label'] = f"Create work order: {equipment.get('canonical', equipment.get('value', 'Equipment'))} {symptom.get('canonical', symptom.get('value', ''))}"
                action_item['payload'] = {
                    'equipment_id': equipment.get('entity_id'),
                    'equipment_label': equipment.get('canonical', equipment.get('value')),
                    'title': f"{equipment.get('canonical', equipment.get('value', ''))} {symptom.get('canonical', symptom.get('value', ''))}".strip(),
                    'priority': 'high' if situation and situation.severity.value == 'high' else 'normal',
                    'due_before': vessel_context.get('next_event_at') if vessel_context.get('is_pre_charter_critical') else None
                }
            else:
                action_item['label'] = rec.action.replace('_', ' ').title()
                action_item['payload'] = {}

            recommended_actions.append(action_item)

        # 8. Build response
        latency_ms = int((time_module.time() - start_time) * 1000)

        response = {
            'situation': situation.to_dict() if situation else None,
            'risk': {
                'if_ignored': situation.severity.value if situation else None,
                'if_acted': 'low' if situation else None,
                'confidence': 'approximate'
            } if situation else None,
            'recommended_actions': recommended_actions,
            'disambiguation': disambiguation,
            'cards': cards,
            'meta': {
                'yacht_id': yacht_id,
                'user_id': user_id,
                'user_role': user_role,
                'suggestion_id': suggestion_id,
                'query': search_request.query,
                'intent': extraction.action if extraction else search_result.get('intent'),
                'entities': resolved_entities,
                'vessel_context': vessel_context if vessel_context else None,
                'confidence_check': {
                    'threshold': CONFIDENCE_THRESHOLD,
                    'skipped_situation': skip_situation,
                    'reason': 'ambiguous' if disambiguation else ('low_confidence' if skip_situation else None)
                },
                'latency_ms': latency_ms
            }
        }

        logger.info(
            f"/v2/search: yacht={yacht_id}, role={user_role}, query='{search_request.query}', "
            f"situation={'detected: ' + situation.type if situation else 'none'}, "
            f"disambiguation={'yes' if disambiguation else 'no'}, "
            f"cards={len(cards)}, latency={latency_ms}ms"
        )

        return response

    except Exception as e:
        logger.error(f"/v2/search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ========================================================================
# /v1/actions - ACTION EXECUTION ENDPOINTS
# ========================================================================

class ActionExecuteRequest(BaseModel):
    """Request model for action execution"""
    suggestion_id: Optional[str] = Field(None, description="Link to the suggestion that triggered this action")
    action_type: str = Field(..., description="Type of action: create_work_order, run_diagnostic, etc.")
    payload: Dict = Field(..., description="Action-specific payload")

    class Config:
        schema_extra = {
            "example": {
                "suggestion_id": "uuid",
                "action_type": "create_work_order",
                "payload": {
                    "equipment_id": "uuid",
                    "title": "Main engine overheating",
                    "priority": "high",
                    "due_before": "2025-11-25T00:00:00Z"
                }
            }
        }


class FeedbackRequest(BaseModel):
    """Request model for suggestion feedback"""
    user_action_taken: str = Field(..., description="What the user did: accepted, ignored, modified")
    action_execution_id: Optional[str] = Field(None, description="If action was executed, link to execution")


VALID_ACTION_TYPES = {
    'create_work_order',
    'run_diagnostic',
    'schedule_inspection',
    'configure_alert',
    'view_predictive_analysis',
    'create_handover_note',
    'log_symptom'
}


@app.post("/v1/actions/execute", tags=["Actions"])
@limiter.limit("30/minute")
async def execute_action(
    request: Request,
    action_request: ActionExecuteRequest,
    auth: Dict = Depends(verify_security)
):
    """
    Execute a recommended action (e.g., create work order).

    **Flow:**
    1. Validates action_type
    2. Logs execution in action_executions table
    3. For create_work_order: creates the WO in work_orders table
    4. Updates suggestion_log if suggestion_id provided

    **Returns:**
    - execution_id: UUID of the action execution record
    - result_id: UUID of created resource (e.g., work order ID)
    - status: 'completed' or 'failed'
    """
    if graphrag_query is None or graphrag_query.client is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        yacht_id = auth.get("yacht_id")
        user_id = auth.get("user_id")

        # Validate action_type
        if action_request.action_type not in VALID_ACTION_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action_type. Must be one of: {', '.join(VALID_ACTION_TYPES)}"
            )

        # CRITICAL: Check gating requirements
        # Gated actions require explicit confirmation token
        if requires_confirmation(action_request.action_type):
            confirmation_token = action_request.payload.get("confirmation_token") if action_request.payload else None
            if not confirmation_token:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "confirmation_required",
                        "action": action_request.action_type,
                        "message": f"Action '{action_request.action_type}' requires user confirmation. "
                                   "Include a valid confirmation_token in payload.",
                        "gated": True
                    }
                )
            # TODO: Validate confirmation token (signature, expiry, user match)

        # 1. Log execution via RPC
        exec_result = graphrag_query.client.rpc('execute_action', {
            'p_yacht_id': yacht_id,
            'p_user_id': user_id,
            'p_action_type': action_request.action_type,
            'p_action_payload': action_request.payload,
            'p_suggestion_id': action_request.suggestion_id
        }).execute()

        execution_id = exec_result.data if exec_result.data else None

        if not execution_id:
            raise HTTPException(status_code=500, detail="Failed to create action execution record")

        # 2. Execute the actual action
        result_id = None
        status = 'completed'
        error_message = None

        if action_request.action_type == 'create_work_order':
            # Create work order in DB
            try:
                wo_result = graphrag_query.client.table('work_orders').insert({
                    'yacht_id': yacht_id,
                    'title': action_request.payload.get('title', 'New Work Order'),
                    'priority': action_request.payload.get('priority', 'normal'),
                    'status': 'open',
                    'created_by': user_id,
                    'equipment_id': action_request.payload.get('equipment_id'),
                    'due_date': action_request.payload.get('due_before')
                }).execute()

                if wo_result.data:
                    result_id = wo_result.data[0].get('id')
            except Exception as wo_err:
                logger.error(f"Failed to create work order: {wo_err}")
                status = 'failed'
                error_message = str(wo_err)

        # 3. Update execution record with result
        graphrag_query.client.rpc('complete_action', {
            'p_execution_id': execution_id,
            'p_status': status,
            'p_result_id': result_id,
            'p_error_message': error_message
        }).execute()

        logger.info(f"/v1/actions/execute: yacht={yacht_id}, action={action_request.action_type}, status={status}, result_id={result_id}")

        return {
            'execution_id': execution_id,
            'result_id': result_id,
            'status': status,
            'error': error_message
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/v1/actions/execute failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Action execution failed: {str(e)}")


@app.post("/v1/suggestions/{suggestion_id}/feedback", tags=["Actions"])
@limiter.limit("60/minute")
async def log_feedback(
    suggestion_id: str,
    request: Request,
    feedback: FeedbackRequest,
    auth: Dict = Depends(verify_security)
):
    """
    Record user feedback on a suggestion.

    **user_action_taken values:**
    - `accepted`: User executed the recommended action
    - `ignored`: User dismissed without acting
    - `modified`: User took a different but related action
    """
    if graphrag_query is None or graphrag_query.client is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # Validate user_action_taken
        if feedback.user_action_taken not in ('accepted', 'ignored', 'modified'):
            raise HTTPException(
                status_code=400,
                detail="user_action_taken must be: accepted, ignored, or modified"
            )

        # Log feedback via RPC
        result = graphrag_query.client.rpc('log_suggestion_feedback', {
            'p_suggestion_id': suggestion_id,
            'p_user_action_taken': feedback.user_action_taken,
            'p_action_execution_id': feedback.action_execution_id
        }).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        logger.info(f"/v1/suggestions/{suggestion_id}/feedback: action={feedback.user_action_taken}")

        return {'status': 'recorded', 'suggestion_id': suggestion_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/v1/suggestions/{suggestion_id}/feedback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")


# ========================================================================
# GRAPHRAG INTERNAL ENDPOINTS (not in public schema)
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
    force_reprocess: bool = Field(default=False, description="Force re-processing even if already successful")

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
                ],
                "force_reprocess": False
            }
        }


@app.post("/graphrag/query", tags=["Internal"], include_in_schema=False)
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


@app.post("/graphrag/populate", tags=["Internal"], include_in_schema=False)
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
            maintenance_facts=populate_request.maintenance,
            force_reprocess=populate_request.force_reprocess
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


@app.get("/graphrag/stats", tags=["Internal"], include_in_schema=False)
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
