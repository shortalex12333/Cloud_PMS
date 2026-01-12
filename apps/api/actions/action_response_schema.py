"""
Action Response Schema
======================

UNIVERSAL response format for ALL action handlers.
Front-end relies on this exact structure - DO NOT deviate.

Design Principles:
1. Every response has the same envelope structure
2. Data types have known shapes (equipment, part, work_order, etc.)
3. File access always uses signed URLs with expiry
4. Available actions are attached to returned entities
5. Pagination is standardized

This ensures:
- Front-end knows exactly what to expect
- Clean orchestration across all handlers
- Consistent error handling
- Universal rendering components
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union, Literal
from datetime import datetime, timezone, timedelta
from enum import Enum
import json


# =============================================================================
# RESPONSE ENVELOPE (every response wrapped in this)
# =============================================================================

@dataclass
class ActionResponseEnvelope:
    """
    Universal response wrapper for ALL action responses.

    Front-end should ALWAYS expect this structure:
    {
        "success": true/false,
        "action_id": "view_equipment",
        "entity_id": "eq-123",
        "entity_type": "equipment",
        "data": { ... entity-specific data ... },
        "files": [ ... file references ... ],
        "available_actions": [ ... actions for this entity ... ],
        "pagination": { ... if applicable ... },
        "mutation_preview": { ... for MUTATE prepare phase ... },
        "meta": { ... timing, source, etc ... },
        "error": null or { ... error details ... }
    }
    """
    success: bool
    action_id: str
    entity_id: str
    entity_type: str
    data: Optional[Dict] = None
    files: Optional[List[Dict]] = None
    available_actions: Optional[List[Dict]] = None
    pagination: Optional[Dict] = None
    mutation_preview: Optional[Dict] = None  # For MUTATE handlers (prepare phase)
    meta: Optional[Dict] = None
    error: Optional[Dict] = None

    def to_dict(self) -> Dict:
        result = {
            "success": self.success,
            "action_id": self.action_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "data": self.data,
            "files": self.files,
            "available_actions": self.available_actions,
            "pagination": self.pagination,
            "mutation_preview": self.mutation_preview,
            "meta": self.meta,
            "error": self.error
        }
        # Remove None values for cleaner JSON
        return {k: v for k, v in result.items() if v is not None}


# =============================================================================
# FILE ACCESS SCHEMA (Supabase Storage signed URLs)
# =============================================================================

class FileType(str, Enum):
    """Supported file types"""
    PDF = "pdf"
    IMAGE = "image"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


@dataclass
class FileReference:
    """
    Secure file reference with signed URL.

    Front-end renders:
    - type="pdf" → PDF viewer component
    - type="image" → Image gallery component
    - type="document" → Document viewer
    - type="video" → Video player

    signed_url expires after expires_at - front-end must refresh if expired.
    """
    file_id: str
    filename: str
    file_type: FileType
    mime_type: str
    size_bytes: Optional[int]
    signed_url: str                    # Supabase signed URL for download/view
    expires_at: str                    # ISO timestamp when URL expires
    thumbnail_url: Optional[str] = None  # For images/PDFs
    storage_bucket: str = "documents"  # Supabase bucket name
    storage_path: str = ""             # Path within bucket

    # Display metadata
    display_name: Optional[str] = None  # Human-friendly name
    description: Optional[str] = None
    page_count: Optional[int] = None    # For PDFs

    def to_dict(self) -> Dict:
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "file_type": self.file_type.value if isinstance(self.file_type, FileType) else self.file_type,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "signed_url": self.signed_url,
            "expires_at": self.expires_at,
            "thumbnail_url": self.thumbnail_url,
            "storage_bucket": self.storage_bucket,
            "storage_path": self.storage_path,
            "display_name": self.display_name or self.filename,
            "description": self.description,
            "page_count": self.page_count
        }


# =============================================================================
# AVAILABLE ACTIONS SCHEMA
# =============================================================================

@dataclass
class AvailableAction:
    """
    Action that can be performed on the returned entity.

    Front-end renders as:
    - variant="READ" + is_primary=True → Primary button
    - variant="READ" + is_primary=False → Secondary action in menu
    - variant="MUTATE" → Dropdown menu item (requires confirmation flow)
    """
    action_id: str
    label: str
    variant: Literal["READ", "MUTATE"]
    icon: str = ""
    is_primary: bool = False
    requires_signature: bool = False
    confirmation_message: Optional[str] = None
    disabled: bool = False
    disabled_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "label": self.label,
            "variant": self.variant,
            "icon": self.icon,
            "is_primary": self.is_primary,
            "requires_signature": self.requires_signature,
            "confirmation_message": self.confirmation_message,
            "disabled": self.disabled,
            "disabled_reason": self.disabled_reason
        }


# =============================================================================
# PAGINATION SCHEMA
# =============================================================================

@dataclass
class PaginationInfo:
    """
    Standard pagination for list responses.

    Front-end uses:
    - offset/limit for infinite scroll
    - has_more to know if more data available
    - total_count for "showing X of Y"
    """
    offset: int
    limit: int
    total_count: int
    has_more: bool

    def to_dict(self) -> Dict:
        return {
            "offset": self.offset,
            "limit": self.limit,
            "total_count": self.total_count,
            "has_more": self.has_more
        }


# =============================================================================
# META SCHEMA
# =============================================================================

@dataclass
class ResponseMeta:
    """
    Metadata about the response.
    """
    executed_at: str                   # ISO timestamp
    latency_ms: int                    # Execution time
    source: str = "supabase"           # Data source: supabase, cache, stub
    cache_hit: bool = False
    api_version: str = "v1"

    def to_dict(self) -> Dict:
        return {
            "executed_at": self.executed_at,
            "latency_ms": self.latency_ms,
            "source": self.source,
            "cache_hit": self.cache_hit,
            "api_version": self.api_version
        }


# =============================================================================
# ERROR SCHEMA
# =============================================================================

@dataclass
class ErrorDetail:
    """
    Standardized error response.

    Front-end uses:
    - code for programmatic handling
    - message for user display
    - field for form validation errors
    - suggestions for recovery options
    """
    code: str                          # e.g., "NOT_FOUND", "PERMISSION_DENIED"
    message: str                       # Human-readable message
    field: Optional[str] = None        # For validation errors
    suggestions: Optional[List[str]] = None  # Recovery suggestions

    def to_dict(self) -> Dict:
        result = {
            "code": self.code,
            "message": self.message
        }
        if self.field:
            result["field"] = self.field
        if self.suggestions:
            result["suggestions"] = self.suggestions
        return result


# =============================================================================
# ENTITY DATA SCHEMAS (domain-specific shapes)
# =============================================================================

# These define the exact shape of `data` for each entity_type.
# Front-end components expect these exact fields.

ENTITY_SCHEMAS = {
    "equipment": {
        "fields": [
            "id", "canonical_label", "category", "manufacturer", "model",
            "serial_number", "location", "install_date", "last_service_date",
            "running_hours", "status", "notes", "risk_score"
        ],
        "relations": ["parts", "faults", "work_orders", "manual_sections"]
    },

    "part": {
        "fields": [
            "id", "canonical_name", "part_number", "manufacturer", "description",
            "quantity", "min_quantity", "max_quantity", "unit", "location",
            "bin_number", "unit_cost", "supplier", "last_ordered_at", "last_used_at"
        ],
        "computed": ["stock_status", "is_low_stock", "reorder_needed"]
    },

    "work_order": {
        "fields": [
            "id", "title", "description", "status", "priority", "created_at",
            "due_date", "completed_at", "resolution", "equipment_id", "assigned_to"
        ],
        "relations": ["equipment", "assignee", "parts", "checklist", "notes", "photos"],
        "computed": ["is_overdue", "days_open", "progress_percent"]
    },

    "fault": {
        "fields": [
            "id", "fault_code", "description", "severity", "status",
            "reported_at", "resolved_at", "equipment_id", "reported_by"
        ],
        "relations": ["equipment", "work_orders", "suggested_parts"],
        "computed": ["is_active", "days_open"]
    },

    "document_chunk": {
        "fields": [
            "id", "document_id", "section_title", "content", "page_number",
            "section_number", "storage_path"
        ],
        "relations": ["document", "related_chunks"]
    },

    "handover_item": {
        "fields": [
            "id", "summary", "content", "category", "author", "created_at",
            "linked_entity_id", "linked_entity_type"
        ],
        "relations": ["linked_entity"]
    },

    "purchase": {
        "fields": [
            "id", "status", "supplier", "total_amount", "currency",
            "tracking_number", "expected_delivery", "shipped_at", "delivered_at",
            "requested_by", "approved_by"
        ],
        "relations": ["items", "invoices"],
        "computed": ["is_delivered", "is_overdue"]
    },

    "checklist": {
        "fields": [
            "id", "title", "category", "work_order_id", "created_at"
        ],
        "relations": ["items"],
        "computed": ["completed_count", "total_count", "progress_percent"]
    },

    "crew": {
        "fields": [
            "id", "name", "role", "department", "email", "phone"
        ],
        "relations": ["hours_of_rest", "assigned_work_orders"]
    }
}


# =============================================================================
# STOCK STATUS ENUM (for inventory)
# =============================================================================

class StockStatus(str, Enum):
    """Stock status for inventory items"""
    IN_STOCK = "IN_STOCK"
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    OVERSTOCKED = "OVERSTOCKED"
    ON_ORDER = "ON_ORDER"


# =============================================================================
# WORK ORDER STATUS ENUM
# =============================================================================

class WorkOrderStatus(str, Enum):
    """Work order status values"""
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_PARTS = "pending_parts"
    COMPLETED = "completed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


# =============================================================================
# SEVERITY ENUM
# =============================================================================

class Severity(str, Enum):
    """Severity levels for faults/issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# MUTATION STATE & PREVIEW (for MUTATE handlers)
# =============================================================================

class MutationState(str, Enum):
    """State of a mutation in the prepare/commit flow"""
    PENDING = "pending"              # Awaiting user confirmation
    CONFIRMED = "confirmed"          # User confirmed, ready to commit
    COMMITTED = "committed"          # Successfully executed
    FAILED = "failed"                # Execution failed
    EXPIRED = "expired"              # Timeout before commit
    CANCELLED = "cancelled"          # User cancelled


@dataclass
class MutationPreview:
    """
    Preview of mutation to be performed.

    Front-end uses this to:
    1. Show confirmation dialog with changes preview
    2. Determine if signature is required
    3. Track mutation_id for commit phase

    Flow:
    1. User initiates action → prepare() called
    2. prepare() returns MutationPreview
    3. Front-end shows confirmation dialog
    4. User confirms (+ signs if required)
    5. commit() called with mutation_id
    6. Final result returned
    """
    mutation_id: str                 # Unique ID to track this mutation
    action: str                      # Action being performed
    changes: List[Dict]              # List of {field, from, to} changes
    requires_signature: bool = False
    confirmation_message: Optional[str] = None
    warning: Optional[str] = None    # Optional warning to display
    expires_at: Optional[str] = None # When this mutation expires if not committed

    def to_dict(self) -> Dict:
        return {
            "mutation_id": self.mutation_id,
            "action": self.action,
            "changes": self.changes,
            "requires_signature": self.requires_signature,
            "confirmation_message": self.confirmation_message,
            "warning": self.warning,
            "expires_at": self.expires_at
        }


# =============================================================================
# RESPONSE BUILDER HELPERS
# =============================================================================

class ResponseBuilder:
    """
    Helper to build standardized responses.

    Usage:
        builder = ResponseBuilder("view_equipment", "eq-123", "equipment")
        builder.set_data(equipment_data)
        builder.add_file(pdf_reference)
        builder.add_available_action(edit_action)
        return builder.build()
    """

    def __init__(
        self,
        action_id: str,
        entity_id: str,
        entity_type: str,
        yacht_id: str = ""
    ):
        self.action_id = action_id
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.yacht_id = yacht_id
        self._data: Optional[Dict] = None
        self._files: List[Dict] = []
        self._available_actions: List[Dict] = []
        self._pagination: Optional[Dict] = None
        self._error: Optional[Dict] = None
        self._mutation_preview: Optional[Dict] = None
        self._start_time = datetime.now(timezone.utc)

    def set_data(self, data: Dict) -> "ResponseBuilder":
        """Set the main response data"""
        self._data = data
        return self

    def add_file(self, file_ref: Union[FileReference, Dict]) -> "ResponseBuilder":
        """Add a file reference"""
        if isinstance(file_ref, FileReference):
            self._files.append(file_ref.to_dict())
        else:
            self._files.append(file_ref)
        return self

    def add_files(self, file_refs: List[Union[FileReference, Dict]]) -> "ResponseBuilder":
        """Add multiple file references"""
        for f in file_refs:
            self.add_file(f)
        return self

    def add_available_action(self, action: Union[AvailableAction, Dict]) -> "ResponseBuilder":
        """Add an available action"""
        if isinstance(action, AvailableAction):
            self._available_actions.append(action.to_dict())
        else:
            self._available_actions.append(action)
        return self

    def add_available_actions(self, actions: List[Union[AvailableAction, Dict]]) -> "ResponseBuilder":
        """Add multiple available actions"""
        for a in actions:
            self.add_available_action(a)
        return self

    def set_pagination(
        self,
        offset: int,
        limit: int,
        total_count: int
    ) -> "ResponseBuilder":
        """Set pagination info"""
        self._pagination = PaginationInfo(
            offset=offset,
            limit=limit,
            total_count=total_count,
            has_more=(offset + limit) < total_count
        ).to_dict()
        return self

    def set_error(
        self,
        code: str,
        message: str,
        field: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ) -> "ResponseBuilder":
        """Set error (makes success=False)"""
        self._error = ErrorDetail(
            code=code,
            message=message,
            field=field,
            suggestions=suggestions
        ).to_dict()
        return self

    def set_mutation_preview(self, preview: MutationPreview) -> "ResponseBuilder":
        """Set mutation preview for MUTATE handlers"""
        self._mutation_preview = preview.to_dict()
        return self

    def build(self, source: str = "supabase") -> Dict:
        """Build the final response"""
        latency_ms = int((datetime.now(timezone.utc) - self._start_time).total_seconds() * 1000)

        meta = ResponseMeta(
            executed_at=datetime.now(timezone.utc).isoformat(),
            latency_ms=latency_ms,
            source=source
        ).to_dict()

        response = ActionResponseEnvelope(
            success=self._error is None,
            action_id=self.action_id,
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            data=self._data,
            files=self._files if self._files else None,
            available_actions=self._available_actions if self._available_actions else None,
            pagination=self._pagination,
            mutation_preview=self._mutation_preview,
            meta=meta,
            error=self._error
        )

        return response.to_dict()

    # =========================================================================
    # STATIC HELPERS (for simpler handler code)
    # =========================================================================

    @staticmethod
    def success(action: str, result: Dict, message: str = "") -> Dict:
        """Quick success response builder."""
        return {
            "status": "success",
            "action": action,
            "result": result,
            "message": message
        }

    @staticmethod
    def error(action: str, error_code: str, message: str) -> Dict:
        """Quick error response builder."""
        return {
            "status": "error",
            "action": action,
            "error_code": error_code,
            "message": message
        }


# =============================================================================
# SIGNED URL GENERATOR (Supabase Storage)
# =============================================================================

class SignedUrlGenerator:
    """
    Generate signed URLs for Supabase storage files.

    Usage:
        generator = SignedUrlGenerator(supabase_client)
        file_ref = generator.create_file_reference(
            bucket="documents",
            path="manuals/engine_manual.pdf",
            filename="CAT 3512B Manual.pdf",
            expires_in_minutes=30
        )
    """

    # Signed URL TTL (default 30 minutes)
    DEFAULT_EXPIRY_MINUTES = 30

    # File type detection
    MIME_TO_TYPE = {
        "application/pdf": FileType.PDF,
        "image/jpeg": FileType.IMAGE,
        "image/png": FileType.IMAGE,
        "image/gif": FileType.IMAGE,
        "image/webp": FileType.IMAGE,
        "application/msword": FileType.DOCUMENT,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCUMENT,
        "application/vnd.ms-excel": FileType.SPREADSHEET,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.SPREADSHEET,
        "video/mp4": FileType.VIDEO,
        "video/quicktime": FileType.VIDEO,
        "audio/mpeg": FileType.AUDIO,
        "audio/m4a": FileType.AUDIO,
    }

    def __init__(self, supabase_client):
        self.client = supabase_client

    def _detect_file_type(self, mime_type: str) -> FileType:
        """Detect file type from MIME type"""
        return self.MIME_TO_TYPE.get(mime_type, FileType.OTHER)

    def _detect_mime_type(self, filename: str) -> str:
        """Detect MIME type from filename"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

    def create_signed_url(
        self,
        bucket: str,
        path: str,
        expires_in_seconds: int = 1800
    ) -> Optional[str]:
        """
        Create a signed URL for a storage file.

        Args:
            bucket: Supabase storage bucket name
            path: Path within the bucket
            expires_in_seconds: URL validity (default 30 minutes)

        Returns:
            Signed URL string or None if failed
        """
        if not self.client:
            return None

        try:
            result = self.client.storage.from_(bucket).create_signed_url(
                path,
                expires_in_seconds
            )
            return result.get("signedURL") or result.get("signed_url")
        except Exception as e:
            import logging
            logging.error(f"Failed to create signed URL: {bucket}/{path} - {e}")
            return None

    def create_file_reference(
        self,
        bucket: str,
        path: str,
        filename: str,
        file_id: Optional[str] = None,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        size_bytes: Optional[int] = None,
        page_count: Optional[int] = None,
        mime_type: Optional[str] = None,
        expires_in_minutes: int = DEFAULT_EXPIRY_MINUTES
    ) -> Optional[FileReference]:
        """
        Create a complete FileReference with signed URL.

        Args:
            bucket: Supabase storage bucket
            path: Path within bucket
            filename: Original filename
            file_id: Unique identifier (generated if not provided)
            display_name: Human-friendly name
            description: File description
            size_bytes: File size
            page_count: Page count (for PDFs)
            mime_type: MIME type (detected if not provided)
            expires_in_minutes: Signed URL validity

        Returns:
            FileReference with signed URL or None if failed
        """
        import uuid

        # Detect MIME type if not provided
        if not mime_type:
            mime_type = self._detect_mime_type(filename)

        file_type = self._detect_file_type(mime_type)

        # Create signed URL
        expires_in_seconds = expires_in_minutes * 60
        signed_url = self.create_signed_url(bucket, path, expires_in_seconds)

        if not signed_url:
            return None

        # Calculate expiry timestamp
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)).isoformat()

        return FileReference(
            file_id=file_id or str(uuid.uuid4()),
            filename=filename,
            file_type=file_type,
            mime_type=mime_type,
            size_bytes=size_bytes,
            signed_url=signed_url,
            expires_at=expires_at,
            storage_bucket=bucket,
            storage_path=path,
            display_name=display_name or filename,
            description=description,
            page_count=page_count
        )


# =============================================================================
# ACTIONS FOR ENTITY HELPER
# =============================================================================

def get_available_actions_for_entity(
    entity_type: str,
    entity_id: str,
    user_role: str = "crew"
) -> List[AvailableAction]:
    """
    Get available actions for an entity based on type and user role.

    This is called by handlers to attach appropriate actions to responses.
    """
    from action_registry import get_registry, ActionVariant

    registry = get_registry()
    actions = registry.get_actions_for_entity(entity_type)

    available = []
    for action in actions:
        # In future: filter by user role/permissions
        available.append(AvailableAction(
            action_id=action.action_id,
            label=action.label,
            variant="READ" if action.variant == ActionVariant.READ else "MUTATE",
            icon=action.ui.icon if action.ui else "",
            is_primary=action.ui.primary if action.ui else False,
            requires_signature=action.mutation.requires_signature if action.mutation else False,
            confirmation_message=action.mutation.confirmation_message if action.mutation else None
        ))

    return available


# =============================================================================
# EXAMPLE RESPONSE
# =============================================================================

EXAMPLE_RESPONSE = """
{
    "success": true,
    "action_id": "view_equipment",
    "entity_id": "eq-12345",
    "entity_type": "equipment",
    "data": {
        "id": "eq-12345",
        "canonical_label": "Main Engine Generator 1",
        "category": "propulsion",
        "manufacturer": "Caterpillar",
        "model": "3512B",
        "serial_number": "CAT3512B-001",
        "location": "Engine Room - Port",
        "install_date": "2020-01-15",
        "last_service_date": "2024-06-20",
        "running_hours": 12450,
        "status": "operational",
        "risk_score": 0.23
    },
    "files": [
        {
            "file_id": "doc-001",
            "filename": "CAT_3512B_Service_Manual.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size_bytes": 15234567,
            "signed_url": "https://xyz.supabase.co/storage/v1/object/sign/documents/manuals/cat_3512b.pdf?token=...",
            "expires_at": "2026-01-06T19:30:00+00:00",
            "display_name": "Service Manual",
            "page_count": 342
        }
    ],
    "available_actions": [
        {
            "action_id": "view_maintenance_history",
            "label": "Maintenance History",
            "variant": "READ",
            "icon": "history",
            "is_primary": false,
            "requires_signature": false
        },
        {
            "action_id": "create_work_order",
            "label": "Create Work Order",
            "variant": "MUTATE",
            "icon": "plus",
            "is_primary": false,
            "requires_signature": true,
            "confirmation_message": "Create work order for this equipment?"
        }
    ],
    "meta": {
        "executed_at": "2026-01-06T18:30:00+00:00",
        "latency_ms": 45,
        "source": "supabase",
        "api_version": "v1"
    }
}
"""


if __name__ == "__main__":
    # Example usage
    print("=" * 60)
    print("ACTION RESPONSE SCHEMA")
    print("=" * 60)

    # Build example response
    builder = ResponseBuilder("view_equipment", "eq-12345", "equipment")
    builder.set_data({
        "id": "eq-12345",
        "canonical_label": "Main Engine Generator 1",
        "manufacturer": "Caterpillar",
        "model": "3512B",
        "status": "operational"
    })

    # Add a file
    builder.add_file(FileReference(
        file_id="doc-001",
        filename="CAT_3512B_Manual.pdf",
        file_type=FileType.PDF,
        mime_type="application/pdf",
        size_bytes=15234567,
        signed_url="https://example.supabase.co/storage/...",
        expires_at="2026-01-06T19:30:00+00:00",
        page_count=342
    ))

    # Add available actions
    builder.add_available_action(AvailableAction(
        action_id="view_maintenance_history",
        label="Maintenance History",
        variant="READ",
        icon="history"
    ))
    builder.add_available_action(AvailableAction(
        action_id="create_work_order",
        label="Create Work Order",
        variant="MUTATE",
        icon="plus",
        requires_signature=True,
        confirmation_message="Create work order for this equipment?"
    ))

    response = builder.build()
    print("\nExample Response:")
    print(json.dumps(response, indent=2))
