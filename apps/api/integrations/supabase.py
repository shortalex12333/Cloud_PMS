"""
CelesteOS Backend - Supabase Integration

Handles:
- Supabase client initialization
- Vector search wrappers
- Row-level security enforcement
- RPC calls
- Storage operations
"""

from typing import List, Dict, Any, Optional
import os
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# TENANT DB configuration - check multiple naming conventions
# Priority: SUPABASE_* > yTEST_YACHT_001_* (Render convention)
SUPABASE_URL = (
    os.getenv('SUPABASE_URL') or
    os.getenv('yTEST_YACHT_001_SUPABASE_URL') or
    ''
)
SUPABASE_SERVICE_KEY = (
    os.getenv('SUPABASE_SERVICE_KEY') or
    os.getenv('yTEST_YACHT_001_SUPABASE_SERVICE_KEY') or
    ''
)

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    # Don't raise at import time - allow partial startup for health checks
    import logging
    logging.getLogger(__name__).warning(
        'Missing Supabase configuration (SUPABASE_URL/SUPABASE_SERVICE_KEY or '
        'yTEST_YACHT_001_SUPABASE_URL/yTEST_YACHT_001_SUPABASE_SERVICE_KEY)'
    )

# ============================================================================
# SUPABASE CLIENT (Default Tenant)
# ============================================================================

_supabase_client: Optional[Client] = None
_supabase_client_errors: int = 0


def get_supabase_client(force_new: bool = False) -> Optional[Client]:
    """
    Get or create default tenant Supabase client (singleton) with connection recovery.

    Uses SERVICE_KEY for backend operations. If the client is stale (>3 consecutive
    errors), it recreates the connection to handle pool exhaustion and timeout issues.

    HARDENED: 5-second timeout ensures blocking I/O doesn't hang forever.
    Combined with asyncio.wait_for in pipeline_service.py for defense in depth.

    Returns:
        Supabase Client or None if credentials are missing
    """
    global _supabase_client, _supabase_client_errors

    # Force recreation if too many errors (connection might be stale)
    if _supabase_client_errors >= 3:
        logger.warning(f"[Supabase] Resetting client after {_supabase_client_errors} consecutive errors")
        _supabase_client = None
        _supabase_client_errors = 0
        force_new = True

    if _supabase_client is None or force_new:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            logger.warning("[Supabase] Missing credentials - client unavailable")
            return None

        try:
            # Import here to avoid circular dependency
            from supabase.lib.client_options import ClientOptions

            # 5-second HTTP timeout prevents hung connections
            # This is defense-in-depth alongside asyncio.wait_for(timeout=3s)
            options = ClientOptions(postgrest_client_timeout=5)
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, options=options)
            _supabase_client_errors = 0  # Reset error count on successful creation
            logger.info("[Supabase] Default client created successfully")
        except Exception as e:
            logger.error(f"[Supabase] Failed to create client: {e}")
            return None

    return _supabase_client


def mark_supabase_error() -> None:
    """Track consecutive Supabase errors for connection recovery."""
    global _supabase_client_errors
    _supabase_client_errors += 1
    logger.warning(f"[Supabase] Error count: {_supabase_client_errors}")


def reset_supabase_error_count() -> None:
    """Reset error count after successful operation."""
    global _supabase_client_errors
    if _supabase_client_errors > 0:
        _supabase_client_errors = 0


# ============================================================================
# TENANT CLIENT FACTORY (Per-Yacht DB Routing)
# ============================================================================

_tenant_clients: Dict[str, Client] = {}


def get_tenant_client(tenant_key_alias: str) -> Client:
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

    tenant_url = os.getenv(url_key)
    tenant_service_key = os.getenv(key_key)

    if not tenant_url or not tenant_service_key:
        logger.error(f"[TenantClient] Missing credentials for {tenant_key_alias}")
        logger.error(f"[TenantClient] Expected env vars: {url_key}, {key_key}")
        raise ValueError(f'Missing credentials for tenant {tenant_key_alias}')

    try:
        from supabase.lib.client_options import ClientOptions

        # 5-second HTTP timeout for tenant clients as well
        options = ClientOptions(postgrest_client_timeout=5)
        client = create_client(tenant_url, tenant_service_key, options=options)
        _tenant_clients[tenant_key_alias] = client
        logger.info(f"[TenantClient] Created client for {tenant_key_alias}")
        return client
    except Exception as e:
        logger.error(f"[TenantClient] Failed to create client for {tenant_key_alias}: {e}")
        raise


# ============================================================================
# VECTOR SEARCH
# ============================================================================

async def vector_search(
    yacht_id: str,
    query_embedding: List[float],
    table: str = 'document_chunks',
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Perform vector similarity search using pgvector.

    Args:
        yacht_id: Yacht ID for isolation
        query_embedding: Query vector (1536 dimensions)
        table: Table to search (document_chunks, celeste_chunks, etc.)
        limit: Max results
        filters: Additional filters (equipment_id, document_type, etc.)

    Returns:
        List of results sorted by similarity
    """
    supabase = get_supabase_client()

    try:
        # Build RPC call for vector search
        # This assumes a Supabase RPC function exists: match_documents
        params = {
            'yacht_id': yacht_id,
            'query_embedding': query_embedding,
            'match_threshold': 0.7,
            'match_count': limit,
        }

        if filters:
            params.update(filters)

        response = supabase.rpc('match_documents', params).execute()

        return response.data or []

    except Exception as e:
        logger.error(f'Vector search failed: {e}')
        raise


# ============================================================================
# EQUIPMENT QUERIES
# ============================================================================

async def get_equipment(yacht_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all equipment for yacht.
    """
    supabase = get_supabase_client()

    response = supabase.table('equipment') \
        .select('*') \
        .eq('yacht_id', yacht_id) \
        .execute()

    return response.data or []


async def get_equipment_by_id(yacht_id: str, equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch equipment by ID with yacht isolation.
    """
    supabase = get_supabase_client()

    response = supabase.table('equipment') \
        .select('*') \
        .eq('id', equipment_id) \
        .eq('yacht_id', yacht_id) \
        .single() \
        .execute()

    return response.data


# ============================================================================
# WORK ORDER QUERIES
# ============================================================================

async def get_work_orders(
    yacht_id: str,
    status: Optional[str] = None,
    equipment_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Fetch work orders with pagination.
    """
    supabase = get_supabase_client()

    query = supabase.table('work_orders') \
        .select('*', count='exact') \
        .eq('yacht_id', yacht_id)

    if status:
        query = query.eq('status', status)

    if equipment_id:
        query = query.eq('equipment_id', equipment_id)

    response = query.range(offset, offset + limit - 1).execute()

    return {
        'data': response.data or [],
        'count': response.count or 0,
    }


async def create_work_order(yacht_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create work order.
    """
    supabase = get_supabase_client()

    data['yacht_id'] = yacht_id

    response = supabase.table('work_orders') \
        .insert(data) \
        .execute()

    return response.data[0] if response.data else {}


# ============================================================================
# FAULT QUERIES
# ============================================================================

async def get_faults(
    yacht_id: str,
    equipment_id: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Fetch faults with pagination.
    """
    supabase = get_supabase_client()

    query = supabase.table('faults') \
        .select('*', count='exact') \
        .eq('yacht_id', yacht_id)

    if equipment_id:
        query = query.eq('equipment_id', equipment_id)

    if resolved is not None:
        query = query.eq('resolved', resolved)

    response = query.range(offset, offset + limit - 1).execute()

    return {
        'data': response.data or [],
        'count': response.count or 0,
    }


# ============================================================================
# PARTS & INVENTORY QUERIES
# ============================================================================

async def get_parts(
    yacht_id: str,
    category: Optional[str] = None,
    equipment_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Fetch parts with pagination.
    """
    supabase = get_supabase_client()

    query = supabase.table('parts') \
        .select('*', count='exact') \
        .eq('yacht_id', yacht_id)

    if category:
        query = query.eq('category', category)

    if equipment_id:
        query = query.contains('compatible_equipment', [equipment_id])

    response = query.range(offset, offset + limit - 1).execute()

    return {
        'data': response.data or [],
        'count': response.count or 0,
    }


async def get_low_stock_parts(yacht_id: str) -> List[Dict[str, Any]]:
    """
    Fetch parts with stock below minimum.
    """
    supabase = get_supabase_client()

    # This uses a Supabase view or RPC function
    response = supabase.rpc('get_low_stock_parts', {
        'yacht_id': yacht_id
    }).execute()

    return response.data or []


# ============================================================================
# PREDICTIVE MAINTENANCE QUERIES
# ============================================================================

async def get_predictive_state(yacht_id: str) -> List[Dict[str, Any]]:
    """
    Fetch predictive state for all equipment.
    """
    supabase = get_supabase_client()

    response = supabase.table('predictive_state') \
        .select('*') \
        .eq('yacht_id', yacht_id) \
        .order('risk_score', desc=True) \
        .execute()

    return response.data or []


async def get_equipment_predictive_state(
    yacht_id: str,
    equipment_id: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch predictive state for specific equipment.
    """
    supabase = get_supabase_client()

    response = supabase.table('predictive_state') \
        .select('*') \
        .eq('yacht_id', yacht_id) \
        .eq('equipment_id', equipment_id) \
        .single() \
        .execute()

    return response.data


# ============================================================================
# HANDOVER QUERIES
# ============================================================================

async def get_handovers(yacht_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all handovers for yacht.
    """
    supabase = get_supabase_client()

    response = supabase.table('handovers') \
        .select('*') \
        .eq('yacht_id', yacht_id) \
        .order('created_at', desc=True) \
        .execute()

    return response.data or []


async def create_handover(yacht_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create handover.
    """
    supabase = get_supabase_client()

    data['yacht_id'] = yacht_id

    response = supabase.table('handovers') \
        .insert(data) \
        .execute()

    return response.data[0] if response.data else {}


async def add_handover_item(
    yacht_id: str,
    handover_id: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add item to handover.
    """
    supabase = get_supabase_client()

    # Verify handover belongs to yacht
    handover = supabase.table('handovers') \
        .select('yacht_id') \
        .eq('id', handover_id) \
        .single() \
        .execute()

    if not handover.data or handover.data['yacht_id'] != yacht_id:
        raise ValueError('Handover not found or access denied')

    data['handover_id'] = handover_id

    response = supabase.table('handover_items') \
        .insert(data) \
        .execute()

    return response.data[0] if response.data else {}


# ============================================================================
# DOCUMENT QUERIES
# ============================================================================

async def get_documents(
    yacht_id: str,
    source: Optional[str] = None,
    indexed: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Fetch documents with pagination.
    """
    supabase = get_supabase_client()

    query = supabase.table('documents') \
        .select('*', count='exact') \
        .eq('yacht_id', yacht_id)

    if source:
        query = query.eq('source', source)

    if indexed is not None:
        query = query.eq('indexed', indexed)

    response = query.range(offset, offset + limit - 1).execute()

    return {
        'data': response.data or [],
        'count': response.count or 0,
    }


async def insert_document(yacht_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert document metadata.
    """
    supabase = get_supabase_client()

    data['yacht_id'] = yacht_id

    response = supabase.table('documents') \
        .insert(data) \
        .execute()

    return response.data[0] if response.data else {}


async def mark_document_indexed(document_id: str) -> None:
    """
    Mark document as indexed.
    """
    supabase = get_supabase_client()

    supabase.table('documents') \
        .update({'indexed': True, 'indexed_at': 'NOW()'}) \
        .eq('id', document_id) \
        .execute()


# ============================================================================
# STORAGE OPERATIONS
# ============================================================================

async def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """
    Get signed URL for object storage.

    Args:
        bucket: Storage bucket name
        path: Object path
        expires_in: URL expiration in seconds

    Returns:
        Signed URL
    """
    supabase = get_supabase_client()

    response = supabase.storage.from_(bucket).create_signed_url(path, expires_in)

    return response['signedURL']


async def upload_to_storage(
    bucket: str,
    path: str,
    file_data: bytes,
    content_type: str = 'application/octet-stream'
) -> str:
    """
    Upload file to Supabase storage.

    Returns storage path.
    """
    supabase = get_supabase_client()

    supabase.storage.from_(bucket).upload(
        path,
        file_data,
        {
            'content-type': content_type,
            'upsert': 'false'
        }
    )

    return path


# ============================================================================
# EVENT LOGGING
# ============================================================================

async def log_event(
    yacht_id: str,
    event_type: str,
    user_id: Optional[str],
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log event to event_logs table.
    """
    supabase = get_supabase_client()

    supabase.table('event_logs').insert({
        'yacht_id': yacht_id,
        'event_type': event_type,
        'user_id': user_id,
        'data': data or {},
    }).execute()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'get_supabase_client',
    'get_tenant_client',
    'mark_supabase_error',
    'reset_supabase_error_count',
    'vector_search',
    'get_equipment',
    'get_equipment_by_id',
    'get_work_orders',
    'create_work_order',
    'get_faults',
    'get_parts',
    'get_low_stock_parts',
    'get_predictive_state',
    'get_equipment_predictive_state',
    'get_handovers',
    'create_handover',
    'add_handover_item',
    'get_documents',
    'insert_document',
    'mark_document_indexed',
    'get_signed_url',
    'upload_to_storage',
    'log_event',
]
