"""
Supabase client wrapper for CelesteOS
"""
from supabase import create_client, Client
from functools import lru_cache
from config import settings
import logging

logger = logging.getLogger(__name__)


@lru_cache()
def get_supabase_client(use_service_role: bool = False) -> Client:
    """
    Get Supabase client instance (cached)

    Args:
        use_service_role: If True, use service role key (bypasses RLS)

    Returns:
        Supabase client instance
    """
    try:
        key = (
            settings.supabase_service_role_key
            if use_service_role
            else settings.supabase_anon_key
        )
        client = create_client(settings.supabase_url, key)
        logger.info(f"Supabase client created (service_role={use_service_role})")
        return client
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        raise


async def execute_query(
    query: str,
    params: dict = None,
    use_service_role: bool = False
) -> dict:
    """
    Execute a raw SQL query via Supabase RPC

    Args:
        query: SQL query string
        params: Query parameters
        use_service_role: Whether to use service role

    Returns:
        Query results
    """
    client = get_supabase_client(use_service_role=use_service_role)
    try:
        result = client.rpc("execute_sql", {"query": query, "params": params or {}})
        return result.data
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise


async def vector_search(
    table: str,
    query_embedding: list[float],
    yacht_id: str,
    limit: int = 15,
    filters: dict = None
) -> list[dict]:
    """
    Perform vector similarity search

    Args:
        table: Table name (document_chunks, etc.)
        query_embedding: Query embedding vector
        yacht_id: Yacht ID for isolation
        limit: Number of results
        filters: Additional filters

    Returns:
        List of matching records with similarity scores
    """
    client = get_supabase_client(use_service_role=True)

    try:
        # Build the query
        query = client.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_count": limit,
                "filter": {"yacht_id": yacht_id, **(filters or {})}
            }
        )

        result = query.execute()
        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []


async def get_equipment_by_name(
    yacht_id: str,
    equipment_name: str,
    fuzzy: bool = True
) -> list[dict]:
    """
    Retrieve equipment records by name (exact or fuzzy)

    Args:
        yacht_id: Yacht ID
        equipment_name: Equipment name to search
        fuzzy: Whether to use fuzzy matching

    Returns:
        List of equipment records
    """
    client = get_supabase_client(use_service_role=True)

    try:
        query = client.table("equipment").select("*").eq("yacht_id", yacht_id)

        if fuzzy:
            query = query.ilike("name", f"%{equipment_name}%")
        else:
            query = query.eq("name", equipment_name)

        result = query.execute()
        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Equipment lookup failed: {e}")
        return []


async def get_fault_by_code(
    yacht_id: str,
    fault_code: str
) -> list[dict]:
    """
    Retrieve fault records by fault code

    Args:
        yacht_id: Yacht ID
        fault_code: Fault code to search

    Returns:
        List of fault records
    """
    client = get_supabase_client(use_service_role=True)

    try:
        result = client.table("faults") \
            .select("*") \
            .eq("yacht_id", yacht_id) \
            .eq("fault_code", fault_code) \
            .execute()

        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Fault lookup failed: {e}")
        return []


async def get_parts_by_number(
    yacht_id: str,
    part_number: str
) -> list[dict]:
    """
    Retrieve parts by part number

    Args:
        yacht_id: Yacht ID
        part_number: Part number to search

    Returns:
        List of part records
    """
    client = get_supabase_client(use_service_role=True)

    try:
        result = client.table("parts") \
            .select("*, stock_levels(*)") \
            .eq("yacht_id", yacht_id) \
            .eq("part_number", part_number) \
            .execute()

        return result.data if result.data else []

    except Exception as e:
        logger.error(f"Parts lookup failed: {e}")
        return []
