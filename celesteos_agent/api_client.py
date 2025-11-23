"""
CelesteOS Cloud API Client.
Handles all communication with cloud ingestion endpoints.
"""

import requests
from typing import Dict, Any, Optional
from pathlib import Path
from .logger import get_logger

logger = get_logger(__name__)


class APIClient:
    """Client for CelesteOS Cloud API (Supabase compatible)."""

    def __init__(
        self,
        api_endpoint: str,
        yacht_signature: str,
        supabase_service_key: Optional[str] = None,
        timeout: int = 300,
        verify_ssl: bool = True
    ):
        """Initialize API client.

        Args:
            api_endpoint: Base API URL (Supabase URL)
            yacht_signature: Yacht signature for authentication
            supabase_service_key: Supabase service role key for auth
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
        """
        self.api_endpoint = api_endpoint.rstrip('/')
        self.yacht_signature = yacht_signature
        self.supabase_service_key = supabase_service_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        self.session = requests.Session()

        # Set headers for both yacht signature and Supabase auth
        headers = {
            'X-Yacht-Signature': yacht_signature,
            'User-Agent': 'CelesteOS-Agent/1.0'
        }

        # Add Supabase authentication if provided
        if supabase_service_key:
            headers['Authorization'] = f'Bearer {supabase_service_key}'
            headers['apikey'] = supabase_service_key
            logger.info("Supabase authentication configured")

        self.session.headers.update(headers)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to API.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.)
            endpoint: API endpoint path
            json_data: Optional JSON data
            data: Optional raw bytes data
            headers: Optional additional headers

        Returns:
            Response JSON

        Raises:
            requests.RequestException: On network/API errors
        """
        url = f"{self.api_endpoint}{endpoint}"

        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)

        try:
            logger.debug(f"{method} {url}")

            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                data=data,
                headers=request_headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )

            response.raise_for_status()

            # Return JSON if available
            if response.content:
                return response.json()
            else:
                return {}

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {url}")
            raise

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code}: {url}")
            logger.error(f"Response: {e.response.text}")
            raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {url} - {e}")
            raise

    # ========================================
    # Ingestion API
    # ========================================

    def init_upload(
        self,
        filename: str,
        sha256: str,
        size_bytes: int,
        source: str = "nas"
    ) -> Dict[str, Any]:
        """Initialize file upload.

        POST /functions/v1/ingest/init (Supabase Edge Function)

        Args:
            filename: Original filename
            sha256: File SHA256 hash
            size_bytes: File size in bytes
            source: Source type (default: "nas")

        Returns:
            Response dict with upload_id, storage_key, expected_chunks

        Example response:
            {
                "upload_id": "uuid",
                "storage_key": "yachts/<yacht_id>/temp/<upload_id>/",
                "expected_chunks": 17
            }
        """
        logger.info(f"Initializing upload: {filename} ({size_bytes} bytes)")

        # Use Supabase Edge Functions format
        endpoint = '/functions/v1/ingest-init'

        response = self._make_request(
            method='POST',
            endpoint=endpoint,
            json_data={
                'filename': filename,
                'sha256': sha256,
                'size_bytes': size_bytes,
                'source': source
            }
        )

        logger.info(f"Upload initialized: upload_id={response.get('upload_id')}")

        return response

    def upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        chunk_sha256: str,
        chunk_data: bytes
    ) -> Dict[str, Any]:
        """Upload a file chunk.

        PATCH /functions/v1/ingest-upload-chunk (Supabase Edge Function)

        Args:
            upload_id: Upload ID from init_upload
            chunk_index: Chunk index (0-based)
            chunk_sha256: Chunk SHA256 hash
            chunk_data: Chunk bytes (compressed)

        Returns:
            Response dict (typically {"status": "ok"})
        """
        logger.debug(
            f"Uploading chunk {chunk_index} for upload {upload_id} "
            f"({len(chunk_data)} bytes)"
        )

        # Use Supabase Edge Functions format
        endpoint = '/functions/v1/ingest-upload-chunk'

        response = self._make_request(
            method='PATCH',
            endpoint=endpoint,
            data=chunk_data,
            headers={
                'Content-Type': 'application/octet-stream',
                'Upload-ID': upload_id,
                'Chunk-Index': str(chunk_index),
                'Chunk-SHA256': chunk_sha256
            }
        )

        logger.debug(f"Chunk {chunk_index} uploaded successfully")

        return response

    def complete_upload(
        self,
        upload_id: str,
        total_chunks: int,
        sha256: str,
        filename: str
    ) -> Dict[str, Any]:
        """Complete file upload and trigger indexing.

        POST /functions/v1/ingest-complete (Supabase Edge Function)

        Args:
            upload_id: Upload ID from init_upload
            total_chunks: Total number of chunks uploaded
            sha256: Original file SHA256
            filename: Original filename

        Returns:
            Response dict with document_id, status, queued_for_indexing

        Example response:
            {
                "document_id": "uuid",
                "status": "received",
                "queued_for_indexing": true
            }
        """
        logger.info(
            f"Completing upload {upload_id}: "
            f"{filename} ({total_chunks} chunks)"
        )

        # Use Supabase Edge Functions format
        endpoint = '/functions/v1/ingest-complete'

        response = self._make_request(
            method='POST',
            endpoint=endpoint,
            json_data={
                'upload_id': upload_id,
                'total_chunks': total_chunks,
                'sha256': sha256,
                'filename': filename
            }
        )

        logger.info(
            f"Upload completed: document_id={response.get('document_id')}, "
            f"queued={response.get('queued_for_indexing')}"
        )

        return response

    # ========================================
    # Health & Status
    # ========================================

    def health_check(self) -> Dict[str, Any]:
        """Check API health.

        GET /v1/health

        Returns:
            Health status dict
        """
        return self._make_request(method='GET', endpoint='/v1/health')

    def ping(self) -> bool:
        """Ping API to check connectivity.

        Returns:
            True if API is reachable
        """
        try:
            response = self.health_check()
            return response.get('status') == 'ok'
        except Exception as e:
            logger.warning(f"API ping failed: {e}")
            return False

    # ========================================
    # Agent Management (Future)
    # ========================================

    def check_update(self) -> Optional[Dict[str, Any]]:
        """Check for agent updates.

        POST /v1/agent/check-update

        Returns:
            Update info if available, None otherwise
        """
        try:
            response = self._make_request(
                method='POST',
                endpoint='/v1/agent/check-update',
                json_data={
                    'current_version': '1.0.0',
                    'platform': 'macos'
                }
            )
            return response if response.get('version') else None
        except Exception as e:
            logger.warning(f"Update check failed: {e}")
            return None

    def close(self) -> None:
        """Close HTTP session."""
        self.session.close()


class RetryableAPIClient(APIClient):
    """API client with automatic retry logic (Supabase compatible)."""

    def __init__(
        self,
        api_endpoint: str,
        yacht_signature: str,
        supabase_service_key: Optional[str] = None,
        timeout: int = 300,
        verify_ssl: bool = True,
        max_retries: int = 3,
        retry_delays: list = None
    ):
        """Initialize retryable API client.

        Args:
            api_endpoint: Base API URL (Supabase URL)
            yacht_signature: Yacht signature
            supabase_service_key: Supabase service role key
            timeout: Request timeout
            verify_ssl: Verify SSL
            max_retries: Maximum retry attempts
            retry_delays: List of retry delays in seconds
        """
        super().__init__(api_endpoint, yacht_signature, supabase_service_key, timeout, verify_ssl)

        self.max_retries = max_retries
        self.retry_delays = retry_delays or [5, 10, 30]

    def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make request with retry logic.

        Args:
            Same as _make_request

        Returns:
            Response JSON

        Raises:
            requests.RequestException: After all retries exhausted
        """
        import time

        last_error = None

        for attempt in range(self.max_retries):
            try:
                return self._make_request(method, endpoint, json_data, data, headers)

            except requests.exceptions.RequestException as e:
                last_error = e

                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Request failed after {self.max_retries} attempts: {e}"
                    )

        raise last_error

    def upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        chunk_sha256: str,
        chunk_data: bytes
    ) -> Dict[str, Any]:
        """Upload chunk with retry (Supabase Edge Function)."""
        return self._make_request_with_retry(
            method='PATCH',
            endpoint='/functions/v1/ingest-upload-chunk',
            data=chunk_data,
            headers={
                'Content-Type': 'application/octet-stream',
                'Upload-ID': upload_id,
                'Chunk-Index': str(chunk_index),
                'Chunk-SHA256': chunk_sha256
            }
        )
