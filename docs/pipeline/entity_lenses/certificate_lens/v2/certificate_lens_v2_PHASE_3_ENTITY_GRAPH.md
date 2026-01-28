# Certificate Lens v2 - Phase 3: Entity & Relationship Model
**Status**: GRAPH COMPLETE
**Date**: 2026-01-25

---

## PURPOSE

This phase maps all **FK-based relationships** for certificate entities. Only actual foreign key paths are documented. No inferred or vector-similarity joins.

---

# ENTITY RELATIONSHIP DIAGRAM

```
                                 ┌───────────────────────┐
                                 │    yacht_registry     │
                                 │         (id)          │
                                 └───────────┬───────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
        ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────┐
        │ pms_vessel_certificates│ │ pms_crew_certificates │ │    doc_metadata   │
        │         (id)          │ │         (id)          │ │        (id)       │
        │                       │ │                       │ │                   │
        │  yacht_id ────────────│ │  yacht_id ────────────│ │  yacht_id ────────│
        │  document_id ─────────┼─┼──document_id ─────────┼─┼──────────────────►│
        │                       │ │  person_node_id ──────┼─┼──► (person entity) │
        └───────────────────────┘ └───────────────────────┘ └───────────────────┘
                    │                        │
                    │                        │
                    ▼                        ▼
        ┌───────────────────────────────────────────────────┐
        │                  pms_audit_log                    │
        │                     (id)                          │
        │                                                   │
        │  entity_type = 'certificate'                      │
        │  entity_id → certificate.id                       │
        │  yacht_id → yacht_registry.id                     │
        │  user_id → auth.users.id                          │
        └───────────────────────────────────────────────────┘
```

---

# OUTBOUND FOREIGN KEYS

## From `pms_vessel_certificates`

| FK Column | References | Cardinality | On Delete | Notes |
|-----------|------------|-------------|-----------|-------|
| `yacht_id` | `yacht_registry(id)` | N:1 | RESTRICT | Required yacht isolation |
| `document_id` | `doc_metadata(id)` | N:1 | SET NULL | Optional document link |

## From `pms_crew_certificates`

| FK Column | References | Cardinality | On Delete | Notes |
|-----------|------------|-------------|-----------|-------|
| `yacht_id` | `yacht_registry(id)` | N:1 | RESTRICT | Required yacht isolation |
| `document_id` | `doc_metadata(id)` | N:1 | SET NULL | Optional document link |
| `person_node_id` | *(unverified)* | N:1 | *(unknown)* | Optional person entity link |

---

# INBOUND FOREIGN KEYS

## To `pms_vessel_certificates`

| From Table | FK Column | Cardinality | Notes |
|------------|-----------|-------------|-------|
| `pms_audit_log` | `entity_id` (logical) | 1:N | Audit trail (entity_type='certificate') |

## To `pms_crew_certificates`

| From Table | FK Column | Cardinality | Notes |
|------------|-----------|-------------|-------|
| `pms_audit_log` | `entity_id` (logical) | 1:N | Audit trail (entity_type='certificate') |

---

# RELATIONSHIP PATH MATRIX

## Vessel Certificate Traversals

| From | To | Path | Query Pattern |
|------|-----|------|---------------|
| Vessel Cert | Yacht | Direct FK | `yacht_id` |
| Vessel Cert | Document | Direct FK | `document_id → doc_metadata.id` |
| Vessel Cert | Audit Log | Logical | `entity_type='certificate' AND entity_id=cert.id` |
| Vessel Cert | User (creator) | Via Audit | `audit_log WHERE action='create_certificate'` |

## Crew Certificate Traversals

| From | To | Path | Query Pattern |
|------|-----|------|---------------|
| Crew Cert | Yacht | Direct FK | `yacht_id` |
| Crew Cert | Document | Direct FK | `document_id → doc_metadata.id` |
| Crew Cert | Person | Direct FK | `person_node_id` (if exists) |
| Crew Cert | Audit Log | Logical | `entity_type='certificate' AND entity_id=cert.id` |

---

# ESCAPE HATCH QUERIES

## Certificate → Document (Direct FK)

```sql
-- When user wants to view linked document
SELECT
    d.id,
    d.filename,
    d.content_type,
    d.storage_path,
    d.created_at
FROM doc_metadata d
WHERE d.id = :document_id
  AND d.yacht_id = public.get_user_yacht_id();
```

**Transition**: Focus shifts from Certificate Lens to Document Lens.

## Certificate → Audit History (Logical Join)

```sql
-- View certificate's full history
SELECT
    a.action,
    a.old_values,
    a.new_values,
    a.signature,
    a.created_at,
    (SELECT name FROM auth_users_profiles WHERE id = a.user_id) AS user_name
FROM pms_audit_log a
WHERE a.entity_type = 'certificate'
  AND a.entity_id = :certificate_id
  AND a.yacht_id = public.get_user_yacht_id()
ORDER BY a.created_at DESC;
```

## Certificate → Superseding Certificate (Self-Reference)

```sql
-- Find certificate that superseded this one
SELECT
    c.id,
    c.certificate_name,
    c.certificate_number,
    c.status,
    c.created_at
FROM pms_vessel_certificates c
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.certificate_type = :certificate_type
  AND c.certificate_number = :certificate_number
  AND c.status = 'valid'
  AND c.id != :old_certificate_id
ORDER BY c.created_at DESC
LIMIT 1;
```

---

# DENORMALIZATION PATTERNS

## `yacht_id` on Every Table
- Both certificate tables have `yacht_id`
- `doc_metadata` has `yacht_id`
- `pms_audit_log` has `yacht_id`

**Rationale**: Enables direct RLS enforcement without joins.

## No `updated_at` on Certificate Tables
- Vessel certificates: **NO `updated_at` column** (verified from schema)
- Crew certificates: **NO `updated_at` column** (verified from schema)

**Impact**: Cannot easily sort by "last modified" - must use audit log or add column.

---

# FORBIDDEN TRAVERSALS

| From | To | Why Forbidden |
|------|-----|---------------|
| Certificate | Work Order | No FK exists (would be inferred/fabricated) |
| Certificate | Equipment | No FK exists (would be inferred/fabricated) |
| Certificate | Other Yacht's Certs | RLS prevents; no cross-yacht FK |
| Crew Cert | Vessel Cert | No FK relationship |

---

# GRAPH INVARIANTS

1. **Yacht Isolation**: All paths must terminate within same `yacht_id`
2. **FK-Only Traversals**: No vector similarity or text-matching joins in lens queries
3. **Audit Always Available**: Every certificate has audit trail via logical join
4. **Document Optional**: `document_id` may be NULL (certificate without attached doc)
5. **Person Optional**: `person_node_id` may be NULL (crew cert without person entity)

---

# JOIN PATTERNS BY ACTION

## `create_certificate`
```
pms_vessel_certificates ──INSERT──> new row
         └──────────────────────────> pms_audit_log (INSERT)
```

## `update_certificate`
```
pms_vessel_certificates ──UPDATE──> existing row
         └──────────────────────────> pms_audit_log (INSERT)
```

## `supersede_certificate`
```
pms_vessel_certificates ──UPDATE──> old row (status='superseded')
pms_vessel_certificates ──INSERT──> new row (status='valid')
         └──────────────────────────> pms_audit_log (INSERT for each)
```

## `link_document`
```
doc_metadata ─────────────SELECT───> verify exists
pms_vessel_certificates ──UPDATE──> set document_id
         └──────────────────────────> pms_audit_log (INSERT)
```

---

# INDEXES FOR RELATIONSHIP QUERIES

## Recommended (if not exist)

```sql
-- Yacht isolation (critical for RLS performance)
CREATE INDEX IF NOT EXISTS idx_vessel_certs_yacht
ON pms_vessel_certificates(yacht_id);

CREATE INDEX IF NOT EXISTS idx_crew_certs_yacht
ON pms_crew_certificates(yacht_id);

-- Expiration queries
CREATE INDEX IF NOT EXISTS idx_vessel_certs_expiry
ON pms_vessel_certificates(yacht_id, expiry_date);

CREATE INDEX IF NOT EXISTS idx_crew_certs_expiry
ON pms_crew_certificates(yacht_id, expiry_date);

-- Document lookups
CREATE INDEX IF NOT EXISTS idx_vessel_certs_doc
ON pms_vessel_certificates(document_id) WHERE document_id IS NOT NULL;

-- Audit log entity lookups
CREATE INDEX IF NOT EXISTS idx_audit_certificate
ON pms_audit_log(entity_id, entity_type) WHERE entity_type = 'certificate';

-- Person lookups for crew
CREATE INDEX IF NOT EXISTS idx_crew_certs_person
ON pms_crew_certificates(person_node_id) WHERE person_node_id IS NOT NULL;
```

---

# BLOCKERS AFFECTING GRAPH

| ID | Impact on Relationships |
|----|------------------------|
| **B1** | No RLS = cannot safely traverse to vessel certificates |
| **B2** | Cannot create/update crew cert rows to test traversals |

---

**ENTITY GRAPH STATUS**: ✅ COMPLETE - Proceed to Phase 4

---

**END OF PHASE 3**
