"""
Manual/Document Handlers
=========================

P0 Actions for manual access:
- show_manual_section (P0 Action #1) - READ

Based on specs: /P0_ACTION_CONTRACTS.md - Cluster 01: FIX_SOMETHING
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import ResponseBuilder

logger = logging.getLogger(__name__)


class ManualHandlers:
    """
    Handlers for manual/document access actions.

    Implements P0 actions:
    - show_manual_section (READ)
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # P0 ACTION #1: show_manual_section
    # =========================================================================

    async def show_manual_section_execute(
        self,
        equipment_id: str,
        yacht_id: str,
        user_id: str,
        fault_code: Optional[str] = None,
        section_id: Optional[str] = None
    ) -> Dict:
        """
        POST /v1/actions/execute (action=show_manual_section)

        Show relevant manual section for equipment/fault.

        READ action - execute only (no prefill or preview needed).

        Logic:
        1. Get equipment details
        2. Find associated manual (document)
        3. If fault_code provided, search for relevant section
        4. If section_id provided, jump to that section
        5. Otherwise, show first section or table of contents
        6. Generate signed URL for PDF access (30 min expiry)
        7. Return related sections

        Returns:
        - Document metadata (title, manufacturer, model, version)
        - Signed URL to PDF (30-minute expiry)
        - Section details (title, page number, preview text)
        - Related sections for navigation
        """
        try:
            # Get equipment details
            equipment_result = self.db.table("pms_equipment").select(
                "id, name, manufacturer, model, manual_id"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not equipment_result.data:
                return ResponseBuilder.error(
                    action="show_manual_section",
                    error_code="EQUIPMENT_NOT_FOUND",
                    message=f"Equipment not found: {equipment_id}"
                )

            equipment = equipment_result.data

            # Get manual (document) for equipment
            # First try manual_id, then search by manufacturer/model
            manual = None
            if equipment.get("manual_id"):
                manual_result = self.db.table("documents").select(
                    "id, title, manufacturer, model, version, storage_path, page_count, "
                    "document_type, created_at"
                ).eq("id", equipment["manual_id"]).maybe_single().execute()
                if manual_result.data:
                    manual = manual_result.data

            # Fallback: search by manufacturer + model
            if not manual:
                manual_result = self.db.table("documents").select(
                    "id, title, manufacturer, model, version, storage_path, page_count, "
                    "document_type, created_at"
                ).eq("manufacturer", equipment.get("manufacturer", "")).eq(
                    "model", equipment.get("model", "")
                ).eq("document_type", "manual").maybe_single().execute()

                if manual_result.data:
                    manual = manual_result.data

            if not manual:
                return ResponseBuilder.error(
                    action="show_manual_section",
                    error_code="MANUAL_NOT_FOUND",
                    message=f"No manual available for {equipment.get('manufacturer', '')} {equipment.get('model', '')}"
                )

            # Find relevant section
            section = None
            related_sections = []

            if section_id:
                # Direct section lookup
                section_result = self.db.table("document_chunks").select(
                    "id, text, page_number, chunk_index, metadata"
                ).eq("id", section_id).eq("document_id", manual["id"]).maybe_single().execute()

                if section_result.data:
                    section = section_result.data
                else:
                    return ResponseBuilder.error(
                        action="show_manual_section",
                        error_code="SECTION_NOT_FOUND",
                        message=f"Section not found: {section_id}"
                    )

            elif fault_code:
                # Search for fault code in document chunks
                search_result = self.db.table("document_chunks").select(
                    "id, text, page_number, chunk_index, metadata"
                ).eq("document_id", manual["id"]).ilike(
                    "text", f"%{fault_code}%"
                ).order("page_number").limit(1).execute()

                if search_result.data and len(search_result.data) > 0:
                    section = search_result.data[0]
                else:
                    # Fallback: first section
                    fallback_result = self.db.table("document_chunks").select(
                        "id, text, page_number, chunk_index, metadata"
                    ).eq("document_id", manual["id"]).order("page_number").limit(1).execute()
                    
                    if fallback_result.data and len(fallback_result.data) > 0:
                        section = fallback_result.data[0]

            else:
                # No fault code or section - show first section
                first_section_result = self.db.table("document_chunks").select(
                    "id, text, page_number, chunk_index, metadata"
                ).eq("document_id", manual["id"]).order("page_number").limit(1).execute()

                if first_section_result.data and len(first_section_result.data) > 0:
                    section = first_section_result.data[0]

            if not section:
                return ResponseBuilder.error(
                    action="show_manual_section",
                    error_code="SECTION_NOT_FOUND",
                    message="No sections found in manual"
                )

            # Get related sections (nearby pages)
            current_page = section.get("page_number", 1)
            related_result = self.db.table("document_chunks").select(
                "id, text, page_number, chunk_index, metadata"
            ).eq("document_id", manual["id"]).gte(
                "page_number", max(1, current_page - 2)
            ).lte(
                "page_number", current_page + 2
            ).neq("id", section["id"]).order("page_number").limit(5).execute()

            if related_result.data:
                related_sections = [
                    {
                        "id": r["id"],
                        "title": r.get("metadata", {}).get("heading", f"Page {r.get('page_number', '?')}"),
                        "page_number": r.get("page_number", 0)
                    }
                    for r in related_result.data
                ]

            # Generate signed URL for PDF
            # NOTE: Supabase Python client doesn't support signed URLs directly
            # This would need to be implemented via Supabase Storage API
            # For now, return storage path
            signed_url = None
            if manual.get("storage_path"):
                try:
                    # Generate signed URL using Supabase Storage
                    # storage_path format: "manuals/manufacturer/model/filename.pdf"
                    signed_url = self.db.storage.from_("documents").create_signed_url(
                        manual["storage_path"],
                        expires_in=1800  # 30 minutes
                    )
                    if isinstance(signed_url, dict) and "signedURL" in signed_url:
                        signed_url = signed_url["signedURL"]
                except Exception as e:
                    logger.warning(f"Failed to generate signed URL: {e}")
                    signed_url = None

            # Extract section title from metadata or text
            section_title = section.get("metadata", {}).get("heading", "")
            if not section_title:
                # Extract first line as title
                text_lines = section.get("text", "").split("\n")
                section_title = text_lines[0] if text_lines else f"Page {section.get('page_number', '?')}"

            # Build response
            return ResponseBuilder.success(
                action="show_manual_section",
                result={
                    "document": {
                        "id": manual["id"],
                        "title": manual.get("title", ""),
                        "manufacturer": manual.get("manufacturer", ""),
                        "model": manual.get("model", ""),
                        "version": manual.get("version", ""),
                        "storage_path": manual.get("storage_path", ""),
                        "signed_url": signed_url,
                        "page_count": manual.get("page_count", 0)
                    },
                    "section": {
                        "id": section["id"],
                        "title": section_title,
                        "page_number": section.get("page_number", 0),
                        "text_preview": section.get("text", "")[:500]  # First 500 chars
                    },
                    "related_sections": related_sections
                }
            )

        except Exception as e:
            logger.exception(f"Error showing manual section for equipment {equipment_id}")
            return ResponseBuilder.error(
                action="show_manual_section",
                error_code="INTERNAL_ERROR",
                message=f"Failed to show manual section: {str(e)}"
            )


__all__ = ["ManualHandlers"]
