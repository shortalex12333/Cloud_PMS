# Attachment Upload Endpoints - Implementation Plan

**Created:** 2026-01-30
**Status:** Ready for implementation after PR #26 merge
**Related:** Work Order Lens V2 Embeddings Phase 2

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          User Upload Flow                                      │
└──────────────────────────────────────────────────────────────────────────────┘

Frontend Upload
    │
    ├─► Cloud_PMS Proxy Endpoint (/api/work_orders/{id}/upload)
    │   └─► Validates JWT, yacht_id, entity exists
    │   └─► Writes to pms_attachments (METADATA ONLY)
    │   └─► Uploads file to Supabase Storage (pms-work-order-attachments bucket)
    │
    ├─► Image-Processing Service (if image/PDF)
    │   └─► OCR extraction via Tesseract/PyPDF2
    │   └─► Writes to pms_image_uploads (separate tracking table)
    │   └─► Returns extracted text
    │
    └─► Digest-Local Service (if needs ingestion)
        └─► Entity extraction (parts, suppliers, etc.)
        └─► Graph population for RAG
        └─► Update pms_attachments.related_text
```

## Services Inventory

### 1. Image-Processing Service (OCR)
**URL:** https://image-processing-givq.onrender.com
**Repo:** shortalex12333/Image-processing (main branch)
**Current Upload Types:** receiving, shipping_label, discrepancy, part_photo, finance

**Current API:**
```python
POST /api/v1/images/upload
Content-Type: multipart/form-data

Fields:
  - file: UploadFile
  - upload_type: Literal["receiving", "shipping_label", "discrepancy", "part_photo", "finance"]
  - receiving_id: Optional[str]
  - comment: Optional[str]
  - doc_type: Optional[str]

Returns:
  {
    "document_id": "uuid",
    "storage_path": "yacht_id/receiving/receiving_id/filename.jpg",
    "extracted_text": "OCR results...",
    "status": "completed"
  }
```

**NEEDS EXTENSION:**
```python
# Add these upload_type values:
"work_order"   → Write to pms_attachments (entity_type='work_order')
"fault"        → Write to pms_attachments (entity_type='fault')
"equipment"    → Write to pms_attachments (entity_type='equipment')

# Add these parameters:
entity_type: Literal["work_order", "fault", "equipment"]
entity_id: str  # UUID of work order/fault/equipment
category: str   # photo, document, pdf, manual, etc.
```

### 2. Digest-Local Service (Document Ingestion)
**URL:** digest-local.int.celeste7.ai
**Location:** Cloud_PMS / main branch / /extraction_Service
**Purpose:** Entity extraction and GraphRAG population

**ASSUMED API (needs verification):**
```python
POST /api/v1/digest/ingest
Content-Type: application/json

Body:
  {
    "document_id": "uuid",           # Reference to pms_attachments.id
    "entity_type": "work_order",     # Context for extraction
    "entity_id": "wo_uuid",          # Parent entity
    "text": "extracted text...",     # From OCR or direct
    "yacht_id": "uuid"               # Tenant isolation
  }

Returns:
  {
    "entities_extracted": {
      "parts": ["pump_123", "seal_456"],
      "suppliers": ["Vendor A"],
      "procedures": ["bleeding_hydraulics"]
    },
    "graph_nodes_created": 5,
    "embeddings_generated": true
  }
```

**QUESTION FOR USER:** What is the actual digest-local API contract?

### 3. Cloud_PMS Proxy Endpoints (NEW - NEEDS CREATION)

#### Pattern Reference: `apps/api/routes/receiving_upload.py`
Existing proxy pattern for receiving uploads. Use same pattern for work orders/faults.

## Endpoints to Create

### Option A: Entity-Specific Endpoints (RECOMMENDED)

**Pros:**
- Clear intent (work order upload vs fault upload)
- Entity-specific validation
- Easier to audit and monitor
- Matches user mental model

**Cons:**
- More endpoints to maintain
- Slight code duplication

```python
# apps/api/routes/work_order_upload.py
POST /api/work_orders/{work_order_id}/upload
POST /api/work_orders/{work_order_id}/attachments/{attachment_id}/comment

# apps/api/routes/fault_upload.py
POST /api/faults/{fault_id}/upload
POST /api/faults/{fault_id}/attachments/{attachment_id}/comment

# apps/api/routes/equipment_upload.py
POST /api/equipment/{equipment_id}/upload
POST /api/equipment/{equipment_id}/attachments/{attachment_id}/comment
```

### Option B: Generic Attachment Endpoint

**Pros:**
- Single endpoint to maintain
- Generic handler logic

**Cons:**
- Less clear intent
- Complex validation logic
- Harder to audit

```python
# apps/api/routes/attachment_upload.py
POST /api/attachments/upload
Body:
  {
    "entity_type": "work_order",
    "entity_id": "uuid",
    "file": ...,
    "category": "photo",
    "description": "Leak on starboard engine"
  }
```

## Implementation Steps (Assuming Option A)

### Step 1: Create Work Order Upload Endpoint

**File:** `apps/api/routes/work_order_upload.py`

```python
from fastapi import APIRouter, File, Form, UploadFile, Header, HTTPException
import httpx
from middleware.auth import get_authenticated_user
from handlers.work_order_handlers import WorkOrderHandler

router = APIRouter(prefix="/api/work_orders", tags=["work_order_upload"])

IMAGE_PROCESSOR_URL = os.getenv("IMAGE_PROCESSOR_URL", "https://image-processing-givq.onrender.com")
DIGEST_LOCAL_URL = os.getenv("DIGEST_LOCAL_URL", "https://digest-local.int.celeste7.ai")

@router.post("/{work_order_id}/upload")
async def upload_work_order_attachment(
    work_order_id: str,
    file: UploadFile = File(...),
    category: str = Form("photo"),  # photo, document, pdf, manual, etc.
    description: Optional[str] = Form(None),
    authorization: str = Header(...),
):
    """
    Upload attachment to work order.

    Flow:
    1. Validate JWT and extract user context
    2. Validate work order exists and user has access
    3. Upload file to Supabase Storage (pms-work-order-attachments bucket)
    4. Create pms_attachments record
    5. If image/PDF: Send to image-processing for OCR
    6. If needs ingestion: Send to digest-local for entity extraction
    7. Return attachment record with signed URL
    """
    # Extract JWT
    jwt_token = authorization.split(" ", 1)[1]

    # Get user context (yacht_id, user_id from JWT)
    user_context = await get_authenticated_user(jwt_token)
    yacht_id = user_context["yacht_id"]
    user_id = user_context["user_id"]

    # Validate work order exists
    handler = WorkOrderHandler(...)
    wo_result = handler.db.table("pms_work_orders").select("id, yacht_id").eq(
        "id", work_order_id
    ).eq("yacht_id", yacht_id).limit(1).execute()

    if not wo_result.data:
        raise HTTPException(404, "Work order not found")

    # Generate storage path
    filename = file.filename
    storage_path = f"{yacht_id}/{work_order_id}/{filename}"
    bucket_name = "pms-work-order-attachments"

    # Upload to Supabase Storage
    file_content = await file.read()
    storage_client = handler.db.storage.from_(bucket_name)
    upload_result = storage_client.upload(
        path=storage_path,
        file=file_content,
        file_options={"content-type": file.content_type}
    )

    # Create pms_attachments record
    attachment_data = {
        "yacht_id": yacht_id,
        "entity_type": "work_order",
        "entity_id": work_order_id,
        "filename": filename,
        "original_filename": filename,
        "mime_type": file.content_type,
        "storage_path": storage_path,
        "category": category,
        "description": description,
        "uploaded_by": user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {"bucket": bucket_name}
    }

    attach_result = handler.db.table("pms_attachments").insert(attachment_data).execute()
    attachment_id = attach_result.data[0]["id"]

    # If image or PDF, send to image-processing for OCR
    extracted_text = None
    if file.content_type in ("image/jpeg", "image/png", "application/pdf"):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                ocr_response = await client.post(
                    f"{IMAGE_PROCESSOR_URL}/api/v1/images/upload",
                    files={"file": (filename, file_content, file.content_type)},
                    data={
                        "upload_type": "work_order",
                        "entity_type": "work_order",
                        "entity_id": work_order_id,
                        "category": category,
                    },
                    headers={"Authorization": authorization}
                )

                if ocr_response.status_code == 200:
                    ocr_data = ocr_response.json()
                    extracted_text = ocr_data.get("extracted_text")
        except Exception as e:
            logger.warning(f"OCR processing failed: {e}")
            # Non-blocking - continue without OCR

    # If needs ingestion (PDFs, documents), send to digest-local
    if category in ("document", "pdf", "manual") and extracted_text:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{DIGEST_LOCAL_URL}/api/v1/digest/ingest",
                    json={
                        "document_id": attachment_id,
                        "entity_type": "work_order",
                        "entity_id": work_order_id,
                        "text": extracted_text,
                        "yacht_id": yacht_id,
                    },
                    headers={"Authorization": authorization}
                )
        except Exception as e:
            logger.warning(f"Digest ingestion failed: {e}")
            # Non-blocking

    # Generate signed URL for immediate display
    signed_url = handler.url_generator.create_signed_url(
        bucket_name, storage_path, expires_in=3600
    )

    return {
        "status": "success",
        "attachment_id": attachment_id,
        "filename": filename,
        "storage_path": storage_path,
        "signed_url": signed_url,
        "extracted_text": extracted_text,
    }


@router.post("/{work_order_id}/attachments/{attachment_id}/comment")
async def add_attachment_comment(
    work_order_id: str,
    attachment_id: str,
    comment: str = Form(...),
    authorization: str = Header(...),
):
    """
    Add comment to attachment.

    Uses pms_attachment_comments table with department-based RLS.
    """
    jwt_token = authorization.split(" ", 1)[1]
    user_context = await get_authenticated_user(jwt_token)

    # Create comment record
    comment_data = {
        "yacht_id": user_context["yacht_id"],
        "attachment_id": attachment_id,
        "comment": comment,
        "created_by": user_context["user_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    handler = WorkOrderHandler(...)
    result = handler.db.table("pms_attachment_comments").insert(comment_data).execute()

    return {
        "status": "success",
        "comment_id": result.data[0]["id"]
    }
```

### Step 2: Clone for Fault and Equipment

Create identical endpoints for:
- `apps/api/routes/fault_upload.py`
- `apps/api/routes/equipment_upload.py`

Change:
- Route prefix
- Entity type
- Bucket name
- Validation handler

### Step 3: Extend Image-Processing Service

**PR to shortalex12333/Image-processing:**

```python
# src/routes/upload_routes.py

# ADD these upload_type values to Literal:
upload_type: Annotated[
    Literal[
        "receiving", "shipping_label", "discrepancy", "part_photo", "finance",
        "work_order", "fault", "equipment"  # ← NEW
    ],
    Form(description="Type of upload")
],

# ADD these new parameters:
entity_type: Annotated[
    Optional[Literal["work_order", "fault", "equipment"]],
    Form(description="Entity type for PMS attachments")
] = None,

entity_id: Annotated[
    Optional[str],
    Form(description="UUID of parent entity")
] = None,

category: Annotated[
    Optional[str],
    Form(description="Attachment category (photo, document, pdf, etc.)")
] = None,

# MODIFY storage path logic:
if upload_type in ("work_order", "fault", "equipment"):
    # Use entity-based buckets
    bucket_name = f"pms-{entity_type}-attachments"
    storage_path = f"{yacht_id}/{entity_id}/{filename}"

    # Write to pms_attachments (NOT pms_image_uploads)
    supabase.table("pms_attachments").insert({
        "yacht_id": yacht_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "storage_path": storage_path,
        "category": category,
        # ... (rest of fields)
    }).execute()
```

### Step 4: Register Routes in Cloud_PMS

```python
# apps/api/pipeline_service.py or main.py

from routes import work_order_upload, fault_upload, equipment_upload

app.include_router(work_order_upload.router)
app.include_router(fault_upload.router)
app.include_router(equipment_upload.router)
```

### Step 5: Frontend Integration

```typescript
// apps/web/src/components/cards/WorkOrderCard.tsx

async function handleFileUpload(file: File, description: string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', 'photo');
  formData.append('description', description);

  const response = await fetch(
    `/api/work_orders/${workOrder.id}/upload`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
      },
      body: formData,
    }
  );

  const result = await response.json();

  // Display attachment with signed URL
  setAttachments([...attachments, {
    id: result.attachment_id,
    filename: result.filename,
    url: result.signed_url,
  }]);
}
```

## Questions for User

1. **Digest-Local API Contract:**
   - What is the actual endpoint URL?
   - What fields does it expect?
   - Is it async (webhook callback) or synchronous?

2. **Upload Strategy:**
   - Should Cloud_PMS proxy to image-processing, OR
   - Should Cloud_PMS upload directly to Supabase Storage and call services separately?

3. **Ingestion Triggers:**
   - Should pms_attachments have a database trigger to auto-queue for ingestion?
   - Or should it be explicit from upload endpoint?

4. **Comment Threading:**
   - Single caption per attachment (simple), OR
   - Full comment thread with replies (complex)?

## Next Actions

1. ✅ Merge PR #26 (attachment table fixes + new infrastructure)
2. ⏳ Clarify digest-local API contract
3. ⏳ Choose upload endpoint strategy (Option A vs B)
4. ⏳ Create work_order_upload.py endpoint
5. ⏳ Submit PR to Image-processing service for entity type support
6. ⏳ Apply migrations 109 & 110 to production
7. ⏳ Frontend upload UI integration
