```markdown
# Handover Draft Model

This document defines the **handover draft object**, its **state machine**, and **edit behavior**.

A handover draft is a **living narrative** built from accepted handover entries, reviewed by humans, then locked by signature.

It is not a report.  
It becomes a report only after acceptance.

---

## Core concept

A handover draft is:

- auto-assembled from accepted handover entries
- explicitly editable by humans
- fully traceable to source events
- unpublishable until signed

Drafts are temporary.  
Signed handovers are permanent records.

---

## Draft lifecycle states

```

DRAFT → IN_REVIEW → ACCEPTED → SIGNED → EXPORTED

```

### DRAFT
- Created by Celeste from stored handover entries
- May be regenerated multiple times
- Not visible outside authorized onboard users
- Editable freely

### IN_REVIEW
- A user has opened the draft for handover preparation
- Edits, merges, rewording allowed
- Additions and removals tracked
- No external export permitted

### ACCEPTED
- Reviewer confirms draft content is correct
- Warning banner displayed:
  “Celeste can make mistakes. You are responsible for reviewing and confirming this handover.”
- Acceptance recorded with user and timestamp
- Content frozen for signing

### SIGNED
- Receiving party countersigns
- Responsibility transfer recorded
- Snapshot locked and immutable

### EXPORTED
- PDF / HTML / Email generated
- Stored permanently
- Traceable to signed snapshot

---

## Draft structure

A handover draft contains:

```

handover_draft:
id
vessel_id
period_start
period_end
created_at
created_by_system_version
state
last_modified_at

```
```

handover_draft_sections:
draft_id
bucket_name   (Command / Engineering / ETO / Deck / Interior / Admin)
section_order

```
```

handover_draft_items:
draft_id
section_bucket
domain_code
summary_text
source_entry_ids[]
source_event_ids[]
risk_tags[]
confidence_level
item_order

```
```

handover_draft_edits:
draft_id
item_id
edited_by_user_id
edit_timestamp
original_text
edited_text
edit_reason (optional)

```

---

## Draft generation rules

- Drafts pull only **accepted handover entries**
- Entries marked suppressed are excluded
- AI may:
  - merge duplicates
  - summarise repetitive items
  - rank by risk posture
- AI must:
  - retain source links
  - preserve attribution
  - mark uncertainty where evidence conflicts

No draft overwrites raw entries.

---

## Editing rules

Users may:

- rewrite summary text
- reorder items
- merge items (with confirmation)
- split items (creating new references)

Users may not:

- delete source references
- change domain classification
- change bucket assignment
- change risk tags directly

Classification corrections are logged separately.

---

## Acceptance rules

A draft cannot be accepted unless:

- user scrolls through all sections
- unresolved conflicts are acknowledged
- acceptance checkbox is ticked
- identity and timestamp recorded

No silent acceptance.  
No background approval.

---

## Signature rules

Signature requires:

- outgoing responsible officer acceptance
- incoming responsible officer countersign
- both identities recorded
- immutable timestamping

Once signed:

- draft becomes read-only
- snapshot generated
- audit record sealed

---

## Export rules

Only SIGNED drafts can be exported.

Exports must include:

- sectioned narrative
- source reference footnotes
- signatory names and timestamps
- document hash for tamper detection

---

## Failure behavior

If generation fails:

- no draft is published
- previous signed handover remains active
- error logged
- manual draft creation allowed

If signing fails:

- draft remains in ACCEPTED
- no export permitted

---

## Success condition

A new crew member opens the signed handover and:

- understands vessel state quickly
- sees unresolved issues clearly
- trusts source traceability
- knows who signed responsibility

If oral explanation is required to fill gaps,  
draft model has failed.

---
```
