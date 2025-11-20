"""
Supabase client for ingestion API
"""
from supabase import create_client, Client
from functools import lru_cache
from config import settings
import logging

logger = logging.getLogger(__name__)


@lru_cache()
def get_supabase_client() -> Client:
    """Get Supabase client instance"""
    try:
        client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        logger.info("Supabase client created")
        return client
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        raise


async def create_upload_record(
    yacht_id: str,
    filename: str,
    sha256: str,
    size_bytes: int,
    source: str
) -> str:
    """Create upload tracking record"""
    client = get_supabase_client()

    try:
        result = client.table("upload_sessions").insert({
            "yacht_id": yacht_id,
            "filename": filename,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "source": source,
            "status": "uploading",
            "chunks_received": 0
        }).execute()

        return result.data[0]["id"]

    except Exception as e:
        logger.error(f"Failed to create upload record: {e}")
        raise


async def update_chunk_status(
    upload_id: str,
    chunk_index: int,
    chunk_sha256: str
) -> None:
    """Update chunk receipt status"""
    client = get_supabase_client()

    try:
        # Increment chunks_received
        client.rpc("increment_chunks_received", {
            "upload_session_id": upload_id
        }).execute()

        # Record chunk
        client.table("upload_chunks").insert({
            "upload_session_id": upload_id,
            "chunk_index": chunk_index,
            "chunk_sha256": chunk_sha256,
            "status": "received"
        }).execute()

    except Exception as e:
        logger.error(f"Failed to update chunk status: {e}")
        raise


async def complete_upload(upload_id: str, yacht_id: str) -> dict:
    """Mark upload as complete and create document record"""
    client = get_supabase_client()

    try:
        # Get upload session
        session_result = client.table("upload_sessions") \
            .select("*") \
            .eq("id", upload_id) \
            .single() \
            .execute()

        session = session_result.data

        # Create document record
        doc_result = client.table("documents").insert({
            "yacht_id": yacht_id,
            "filename": session["filename"],
            "sha256": session["sha256"],
            "size_bytes": session["size_bytes"],
            "source": session["source"],
            "storage_path": session["storage_path"],
            "indexed": False
        }).execute()

        document_id = doc_result.data[0]["id"]

        # Update session status
        client.table("upload_sessions") \
            .update({"status": "completed"}) \
            .eq("id", upload_id) \
            .execute()

        return {
            "document_id": document_id,
            "filename": session["filename"],
            "storage_path": session["storage_path"]
        }

    except Exception as e:
        logger.error(f"Failed to complete upload: {e}")
        raise


async def get_yacht_signature_info(signature: str) -> dict:
    """Get yacht info from signature"""
    client = get_supabase_client()

    try:
        result = client.table("yachts") \
            .select("id, name") \
            .eq("signature", signature) \
            .single() \
            .execute()

        return result.data

    except Exception as e:
        logger.error(f"Failed to get yacht info: {e}")
        raise
