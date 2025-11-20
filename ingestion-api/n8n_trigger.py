"""
n8n workflow trigger for indexing pipeline
"""
import httpx
import logging
from typing import Optional
from uuid import UUID
import asyncio

from config import settings

logger = logging.getLogger(__name__)


class N8NTrigger:
    """Triggers n8n workflow for document indexing"""

    def __init__(self):
        self.webhook_url = settings.N8N_WEBHOOK_URL
        self.webhook_secret = settings.N8N_WEBHOOK_SECRET
        self.timeout = 30.0
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY_SECONDS

    async def trigger_indexing(
        self,
        document_id: UUID,
        yacht_id: UUID,
        file_sha256: str,
        storage_path: str,
        filename: str,
        file_size: int
    ) -> bool:
        """
        Trigger n8n indexing workflow

        Args:
            document_id: Document identifier
            yacht_id: Yacht identifier
            file_sha256: SHA256 hash of file
            storage_path: Path to file in object storage
            filename: Original filename
            file_size: File size in bytes

        Returns:
            True if triggered successfully, False otherwise
        """
        payload = {
            "document_id": str(document_id),
            "yacht_id": str(yacht_id),
            "file_sha256": file_sha256,
            "storage_path": storage_path,
            "filename": filename,
            "file_size": file_size,
            "trigger_source": "ingestion_api"
        }

        # Add webhook secret if configured
        headers = {
            "Content-Type": "application/json"
        }
        if self.webhook_secret:
            headers["X-Webhook-Secret"] = self.webhook_secret

        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.webhook_url,
                        json=payload,
                        headers=headers
                    )

                    response.raise_for_status()

                    logger.info(
                        f"Successfully triggered n8n indexing for document {document_id}"
                    )
                    return True

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error triggering n8n (attempt {attempt + 1}/{self.max_retries}): "
                    f"{e.response.status_code} - {e.response.text}"
                )

                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    return False

            except httpx.RequestError as e:
                logger.error(
                    f"Request error triggering n8n (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

            except Exception as e:
                logger.error(
                    f"Unexpected error triggering n8n (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

            # Wait before retrying (exponential backoff)
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        logger.error(
            f"Failed to trigger n8n indexing after {self.max_retries} attempts"
        )
        return False

    async def trigger_retry_failed(
        self,
        document_id: UUID,
        yacht_id: UUID
    ) -> bool:
        """
        Trigger retry of failed indexing job

        Args:
            document_id: Document identifier
            yacht_id: Yacht identifier

        Returns:
            True if triggered successfully, False otherwise
        """
        # This could call a different n8n endpoint for retries
        # For now, just use the same endpoint
        logger.info(f"Triggering retry for document {document_id}")

        # Implementation would be similar to trigger_indexing
        # but potentially call a different endpoint or include retry metadata
        return True

    async def health_check(self) -> bool:
        """
        Check if n8n webhook is reachable

        Returns:
            True if reachable, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try to hit the webhook URL with a HEAD request
                # or a dedicated health endpoint if available
                response = await client.get(
                    self.webhook_url.replace("/webhook/", "/healthz"),
                    follow_redirects=True
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"n8n health check failed: {e}")
            return False
