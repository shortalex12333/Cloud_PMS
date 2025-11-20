"""
Supabase client for document management and storage
"""
import logging
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from pathlib import Path
from supabase import create_client, Client

from config import settings
from models import DocumentMetadata, IngestionState

logger = logging.getLogger(__name__)


class SupabaseManager:
    """Manages Supabase operations for document ingestion"""

    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    async def create_document_record(
        self,
        state: IngestionState,
        storage_path: str,
        content_type: Optional[str] = None
    ) -> UUID:
        """
        Create a new document record in the documents table

        Args:
            state: Upload state containing metadata
            storage_path: Path to file in object storage
            content_type: MIME type of the document

        Returns:
            UUID of created document
        """
        document_id = uuid4()

        try:
            data = {
                "id": str(document_id),
                "yacht_id": str(state.yacht_id),
                "source": state.source,
                "original_path": None,  # Not tracked for uploads
                "filename": state.filename,
                "content_type": content_type,
                "size_bytes": state.file_size,
                "sha256": state.file_sha256,
                "storage_path": storage_path,
                "indexed": False,
                "indexed_at": None,
                "status": "ready_for_indexing",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "upload_id": str(state.upload_id),
                    "total_chunks": state.total_chunks,
                    "source": state.source
                }
            }

            result = self.client.table("documents").insert(data).execute()

            if not result.data:
                raise Exception("Failed to create document record")

            logger.info(f"Created document record: {document_id}")
            return document_id

        except Exception as e:
            logger.error(f"Error creating document record: {e}")
            raise

    async def update_document_status(
        self,
        document_id: UUID,
        status: str,
        indexed: bool = False,
        error_message: Optional[str] = None
    ) -> None:
        """Update document status"""
        try:
            data = {
                "status": status,
                "indexed": indexed,
                "updated_at": datetime.utcnow().isoformat()
            }

            if indexed:
                data["indexed_at"] = datetime.utcnow().isoformat()

            if error_message:
                data["metadata"] = {"error": error_message}

            self.client.table("documents").update(data).eq(
                "id", str(document_id)
            ).execute()

            logger.info(f"Updated document {document_id} status to {status}")

        except Exception as e:
            logger.error(f"Error updating document status: {e}")
            raise

    async def upload_to_storage(
        self,
        yacht_id: UUID,
        file_sha256: str,
        filename: str,
        file_path: Path
    ) -> str:
        """
        Upload file to Supabase object storage

        Args:
            yacht_id: Yacht identifier
            file_sha256: SHA256 hash of file
            filename: Original filename
            file_path: Path to file to upload

        Returns:
            Storage path of uploaded file
        """
        try:
            # Construct storage path: yachts/{yacht_id}/raw/{sha256}/{filename}
            storage_path = f"yachts/{yacht_id}/raw/{file_sha256}/{filename}"

            # Read file
            with open(file_path, "rb") as f:
                file_data = f.read()

            # Upload to Supabase storage
            result = self.client.storage.from_(self.bucket).upload(
                path=storage_path,
                file=file_data,
                file_options={
                    "content-type": "application/octet-stream",
                    "x-upsert": "false"  # Don't overwrite if exists
                }
            )

            logger.info(f"Uploaded file to storage: {storage_path}")
            return storage_path

        except Exception as e:
            logger.error(f"Error uploading to storage: {e}")
            raise

    async def log_ingestion_event(
        self,
        yacht_id: UUID,
        upload_id: UUID,
        document_id: Optional[UUID],
        event_type: str,
        status: str,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Log ingestion event to document_ingestion_log table

        Args:
            yacht_id: Yacht identifier
            upload_id: Upload session identifier
            document_id: Document identifier (if created)
            event_type: Type of event (init, chunk, complete, error)
            status: Status of event
            error_message: Error message if any
            metadata: Additional metadata
        """
        try:
            data = {
                "id": str(uuid4()),
                "yacht_id": str(yacht_id),
                "upload_id": str(upload_id),
                "document_id": str(document_id) if document_id else None,
                "event_type": event_type,
                "status": status,
                "error_message": error_message,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            }

            self.client.table("document_ingestion_log").insert(data).execute()

        except Exception as e:
            logger.error(f"Error logging ingestion event: {e}")
            # Don't raise - logging failures shouldn't break the flow

    async def get_yacht_upload_count(
        self,
        yacht_id: UUID,
        minutes: int = 60
    ) -> int:
        """
        Get count of uploads for a yacht in the last N minutes
        Used for rate limiting

        Args:
            yacht_id: Yacht identifier
            minutes: Time window in minutes

        Returns:
            Count of uploads
        """
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=minutes)

            result = self.client.table("document_ingestion_log").select(
                "id", count="exact"
            ).eq(
                "yacht_id", str(yacht_id)
            ).eq(
                "event_type", "init"
            ).gte(
                "created_at", cutoff.isoformat()
            ).execute()

            return result.count or 0

        except Exception as e:
            logger.error(f"Error getting upload count: {e}")
            return 0

    async def check_duplicate_document(
        self,
        yacht_id: UUID,
        file_sha256: str
    ) -> Optional[dict]:
        """
        Check if a document with the same SHA256 already exists

        Args:
            yacht_id: Yacht identifier
            file_sha256: SHA256 hash of file

        Returns:
            Document data if exists, None otherwise
        """
        try:
            result = self.client.table("documents").select("*").eq(
                "yacht_id", str(yacht_id)
            ).eq(
                "sha256", file_sha256
            ).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]

            return None

        except Exception as e:
            logger.error(f"Error checking duplicate document: {e}")
            return None


from datetime import timedelta
