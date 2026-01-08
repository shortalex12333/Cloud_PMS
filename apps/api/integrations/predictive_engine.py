"""
CelesteOS Backend - Predictive Engine Integration

Handles calls from Cloud API to Predictive Maintenance Engine.

Architecture:
Cloud API → Predictive Engine (Python/Render) → Supabase
"""

from typing import Dict, Any, List, Optional
import os
import httpx
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

PREDICTIVE_ENGINE_URL = os.getenv('PREDICTIVE_ENGINE_URL', '')

if not PREDICTIVE_ENGINE_URL:
    logger.warning('PREDICTIVE_ENGINE_URL not configured')

# ============================================================================
# HTTP CLIENT
# ============================================================================

async def get_http_client() -> httpx.AsyncClient:
    """
    Get HTTP client for Predictive Engine requests.
    """
    return httpx.AsyncClient(
        base_url=PREDICTIVE_ENGINE_URL,
        timeout=60.0  # Predictive calculations can take longer
    )


# ============================================================================
# PREDICTIVE STATE
# ============================================================================

async def get_predictive_state(yacht_id: str) -> List[Dict[str, Any]]:
    """
    Get predictive state for all equipment on yacht.

    Returns list of equipment with risk scores and signals.
    """
    async with await get_http_client() as client:
        try:
            response = await client.get(
                '/v1/predictive/state',
                params={'yacht_id': yacht_id}
            )

            response.raise_for_status()
            data = response.json()
            return data.get('data', [])

        except httpx.HTTPError as e:
            logger.error(f'Get predictive state failed: {e}')
            raise


async def get_equipment_predictive_state(
    yacht_id: str,
    equipment_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get predictive state for specific equipment.

    Returns detailed risk analysis with contributing factors.
    """
    async with await get_http_client() as client:
        try:
            response = await client.get(
                f'/v1/predictive/state/{equipment_id}',
                params={'yacht_id': yacht_id}
            )

            response.raise_for_status()
            data = response.json()
            return data.get('data')

        except httpx.HTTPError as e:
            logger.error(f'Get equipment predictive state failed: {e}')
            raise


# ============================================================================
# PREDICTIVE INSIGHTS
# ============================================================================

async def get_predictive_insights(yacht_id: str) -> List[Dict[str, Any]]:
    """
    Get actionable predictive insights.

    Returns list of insights with:
    - equipment_id
    - insight_type (risk, pattern, anomaly, recommendation)
    - severity
    - description
    - confidence
    """
    async with await get_http_client() as client:
        try:
            response = await client.get(
                '/v1/predictive/insights',
                params={'yacht_id': yacht_id}
            )

            response.raise_for_status()
            data = response.json()
            return data.get('data', [])

        except httpx.HTTPError as e:
            logger.error(f'Get predictive insights failed: {e}')
            raise


# ============================================================================
# TRIGGER CALCULATIONS
# ============================================================================

async def trigger_predictive_calculation(
    yacht_id: str,
    equipment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Trigger predictive maintenance calculation.

    Args:
        yacht_id: Yacht to calculate for
        equipment_id: Optional specific equipment (otherwise all equipment)

    Returns:
        Status of calculation job
    """
    async with await get_http_client() as client:
        try:
            payload = {
                'yacht_id': yacht_id,
            }

            if equipment_id:
                payload['equipment_id'] = equipment_id

            response = await client.post(
                '/v1/predictive/calculate',
                json=payload
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f'Trigger predictive calculation failed: {e}')
            raise


# ============================================================================
# SIGNAL ANALYSIS
# ============================================================================

async def analyze_signals(
    yacht_id: str,
    equipment_id: str
) -> Dict[str, Any]:
    """
    Get detailed signal breakdown for equipment.

    Returns:
    - fault_signal
    - work_order_signal
    - crew_activity_signal
    - part_consumption_signal
    - global_knowledge_signal
    """
    async with await get_http_client() as client:
        try:
            response = await client.get(
                f'/v1/predictive/signals/{equipment_id}',
                params={'yacht_id': yacht_id}
            )

            response.raise_for_status()
            data = response.json()
            return data.get('data', {})

        except httpx.HTTPError as e:
            logger.error(f'Analyze signals failed: {e}')
            raise


# ============================================================================
# RISK TRENDS
# ============================================================================

async def get_risk_trends(
    yacht_id: str,
    equipment_id: str,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get risk score trends over time.

    Args:
        yacht_id: Yacht ID
        equipment_id: Equipment ID
        days: Number of days to include

    Returns:
        Time series of risk scores
    """
    async with await get_http_client() as client:
        try:
            response = await client.get(
                f'/v1/predictive/trends/{equipment_id}',
                params={
                    'yacht_id': yacht_id,
                    'days': days,
                }
            )

            response.raise_for_status()
            data = response.json()
            return data.get('data', {})

        except httpx.HTTPError as e:
            logger.error(f'Get risk trends failed: {e}')
            raise


# ============================================================================
# HEALTH CHECK
# ============================================================================

async def health_check() -> Dict[str, Any]:
    """
    Check Predictive Engine health.
    """
    async with await get_http_client() as client:
        try:
            response = await client.get('/health')
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f'Predictive engine health check failed: {e}')
            return {'status': 'unhealthy', 'error': str(e)}


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'get_predictive_state',
    'get_equipment_predictive_state',
    'get_predictive_insights',
    'trigger_predictive_calculation',
    'analyze_signals',
    'get_risk_trends',
    'health_check',
]
