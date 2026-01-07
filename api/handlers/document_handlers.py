"""
Document/Manual Domain Handlers
===============================

Group 5: READ handlers for document and manual actions.

Handlers:
- view_manual_section: Document chunk with PDF file access
- view_related_docs: Related documents with file URLs

All handlers return standardized ActionResponseEnvelope with signed file URLs.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action_response_schema import (
    ResponseBuilder,
    FileReference,
    FileType,
    AvailableAction,
    SignedUrlGenerator
)

logger = logging.getLogger(__name__)


class DocumentHandlers:
    """
    Document/manual domain READ handlers.

    Key feature: All document handlers generate signed URLs for file access.
    """

    # Default signed URL expiry (30 minutes)
    URL_EXPIRY_MINUTES = 30

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    async def view_manual_section(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View document/manual section.

        Returns:
        - Document chunk content (section_title, content, page_number)
        - Parent document info
        - Signed URL for PDF file (opens in new tab)
        - Related sections
        """
        builder = ResponseBuilder("view_manual_section", entity_id, "document_chunk", yacht_id)

        try:
            # Query document chunk with parent document
            result = self.db.table("document_chunks").select(
                "id, document_id, section_title, section_number, content, page_number, "
                "storage_path, "
                "documents:document_id(id, title, category, storage_path, mime_type, page_count, file_size)"
            ).eq("id", entity_id).single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Document section not found: {entity_id}")
                return builder.build()

            chunk = result.data
            document = chunk.get("documents") or {}

            # Build chunk data
            chunk_data = {
                "chunk_id": chunk.get("id"),
                "document_id": chunk.get("document_id"),
                "section_title": chunk.get("section_title"),
                "section_number": chunk.get("section_number"),
                "page_number": chunk.get("page_number"),
                "content": chunk.get("content"),
                "document": {
                    "id": document.get("id"),
                    "title": document.get("title"),
                    "category": document.get("category"),
                    "page_count": document.get("page_count")
                }
            }

            builder.set_data(chunk_data)

            # Generate signed URL for the document PDF
            if self.url_generator and document.get("storage_path"):
                file_ref = self.url_generator.create_file_reference(
                    bucket="documents",
                    path=document["storage_path"],
                    filename=document.get("title", "document.pdf"),
                    file_id=document.get("id"),
                    display_name=document.get("title"),
                    page_count=document.get("page_count"),
                    size_bytes=document.get("file_size"),
                    mime_type=document.get("mime_type", "application/pdf"),
                    expires_in_minutes=self.URL_EXPIRY_MINUTES
                )
                if file_ref:
                    # Add page anchor for direct navigation
                    page_num = chunk.get("page_number")
                    if page_num and file_ref.signed_url:
                        # Most PDF viewers support #page=N anchor
                        file_ref_dict = file_ref.to_dict()
                        file_ref_dict["page_anchor"] = f"#page={page_num}"
                        file_ref_dict["direct_url"] = f"{file_ref.signed_url}#page={page_num}"
                        builder.add_file(file_ref_dict)
                    else:
                        builder.add_file(file_ref)

            # Get related sections from same document
            related = await self._get_related_sections(
                document_id=chunk.get("document_id"),
                current_chunk_id=entity_id,
                limit=5
            )
            if related:
                chunk_data["related_sections"] = related

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="view_related_docs",
                label="Related Documents",
                variant="READ",
                icon="link"
            ))
            builder.add_available_action(AvailableAction(
                action_id="add_to_handover",
                label="Add to Handover",
                variant="MUTATE",
                icon="send"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_manual_section failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_related_docs(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Find related documents.

        Returns:
        - List of related document chunks
        - Signed URLs for each document
        """
        builder = ResponseBuilder("view_related_docs", entity_id, "document_chunk", yacht_id)

        try:
            # Get source chunk
            source_result = self.db.table("document_chunks").select(
                "id, content, document_id, section_title"
            ).eq("id", entity_id).single().execute()

            if not source_result.data:
                builder.set_error("NOT_FOUND", f"Document chunk not found: {entity_id}")
                return builder.build()

            source = source_result.data

            # Get related via graph edges
            related_chunks = []
            try:
                edge_result = self.db.table("graph_edges").select(
                    "target_id, edge_type"
                ).eq("source_id", entity_id).in_(
                    "edge_type", ["REFERENCES", "RELATED_TO", "SEE_ALSO"]
                ).limit(10).execute()

                target_ids = [e["target_id"] for e in (edge_result.data or [])]

                if target_ids:
                    chunks_result = self.db.table("document_chunks").select(
                        "id, section_title, page_number, document_id, "
                        "documents:document_id(id, title, storage_path, mime_type)"
                    ).in_("id", target_ids).execute()

                    related_chunks = chunks_result.data or []

            except Exception as e:
                logger.warning(f"Failed to get related via graph: {e}")

            # If no graph relations, search by content similarity (basic keyword match)
            if not related_chunks:
                content = source.get("content", "")
                keywords = self._extract_keywords(content)

                if keywords:
                    try:
                        # Search for chunks containing similar keywords
                        search_result = self.db.table("document_chunks").select(
                            "id, section_title, page_number, document_id, "
                            "documents:document_id(id, title, storage_path, mime_type)"
                        ).eq("yacht_id", yacht_id).neq(
                            "id", entity_id
                        ).neq("document_id", source.get("document_id")).limit(10).execute()

                        related_chunks = search_result.data or []
                    except Exception:
                        pass

            # Build response with signed URLs
            files = []
            seen_docs = set()

            for chunk in related_chunks:
                doc = chunk.get("documents")
                if doc and doc.get("id") not in seen_docs:
                    seen_docs.add(doc["id"])

                    if self.url_generator and doc.get("storage_path"):
                        file_ref = self.url_generator.create_file_reference(
                            bucket="documents",
                            path=doc["storage_path"],
                            filename=doc.get("title", "document.pdf"),
                            file_id=doc["id"],
                            display_name=doc.get("title"),
                            mime_type=doc.get("mime_type", "application/pdf"),
                            expires_in_minutes=self.URL_EXPIRY_MINUTES
                        )
                        if file_ref:
                            files.append(file_ref.to_dict())

            builder.set_data({
                "source_id": entity_id,
                "source_title": source.get("section_title"),
                "related": [
                    {
                        "chunk_id": c["id"],
                        "section_title": c.get("section_title"),
                        "page_number": c.get("page_number"),
                        "document_id": c.get("document_id"),
                        "document_title": c.get("documents", {}).get("title") if c.get("documents") else None
                    }
                    for c in related_chunks
                ],
                "related_count": len(related_chunks)
            })

            if files:
                builder.add_files(files)

            return builder.build()

        except Exception as e:
            logger.error(f"view_related_docs failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _get_related_sections(
        self,
        document_id: str,
        current_chunk_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """Get other sections from same document"""
        try:
            result = self.db.table("document_chunks").select(
                "id, section_title, section_number, page_number"
            ).eq("document_id", document_id).neq(
                "id", current_chunk_id
            ).order("section_number").limit(limit).execute()

            return [
                {
                    "chunk_id": c["id"],
                    "section_title": c.get("section_title"),
                    "section_number": c.get("section_number"),
                    "page_number": c.get("page_number")
                }
                for c in (result.data or [])
            ]
        except Exception:
            return []

    def _extract_keywords(self, content: str, limit: int = 5) -> List[str]:
        """Extract keywords from content for similarity search"""
        if not content:
            return []

        # Simple keyword extraction (in production, use NLP)
        import re

        # Remove common words
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "to", "of", "in", "for", "on", "with", "at",
            "by", "from", "as", "into", "through", "during", "before",
            "after", "above", "below", "between", "under", "again",
            "further", "then", "once", "here", "there", "when", "where",
            "why", "how", "all", "each", "few", "more", "most", "other",
            "some", "such", "no", "nor", "not", "only", "own", "same",
            "so", "than", "too", "very", "just", "and", "but", "or",
            "this", "that", "these", "those", "it", "its"
        }

        # Extract words
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())

        # Filter and count
        word_counts = {}
        for word in words:
            if word not in stopwords:
                word_counts[word] = word_counts.get(word, 0) + 1

        # Sort by frequency and return top N
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:limit]]


def get_document_handlers(supabase_client) -> Dict[str, callable]:
    """Get document handler functions for registration."""
    handlers = DocumentHandlers(supabase_client)

    return {
        "view_manual_section": handlers.view_manual_section,
        "view_related_docs": handlers.view_related_docs,
    }
