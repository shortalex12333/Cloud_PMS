# Certificate Lens v2 - Phase 1: Scope & Doctrine Lock
**Status**: SCOPE LOCKED
**Date**: 2026-01-25

---

## 1. LENS IDENTITY

| Property | Value |
|----------|-------|
| **Lens Name** | Certificate Lens |
| **Entity Type** | `certificate` (audit log entity_type) |
| **Primary Tables** | `pms_vessel_certificates`, `pms_crew_certificates` |
| **Secondary Tables** | `doc_metadata`, `pms_audit_log` |
| **Storage Bucket** | `documents` (private) |

---

## 2. SCOPE STATEMENT

This lens governs **all certificate operations** for:
1. **Vessel certificates** - Class, ISM, ISPS, Flag State, Safety Equipment, etc.
2. **Crew certificates** - STCW, ENG1/Medical, Licenses, Training Records, etc.

### In Scope
- Create certificates (vessel and crew)
- Update certificate details
- Supersede expiring certificates (with signature)
- Link documents to certificates
- View certificate details and history
- Expiration tracking and status management

### Out of Scope
- Document upload mechanics (handled by Storage layer)
- Person/crew profile management (handled by Crew Lens)
- Yacht registration (handled by Admin)
- ISM compliance audits (future: Compliance Lens)

---

## 3. DOCTRINE ADHERENCE

### 3.1 Single Search Bar UX
- User types "class certificate" → Entity extraction identifies certificate context
- User types "STCW certificates" → Shows crew certificates matching type
- User types "expiring soon" → Filters certificates by expiry_date proximity
- **NO** certificate dashboard
- **NO** global "Add Certificate" button

### 3.2 Query-Only Activation
- Actions (create, update, supersede, link) appear **ONLY** when:
  - A specific certificate is focused, OR
  - User is in certificate list context with role permissions

### 3.3 Three Permanent Elements Only
1. **Search Bar** - Entry point for all certificate queries
2. **Ledger** - Shows certificate mutations (create, update, supersede)
3. **Settings** - User preferences (not certificate config)

### 3.4 WO-First Doctrine Adaptation
- Certificates are **regulatory records**, not operational tasks
- Primary entity is **Certificate**, not Work Order
- Linked documents are metadata, not the certificate itself

---

## 4. FORBIDDEN PATTERNS

The following are **NEVER** allowed in Certificate Lens:

| Forbidden | Why |
|-----------|-----|
| "Certificates Dashboard" | Violates single search bar doctrine |
| "Add New Certificate" button (always visible) | Actions appear only on focused entity |
| "Navigate to Certificates" | Cross-lens uses escape hatch pattern |
| Auto-inference of certificate type | User must explicitly specify |
| Silent status changes | All mutations require audit log entry |
| Unsigned supersession | Supersede action requires signature |

---

## 5. ENTITY TYPES

### 5.1 Vessel Certificates
**Definition**: Documents certifying vessel compliance with maritime regulations.

**Examples**:
- Class Certificate (Lloyds, DNV, ABS, etc.)
- ISM DOC (Document of Compliance)
- ISPS Certificate
- Safety Equipment Certificate
- Load Line Certificate
- MARPOL Certificate
- Radio License
- Flag State Registration

**Lifecycle**: `valid` → `due_soon` (30 days before expiry) → `expired` → `superseded`

### 5.2 Crew Certificates
**Definition**: Documents certifying individual crew member qualifications.

**Examples**:
- STCW (various grades)
- ENG1 / Medical Certificate
- GMDSS Radio Operator Certificate
- Yacht Rating / Officer of the Watch
- Engineer Certificates (MCA, USCG, etc.)
- Flag State Endorsements
- Training Certificates (firefighting, survival, etc.)

**Lifecycle**: `valid` → `due_soon` (30 days before expiry) → `expired`

---

## 6. ROLE PERMISSIONS SUMMARY

| Role | Can View | Can Create | Can Update | Can Supersede | Can Delete |
|------|----------|------------|------------|---------------|------------|
| Deckhand | ✅ | ❌ | ❌ | ❌ | ❌ |
| Steward | ✅ | ❌ | ❌ | ❌ | ❌ |
| Engineer | ✅ | ❌ | ❌ | ❌ | ❌ |
| Chief Engineer | ✅ | ✅ | ✅ | ✅ (signed) | ❌ |
| Purser | ✅ | ✅ | ✅ | ❌ | ❌ |
| Captain | ✅ | ✅ | ✅ | ✅ (signed) | ✅ |
| Manager | ✅ | ✅ | ✅ | ✅ (signed) | ✅ |

---

## 7. SIGNATURE REQUIREMENTS

| Action | Signature Required | Rationale |
|--------|-------------------|-----------|
| `create_certificate` | NO | Creation is a data entry, not a legal act |
| `update_certificate` | NO | Corrections are administrative |
| `supersede_certificate` | **YES** | Legal act - marks old as superseded, creates new |
| `link_document` | NO | Attaching evidence, not modifying certificate |
| `delete_certificate` | **YES** | Permanent removal requires accountability |

---

## 8. AUDIT REQUIREMENTS

### 8.1 Entity Type Convention
```sql
entity_type = 'certificate'
```
Used for ALL certificate operations (vessel and crew).

### 8.2 Signature Invariant
```sql
signature = '{}'::jsonb     -- Non-signature action
signature = :payload::jsonb  -- Signed action (supersede, delete)
```
**NEVER** `NULL` - the column is `NOT NULL`.

### 8.3 Required Audit Fields
```sql
INSERT INTO pms_audit_log (
    id,           -- gen_random_uuid()
    yacht_id,     -- public.get_user_yacht_id()
    entity_type,  -- 'certificate'
    entity_id,    -- certificate.id
    action,       -- 'create_certificate', 'update_certificate', etc.
    user_id,      -- auth.uid()
    old_values,   -- NULL for create, jsonb for update
    new_values,   -- jsonb of new state
    signature,    -- '{}' or signed payload
    metadata,     -- additional context
    created_at    -- now()
)
```

---

## 9. ESCAPE HATCHES

| From Certificate | To Lens | Trigger | Query |
|------------------|---------|---------|-------|
| View linked document | Document Lens | Click `document_id` | `SELECT * FROM doc_metadata WHERE id = :doc_id` |
| View crew member | Crew Lens | Click `person_node_id` | (Future: person lookup) |
| View related equipment | Equipment Lens | Click equipment tag | (If certificates link to equipment) |

---

## 10. STATUS LIFECYCLE

```
                    ┌─────────────────────┐
                    │      valid          │
                    │  (expiry_date > 30d)│
                    └─────────┬───────────┘
                              │ expiry_date approaches
                              ▼
                    ┌─────────────────────┐
                    │     due_soon        │
                    │ (expiry_date <= 30d)│
                    └─────────┬───────────┘
                              │ expiry_date passed
                              ▼
                    ┌─────────────────────┐
                    │      expired        │
                    │  (expiry_date < now)│
                    └─────────────────────┘
                              │ supersede action (signed)
                              ▼
                    ┌─────────────────────┐
                    │    superseded       │
                    │ (new cert replaces) │
                    └─────────────────────┘
```

---

## 11. BLOCKERS CARRIED FORWARD

| ID | Blocker | Impact on Scope |
|----|---------|-----------------|
| **B1** | `pms_vessel_certificates` has no RLS | All vessel cert actions DISABLED |
| **B2** | Crew cert migration pending | Crew CREATE/UPDATE at risk until deployed |
| **B3** | No status CHECK constraint | Status values not DB-enforced |
| **B4** | No expiration trigger | Status transitions must be manual/scheduled |

---

## 12. SCOPE LOCK CONFIRMATION

- [x] Entity types defined
- [x] Doctrine adherence verified
- [x] Forbidden patterns documented
- [x] Role permissions mapped
- [x] Signature requirements specified
- [x] Audit requirements defined
- [x] Escape hatches identified
- [x] Blockers acknowledged

**SCOPE STATUS**: ✅ LOCKED - Proceed to Phase 2

---

**END OF PHASE 1**
