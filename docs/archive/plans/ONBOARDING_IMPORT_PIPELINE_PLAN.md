# Onboarding Import Pipeline — Implementation Plan

**Date**: 2026-04-01
**Team**: onboard_backend01 (backend), onboard_frontend01 (frontend)
**Status**: DRAFT — awaiting boss approval

---

## 1. ARCHITECTURE OVERVIEW

```
registration.celeste7.ai (Vite+React portal)
         │
         │  POST /api/import/upload (multipart)
         │  GET  /api/import/session/:id
         │  POST /api/import/session/:id/confirm-mapping
         │  POST /api/import/session/:id/dry-run
         │  POST /api/import/session/:id/commit
         │  POST /api/import/session/:id/rollback
         │
         ▼
pipeline-core.int.celeste7.ai (FastAPI on Render)
         │
         │  Validates JWT (MASTER_SUPABASE_JWT_SECRET)
         │  Extracts yacht_id from token
         │
         ├──→ TENANT Supabase Storage (vessel-imports bucket)
         │      File storage: /{yacht_id}/{import_session_id}/{filename}
         │
         ├──→ TENANT Supabase DB (operational tables)
         │      pms_equipment, pms_work_orders, pms_faults,
         │      pms_parts, pms_vessel_certificates, pms_crew_certificates
         │      + NEW: import_sessions table
         │
         └──→ search_index (embedding_status = 'pending')
                │
                ▼
         projection_worker (auto-picks up, builds search_text)
                │
                ▼
         embedding_worker_1536 (generates vectors)
```

### Database Topology
- **MASTER** (qvzmkaamzaqxpzbewjxe.supabase.co): Auth only. JWT verification.
- **TENANT** (vzsohavtuotocgrfkfyd.supabase.co): All import data. Multi-tenant via yacht_id.
- **Connection**: Service role key for bulk inserts, pooler on port 6543 for workers.

---

## 2. SCHEMA CHANGES (TENANT DB)

### 2a. New table: import_sessions

```sql
CREATE TABLE IF NOT EXISTS public.import_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('idea_yacht', 'seahub', 'sealogical', 'generic')),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'detecting', 'mapping', 'preview', 'importing', 'completed', 'failed', 'rolled_back')),
    file_paths JSONB,                    -- array of Supabase Storage paths
    detection_result JSONB,              -- {source_detected, files: [{filename, domain, columns, ...}]}
    column_map JSONB,                    -- {source_col: celeste_field} after human confirms
    preview_summary JSONB,               -- {domains: {equipment: {total, new, ...}}, warnings: [...]}
    records_created JSONB,               -- counts per domain after commit
    warnings JSONB,                      -- array of {field, message, severity}
    created_by TEXT,                      -- email from JWT
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ
);

CREATE INDEX idx_import_sessions_yacht ON import_sessions(yacht_id);
CREATE INDEX idx_import_sessions_status ON import_sessions(status) WHERE status NOT IN ('completed', 'rolled_back');

-- RLS: service_role only (import API uses service key)
ALTER TABLE import_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_only" ON import_sessions FOR ALL TO service_role USING (true);
```

### 2b. Add tracking columns to entity tables

```sql
-- Apply to: pms_equipment, pms_work_orders, pms_faults, pms_parts,
--           pms_vessel_certificates, pms_crew_certificates

ALTER TABLE pms_equipment ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';
ALTER TABLE pms_equipment ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE pms_equipment ADD COLUMN IF NOT EXISTS import_session_id UUID REFERENCES import_sessions(id);
ALTER TABLE pms_equipment ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;

-- Repeat for all 6 tables (script generates all ALTER statements)

-- Indexes for rollback performance
CREATE INDEX IF NOT EXISTS idx_pms_equipment_import_session ON pms_equipment(import_session_id) WHERE import_session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_import_session ON pms_work_orders(import_session_id) WHERE import_session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pms_faults_import_session ON pms_faults(import_session_id) WHERE import_session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pms_parts_import_session ON pms_parts(import_session_id) WHERE import_session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pms_vessel_certificates_import_session ON pms_vessel_certificates(import_session_id) WHERE import_session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pms_crew_certificates_import_session ON pms_crew_certificates(import_session_id) WHERE import_session_id IS NOT NULL;
```

### 2c. Source fields for user references

```sql
-- For imported records where FK user references can't be resolved
ALTER TABLE pms_work_orders ADD COLUMN IF NOT EXISTS source_assigned_to TEXT;
ALTER TABLE pms_work_orders ADD COLUMN IF NOT EXISTS source_created_by TEXT;
ALTER TABLE pms_faults ADD COLUMN IF NOT EXISTS source_reported_by TEXT;
ALTER TABLE pms_faults ADD COLUMN IF NOT EXISTS source_resolved_by TEXT;
```

### 2d. Make user FK columns nullable for imported records

```sql
-- work_orders.created_by is currently NOT NULL with FK to auth.users
-- We need it nullable for imported records
ALTER TABLE pms_work_orders ALTER COLUMN created_by DROP NOT NULL;
```

---

## 3. FILE STRUCTURE (new code in apps/api/)

```
apps/api/
├── routes/
│   └── import_routes.py          # FastAPI router: all 6 endpoints
├── services/
│   └── import_service.py         # Core import logic: parse, detect, map, commit
├── parsers/
│   ├── __init__.py
│   ├── base_parser.py            # Abstract base: ParseResult dataclass
│   ├── csv_parser.py             # CSV: delimiter/encoding detection
│   ├── sql_parser.py             # SQL: extract INSERTs from IDEA Yacht dumps
│   ├── xlsx_parser.py            # XLSX: header row detection, date conversion
│   └── zip_handler.py            # ZIP: extract + identify file types
├── mappers/
│   ├── __init__.py
│   ├── column_matcher.py         # Fuzzy matching: source col → CelesteOS field
│   ├── vocabulary.py             # CelesteOS column vocabulary per domain
│   ├── source_profiles.py        # Known mappings per PMS source
│   ├── date_normalizer.py        # Multi-format date detection and ISO conversion
│   └── status_mapper.py          # Source status values → CelesteOS statuses
├── tests/
│   ├── test_import_pipeline.py   # Integration tests
│   ├── test_parsers.py           # Unit tests for each parser
│   ├── test_column_matcher.py    # Fuzzy matching accuracy tests
│   └── fixtures/
│       └── import_samples/       # Test data (already created)
└── config/
    └── import_source_profiles.yaml  # Column templates per known PMS source
```

---

## 4. API ENDPOINTS (routes/import_routes.py)

### 4a. POST /api/import/upload

**Request**: multipart/form-data
- `source`: string (idea_yacht | seahub | sealogical | generic)
- `files`: one or more files (.csv, .xlsx, .xls, .sql, .zip)

**Response** (201 Created):
```json
{
  "import_session_id": "uuid",
  "status": "detecting",
  "files_received": ["equipment.csv", "work_orders.csv"],
  "message": "Files received. Analysing structure."
}
```

**Backend logic**:
1. Validate JWT → extract yacht_id
2. Create import_sessions row (status='pending')
3. Store files in Supabase Storage: vessel-imports/{yacht_id}/{session_id}/{filename}
4. If .zip: extract, store individual files
5. Update status to 'detecting'
6. Run parse & detect (synchronous for MVP, async for large files later)
7. Store detection_result in import_sessions
8. Return session_id

**Verification criteria**:
- [ ] Files actually stored in Supabase Storage (not just 201)
- [ ] import_sessions row created with correct yacht_id
- [ ] detection_result contains correct column names from the uploaded file
- [ ] Encoding correctly detected (test with Latin-1 fixture)
- [ ] Delimiter correctly detected (test with semicolon IDEA fixture)
- [ ] Header row correctly identified (test with Sealogical metadata rows)

### 4b. GET /api/import/session/:id

**Response** (200 OK):
```json
{
  "id": "uuid",
  "yacht_id": "uuid",
  "source": "idea_yacht",
  "status": "mapping",
  "file_paths": ["vessel-imports/yacht-id/sess-id/equipment.csv"],
  "detection_result": {
    "source_detected": "idea_yacht",
    "files": [{
      "filename": "equipment.csv",
      "domain": "equipment",
      "encoding_detected": "latin-1",
      "delimiter_detected": ";",
      "header_row": 0,
      "row_count": 15,
      "date_format_detected": "DD-MMM-YYYY",
      "columns": [{
        "source_name": "EQUIP_NAME",
        "suggested_target": "name",
        "confidence": 0.95,
        "sample_values": ["Main Engine Port", "Generator 1", "Watermaker", "Bow Thruster", "AC Plant"]
      }],
      "warnings": []
    }]
  },
  "celeste_vocabulary": {
    "equipment": {
      "mappable": ["name", "manufacturer", "model", "serial_number", "location", "category", "status", "criticality", "description", "code", "system_type"],
      "auto_set": ["id", "yacht_id", "created_at", "updated_at", "source", "source_id", "import_session_id", "imported_at"]
    },
    "work_orders": {
      "mappable": ["title", "description", "status", "priority", "due_date", "completed_at", "completion_notes"],
      "auto_set": ["id", "yacht_id", "wo_number", "created_by", "created_at", "updated_at", "source", "source_id", "import_session_id", "imported_at"]
    },
    "faults": {
      "mappable": ["title", "description", "severity", "status", "fault_code", "detected_at", "resolved_at", "resolution_notes"],
      "auto_set": ["id", "yacht_id", "created_at", "updated_at", "source", "source_id", "import_session_id", "imported_at"]
    },
    "parts": {
      "mappable": ["name", "description", "part_number", "category", "manufacturer", "unit", "quantity_on_hand", "minimum_quantity", "location"],
      "auto_set": ["id", "yacht_id", "created_at", "updated_at", "source", "source_id", "import_session_id", "imported_at"]
    },
    "vessel_certificates": {
      "mappable": ["certificate_type", "certificate_name", "certificate_number", "issuing_authority", "issue_date", "expiry_date", "last_survey_date", "next_survey_due", "status"],
      "auto_set": ["id", "yacht_id", "created_at", "source", "source_id", "import_session_id", "imported_at"]
    },
    "crew_certificates": {
      "mappable": ["person_name", "certificate_type", "certificate_number", "issuing_authority", "issue_date", "expiry_date"],
      "auto_set": ["id", "yacht_id", "created_at", "source", "source_id", "import_session_id", "imported_at"]
    }
  },
  "column_map": null,
  "preview_summary": null,
  "records_created": null,
  "created_at": "2026-04-01T12:00:00Z",
  "completed_at": null
}
```

**Verification criteria**:
- [ ] Returns correct session data (not just 200)
- [ ] celeste_vocabulary matches actual tenant DB columns
- [ ] detection_result.files[].columns has meaningful confidence scores
- [ ] sample_values are real data from the file (not empty arrays)
- [ ] yacht_id matches the JWT token (cross-tenant leak prevention)

### 4c. POST /api/import/session/:id/confirm-mapping

**Request**:
```json
{
  "mappings": [{
    "file": "equipment.csv",
    "domain": "equipment",
    "columns": [
      {"source": "EQUIP_NAME", "target": "name", "action": "map"},
      {"source": "SERIAL_NO", "target": "serial_number", "action": "map"},
      {"source": "PARENT_EQUIP_ID", "target": null, "action": "skip"},
      {"source": "RUNNING_HOURS", "target": "running_hours", "action": "map", "date_format": null}
    ]
  }]
}
```

**Response** (200 OK):
```json
{
  "status": "mapping_confirmed",
  "message": "Column mapping saved. Ready for dry run."
}
```

**Backend logic**:
1. Validate session exists and status='mapping' (or 'detecting')
2. Store column_map in import_sessions
3. Update status to 'mapping'
4. NEVER auto-proceed to dry-run — wait for explicit trigger

**Verification criteria**:
- [ ] column_map actually stored in DB (query and verify)
- [ ] Status updated to 'mapping'
- [ ] Cannot confirm mapping twice (idempotent or error)
- [ ] Cannot confirm mapping for a different yacht_id's session

### 4d. POST /api/import/session/:id/dry-run

**Response** (200 OK):
```json
{
  "status": "preview",
  "preview_summary": {
    "domains": {
      "equipment": {"total": 15, "new": 15, "duplicates": 0, "errors": 0, "warnings_count": 1},
      "work_orders": {"total": 12, "new": 12, "orphaned": 0, "errors": 0, "warnings_count": 0}
    },
    "total_records": 27,
    "can_commit": true,
    "warnings": [
      {"domain": "equipment", "row": 8, "field": "RUNNING_HOURS", "message": "Empty value — will import as NULL", "severity": "info"}
    ],
    "first_10": {
      "equipment": [
        {"name": "Main Engine Port", "manufacturer": "MTU", "model": "16V4000 M93L", "serial_number": "MTU-2019-7834", "location": "Engine Room Deck 3"}
      ]
    }
  }
}
```

**Backend logic**:
1. Read file(s) from Supabase Storage
2. Apply column_map to transform source data → CelesteOS schema
3. Validate each row: required fields present, dates parseable, no duplicate source_ids
4. Check for UNIQUE constraint conflicts (equipment name, part_number, wo_number)
5. Count per domain: total, new, duplicates, errors
6. Store preview_summary in import_sessions
7. Update status to 'preview'
8. DO NOT write to production tables

**Verification criteria**:
- [ ] Row counts match source file (not just "has data")
- [ ] Dates converted to ISO 8601 (spot-check actual values)
- [ ] Duplicate detection actually works (test with overlapping data)
- [ ] UNIQUE constraint conflicts flagged (not just caught at commit time)
- [ ] can_commit=false when there are red-severity errors
- [ ] first_10 rows contain real transformed data

### 4e. POST /api/import/session/:id/commit

**Response** (200 OK):
```json
{
  "status": "completed",
  "records_created": {
    "equipment": 15,
    "work_orders": 12,
    "faults": 5,
    "parts": 10,
    "vessel_certificates": 8,
    "crew_certificates": 0
  },
  "message": "Import complete. 50 records imported. Your vessel history is now searchable.",
  "rollback_available_until": "2026-04-03T12:00:00Z"
}
```

**Backend logic**:
1. Verify status='preview' and can_commit=true
2. Begin transaction
3. For each domain, for each row:
   a. Transform using column_map
   b. Set: yacht_id, source, source_id, import_session_id, imported_at=now()
   c. Set: created_by=NULL, source_created_by="unknown" (for user FK fields)
   d. INSERT into target table (pms_equipment, etc.)
   e. INSERT into search_index with embedding_status='pending', object_type, object_id, yacht_id
4. Update import_sessions: status='completed', completed_at=now(), records_created
5. Commit transaction
6. Return summary

**Verification criteria**:
- [ ] All records have correct yacht_id (query DB, don't trust response)
- [ ] All records have source='idea_yacht' (or whichever source)
- [ ] All records have import_session_id set
- [ ] All records have imported_at set (not null)
- [ ] source_id preserves original ID from source system
- [ ] search_index rows created with embedding_status='pending'
- [ ] Row counts in response match actual DB row counts
- [ ] No cross-tenant data leakage (query with different yacht_id returns 0)

### 4f. POST /api/import/session/:id/rollback

**Response** (200 OK):
```json
{
  "status": "rolled_back",
  "records_deleted": {
    "equipment": 15,
    "work_orders": 12,
    "faults": 5,
    "parts": 10,
    "vessel_certificates": 8,
    "search_index": 50
  },
  "message": "Import reversed. All imported records have been removed."
}
```

**Backend logic**:
1. Verify status='completed' and rolled_back_at is NULL
2. Verify within 48-hour window
3. Begin transaction
4. DELETE FROM each entity table WHERE import_session_id = :id AND yacht_id = :yacht_id
5. DELETE FROM search_index WHERE object_id IN (deleted IDs) AND yacht_id = :yacht_id
6. Update import_sessions: status='rolled_back', rolled_back_at=now()
7. Commit transaction

**Verification criteria**:
- [ ] Records actually deleted from entity tables (query DB)
- [ ] search_index rows also deleted
- [ ] Cannot rollback after 48 hours
- [ ] Cannot rollback someone else's import (yacht_id enforcement)
- [ ] import_sessions status updated to 'rolled_back'

---

## 5. PARSER DESIGN

### 5a. Encoding detection
- Library: `charset-normalizer` (faster, more accurate than chardet)
- Read first 10KB of file, detect encoding
- Convert to UTF-8 on load

### 5b. CSV parsing
- Library: Python `csv` module (stdlib, no extra dependency)
- Delimiter detection: count `;`, `,`, `\t` in first 5 lines, pick highest
- Header row: first non-empty row where most cells are strings

### 5c. XLSX parsing
- Library: `openpyxl` (read-only mode for memory efficiency)
- Header detection: scan rows 1-10 for the row with most non-empty string cells
- Date handling: check cell type — if datetime, convert directly; if string, parse with date_normalizer
- Strip metadata rows (Sealogical pattern)

### 5d. SQL parsing
- Library: `sqlparse` for tokenization of CREATE TABLE + INSERT statements
- Custom regex parser for pg_dump `COPY ... FROM stdin;` blocks (tab-separated data — sqlparse cannot handle these)
- Extract: CREATE TABLE statements → schema detection, column names
- Extract: INSERT INTO statements → data rows
- Extract: COPY blocks → table_name, columns, tab-delimited rows
- Map column positions from CREATE TABLE to INSERT VALUES
- Handle: multiline strings, escaped quotes, NULL values
- Memory: stream file and split on statement boundaries (`;` + newline), never load entire SQL dump

### 5e. ZIP handling (with embedded documents/media)
- Library: `zipfile` (stdlib)
- Extract to temp directory
- **Classify files by extension into two pipelines:**

**Data pipeline** (parse → detect → map → import):
  - `.csv`, `.sql`, `.xlsx`, `.xls` → route to appropriate parser

**Document pipeline** (store → index → search):
  - `.pdf`, `.jpg`, `.png`, `.tiff`, `.docx` → store in `vessel-documents` Supabase bucket
  - Create `doc_metadata` row per file (filename, content_type, storage_path, size, yacht_id, source, import_session_id)
  - Insert `search_index` row with `embedding_status='pending'` → projection_worker extracts text via PyMuPDF (already in requirements.txt)
  - Storage path: `vessel-documents/{yacht_id}/{domain}/{filename}` — domain inferred from ZIP folder structure

**Unknown files** → store in `vessel-imports/{yacht_id}/{session_id}/unclassified/` and flag for manual review

- Use ZIP folder names as domain hints (e.g., `/Certificates/` → certificates domain, `/Manuals/` → manuals, `/Photos/Faults/` → fault attachments)
- Associate all files with single import_session_id
- Report document counts alongside data counts in detection_result

### 5f. Date normalization
- Detect format from sample values (test multiple patterns)
- Patterns: ISO 8601, DD/MM/YYYY, MM/DD/YYYY, DD-MMM-YYYY, Excel serial
- Ambiguous dates (01/02/2025): flag as warning, ask user in mapping step
- Convert all to ISO 8601 (YYYY-MM-DD) for storage

### 5g. Fuzzy column matching
- Library: `rapidfuzz` (fast C-based fuzzy matching)
- Match source column names against CelesteOS vocabulary
- Score threshold: ≥90% = green (auto-map), 60-89% = amber (suggest), <60% = red (manual)
- Known source profiles override fuzzy matching (IDEA EQUIP_NAME → name is 100%)

---

## 6. COLUMN MAPPING ENGINE

### Known source profiles (mappers/source_profiles.py)

```python
IDEA_YACHT_PROFILE = {
    "equipment": {
        "EQUIP_NAME": "name",
        "EQUIP_CODE": "code",
        "MAKER": "manufacturer",
        "MODEL": "model",
        "SERIAL_NO": "serial_number",
        "LOCATION": "location",
        "CLASS_CODE": "system_type",
        "CRITICALITY": "criticality",
        "STATUS": "status",
        "RUNNING_HOURS": "running_hours",
        "SERVICE_INTERVAL_HOURS": "service_interval_hours",
    },
    "work_orders": {
        "WO_NUMBER": "wo_number",
        "DESCRIPTION": "title",
        "PRIORITY": "priority",
        "STATUS": "status",
        "DUE_DATE": "due_date",
        "COMPLETED_DATE": "completed_at",
        "ASSIGNED_TO": "source_assigned_to",
        "REMARKS": "completion_notes",
    },
    # ... faults, parts, certificates
}

SEAHUB_PROFILE = {
    "equipment": {
        "equipment_name": "name",
        "equipment_code": "code",
        "maker": "manufacturer",
        "model": "model",
        "serial_number": "serial_number",
        "location": "location",
        "criticality": "criticality",
        "status": "status",
        "running_hours": "running_hours",
        "service_interval_hours": "service_interval_hours",
    },
    # ... Seahub "defects" → faults, "tasks" → work_orders, "inventory" → parts
}
```

### Status mapping (mappers/status_mapper.py)

```python
STATUS_MAP = {
    "idea_yacht": {
        "equipment.status": {"ACTIVE": "operational", "INACTIVE": "decommissioned", "MAINTENANCE": "maintenance"},
        "work_orders.status": {"COMPLETED": "completed", "OPEN": "open", "IN_PROGRESS": "in_progress"},
        "work_orders.priority": {"HIGH": "high", "NORMAL": "normal", "CRITICAL": "urgent", "LOW": "low"},
    },
    "seahub": {
        "defects.status": {"open": "open", "closed": "resolved", "in_progress": "in_progress", "rectified": "resolved"},
        "tasks.status": {"open": "open", "completed": "completed"},
    },
}
```

---

## 7. SEARCH INDEX WIRING

After commit, for every imported entity:

```python
# Insert search_index row so projection_worker picks it up
cur.execute("""
    INSERT INTO search_index (
        object_type, object_id, yacht_id, org_id,
        embedding_status, embedding_priority, updated_at
    ) VALUES (%s, %s, %s, %s, 'pending', 0, now())
    ON CONFLICT (object_type, object_id) DO UPDATE SET
        embedding_status = 'pending',
        updated_at = now()
""", (object_type, str(entity_id), yacht_id, yacht_id))
```

The projection_worker (polling every 5s, batch of 50) will:
1. Claim these rows
2. Read the source entity from pms_equipment / pms_work_orders / etc.
3. Build search_text, filters, payload per projection.yaml
4. Mark as 'indexed'

The embedding_worker_1536 will then generate vectors.

**Estimated processing time for a typical vessel import (600 records):**
- Projection: 600 records / 50 per batch / 5s interval = ~60 seconds
- Embedding: 600 records at ~500/min = ~72 seconds
- Total: **~2-3 minutes** until fully searchable

---

## 8. AUTH FLOW

```
User completes 2FA on registration.celeste7.ai
         │
         ▼
Registration backend issues JWT:
{
  "sub": "captain@vessel.com",
  "yacht_id": "85fe1119-...",
  "scope": "import",
  "iat": 1711975200,
  "exp": 1712061600  (24 hours)
}
Signed with: MASTER_SUPABASE_JWT_SECRET
         │
         ▼
Frontend stores token, sends as:
Authorization: Bearer <token>
         │
         ▼
pipeline-core verifies:
1. Decode JWT with MASTER_SUPABASE_JWT_SECRET
2. Check exp > now()
3. Check scope == "import"
4. Extract yacht_id
5. All DB queries scoped to this yacht_id
```

**CORS update needed on pipeline-core**:
```
ALLOWED_ORIGINS += "https://registration.celeste7.ai"
```

---

## 9. DEPENDENCIES (new pip packages)

```
# Add to apps/api/requirements.txt
openpyxl==3.1.5              # XLSX parsing (read-only streaming mode)
xlrd==2.0.1                  # Legacy .xls parsing (pre-2007 Excel)
rapidfuzz==3.9.7             # Fuzzy column name matching (C++ compiled, 10-100x faster than fuzzywuzzy)
sqlparse==0.5.3              # SQL tokenization for IDEA Yacht dumps
python-dateutil==2.9.0       # Multi-format date parsing with DD/MM vs MM/DD detection
```

Note: `charset-normalizer` is already a transitive dependency of `httpx` (via httpcore).
`csv`, `zipfile`, `json`, `io`, `tempfile`, `re` are stdlib — zero added weight.

**NOT needed**: pandas (150MB+, overkill), polars (same), chardet (slower, less accurate than charset-normalizer), fuzzywuzzy (deprecated, replaced by rapidfuzz), python-magic (extension-based detection sufficient).

Total added weight: ~15MB installed. All ship pre-built wheels for Linux/macOS/Windows on Python 3.11+.

---

## 10. IMPLEMENTATION ORDER

| Step | What | Who | Days | Unlocks |
|------|------|-----|------|---------|
| 1 | Schema migrations (import_sessions + ALTER columns) | Backend | 0.5 | Everything |
| 2 | CSV parser + encoding/delimiter detection | Backend | 1 | Upload endpoint |
| 3 | Upload endpoint + Supabase Storage wiring | Backend | 1 | Frontend upload UI |
| 4 | Column matcher + known source profiles | Backend | 1 | Mapping endpoint |
| 5 | Upload UI + source dropdown + file picker | Frontend | 1 | Integration test |
| 6 | Confirm-mapping endpoint | Backend | 0.5 | Mapping UI |
| 7 | Column mapping review UI | Frontend | 2 | Human gate |
| 8 | Dry-run logic + preview endpoint | Backend | 1.5 | Preview UI |
| 9 | Dry-run preview UI | Frontend | 1 | Commit flow |
| 10 | Commit endpoint + search_index wiring | Backend | 1 | Live import |
| 11 | Commit confirmation + completion UI | Frontend | 0.5 | Full flow |
| 12 | Rollback endpoint + UI | Both | 1 | Safety net |
| 13 | XLSX parser (Sealogical) | Backend | 0.5 | XLSX support |
| 14 | SQL parser (IDEA Yacht) | Backend | 1 | SQL support |
| 15 | ZIP handler | Backend | 0.5 | Multi-file uploads |
| **Total** | | | **~13 days** | |

Steps 1-7 unlock the demo (upload + detect + map).
Steps 8-11 unlock full import.
Steps 12-15 are polish/completeness.

---

## 11. KNOWN RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Real PMS exports differ from test fixtures | Parser fails on real data | Request sample exports from a customer; build parser defensively with fallbacks |
| Large files (>100MB) timeout on Render Starter | Upload/parse fails | Chunked upload for files >50MB; async processing with status polling |
| Equipment hierarchy loss (no parent_id) | Data structure degraded | Store parent info in metadata JSONB; can be linked later |
| Cross-tenant data leakage | Security breach | Every query includes yacht_id; integration tests verify isolation |
| Supabase Storage 50MB free tier limit | Upload blocked | vessel-imports bucket; monitor usage; upgrade if needed |
| User FK columns NOT NULL constraints | Migration breaks existing rows | Use ALTER COLUMN DROP NOT NULL carefully; verify no existing code depends on NOT NULL |

---

## 12. VERIFICATION STRATEGY (per verification-integrity skill)

### What constitutes a REAL SUCCESS:

1. **Upload**: File exists in Supabase Storage at correct path AND import_sessions row exists with correct yacht_id AND detection_result is populated with real column data
2. **Detect**: Encoding, delimiter, header row, and date format are ALL correct for each PMS source type (tested against fixtures)
3. **Map**: Column map stored in DB matches what was sent AND cannot be bypassed (no auto-proceed)
4. **Dry Run**: Row counts match source file exactly AND dates are ISO 8601 AND duplicates flagged AND can_commit reflects actual error state
5. **Commit**: Entity table row counts match AND yacht_id on every row AND search_index rows created with embedding_status='pending' AND source_id preserved
6. **Rollback**: Entity rows actually deleted AND search_index rows deleted AND cannot rollback after 48h AND cannot rollback another yacht's data

### What constitutes a FALSE SUCCESS:

- 200 OK but detection_result is empty or has wrong columns
- "15 records imported" but only 10 actually in DB
- search_index rows created but with wrong object_type
- Test passes but assertions only check HTTP status, not response body
- Commit "succeeds" but yacht_id is NULL on imported records

### Test matrix (minimum):

| Test | IDEA Yacht | Seahub | Sealogical | Generic |
|------|-----------|--------|------------|---------|
| Encoding detection | Latin-1 | UTF-8 | Windows-1252 | UTF-8 |
| Delimiter detection | semicolon | comma | comma | tab |
| Header row detection | row 0 | row 0 | row 4 (skip metadata) | row 0 |
| Date format | DD-MMM-YYYY | ISO | DD/MM/YYYY | mixed |
| Column matching | UPPER_SNAKE | snake_case | Title Case | unknown |
| Vocabulary mapping | defects=faults | defects=faults | — | — |
| Status mapping | ACTIVE→operational | open→open | Active→operational | — |
| Equipment hierarchy | parent_id present | parent_id present | flat | flat |
| Rollback | ✓ | ✓ | ✓ | ✓ |

---

**END OF PLAN — AWAITING BOSS APPROVAL**
