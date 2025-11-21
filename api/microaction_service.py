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

Endpoints:
- POST /extract_microactions - Main extraction endpoint
- POST /extract_detailed - Extended extraction with metadata
- GET /health - Health check
- GET /patterns - List all supported actions

Similar architecture to maritime entity extraction service.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
import time
import logging
from pathlib import Path

# Import extraction modules
from microaction_extractor import MicroActionExtractor, get_extractor
from microaction_config import get_config, ExtractionConfig, ValidationRules

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
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for n8n and frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================================================
# GLOBAL STATE (load patterns once at startup)
# ========================================================================

# Extractor instance (singleton, loaded at startup)
extractor: Optional[MicroActionExtractor] = None

# Configuration (default to production)
config: ExtractionConfig = get_config('production')

# Request counter for monitoring
request_counter = 0

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


class PatternsResponse(BaseModel):
    """Response listing all supported actions"""
    total_actions: int
    actions_by_category: Dict[str, List[str]]
    all_actions: List[str]


# ========================================================================
# STARTUP & SHUTDOWN EVENTS
# ========================================================================

startup_time = time.time()

@app.on_event("startup")
async def startup_event():
    """Load extractor and patterns at startup (runs once)"""
    global extractor, config
    logger.info("🚀 Starting Micro-Action Extraction Service...")

    try:
        # Initialize extractor (this loads and compiles all patterns)
        extractor = get_extractor()
        logger.info(f"✓ Loaded {len(extractor.patterns)} patterns")
        logger.info(f"✓ Compiled {len(extractor.compiled_patterns)} action patterns")
        logger.info(f"✓ Built gazetteer with {len(extractor.gazetteer)} terms")

        # Load configuration
        config = get_config('production')
        logger.info(f"✓ Configuration: AI fallback threshold = {config.ai_fallback_threshold}")

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

@app.post("/extract_microactions", response_model=ExtractionResponse, tags=["Extraction"])
async def extract_microactions(request: ExtractionRequest):
    """
    Main extraction endpoint. Extract micro-actions from natural language query.

    Returns list of canonical action names (e.g., ["create_work_order", "add_to_handover"]).

    **Examples:**
    - "create work order" → ["create_work_order"]
    - "add to handover and create wo" → ["add_to_handover", "create_work_order"]
    - "show all open work orders" → ["list_work_orders"]
    - "what's the weather" → [] (unsupported)
    """
    if extractor is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    start_time = time.time()

    try:
        # Run extraction
        if request.include_metadata:
            result = extractor.extract_with_details(request.query)
            actions = result['micro_actions']
            has_unsupported = result['has_unsupported']
        else:
            actions = extractor.extract_microactions(request.query)
            has_unsupported = False

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Validate action combination if requested
        validation = None
        if request.validate_combination and actions:
            validation = ValidationRules.validate_action_combination(actions)

        # Build response
        response = ExtractionResponse(
            micro_actions=actions,
            count=len(actions),
            latency_ms=latency_ms,
            query=request.query,
            has_unsupported=has_unsupported,
            validation=validation
        )

        logger.info(
            f"Extracted {len(actions)} actions from '{request.query}' "
            f"in {latency_ms}ms: {actions}"
        )

        return response

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.post("/extract_detailed", response_model=DetailedExtractionResponse, tags=["Extraction"])
async def extract_detailed(request: ExtractionRequest):
    """
    Extended extraction endpoint with detailed match metadata.

    Returns:
    - All detected micro-actions
    - Detailed match information (confidence, source, span)
    - Total matches before deduplication
    - Validation results

    Useful for debugging and understanding extraction decisions.
    """
    if extractor is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    start_time = time.time()

    try:
        # Run detailed extraction
        result = extractor.extract_with_details(request.query)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Validate action combination
        validation = None
        if request.validate_combination and result['micro_actions']:
            validation = ValidationRules.validate_action_combination(result['micro_actions'])

        # Build response
        response = DetailedExtractionResponse(
            micro_actions=result['micro_actions'],
            count=result['unique_actions'],
            latency_ms=latency_ms,
            query=request.query,
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

    return HealthResponse(
        status="healthy" if extractor is not None else "unhealthy",
        version="1.0.0",
        patterns_loaded=len(extractor.patterns) if extractor else 0,
        total_requests=request_counter,
        uptime_seconds=uptime
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

    for action_name, action_data in extractor.patterns.items():
        # Skip meta keys
        if action_name.startswith('_'):
            continue

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
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "extract": "POST /extract_microactions",
            "detailed": "POST /extract_detailed",
            "patterns": "GET /patterns"
        }
    }


# ========================================================================
# N8N WRAPPER FUNCTION (for direct import in n8n Code node)
# ========================================================================

def extract_for_n8n(query: str) -> Dict:
    """
    Simple wrapper for n8n HTTP Request node.

    Usage in n8n:
    1. HTTP Request node
    2. Method: POST
    3. URL: https://your-render-url.onrender.com/extract_microactions
    4. Body: {"query": "create work order and add to handover"}
    5. Response: {"micro_actions": ["create_work_order", "add_to_handover"], "count": 2, "latency_ms": 102}
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
