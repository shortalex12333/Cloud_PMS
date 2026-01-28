# 11_storage_paths_naming.md

# Storage Paths and Naming Convention

This document defines how handover-related artifacts are stored in Supabase Storage (or equivalent object storage).

Storage structure must:

- preserve audit traceability
- support multi-yacht tenancy
- prevent overwrite of signed records
- allow deterministic retrieval
- survive external export

No ad-hoc paths.  
No manual file naming.  
No silent overwrite.

---

## Root structure

```

/handover
/{vessel_id}
/drafts
/signed
/exports
/sources

```

---

## Draft storage

Draft snapshots (HTML previews, working renders):

```

/handover/{vessel_id}/drafts/{draft_id}/
draft.html
draft.json
assets/

```

Rules:

- drafts may be regenerated
- previous draft files may be replaced
- drafts are never externally shared
- draft storage is non-authoritative

---

## Signed snapshot storage

Signed handovers are immutable.

```

/handover/{vessel_id}/signed/{draft_id}/
handover.html
handover.pdf
handover.json
document_hash.txt

```

Rules:

- signed snapshots never overwritten
- any correction requires new draft + new signature
- hash must match database record

---

## Export storage

Exports distributed externally.

```

/handover/{vessel_id}/exports/{export_id}/
handover.pdf
handover.html
email.eml (if applicable)
recipients.json
document_hash.txt

```

Rules:

- exports reference signed snapshot only
- exports immutable
- exports always traceable to signoff

---

## Source material storage

External materials linked to entries:

```

/handover/{vessel_id}/sources/{source_id}/
original_file.ext
metadata.json

```

Examples:

- forwarded emails
- inspection reports
- vendor quotations
- photos

Sources never modified after upload.

---

## Naming conventions

- `{vessel_id}`: UUID of yacht tenant
- `{draft_id}`: UUID of handover draft
- `{export_id}`: UUID of export record
- `{source_id}`: UUID of source record

No human-readable names required.  
All human-readable labels live in database metadata.

---

## Access control

- Draft paths accessible only to onboard authenticated users
- Signed paths readable by authorized crew and management
- Export paths readable by external recipients via time-limited links

No public buckets.  
No shared credentials.

---

## Version guarantees

- Drafts may change
- Signed snapshots never change
- Exports never change

If content changes, a new object is created.

---

## Disaster recovery

Signed and exported paths must be included in:

- daily backups
- retention policies aligned with audit requirements

Minimum retention: 24 months.

---

## Non-negotiable

- No overwrite of signed files
- No deletion of signed handovers
- No reuse of storage paths
- No direct user upload into signed/export directories

Immutable means immutable.

---
```
