"""
Handover Export Routes
======================

Endpoints for generating and retrieving handover exports.

Routes:
- POST /v1/handover/export - Generate new export
- GET /v1/handover/export/{export_id} - Get export by ID
- GET /v1/handover/exports - List exports for yacht

Editable Workflow Routes (two-bucket storage):
- GET /v1/handover/export/{export_id}/content - Get parsed editable content
- POST /v1/handover/export/{export_id}/save-draft - Auto-save user edits
- POST /v1/handover/export/{export_id}/submit - User signs and submits
- POST /v1/handover/export/{export_id}/countersign - HOD countersigns
"""

import logging
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from services.handover_export_service import HandoverExportService
from services.handover_html_parser import parse_handover_html
from middleware.auth import get_authenticated_user

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


# =============================================================================
# EDITABLE WORKFLOW — Two-Bucket Storage Models
# =============================================================================

class SectionItem(BaseModel):
    id: str
    content: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    priority: Optional[str] = None


class Section(BaseModel):
    id: str
    title: str
    content: str
    items: List[SectionItem]
    is_critical: bool
    order: int


class SignatureData(BaseModel):
    image_base64: str
    signed_at: str
    signer_name: str
    signer_id: str


class SubmitRequest(BaseModel):
    sections: List[Section]
    userSignature: SignatureData


class CountersignRequest(BaseModel):
    hodSignature: SignatureData


# =============================================================================
# EDITABLE WORKFLOW — Endpoints
# =============================================================================

@router.get("/export/{export_id}/content")
async def get_export_content(
    export_id: str,
    user=Depends(get_authenticated_user)
):
    """Get parsed editable content for a handover export."""
    from integrations.supabase import get_supabase_client
    supabase = get_supabase_client()

    # Fetch export record with yacht name for lens display
    result = supabase.table("handover_exports").select(
        "id, handover_id, yacht_id, original_storage_url, edited_content, review_status, created_at, "
        "user_signature, user_signed_at, hod_signature, hod_signed_at, yachts(name)"
    ).eq("id", export_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Export not found")

    export_data = result.data

    # Extract yacht name from joined relation
    yachts = export_data.get("yachts")
    yacht_name = yachts.get("name") if isinstance(yachts, dict) else (yachts[0].get("name") if yachts else None)

    # If edited content exists, return it
    if export_data.get("edited_content"):
        return {
            "id": export_id,
            "sections": export_data["edited_content"].get("sections", []),
            "review_status": export_data["review_status"],
            "created_at": export_data.get("created_at"),
            "yacht_name": yacht_name,
            "user_signature": export_data.get("user_signature"),
            "user_signed_at": export_data.get("user_signed_at"),
            "hod_signature": export_data.get("hod_signature"),
            "hod_signed_at": export_data.get("hod_signed_at"),
            "from_cache": True
        }

    # Otherwise, fetch and parse original HTML
    original_url = export_data.get("original_storage_url")
    if not original_url:
        raise HTTPException(status_code=404, detail="Original HTML not available")

    # Download HTML from Supabase Storage
    storage_path = original_url.replace("handover-exports/", "")
    html_bytes = supabase.storage.from_("handover-exports").download(storage_path)
    html_content = html_bytes.decode("utf-8")

    # Parse HTML into editable structure
    document = parse_handover_html(html_content, export_id)

    return {
        "id": export_id,
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "content": s.content,
                "items": [
                    {
                        "id": i.id,
                        "content": i.content,
                        "entity_type": i.entity_type,
                        "entity_id": i.entity_id,
                        "priority": i.priority
                    }
                    for i in s.items
                ],
                "is_critical": s.is_critical,
                "order": s.order
            }
            for s in document.sections
        ],
        "review_status": export_data["review_status"],
        "created_at": export_data.get("created_at"),
        "yacht_name": yacht_name,
        "user_signature": export_data.get("user_signature"),
        "user_signed_at": export_data.get("user_signed_at"),
        "hod_signature": export_data.get("hod_signature"),
        "hod_signed_at": export_data.get("hod_signed_at"),
        "from_cache": False
    }


@router.post("/export/{export_id}/save-draft")
async def save_draft(
    export_id: str,
    sections: List[Section],
    user=Depends(get_authenticated_user)
):
    """Auto-save user edits without signature."""
    from integrations.supabase import get_supabase_client
    supabase = get_supabase_client()

    # Verify export exists and user has access
    result = supabase.table("handover_exports").select(
        "id, yacht_id, review_status"
    ).eq("id", export_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Export not found")

    if result.data["review_status"] != "pending_review":
        raise HTTPException(status_code=400, detail="Cannot edit after submission")

    # Update edited content
    supabase.table("handover_exports").update({
        "edited_content": {
            "sections": [s.dict() for s in sections],
            "last_saved_at": datetime.utcnow().isoformat(),
            "saved_by": user.id if hasattr(user, "id") else str(user)
        }
    }).eq("id", export_id).execute()

    return {"success": True, "saved_at": datetime.utcnow().isoformat()}


@router.post("/export/{export_id}/submit")
async def submit_export(
    export_id: str,
    request: SubmitRequest,
    user=Depends(get_authenticated_user)
):
    """User signs and submits handover for HOD approval."""
    from integrations.supabase import get_supabase_client
    supabase = get_supabase_client()

    # Fetch export
    result = supabase.table("handover_exports").select(
        "id, yacht_id, review_status, original_storage_url"
    ).eq("id", export_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Export not found")

    export_data = result.data

    if export_data["review_status"] != "pending_review":
        raise HTTPException(status_code=400, detail="Already submitted")

    yacht_id = export_data["yacht_id"]

    # Generate signed HTML with user's edits
    signed_html = _generate_signed_html(request.sections, request.userSignature)

    # Upload to Bucket 2 (signed)
    signed_path = f"{yacht_id}/signed/{export_id}.html"
    supabase.storage.from_("handover-exports").upload(
        signed_path,
        signed_html.encode("utf-8"),
        {"content-type": "text/html"}
    )

    # Update database record
    user_id = user.id if hasattr(user, "id") else str(user)
    supabase.table("handover_exports").update({
        "edited_content": {
            "sections": [s.dict() for s in request.sections]
        },
        "signed_storage_url": f"handover-exports/{signed_path}",
        "user_signature": request.userSignature.dict(),
        "user_signed_at": request.userSignature.signed_at,
        "user_submitted_at": datetime.utcnow().isoformat(),
        "review_status": "pending_hod_signature"
    }).eq("id", export_id).execute()

    # Create ledger notification for HOD
    _notify_hod_for_countersign(supabase, export_id, yacht_id, user)

    return {
        "success": True,
        "review_status": "pending_hod_signature",
        "signed_storage_url": f"handover-exports/{signed_path}"
    }


@router.post("/export/{export_id}/countersign")
async def countersign_export(
    export_id: str,
    request: CountersignRequest,
    user=Depends(get_authenticated_user)
):
    """HOD countersigns the handover to complete."""
    from integrations.supabase import get_supabase_client
    supabase = get_supabase_client()

    # Verify user is HOD
    user_id = user.id if hasattr(user, "id") else str(user)
    profile = supabase.table("auth_users_profiles").select(
        "role"
    ).eq("id", user_id).single().execute()

    if not profile.data or profile.data["role"] not in ["hod", "captain", "manager"]:
        raise HTTPException(status_code=403, detail="Only HOD+ can countersign")

    # Fetch export
    result = supabase.table("handover_exports").select(
        "id, yacht_id, review_status, signed_storage_url, edited_content, user_signature"
    ).eq("id", export_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Export not found")

    export_data = result.data

    if export_data["review_status"] != "pending_hod_signature":
        raise HTTPException(status_code=400, detail="Not awaiting countersign")

    yacht_id = export_data["yacht_id"]

    # Update signed HTML with both signatures
    signed_html = _generate_final_html(
        export_data["edited_content"]["sections"],
        export_data["user_signature"],
        request.hodSignature.dict()
    )

    signed_path = f"{yacht_id}/signed/{export_id}.html"
    supabase.storage.from_("handover-exports").update(
        signed_path,
        signed_html.encode("utf-8"),
        {"content-type": "text/html"}
    )

    # Update database record
    supabase.table("handover_exports").update({
        "hod_signature": request.hodSignature.dict(),
        "hod_signed_at": request.hodSignature.signed_at,
        "review_status": "complete"
    }).eq("id", export_id).execute()

    # Trigger embedding worker for indexing
    _trigger_indexing(supabase, export_id, yacht_id)

    return {
        "success": True,
        "review_status": "complete"
    }


# =============================================================================
# PRIVATE HELPERS
# =============================================================================

def _generate_signed_html(sections: List[Section], user_sig: SignatureData) -> str:
    """Generate HTML document with user's edits and signature."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head><title>Handover Export</title></head>",
        "<body>"
    ]

    for section in sorted(sections, key=lambda s: s.order):
        critical_class = " critical" if section.is_critical else ""
        html_parts.append(f'<section class="handover-section{critical_class}">')
        html_parts.append(f"<h2>{section.title}</h2>")
        html_parts.append(f"<p>{section.content}</p>")

        if section.items:
            html_parts.append("<ul>")
            for item in section.items:
                html_parts.append(f'<li class="{item.priority or "fyi"}">{item.content}</li>')
            html_parts.append("</ul>")

        html_parts.append("</section>")

    # User signature block
    html_parts.append('<div class="signatures">')
    html_parts.append('<div class="signature-block" data-role="outgoing">')
    html_parts.append(f'<img src="{user_sig.image_base64}" alt="User signature"/>')
    html_parts.append(f'<p>{user_sig.signer_name} — {user_sig.signed_at}</p>')
    html_parts.append('</div>')
    html_parts.append('<div class="signature-block" data-role="hod">')
    html_parts.append('<p>Awaiting HOD countersignature</p>')
    html_parts.append('</div>')
    html_parts.append('</div>')

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def _generate_final_html(sections: list, user_sig: dict, hod_sig: dict) -> str:
    """Generate final HTML with both signatures."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head><title>Handover Export - Complete</title></head>",
        "<body>"
    ]

    for section in sorted(sections, key=lambda s: s["order"]):
        critical_class = " critical" if section["is_critical"] else ""
        html_parts.append(f'<section class="handover-section{critical_class}">')
        html_parts.append(f"<h2>{section['title']}</h2>")
        html_parts.append(f"<p>{section['content']}</p>")

        if section.get("items"):
            html_parts.append("<ul>")
            for item in section["items"]:
                html_parts.append(f'<li class="{item.get("priority", "fyi")}">{item["content"]}</li>')
            html_parts.append("</ul>")

        html_parts.append("</section>")

    # Both signatures
    html_parts.append('<div class="signatures">')
    html_parts.append('<div class="signature-block" data-role="outgoing">')
    html_parts.append(f'<img src="{user_sig["image_base64"]}" alt="User signature"/>')
    html_parts.append(f'<p>{user_sig["signer_name"]} — {user_sig["signed_at"]}</p>')
    html_parts.append('</div>')
    html_parts.append('<div class="signature-block" data-role="hod">')
    html_parts.append(f'<img src="{hod_sig["image_base64"]}" alt="HOD signature"/>')
    html_parts.append(f'<p>{hod_sig["signer_name"]} — {hod_sig["signed_at"]}</p>')
    html_parts.append('</div>')
    html_parts.append('</div>')

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def _notify_hod_for_countersign(supabase, export_id: str, yacht_id: str, user):
    """Create ledger notification for HOD users."""
    user_id = user.id if hasattr(user, "id") else str(user)
    user_email = user.email if hasattr(user, "email") else user_id

    # Get HOD users for this yacht
    hod_users = supabase.table("auth_users_profiles").select(
        "id, full_name"
    ).eq("yacht_id", yacht_id).in_("role", ["hod", "captain", "manager"]).execute()

    # Create ledger entries for each HOD
    for hod in (hod_users.data or []):
        supabase.table("pms_audit_log").insert({
            "yacht_id": yacht_id,
            "entity_type": "handover_export",
            "entity_id": export_id,
            "action": "requires_countersignature",
            "event_type": "handover_pending_countersign",
            "change_summary": f"Handover from {user_email} requires your countersignature",
            "user_id": hod["id"],
            "metadata": {
                "submitted_by": user_id,
                "submitted_at": datetime.utcnow().isoformat()
            }
        }).execute()


def _trigger_indexing(supabase, export_id: str, yacht_id: str):
    """Trigger embedding worker to index the signed handover."""
    try:
        supabase.table("search_index_queue").insert({
            "entity_type": "handover_export",
            "entity_id": export_id,
            "yacht_id": yacht_id,
            "priority": 1,
            "status": "pending"
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to queue indexing for export {export_id}: {e}")


__all__ = ["router"]
