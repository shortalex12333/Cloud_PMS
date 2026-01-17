"""
Email Embedding Service
========================

Generates embeddings for email signals at ingest time.

Signals embedded:
    - subject: Email subject line
    - sender: Sender display name
    - attachment_names: List of attachment filenames
    - meta: Combined signal (subject + sender + attachments)

Model: text-embedding-3-small (same as query time for consistency)
Vector dimension: 1536

Usage:
    service = EmailEmbeddingService()

    # Embed a single email
    embeddings = await service.embed_email(
        subject="Re: WO-1234 Parts shipped",
        sender_name="John Smith",
        attachment_names=["invoice.pdf", "quote.pdf"]
    )

    # embeddings = {
    #     'subject_embedding': [...],
    #     'sender_embedding': [...],
    #     'meta_embedding': [...],
    # }
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - embeddings will be disabled")


@dataclass
class EmailEmbeddings:
    """Container for email embeddings."""
    subject_embedding: Optional[List[float]] = None
    sender_embedding: Optional[List[float]] = None
    meta_embedding: Optional[List[float]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'subject_embedding': self.subject_embedding,
            'sender_embedding': self.sender_embedding,
            'meta_embedding': self.meta_embedding,
            'error': self.error,
        }

    def has_embeddings(self) -> bool:
        return self.meta_embedding is not None


class EmailEmbeddingService:
    """
    Service for generating email signal embeddings.

    Uses OpenAI text-embedding-3-small for consistency with
    query-time embeddings.
    """

    MODEL = "text-embedding-3-small"
    DIMENSION = 1536

    def __init__(self, api_key: str = None):
        """
        Initialize service.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self._client = None

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None and OPENAI_AVAILABLE and self.api_key:
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def is_available(self) -> bool:
        """Check if embedding service is available."""
        return OPENAI_AVAILABLE and self.api_key is not None

    async def embed_email(
        self,
        subject: str = "",
        sender_name: str = "",
        attachment_names: List[str] = None,
    ) -> EmailEmbeddings:
        """
        Generate embeddings for email signals.

        Args:
            subject: Email subject line
            sender_name: Sender display name
            attachment_names: List of attachment filenames

        Returns:
            EmailEmbeddings with all signal embeddings
        """
        if not self.is_available():
            return EmailEmbeddings(error="Embedding service not available")

        attachment_names = attachment_names or []

        try:
            # Embed subject
            subject_emb = None
            if subject and subject.strip():
                subject_emb = await self._embed_text(subject.strip())

            # Embed sender
            sender_emb = None
            if sender_name and sender_name.strip():
                sender_emb = await self._embed_text(sender_name.strip())

            # Build meta text (combined signal)
            meta_parts = []
            if subject:
                meta_parts.append(f"Subject: {subject}")
            if sender_name:
                meta_parts.append(f"From: {sender_name}")
            if attachment_names:
                meta_parts.append(f"Attachments: {', '.join(attachment_names)}")

            meta_text = " | ".join(meta_parts) if meta_parts else ""
            meta_emb = await self._embed_text(meta_text) if meta_text else None

            return EmailEmbeddings(
                subject_embedding=subject_emb,
                sender_embedding=sender_emb,
                meta_embedding=meta_emb,
            )

        except Exception as e:
            logger.error(f"Email embedding failed: {e}")
            return EmailEmbeddings(error=str(e))

    async def _embed_text(self, text: str) -> Optional[List[float]]:
        """
        Embed a single text string.

        Args:
            text: Text to embed

        Returns:
            1536-dimension embedding vector
        """
        if not text or not self.client:
            return None

        try:
            response = self.client.embeddings.create(
                model=self.MODEL,
                input=text[:8000],  # Truncate to model limit
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Text embedding failed: {e}")
            return None

    def embed_email_sync(
        self,
        subject: str = "",
        sender_name: str = "",
        attachment_names: List[str] = None,
    ) -> EmailEmbeddings:
        """
        Synchronous wrapper for embed_email.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.embed_email(subject, sender_name, attachment_names)
        )

    async def embed_batch(
        self,
        emails: List[Dict[str, Any]],
    ) -> List[EmailEmbeddings]:
        """
        Embed a batch of emails.

        Args:
            emails: List of dicts with 'subject', 'sender_name', 'attachment_names'

        Returns:
            List of EmailEmbeddings
        """
        results = []
        for email in emails:
            emb = await self.embed_email(
                subject=email.get('subject', ''),
                sender_name=email.get('sender_name', ''),
                attachment_names=email.get('attachment_names', []),
            )
            results.append(emb)
        return results


class EmailEmbeddingUpdater:
    """
    Updates email embeddings in the database.

    Used by the email sync worker to populate embeddings
    for newly synced emails.
    """

    def __init__(self, supabase_client, yacht_id: str):
        """
        Initialize updater.

        Args:
            supabase_client: Supabase client for the tenant
            yacht_id: Yacht ID for isolation
        """
        self.client = supabase_client
        self.yacht_id = yacht_id
        self.embedding_service = EmailEmbeddingService()

    async def update_email_embeddings(
        self,
        email_id: str,
        subject: str,
        sender_name: str,
        attachments: List[Dict] = None,
    ) -> bool:
        """
        Generate and store embeddings for an email.

        Args:
            email_id: Email message ID
            subject: Email subject
            sender_name: Sender display name
            attachments: List of attachment metadata dicts

        Returns:
            True if successful
        """
        if not self.embedding_service.is_available():
            logger.warning("Embedding service not available - skipping")
            return False

        # Extract attachment names
        attachment_names = []
        if attachments:
            for att in attachments:
                name = att.get('name') or att.get('filename')
                if name:
                    attachment_names.append(name)

        # Generate embeddings
        embeddings = await self.embedding_service.embed_email(
            subject=subject,
            sender_name=sender_name,
            attachment_names=attachment_names,
        )

        if not embeddings.has_embeddings():
            logger.warning(f"No embeddings generated for email {email_id}: {embeddings.error}")
            return False

        # Update database
        try:
            update_data = {}

            if embeddings.subject_embedding:
                update_data['subject_embedding'] = embeddings.subject_embedding

            if embeddings.sender_embedding:
                update_data['sender_embedding'] = embeddings.sender_embedding

            if embeddings.meta_embedding:
                update_data['meta_embedding'] = embeddings.meta_embedding

            if update_data:
                self.client.table('email_messages').update(
                    update_data
                ).eq('id', email_id).eq('yacht_id', self.yacht_id).execute()

                logger.debug(f"Updated embeddings for email {email_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to update embeddings for email {email_id}: {e}")

        return False

    async def backfill_embeddings(
        self,
        limit: int = 100,
        batch_size: int = 10,
    ) -> Dict[str, int]:
        """
        Backfill embeddings for emails missing them.

        Args:
            limit: Max emails to process
            batch_size: Emails per batch

        Returns:
            Stats dict with counts
        """
        stats = {'processed': 0, 'success': 0, 'failed': 0}

        try:
            # Find emails without meta_embedding
            result = self.client.table('email_messages').select(
                'id, subject, from_display_name, attachments'
            ).eq('yacht_id', self.yacht_id).is_(
                'meta_embedding', 'null'
            ).limit(limit).execute()

            emails = result.data or []
            logger.info(f"Found {len(emails)} emails needing embeddings")

            for email in emails:
                stats['processed'] += 1

                # Parse attachments
                attachments = email.get('attachments') or []
                if isinstance(attachments, str):
                    import json
                    try:
                        attachments = json.loads(attachments)
                    except:
                        attachments = []

                success = await self.update_email_embeddings(
                    email_id=email['id'],
                    subject=email.get('subject', ''),
                    sender_name=email.get('from_display_name', ''),
                    attachments=attachments,
                )

                if success:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1

        except Exception as e:
            logger.error(f"Backfill failed: {e}")

        return stats


# =============================================================================
# Factory function
# =============================================================================

_embedding_service = None


def get_embedding_service() -> EmailEmbeddingService:
    """Get singleton embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmailEmbeddingService()
    return _embedding_service
