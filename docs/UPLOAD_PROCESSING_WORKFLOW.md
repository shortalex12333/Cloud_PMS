# Upload Processing Workflow & Queue Strategy

**Created:** 2026-01-30
**Purpose:** Define processing architecture for work order/fault attachment uploads with queue fairness

## Current Architecture Analysis

### Image-Processing Service
**Status:** ✅ NO QUEUE - Immediate Processing

```python
# Current pattern (receiving uploads):
POST /api/v1/images/upload
→ Validates file
→ OCR processing (immediate)
→ Uploads to Supabase Storage
→ Writes to pms_image_uploads
→ Returns result

Processing: Synchronous within async endpoint
No Celery/RQ: Uses FastAPI native async
```

**Impact:** User uploads process immediately. No queue starvation concern.

### Cloud_PMS Extraction Worker
**Status:** ⚠️ HAS QUEUE - Database Polling

```python
# Pattern (email_rag worker):
email_extraction_jobs table
├─ status: 'pending' | 'processing' | 'completed' | 'failed'
├─ priority: (if column exists?)
└─ created_at

Worker polls every 60s:
- SELECT * FROM email_extraction_jobs WHERE status='pending' LIMIT 10
- Process batch
- Update status
```

**Impact:** If we add document ingestion jobs here, need priority system.

## User's Concern

> "If we mark uploads as high priority, will we abruptly stop and cannot proceed with remaining queue?"

### Answer: NO - With Proper Design

**Why:**
1. **Image-processing has no queue** → Uploads process immediately
2. **Extraction worker uses FIFO** → We'll add WEIGHTED FAIR QUEUING
3. **Parallel processing** → Both services can run simultaneously

## Recommended Upload Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER UPLOADS FILE                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌────────────────────────────────────────────┐
        │  Cloud_PMS Upload Endpoint                 │
        │  /api/work_orders/{id}/upload              │
        └────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
        ┌─────────────────────┐     ┌─────────────────────┐
        │  WRITE METADATA     │     │  UPLOAD FILE        │
        │  pms_attachments    │     │  Supabase Storage   │
        │  (immediate)        │     │  (immediate)        │
        └─────────────────────┘     └─────────────────────┘
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                    ┌─────────────────────────────┐
                    │  IMAGE/PDF?                 │
                    └─────────────────────────────┘
                            │             │
                    YES ────┘             └──── NO (done)
                     │
                     ▼
        ┌──────────────────────────────────────────┐
        │  Proxy to Image-Processing               │
        │  https://image-processing-givq...        │
        │  → OCR extraction                        │
        │  → Returns text immediately              │
        │  (NO QUEUE - immediate processing)       │
        └──────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────┐
        │  NEEDS INGESTION? (PDF/Doc)              │
        └──────────────────────────────────────────┘
                     │
                YES ─┘
                     ▼
        ┌──────────────────────────────────────────┐
        │  Queue Job for Extraction Worker         │
        │  INSERT INTO extraction_jobs             │
        │  - priority: 'user_upload' (higher)      │
        │  - type: 'attachment_ingestion'          │
        │  - status: 'pending'                     │
        └──────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────┐
        │  Return to User IMMEDIATELY              │
        │  - attachment_id                         │
        │  - signed_url                            │
        │  - extracted_text                        │
        │  - processing_status: "queued"           │
        └──────────────────────────────────────────┘
```

## Queue Fairness Strategy

### Problem
Existing queue: Email embeddings processing (background batch jobs)
New queue items: User attachment ingestion (on-demand, user-facing)

**Conflict:** High-priority uploads could starve background jobs.

### Solution: Weighted Fair Queuing

Create `extraction_jobs` table with priority tiers:

```sql
CREATE TABLE extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    job_type VARCHAR(50) NOT NULL,  -- 'email_embedding', 'attachment_ingestion', 'document_ocr'
    priority VARCHAR(20) NOT NULL,  -- 'user_upload', 'background', 'low'
    entity_type VARCHAR(50),        -- 'work_order', 'fault', 'email'
    entity_id UUID,
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    attempts INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT
);

CREATE INDEX idx_extraction_jobs_queue ON extraction_jobs(status, priority, created_at)
    WHERE status = 'pending';
```

### Worker Poll Strategy: Round-Robin with Priority Weights

```python
class ExtractionWorker:
    """
    Polls extraction_jobs with weighted fair queuing.

    Weights:
    - user_upload: 60% of batch (6 out of 10 slots)
    - background: 30% of batch (3 out of 10 slots)
    - low: 10% of batch (1 out of 10 slots)

    This ensures:
    - User uploads are prioritized (fast feedback)
    - Background jobs continue processing (not starved)
    - Low-priority jobs eventually process
    """

    async def poll_jobs(self, batch_size: int = 10):
        """Fetch next batch with weighted fair queuing."""

        # Allocate batch slots by priority
        user_upload_slots = 6
        background_slots = 3
        low_slots = 1

        jobs = []

        # Fetch user_upload jobs (up to 6)
        user_jobs = await self.fetch_jobs_by_priority('user_upload', user_upload_slots)
        jobs.extend(user_jobs)

        # Fetch background jobs (up to 3)
        background_jobs = await self.fetch_jobs_by_priority('background', background_slots)
        jobs.extend(background_jobs)

        # Fetch low-priority jobs (up to 1)
        low_jobs = await self.fetch_jobs_by_priority('low', low_slots)
        jobs.extend(low_jobs)

        # If any tier under-utilized, backfill from higher priority
        remaining_slots = batch_size - len(jobs)
        if remaining_slots > 0:
            backfill_jobs = await self.fetch_jobs_by_priority(
                priority=None,  # Any priority
                limit=remaining_slots
            )
            jobs.extend(backfill_jobs)

        return jobs

    async def fetch_jobs_by_priority(self, priority: str, limit: int):
        """Fetch jobs for specific priority tier."""
        result = self.db.table("extraction_jobs").select("*").eq(
            "status", "pending"
        ).eq("priority", priority).order("created_at", desc=False).limit(limit).execute()

        return result.data
```

### Fairness Guarantees

| Priority      | Batch Slots | Wait Time (typical) | Use Case                  |
|---------------|-------------|---------------------|---------------------------|
| user_upload   | 6/10 (60%)  | <60s (next poll)    | Attachments, on-demand    |
| background    | 3/10 (30%)  | <120s               | Email embeddings, batch   |
| low           | 1/10 (10%)  | <600s               | Cleanup, maintenance      |

**Key Properties:**
- ✅ User uploads prioritized (60% of capacity)
- ✅ Background jobs NOT starved (30% guaranteed)
- ✅ No single priority monopolizes queue
- ✅ Backfill mechanism prevents wasted capacity

## Implementation Steps

### Step 1: Create extraction_jobs Table

```sql
-- Migration: 20260130_111_create_extraction_jobs_table.sql

CREATE TABLE IF NOT EXISTS public.extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    attempts INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    completed_by VARCHAR(100),  -- Worker instance ID
    error TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT chk_status CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    CONSTRAINT chk_priority CHECK (priority IN ('user_upload', 'background', 'low'))
);

CREATE INDEX idx_extraction_jobs_queue ON public.extraction_jobs(status, priority, created_at)
    WHERE status = 'pending';

CREATE INDEX idx_extraction_jobs_entity ON public.extraction_jobs(entity_type, entity_id);

-- RLS: Users can view their own yacht's jobs
ALTER TABLE public.extraction_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "extraction_jobs_select"
ON public.extraction_jobs FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = extraction_jobs.yacht_id
    )
);
```

### Step 2: Update Upload Endpoint to Queue Ingestion

```python
# apps/api/routes/work_order_upload.py

@router.post("/{work_order_id}/upload")
async def upload_work_order_attachment(...):
    # ... (upload file, create pms_attachments record)

    # If PDF/document, queue for extraction
    if file.content_type == "application/pdf" or category in ("document", "manual"):
        # Queue ingestion job (don't block user)
        job_data = {
            "yacht_id": yacht_id,
            "job_type": "attachment_ingestion",
            "priority": "user_upload",  # High priority for user uploads
            "entity_type": "work_order",
            "entity_id": work_order_id,
            "payload": {
                "attachment_id": attachment_id,
                "storage_path": storage_path,
                "extracted_text": extracted_text,  # From OCR
                "mime_type": file.content_type,
            },
            "status": "pending",
        }

        await db.table("extraction_jobs").insert(job_data).execute()

    # Return immediately (don't wait for extraction)
    return {
        "status": "success",
        "attachment_id": attachment_id,
        "processing_status": "queued" if needs_extraction else "completed",
    }
```

### Step 3: Create Extraction Worker

```python
# apps/api/workers/extraction_worker.py

class ExtractionWorker:
    """
    Processes extraction_jobs with weighted fair queuing.

    Handles:
    - attachment_ingestion: Extract entities from work order/fault attachments
    - email_embedding: Generate embeddings for emails (existing)
    - document_ocr: OCR for scanned documents
    """

    async def process_attachment_ingestion(self, job: Dict):
        """Process attachment for entity extraction and GraphRAG."""
        payload = job["payload"]
        attachment_id = payload["attachment_id"]
        extracted_text = payload["extracted_text"]

        # Use existing extraction pipeline
        from extraction.orchestrator import ExtractionOrchestrator

        orchestrator = ExtractionOrchestrator()
        entities = orchestrator.extract(extracted_text)

        # Update pms_attachments with extracted entities
        await self.db.table("pms_attachments").update({
            "related_text": extracted_text,
            "metadata": {
                **payload.get("metadata", {}),
                "entities_extracted": entities,
                "extraction_completed_at": datetime.now(timezone.utc).isoformat(),
            }
        }).eq("id", attachment_id).execute()

        # TODO: Populate GraphRAG with entities
```

### Step 4: Deploy Worker as Separate Service

**Render Configuration:**
```yaml
# render.yaml (add new service)
services:
  - type: background_worker
    name: extraction-worker
    env: python
    repo: https://github.com/shortalex12333/Cloud_PMS
    branch: main
    rootDir: apps/api
    buildCommand: pip install -r requirements.txt
    startCommand: python workers/extraction_worker.py
    envVars:
      - key: WORKER_TYPE
        value: extraction
      - key: POLL_INTERVAL
        value: 30  # Poll every 30s for faster user feedback
      - key: BATCH_SIZE
        value: 10
```

## Parallel Processing Capability

**Question:** "Can this workflow handle parallel tasks and do together?"

**Answer:** YES - Multiple parallelism layers:

```
┌───────────────────────────────────────────────────────────┐
│  Layer 1: Multi-Service Parallelism                       │
│  ├─ Image-processing service (OCR)                        │
│  ├─ Extraction worker (entity extraction)                 │
│  └─ Cloud_PMS API (file upload)                           │
│  ✅ All run simultaneously on different Render services   │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│  Layer 2: Async Concurrency (within each service)         │
│  ├─ FastAPI handles 100+ concurrent requests              │
│  ├─ Worker processes 10 jobs per batch                    │
│  └─ Async I/O (OCR, DB, storage) don't block              │
│  ✅ Single service handles many users simultaneously      │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│  Layer 3: Batch Fairness (within worker queue)            │
│  ├─ 6 user uploads                                        │
│  ├─ 3 background jobs                                     │
│  └─ 1 low priority                                        │
│  ✅ All priorities make progress each poll cycle          │
└───────────────────────────────────────────────────────────┘
```

## Example Timeline

**Scenario:** User uploads 3 PDFs to work order while background worker is processing 100 pending email embeddings.

```
T=0s:    User uploads PDF 1, 2, 3
         → Cloud_PMS creates pms_attachments records (immediate)
         → Proxy to image-processing for OCR (immediate, parallel)
         → Queue 3 ingestion jobs (priority: user_upload)

T=2s:    Image-processing returns OCR text for all 3 PDFs
         → User sees files immediately with text preview

T=30s:   Worker polls extraction_jobs
         → Fetches: 6 user_upload (including user's 3 PDFs) + 3 background + 1 low
         → Processes batch in parallel (async)

T=35s:   User's 3 PDFs extracted
         → Entities identified: [pump_A, hydraulic_seal, bleeding_procedure]
         → pms_attachments.metadata updated
         → User can search by entities

T=60s:   Next poll cycle
         → Remaining background jobs continue (30% of capacity)
         → No starvation
```

**Key Property:** User gets IMMEDIATE feedback (file visible), with async enhancement (entity extraction) completing within 30-60s without blocking background work.

## Summary

### User Concern Resolution

> "My fear is if we mark uploads as high priority, we abruptly stop and cannot proceed with remaining queue?"

**Resolution:**
- ✅ Image-processing has NO queue (immediate processing)
- ✅ Extraction worker uses weighted fair queuing (60/30/10 split)
- ✅ Background jobs guaranteed 30% of capacity (not starved)
- ✅ User uploads get 60% (fast feedback within 30-60s)
- ✅ Parallel processing at multiple layers

### Workflow Decision

**Recommendation:** Follow receiving upload pattern

```python
User Upload
  → Cloud_PMS endpoint (validates, creates record)
  → Proxy to image-processing (OCR)
  → Queue extraction job (if needed)
  → Return immediately to user

# User sees file right away
# Processing continues in background
# No blocking
# No starvation
```

**Next Steps:**
1. ✅ Merge PR #26 (attachment infrastructure)
2. Create extraction_jobs table (migration 111)
3. Create work_order_upload.py endpoint
4. Deploy extraction worker as background service
5. Frontend upload UI
