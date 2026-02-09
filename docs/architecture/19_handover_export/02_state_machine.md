# State Machine

## Draft Lifecycle and Transitions

This document defines the handover draft state machine and transition rules.

---

## State Diagram

```
                    ┌─────────────────┐
                    │   User adds     │
                    │   handover      │
                    │   items         │
                    └────────┬────────┘
                             │
                             ▼
          ┌──────────────────────────────────┐
          │             DRAFT                 │
          │                                   │
          │  • Items can be added/removed    │
          │  • Regeneration allowed          │
          │  • Not visible externally        │
          │  • Editable freely               │
          └────────────────┬─────────────────┘
                           │
                           │ POST /draft/{id}/review
                           │ (user opens for review)
                           ▼
          ┌──────────────────────────────────┐
          │           IN_REVIEW               │
          │                                   │
          │  • Edits allowed                 │
          │  • Merges allowed                │
          │  • Reordering allowed            │
          │  • No external export            │
          │  • Edit history tracked          │
          └────────────────┬─────────────────┘
                           │
                           │ POST /draft/{id}/accept
                           │ (outgoing officer confirms)
                           │
                           │ Requirements:
                           │  • confirmation_flag = true
                           │  • user scrolled all sections
                           ▼
          ┌──────────────────────────────────┐
          │           ACCEPTED                │
          │                                   │
          │  • Content frozen                │
          │  • Outgoing user recorded        │
          │  • Waiting for countersign       │
          │  • No edits allowed              │
          └────────────────┬─────────────────┘
                           │
                           │ POST /draft/{id}/sign
                           │ (incoming officer countersigns)
                           │
                           │ Requirements:
                           │  • confirmation_flag = true
                           │  • different user from outgoing
                           ▼
          ┌──────────────────────────────────┐
          │            SIGNED                 │
          │                                   │
          │  • Both signatories recorded     │
          │  • Document hash locked          │
          │  • Snapshot immutable            │
          │  • Export now permitted          │
          └────────────────┬─────────────────┘
                           │
                           │ POST /draft/{id}/export
                           │ (generate PDF/HTML/Email)
                           ▼
          ┌──────────────────────────────────┐
          │           EXPORTED                │
          │                                   │
          │  • Export record created         │
          │  • File stored permanently       │
          │  • Email sent (if requested)     │
          │  • Fully archived                │
          └──────────────────────────────────┘
```

---

## State Definitions

### DRAFT

**Entry condition:** New draft created from handover items

**Allowed operations:**
- Add items to draft
- Remove items from draft
- Regenerate draft (re-pull from source items)
- Edit item text
- Merge items
- Reorder items
- Change bucket assignments

**Exit condition:** User initiates review

**Failure behavior:** Draft persists, no data loss

---

### IN_REVIEW

**Entry condition:** User explicitly opens draft for handover preparation

**Allowed operations:**
- Edit item summary text
- Merge items (with confirmation)
- Split items
- Reorder items within section
- Add annotations

**Not allowed:**
- Delete source references
- Change domain classification
- Change bucket assignment

**Exit condition:** Outgoing officer accepts

**Failure behavior:** Returns to DRAFT if review abandoned

---

### ACCEPTED

**Entry condition:** Outgoing officer confirms accuracy

**Required inputs:**
- `confirmation_flag: true`
- User identity verified
- All sections viewed

**Allowed operations:**
- None (content frozen)

**Records:**
- `outgoing_user_id`
- `outgoing_signed_at`

**Exit condition:** Incoming officer countersigns

**Warning displayed:**
> "Celeste can make mistakes. You are responsible for reviewing and confirming this handover."

---

### SIGNED

**Entry condition:** Incoming officer countersigns

**Required inputs:**
- `confirmation_flag: true`
- User identity verified
- Different user from outgoing

**Records:**
- `incoming_user_id`
- `incoming_signed_at`
- `document_hash` (SHA-256 of content)

**Allowed operations:**
- Export (PDF/HTML/Email)

**Exit condition:** Export requested

---

### EXPORTED

**Entry condition:** Export successfully generated

**Records:**
- `export_type` (pdf/html/email)
- `storage_path`
- `document_hash`
- `exported_by_user_id`
- `recipients[]` (if email)

**Allowed operations:**
- Re-export (new export record created)
- Download existing exports

**Terminal state:** No further transitions

---

## Transition Matrix

| Current State | Action | Next State | Requirements |
|--------------|--------|------------|--------------|
| DRAFT | `/review` | IN_REVIEW | User authenticated |
| IN_REVIEW | `/accept` | ACCEPTED | confirmation_flag, sections_viewed |
| IN_REVIEW | `/abandon` | DRAFT | None |
| ACCEPTED | `/sign` | SIGNED | confirmation_flag, different_user |
| ACCEPTED | `/reject` | IN_REVIEW | Reason provided |
| SIGNED | `/export` | EXPORTED | export_type specified |
| EXPORTED | `/export` | EXPORTED | Creates new export record |

---

## Invalid Transitions (HTTP 409)

The following transitions must be rejected:

| Attempted | Error Message |
|-----------|--------------|
| DRAFT → ACCEPTED | "Cannot accept draft without review" |
| DRAFT → SIGNED | "Cannot sign draft without acceptance" |
| DRAFT → EXPORTED | "Cannot export unsigned draft" |
| IN_REVIEW → SIGNED | "Cannot sign without acceptance" |
| IN_REVIEW → EXPORTED | "Cannot export unaccepted draft" |
| ACCEPTED → EXPORTED | "Cannot export without signature" |
| EXPORTED → DRAFT | "Cannot modify exported handover" |
| EXPORTED → IN_REVIEW | "Cannot modify exported handover" |

---

## Rollback Rules

### Review Abandonment

If user abandons review (closes without accepting):
- State returns to DRAFT
- Edits made during review are **preserved**
- Edit history remains in `handover_draft_edits`
- No data loss

### Acceptance Rejection

If incoming officer rejects acceptance:
- State returns to IN_REVIEW
- Rejection reason recorded
- Outgoing officer notified
- Outgoing officer may edit and re-accept

### Export Failure

If export generation fails:
- State remains SIGNED
- No partial export released
- Error logged
- Retry permitted

---

## Concurrency Rules

1. **One active draft per shift:** Only one DRAFT or IN_REVIEW per yacht + shift_date + department
2. **No concurrent edits:** Only one user may have draft in IN_REVIEW at a time
3. **Sequential sign-off:** Outgoing must accept before incoming can sign
4. **Export queuing:** Multiple exports may be queued, processed sequentially

---

## Audit Trail

Every state transition records:

```json
{
  "draft_id": "uuid",
  "from_state": "DRAFT",
  "to_state": "IN_REVIEW",
  "triggered_by_user_id": "uuid",
  "triggered_at": "2026-02-03T10:30:00Z",
  "reason": null,
  "metadata": {}
}
```

Stored in `pms_audit_log` with `entity_type: 'handover_draft'`.

---

## Timeout Rules

| State | Timeout | Action |
|-------|---------|--------|
| DRAFT | 7 days | Auto-archive (soft delete) |
| IN_REVIEW | 24 hours | Warning notification |
| ACCEPTED | 48 hours | Warning notification |
| SIGNED | None | Persists indefinitely |
| EXPORTED | None | Persists indefinitely |

---
