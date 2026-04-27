"""
Part Lens Routes
================

FastAPI routes for Part Lens v2 actions.

Endpoints:
- GET  /v1/parts/suggestions     - Get context-valid actions with prefill
- POST /v1/parts/shopping-list/prefill - Prefill for add_to_shopping_list
- POST /v1/parts/adjust-stock/prefill  - Prefill for adjust_stock_quantity
- GET  /v1/parts/low-stock       - View parts below min_level

Stock computation rule:
  suggested_qty = round_up(max(min_level - on_hand, 1), reorder_multiple)

All routes require JWT authentication and yacht isolation validation.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from middleware.auth import get_authenticated_user
from handlers.part_handlers import get_part_handlers

logger = logging.getLogger(__name__)


# ============================================================================
# SUPABASE CLIENT
# ============================================================================

def get_tenant_supabase_client(tenant_key_alias: str) -> Client:
    """Get tenant-specific Supabase client instance."""
    if not tenant_key_alias:
        raise ValueError("tenant_key_alias is required for tenant DB access")

    url = os.getenv(f"{tenant_key_alias}_SUPABASE_URL")
    key = os.getenv(f"{tenant_key_alias}_SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError(f"Missing tenant credentials for {tenant_key_alias}")

    return create_client(url, key)


def get_default_supabase_client() -> Optional[Client]:
    """Get default tenant Supabase client."""
    default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")
    url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/v1/parts", tags=["part-lens"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SuggestedAction(BaseModel):
    """A suggested action with prefill data."""
    action_id: str
    label: str
    variant: str
    prefill: Optional[Dict[str, Any]] = None
    field_metadata: Optional[List[Dict[str, Any]]] = None
    is_primary: bool = False


class PartSuggestionsResponse(BaseModel):
    """Response for part suggestions endpoint."""
    part_id: str
    part_name: Optional[str] = None
    part_number: Optional[str] = None
    stock: Dict[str, Any]
    suggested_actions: List[SuggestedAction]
    warnings: List[str] = []


class LowStockItem(BaseModel):
    """A part below minimum stock level."""
    id: str
    name: str
    part_number: Optional[str] = None
    is_critical: bool = False
    on_hand: int
    min_level: int
    shortage: int
    suggested_order_qty: int
    reorder_multiple: int = 1
    department: Optional[str] = None


class LowStockResponse(BaseModel):
    """Response for low stock endpoint."""
    parts: List[LowStockItem]
    total_low_stock: int
    critical_count: int
    total_suggested_order_value: Optional[float] = None


class PrefillResponse(BaseModel):
    """Response for prefill endpoints."""
    status: str
    prefill: Dict[str, Any]
    field_metadata: Dict[str, Any]


# ============================================================================
# IMAGE UPLOAD MODELS (MVP)
# ============================================================================

class UploadImageRequest(BaseModel):
    """Request to upload part image."""
    # Note: yacht_id comes from JWT auth context, not request body
    part_id: str
    file_name: str
    mime_type: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class UploadImageResponse(BaseModel):
    """Response from upload image endpoint."""
    status: str
    part_id: str
    part_name: Optional[str] = None
    storage_path: str
    bucket: str
    image_url: str
    message: str


class UpdateImageRequest(BaseModel):
    """Request to update part image metadata."""
    # Note: yacht_id comes from JWT auth context, not request body
    image_id: str  # Actually part_id for MVP
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class UpdateImageResponse(BaseModel):
    """Response from update image endpoint."""
    status: str
    part_id: str
    image_file_name: Optional[str] = None
    message: str


class DeleteImageRequest(BaseModel):
    """Request to delete part image (SIGNED action)."""
    # Note: yacht_id comes from JWT auth context, not request body
    image_id: str  # Actually part_id for MVP
    reason: str
    signature: Dict[str, Any]


class DeleteImageResponse(BaseModel):
    """Response from delete image endpoint."""
    status: str
    part_id: str
    deleted_path: Optional[str] = None
    reason: str
    message: str


# ============================================================================
# ROUTES
# ============================================================================

@router.get("/suggestions")
async def get_part_suggestions(
    part_id: str = Query(..., description="Part UUID"),
    auth: dict = Depends(get_authenticated_user),
) -> PartSuggestionsResponse:
    """Get context-valid actions for a part with prefill data."""
    tenant_key_alias = auth.get("tenant_key_alias")
    db = get_tenant_supabase_client(tenant_key_alias) if tenant_key_alias else get_default_supabase_client()
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")
    handlers = get_part_handlers(db)
    try:
        return await handlers["get_part_suggestions"](
            yacht_id=auth["yacht_id"],
            user_id=auth["user_id"],
            role=auth.get("role", "crew"),
            part_id=part_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"get_part_suggestions failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve part suggestions")


@router.post("/shopping-list/prefill")
async def prefill_add_to_shopping_list(
    part_id: str = Query(...),
    auth: dict = Depends(get_authenticated_user),
) -> PrefillResponse:
    """Prefill values for add_to_shopping_list action."""
    tenant_key_alias = auth.get("tenant_key_alias")
    db = get_tenant_supabase_client(tenant_key_alias) if tenant_key_alias else get_default_supabase_client()
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")
    handlers = get_part_handlers(db)
    try:
        return await handlers["get_shopping_list_prefill"](
            yacht_id=auth["yacht_id"],
            part_id=part_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"prefill_add_to_shopping_list failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute prefill")


@router.post("/adjust-stock/prefill")
async def prefill_adjust_stock(
    part_id: str = Query(...),
    auth: dict = Depends(get_authenticated_user),
) -> PrefillResponse:
    """Prefill values for adjust_stock_quantity action."""
    tenant_key_alias = auth.get("tenant_key_alias")
    db = get_tenant_supabase_client(tenant_key_alias) if tenant_key_alias else get_default_supabase_client()
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")
    handlers = get_part_handlers(db)
    try:
        return await handlers["get_adjust_stock_prefill"](
            yacht_id=auth["yacht_id"],
            part_id=part_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"prefill_adjust_stock failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute prefill")


@router.get("/low-stock")
async def get_low_stock(
    department: str = Query(None, description="Filter by department"),
    threshold_percent: float = Query(None, description="Filter by % of min_level"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    auth: dict = Depends(get_authenticated_user),
) -> LowStockResponse:
    """View parts below minimum stock level, sorted by criticality then shortage."""
    tenant_key_alias = auth.get("tenant_key_alias")
    db = get_tenant_supabase_client(tenant_key_alias) if tenant_key_alias else get_default_supabase_client()
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")
    handlers = get_part_handlers(db)
    try:
        return await handlers["get_low_stock"](
            yacht_id=auth["yacht_id"],
            department=department,
            threshold_percent=threshold_percent,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"get_low_stock failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve low stock data")


# ============================================================================
# IMAGE UPLOAD ROUTES (MVP)
# ============================================================================

@router.post("/upload-image", response_model=UploadImageResponse)
async def upload_part_image(
    file: UploadFile = File(...),
    part_id: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    auth: dict = Depends(get_authenticated_user),
) -> UploadImageResponse:
    """
    Upload part image directly to Supabase Storage.

    Accepts multipart/form-data with actual file upload.
    """
    try:
        user_id = auth["user_id"]
        yacht_id = auth["yacht_id"]
        tenant_key_alias = auth["tenant_key_alias"]

        # Get tenant-specific Supabase client
        db = get_tenant_supabase_client(tenant_key_alias) if tenant_key_alias else get_default_supabase_client()

        if not db:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Read file content
        file_content = await file.read()

        # Parse tags if provided
        tags_list = tags.split(',') if tags else None

        # Get part handlers
        from handlers.part_handlers import get_part_handlers
        handlers = get_part_handlers(db)

        # Call handler with actual file data
        result = await handlers["upload_part_image"](
            yacht_id=yacht_id,
            user_id=user_id,
            part_id=part_id,
            file_name=file.filename,
            file_content=file_content,
            mime_type=file.content_type,
            description=description,
            tags=tags_list,
        )

        return UploadImageResponse(**result)

    except ValueError as e:
        logger.error(f"upload_part_image validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"upload_part_image failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-image", response_model=UpdateImageResponse)
async def update_part_image(
    request: UpdateImageRequest,
    auth: dict = Depends(get_authenticated_user),
) -> UpdateImageResponse:
    """
    Update part image metadata (description).

    For MVP, only the description field can be updated.
    """
    try:
        user_id = auth["user_id"]
        yacht_id = auth["yacht_id"]
        tenant_key_alias = auth["tenant_key_alias"]

        # Get tenant-specific Supabase client
        db = get_tenant_supabase_client(tenant_key_alias) if tenant_key_alias else get_default_supabase_client()

        if not db:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Get part handlers
        from handlers.part_handlers import get_part_handlers
        handlers = get_part_handlers(db)

        # Call handler
        result = await handlers["update_part_image"](
            yacht_id=yacht_id,
            user_id=user_id,
            image_id=request.image_id,
            description=request.description,
            tags=request.tags,
        )

        return UpdateImageResponse(**result)

    except ValueError as e:
        logger.error(f"update_part_image validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"update_part_image failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update image")


@router.post("/delete-image", response_model=DeleteImageResponse)
async def delete_part_image(
    request: DeleteImageRequest,
    auth: dict = Depends(get_authenticated_user),
) -> DeleteImageResponse:
    """
    Delete part image (SIGNED action - requires PIN+TOTP signature).

    Captain/Manager role only.
    """
    try:
        user_id = auth["user_id"]
        yacht_id = auth["yacht_id"]
        tenant_key_alias = auth["tenant_key_alias"]

        # Get tenant-specific Supabase client
        db = get_tenant_supabase_client(tenant_key_alias) if tenant_key_alias else get_default_supabase_client()

        if not db:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Get part handlers
        from handlers.part_handlers import get_part_handlers
        handlers = get_part_handlers(db)

        # Call handler (signature validation done in handler)
        result = await handlers["delete_part_image"](
            yacht_id=yacht_id,
            user_id=user_id,
            image_id=request.image_id,
            reason=request.reason,
            signature=request.signature,
        )

        return DeleteImageResponse(**result)

    except ValueError as e:
        logger.error(f"delete_part_image validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"delete_part_image failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete image")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ["router"]
