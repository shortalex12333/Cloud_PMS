# Certificate Lens v2 - Phase 0: Extraction Gate
**Status**: EXTRACTION COMPLETE
**Date**: 2026-01-25
**Source Files Verified**: ✅

---

## PURPOSE

This phase exists to **prevent hallucination**. Before writing ANY lens content, we must read and verify all source files. This creates an evidence trail that all schema, RLS, and function information comes from actual deployed code.

---

## FILES READ (Required Before Proceeding)

### 1. Database Schema Snapshot
**File**: `/Volumes/Backup/CELESTE/database_schema.txt`
**Extracted**:
- `pms_vessel_certificates`: 14 columns
- `pms_crew_certificates`: 12 columns
- `doc_metadata`: 21 columns
- `pms_audit_log`: 11 columns

### 2. Migration Files Checked
| Migration | Contains | Status |
|-----------|----------|--------|
| `00000000000011_05_rename_auth_tables.sql` | `get_user_role()`, `is_hod()` functions | DEPLOYED |
| `20260125_006_fix_crew_certificates_rls.sql` | INSERT/UPDATE/DELETE policies for crew certs | PENDING DEPLOY |
| *(none found)* | RLS for `pms_vessel_certificates` | **MISSING - BLOCKER** |

### 3. Helper Functions Verified
| Function | Signature | Status |
|----------|-----------|--------|
| `public.get_user_yacht_id()` | `() RETURNS UUID` | ✅ DEPLOYED |
| `public.get_user_role()` | `() RETURNS TEXT` | ✅ DEPLOYED |
| `public.get_user_role(p_user_id, p_yacht_id)` | `(UUID, UUID) RETURNS TEXT` | ✅ DEPLOYED |
| `public.is_hod(p_user_id, p_yacht_id)` | `(UUID, UUID) RETURNS BOOLEAN` | ✅ DEPLOYED |

### 4. Gold Standard Reference
**File**: `fault_lens_v5_FINAL.md`
**Purpose**: Defines required depth for all lens documents

---

## EXTRACTION RESULTS

### pms_vessel_certificates (14 columns)
```
certificate_name         text         NOT NULL
certificate_number       text         nullable
certificate_type         text         NOT NULL
created_at               timestamptz  NOT NULL (default: now())
document_id              uuid         nullable (FK → doc_metadata.id)
expiry_date              date         nullable
id                       uuid         NOT NULL (PK)
issue_date               date         nullable
issuing_authority        text         NOT NULL
last_survey_date         date         nullable
next_survey_due          date         nullable
properties               jsonb        nullable
status                   text         NOT NULL
yacht_id                 uuid         NOT NULL (FK → yacht_registry.id)
```

### pms_crew_certificates (12 columns)
```
certificate_number       text         nullable
certificate_type         text         NOT NULL
created_at               timestamptz  NOT NULL (default: now())
document_id              uuid         nullable (FK → doc_metadata.id)
expiry_date              date         nullable
id                       uuid         NOT NULL (PK)
issue_date               date         nullable
issuing_authority        text         nullable
person_name              text         NOT NULL
person_node_id           uuid         nullable
properties               jsonb        nullable
yacht_id                 uuid         NOT NULL (FK → yacht_registry.id)
```

### RLS Status Summary
| Table | RLS Enabled | SELECT | INSERT | UPDATE | DELETE |
|-------|-------------|--------|--------|--------|--------|
| `pms_vessel_certificates` | UNKNOWN | ❌ NO POLICY | ❌ NO POLICY | ❌ NO POLICY | ❌ NO POLICY |
| `pms_crew_certificates` | YES | ✅ yacht scope | ✅ officers | ✅ officers | ✅ managers |
| `doc_metadata` | YES | ✅ yacht scope | ✅ yacht scope | ✅ managers | ❌ |

---

## BLOCKERS IDENTIFIED

| ID | Blocker | Severity | Affects |
|----|---------|----------|---------|
| **B1** | `pms_vessel_certificates` has NO RLS policies | CRITICAL | All vessel certificate actions |
| **B2** | Migration 20260125_006 (crew cert RLS) not yet deployed | MEDIUM | Crew certificate CREATE/UPDATE/DELETE |
| **B3** | `status` column has no CHECK constraint (enum not enforced) | LOW | Status transitions |
| **B4** | No trigger exists for automatic status updates based on `expiry_date` | LOW | Expiration handling |

---

## GATE VERIFICATION

- [x] Database schema file read
- [x] All relevant migration files checked
- [x] Helper functions verified as deployed
- [x] Gold standard reference acknowledged
- [x] Blockers documented

**GATE STATUS**: ✅ PASSED - Proceed to Phase 1

---

## NOTES FOR SUBSEQUENT PHASES

1. **All vessel certificate actions are DISABLED** until B1 is resolved
2. **Crew certificate actions** can proceed (existing SELECT policy + pending migration)
3. **Status values** must be application-enforced until B3 is addressed
4. **Expiration alerts** require manual implementation until B4 is addressed

---

**END OF PHASE 0**
