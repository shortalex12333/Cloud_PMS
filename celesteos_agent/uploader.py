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

                elif response.status_code >= 500:
                    # Server error, retry
                    last_error = f"Server error {response.status_code}: {response.text[:200]}"
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue

                else:
                    # Client error, don't retry
                    raise UploadError(f"Upload failed {response.status_code}: {response.text[:200]}")

            except requests.Timeout:
                last_error = f"Request timeout (>{self.timeout}s)"
                time.sleep(2 ** attempt)
                continue

            except requests.RequestException as e:
                last_error = f"Request error: {e}"
                time.sleep(2 ** attempt)
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
