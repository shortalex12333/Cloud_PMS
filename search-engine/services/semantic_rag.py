"""
Semantic RAG Module
Performs vector similarity search across document chunks using pgvector
"""
from typing import List, Dict, Optional, Any
from utils.supabase_client import get_supabase_client, vector_search
from utils.embeddings import get_embedding
from models.responses import EntityExtractionResult, IntentType
from config import settings
import logging

logger = logging.getLogger(__name__)


async def search_semantic(
    query: str,
    yacht_id: str,
    entities: EntityExtractionResult,
    intent: IntentType,
    top_k: int = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Perform semantic search across multiple data sources

    Args:
        query: Search query text
        yacht_id: Yacht ID for isolation
        entities: Extracted entities
        intent: Detected intent
        top_k: Number of results per source

    Returns:
        Dictionary mapping source names to result lists
    """
    logger.info(f"Starting semantic search for yacht {yacht_id}")

    if top_k is None:
        top_k = settings.default_top_k

    # Generate query embedding
    try:
        query_embedding = await get_embedding(query)
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        return {}

    # Build filters based on entities
    filters = build_filters(entities)

    # Search across multiple sources based on intent
    results = {}

    # 1. Document chunks (always search)
    doc_results = await search_document_chunks(
        query_embedding=query_embedding,
        yacht_id=yacht_id,
        filters=filters,
        top_k=top_k
    )
    if doc_results:
        results["document_chunks"] = doc_results

    # 2. Work order history (if relevant)
    if intent in [IntentType.DIAGNOSE_FAULT, IntentType.CREATE_WORK_ORDER, IntentType.GENERAL_SEARCH]:
        wo_results = await search_work_order_history(
            query_embedding=query_embedding,
            yacht_id=yacht_id,
            filters=filters,
            top_k=min(top_k, 10)
        )
        if wo_results:
            results["work_order_history"] = wo_results

    # 3. Faults (if fault-related)
    if entities.fault_codes or intent == IntentType.DIAGNOSE_FAULT:
        fault_results = await search_faults(
            yacht_id=yacht_id,
            entities=entities,
            top_k=min(top_k, 8)
        )
        if fault_results:
            results["faults"] = fault_results

    # 4. Parts (if part-related)
    if entities.part_numbers or intent == IntentType.FIND_PART:
        part_results = await search_parts(
            yacht_id=yacht_id,
            entities=entities,
            query=query,
            top_k=min(top_k, 8)
        )
        if part_results:
            results["parts"] = part_results

    # 5. Email messages (if available)
    if intent == IntentType.FIND_DOCUMENT:
        email_results = await search_emails(
            query_embedding=query_embedding,
            yacht_id=yacht_id,
            top_k=min(top_k, 5)
        )
        if email_results:
            results["emails"] = email_results

    # 6. Global Celeste knowledge (fallback if local results weak)
    if sum(len(r) for r in results.values()) < 5:
        global_results = await search_global_knowledge(
            query_embedding=query_embedding,
            entities=entities,
            top_k=5
        )
        if global_results:
            results["global_knowledge"] = global_results

    logger.info(f"Semantic search completed: {sum(len(r) for r in results.values())} total results")

    return results


async def search_document_chunks(
    query_embedding: List[float],
    yacht_id: str,
    filters: Dict[str, Any],
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Search document chunks using vector similarity

    Args:
        query_embedding: Query embedding vector
        yacht_id: Yacht ID
        filters: Metadata filters
        top_k: Number of results

    Returns:
        List of matching document chunks with scores
    """
    try:
        results = await vector_search(
            table="document_chunks",
            query_embedding=query_embedding,
            yacht_id=yacht_id,
            limit=top_k,
            filters=filters
        )

        return results

    except Exception as e:
        logger.error(f"Document chunk search failed: {e}")
        return []


async def search_work_order_history(
    query_embedding: List[float],
    yacht_id: str,
    filters: Dict[str, Any],
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Search work order history notes (if they have embeddings)

    Args:
        query_embedding: Query embedding vector
        yacht_id: Yacht ID
        filters: Metadata filters
        top_k: Number of results

    Returns:
        List of matching work order history records
    """
    try:
        # Assuming work_order_history has been embedded
        # (This would need to be set up in the indexing pipeline)
        client = get_supabase_client(use_service_role=True)

        # For now, use simple text search on notes
        # In production, this would use embeddings
        query = client.table("work_order_history") \
            .select("*, equipment(name), work_order:work_orders(title)") \
            .eq("yacht_id", yacht_id) \
            .order("completed_at", desc=True) \
            .limit(top_k)

        if filters.get("equipment_id"):
            query = query.eq("equipment_id", filters["equipment_id"])

        result = query.execute()

        # Add source field
        for item in result.data:
            item["source"] = "work_order_history"
            item["similarity"] = 0.7  # Placeholder

        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Work order history search failed: {e}")
        return []


async def search_faults(
    yacht_id: str,
    entities: EntityExtractionResult,
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Search faults table (structured search)

    Args:
        yacht_id: Yacht ID
        entities: Extracted entities
        top_k: Number of results

    Returns:
        List of matching fault records
    """
    try:
        client = get_supabase_client(use_service_role=True)
        query = client.table("faults") \
            .select("*, equipment(name, code)") \
            .eq("yacht_id", yacht_id) \
            .order("detected_at", desc=True) \
            .limit(top_k)

        # Filter by fault code if present
        if entities.fault_codes:
            # Search for any of the fault codes
            fault_code_filter = "|".join(entities.fault_codes)
            query = query.in_("fault_code", entities.fault_codes)

        # Filter by equipment if matched
        # (Would need equipment_id resolution in practice)

        result = query.execute()

        # Add source and score
        for item in result.data:
            item["source"] = "fault"
            item["similarity"] = 0.95  # High confidence for exact matches

        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Fault search failed: {e}")
        return []


async def search_parts(
    yacht_id: str,
    entities: EntityExtractionResult,
    query: str,
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Search parts table

    Args:
        yacht_id: Yacht ID
        entities: Extracted entities
        query: Original query text
        top_k: Number of results

    Returns:
        List of matching part records
    """
    try:
        client = get_supabase_client(use_service_role=True)
        query_builder = client.table("parts") \
            .select("*, stock_levels(quantity, location:stock_locations(name))") \
            .eq("yacht_id", yacht_id) \
            .limit(top_k)

        # Exact part number match
        if entities.part_numbers:
            query_builder = query_builder.in_("part_number", entities.part_numbers)
        else:
            # Fuzzy search on name
            query_builder = query_builder.ilike("name", f"%{query}%")

        result = query_builder.execute()

        # Add source and score
        for item in result.data:
            item["source"] = "part"
            item["similarity"] = 0.9 if entities.part_numbers else 0.7

        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Parts search failed: {e}")
        return []


async def search_emails(
    query_embedding: List[float],
    yacht_id: str,
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Search email messages (if table exists)

    Args:
        query_embedding: Query embedding
        yacht_id: Yacht ID
        top_k: Number of results

    Returns:
        List of matching emails
    """
    try:
        results = await vector_search(
            table="email_messages",
            query_embedding=query_embedding,
            yacht_id=yacht_id,
            limit=top_k,
            filters={}
        )

        return results

    except Exception as e:
        logger.debug(f"Email search skipped (table may not exist): {e}")
        return []


async def search_global_knowledge(
    query_embedding: List[float],
    entities: EntityExtractionResult,
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Search global Celeste knowledge base

    Args:
        query_embedding: Query embedding
        entities: Extracted entities
        top_k: Number of results

    Returns:
        List of matching global knowledge chunks
    """
    try:
        client = get_supabase_client(use_service_role=True)

        # Query celeste_chunks (no yacht_id filter)
        # This would use the match_documents function adapted for global data
        result = client.rpc(
            "match_global_documents",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "filter": {}  # Could filter by manufacturer if entity present
            }
        ).execute()

        # Add source marker
        for item in result.data:
            item["source"] = "global_knowledge"

        return result.data if result.data else []

    except Exception as e:
        logger.debug(f"Global knowledge search skipped: {e}")
        return []


def build_filters(entities: EntityExtractionResult) -> Dict[str, Any]:
    """
    Build metadata filters from extracted entities

    Args:
        entities: Extracted entities

    Returns:
        Filter dictionary for vector search
    """
    filters = {}

    # Filter by document type if specified
    if entities.document_types:
        filters["document_type"] = entities.document_types[0]

    # Could add more filters based on entities
    # For example, equipment_id if we resolve equipment names to IDs

    return filters
