"""
Search API Router
Handles all search-related endpoints

GraphRAG is controlled by settings.graph_rag_enabled flag
"""
from fastapi import APIRouter, Header, HTTPException, status
from typing import Optional
import uuid
import time
import logging

from models.requests import SearchRequest, BatchSearchRequest
from models.responses import SearchResponse, EntityExtractionResult, IntentDetectionResult
from models.card import SearchResultCard
from utils.validators import validate_jwt, validate_yacht_signature, get_yacht_id_from_signature
from services import (
    extract_entities,
    detect_intent,
    search_semantic,
)
from services.graph_rag import search_graph
from services.fusion import fuse_results
from services.card_generator import generate_cards
from services.intent_detection import should_activate_graph_rag
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    authorization: str = Header(...),
    x_yacht_signature: Optional[str] = Header(None)
):
    """
    Universal search endpoint

    Processes natural language queries through:
    1. Entity extraction
    2. Intent detection
    3. Semantic RAG (always)
    4. GraphRAG (feature-flagged, disabled by default)
    5. Result fusion
    6. Card generation with micro-actions

    Returns structured search results with contextual actions.
    """
    start_time = time.time()

    # Validate authentication
    try:
        jwt_payload = await validate_jwt(authorization)
        yacht_signature = await validate_yacht_signature(x_yacht_signature)
        yacht_id = await get_yacht_id_from_signature(yacht_signature)
        user_role = jwt_payload.get("role", "Engineer")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

    # Generate unique query ID
    query_id = str(uuid.uuid4())

    logger.info(f"[{query_id}] Search request from yacht {yacht_id}: {request.query}")

    try:
        # Step 1: Entity Extraction
        entities = extract_entities(request.query)

        # Step 2: Intent Detection
        intent_result = detect_intent(request.query, entities)

        # Step 3: Determine if GraphRAG should be used
        # GraphRAG is disabled by default (settings.graph_rag_enabled = False)
        use_graph_rag = False

        if settings.graph_rag_enabled:
            # Only consider using GraphRAG if globally enabled
            use_graph_rag = should_activate_graph_rag(
                intent_result.intent,
                entities,
                request.query
            )

        # Override based on mode parameter
        if request.mode == "rag":
            use_graph_rag = False
        elif request.mode == "graph_rag":
            # Only allow graph_rag mode if feature is enabled
            if settings.graph_rag_enabled:
                use_graph_rag = True
            else:
                logger.warning(f"[{query_id}] graph_rag mode requested but feature is disabled")

        sources_searched = []

        # Step 4: Semantic RAG (always run - PRIMARY source)
        semantic_results = await search_semantic(
            query=request.query,
            yacht_id=yacht_id,
            entities=entities,
            intent=intent_result.intent,
            top_k=request.top_k
        )
        sources_searched.extend(semantic_results.keys())

        # Step 5: GraphRAG (feature-flagged)
        # When disabled, search_graph returns empty structured response
        graph_results = {}
        if use_graph_rag:
            graph_results = await search_graph(
                query=request.query,
                yacht_id=yacht_id,
                entities=entities,
                intent=intent_result.intent
            )
            if graph_results.get("nodes"):
                sources_searched.append("graph_rag")
            logger.info(
                f"[{query_id}] GraphRAG: {len(graph_results.get('nodes', []))} nodes, "
                f"{len(graph_results.get('edges', []))} edges"
            )
        else:
            logger.debug(f"[{query_id}] GraphRAG disabled/skipped")

        # Step 6: Fusion (works correctly without graph signals)
        fused_results = await fuse_results(
            semantic_results=semantic_results,
            graph_results=graph_results,
            entities=entities,
            intent=intent_result.intent
        )

        # Step 7: Generate cards with micro-actions
        # Yacht config for feature flags
        yacht_config = {
            "predictive_enabled": settings.predictive_enabled,
            "graph_rag_enabled": settings.graph_rag_enabled
        }

        cards = await generate_cards(
            fused_results=fused_results,
            intent=intent_result.intent,
            entities=entities,
            user_role=user_role,
            yacht_config=yacht_config
        )

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Build response
        response = SearchResponse(
            query_id=query_id,
            query=request.query,
            entities=entities,
            intent=intent_result,
            results=cards,
            latency_ms=latency_ms,
            sources_searched=list(set(sources_searched))
        )

        logger.info(
            f"[{query_id}] Search completed in {latency_ms}ms: "
            f"{len(cards)} results, "
            f"intent={intent_result.intent}, "
            f"graph_rag={'enabled' if use_graph_rag else 'disabled'}"
        )

        return response

    except Exception as e:
        logger.error(f"[{query_id}] Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/entities/debug")
async def debug_entities(
    query: str,
    authorization: str = Header(...)
):
    """
    Debug endpoint for entity extraction

    Useful for testing and debugging entity extraction logic.
    """
    # Validate authentication
    await validate_jwt(authorization)

    # Extract entities
    entities = extract_entities(query)

    return {
        "query": query,
        "entities": entities.model_dump()
    }


@router.get("/config/features")
async def get_feature_flags(
    authorization: str = Header(...)
):
    """
    Get current feature flag configuration

    Useful for debugging and frontend feature detection.
    """
    await validate_jwt(authorization)

    return {
        "graph_rag_enabled": settings.graph_rag_enabled,
        "predictive_enabled": settings.predictive_enabled,
        "keyword_search_enabled": settings.keyword_search_enabled,
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "default_top_k": settings.default_top_k,
        "graph_max_depth": settings.graph_max_depth
    }


@router.post("/search/batch")
async def batch_search(
    request: BatchSearchRequest,
    authorization: str = Header(...),
    x_yacht_signature: Optional[str] = Header(None)
):
    """
    Batch search endpoint

    Processes multiple queries in a single request.
    Useful for testing and bulk analysis.
    """
    # Validate authentication
    jwt_payload = await validate_jwt(authorization)
    yacht_signature = await validate_yacht_signature(x_yacht_signature)
    yacht_id = await get_yacht_id_from_signature(yacht_signature)

    results = []

    for query_text in request.queries:
        try:
            # Create individual search request
            search_req = SearchRequest(
                query=query_text,
                mode=request.mode,
                filters=request.filters
            )

            # Execute search (reuse main search logic)
            result = await search(
                request=search_req,
                authorization=authorization,
                x_yacht_signature=x_yacht_signature
            )

            results.append({
                "query": query_text,
                "success": True,
                "result": result
            })

        except Exception as e:
            logger.error(f"Batch search failed for query '{query_text}': {e}")
            results.append({
                "query": query_text,
                "success": False,
                "error": str(e)
            })

    return {
        "total_queries": len(request.queries),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


@router.get("/graph/related")
async def get_graph_related(
    equipment_id: Optional[str] = None,
    fault_code: Optional[str] = None,
    part_id: Optional[str] = None,
    max_depth: int = 2,
    limit: int = 20,
    authorization: str = Header(...),
    x_yacht_signature: Optional[str] = Header(None)
):
    """
    Get related nodes from graph (GraphRAG interface)

    Returns stubbed empty response when graph_rag_enabled = False
    """
    await validate_jwt(authorization)
    yacht_signature = await validate_yacht_signature(x_yacht_signature)
    yacht_id = await get_yacht_id_from_signature(yacht_signature)

    if not settings.graph_rag_enabled:
        return {
            "enabled": False,
            "message": "GraphRAG is currently disabled",
            "nodes": [],
            "edges": [],
            "total_count": 0
        }

    from services.graph_rag import get_related_nodes

    result = await get_related_nodes(
        yacht_id=yacht_id,
        equipment_id=equipment_id,
        fault_code=fault_code,
        part_id=part_id,
        max_depth=max_depth,
        limit=limit
    )

    return {
        "enabled": True,
        **result
    }


@router.get("/graph/fault-cascade")
async def get_fault_cascade_analysis(
    equipment_id: str,
    fault_code: str,
    lookback_days: int = 90,
    authorization: str = Header(...),
    x_yacht_signature: Optional[str] = Header(None)
):
    """
    Get fault cascade analysis (predictive GraphRAG)

    Returns stubbed empty response when graph_rag_enabled = False
    """
    await validate_jwt(authorization)
    yacht_signature = await validate_yacht_signature(x_yacht_signature)
    yacht_id = await get_yacht_id_from_signature(yacht_signature)

    if not settings.graph_rag_enabled:
        return {
            "enabled": False,
            "message": "GraphRAG is currently disabled",
            "root_fault": None,
            "cascade_nodes": [],
            "cascade_edges": [],
            "affected_equipment": [],
            "risk_level": "unknown",
            "recommended_actions": []
        }

    from services.graph_rag import get_fault_cascade

    result = await get_fault_cascade(
        yacht_id=yacht_id,
        equipment_id=equipment_id,
        fault_code=fault_code,
        lookback_days=lookback_days
    )

    return {
        "enabled": True,
        **result
    }
