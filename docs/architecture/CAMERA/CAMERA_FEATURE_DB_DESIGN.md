# Camera Feature - Database Architecture Design
## Image Capture for Inventory & Receiving

**Date:** 2026-01-09
**Status:** Foundation Design - Backend Only
**Scope:** Database schema, storage, policies, audit - NO workflow/frontend

---

## Executive Summary

This design provides the complete database foundation to support:

1. **Image Upload & Storage** - Packing slips, shipping labels, invoices, discrepancy photos, part photos
2. **Staged Processing Pipeline** - Intake → Classification → Extraction → Reconciliation → Verification → Commit
3. **Audit Trail** - Immutable record of who uploaded what, when, with source preservation
4. **Linkages** - Images attached to orders, receiving events, line items, parts, work orders, shopping list
5. **Label Generation** - PDF generation tracking and storage
6. **Abuse Resistance** - Rate limiting, duplicate detection, validation gates

---

## Core Principles

1. **Checkbox = Truth** - No auto-commit, explicit human verification required
2. **Immutable Audit** - All images, extractions, and verifications permanently stored
3. **Source Preservation** - Original images never deleted, always linked
4. **Stage-Gated** - Processing pipeline with clear stage transitions
5. **Precision > Speed** - Verification steps prevent garbage data
6. **Multi-Tenant** - All tables include `yacht_id` for isolation

---

## Supabase Storage Buckets

### 1. `receiving-images` Bucket

**Purpose:** Store raw uploaded images from receiving workflow

**Structure:**
```
/{yacht_id}/receiving/{year}/{month}/{session_id}/{image_id}.{ext}

Example:
/85fe1119-b04c-41ac-80f1-829d23322598/receiving/2026/01/sess-123/img-456.jpg
```

**Access Policies:**
- Authenticated users can upload to their yacht
- Service role can read/write all
- Users can read their yacht's images
- Images never deleted (soft delete via metadata)

**File Types:** jpg, jpeg, png, pdf, heic
**Size Limit:** 15MB per file
**MIME Types:** image/jpeg, image/png, application/pdf, image/heic

---

### 2. `discrepancy-photos` Bucket

**Purpose:** Store photos of damaged, missing, or incorrect items

**Structure:**
```
/{yacht_id}/discrepancies/{year}/{month}/{receiving_event_id}/{line_item_id}_{timestamp}.{ext}

Example:
/85fe1119-b04c-41ac-80f1-829d23322598/discrepancies/2026/01/rcv-789/line-101_20260109T143022.jpg
```

**Access Policies:**
- Authenticated users can upload discrepancy photos
- Service role can read/write all
- Users can read their yacht's photos
- Never deleted (evidence for supplier claims)

**File Types:** jpg, jpeg, png, heic
**Size Limit:** 10MB per file

---

### 3. `label-pdfs` Bucket

**Purpose:** Store generated label PDFs for printing

**Structure:**
```
/{yacht_id}/labels/{year}/{month}/{receiving_event_id}/labels_{timestamp}.pdf

Example:
/85fe1119-b04c-41ac-80f1-829d23322598/labels/2026/01/rcv-789/labels_20260109T143530.pdf
```

**Access Policies:**
- Service role generates and writes
- Users can read their yacht's labels
- Auto-expire after 90 days (can be regenerated)

**File Types:** pdf only
**Size Limit:** 5MB per file

---

### 4. `part-photos` Bucket

**Purpose:** Store photos of parts for identification (especially candidate parts)

**Structure:**
```
/{yacht_id}/parts/{part_id}/{photo_id}.{ext}

Example:
/85fe1119-b04c-41ac-80f1-829d23322598/parts/part-123/photo-456.jpg
```

**Access Policies:**
- Authenticated users can upload part photos
- Service role can read/write all
- Users can read their yacht's part photos

**File Types:** jpg, jpeg, png
**Size Limit:** 5MB per file

---

## New Database Tables

### 1. `pms_image_uploads`

**Purpose:** Immutable record of every uploaded image with validation metadata

```sql
CREATE TABLE pms_image_uploads (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yacht_registry(id) ON DELETE CASCADE,

    -- Storage reference
    storage_bucket TEXT NOT NULL, -- 'receiving-images', 'discrepancy-photos', 'part-photos'
    storage_path TEXT NOT NULL,   -- Full path within bucket
    file_name TEXT NOT NULL,      -- Original filename
    mime_type TEXT NOT NULL,      -- image/jpeg, application/pdf, etc.
    file_size_bytes BIGINT NOT NULL,

    -- Content validation
    sha256_hash TEXT UNIQUE NOT NULL, -- Deduplication + integrity
    is_valid BOOLEAN NOT NULL DEFAULT false,
    validation_stage TEXT NOT NULL DEFAULT 'uploaded', -- 'uploaded', 'validated', 'classified', 'extracted', 'processed', 'failed'
    validation_errors JSONB,      -- Array of error messages if validation failed

    -- Classification (Stage 2)
    document_type TEXT,            -- 'packing_slip', 'shipping_label', 'invoice', 'part_photo', 'discrepancy_photo', 'unknown'
    classification_confidence NUMERIC(5,4), -- 0.0000 to 1.0000 (informational only, not used for decisions)
    classification_metadata JSONB, -- Additional classification details

    -- OCR & Extraction (Stage 3)
    ocr_raw_text TEXT,            -- Full OCR output
    ocr_completed_at TIMESTAMPTZ,
    extraction_status TEXT,        -- 'pending', 'processing', 'completed', 'failed'
    extracted_data JSONB,          -- Structured extraction results
    extracted_at TIMESTAMPTZ,

    -- Anti-abuse
    upload_ip_address INET,        -- Rate limiting per IP
    is_duplicate BOOLEAN NOT NULL DEFAULT false,
    duplicate_of_image_id UUID REFERENCES pms_image_uploads(id),

    -- Audit
    uploaded_by UUID NOT NULL REFERENCES auth.users(id),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_by UUID REFERENCES auth.users(id), -- If manually processed
    processed_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB,               -- Flexible storage for future needs

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES auth.users(id),
    deletion_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_image_uploads_yacht ON pms_image_uploads(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_image_uploads_hash ON pms_image_uploads(sha256_hash);
CREATE INDEX idx_image_uploads_validation_stage ON pms_image_uploads(validation_stage) WHERE deleted_at IS NULL;
CREATE INDEX idx_image_uploads_document_type ON pms_image_uploads(document_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_image_uploads_uploaded_at ON pms_image_uploads(yacht_id, uploaded_at DESC);
CREATE INDEX idx_image_uploads_uploaded_by ON pms_image_uploads(uploaded_by, uploaded_at DESC);

-- Unique constraint on storage path
CREATE UNIQUE INDEX idx_image_uploads_storage_path ON pms_image_uploads(storage_bucket, storage_path) WHERE deleted_at IS NULL;

-- Comments
COMMENT ON TABLE pms_image_uploads IS 'Immutable record of all uploaded images for receiving, inventory, and parts. Includes validation, classification, and OCR metadata.';
COMMENT ON COLUMN pms_image_uploads.sha256_hash IS 'SHA256 hash for deduplication and integrity verification. Computed on upload.';
COMMENT ON COLUMN pms_image_uploads.validation_stage IS 'Current processing stage: uploaded → validated → classified → extracted → processed → failed';
COMMENT ON COLUMN pms_image_uploads.document_type IS 'Classified document type from Stage 2: packing_slip, shipping_label, invoice, part_photo, discrepancy_photo, unknown';
```

**Key Features:**
- Immutable (no UPDATEs to core fields after creation)
- Duplicate detection via SHA256 hash
- Full processing pipeline tracking
- OCR results stored for traceability
- Soft delete preserves audit trail

---

### 2. `pms_receiving_sessions`

**Purpose:** Represents a complete receiving workflow session from image upload to final commit

```sql
CREATE TABLE pms_receiving_sessions (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yacht_registry(id) ON DELETE CASCADE,
    session_number TEXT UNIQUE NOT NULL, -- Human-readable: RSESS-2026-001

    -- Session lifecycle
    status TEXT NOT NULL DEFAULT 'draft', -- 'draft', 'reconciling', 'verifying', 'committed', 'cancelled'
    CHECK (status IN ('draft', 'reconciling', 'verifying', 'committed', 'cancelled')),

    -- Linked order (optional - can receive without order)
    order_id UUID REFERENCES pms_orders(id) ON DELETE SET NULL,
    order_matched_automatically BOOLEAN DEFAULT false,
    order_match_confidence NUMERIC(5,4), -- Informational only

    -- Session metadata
    session_type TEXT NOT NULL, -- 'packing_slip', 'shipping_label', 'barcode_scan', 'manual'
    supplier_name TEXT,         -- Extracted or manual
    tracking_number TEXT,       -- If from shipping label
    expected_items_count INT,   -- From OCR or user input

    -- Processing stages
    extraction_completed_at TIMESTAMPTZ,
    reconciliation_completed_at TIMESTAMPTZ,
    verification_completed_at TIMESTAMPTZ,
    committed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    -- Results (after commit)
    received_to_inventory_count INT DEFAULT 0,
    installed_immediately_count INT DEFAULT 0,
    discrepancy_count INT DEFAULT 0,
    unresolved_lines_count INT DEFAULT 0,

    -- Linked receiving event (created on commit)
    receiving_event_id UUID REFERENCES pms_receiving_events(id) ON DELETE SET NULL,

    -- Audit
    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    committed_by UUID REFERENCES auth.users(id),
    cancelled_by UUID REFERENCES auth.users(id),
    cancellation_reason TEXT,

    -- Metadata
    metadata JSONB, -- Session notes, special instructions, etc.

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_receiving_sessions_yacht ON pms_receiving_sessions(yacht_id, created_at DESC);
CREATE INDEX idx_receiving_sessions_status ON pms_receiving_sessions(status) WHERE status != 'committed' AND status != 'cancelled';
CREATE INDEX idx_receiving_sessions_order ON pms_receiving_sessions(order_id) WHERE order_id IS NOT NULL;
CREATE INDEX idx_receiving_sessions_created_by ON pms_receiving_sessions(created_by, created_at DESC);

-- Auto-generate session number
CREATE OR REPLACE FUNCTION generate_receiving_session_number()
RETURNS TRIGGER AS $$
DECLARE
    v_year TEXT;
    v_count INT;
    v_number TEXT;
BEGIN
    -- Format: RSESS-YYYY-NNN
    v_year := TO_CHAR(NOW(), 'YYYY');

    -- Get count of sessions this year
    SELECT COUNT(*) + 1 INTO v_count
    FROM pms_receiving_sessions
    WHERE yacht_id = NEW.yacht_id
    AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW());

    v_number := 'RSESS-' || v_year || '-' || LPAD(v_count::TEXT, 3, '0');

    NEW.session_number := v_number;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_generate_receiving_session_number
BEFORE INSERT ON pms_receiving_sessions
FOR EACH ROW
WHEN (NEW.session_number IS NULL)
EXECUTE FUNCTION generate_receiving_session_number();

COMMENT ON TABLE pms_receiving_sessions IS 'Complete receiving workflow session from image upload to final commit. Tracks multi-stage pipeline.';
COMMENT ON COLUMN pms_receiving_sessions.status IS 'Session lifecycle: draft → reconciling → verifying → committed | cancelled';
```

**Key Features:**
- Session = entire receiving workflow
- Can link to order (optional)
- Tracks all processing stages
- Creates receiving_event on commit
- Auto-generates session number

---

### 3. `pms_receiving_session_images`

**Purpose:** Junction table linking receiving sessions to uploaded images

```sql
CREATE TABLE pms_receiving_session_images (
    -- Junction
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yacht_registry(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES pms_receiving_sessions(id) ON DELETE CASCADE,
    image_id UUID NOT NULL REFERENCES pms_image_uploads(id) ON DELETE CASCADE,

    -- Image role in session
    image_type TEXT NOT NULL, -- 'primary', 'supplementary', 'discrepancy', 'reference'
    image_sequence INT,       -- Order of images in multi-image sessions

    -- Usage tracking
    is_used_for_extraction BOOLEAN DEFAULT false,
    extraction_source_priority INT, -- If multiple images, which takes precedence

    -- Audit
    added_by UUID NOT NULL REFERENCES auth.users(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Metadata
    notes TEXT,
    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_session_images_session ON pms_receiving_session_images(session_id, image_sequence);
CREATE INDEX idx_session_images_image ON pms_receiving_session_images(image_id);
CREATE UNIQUE INDEX idx_session_images_unique ON pms_receiving_session_images(session_id, image_id);

COMMENT ON TABLE pms_receiving_session_images IS 'Links receiving sessions to uploaded images. One session can have multiple images (multi-page packing slips).';
```

**Key Features:**
- M:M relationship (session ↔ images)
- Supports multiple images per session
- Tracks which image used for extraction
- Image sequencing for multi-page docs

---

### 4. `pms_receiving_draft_lines`

**Purpose:** Pre-verification extracted line items from images (Stage 3-5 outputs)

```sql
CREATE TABLE pms_receiving_draft_lines (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yacht_registry(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES pms_receiving_sessions(id) ON DELETE CASCADE,

    -- Extraction metadata
    source_image_id UUID NOT NULL REFERENCES pms_image_uploads(id) ON DELETE CASCADE,
    line_sequence INT NOT NULL, -- Order as extracted from image
    raw_text TEXT NOT NULL,     -- Original extracted text

    -- Extracted fields (Stage 3)
    extracted_part_name TEXT,
    extracted_part_number TEXT,
    extracted_quantity NUMERIC,
    extracted_unit TEXT,
    extracted_description TEXT,
    extracted_manufacturer TEXT,
    extraction_confidence NUMERIC(5,4), -- Informational only, not used for decisions

    -- Reconciliation (Stage 5 - matching)
    match_status TEXT NOT NULL DEFAULT 'unmatched', -- 'matched_order', 'matched_part', 'matched_shopping_list', 'unmatched', 'ignored'
    CHECK (match_status IN ('matched_order', 'matched_part', 'matched_shopping_list', 'unmatched', 'ignored')),

    -- Match candidates (suggestions, not auto-applied)
    suggested_order_line_id UUID, -- If matched to order
    suggested_part_id UUID REFERENCES pms_parts(id),
    suggested_shopping_list_item_id UUID REFERENCES pms_shopping_list_items(id),
    match_confidence NUMERIC(5,4), -- How confident the match is (informational)
    alternative_matches JSONB,     -- Array of other potential matches

    -- Human verification (Stage 6)
    is_verified BOOLEAN NOT NULL DEFAULT false,
    verified_by UUID REFERENCES auth.users(id),
    verified_at TIMESTAMPTZ,

    -- Final resolved values (after human verification)
    resolved_part_id UUID REFERENCES pms_parts(id),
    resolved_shopping_list_item_id UUID REFERENCES pms_shopping_list_items(id),
    resolved_quantity NUMERIC,
    resolved_unit TEXT,
    resolved_disposition TEXT, -- 'receive_inventory', 'install_immediately', 'missing', 'damaged', 'incorrect', 'ignore'
    resolution_notes TEXT,

    -- Discrepancy handling
    is_discrepancy BOOLEAN DEFAULT false,
    discrepancy_type TEXT, -- 'missing', 'damaged', 'incorrect', 'quantity_mismatch'
    discrepancy_photo_id UUID REFERENCES pms_image_uploads(id), -- Photo of damage/issue
    discrepancy_notes TEXT,

    -- Candidate part creation
    creates_candidate_part BOOLEAN DEFAULT false,
    created_candidate_part_id UUID REFERENCES pms_parts(id), -- If user chose "create new part"

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_draft_lines_session ON pms_receiving_draft_lines(session_id, line_sequence);
CREATE INDEX idx_draft_lines_image ON pms_receiving_draft_lines(source_image_id);
CREATE INDEX idx_draft_lines_match_status ON pms_receiving_draft_lines(match_status) WHERE is_verified = false;
CREATE INDEX idx_draft_lines_unverified ON pms_receiving_draft_lines(session_id) WHERE is_verified = false;
CREATE INDEX idx_draft_lines_verified ON pms_receiving_draft_lines(verified_by, verified_at DESC) WHERE is_verified = true;

COMMENT ON TABLE pms_receiving_draft_lines IS 'Pre-verification extracted line items from receiving images. Stores OCR results, matching suggestions, and human verification decisions.';
COMMENT ON COLUMN pms_receiving_draft_lines.match_status IS 'Matching outcome: matched_order | matched_part | matched_shopping_list | unmatched | ignored';
COMMENT ON COLUMN pms_receiving_draft_lines.is_verified IS 'Human checkbox verification. Only verified lines are committed to receiving_line_items.';
```

**Key Features:**
- Draft = not yet committed
- Stores raw extraction + suggestions
- Human verification checkbox per line
- Discrepancy handling
- Can trigger candidate part creation

---

### 5. `pms_label_generations`

**Purpose:** Tracks label PDF generation requests and outputs

```sql
CREATE TABLE pms_label_generations (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yacht_registry(id) ON DELETE CASCADE,

    -- Context (what triggered label generation)
    receiving_event_id UUID REFERENCES pms_receiving_events(id) ON DELETE CASCADE,
    receiving_session_id UUID REFERENCES pms_receiving_sessions(id) ON DELETE CASCADE,

    -- Label configuration
    label_type TEXT NOT NULL, -- 'per_line_item', 'per_unit'
    lines_included JSONB NOT NULL, -- Array of receiving_line_item_ids
    total_labels_count INT NOT NULL,

    -- Generation status
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'generating', 'completed', 'failed'
    CHECK (status IN ('pending', 'generating', 'completed', 'failed')),

    -- Output
    pdf_storage_path TEXT, -- Path in label-pdfs bucket
    pdf_file_size_bytes BIGINT,
    generation_completed_at TIMESTAMPTZ,
    generation_errors JSONB,

    -- Distribution
    emailed_to TEXT, -- Email address if user requested email
    emailed_at TIMESTAMPTZ,
    downloaded_count INT DEFAULT 0,
    last_downloaded_at TIMESTAMPTZ,

    -- Audit
    requested_by UUID NOT NULL REFERENCES auth.users(id),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Auto-expire (labels can be regenerated)
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '90 days',

    -- Metadata
    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_label_generations_receiving_event ON pms_label_generations(receiving_event_id);
CREATE INDEX idx_label_generations_status ON pms_label_generations(status) WHERE status IN ('pending', 'generating');
CREATE INDEX idx_label_generations_requested_by ON pms_label_generations(requested_by, requested_at DESC);
CREATE INDEX idx_label_generations_expires ON pms_label_generations(expires_at) WHERE status = 'completed';

COMMENT ON TABLE pms_label_generations IS 'Tracks label PDF generation requests after receiving. Labels are ephemeral (auto-expire after 90 days).';
```

**Key Features:**
- Async label generation
- Tracks email delivery
- Auto-expiry (can regenerate)
- Configuration stored (per-line vs per-unit)

---

## Modified Existing Tables

### Changes to `pms_receiving_events`

Add columns to link to receiving sessions and source images:

```sql
ALTER TABLE pms_receiving_events
ADD COLUMN receiving_session_id UUID REFERENCES pms_receiving_sessions(id) ON DELETE SET NULL,
ADD COLUMN source_image_ids UUID[] DEFAULT '{}', -- Array of image_upload IDs
ADD COLUMN was_camera_initiated BOOLEAN DEFAULT false,
ADD COLUMN camera_session_metadata JSONB;

COMMENT ON COLUMN pms_receiving_events.receiving_session_id IS 'Links to receiving session if created via camera workflow';
COMMENT ON COLUMN pms_receiving_events.source_image_ids IS 'Array of pms_image_uploads.id that were used to create this receiving event';
COMMENT ON COLUMN pms_receiving_events.was_camera_initiated IS 'True if this receiving event was created via camera/image upload workflow';
```

**Indexes:**
```sql
CREATE INDEX idx_receiving_events_session ON pms_receiving_events(receiving_session_id) WHERE receiving_session_id IS NOT NULL;
CREATE INDEX idx_receiving_events_camera_initiated ON pms_receiving_events(yacht_id) WHERE was_camera_initiated = true;
```

---

### Changes to `pms_receiving_line_items`

Add columns to link to draft lines and discrepancy photos:

```sql
ALTER TABLE pms_receiving_line_items
ADD COLUMN draft_line_id UUID REFERENCES pms_receiving_draft_lines(id) ON DELETE SET NULL,
ADD COLUMN discrepancy_photo_ids UUID[] DEFAULT '{}', -- Array of image_upload IDs for damage/missing
ADD COLUMN verification_notes TEXT,
ADD COLUMN human_verified_at TIMESTAMPTZ,
ADD COLUMN human_verified_by UUID REFERENCES auth.users(id);

COMMENT ON COLUMN pms_receiving_line_items.draft_line_id IS 'Links to draft line if created via camera workflow (traceability)';
COMMENT ON COLUMN pms_receiving_line_items.discrepancy_photo_ids IS 'Array of image IDs for photos of damaged/missing/incorrect items';
COMMENT ON COLUMN pms_receiving_line_items.verification_notes IS 'Human verification notes from camera workflow';
```

**Indexes:**
```sql
CREATE INDEX idx_receiving_line_items_draft ON pms_receiving_line_items(draft_line_id) WHERE draft_line_id IS NOT NULL;
```

---

### Changes to `pms_shopping_list_items`

Add column to link to source images (for items added via camera):

```sql
ALTER TABLE pms_shopping_list_items
ADD COLUMN source_image_ids UUID[] DEFAULT '{}', -- Array of image_upload IDs
ADD COLUMN image_notes TEXT;

COMMENT ON COLUMN pms_shopping_list_items.source_image_ids IS 'Array of images used to identify/specify this part (especially for candidate parts)';
```

---

### Changes to `pms_parts`

Add column for part photos (especially candidate parts):

```sql
ALTER TABLE pms_parts
ADD COLUMN photo_ids UUID[] DEFAULT '{}', -- Array of image_upload IDs
ADD COLUMN primary_photo_id UUID REFERENCES pms_image_uploads(id) ON DELETE SET NULL,
ADD COLUMN photos_updated_at TIMESTAMPTZ;

COMMENT ON COLUMN pms_parts.photo_ids IS 'Array of part photo image IDs for identification';
COMMENT ON COLUMN pms_parts.primary_photo_id IS 'Primary photo to display in lists/searches';
```

**Indexes:**
```sql
CREATE INDEX idx_parts_primary_photo ON pms_parts(primary_photo_id) WHERE primary_photo_id IS NOT NULL;
```

---

### Changes to `pms_orders`

Add columns to link to shipping labels and invoice images:

```sql
ALTER TABLE pms_orders
ADD COLUMN shipping_label_image_ids UUID[] DEFAULT '{}',
ADD COLUMN invoice_image_ids UUID[] DEFAULT '{}';

COMMENT ON COLUMN pms_orders.shipping_label_image_ids IS 'Array of uploaded shipping label images';
COMMENT ON COLUMN pms_orders.invoice_image_ids IS 'Array of uploaded invoice images (in addition to invoice_document_id)';
```

---

## Row Level Security (RLS) Policies

### `pms_image_uploads` RLS

```sql
ALTER TABLE pms_image_uploads ENABLE ROW LEVEL SECURITY;

-- Users can view images for their yacht
CREATE POLICY "Users can view their yacht's images"
ON pms_image_uploads FOR SELECT
TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- Users can upload images for their yacht
CREATE POLICY "Users can upload images for their yacht"
ON pms_image_uploads FOR INSERT
TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND uploaded_by = auth.uid()
);

-- Service role can do anything (for processing pipeline)
CREATE POLICY "Service role full access"
ON pms_image_uploads FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Users cannot delete images (soft delete only via service)
-- No DELETE policy = users cannot hard delete
```

---

### `pms_receiving_sessions` RLS

```sql
ALTER TABLE pms_receiving_sessions ENABLE ROW LEVEL SECURITY;

-- Users can view sessions for their yacht
CREATE POLICY "Users can view their yacht's sessions"
ON pms_receiving_sessions FOR SELECT
TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- Users can create sessions for their yacht
CREATE POLICY "Users can create sessions for their yacht"
ON pms_receiving_sessions FOR INSERT
TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND created_by = auth.uid()
);

-- Users can update their own draft sessions
CREATE POLICY "Users can update own draft sessions"
ON pms_receiving_sessions FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND created_by = auth.uid()
    AND status IN ('draft', 'reconciling', 'verifying')
);

-- Service role can commit sessions (triggers receiving_event creation)
CREATE POLICY "Service role can update sessions"
ON pms_receiving_sessions FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);
```

---

### `pms_receiving_session_images` RLS

```sql
ALTER TABLE pms_receiving_session_images ENABLE ROW LEVEL SECURITY;

-- Users can view session images for their yacht
CREATE POLICY "Users can view their yacht's session images"
ON pms_receiving_session_images FOR SELECT
TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- Users can add images to their sessions
CREATE POLICY "Users can add images to their sessions"
ON pms_receiving_session_images FOR INSERT
TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND added_by = auth.uid()
);
```

---

### `pms_receiving_draft_lines` RLS

```sql
ALTER TABLE pms_receiving_draft_lines ENABLE ROW LEVEL SECURITY;

-- Users can view draft lines for their yacht
CREATE POLICY "Users can view their yacht's draft lines"
ON pms_receiving_draft_lines FOR SELECT
TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- Users can update draft lines (verification)
CREATE POLICY "Users can verify draft lines"
ON pms_receiving_draft_lines FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND is_verified = false -- Can only update unverified lines
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND verified_by = auth.uid()
);

-- Service role can create and update (for extraction pipeline)
CREATE POLICY "Service role can manage draft lines"
ON pms_receiving_draft_lines FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

---

### `pms_label_generations` RLS

```sql
ALTER TABLE pms_label_generations ENABLE ROW LEVEL SECURITY;

-- Users can view their label generations
CREATE POLICY "Users can view their label generations"
ON pms_label_generations FOR SELECT
TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- Users can request label generation
CREATE POLICY "Users can request labels"
ON pms_label_generations FOR INSERT
TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND requested_by = auth.uid()
);

-- Service role generates PDFs
CREATE POLICY "Service role can update label generations"
ON pms_label_generations FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);
```

---

## Triggers & Functions

### 1. Auto-Update `updated_at` Timestamps

```sql
-- For pms_image_uploads
CREATE TRIGGER trg_image_uploads_updated_at
BEFORE UPDATE ON pms_image_uploads
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

-- For pms_receiving_sessions
CREATE TRIGGER trg_receiving_sessions_updated_at
BEFORE UPDATE ON pms_receiving_sessions
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

-- For pms_receiving_draft_lines
CREATE TRIGGER trg_draft_lines_updated_at
BEFORE UPDATE ON pms_receiving_draft_lines
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();
```

---

### 2. Enforce Session State Machine

```sql
CREATE OR REPLACE FUNCTION enforce_receiving_session_state_transitions()
RETURNS TRIGGER AS $$
BEGIN
    -- Valid transitions:
    -- draft → reconciling
    -- reconciling → verifying
    -- verifying → committed
    -- any → cancelled

    IF OLD.status = 'committed' AND NEW.status != 'committed' THEN
        RAISE EXCEPTION 'Cannot change status of committed session';
    END IF;

    IF OLD.status = 'cancelled' AND NEW.status != 'cancelled' THEN
        RAISE EXCEPTION 'Cannot change status of cancelled session';
    END IF;

    -- draft can only go to reconciling or cancelled
    IF OLD.status = 'draft' AND NEW.status NOT IN ('draft', 'reconciling', 'cancelled') THEN
        RAISE EXCEPTION 'Invalid transition from draft to %', NEW.status;
    END IF;

    -- reconciling can only go to verifying or cancelled
    IF OLD.status = 'reconciling' AND NEW.status NOT IN ('reconciling', 'verifying', 'cancelled') THEN
        RAISE EXCEPTION 'Invalid transition from reconciling to %', NEW.status;
    END IF;

    -- verifying can only go to committed or cancelled
    IF OLD.status = 'verifying' AND NEW.status NOT IN ('verifying', 'committed', 'cancelled') THEN
        RAISE EXCEPTION 'Invalid transition from verifying to %', NEW.status;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_session_state
BEFORE UPDATE ON pms_receiving_sessions
FOR EACH ROW
WHEN (OLD.status IS DISTINCT FROM NEW.status)
EXECUTE FUNCTION enforce_receiving_session_state_transitions();
```

---

### 3. Create Receiving Event on Session Commit

```sql
CREATE OR REPLACE FUNCTION create_receiving_event_from_session()
RETURNS TRIGGER AS $$
DECLARE
    v_receiving_event_id UUID;
    v_receiving_number TEXT;
    v_draft_line RECORD;
BEGIN
    -- Only trigger when session is committed
    IF NEW.status = 'committed' AND OLD.status != 'committed' THEN

        -- Generate receiving number
        v_receiving_number := 'RCV-' || TO_CHAR(NOW(), 'YYYY') || '-' ||
            LPAD((
                SELECT COUNT(*) + 1
                FROM pms_receiving_events
                WHERE yacht_id = NEW.yacht_id
                AND EXTRACT(YEAR FROM received_at) = EXTRACT(YEAR FROM NOW())
            )::TEXT, 3, '0');

        -- Create receiving_event
        INSERT INTO pms_receiving_events (
            yacht_id,
            receiving_number,
            order_id,
            received_at,
            received_by,
            status,
            receiving_session_id,
            source_image_ids,
            was_camera_initiated,
            is_locked
        ) VALUES (
            NEW.yacht_id,
            v_receiving_number,
            NEW.order_id,
            NOW(),
            NEW.committed_by,
            'completed',
            NEW.id,
            (SELECT ARRAY_AGG(image_id) FROM pms_receiving_session_images WHERE session_id = NEW.id),
            true,
            true
        ) RETURNING id INTO v_receiving_event_id;

        -- Update session with receiving_event_id
        NEW.receiving_event_id := v_receiving_event_id;

        -- Create receiving_line_items from verified draft lines
        FOR v_draft_line IN
            SELECT * FROM pms_receiving_draft_lines
            WHERE session_id = NEW.id
            AND is_verified = true
            AND resolved_disposition IN ('receive_inventory', 'install_immediately')
        LOOP
            INSERT INTO pms_receiving_line_items (
                yacht_id,
                receiving_event_id,
                draft_line_id,
                part_id,
                part_name,
                part_number,
                quantity_received,
                quantity_accepted,
                unit,
                disposition,
                disposition_notes,
                installed_immediately,
                installed_to_equipment_id,
                discrepancy_photo_ids,
                verification_notes,
                human_verified_at,
                human_verified_by,
                received_by,
                is_verified
            ) VALUES (
                NEW.yacht_id,
                v_receiving_event_id,
                v_draft_line.id,
                v_draft_line.resolved_part_id,
                COALESCE(v_draft_line.extracted_part_name, 'Unknown'),
                v_draft_line.extracted_part_number,
                v_draft_line.resolved_quantity,
                v_draft_line.resolved_quantity, -- Assume accepted = received unless discrepancy
                v_draft_line.resolved_unit,
                v_draft_line.resolved_disposition,
                v_draft_line.resolution_notes,
                (v_draft_line.resolved_disposition = 'install_immediately'),
                NULL, -- Equipment ID to be filled by user
                CASE WHEN v_draft_line.discrepancy_photo_id IS NOT NULL
                     THEN ARRAY[v_draft_line.discrepancy_photo_id]
                     ELSE '{}'
                END,
                v_draft_line.resolution_notes,
                v_draft_line.verified_at,
                v_draft_line.verified_by,
                NEW.committed_by,
                true
            );
        END LOOP;

        RAISE NOTICE 'Created receiving event % from session %', v_receiving_number, NEW.session_number;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_create_receiving_event
BEFORE UPDATE ON pms_receiving_sessions
FOR EACH ROW
WHEN (NEW.status = 'committed' AND OLD.status != 'committed')
EXECUTE FUNCTION create_receiving_event_from_session();
```

---

### 4. Rate Limiting Function

```sql
CREATE OR REPLACE FUNCTION check_image_upload_rate_limit(
    p_user_id UUID,
    p_yacht_id UUID
) RETURNS BOOLEAN AS $$
DECLARE
    v_upload_count INT;
BEGIN
    -- Max 50 uploads per hour per user
    SELECT COUNT(*) INTO v_upload_count
    FROM pms_image_uploads
    WHERE uploaded_by = p_user_id
    AND yacht_id = p_yacht_id
    AND uploaded_at > NOW() - INTERVAL '1 hour';

    IF v_upload_count >= 50 THEN
        RAISE EXCEPTION 'Upload rate limit exceeded. Max 50 uploads per hour.';
    END IF;

    RETURN true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Call this from application layer before allowing upload
```

---

### 5. Duplicate Detection Function

```sql
CREATE OR REPLACE FUNCTION check_duplicate_image(
    p_sha256_hash TEXT,
    p_yacht_id UUID
) RETURNS UUID AS $$
DECLARE
    v_existing_image_id UUID;
BEGIN
    -- Check if image with this hash already exists for this yacht
    SELECT id INTO v_existing_image_id
    FROM pms_image_uploads
    WHERE sha256_hash = p_sha256_hash
    AND yacht_id = p_yacht_id
    AND deleted_at IS NULL
    LIMIT 1;

    RETURN v_existing_image_id; -- NULL if no duplicate
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Call this before processing image
-- If returns non-NULL, mark as duplicate and link to existing
```

---

## Supabase Storage RLS Policies

### `receiving-images` Bucket Policies

```sql
-- Users can upload to their yacht folder
CREATE POLICY "Users can upload receiving images for their yacht"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'receiving-images'
    AND (storage.foldername(name))[1] = (SELECT yacht_id::TEXT FROM user_profiles WHERE id = auth.uid())
    AND auth.role() = 'authenticated'
);

-- Users can read their yacht's images
CREATE POLICY "Users can view their yacht's receiving images"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'receiving-images'
    AND (storage.foldername(name))[1] = (SELECT yacht_id::TEXT FROM user_profiles WHERE id = auth.uid())
);

-- Service role full access
CREATE POLICY "Service role full access to receiving images"
ON storage.objects FOR ALL
TO service_role
USING (bucket_id = 'receiving-images')
WITH CHECK (bucket_id = 'receiving-images');

-- No DELETE for users (images are immutable)
```

### Similar policies for other buckets (`discrepancy-photos`, `label-pdfs`, `part-photos`)

---

## Anti-Abuse Mechanisms

### 1. Rate Limiting

**Database Level:**
- Trigger on `pms_image_uploads` INSERT checks `check_image_upload_rate_limit()`
- Max 50 uploads per hour per user

**Application Level:**
- Additional rate limiting via API middleware
- Per-IP rate limits (stored in `pms_image_uploads.upload_ip_address`)

---

### 2. Duplicate Detection

**On Upload:**
1. Compute SHA256 hash of file
2. Call `check_duplicate_image(hash, yacht_id)`
3. If duplicate found:
   - Mark new upload as `is_duplicate = true`
   - Set `duplicate_of_image_id = existing_id`
   - Don't reprocess (save OCR cost)
   - Link to existing extraction results

---

### 3. Validation Gates

**Stage 1 (Intake):**
- File type validation (reject exe, zip, etc.)
- File size limits (15MB for receiving, 10MB for discrepancies)
- Image integrity check
- Basic text detection (reject pure photos with no text)

**Stage 4 (Sanity):**
- If extracted rows < 2 → warn user
- If most rows have no qty → likely not a packing slip
- If OCR confidence very low → suggest retake

---

### 4. Quarantine Bucket

**Failed Validations:**
- Images that fail validation stored in `/quarantine/` subfolder
- Metadata stored in `pms_image_uploads` with `validation_stage = 'failed'`
- Not processed further
- Can be manually reviewed by HOD

---

## Audit Trail & Compliance

### What's Logged:

1. **Image Upload Events**
   - Who uploaded, when, from what IP
   - SHA256 hash (integrity + deduplication)
   - Validation outcome
   - Processing stages

2. **Extraction Results**
   - Raw OCR text preserved
   - Extracted structured data preserved
   - Matching suggestions preserved
   - Final human decisions preserved

3. **Verification Events**
   - Who verified each line, when
   - Before/after values (draft vs resolved)
   - Discrepancy photos linked

4. **Session Lifecycle**
   - State transitions logged
   - Commit timestamp + user
   - Linked receiving_event created

### Immutability:

- `pms_image_uploads` - No UPDATEs to core fields after creation
- `pms_receiving_draft_lines` - Draft preserved after commit (not deleted)
- Images never hard-deleted (soft delete only)

### Retention:

- Images: Indefinite (soft delete only)
- Draft lines: Indefinite (audit trail)
- Labels: 90 days (can regenerate)

---

## Data Types & Constraints

### UUID Generation
- All IDs use `uuid_generate_v4()` (requires `uuid-ossp` extension)

### JSONB Usage
- Flexible metadata storage
- Indexable with GIN indexes if needed
- Examples: `metadata`, `extracted_data`, `classification_metadata`

### Array Columns
- `image_ids UUID[]` - Array of image references
- More efficient than junction tables for simple M:1 relationships
- Indexed with GIN if needed: `CREATE INDEX idx_name ON table USING GIN (array_column);`

### Timestamp Precision
- All timestamps use `TIMESTAMPTZ` (timezone-aware)
- `DEFAULT NOW()` for automatic timestamps

### Text vs VARCHAR
- Use `TEXT` for all string columns (no length limit)
- PostgreSQL optimizes TEXT same as VARCHAR

---

## Migration Script Outline

```sql
-- ============================================================================
-- CAMERA FEATURE - DATABASE MIGRATION
-- ============================================================================
-- Purpose: Add image upload, receiving session, and label generation support
-- Prerequisites: Base PMS schema and Finance/Shopping schema already applied
-- ============================================================================

BEGIN;

-- 1. Create pms_image_uploads table
CREATE TABLE pms_image_uploads (...);
-- Add indexes, triggers, RLS policies

-- 2. Create pms_receiving_sessions table
CREATE TABLE pms_receiving_sessions (...);
-- Add indexes, triggers, RLS policies, session number generation

-- 3. Create pms_receiving_session_images table
CREATE TABLE pms_receiving_session_images (...);
-- Add indexes, RLS policies

-- 4. Create pms_receiving_draft_lines table
CREATE TABLE pms_receiving_draft_lines (...);
-- Add indexes, RLS policies

-- 5. Create pms_label_generations table
CREATE TABLE pms_label_generations (...);
-- Add indexes, RLS policies

-- 6. Alter existing tables
ALTER TABLE pms_receiving_events ADD COLUMN receiving_session_id ...;
ALTER TABLE pms_receiving_line_items ADD COLUMN draft_line_id ...;
ALTER TABLE pms_shopping_list_items ADD COLUMN source_image_ids ...;
ALTER TABLE pms_parts ADD COLUMN photo_ids ...;
ALTER TABLE pms_orders ADD COLUMN shipping_label_image_ids ...;

-- 7. Create helper functions
CREATE FUNCTION check_image_upload_rate_limit ...;
CREATE FUNCTION check_duplicate_image ...;
CREATE FUNCTION enforce_receiving_session_state_transitions ...;
CREATE FUNCTION create_receiving_event_from_session ...;

-- 8. Create Supabase storage buckets (via Supabase Dashboard or API)
-- receiving-images, discrepancy-photos, label-pdfs, part-photos

-- 9. Set up storage RLS policies

COMMIT;
```

---

## Frontend API Endpoints (Reference for Backend)

### Image Upload Flow:

```
POST /api/receiving/upload-image
- Upload file
- Compute SHA256
- Check duplicate
- Check rate limit
- Store in Supabase storage
- Create pms_image_uploads record
- Return image_id + upload confirmation

GET /api/receiving/image-status/{image_id}
- Get validation_stage, document_type, extraction_status
- Poll for OCR completion

POST /api/receiving/create-session
- Create pms_receiving_sessions record
- Link images via pms_receiving_session_images
- Return session_id

GET /api/receiving/session/{session_id}/draft-lines
- Get extracted lines with suggestions
- Return draft_lines array

POST /api/receiving/session/{session_id}/verify-line/{line_id}
- Update pms_receiving_draft_lines
- Set is_verified = true
- Set resolved values

POST /api/receiving/session/{session_id}/commit
- Validate all lines verified or resolved
- Update session status to 'committed'
- Trigger creates pms_receiving_event + line_items
- Return receiving_event_id

POST /api/receiving/generate-labels
- Create pms_label_generations record
- Async job generates PDF
- Store in label-pdfs bucket
- Return generation_id

GET /api/receiving/labels/{generation_id}/download
- Get PDF from storage
- Track download count
```

---

## Summary

This database design provides:

✅ **Complete Image Lifecycle** - Upload → Validation → Classification → Extraction → Verification → Commit
✅ **Audit Trail** - Every image, extraction, and verification permanently logged
✅ **Anti-Abuse** - Rate limiting, duplicate detection, validation gates
✅ **Multi-Stage Pipeline** - Draft lines separate from committed data
✅ **Checkbox Truth** - No auto-commit, explicit human verification required
✅ **Source Preservation** - Original images never deleted, always linked
✅ **Linkages** - Images attached to orders, receiving, parts, shopping list, work orders
✅ **Label Generation** - PDF creation tracked and stored
✅ **RLS Security** - Multi-tenant isolation enforced at row level
✅ **Immutable Audit** - Compliance-ready audit trail

**Next Steps:**
1. Review and approve this schema
2. Create migration SQL file
3. Apply to development environment
4. Test with sample images
5. Build frontend API layer
6. Implement OCR/extraction pipeline
7. Deploy to production

---

**Generated:** 2026-01-09
**Database:** Supabase PostgreSQL
**Version:** 1.0 - Foundation Design
