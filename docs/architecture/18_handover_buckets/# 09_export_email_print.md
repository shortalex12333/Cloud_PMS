# 09_export_email_print.md

# Export, Email, and Print

This document defines how signed handovers are **exported, distributed, and archived**.

Export is a **representation step**, not a content step.  
No export may alter meaning, structure, or evidence.

---

## Core principle

**Only SIGNED handovers may be exported.**

If a handover is not signed:

- it cannot be emailed
- it cannot be printed
- it cannot be shared externally

This prevents circulation of unverified operational truth.

---

## Export formats

Celeste must support:

- HTML (interactive view)
- PDF (archival and audit)
- Email (distribution)

All exports are generated from the **signed snapshot**, never from live draft data.

---

## Export content requirements

Every exported handover must contain:

- vessel name and reporting period
- sectioned buckets in fixed order
- narrative items per domain
- risk tags where applicable
- uncertainty indicators
- source reference footnotes or links
- outgoing and incoming signatories
- timestamps
- document hash

No export may omit attribution or source traceability.

---

## Email distribution rules

When emailing a handover:

- recipients are selected manually by user
- default recipients may be suggested by role
- email body contains summary and link to full document
- PDF snapshot attached
- email metadata logged

No automatic emailing without user confirmation.

---

## Print rules

Printed versions must:

- match PDF layout exactly
- include document hash
- include signatory block
- include page numbers and section headers

Printed handovers remain valid records outside Celeste.

---

## Storage of exports

Each export creates a record:

```

handover_export:
id
draft_id
export_type (pdf/html/email)
storage_path
exported_by_user_id
exported_at
recipients[] (if email)
document_hash

```

Exports are immutable.  
If content changes, a new handover must be signed.

---

## Branding and uniformity

All exports use:

- fixed typography
- fixed bucket ordering
- fixed header and footer
- consistent tone and layout

Only section visibility and content change.

No dynamic templates per department.  
One brand. One format. Always.

---

## External availability

Exports must be:

- readable without Celeste
- valid during network loss
- archivable by management
- admissible in audits

Celeste accelerates handover creation.  
Celeste is not required to read handovers.

---

## Failure behavior

If export fails:

- signed handover remains valid
- no partial export released
- user notified
- retry permitted

No fallback to unsigned drafts.

---

## Non-negotiable

- No export before sign-off
- No silent email sending
- No template deviation
- No removal of source references
- No mutable export files

Signed means final.  
Export means permanent.

---
```
