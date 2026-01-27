#!/usr/bin/env python3
"""
Email RAG Idempotency Module (M6.2)

Zero duplicates via content hashing, upsert policy, and prepare job dedupe.

Invariants:
- (yacht_id, provider_message_id) is globally unique
- content_hash enables no-op detection for unchanged messages
- Attachments deduped by SHA256
- Thread aggregates maintained consistently
- Prepare jobs deduped to avoid redundant work

Usage:
    from email_rag.idempotency import IdempotentProcessor, ContentHasher

    processor = IdempotentProcessor(supabase, yacht_id, watcher_id)
    result = await processor.upsert_message(graph_message)
    # result.action in ['inserted', 'updated', 'noop', 'error']
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CONTENT HASH NORMALIZATION
# =============================================================================

class ContentHasher:
    """
    Computes deterministic content hashes for email deduplication.

    Normalization rules:
    - Case-insensitive (lowercase)
    - Whitespace normalized (strip, collapse multiple spaces)
    - Participants sorted (to[], cc[] order-independent)
    - sent_at floored to minute (ignore seconds variance)
    - Empty/None treated as empty string
    """

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Normalize text: lowercase, strip, collapse whitespace."""
        if not text:
            return ""
        # Lowercase, strip, collapse multiple spaces
        normalized = " ".join(text.lower().split())
        return normalized

    @staticmethod
    def normalize_email(email: Optional[str]) -> str:
        """Normalize email address: lowercase, strip."""
        if not email:
            return ""
        return email.lower().strip()

    @staticmethod
    def normalize_participants(emails: Optional[List[str]]) -> str:
        """Normalize participant list: lowercase, sorted, joined."""
        if not emails:
            return ""
        normalized = sorted(ContentHasher.normalize_email(e) for e in emails if e)
        return "|".join(normalized)

    @staticmethod
    def normalize_timestamp(ts: Optional[str]) -> str:
        """Normalize timestamp: floor to minute."""
        if not ts:
            return ""
        try:
            # Parse ISO timestamp and floor to minute
            if isinstance(ts, str):
                # Handle various ISO formats
                ts = ts.replace("Z", "+00:00")
                if "." in ts:
                    ts = ts.split(".")[0] + ts[ts.rfind("+"):] if "+" in ts else ts.split(".")[0]
            dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
            return dt.strftime("%Y-%m-%dT%H:%M")
        except (ValueError, TypeError):
            return ""

    @classmethod
    def compute_content_hash(
        cls,
        subject: Optional[str],
        preview: Optional[str],
        from_addr: Optional[str],
        to_addrs: Optional[List[str]] = None,
        cc_addrs: Optional[List[str]] = None,
        sent_at: Optional[str] = None,
    ) -> str:
        """
        Compute SHA256 content hash for deduplication.

        Returns 64-char hex string.
        """
        parts = [
            cls.normalize_text(subject),
            cls.normalize_text(preview),
            cls.normalize_email(from_addr),
            cls.normalize_participants(to_addrs),
            cls.normalize_participants(cc_addrs),
            cls.normalize_timestamp(sent_at),
        ]

        combined = "\n".join(parts)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    @classmethod
    def compute_attachment_hash(cls, content: bytes) -> str:
        """Compute SHA256 hash of attachment content."""
        return hashlib.sha256(content).hexdigest()


# =============================================================================
# UPSERT RESULT TYPES
# =============================================================================

class UpsertAction(str, Enum):
    """Possible outcomes of upsert operation."""
    INSERTED = "inserted"     # New message created
    UPDATED = "updated"       # Message content changed
    NOOP = "noop"             # No changes (same content_hash)
    DELETED = "deleted"       # Soft deleted
    ALREADY_DELETED = "already_deleted"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass
class UpsertResult:
    """Result of an upsert operation."""
    action: UpsertAction
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    enqueue_prepare: bool = False
    prepare_job_type: Optional[str] = None
    error: Optional[str] = None
    latency_ms: int = 0


@dataclass
class AttachmentResult:
    """Result of attachment upsert (two-table model)."""
    action: str  # 'inserted', 'linked', 'already_linked'
    blob_id: Optional[str] = None
    link_id: Optional[str] = None
    deduped: bool = False


@dataclass
class TelemetrySnapshot:
    """Telemetry counters for a sync session."""
    messages_inserted: int = 0
    messages_updated: int = 0
    messages_noop: int = 0
    messages_deleted: int = 0
    duplicates_dropped: int = 0
    attachments_deduped: int = 0
    prepare_jobs_deduped: int = 0
    upsert_latency_sum_ms: int = 0
    upsert_count: int = 0

    @property
    def total_processed(self) -> int:
        return self.messages_inserted + self.messages_updated + self.messages_noop + self.messages_deleted

    @property
    def avg_upsert_latency_ms(self) -> float:
        if self.upsert_count == 0:
            return 0
        return self.upsert_latency_sum_ms / self.upsert_count


# =============================================================================
# IDEMPOTENT PROCESSOR
# =============================================================================

class IdempotentProcessor:
    """
    Processes email messages with full idempotency guarantees.

    Uses:
    - RPC functions for atomic upserts
    - Content hashing for no-op detection
    - Prepare job dedupe
    - Telemetry tracking
    """

    def __init__(
        self,
        supabase,
        yacht_id: str,
        watcher_id: Optional[str] = None,
    ):
        self.supabase = supabase
        self.yacht_id = yacht_id
        self.watcher_id = watcher_id
        self.hasher = ContentHasher()
        self.telemetry = TelemetrySnapshot()

    async def upsert_message(
        self,
        graph_message: Dict[str, Any],
        thread_id: str,
    ) -> UpsertResult:
        """
        Upsert a message with full idempotency.

        Decision matrix:
        - If not exists → INSERT, enqueue prepare(new)
        - If exists and change_key + content_hash unchanged → NO-OP
        - If exists and changed → UPDATE, enqueue prepare(update)
        """
        start_time = time.time()

        try:
            # Extract fields from Graph message
            provider_message_id = graph_message.get("id")
            if not provider_message_id:
                return UpsertResult(
                    action=UpsertAction.ERROR,
                    error="Missing message id"
                )

            # Extract sender
            from_data = graph_message.get("from", {}).get("emailAddress", {})
            from_addr = from_data.get("address", "")
            from_name = from_data.get("name", "")
            from_hash = hashlib.sha256(from_addr.lower().encode()).hexdigest() if from_addr else ""

            # Extract recipients
            to_addrs = [
                r.get("emailAddress", {}).get("address", "")
                for r in graph_message.get("toRecipients", [])
            ]
            to_hashes = [hashlib.sha256(a.lower().encode()).hexdigest() for a in to_addrs if a]

            cc_addrs = [
                r.get("emailAddress", {}).get("address", "")
                for r in graph_message.get("ccRecipients", [])
            ]
            cc_hashes = [hashlib.sha256(a.lower().encode()).hexdigest() for a in cc_addrs if a]

            # Extract content
            subject = graph_message.get("subject", "")
            preview = (graph_message.get("bodyPreview", "") or "")[:200]
            change_key = graph_message.get("changeKey", "")
            sent_at = graph_message.get("sentDateTime")
            received_at = graph_message.get("receivedDateTime")
            has_attachments = graph_message.get("hasAttachments", False)
            internet_message_id = graph_message.get("internetMessageId")

            # Compute content hash
            content_hash = self.hasher.compute_content_hash(
                subject=subject,
                preview=preview,
                from_addr=from_addr,
                to_addrs=to_addrs,
                cc_addrs=cc_addrs,
                sent_at=sent_at,
            )

            # Determine direction
            folder = graph_message.get("parentFolderId", "")
            direction = "outbound" if "sent" in folder.lower() else "inbound"

            # Call RPC upsert function
            result = self.supabase.rpc("upsert_email_message", {
                "p_yacht_id": self.yacht_id,
                "p_provider_message_id": provider_message_id,
                "p_thread_id": thread_id,
                "p_change_key": change_key,
                "p_content_hash": content_hash,
                "p_subject": subject,
                "p_preview_text": preview,
                "p_from_address_hash": from_hash,
                "p_from_display_name": from_name,
                "p_to_addresses_hash": to_hashes,
                "p_cc_addresses_hash": cc_hashes,
                "p_direction": direction,
                "p_sent_at": sent_at,
                "p_received_at": received_at,
                "p_has_attachments": has_attachments,
                "p_internet_message_id": internet_message_id,
            }).execute()

            latency_ms = int((time.time() - start_time) * 1000)

            if not result.data:
                return UpsertResult(
                    action=UpsertAction.ERROR,
                    error="RPC returned no data",
                    latency_ms=latency_ms
                )

            rpc_result = result.data
            action_str = rpc_result.get("action", "error")
            message_id = rpc_result.get("message_id")
            enqueue_prepare = rpc_result.get("enqueue_prepare", False)
            prepare_job_type = rpc_result.get("prepare_job_type")

            # Map to enum
            action_map = {
                "inserted": UpsertAction.INSERTED,
                "updated": UpsertAction.UPDATED,
                "noop": UpsertAction.NOOP,
            }
            action = action_map.get(action_str, UpsertAction.ERROR)

            # Update telemetry
            self._update_telemetry(action, latency_ms)

            # Enqueue prepare job if needed
            job_deduped = False
            if enqueue_prepare and message_id:
                job_result = await self._enqueue_prepare_job(message_id, prepare_job_type)
                job_deduped = job_result.get("deduped", False)
                if job_deduped:
                    self.telemetry.prepare_jobs_deduped += 1

            return UpsertResult(
                action=action,
                message_id=message_id,
                thread_id=thread_id,
                enqueue_prepare=enqueue_prepare,
                prepare_job_type=prepare_job_type,
                latency_ms=latency_ms
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[idempotency] Upsert error: {e}")

            # Check for duplicate key error (race condition)
            if "duplicate" in str(e).lower() or "23505" in str(e):
                self.telemetry.duplicates_dropped += 1
                return UpsertResult(
                    action=UpsertAction.NOOP,
                    error="duplicate_key",
                    latency_ms=latency_ms
                )

            return UpsertResult(
                action=UpsertAction.ERROR,
                error=str(e),
                latency_ms=latency_ms
            )

    async def soft_delete_message(
        self,
        provider_message_id: str,
        reason: str = "deleted",
    ) -> UpsertResult:
        """Soft delete a message."""
        start_time = time.time()

        try:
            result = self.supabase.rpc("soft_delete_email_message", {
                "p_yacht_id": self.yacht_id,
                "p_provider_message_id": provider_message_id,
                "p_reason": reason,
            }).execute()

            latency_ms = int((time.time() - start_time) * 1000)

            if not result.data:
                return UpsertResult(
                    action=UpsertAction.ERROR,
                    error="RPC returned no data",
                    latency_ms=latency_ms
                )

            rpc_result = result.data
            action_str = rpc_result.get("action", "error")
            message_id = rpc_result.get("message_id")

            action_map = {
                "deleted": UpsertAction.DELETED,
                "already_deleted": UpsertAction.ALREADY_DELETED,
                "not_found": UpsertAction.NOT_FOUND,
            }
            action = action_map.get(action_str, UpsertAction.ERROR)

            if action == UpsertAction.DELETED:
                self.telemetry.messages_deleted += 1

            return UpsertResult(
                action=action,
                message_id=message_id,
                latency_ms=latency_ms
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[idempotency] Delete error: {e}")
            return UpsertResult(
                action=UpsertAction.ERROR,
                error=str(e),
                latency_ms=latency_ms
            )

    async def upsert_attachment(
        self,
        message_id: str,
        attachment_data: Dict[str, Any],
    ) -> AttachmentResult:
        """
        Upsert attachment with SHA256 dedupe (two-table model).

        Uses:
        - email_attachment_blobs: unique content per yacht
        - email_attachment_links: message-to-blob references

        Returns blob_id and link_id for tracking.
        """
        try:
            provider_id = attachment_data.get("id", "")
            name = attachment_data.get("name", "unknown")
            content_type = attachment_data.get("contentType", "application/octet-stream")
            size_bytes = attachment_data.get("size", 0)
            is_inline = attachment_data.get("isInline", False)

            # Compute SHA256 from content if available
            content = attachment_data.get("contentBytes")
            if content:
                import base64
                content_bytes = base64.b64decode(content)
                sha256 = self.hasher.compute_attachment_hash(content_bytes)
            else:
                # Fallback: hash based on metadata + provider_id to reduce false links
                # This is less reliable but avoids deferred dedupe complexity
                meta_str = f"{provider_id}|{name}|{size_bytes}|{content_type}"
                sha256 = hashlib.sha256(meta_str.encode()).hexdigest()
                logger.debug(f"[idempotency] Attachment fallback hash (no content): {name}")

            result = self.supabase.rpc("upsert_email_attachment", {
                "p_yacht_id": self.yacht_id,
                "p_message_id": message_id,
                "p_provider_attachment_id": provider_id,
                "p_name": name,
                "p_content_type": content_type,
                "p_sha256": sha256,
                "p_size_bytes": size_bytes,
                "p_is_inline": is_inline,
            }).execute()

            if not result.data:
                return AttachmentResult(action="error")

            rpc_result = result.data
            deduped = rpc_result.get("deduped", False)

            if deduped:
                self.telemetry.attachments_deduped += 1

            return AttachmentResult(
                action=rpc_result.get("action", "error"),
                blob_id=rpc_result.get("blob_id"),
                link_id=rpc_result.get("link_id"),
                deduped=deduped
            )

        except Exception as e:
            logger.error(f"[idempotency] Attachment error: {e}")
            return AttachmentResult(action="error")

    async def refresh_thread_aggregates(self, thread_id: str) -> Dict[str, Any]:
        """Refresh thread aggregates after message mutations."""
        try:
            result = self.supabase.rpc("refresh_thread_aggregates", {
                "p_thread_id": thread_id
            }).execute()

            return result.data if result.data else {}
        except Exception as e:
            logger.error(f"[idempotency] Thread refresh error: {e}")
            return {}

    async def _enqueue_prepare_job(
        self,
        message_id: str,
        job_type: str,
    ) -> Dict[str, Any]:
        """Enqueue prepare job with dedupe."""
        try:
            result = self.supabase.rpc("enqueue_prepare_job_deduped", {
                "p_yacht_id": self.yacht_id,
                "p_message_id": message_id,
                "p_job_type": job_type,
            }).execute()

            return result.data if result.data else {}
        except Exception as e:
            logger.error(f"[idempotency] Enqueue error: {e}")
            return {}

    def _update_telemetry(self, action: UpsertAction, latency_ms: int):
        """Update telemetry counters."""
        if action == UpsertAction.INSERTED:
            self.telemetry.messages_inserted += 1
        elif action == UpsertAction.UPDATED:
            self.telemetry.messages_updated += 1
        elif action == UpsertAction.NOOP:
            self.telemetry.messages_noop += 1

        self.telemetry.upsert_latency_sum_ms += latency_ms
        self.telemetry.upsert_count += 1

    async def flush_telemetry(self):
        """Flush telemetry counters to database."""
        if self.telemetry.total_processed == 0:
            return

        try:
            self.supabase.rpc("increment_sync_telemetry", {
                "p_yacht_id": self.yacht_id,
                "p_watcher_id": self.watcher_id,
                "p_messages_inserted": self.telemetry.messages_inserted,
                "p_messages_updated": self.telemetry.messages_updated,
                "p_messages_noop": self.telemetry.messages_noop,
                "p_messages_deleted": self.telemetry.messages_deleted,
                "p_duplicates_dropped": self.telemetry.duplicates_dropped,
                "p_attachments_deduped": self.telemetry.attachments_deduped,
                "p_prepare_jobs_deduped": self.telemetry.prepare_jobs_deduped,
                "p_upsert_latency_ms": self.telemetry.upsert_latency_sum_ms,
            }).execute()

            logger.info(
                f"[idempotency] Telemetry flushed: "
                f"inserted={self.telemetry.messages_inserted} "
                f"updated={self.telemetry.messages_updated} "
                f"noop={self.telemetry.messages_noop} "
                f"deleted={self.telemetry.messages_deleted} "
                f"duplicates_dropped={self.telemetry.duplicates_dropped}"
            )

            # Reset counters
            self.telemetry = TelemetrySnapshot()

        except Exception as e:
            logger.error(f"[idempotency] Telemetry flush error: {e}")


# =============================================================================
# THREAD MANAGER
# =============================================================================

class ThreadManager:
    """
    Manages email threads with idempotent creation and aggregate maintenance.
    """

    def __init__(self, supabase, yacht_id: str):
        self.supabase = supabase
        self.yacht_id = yacht_id

    async def get_or_create_thread(
        self,
        conversation_id: Optional[str],
        message_data: Dict[str, Any],
    ) -> str:
        """Get or create thread for a message, idempotently."""
        if not conversation_id:
            # Generate fallback thread ID for orphan messages
            conversation_id = f"orphan_{message_data.get('id', 'unknown')}"

        # Check if thread exists
        existing = self.supabase.table("email_threads").select("id").eq(
            "yacht_id", self.yacht_id
        ).eq("provider_conversation_id", conversation_id).single().execute()

        if existing.data:
            return existing.data["id"]

        # Create new thread
        thread_data = {
            "yacht_id": self.yacht_id,
            "provider_conversation_id": conversation_id,
            "latest_subject": message_data.get("subject"),
            "message_count": 0,
            "active_message_count": 0,
            "has_attachments": message_data.get("hasAttachments", False),
            "source": "external",
        }

        result = self.supabase.table("email_threads").insert(thread_data).execute()

        if result.data:
            return result.data[0]["id"]
        else:
            raise Exception("Failed to create thread")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ContentHasher",
    "UpsertAction",
    "UpsertResult",
    "AttachmentResult",
    "TelemetrySnapshot",
    "IdempotentProcessor",
    "ThreadManager",
]
