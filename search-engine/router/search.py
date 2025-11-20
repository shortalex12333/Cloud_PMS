"""
Search API Router
Handles all search-related endpoints
"""
from fastapi import APIRouter, Header, HTTPException, status
from typing import Optional
import uuid
import time
import logging

from models.requests import SearchRequest, BatchSearchRequest
from models.responses import SearchResponse, EntityExtractionResult, IntentDetectionResult
from utils.validators import validate_jwt, validate_yacht_signature, get_yacht_id_from_signature
from services import (
    extract_entities,
    detect_intent,
    search_semantic,
    search_graph,
    fuse_results,
    generate_cards,
    generate_micro_actions
)
from services.intent_detection import should_activate_graph_rag

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
    3. Semantic RAG
    4. GraphRAG (if applicable)
    5. Result fusion
    6. Card generation
    7. Micro-action assignment

    Returns structured search results with contextual actions.
    """
    start_time = time.time()

    # Validate authentication
    try:
        jwt_payload = await validate_jwt(authorization)
        yacht_signature = await validate_yacht_signature(x_yacht_signature)
        yacht_id = await get_yacht_id_from_signature(yacht_signature)

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

        # Step 3: Determine search strategy
        use_graph_rag = should_activate_graph_rag(
            intent_result.intent,
            entities,
            request.query
        )

        # Override based on mode parameter
        if request.mode == "rag":
            use_graph_rag = False
        elif request.mode == "graph_rag":
            use_graph_rag = True

        sources_searched = []

        # Step 4: Semantic RAG (always run)
        semantic_results = await search_semantic(
            query=request.query,
            yacht_id=yacht_id,
            entities=entities,
            intent=intent_result.intent,
            top_k=request.top_k
        )
        sources_searched.extend(semantic_results.keys())

        # Step 5: GraphRAG (conditional)
        graph_results = {}
        if use_graph_rag:
            graph_results = await search_graph(
                query=request.query,
                yacht_id=yacht_id,
                entities=entities,
                intent=intent_result.intent
            )
            sources_searched.append("graph_rag")

        # Step 6: Fusion
        fused_results = await fuse_results(
            semantic_results=semantic_results,
            graph_results=graph_results,
            entities=entities,
            intent=intent_result.intent
        )

        # Step 7: Generate cards
        cards = await generate_cards(fused_results)

        # Step 8: Attach micro-actions
        cards_with_actions = await generate_micro_actions(
            cards=cards,
            intent=intent_result.intent,
            entities=entities
        )

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Build response
        response = SearchResponse(
            query_id=query_id,
            query=request.query,
            entities=entities,
            intent=intent_result,
            results=cards_with_actions,
            latency_ms=latency_ms,
            sources_searched=list(set(sources_searched))
        )

        logger.info(
            f"[{query_id}] Search completed in {latency_ms}ms: "
            f"{len(cards_with_actions)} results, "
            f"intent={intent_result.intent}"
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
