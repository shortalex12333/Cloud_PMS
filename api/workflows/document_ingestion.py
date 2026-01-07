"""
Document Ingestion Workflow
Converted from n8n: Ingestion_Docs.json

Flow:
1. Receive file upload + metadata from Local Agent
2. Parse metadata from multipart form
3. Check for duplicate (filename + yacht_id)
4. Upload file to Supabase Storage
5. Insert metadata to doc_metadata table
6. Trigger indexing workflow
7. Respond with success/duplicate status

Endpoint: POST /webhook/ingest-docs-nas-cloud
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from supabase import create_client, Client
import httpx

logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


async def handle_document_ingestion(
    yacht_id: str,
    filename: str,
    content_type: str,
    file_size: int,
    system_path: str,
    directories: list,
    doc_type: str,
    system_tag: str,
    local_path: str,
    file_content: bytes,
    sha256: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handle document ingestion from Local Agent

    Args:
        yacht_id: UUID of yacht uploading document
        filename: Original filename
        content_type: MIME type
        file_size: File size in bytes
        system_path: System classification path
        directories: Directory structure
        doc_type: Document type classification
        system_tag: System tag for categorization
        local_path: Original path on NAS
        file_content: Binary file content
        sha256: SHA-256 hash (optional, for duplicate detection)

    Returns:
        Dict with status, message, and document metadata
    """

    try:
        # Step 1: Check for duplicate
        logger.info(f"Checking for duplicate: {filename} for yacht {yacht_id}")

        duplicate_check = supabase.table("doc_metadata").select("id, filename, indexed, sha256").eq(
            "yacht_id", yacht_id
        ).eq(
            "filename", filename
        ).execute()

        if duplicate_check.data and len(duplicate_check.data) > 0:
            existing_doc = duplicate_check.data[0]
            logger.info(f"Duplicate found: {existing_doc['id']}")
            return {
                "status": "duplicate",
                "message": "File already exists (SHA256 match)",
                "file": filename,
                "document_id": existing_doc["id"],
                "sha256": existing_doc.get("sha256"),
                "indexed": existing_doc.get("indexed", False)
            }

        # Step 2: Upload to Supabase Storage
        storage_path = f"{yacht_id}/{system_path}/{filename}".replace("//", "/")

        logger.info(f"Uploading to storage: documents/{storage_path}")

        try:
            upload_result = supabase.storage.from_("documents").upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": content_type}
            )
            logger.info(f"Upload successful: {storage_path}")
        except Exception as upload_error:
            logger.error(f"Storage upload failed: {upload_error}")
            return {
                "status": "error",
                "message": f"Upload failed: {str(upload_error)}",
                "file": filename
            }

        # Step 3: Build metadata JSONB
        metadata = {
            "directories": directories,
            "upload_timestamp": datetime.utcnow().isoformat(),
            "file_extension": filename.split(".")[-1] if "." in filename else None,
            "department": directories[0] if directories and len(directories) > 0 else None,
            "local_path": local_path
        }

        # Step 4: Insert to doc_metadata table
        insert_data = {
            "yacht_id": yacht_id,
            "source": "nas",
            "original_path": local_path,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": file_size,
            "sha256": sha256,
            "storage_path": f"documents/{storage_path}",
            "system_path": system_path,
            "indexed": False,
            "metadata": metadata,
            "doc_type": doc_type,
            "system_type": system_tag
        }

        logger.info(f"Inserting metadata to doc_metadata table")

        insert_result = supabase.table("doc_metadata").insert(insert_data).execute()

        if not insert_result.data or len(insert_result.data) == 0:
            logger.error("Failed to insert metadata")
            return {
                "status": "error",
                "message": "Failed to insert metadata",
                "file": filename
            }

        document_record = insert_result.data[0]
        document_id = document_record["id"]

        logger.info(f"Document metadata inserted: {document_id}")

        # Step 5: Trigger indexing (async, don't wait for response)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                indexing_payload = {
                    "filename": filename,
                    "content_type": content_type,
                    "storage_path": f"documents/{storage_path}",
                    "document_id": document_id,
                    "yacht_id": yacht_id,
                    "system_tag": system_tag,
                    "doc_type": doc_type
                }

                # Trigger indexing asynchronously (fire and forget)
                indexing_url = os.getenv("INDEXING_ENDPOINT", "https://api.celeste7.ai/webhook/index-documents")
                await client.post(indexing_url, json=indexing_payload)
                logger.info(f"Triggered indexing for document {document_id}")
        except Exception as index_error:
            # Log but don't fail - indexing can happen later
            logger.warning(f"Failed to trigger indexing: {index_error}")

        # Step 6: Return success response
        return {
            "status": "success",
            "message": "Document uploaded successfully",
            "document_id": document_id,
            "filename": filename,
            "storage_path": f"documents/{storage_path}",
            "indexed": False,
            **document_record
        }

    except Exception as error:
        logger.error(f"Document ingestion failed: {error}", exc_info=True)
        return {
            "status": "error",
            "message": str(error),
            "file": filename
        }
