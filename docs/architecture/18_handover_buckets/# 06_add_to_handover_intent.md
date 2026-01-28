```markdown
# 06_add_to_handover_intent.md

# Add to Handover Intent Detection

This document defines **when and how Celeste proposes or accepts the addition of content into a handover entry**.

Handover content must originate from real operational context.  
No speculative insertion.  
No silent capture.

---

## Core principle

**Handover entries are created at the moment operational relevance is detected — not at report generation time.**

If context is not captured when it occurs,  
it will be misrepresented later.

---

## Two valid creation paths

### 1) Explicit user addition

A user manually selects:

> “Add to handover”

This action:

- creates a new handover entry
- captures current narrative context
- links any active search or viewed records
- records author and timestamp
- stores classification metadata

No further inference required.

---

### 2) Proposed addition by Celeste

Celeste may propose:

> “Add this to handover?”

This proposal appears only when:

- a search query indicates unresolved state
- a ledger mutation records a fault or deferral
- repeated queries indicate persistent uncertainty
- a risk-tagged entity is detected
- a user views critical evidence without resolution

Proposal must always be:

- visible
- dismissible
- never auto-accepted

If dismissed, dismissal is logged.

---

## Intent detection signals

Celeste monitors for:

### Search-based signals
- “still broken”
- “not fixed”
- “unknown alarm”
- “recurring issue”
- “waiting for parts”
- “no update”
- “temporary fix”

### Entity-based signals
- safety equipment entities
- compliance certificates
- propulsion / power entities
- guest-impact systems
- network / monitoring systems

### Event-based signals
- fault logged
- maintenance deferred
- inspection failed
- spares ordered
- vendor contacted
- workaround applied

---

## Entity-to-domain mapping

When intent detected, Celeste assigns:

- primary domain (from entity map)
- secondary domains (if multi-discipline)
- presentation bucket (from domain map)
- suggested owner roles (from role bias map)
- risk tags (from rule engine)

These are shown to the user **before saving**.

User never manually selects taxonomy.

---

## Creation payload

Each accepted addition stores:

```

handover_entry:
id
vessel_id
created_at
created_by_user_id
created_by_role
primary_domain
secondary_domains[]
presentation_bucket
suggested_owner_roles[]
risk_tags[]
narrative_text
source_event_ids[]
source_document_ids[]
status = candidate

```

---

## Narrative text rules

Narrative must:

- default to user’s own phrasing
- be editable before save
- never be rewritten automatically without approval

Celeste may propose wording suggestions,  
but must never overwrite human phrasing silently.

---

## Classification correction

If user disagrees with suggested domain:

- user may flag misclassification
- entry still saved
- correction request logged
- taxonomy team reviews offline

Classification is never silently changed.

---

## Why this matters

If handover entries are only created at report time:

- urgency is lost
- emphasis is distorted
- accountability is blurred
- narrative becomes retrospective fiction

Capturing intent at moment of work preserves truth.

---

## Non-negotiable

- No silent handover entry creation
- No mandatory taxonomy selection by users
- No auto-accept of proposed additions
- No deletion of dismissed proposals without trace

If intent detection fails,  
users must still be able to add manually.

---
```
