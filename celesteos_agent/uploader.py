"""
File uploader for sending binary files to n8n ingestion webhook.
Uploads entire files (not chunks) to cloud for processing.
"""

import json
import time
import hashlib
import os
from typing import Dict, Any, Optional
from pathlib import Path
import requests


class UploadError(Exception):
    """Upload error."""
    pass


class FileUploader:
    """
    Uploads binary files to n8n ingestion webhook.

    Architecture:
        - Local agent uploads BINARY FILES (not chunks)
        - n8n handles chunking, embedding, and GraphRAG
        - SHA256 duplicate detection happens in cloud

    Flow:
        Local File → n8n Webhook → Supabase Storage → doc_metadata
            → n8n Indexing → Chunking → Embeddings → search_document_chunks
            → n8n GraphRAG → Entities → search_graph_nodes/edges/maintenance_facts
    """

    def __init__(
        self,
        webhook_endpoint: str,
        yacht_id: str,
        yacht_salt: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 120
    ):
        """
        Initialize uploader.

        Args:
            webhook_endpoint: n8n webhook base URL (e.g. https://api.celeste7.ai)
            yacht_id: Yacht UUID
            yacht_salt: Salt for yacht signature (HMAC-SHA256)
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds (default 120 for large files)
        """
        self.webhook_endpoint = webhook_endpoint.rstrip('/')
        self.yacht_id = yacht_id
        self.yacht_salt = yacht_salt or os.getenv("YACHT_SALT", "")
        self.max_retries = max_retries
        self.timeout = timeout

    def _generate_yacht_signature(self) -> str:
        """
        Generate yacht signature for authentication.

        Signature = sha256(yacht_id + salt)

        Returns:
            HMAC-SHA256 signature as hex string
        """
        if not self.yacht_salt:
            return ""

        signature_input = f"{self.yacht_id}{self.yacht_salt}"
        return hashlib.sha256(signature_input.encode()).hexdigest()

    def upload_file(
        self,
        file_path: Path,
        system_path: str,
        directories: list,
        doc_type: str,
        system_tag: str
    ) -> Dict[str, Any]:
        """
        Upload binary file to n8n ingestion webhook.

        Args:
            file_path: Path to document (PDF, DOCX, XLSX, etc.)
            system_path: Relative path from NAS root (e.g. "02_Engineering/Electrical")
            directories: Directory hierarchy (e.g. ["02_Engineering", "Electrical"])
            doc_type: Document type (manual, schematic, sop, etc.)
            system_tag: System tag (electrical, hvac, plumbing, etc.)

        Returns:
            {
                "status": "stored" | "duplicate",
                "file": "filename.pdf",
                "storage_path": "yacht-id/system-path/filename.pdf",
                "document_id": "uuid",
                "sha256": "hash" (if stored)
            }

        Raises:
            UploadError: If upload fails after retries
        """
        if not file_path.exists():
            raise UploadError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size

        # Validate file size (max 100MB)
        if file_size > 100 * 1024 * 1024:
            raise UploadError(f"File too large: {file_size:,} bytes (max 100MB)")

        # Prepare multipart form data
        metadata = {
            'yacht_id': self.yacht_id,
            'local_path': str(file_path),
            'filename': file_path.name,
            'content_type': self._get_content_type(file_path),
            'file_size': file_size,
            'system_path': system_path,
            'directories': directories,
            'doc_type': doc_type,
            'system_tag': system_tag
        }

        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()

        files = {
            'file': (file_path.name, file_data, metadata['content_type'])
        }

        data = {
            'data': json.dumps(metadata)
        }

        # Generate yacht signature for authentication
        yacht_signature = self._generate_yacht_signature()

        headers = {
            'X-Yacht-ID': self.yacht_id,
            'X-Yacht-Signature': yacht_signature
        }

        # Upload with retry logic
        url = f"{self.webhook_endpoint}/webhook/ingest-docs-nas-cloud"
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Calculate exponential backoff (if retrying)
                if attempt > 0:
                    backoff_seconds = min(2 ** attempt, 60)  # Max 60s
                    print(f"⏳ Retry {attempt}/{self.max_retries - 1} - waiting {backoff_seconds}s...")
                    time.sleep(backoff_seconds)

                response = requests.post(
                    url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=self.timeout
                )

                # Debug output
                print(f"\n🔍 DEBUG - Upload Response:")
                print(f"   Status Code: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
                print(f"   Response Length: {len(response.text)} bytes")
                print(f"   First 500 chars: {response.text[:500]}")

                if response.status_code == 200:
                    try:
                        result = response.json()
                    except json.JSONDecodeError as e:
                        raise UploadError(f"Invalid JSON response (status 200): {response.text[:500]}")

                    # Validate response
                    if result.get('status') in ['stored', 'duplicate']:
                        return result
                    else:
                        raise UploadError(f"Unexpected response: {result}")

                elif response.status_code == 401:
                    # Unauthorized - missing signature
                    raise UploadError(f"Unauthorized (401): Missing yacht signature - check YACHT_SALT")

                elif response.status_code == 403:
                    # Forbidden - invalid signature (don't retry)
                    raise UploadError(f"Forbidden (403): Invalid yacht signature - check yacht_id and YACHT_SALT")

                elif response.status_code == 413:
                    # File too large (don't retry)
                    raise UploadError(f"File too large (413): {file_size:,} bytes - max 500 MB")

                elif response.status_code == 415:
                    # Unsupported file type (don't retry)
                    raise UploadError(f"Unsupported file type (415): {metadata['content_type']}")

                elif response.status_code == 429:
                    # Rate limited - retry with longer backoff
                    last_error = f"Rate limited (429): Too many requests"
                    backoff_seconds = min(60 * (2 ** attempt), 300)  # Max 5 minutes
                    print(f"⚠️  {last_error} - waiting {backoff_seconds}s...")
                    time.sleep(backoff_seconds)
                    continue

                elif response.status_code >= 500:
                    # Server error, retry
                    last_error = f"Server error {response.status_code}: {response.text[:200]}"
                    print(f"⚠️  {last_error} - will retry")
                    continue

                else:
                    # Other client error, don't retry
                    raise UploadError(f"Upload failed ({response.status_code}): {response.text[:200]}")

            except requests.Timeout:
                last_error = f"Request timeout (>{self.timeout}s)"
                print(f"⚠️  {last_error} - will retry")
                continue

            except requests.ConnectionError as e:
                last_error = f"Connection error: {e}"
                print(f"⚠️  {last_error} - will retry")
                continue

            except UploadError:
                # Re-raise UploadError (don't retry client errors)
                raise

            except requests.RequestException as e:
                last_error = f"Request error: {e}"
                print(f"⚠️  {last_error} - will retry")
                continue

        # All retries exhausted
        raise UploadError(f"Upload failed after {self.max_retries} attempts: {last_error}")

    def _get_content_type(self, file_path: Path) -> str:
        """Determine MIME type from file extension."""
        ext = file_path.suffix.lower()
        mapping = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.json': 'application/json',
        }
        return mapping.get(ext, 'application/octet-stream')


def create_uploader(webhook_endpoint: str, yacht_id: str) -> FileUploader:
    """
    Convenience function to create uploader.

    Args:
        webhook_endpoint: n8n webhook base URL
        yacht_id: Yacht UUID

    Returns:
        FileUploader instance
    """
    return FileUploader(webhook_endpoint, yacht_id)
