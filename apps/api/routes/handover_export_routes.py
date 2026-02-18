"""
Handover Export Routes
======================

Endpoints for generating and retrieving handover exports.

Routes:
- POST /v1/handover/export - Generate new export
- GET /v1/handover/export/{export_id} - Get export by ID
- GET /v1/handover/exports - List exports for yacht
"""

import logging
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from services.handover_export_service import HandoverExportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/handover", tags=["handover"])


class ExportRequest(BaseModel):
    """Request body for generating export."""
    handover_id: Optional[str] = Field(None, description="Specific handover ID to export")
    date_from: Optional[date] = Field(None, description="Start date filter")
    date_to: Optional[date] = Field(None, description="End date filter")
    export_type: str = Field("html", description="Export format: html, pdf, email")
    include_completed: bool = Field(False, description="Include completed items")
    item_ids: Optional[List[str]] = Field(None, description="Specific item IDs to export (for user draft exports)")
    filter_by_user: bool = Field(False, description="Filter items by user_id (added_by = user_id)")


class ExportResponse(BaseModel):
    """Response from export generation."""
    status: str
    export_id: str
    total_items: int
    sections_count: int
    document_hash: str
    generated_at: str
    html_preview_url: Optional[str] = None


@router.post("/export")
async def generate_export(
    request: ExportRequest,
    yacht_id: str = Query(..., description="Yacht ID"),
    user_id: str = Query(..., description="User ID generating export"),
    db_client=Depends(lambda: None)  # Will be injected by app
) -> ExportResponse:
    """
    Generate a handover export.

    Pulls items from the unified view (both pms_handover and handover_items),
    groups by section, enriches with entity details, and generates HTML.

    Returns export metadata. Use /export/{export_id}/html to get the content.
    """
    try:
        # Get db client from app state (injected via dependency)
        from integrations.supabase import get_supabase_client
        db = get_supabase_client()

        service = HandoverExportService(db)

        result = await service.generate_export(
            yacht_id=yacht_id,
            user_id=user_id,
            handover_id=request.handover_id,
            date_from=request.date_from,
            date_to=request.date_to,
            export_type=request.export_type,
            include_completed=request.include_completed,
            item_ids=request.item_ids,
            filter_by_user=request.filter_by_user
        )

        return ExportResponse(
            status="success",
            export_id=result.export_id,
            total_items=result.total_items,
            sections_count=len(result.sections),
            document_hash=result.document_hash,
            generated_at=result.generated_at.isoformat(),
            html_preview_url=f"/v1/handover/export/{result.export_id}/html" if result.export_id else None
        )

    except Exception as e:
        logger.exception(f"Error generating handover export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/html")
async def generate_export_html(
    request: ExportRequest,
    yacht_id: str = Query(..., description="Yacht ID"),
    user_id: str = Query(..., description="User ID generating export"),
) -> Response:
    """
    Generate and return HTML export directly.

    This is a convenience endpoint that returns the HTML content
    directly instead of just metadata.
    """
    try:
        from integrations.supabase import get_supabase_client
        db = get_supabase_client()

        service = HandoverExportService(db)

        result = await service.generate_export(
            yacht_id=yacht_id,
            user_id=user_id,
            handover_id=request.handover_id,
            date_from=request.date_from,
            date_to=request.date_to,
            export_type="html",
            include_completed=request.include_completed,
            item_ids=request.item_ids,
            filter_by_user=request.filter_by_user
        )

        return Response(
            content=result.html,
            media_type="text/html",
            headers={
                "X-Export-ID": result.export_id or "",
                "X-Document-Hash": result.document_hash,
                "X-Total-Items": str(result.total_items)
            }
        )

    except Exception as e:
        logger.exception(f"Error generating handover HTML: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exports")
async def list_exports(
    yacht_id: str = Query(..., description="Yacht ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List handover exports for a yacht.

    Returns export records with metadata (not the actual HTML content).
    """
    try:
        from integrations.supabase import get_supabase_client
        db = get_supabase_client()

        result = db.table("handover_exports").select(
            "id, draft_id, export_type, exported_at, exported_by_user_id, "
            "document_hash, export_status, file_name"
        ).eq("yacht_id", yacht_id).order(
            "exported_at", desc=True
        ).range(offset, offset + limit - 1).execute()

        return {
            "status": "success",
            "exports": result.data or [],
            "count": len(result.data or [])
        }

    except Exception as e:
        logger.exception(f"Error listing exports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{export_id}")
async def get_export(
    export_id: str,
    yacht_id: str = Query(..., description="Yacht ID")
):
    """
    Get export record by ID.
    """
    try:
        from integrations.supabase import get_supabase_client
        db = get_supabase_client()

        result = db.table("handover_exports").select("*").eq(
            "id", export_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Export not found")

        return {
            "status": "success",
            "export": result.data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]
