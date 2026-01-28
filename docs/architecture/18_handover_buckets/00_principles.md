00_principles.md



---

# Handover Principles

This document defines the non-negotiable principles governing handover in Celeste.

If implementation conflicts with these principles,  
implementation must change — not the principles.

---

## 1. Handover is continuity, not planning

Handover answers one question:

**“What state is the vessel in right now, and why?”**

Handover does **not**:

- assign future work
- track progress
- schedule tasks
- measure performance
- define ownership of completion

If a user attempts to plan work inside handover, the design has failed.

---

## 2. Ledger and handover are separate

**Ledger**
- Immutable
- Event-based
- Records what happened
- Never edited or summarised

**Handover**
- Narrative
- Editable
- Summarises what matters
- Always traceable to ledger events

Ledger is truth storage.  
Handover is truth communication.

Neither replaces the other.

---

## 3. Nothing enters handover silently

Handover content may originate from:

- user search interactions
- ledger mutation events
- explicit manual additions

In all cases:

**Celeste may suggest.  
Humans must accept.**

No automatic insertion.
No invisible aggregation.

---

## 4. Nothing leaves handover silently

Removal of content requires:

- explicit user action
- preserved attribution
- retained source linkage

Resolved items may be marked as resolved,  
but never deleted from history.

---

## 5. Handover is a living draft until signed

Handover states:

- Draft
- In Review
- Accepted
- Signed
- Exported

No export, email, or print occurs  
before Accepted state is reached.

---

## 6. Humans own the final wording

Users may:

- rephrase
- reorder
- merge
- split
- annotate

Edits must:

- preserve source references
- preserve original author attribution
- remain auditable

Celeste assists wording.  
Celeste does not overwrite human judgment.

---

## 7. Buckets serve relevance, not bureaucracy

Classification exists to:

- improve retrieval
- drive relevance ranking
- structure handover presentation

Classification must never:

- require users to learn taxonomy
- force users to choose categories
- block recording of real-world anomalies

If taxonomy conflicts with reality, taxonomy adapts.

---

## 8. Overlap is allowed

A single operational issue may:

- belong to multiple system domains
- concern multiple departments
- affect multiple risk postures

The system must support overlap  
without duplication or confusion.

---

## 9. Uncertainty is surfaced, not hidden

When evidence conflicts or is incomplete:

- Celeste highlights uncertainty
- does not fabricate certainty
- does not collapse conflicting records

Trust is built by admitting ambiguity.

---

## 10. Sign-off is responsibility transfer

Sign-off means:

“I have reviewed this handover.  
I accept responsibility for the stated vessel context.”

Therefore:

- identity is recorded
- timestamp is immutable
- snapshot is preserved

No anonymous or auto sign-off is permitted.

---

## 11. Handover must survive system absence

Exports must be:

- human readable outside Celeste
- traceable to source events
- usable during connectivity loss

Celeste accelerates handover.  
Celeste is not required for handover to exist.

---

## 12. Failure states must be safe

If automation fails:

- no data is lost
- no silent publication occurs
- default state is draft

Safety beats convenience.

---

## 13. The design target

A new crew member opening handover should:

- understand vessel state in minutes
- see unresolved risks clearly
- know where uncertainty exists
- trust that nothing important is hidden

If they need oral folklore to understand context,  
handover has failed.

---
```
