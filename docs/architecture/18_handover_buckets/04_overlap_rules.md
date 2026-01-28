# Overlap Rules

This document defines how Celeste handles **overlapping domains, roles, and departmental relevance** inside handover entries.

Overlap is expected.  
Overlap is necessary.  
Uncontrolled overlap destroys trust.

These rules ensure overlap remains structured, auditable, and predictable.

---

## 1. Overlap is allowed at the domain level

A single operational issue may involve:

- multiple physical systems
- multiple disciplines
- multiple departments

Example:
A passerelle fault caused by a touch-panel controller failure.

This touches:

- Deck Machinery  
- AV & Guest Control  
- Monitoring & Alarm Routing

Celeste must support this overlap without creating multiple handover entries.

---

## 2. Every entry has exactly one primary domain

Primary domain represents:

**“What system is actually affected.”**

This determines:

- presentation bucket
- default department section
- primary ownership

Primary domain must always be set.

---

## 3. Secondary domains are optional

Secondary domains represent:

**“Which other disciplines are implicated.”**

They influence:

- relevance ranking
- role bias
- cross-department visibility

They do not create additional document sections.

---

## 4. No duplicate entries across buckets

Even if an issue touches multiple domains:

- it appears only once in the handover document
- it appears in the bucket of its primary domain
- secondary relevance is handled invisibly

This prevents:

- repeated content
- confusion
- conflicting edits

---

## 5. Role overlap is inferred, not assigned

Roles do not choose buckets.

Roles are inferred from:

- primary domain ownership map
- secondary domain overlap
- risk tags

Users never manually assign roles to handover entries.

This avoids misclassification under pressure.

---

## 6. Risk posture does not change bucket placement

Risk tags influence:

- ordering
- emphasis
- command synthesis

They never move an entry to another bucket.

Example:
A safety-critical deck issue remains in Deck bucket,  
but is promoted into Command risk synthesis.

---

## 7. Command synthesis is derivative

Command bucket entries:

- are generated from underlying entries
- always reference source entries
- never exist independently
- never accept manual edits directly

This prevents divergence between summary and truth.

---

## 8. Manual edits do not change classification

Users may:

- rewrite narrative
- clarify context
- reorder content

Users may not:

- change primary domain
- change bucket
- delete secondary domains

Classification remains stable and auditable.

If classification is wrong, a correction request is logged, not silently changed.

---

## 9. Conflict handling

If two users add overlapping entries describing the same issue:

- AI merge pipeline proposes merge
- both source references remain
- user must accept merge
- no silent deduplication occurs

Conflict resolution is human-approved.

---

## 10. Why this matters

Without overlap rules:

- buckets sprawl
- duplicates multiply
- crew stop trusting documents
- relevance ranking becomes chaotic

With overlap rules:

- truth remains singular
- perspective remains flexible
- documents remain readable
- automation remains safe

---

## Non-negotiable

- One primary domain per entry
- No multi-bucket duplication
- No silent reclassification
- No silent merge

Overlap is structured.  
Not improvised.

---
