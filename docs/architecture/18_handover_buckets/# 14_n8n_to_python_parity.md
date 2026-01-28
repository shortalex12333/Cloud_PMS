# 14_n8n_to_python_parity.md

# n8n to Python Parity Mapping

This document defines how the existing n8n-based handover email workflow maps to the Celeste Python-based handover pipeline.

The goal is **behavioral parity first**, improvement second.

No regression in reliability.  
No loss of features.  
No loss of traceability.

---

## Current n8n behavior (baseline)

Existing workflow performs:

1. Receives webhook trigger  
2. Fetches email content  
3. Formats handover report in HTML  
4. Sends email via Outlook connector  
5. Logs send result  

This produces a readable report,  
but lacks traceability, acceptance gates, and audit linking.

---

## Celeste Python pipeline (replacement)

Celeste replaces each n8n stage with controlled steps.

| Stage | n8n Today | Celeste Python |
|-------|-----------|----------------|
| Trigger | Webhook | Draft generation trigger (schedule or manual) |
| Data fetch | Email body | Fetch handover_entries + ledger + sources |
| Formatting | HTML templating | Draft assembly pipeline |
| Human review | None | IN_REVIEW → ACCEPTED → SIGNED |
| Email send | Outlook connector | Export after signoff only |
| Logging | n8n execution log | handover_exports + audit trail |

---

## Functional parity requirements

Celeste must match n8n ability to:

- generate HTML handover
- send email with attachments
- run on schedule
- retry failed sends

Celeste must exceed n8n by adding:

- explicit review
- sign-off gates
- source traceability
- immutable snapshots

---

## Event triggers

### n8n today

```

Webhook → Execute workflow → Send email

```

### Celeste

```

Scheduler / Manual Trigger
→ Generate Draft
→ Human Review
→ Sign-off
→ Export + Email

```

No direct trigger may bypass review.

---

## Email formatting parity

Celeste templates must:

- match current professional layout
- support dynamic section list
- preserve consistent styling

But:

- must include signatory block
- must include traceability footer
- must include document hash

---

## Failure parity

If email send fails:

n8n today:
- workflow retries or logs error

Celeste:
- signed handover remains valid
- export retry available
- no loss of data

---

## Removal of implicit behavior

n8n today:

- silently formats content
- silently sends

Celeste must:

- never silently publish
- never silently edit content
- never silently skip errors

---

## Migration path

1. Run Celeste pipeline in parallel with n8n
2. Compare outputs for several handovers
3. Validate layout parity
4. Enable sign-off gating
5. Disable n8n email send
6. Remove webhook dependency

---

## Non-negotiable

- Python pipeline must replicate n8n reliability
- Must exceed n8n traceability
- Must not send without sign-off
- Must support manual resend

If parity not achieved, n8n remains fallback.

---
```
