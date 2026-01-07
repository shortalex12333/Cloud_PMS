"""
CelesteOS Backend - Search Engine Integration

Handles calls from Cloud API to Search Engine microservice.

Architecture:
Cloud API → Search Engine (Python/Render) → Supabase

The Cloud API acts as a gateway and adds JWT validation.
"""

from typing import Dict, Any, Optional, AsyncGenerator
import os
import httpx
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

SEARCH_ENGINE_URL = os.getenv('SEARCH_ENGINE_URL', '')

if not SEARCH_ENGINE_URL:
    logger.warning('SEARCH_ENGINE_URL not configured')

# ============================================================================
# HTTP CLIENT
# ============================================================================

async def get_http_client() -> httpx.AsyncClient:
    """
    Get HTTP client for Search Engine requests.
    """
    return httpx.AsyncClient(
        base_url=SEARCH_ENGINE_URL,
        timeout=30.0
    )


# ============================================================================
# SEARCH ENGINE CALLS
# ============================================================================

async def search(
    yacht_id: str,
    query: str,
    mode: str = 'auto',
    filters: Optional[Dict[str, Any]] = None,
    user_jwt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Forward search query to Search Engine.

    Args:
        yacht_id: Yacht ID for isolation
        query: User search query
        mode: 'auto', 'standard', or 'deep'
        filters: Additional filters
        user_jwt: User JWT token (forwarded for logging)

    Returns:
        Search response with results and actions
    """
    async with await get_http_client() as client:
        try:
            payload = {
                'yacht_id': yacht_id,
                'query': query,
                'mode': mode,
                'filters': filters or {},
            }

            headers = {}
            if user_jwt:
                headers['X-User-JWT'] = user_jwt

            response = await client.post(
                '/v1/search',
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f'Search engine request failed: {e}')
            raise


async def stream_search(
    yacht_id: str,
    query: str,
    mode: str = 'auto',
    filters: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream search results from Search Engine (SSE).

    Yields search result updates as they become available.
    """
    async with await get_http_client() as client:
        try:
            payload = {
                'yacht_id': yacht_id,
                'query': query,
                'mode': mode,
                'filters': filters or {},
                'stream': True,
            }

            async with client.stream('POST', '/v1/search', json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        try:
                            import json
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            logger.warning(f'Failed to parse SSE data: {data}')

        except httpx.HTTPError as e:
            logger.error(f'Search stream failed: {e}')
            raise


# ============================================================================
# ENTITY EXTRACTION
# ============================================================================

async def extract_entities(
    yacht_id: str,
    text: str
) -> Dict[str, Any]:
    """
    Extract entities from text using Search Engine.

    Returns detected:
    - equipment names
    - fault codes
    - part numbers
    - document types
    - intent
    """
    async with await get_http_client() as client:
        try:
            response = await client.post(
                '/v1/entities/extract',
                json={
                    'yacht_id': yacht_id,
                    'text': text,
                }
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f'Entity extraction failed: {e}')
            raise


# ============================================================================
# INTENT DETECTION
# ============================================================================

async def detect_intent(
    yacht_id: str,
    query: str,
    entities: Optional[Dict[str, Any]] = None
) -> str:
    """
    Detect user intent from query.

    Returns one of:
    - diagnose_fault
    - find_document
    - create_work_order
    - add_to_handover
    - find_part
    - general_search
    - predictive_request
    """
    async with await get_http_client() as client:
        try:
            response = await client.post(
                '/v1/intent/detect',
                json={
                    'yacht_id': yacht_id,
                    'query': query,
                    'entities': entities or {},
                }
            )

            response.raise_for_status()
            data = response.json()
            return data.get('intent', 'general_search')

        except httpx.HTTPError as e:
            logger.error(f'Intent detection failed: {e}')
            return 'general_search'


# ============================================================================
# HEALTH CHECK
# ============================================================================

async def health_check() -> Dict[str, Any]:
    """
    Check Search Engine health.
    """
    async with await get_http_client() as client:
        try:
            response = await client.get('/health')
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f'Search engine health check failed: {e}')
            return {'status': 'unhealthy', 'error': str(e)}


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'search',
    'stream_search',
    'extract_entities',
    'detect_intent',
    'health_check',
]