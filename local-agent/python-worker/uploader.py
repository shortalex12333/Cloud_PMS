"""
CelesteOS Local Agent - Cloud Uploader
Handles chunked file uploads to cloud with retry logic
"""

import os
import time
import logging
import requests
from typing import Optional, Dict, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class UploadError(Exception):
    """Base exception for upload errors"""
    pass


class AuthenticationError(UploadError):
    """Authentication/authorization errors"""
    pass


class NetworkError(UploadError):
    """Network-related errors"""
    pass


class ValidationError(UploadError):
    """Validation errors (SHA256 mismatch, etc.)"""
    pass


class CloudUploader:
    """
    Handles uploading files to CelesteOS cloud using three-phase protocol:
    1. POST /v1/ingest/init - Initialize upload session
    2. PATCH /v1/ingest/upload_chunk - Upload each chunk
    3. POST /v1/ingest/complete - Complete upload
    """

    def __init__(self,
                 api_endpoint: str,
                 yacht_signature: str,
                 auth_token: str,
                 max_retries: int = 5,
                 initial_retry_delay: float = 30.0,
                 timeout: int = 300):
        """
        Initialize cloud uploader.

        Args:
            api_endpoint: Cloud API base URL (e.g., https://api.celesteos.com)
            yacht_signature: Yacht signature for authentication
            auth_token: JWT access token
            max_retries: Maximum retry attempts for failed uploads
            initial_retry_delay: Initial delay for exponential backoff (seconds)
            timeout: Request timeout in seconds
        """
        self.api_endpoint = api_endpoint.rstrip('/')
        self.yacht_signature = yacht_signature
        self.auth_token = auth_token
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.timeout = timeout

        logger.info(f"CloudUploader initialized: endpoint={api_endpoint}")

    def _get_headers(self, additional_headers: Optional[Dict] = None) -> Dict:
        """
        Get standard request headers.

        Args:
            additional_headers: Optional extra headers

        Returns:
            Headers dict
        """
        headers = {
            'X-Yacht-Signature': self.yacht_signature,
            'Authorization': f'Bearer {self.auth_token}',
            'User-Agent': 'CelesteOS-LocalAgent/1.0'
        }

        if additional_headers:
            headers.update(additional_headers)

        return headers

    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute a function with exponential backoff retry logic.

        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        delay = self.initial_retry_delay
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except (NetworkError, requests.exceptions.RequestException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                                 f"Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(f"All {self.max_retries} attempts failed")

        raise last_exception

    def init_upload(self,
                    filename: str,
                    file_size: int,
                    file_sha256: str,
                    total_chunks: int,
                    mime_type: Optional[str] = None,
                    source_type: str = 'nas',
                    source_path: Optional[str] = None,
                    nas_path: Optional[str] = None,
                    document_type: Optional[str] = None) -> str:
        """
        Initialize upload session (Phase 1).

        Args:
            filename: Original filename
            file_size: File size in bytes
            file_sha256: SHA256 hash of file
            total_chunks: Total number of chunks
            mime_type: MIME type
            source_type: Source type ('nas', 'mobile_upload', etc.)
            source_path: Source path
            nas_path: NAS path
            document_type: Document type hint

        Returns:
            upload_id (UUID string)

        Raises:
            UploadError: If initialization fails
        """
        url = f"{self.api_endpoint}/v1/ingest/init"

        payload = {
            'filename': filename,
            'file_size': file_size,
            'file_sha256': file_sha256,
            'total_chunks': total_chunks,
            'mime_type': mime_type,
            'source_type': source_type,
            'source_path': source_path,
            'nas_path': nas_path,
            'document_type': document_type
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        headers = self._get_headers({'Content-Type': 'application/json'})

        logger.info(f"Initializing upload: {filename} ({file_size} bytes, {total_chunks} chunks)")

        def _do_request():
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)

                if response.status_code == 201:
                    # Success
                    data = response.json()
                    upload_id = data.get('upload_id')

                    if not upload_id:
                        raise UploadError("No upload_id in response")

                    logger.info(f"Upload initialized: upload_id={upload_id}")
                    return upload_id

                elif response.status_code == 200:
                    # File already exists (duplicate)
                    data = response.json()
                    if data.get('status') == 'duplicate':
                        document_id = data.get('document_id')
                        logger.info(f"File already exists: document_id={document_id}")
                        raise ValidationError(f"Duplicate file: {document_id}")

                elif response.status_code in (401, 403):
                    # Authentication error
                    raise AuthenticationError(f"Auth failed: {response.status_code} - {response.text}")

                else:
                    # Other error
                    raise UploadError(f"Init failed: {response.status_code} - {response.text}")

            except requests.exceptions.Timeout:
                raise NetworkError("Request timeout")
            except requests.exceptions.ConnectionError as e:
                raise NetworkError(f"Connection error: {e}")
            except requests.exceptions.RequestException as e:
                raise NetworkError(f"Request error: {e}")

        return self._retry_with_backoff(_do_request)

    def upload_chunk(self,
                     upload_id: str,
                     chunk_index: int,
                     chunk_path: str,
                     chunk_sha256: str) -> bool:
        """
        Upload a single chunk (Phase 2).

        Args:
            upload_id: Upload session ID from init
            chunk_index: Chunk index (0-based)
            chunk_path: Path to chunk file
            chunk_sha256: SHA256 hash of chunk

        Returns:
            True if successful

        Raises:
            UploadError: If upload fails
        """
        url = f"{self.api_endpoint}/v1/ingest/upload_chunk"

        if not os.path.exists(chunk_path):
            raise FileNotFoundError(f"Chunk file not found: {chunk_path}")

        chunk_size = os.path.getsize(chunk_path)

        headers = self._get_headers({
            'Content-Type': 'application/octet-stream',
            'Upload-ID': upload_id,
            'Chunk-Index': str(chunk_index),
            'Chunk-SHA256': chunk_sha256
        })

        logger.debug(f"Uploading chunk {chunk_index}: {chunk_size} bytes, hash={chunk_sha256[:16]}...")

        def _do_request():
            try:
                with open(chunk_path, 'rb') as chunk_file:
                    chunk_data = chunk_file.read()

                response = requests.patch(url, data=chunk_data, headers=headers, timeout=self.timeout)

                if response.status_code == 200:
                    # Success
                    data = response.json()
                    verified = data.get('verified', False)

                    if not verified:
                        raise ValidationError(f"Chunk {chunk_index} verification failed")

                    logger.debug(f"Chunk {chunk_index} uploaded and verified")
                    return True

                elif response.status_code in (401, 403):
                    raise AuthenticationError(f"Auth failed: {response.status_code}")

                elif response.status_code == 400:
                    # SHA256 mismatch or other validation error
                    raise ValidationError(f"Chunk validation failed: {response.text}")

                elif response.status_code == 404:
                    raise UploadError(f"Upload session not found: {upload_id}")

                else:
                    raise UploadError(f"Chunk upload failed: {response.status_code} - {response.text}")

            except requests.exceptions.Timeout:
                raise NetworkError("Chunk upload timeout")
            except requests.exceptions.ConnectionError as e:
                raise NetworkError(f"Connection error: {e}")
            except requests.exceptions.RequestException as e:
                raise NetworkError(f"Request error: {e}")

        return self._retry_with_backoff(_do_request)

    def complete_upload(self, upload_id: str) -> Dict:
        """
        Complete upload session (Phase 3).

        Args:
            upload_id: Upload session ID

        Returns:
            Dict with completion data (document_id, sha256, etc.)

        Raises:
            UploadError: If completion fails
        """
        url = f"{self.api_endpoint}/v1/ingest/complete"

        payload = {
            'upload_id': upload_id
        }

        headers = self._get_headers({'Content-Type': 'application/json'})

        logger.info(f"Completing upload: upload_id={upload_id}")

        def _do_request():
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)

                if response.status_code == 200:
                    # Success
                    data = response.json()
                    document_id = data.get('document_id')

                    if not document_id:
                        raise UploadError("No document_id in completion response")

                    logger.info(f"Upload completed: document_id={document_id}")
                    return data

                elif response.status_code in (401, 403):
                    raise AuthenticationError(f"Auth failed: {response.status_code}")

                elif response.status_code == 400:
                    # Incomplete upload or validation error
                    raise ValidationError(f"Upload incomplete or invalid: {response.text}")

                elif response.status_code == 404:
                    raise UploadError(f"Upload session not found: {upload_id}")

                else:
                    raise UploadError(f"Completion failed: {response.status_code} - {response.text}")

            except requests.exceptions.Timeout:
                raise NetworkError("Completion request timeout")
            except requests.exceptions.ConnectionError as e:
                raise NetworkError(f"Connection error: {e}")
            except requests.exceptions.RequestException as e:
                raise NetworkError(f"Request error: {e}")

        return self._retry_with_backoff(_do_request)

    def upload_file_with_chunks(self,
                                file_path: str,
                                file_sha256: str,
                                chunks: List[Dict],
                                nas_path: Optional[str] = None,
                                document_type: Optional[str] = None,
                                progress_callback=None) -> Dict:
        """
        Complete file upload workflow (init -> upload chunks -> complete).

        Args:
            file_path: Path to source file
            file_sha256: SHA256 hash of file
            chunks: List of chunk metadata dicts
            nas_path: NAS path
            document_type: Document type hint
            progress_callback: Optional callback(chunk_index, total_chunks)

        Returns:
            Dict with upload result

        Raises:
            UploadError: If upload fails
        """
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        total_chunks = len(chunks)

        logger.info(f"Starting upload workflow for {filename}")

        try:
            # Phase 1: Initialize
            upload_id = self.init_upload(
                filename=filename,
                file_size=file_size,
                file_sha256=file_sha256,
                total_chunks=total_chunks,
                source_type='nas',
                nas_path=nas_path,
                document_type=document_type
            )

            # Phase 2: Upload chunks
            for chunk in chunks:
                chunk_index = chunk['chunk_index']
                chunk_path = chunk['chunk_path']
                chunk_sha256 = chunk['chunk_sha256']

                self.upload_chunk(upload_id, chunk_index, chunk_path, chunk_sha256)

                if progress_callback:
                    progress_callback(chunk_index + 1, total_chunks)

            # Phase 3: Complete
            result = self.complete_upload(upload_id)

            logger.info(f"Upload workflow complete: {filename} -> {result['document_id']}")

            return {
                'success': True,
                'upload_id': upload_id,
                'document_id': result['document_id'],
                'sha256': file_sha256,
                'filename': filename
            }

        except ValidationError as e:
            # Duplicate file - not an error
            logger.info(f"File already exists: {e}")
            return {
                'success': True,
                'duplicate': True,
                'message': str(e)
            }

        except Exception as e:
            logger.error(f"Upload workflow failed for {filename}: {e}")
            raise


class TokenManager:
    """
    Manages JWT token refresh.
    """

    def __init__(self, api_endpoint: str, yacht_signature: str,
                 refresh_token: str, on_token_refresh=None):
        """
        Initialize token manager.

        Args:
            api_endpoint: API base URL
            yacht_signature: Yacht signature
            refresh_token: Refresh token
            on_token_refresh: Callback when token refreshed
        """
        self.api_endpoint = api_endpoint.rstrip('/')
        self.yacht_signature = yacht_signature
        self.refresh_token = refresh_token
        self.on_token_refresh = on_token_refresh

        self.access_token = None
        self.token_expiry = None

    def get_valid_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If token refresh fails
        """
        if self._needs_refresh():
            self._refresh_tokens()

        return self.access_token

    def _needs_refresh(self) -> bool:
        """Check if token needs refresh"""
        if not self.access_token or not self.token_expiry:
            return True

        # Refresh if token expires in less than 2 hours
        from datetime import datetime, timedelta
        threshold = datetime.now() + timedelta(hours=2)
        return self.token_expiry < threshold

    def _refresh_tokens(self):
        """Refresh access token"""
        url = f"{self.api_endpoint}/v1/auth/refresh"

        payload = {
            'refresh_token': self.refresh_token,
            'yacht_signature': self.yacht_signature
        }

        try:
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                self.access_token = data['access_token']

                # Parse expiry (assume 24h from now)
                from datetime import datetime, timedelta
                self.token_expiry = datetime.now() + timedelta(hours=24)

                logger.info("Access token refreshed")

                if self.on_token_refresh:
                    self.on_token_refresh(self.access_token)

            else:
                raise AuthenticationError(f"Token refresh failed: {response.status_code}")

        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Token refresh error: {e}")
