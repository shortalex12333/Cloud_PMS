# Implementation Plan

## Step-by-Step Rollout

This document provides the detailed implementation sequence for the Handover Export System.

---

## Phase 1: Database Cleanup (COMPLETED)

**Status:** ✅ Done

### 1.1 Drop Orphaned Tables

```sql
-- Backups created
CREATE TABLE _bkp_dash_handover_records AS TABLE dash_handover_records WITH NO DATA;
CREATE TABLE _bkp_dash_handover_items AS TABLE dash_handover_items WITH NO DATA;
CREATE TABLE _bkp_handover_entries AS TABLE handover_entries WITH NO DATA;
CREATE TABLE _bkp_handover_sources AS TABLE handover_sources WITH NO DATA;

-- Drops executed
DROP TABLE dash_handover_records CASCADE;
DROP TABLE dash_handover_items CASCADE;
DROP TABLE handover_entries CASCADE;
DROP TABLE handover_sources CASCADE;
```

### 1.2 Add Missing Foreign Keys

```sql
-- handovers FKs
ALTER TABLE handovers ADD CONSTRAINT fk_handovers_yacht
    FOREIGN KEY (yacht_id) REFERENCES yacht_registry(id);
ALTER TABLE handovers ADD CONSTRAINT fk_handovers_created_by
    FOREIGN KEY (created_by) REFERENCES auth_users_profiles(id);
ALTER TABLE handovers ADD CONSTRAINT fk_handovers_approved_by
    FOREIGN KEY (approved_by) REFERENCES auth_users_profiles(id);
ALTER TABLE handovers ADD CONSTRAINT fk_handovers_from_user
    FOREIGN KEY (from_user_id) REFERENCES auth_users_profiles(id);
ALTER TABLE handovers ADD CONSTRAINT fk_handovers_to_user
    FOREIGN KEY (to_user_id) REFERENCES auth_users_profiles(id);

-- handover_items FKs
ALTER TABLE handover_items ADD CONSTRAINT fk_handover_items_yacht
    FOREIGN KEY (yacht_id) REFERENCES yacht_registry(id);
ALTER TABLE handover_items ADD CONSTRAINT fk_handover_items_added_by
    FOREIGN KEY (added_by) REFERENCES auth_users_profiles(id);
ALTER TABLE handover_items ADD CONSTRAINT fk_handover_items_updated_by
    FOREIGN KEY (updated_by) REFERENCES auth_users_profiles(id);
ALTER TABLE handover_items ADD CONSTRAINT fk_handover_items_acknowledged_by
    FOREIGN KEY (acknowledged_by) REFERENCES auth_users_profiles(id);
```

### 1.3 Create Unified View

```sql
CREATE OR REPLACE VIEW v_handover_export_items AS
-- (see 01_data_model.md for full definition)
```

### 1.4 Add Indexes

```sql
CREATE INDEX idx_handovers_yacht ON handovers(yacht_id);
CREATE INDEX idx_handovers_shift_date ON handovers(shift_date);
CREATE INDEX idx_handover_items_handover ON handover_items(handover_id);
CREATE INDEX idx_handover_items_yacht ON handover_items(yacht_id);
-- etc.
```

---

## Phase 2: Service Implementation

### 2.1 Create Export Service (COMPLETED)

**File:** `apps/api/services/handover_export_service.py`

Features:
- Fetch from unified view
- Enrich with entity details
- Generate HTML with hyperlinks
- Create export records

### 2.2 Create Export Routes (COMPLETED)

**File:** `apps/api/routes/handover_export_routes.py`

Endpoints:
- `POST /v1/handover/export`
- `POST /v1/handover/export/html`
- `GET /v1/handover/exports`
- `GET /v1/handover/export/{id}`

### 2.3 Register Routes (COMPLETED)

**File:** `apps/api/pipeline_service.py`

```python
try:
    from routes.handover_export_routes import router as handover_export_router
    app.include_router(handover_export_router)
    logger.info("✅ Handover Export routes registered at /v1/handover/*")
except Exception as e:
    logger.error(f"❌ Failed to register Handover Export routes: {e}")
```

---

## Phase 3: Draft Workflow Implementation

### 3.1 Create Draft Generator Service

**File:** `apps/api/services/draft_generator_service.py`

```python
class DraftGeneratorService:
    """
    Generates handover drafts from source items.

    Steps:
    1. Fetch candidate items from unified view
    2. Group by presentation bucket
    3. Create draft record
    4. Create sections and items
    """

    BUCKET_ORDER = [
        "Command", "Engineering", "ETO_AVIT",
        "Deck", "Interior", "Galley",
        "Security", "Admin_Compliance"
    ]

    async def generate_draft(
        self,
        yacht_id: str,
        user_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> str:
        """Generate draft from items in period."""
        ...
```

### 3.2 Create Draft Routes

**File:** `apps/api/routes/handover_draft_routes.py`

Endpoints:
- `POST /v1/handover/draft/generate`
- `GET /v1/handover/draft/{id}`
- `POST /v1/handover/draft/{id}/review`
- `PATCH /v1/handover/draft/{id}/item/{item_id}`
- `POST /v1/handover/draft/{id}/merge`
- `POST /v1/handover/draft/{id}/accept`
- `POST /v1/handover/draft/{id}/sign`

### 3.3 Create Signoff Service

**File:** `apps/api/services/handover_signoff_service.py`

```python
class HandoverSignoffService:
    """
    Handles draft acceptance and signing.

    Enforces:
    - State machine rules
    - Different users for accept/sign
    - Document hash generation
    """

    async def accept_draft(self, draft_id: str, user_id: str) -> dict:
        """Outgoing officer accepts draft."""
        ...

    async def sign_draft(self, draft_id: str, user_id: str) -> dict:
        """Incoming officer countersigns."""
        ...
```

---

## Phase 4: PDF Generation

### 4.1 Install WeasyPrint

```bash
# Requirements
pip install weasyprint

# System dependencies (macOS)
brew install pango cairo gdk-pixbuf libffi
```

### 4.2 Create PDF Generator

**File:** `apps/api/services/pdf_generator.py`

```python
from weasyprint import HTML, CSS

class PDFGenerator:
    """Generate PDFs from HTML content."""

    def generate(self, html: str, output_path: str) -> str:
        """Convert HTML to PDF."""
        doc = HTML(string=html)
        doc.write_pdf(
            output_path,
            stylesheets=[self._print_css()]
        )
        return output_path

    def _print_css(self) -> CSS:
        """Print-optimized CSS."""
        return CSS(string='''
            @page {
                size: A4;
                margin: 2cm;
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages);
                }
            }
        ''')
```

### 4.3 Create Storage Service

**File:** `apps/api/services/storage_service.py`

```python
class StorageService:
    """Handle Supabase storage operations."""

    async def upload_export(
        self,
        yacht_id: str,
        draft_id: str,
        content: bytes,
        content_type: str,
        file_ext: str
    ) -> str:
        """Upload export file to storage."""
        path = f"{yacht_id}/handover/{draft_id}/{timestamp()}.{file_ext}"
        self.db.storage.from_("handover-exports").upload(
            path, content, {"content-type": content_type}
        )
        return path
```

---

## Phase 5: Email Integration

### 5.1 Create Email Sender Service

**File:** `apps/api/services/email_sender_service.py`

```python
class EmailSenderService:
    """Send handover reports via email."""

    async def send_handover(
        self,
        recipients: List[str],
        subject: str,
        html_body: str,
        pdf_attachment: bytes
    ) -> dict:
        """Send handover email with PDF attachment."""
        ...
```

### 5.2 Integrate with Microsoft Graph

For yachts with Outlook integration, use Graph API to send from user's mailbox:

```python
async def send_via_graph(
    self,
    access_token: str,
    recipients: List[str],
    subject: str,
    body: str,
    attachment: bytes
) -> dict:
    """Send via Microsoft Graph API."""
    ...
```

---

## Phase 6: Import/Migration Tools

### 6.1 Create Import Service

**File:** `apps/api/services/handover_import_service.py`

```python
class HandoverImportService:
    """Import legacy data into draft workflow."""

    async def import_from_legacy(
        self,
        handover_id: str,
        yacht_id: str,
        user_id: str
    ) -> str:
        """Import handovers + handover_items into draft."""
        ...

    async def import_from_quickadd(
        self,
        yacht_id: str,
        user_id: str,
        date_from: date,
        date_to: date
    ) -> str:
        """Import pms_handover items into draft."""
        ...
```

### 6.2 Create Import Routes

```python
@router.post("/v1/handover/import-from-legacy")
async def import_legacy(...) -> dict:
    ...

@router.post("/v1/handover/import-from-quickadd")
async def import_quickadd(...) -> dict:
    ...
```

---

## Phase 7: RLS and Security

### 7.1 Apply RLS Policies

```sql
-- Execute SQL from 07_security_rls.md
-- All policies for draft tables
```

### 7.2 Create Storage Bucket

```sql
INSERT INTO storage.buckets (id, name, public)
VALUES ('handover-exports', 'handover-exports', false);

-- Apply yacht isolation policy
CREATE POLICY "handover_exports_storage"
ON storage.objects FOR ALL
TO authenticated
USING (
    bucket_id = 'handover-exports'
    AND (storage.foldername(name))[1] = get_user_yacht_id()::text
);
```

### 7.3 Apply Audit Triggers

```sql
-- Triggers from 07_security_rls.md
CREATE TRIGGER handover_drafts_audit ...
CREATE TRIGGER handover_signoffs_audit ...
CREATE TRIGGER handover_exports_audit ...
```

---

## Phase 8: Testing and Validation

### 8.1 Unit Tests

- Draft generator service
- Export service
- Signoff service
- PDF generator

### 8.2 Integration Tests

- Full draft → sign → export flow
- Import from legacy
- RLS isolation

### 8.3 E2E Tests

- User journey: add item → export
- Multi-user sign-off

---

## Deployment Checklist

### Pre-Deployment

- [ ] All SQL migrations reviewed
- [ ] Backup of existing data
- [ ] RLS policies tested in staging
- [ ] WeasyPrint dependencies installed
- [ ] Storage bucket created
- [ ] Environment variables set

### Deployment

- [ ] Deploy database migrations
- [ ] Deploy API changes
- [ ] Verify routes registered
- [ ] Test export endpoint
- [ ] Test draft workflow

### Post-Deployment

- [ ] Monitor error logs
- [ ] Verify RLS working
- [ ] Test from different yacht contexts
- [ ] Document any issues

---

## Rollback Plan

### Database Rollback

```sql
-- Drop new constraints
ALTER TABLE handovers DROP CONSTRAINT IF EXISTS fk_handovers_yacht;
-- etc.

-- Restore dropped tables from backup
CREATE TABLE dash_handover_records AS TABLE _bkp_dash_handover_records;
-- etc.

-- Drop unified view
DROP VIEW IF EXISTS v_handover_export_items;
```

### Code Rollback

```bash
# Revert to previous commit
git revert HEAD

# Redeploy
render deploy
```

---
