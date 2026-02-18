---
phase: 14-handover-export-editable
plan: "02"
subsystem: database
tags: [postgres, supabase, migration, handover, signatures, jsonb]

# Dependency graph
requires:
  - phase: 07-handover
    provides: handover_exports table baseline schema
provides:
  - handover_exports table with two-bucket storage URL columns
  - user_signature + hod_signature JSONB fields for dual signatures
  - review_status column with CHECK constraint (pending_review/pending_hod_signature/complete)
  - idx_handover_exports_pending_hod partial index for HOD queue
  - edited_content JSONB for section-level edit tracking
affects:
  - 14-03 (API endpoints will query new columns)
  - 14-04 (frontend editor will read/write edited_content)
  - 14-05 (signature capture will write user_signature/hod_signature)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Idempotent migrations using IF NOT EXISTS / DO $$ guard pattern
    - Two-bucket storage pattern: original_storage_url (AI) + signed_storage_url (user-edited)
    - JSONB for structured signature data (image_base64, signed_at, signer_name, signer_id)
    - Partial index on review_status WHERE clause for HOD queue efficiency

key-files:
  created:
    - apps/api/migrations/20260218_handover_export_editable.sql
  modified: []

key-decisions:
  - "review_status uses CHECK constraint with 3 values: pending_review, pending_hod_signature, complete"
  - "Dual signature stored as JSONB objects (not separate columns) to preserve full signature metadata"
  - "Partial index WHERE review_status = 'pending_hod_signature' optimises HOD countersign queue"
  - "user_submitted_at separate from user_signed_at to distinguish signing from submission"

patterns-established:
  - "Idempotent SQL: all ALTER TABLE use IF NOT EXISTS, constraint uses DO $$ guard"
  - "JSONB signature shape: {image_base64, signed_at, signer_name, signer_id} + {role} for HOD"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-02-18
---

# Phase 14 Plan 02: Database Schema Updates Summary

**handover_exports table extended with two-bucket storage URLs, JSONB dual-signature fields, and review_status workflow column applied to live Supabase database**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-18T16:14:59Z
- **Completed:** 2026-02-18T16:17:13Z
- **Tasks:** 2 of 2
- **Files modified:** 1

## Accomplishments

- Created idempotent migration file adding 9 columns to handover_exports
- Applied migration to live Supabase tenant database (vzsohavtuotocgrfkfyd), confirmed via psql query
- Verified all columns, CHECK constraint, and partial index active on live schema

## Task Commits

Each task was committed atomically:

1. **Task 1: Create migration file** - `31c30ae7` (chore)
2. **Task 2: Apply migration via Supabase** - no separate file commit (DB execution step; migration file committed in Task 1)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `apps/api/migrations/20260218_handover_export_editable.sql` - SQL migration adding 9 columns, 1 CHECK constraint, 1 partial index, 6 column comments to handover_exports table

## Decisions Made

- Applied migration via direct psql connection to `db.vzsohavtuotocgrfkfyd.supabase.co` (local Supabase container not running; CLI `supabase db push` unavailable without local instance)
- review_status DEFAULT 'pending_review' so existing rows are handled automatically on schema update
- Partial index scoped to `pending_hod_signature` only — the hot query path for HOD dashboards

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Supabase pooler connection URL failed (password contains `@` character); resolved by using separate psql `-h/-U/-d` params with PGPASSWORD env var against direct DB host.
- Local Supabase container not running; applied directly to remote DB host `db.vzsohavtuotocgrfkfyd.supabase.co:5432`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Schema changes are live on the tenant database
- handover_exports table ready for 14-03 API endpoint work (read/write new columns)
- Review status workflow states defined: pending_review → pending_hod_signature → complete

---
*Phase: 14-handover-export-editable*
*Completed: 2026-02-18*

## Self-Check: PASSED

- FOUND: `apps/api/migrations/20260218_handover_export_editable.sql`
- FOUND: `.planning/phases/14-handover-export-editable/14-02-SUMMARY.md`
- FOUND: commit `31c30ae7` (chore(14-02): create handover_exports editable columns migration)
