# DB CONTRACT — SCHEMA, RLS, AND CONSTRAINTS

> **This file defines database contracts. Changes require verification.**
>
> Last Updated: 2026-02-17
> Updated By: Claude Opus 4.5

---

## Core Tables (Receiving Domain)

| Table | Purpose |
|-------|---------|
| `pms_receiving` | Main receiving records |
| `pms_receiving_items` | Line items |
| `pms_receiving_documents` | Attached documents |
| `pms_receiving_extractions` | OCR extraction payloads |
| `pms_image_uploads` | Uploaded images with OCR results |
| `pms_audit_log` | Audit trail |

---

## Required Columns (pms_receiving_extractions)

| Column | Type | Constraint |
|--------|------|------------|
| `id` | UUID | PK |
| `yacht_id` | UUID | FK |
| `receiving_id` | UUID | FK, nullable |
| `source_document_id` | UUID | FK |
| `payload` | JSONB | includes `extraction_confidence` inside payload |
| `created_at` | timestamp | |

**Note**: No separate `confidence` or `status` columns — confidence goes inside `payload.extraction_confidence`

---

## RLS Policies (pms_receiving table)

| Policy Name | Command | Check |
|-------------|---------|-------|
| `receiving_insert_hod` | INSERT | `is_hod(auth.uid(), yacht_id)` |
| `receiving_update_hod` | UPDATE | `is_hod(auth.uid(), yacht_id)` |
| `receiving_select_yacht` | SELECT | `yacht_id = get_user_yacht_id()` |
| `receiving_service_role` | ALL | service_role bypass |

**Note**: Backend uses service_role key, bypassing RLS. Action registry is the source of truth for API permissions.

---

## Role Permissions (CANONICAL)

### `is_hod()` Function Returns TRUE For:

```sql
'chief_engineer', 'chief_officer', 'captain', 'purser', 'manager'
```

### Action Permissions (registry.py is source of truth)

| Action | Allowed Roles | Signature Required |
|--------|---------------|-------------------|
| `create_receiving` | ALL crew | No |
| `add_receiving_item` | Receiver (owner) or HOD+ | No |
| `update_receiving_fields` | Receiver (owner) or HOD+ | No |
| `accept_receiving` | chief_engineer, chief_officer, purser, captain, manager | Yes |
| `reject_receiving` | HOD+ | No |
| `view_receiving_history` | All crew | No |

### ALL crew roles:
```
crew, deckhand, steward, chef, bosun, engineer, eto,
chief_engineer, chief_officer, chief_steward, purser, captain, manager
```

---

## RLS Verification Rules

After each mutation:
1. Verify yacht_id isolation is maintained
2. Check service_role bypass is only used by backend
3. Run RLS test suite

---

## OCR Pipeline Locks

| Setting | Value |
|---------|-------|
| Service port | 8001 (Docker) |
| Engine | Tesseract (ENABLE_TESSERACT=true) |
| Storage bucket | `pms-receiving-images` |
| Processing | Synchronous (OCR before API response) |
| Tables written | `pms_image_uploads`, `pms_receiving_extractions` |

---

## Test Users (Staging)

| Role | Email | Password |
|------|-------|----------|
| Captain | captain.test@alex-short.com | Password2! |
| Chief Engineer (HOD) | x@alex-short.com | Password2! |
| HOD | hod.test@alex-short.com | Password2! |
| Crew | crew.test@alex-short.com | Password2! |

**Test Yacht ID**: `85fe1119-b04c-41ac-80f1-829d23322598`

**Note**: Only `x@alex-short.com` and `captain.tenant@alex-short.com` exist in Supabase auth.

---

## Verification Commands

```bash
# Check RLS policies
supabase db diff --schema public

# List policies on receiving table
psql -c "SELECT policyname, cmd FROM pg_policies WHERE tablename = 'pms_receiving';"

# Test yacht isolation
psql -c "SELECT yacht_id, COUNT(*) FROM pms_receiving GROUP BY yacht_id;"
```
