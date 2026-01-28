# 08_review_accept_signoff.md

# Review, Acceptance, and Sign-Off

This document defines how a handover draft is **reviewed, accepted, countersigned, and locked**.

This is the responsibility transfer moment.  
No automation may bypass it.

---

## Core principle

**A handover is not valid until a human accepts it.  
A handover is not complete until a second human countersigns it.**

Celeste assists.  
Humans take responsibility.

---

## Review phase (IN_REVIEW)

When a draft enters IN_REVIEW:

- The reviewer must open the draft
- All sections must be scroll-viewed
- All conflict or uncertainty flags are displayed
- All merge suggestions must be acknowledged

Edits are permitted in this phase.

No export is allowed.

---

## Acceptance phase (ACCEPTED)

Acceptance represents:

> “I confirm this handover reflects the current operational state to the best of my knowledge.”

Before acceptance:

- A mandatory banner is displayed:

  **“Celeste can make mistakes.  
  You are responsible for reviewing and confirming this handover.”**

- The reviewer must tick a confirmation checkbox
- Identity and timestamp are recorded

Upon acceptance:

- Draft content becomes frozen
- No further edits permitted
- Draft state changes to ACCEPTED

---

## Countersign phase (SIGNED)

Countersign represents:

> “I acknowledge receipt of this handover and accept operational responsibility.”

Requirements:

- Incoming responsible officer opens the accepted draft
- Must scroll all sections
- Must confirm acknowledgement
- Identity and timestamp recorded

Upon countersign:

- Draft state becomes SIGNED
- Snapshot is locked
- Hash generated for tamper detection

---

## Signature record

```

handover_signoff:
draft_id
outgoing_user_id
outgoing_signed_at
incoming_user_id
incoming_signed_at
document_hash

```

---

## Edit restrictions after acceptance

After ACCEPTED:

- No text edits permitted
- No reordering permitted
- No classification changes permitted

If an error is discovered:

- Draft must be reverted to IN_REVIEW
- Reason logged
- Both parties notified

No silent reopen.

---

## Legal and audit guarantees

Signed handovers guarantee:

- Non-repudiation
- Identity traceability
- Immutable snapshot
- Source evidence preserved

They may be presented in:

- audits
- insurance investigations
- incident inquiries
- management reviews

---

## Export gating

Only SIGNED handovers may be:

- exported as PDF
- sent via email
- stored in external document systems
- printed

No export before sign-off.

---

## Failure handling

If sign-off fails:

- Draft remains ACCEPTED
- No export possible
- System notifies responsible parties
- Previous signed handover remains authoritative

---

## Non-negotiable

- No auto-acceptance
- No auto-countersign
- No anonymous sign-off
- No export without signature
- No silent modification after signing

Responsibility transfer must be explicit, deliberate, and auditable.

---
```
