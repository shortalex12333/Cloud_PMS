# Entity Lens: Document

**Status**: v1 - PRODUCTION READY
**Last Updated**: 2026-01-25
**Schema Source**: Production Supabase Database (db_truth_snapshot.md)

---

# BLOCKERS

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| ⚠️ | RLS uses mixed patterns | Consistency | Migrate to canonical get_user_yacht_id() |

---

# PART 1: DATABASE SCHEMA

## Table: `doc_metadata`

**Production DB Columns** (21 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry |
| `source` | text | NOT NULL | BACKEND_AUTO | Upload source |
| `original_path` | text | YES | BACKEND_AUTO | Original file location |
| `filename` | text | NOT NULL | REQUIRED | File name |
| `content_type` | text | YES | BACKEND_AUTO | MIME type |
| `size_bytes` | bigint | YES | BACKEND_AUTO | File size |
| `sha256` | text | YES | BACKEND_AUTO | Checksum |
| `storage_path` | text | NOT NULL | BACKEND_AUTO | Cloud storage path |
| `equipment_ids` | uuid[] | YES | CONTEXT | Linked equipment. Default: '{}' |
| `tags` | text[] | YES | OPTIONAL | User tags. Default: '{}' |
| `indexed` | boolean | YES | BACKEND_AUTO | Is document indexed. Default: false |
| `indexed_at` | timestamp | YES | BACKEND_AUTO | When indexed |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |
| `created_at` | timestamp | NOT NULL | BACKEND_AUTO | NOW() |
| `updated_at` | timestamp | NOT NULL | BACKEND_AUTO | Trigger |
| `system_path` | text | YES | CONTEXT | Hierarchical path (e.g., "Engineering/Main Engine") |
| `doc_type` | text | YES | OPTIONAL | Document type classification |
| `oem` | text | YES | OPTIONAL | OEM/Manufacturer |
| `model` | text | YES | OPTIONAL | Model reference |
| `system_type` | text | YES | OPTIONAL | System classification |

**Row Count**: 2,759

---

## Key Indexes

| Index | Purpose |
|-------|---------|
| `idx_documents_equipment_ids` | GIN - Equipment lookup |
| `idx_documents_tags` | GIN - Tag filtering |
| `idx_documents_system_path` | Hierarchical navigation |
| `idx_documents_system_path_gin` | Trigram search on path |
| `idx_documents_doc_type` | Filter by type |
| `idx_documents_oem` | Filter by manufacturer |
| `idx_documents_indexed` | Find unindexed docs |

---

## RLS Policies

```sql
-- SELECT: Users can view (mixed pattern - uses both functions)
CREATE POLICY "Users can view documents" ON doc_metadata
    FOR SELECT TO public
    USING (yacht_id = COALESCE(jwt_yacht_id(), get_user_yacht_id()));

-- INSERT: System can insert
CREATE POLICY "System can insert documents" ON doc_metadata
    FOR INSERT TO public
    WITH CHECK (yacht_id = get_user_yacht_id());

-- ALL: Managers can manage
CREATE POLICY "Managers can manage documents" ON doc_metadata
    FOR ALL TO public
    USING ((yacht_id = jwt_yacht_id()) AND is_manager());

-- Service role bypass
CREATE POLICY "Service role full access documents" ON doc_metadata
    FOR ALL TO service_role
    USING (true);
```

**Note**: Mixed RLS patterns detected. Consider migrating to canonical `get_user_yacht_id()`.

---

# PART 2: MICRO-ACTIONS

## Action 1: `view_document`

**Purpose**: Open/download document

**Allowed Roles**: All Crew (read-only)

**Tables Read**: `doc_metadata`, generates signed URL from storage

---

## Action 2: `add_tags`

**Purpose**: Add tags to document for organization

**Allowed Roles**: All Crew

**Tables Written**: `doc_metadata` (UPDATE tags), `pms_audit_log`

---

## Action 3: `link_to_equipment`

**Purpose**: Associate document with equipment

**Allowed Roles**: Engineers

**Tables Written**: `doc_metadata` (UPDATE equipment_ids), `pms_audit_log`

---

## Action 4: `view_linked_equipment` (Escape Hatch)

**Purpose**: Navigate to equipment this document relates to

**Allowed Roles**: All Crew (read-only)

---

## Action 5: `search_document_content`

**Purpose**: Full-text search within document (if indexed)

**Tables Read**: `search_chunks` (RAG system)

---

# PART 3: QUERY PATTERNS

## Scenario 1: "Show me Generator #1 manual"

```sql
SELECT
    d.id,
    d.filename,
    d.doc_type,
    d.oem,
    d.system_path,
    d.storage_path,
    d.indexed
FROM doc_metadata d
WHERE :equipment_id = ANY(d.equipment_ids)
  AND d.yacht_id = public.get_user_yacht_id()
ORDER BY d.filename;
```

## Scenario 2: "Documents with tag 'safety'"

```sql
SELECT id, filename, doc_type, system_path
FROM doc_metadata
WHERE 'safety' = ANY(tags)
  AND yacht_id = public.get_user_yacht_id()
ORDER BY created_at DESC;
```

## Scenario 3: "Caterpillar documents"

```sql
SELECT id, filename, doc_type, model, system_path
FROM doc_metadata
WHERE oem ILIKE '%caterpillar%'
  AND yacht_id = public.get_user_yacht_id()
ORDER BY filename;
```

---

# PART 4: SUMMARY

## Document Lens Actions

| Action | Tables Written | RLS Tier |
|--------|---------------|----------|
| `view_document` | None (read) | All Crew |
| `add_tags` | doc_metadata, audit | All Crew |
| `link_to_equipment` | doc_metadata, audit | Engineers |
| `view_linked_equipment` | None (read) | All Crew |

## Escape Hatches

| From Document | To Lens | Trigger |
|---------------|---------|---------|
| view_linked_equipment | Equipment Lens | Click equipment |

## Key Invariants

1. **Documents are read-only** - Content uploaded externally, metadata managed here
2. **Equipment linking via array** - `equipment_ids` allows multiple associations
3. **RAG integration** - `indexed` flag tracks search availability
4. **Hierarchical organization** - `system_path` provides folder structure

---

**END OF DOCUMENT LENS v1 FINAL**
