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

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import time
import logging
import os
import sys

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post("/search", response_model=SearchResponse)
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
async def webhook_search(request: Request):
    """
    Webhook endpoint for frontend search requests.

    Accepts frontend payload format with auth and context.
    Extracts yacht_id from auth payload and routes to pipeline.
    """
    try:
        body = await request.json()
        logger.info(f"[webhook/search] Received query: {body.get('query')}")

        # Extract data from frontend format
        query = body.get('query')
        auth = body.get('auth', {})
        yacht_id = auth.get('yacht_id')
        limit = body.get('limit', 20)

        # Validate required fields
        if not query:
            raise HTTPException(status_code=400, detail="Missing required field: query")
        if not yacht_id:
            raise HTTPException(status_code=400, detail="Missing required field: auth.yacht_id")

        logger.info(f"[webhook/search] yacht_id={yacht_id}, query='{query}'")

        # Call main search logic
        search_request = SearchRequest(
            query=query,
            yacht_id=yacht_id,
            limit=limit
        )

        result = await search(search_request)
        return result

    except Exception as e:
        logger.error(f"[webhook/search] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract", response_model=ExtractResponse)
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
