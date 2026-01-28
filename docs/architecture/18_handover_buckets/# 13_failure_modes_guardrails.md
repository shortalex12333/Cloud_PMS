# 13_failure_modes_guardrails.md

# Failure Modes and Guardrails

This document defines **system behaviors that must be prevented** in Celeste’s handover pipeline.

These are known failure patterns from legacy yacht software and email-based handovers.

If any of these occur, the system is considered in breach of design.

---

## Core rule

**If the system is uncertain, it must slow down — not guess.**

Automation convenience must never override operational truth.

---

## Forbidden failure modes

### 1) Silent handover creation

Failure:
- System generates handover entries without user awareness

Guardrail:
- All entries require explicit user acceptance
- Proposed additions must be visible and dismissible

---

### 2) Silent handover modification

Failure:
- AI rewrites narrative or merges entries without approval

Guardrail:
- All merges and rewrites require confirmation
- Original text always preserved

---

### 3) Silent publishing

Failure:
- Handover exported or emailed automatically

Guardrail:
- Export only possible after dual sign-off
- No background sending

---

### 4) Taxonomy drift

Failure:
- New categories appear ad-hoc
- “Miscellaneous” or “General” buckets emerge

Guardrail:
- Only predefined buckets allowed
- Domain list version-controlled
- Classification change requests logged

---

### 5) Duplicate or conflicting truths

Failure:
- Same issue appears multiple times
- Conflicting summaries exist

Guardrail:
- Duplicate detection proposes merge
- Conflict flagged until resolved
- No silent deduplication

---

### 6) Loss of source evidence

Failure:
- Summary exists without reference
- Source documents overwritten

Guardrail:
- Referential integrity enforced
- No deletion of source references

---

### 7) Planning inside handover

Failure:
- Tasks, owners, deadlines inserted
- Progress states added

Guardrail:
- UI rejects task-like fields
- Language patterns detecting planning blocked

---

### 8) Hidden uncertainty

Failure:
- Conflicting evidence collapsed into false certainty

Guardrail:
- Uncertainty flag required
- Confidence level must drop
- Conflict banner displayed

---

### 9) Untraceable edits

Failure:
- Narrative rewritten without audit trail

Guardrail:
- Edit history table mandatory
- Original text immutable

---

### 10) Orphaned drafts

Failure:
- Draft accepted but not signed
- Signed but not exported
- Export with no sign-off

Guardrail:
- State machine enforcement
- Invalid transitions rejected

---

### 11) Role-based content hiding

Failure:
- Certain roles cannot see certain handover content

Guardrail:
- Biasing only affects ordering
- No content hidden by role

---

### 12) External dependency failure

Failure:
- Email or PDF generation fails
- Resulting handover lost

Guardrail:
- Signed snapshot remains authoritative
- Export retriable
- No data loss

---

## System-safe defaults

If any step fails:

- Draft remains in previous valid state
- No new handover published
- Users notified
- Logs written

No silent fallback.

---

## Operational consequences

If guardrails are bypassed:

- Crew lose trust
- Legal liability increases
- Audit readiness collapses
- System adoption fails

These guardrails are not optional.

---

## Non-negotiable

- No silent automation
- No hidden edits
- No hidden uncertainty
- No auto-planning
- No category sprawl
- No trace loss

If a developer requests bypass,  
the request must be rejected.

---
```
