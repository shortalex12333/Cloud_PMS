"""
Indexing queue service - triggers n8n workflow
"""
import httpx
import logging
from config import settings

logger = logging.getLogger(__name__)


async def trigger_indexing(
    document_id: str,
    yacht_id: str,
    filename: str,
    storage_path: str,
    sha256: str
) -> bool:
    """
    Trigger n8n indexing workflow

    Returns: True if successfully queued
    """
    payload = {
        "document_id": document_id,
        "yacht_id": yacht_id,
        "filename": filename,
        "storage_path": storage_path,
        "sha256": sha256,
        "trigger": "ingestion_complete"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.n8n_webhook_url,
                json=payload,
                timeout=10.0
            )

            if response.status_code == 200:
                logger.info(f"Successfully queued indexing for document {document_id}")
                return True
            else:
                logger.error(
                    f"Failed to queue indexing: HTTP {response.status_code}, "
                    f"body: {response.text}"
                )
                return False

    except Exception as e:
        logger.error(f"Error triggering indexing: {e}")
        return False
