# Warranty Domain — Test Cheat Sheet

**Last verified:** 2026-04-16 (live backend wire walk — 17 tests, 0 failures)  
**Commit:** `d5a5de92` (PR #558) + fixes in PRs #552, #558  
**Backend:** `https://backend.celeste7.ai`  
**Frontend:** `https://app.celeste7.ai`  
**Tenant DB:** `vzsohavtuotocgrfkfyd.supabase.co`  
**Test yacht_id:** `85fe1119-b04c-41ac-80f1-829d23322598`

---

## How to navigate to a warranty claim

1. Log in to `app.celeste7.ai`
2. Sidebar → **Warranty**
3. Click any claim row → opens `/warranty/{id}` (the warranty lens)
4. Or: Global search → type "warranty" → select a claim

---

## Role map — who can do what

| Role | Draft claim | File claim | Submit | Approve | Reject | Close | Compose email | Add note | View |
|------|------------|-----------|--------|---------|--------|-------|---------------|----------|------|
| `crew` | **YES** (draft_warranty_claim) | **NO** | NO | NO | NO | NO | NO | NO | YES |
| `chief_engineer` | YES | YES | YES | NO | NO | NO | YES | YES | YES |
| `chief_officer` | YES | YES | YES | NO | NO | NO | YES | YES | YES |
| `captain` | YES | YES | YES | YES | YES | YES | YES | YES | YES |
| `manager` | YES | YES | YES | YES | YES | YES | YES | YES | YES |
| `purser` | NO | NO | NO | NO | NO | NO | NO | NO | YES |

**Two filing actions — same dispatcher, different allowed roles:**
- `draft_warranty_claim` (`registry.py:2243`) — crew + HOD. Creates a draft claim. No difference in output from `file_warranty_claim`.
- `file_warranty_claim` (`registry.py:2734`) — HOD only (chief_engineer, chief_officer, captain, manager). Semantically identical.

**Source:** `apps/api/action_router/registry.py` — `file_warranty_claim:2734`, `draft_warranty_claim:2243`, `submit_warranty_claim:2277`, `approve_warranty_claim:2294`, `compose_warranty_email:2348`

> **Crew CAN initiate:** crew uses `draft_warranty_claim`. HOD uses `file_warranty_claim`. Both call `_draft_warranty_claim` in the dispatcher (`internal_dispatcher.py:4188–4189`).

---

## Status lifecycle

```
draft → submitted → approved → closed
           ↓
        rejected → (revise) → submitted
```

| Status | DB value | Status label (UI) | Who transitions it |
|--------|----------|------------------|--------------------|
| Draft | `draft` | Draft | Created by filer |
| Submitted | `submitted` | Submitted | Chief Engineer / Captain submits |
| Approved | `approved` | Approved | Captain / Manager approves |
| Rejected | `rejected` | Rejected | Captain / Manager rejects |
| Closed | `closed` | Closed | Captain / Manager closes |

---

## Normal operation — full flow test

### Flow A: File → Submit → Approve → Close

| Step | Who | Button / Action | Expected result | Y/N check |
|------|-----|-----------------|-----------------|-----------|
| 1 | Chief Engineer | **File Warranty Claim** (sidebar or search) | Modal opens with: Title, Vendor, Description, Claim Type, Currency (USD default), Manufacturer Email, optional Part/Serial/Amount fields | Y if modal opens cleanly |
| 2 | Chief Engineer | Fill form, click **Submit** | Claim created, lens opens, status pill = **Draft** | Y if pill shows Draft |
| 3 | Chief Engineer | Primary button: **Submit Claim** | Status changes to **Submitted**, pill = amber Submitted | Y if pill turns amber |
| 4 | Captain | Opens same claim | Status = Submitted, sees **Approve** as primary button | Y if Approve appears |
| 5 | Captain | Clicks **Approve** | Popup opens with `approved_amount` and `notes` optional fields | Y if popup shows those fields |
| 6 | Captain | Fills approved amount, submits | Status = **Approved**, pill = green | Y if pill turns green |
| 7 | Captain | Primary button: **Close Claim** | Status = **Closed**, pill = red | Y if pill turns red |

### Flow B: File → Submit → Reject → Revise → Resubmit

| Step | Who | Button | Expected result | Y/N check |
|------|-----|--------|-----------------|-----------|
| 1–3 | Chief Engineer | As above | Claim in Submitted state | — |
| 4 | Captain | Dropdown → **Reject Claim** | Popup opens with `rejection_reason` required field | Y if popup shows rejection_reason |
| 5 | Captain | Enter reason, submit | Status = **Rejected**, `rejection_reason` visible in Claim Details | Y if reason appears |
| 6 | Chief Engineer | Primary button: **Revise & Resubmit** | Status → Submitted again | Y if status resets to Submitted |

### Flow C: Compose email draft

| Step | Who | Button | Expected result | Y/N check |
|------|-----|--------|-----------------|-----------|
| 1 | Any HOD+ | Dropdown → **Compose Email Draft** | Button only visible when claim status ≠ draft | Y if not shown on Draft claims |
| 2 | Any HOD+ | Click it | Triggers `compose_warranty_email` action | — |
| 3 | — | Page reloads / refetches | **Email Draft** section appears at bottom of lens | Y if section visible |
| 4 | — | Check Email Draft section | Shows: Subject line, **To** = manufacturer email (not company name) | Y if "To" is an email address |
| 5 | DB verify | Query `pms_warranty_claims.email_draft` | `email_draft.to = manufacturer_email` from metadata | Y if address matches what was filed |

---

## Buttons on the warranty lens — complete list

| Button | Location | Visible when | Role required | Action fired |
|--------|----------|--------------|---------------|--------------|
| **Submit Claim** | Primary (top right) | status = `draft` | chief_engineer, chief_officer, captain, manager | `submit_warranty_claim` |
| **Approve** | Primary | status = `submitted` | captain, manager | `approve_warranty_claim` — popup |
| **Close Claim** | Primary | status = `approved` | captain, manager | `close_warranty_claim` |
| **Revise & Resubmit** | Primary | status = `rejected` | chief_engineer, chief_officer, captain, manager | `submit_warranty_claim` |
| **Reject Claim** | Dropdown | status = `submitted` | captain, manager | `reject_warranty_claim` — popup |
| **Compose Email Draft** | Dropdown | status ≠ `draft` | chief_engineer, chief_officer, captain, manager | `compose_warranty_email` |
| **Add Note** | Dropdown | always | chief_engineer, chief_officer, captain, manager | opens AddNoteModal |
| **Archive** | Dropdown | status = `draft` or `rejected` | (same as file) | `archive_warranty` |
| **Add file** | Attachments section | always | any authenticated user | opens AttachmentUploadModal |

**Source:** `apps/web/src/components/lens-v2/entity/WarrantyContent.tsx:119–213`

---

## Signature / confirmation popups — where they appear

| Action | Has popup | Popup fields | Source |
|--------|-----------|-------------|--------|
| Submit Claim | **NO** — fires directly | None | `WarrantyContent.tsx:139` `actionHasFields` = false |
| Approve | **YES** | `approved_amount` (optional), `notes` (optional) | `registry.py:2293`, `mapActionFields.ts` renders optional_fields |
| Reject | **YES** | `rejection_reason` (required) | `registry.py:2309` |
| Close Claim | **NO** — fires directly | None | No fields in registry |
| Compose Email | **NO** — fires directly | None | No user fields needed |
| Add Note | **YES** — separate modal | `note_text` textarea | `AddNoteModal` component |

> **Signature level:** None of the warranty actions currently require a cryptographic signature (`requires_signature = False` on all). The Approve action has an `ActionPopup` for data input but is not a signed action in the MLC sense. This is intentional for warranty — it is an internal workflow, not a compliance document.

---

## Field contract — what to enter and what lands in the DB

| UI field | DB column | Notes |
|----------|-----------|-------|
| Title | `title` | Required |
| Vendor / Manufacturer name | `vendor_name` | Required |
| Claim type (dropdown) | `claim_type` | Options: manufacturer_defect, premature_failure, incorrect_part, damage_in_transit, other |
| Description | `description` | Clean — manufacturer email no longer prepended here |
| Manufacturer email | `metadata.manufacturer_email` | Stored in JSONB metadata column, not a dedicated column |
| Currency | `currency` | EUR/USD/GBP/AUD/SGD — defaults to USD in modal |
| Claimed amount | `claimed_amount` | Numeric |
| Equipment ID | `equipment_id` | Free-text UUID currently (search picker not built) |
| Part number | `part_number` | Free text |
| Serial number | `serial_number` | Free text |

**Source:** `apps/api/action_router/dispatchers/internal_dispatcher.py:3491–3514`

---

## Email draft — what works and what doesn't

### What works
- `compose_warranty_email` action generates a structured email template
- `email_draft.to` = `metadata.manufacturer_email` (the address filed with the claim), falls back to `vendor_name` if no email stored
- `email_draft.subject` = `"Warranty Claim {claim_number} — {title}"`
- `email_draft.body` contains: salutation, claim number, title, claim type, serial number, manufacturer, claimed amount, description
- Email draft is stored in `pms_warranty_claims.email_draft` JSONB and returned via entity endpoint
- Lens shows **Subject** and **To** address in the Email Draft section

**Source:** `internal_dispatcher.py:3834–3890`, `WarrantyContent.tsx:382–394`

### What does NOT work (gaps)
- **Body text is NOT rendered in the UI.** It is in the DB but WarrantyContent only shows Subject and To.
- **No edit UI.** The template cannot be modified in-app.
- **No Bcc / CC fields.** Not in the data model or the UI. `internal_dispatcher.py:3847` only has `to`, `subject`, `body`.
- **Does not send.** This is correct and intentional — system provides a draft template only. The user copies and sends via their own email client.

---

## Ledger — what gets written and where

| Action | `event_type` | `entity_type` | Written by |
|--------|-------------|---------------|-----------|
| View claim | `view` | `warranty` | `entity_routes.py:500–518` — explicit |
| File claim | `create` | `warranty` | `p0_actions_routes.py:1133` Phase B safety net |
| Submit claim | `status_change` | `warranty` | Phase B safety net |
| Approve | `approval` | `warranty` | Phase B safety net |
| Reject | `rejection` | `warranty` | Phase B safety net |
| Close | `status_change` | `warranty` | Phase B safety net |
| Compose email | `update` | `warranty` | Phase B safety net |
| Add note | `update` | `warranty` | Phase B safety net |

**Source:** `apps/api/action_router/ledger_metadata.py:97–105`, `p0_actions_routes.py:1133–1177`

**To verify ledger in DB:**
```sql
SELECT event_type, action, user_role, created_at
FROM ledger_events
WHERE entity_type = 'warranty'
  AND entity_id = '<claim_id>'
ORDER BY created_at;
```

Or via Supabase REST:
```
GET /rest/v1/ledger_events?entity_id=eq.<claim_id>&entity_type=eq.warranty
```

---

## Notifications — what gets sent and to whom

| Trigger | Recipient | Notification type | Title |
|---------|-----------|-------------------|-------|
| Claim submitted | All `captain` + `manager` on vessel | `warranty_submitted` | "Warranty Claim Submitted: {title}" |
| Claim approved | Drafter of claim | `warranty_approved` | "Warranty Claim Approved" |
| Claim approved | Submitter (if ≠ drafter) | `warranty_approved` | "Warranty Claim Approved" |
| Claim rejected | Drafter | `warranty_rejected` | "Warranty Claim Rejected" |
| Claim rejected | Submitter (if ≠ drafter) | `warranty_rejected` | "Warranty Claim Rejected" |
| Claim closed | Drafter + submitter | `warranty_closed` | "Warranty Claim Closed" |
| Email composed | All captains/managers (excl. composer) | `warranty_email_composed` | "Warranty Email Draft Ready" |
| Note added | Drafter + submitter + approver | `warranty_note_added` | "Note Added to Warranty Claim" |

Every notification row has `entity_type=warranty` and `entity_id=<claim_id>`.

**Frontend bell wired** (verified 2026-04-18 by WARRANTY04). `apps/web/src/components/shell/NotificationBell.tsx` polls `/api/v1/notifications` every 30s; the route proxies to backend `/v1/notifications` (not an empty stub any more — the old doc line was stale). Clicking a warranty row routes to `/warranties?id=<claim_id>` per the route map at `NotificationBell.tsx:47-48`.

**To verify notifications in DB:**
```sql
SELECT notification_type, title, user_id, is_read
FROM pms_notifications
WHERE entity_id = '<claim_id>'
ORDER BY created_at;
```

---

## Document attachments

- Upload button is always visible in the Attachments section of the lens
- Opens `AttachmentUploadModal` with `bucket=pms-warranty-documents`, `entityType=warranty`, `category=claim_document`
- **Source:** `WarrantyContent.tsx:396–406`
- Uploaded files are retrieved on entity load via `_get_attachments(supabase, "warranty", warranty_id, yacht_id)` in `entity_routes.py:~530`
- Any authenticated user can upload (no role gate on the upload button itself)

---

## Edge cases and limits

### is_seed trap
All `pms_warranty_claims` rows have `is_seed DEFAULT TRUE` in the DB schema. The `v_warranty_enriched` view filters out rows where `is_seed = true`. If a claim was created before PR #558 (2026-04-15), it may have `is_seed = true` and will return 404 from the entity endpoint.

**Fix:** Set `is_seed = false` directly in DB for those rows:
```sql
UPDATE pms_warranty_claims SET is_seed = false WHERE is_seed = true AND claim_number NOT LIKE 'WC-TEST-%';
```
Do NOT clear seed data rows (WC-TEST-001 through WC-TEST-005) — they are intentional test fixtures.

### Status gate violations
- Trying to submit a claim that is already `submitted` → returns `{"status": "error", "message": "Claim must be in draft or rejected status to submit"}`
- Trying to approve a `draft` → `"Claim must be submitted to approve"`
- Trying to close an `approved=false` claim → `"Claim must be approved to close"`

These are hard guards in `internal_dispatcher.py:3553`, `3618`, `3782`.

### Compose email before manufacturer email filed
If the claim was filed without a `manufacturer_email` value, `compose_warranty_email` will set `email_draft.to = vendor_name` (the company name). This is a visual tell that no email address was captured.

**Check:** look at `email_draft.to` — if it contains spaces or looks like a company name rather than an email address, no manufacturer email was supplied at filing time.

### Duplicate claim numbers
Claim numbering is `WC-{year}-{count+1}`. Count is computed as the number of existing claims for that yacht in that year. This is NOT atomic — concurrent filings could produce duplicate numbers. Low risk for single-vessel operation.

**Source:** `internal_dispatcher.py:3483–3489`

### No equipment search picker
`equipment_id` and `work_order_id` in the file warranty modal are free-text UUID inputs. Entering an invalid UUID or wrong ID will store a broken FK that cannot be resolved by the entity endpoint's equipment join. The equipment name will appear blank on the lens.

---

## Proof checklist — run this to call it done

```
□ 1. Log in as chief_engineer
      Navigate to Warranty → File Warranty Claim modal opens
      Fill: Title, Vendor, Manufacturer Email (test@test.com), Currency=EUR, Amount=1000
      Click Submit
      PASS: status pill = "Draft", claim_number = "WC-{year}-XXX"

□ 2. Same user clicks "Submit Claim" primary button
      PASS: pill changes to amber "Submitted", no popup
      FAIL signals: 422 error, unchanged status, spinner hangs

□ 3. Log in as captain, navigate to same claim
      PASS: primary button = "Approve" (not "Submit Claim")
      Click Approve
      PASS: popup appears with "approved_amount" and "notes" fields (both optional, "(optional)" suffix visible)
      Enter approved_amount=900, submit
      PASS: status = green "Approved"

□ 4. Captain: Dropdown → Compose Email Draft
      PASS: Email Draft section appears at bottom
      PASS: "To" field = test@test.com (the email entered at filing, not the company name)
      FAIL signal: "To" shows company name = manufacturer_email was not stored

□ 5. Captain: Primary button = "Close Claim"
      PASS: status = red "Closed", no popup
      
□ 6. Create a second claim, go through to Submitted, captain clicks Reject
      PASS: popup appears with "rejection_reason" REQUIRED field
      FAIL signal: popup missing field
      Fill reason, submit
      PASS: rejection_reason visible in Claim Details section

□ 7. Rejected claim: chief_engineer clicks "Revise & Resubmit"
      PASS: status back to Submitted

□ 8. Attachments: click Add file on any claim
      PASS: upload modal opens
      Upload any PDF
      PASS: attachment row appears in Attachments section after upload

□ 9. Notes: Dropdown → Add Note
      PASS: modal opens with text area
      Submit note
      PASS: note row appears in Notes section

□ 10. DB verify (Supabase dashboard or psql):
      SELECT currency, metadata, description FROM pms_warranty_claims WHERE id = '<claim_id>';
      PASS: currency = 'EUR', metadata = {"manufacturer_email":"test@test.com"}, description does NOT contain the email address

□ 11. Ledger verify:
      SELECT event_type, action FROM ledger_events WHERE entity_type='warranty' AND entity_id='<claim_id>';
      PASS: rows exist for create, status_change, approval, view
      FAIL signal: empty result = Phase B safety net not firing

□ 12. Notifications verify:
      SELECT notification_type, user_id FROM pms_notifications WHERE entity_id='<claim_id>';
      PASS: warranty_submitted rows exist (one per captain/manager on vessel)
      PASS: warranty_approved row exists addressed to the drafter's user_id
```

---

## CRITICAL: API payload field names — use exactly these

The dispatcher at `internal_dispatcher.py:3546` resolves the claim ID via:
```python
warranty_id = params.get("warranty_id") or params.get("claim_id") or params.get("entity_id")
```

**Wrong field names will silently pass (no 400), but the handler gets `None` → Supabase gets the literal string `"None"` → `22P02 invalid input syntax for type uuid` at DB level.**

| Action | Correct payload field for the claim ID | Other required fields |
|--------|----------------------------------------|----------------------|
| `draft_warranty_claim` | N/A (creates new) | `title`, `description` (required), `vendor_name`, `manufacturer_email` (optional) |
| `file_warranty_claim` | N/A (creates new) | same as above |
| `submit_warranty_claim` | `claim_id` | — |
| `approve_warranty_claim` | `claim_id` | `approved_amount` (opt), `notes` (opt) |
| `reject_warranty_claim` | `claim_id` | `rejection_reason` (required) |
| `close_warranty_claim` | `warranty_id` | — |
| `compose_warranty_email` | `claim_id` | — |
| `add_warranty_note` | `warranty_id` | `note_text` (required) |
| `attach_warranty_document` | `entity_id` | `document_url`, `document_name` |

> **NB:** `add_warranty_note` uses `warranty_id` not `claim_id`. The note is stored in `pms_notes.warranty_id`. Entity endpoint query at `entity_routes.py:526` selects `.eq("warranty_id", warranty_id)` — if you send the wrong field, the note is written to DB but not linked to the claim and won't appear in the Notes section.

### Correct curl shapes

```bash
# File claim (HOD)
curl -X POST https://backend.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"file_warranty_claim","context":{"yacht_id":"85fe1119-..."},"payload":{"title":"Compressor failure","description":"...","vendor_name":"Atlas Copco","manufacturer_email":"warranty@atlascopco.com"}}'

# Submit claim
curl -X POST https://backend.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"submit_warranty_claim","context":{"yacht_id":"85fe1119-..."},"payload":{"claim_id":"<CLAIM_ID>"}}'

# Approve (captain)
curl -X POST https://backend.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"approve_warranty_claim","context":{"yacht_id":"85fe1119-..."},"payload":{"claim_id":"<CLAIM_ID>","approved_amount":4500,"notes":"Approved."}}'

# Reject (captain)
curl -X POST https://backend.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"reject_warranty_claim","context":{"yacht_id":"85fe1119-..."},"payload":{"claim_id":"<CLAIM_ID>","rejection_reason":"Outside warranty window."}}'

# Compose email
curl -X POST https://backend.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"compose_warranty_email","context":{"yacht_id":"85fe1119-..."},"payload":{"claim_id":"<CLAIM_ID>"}}'

# Add note
curl -X POST https://backend.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"add_warranty_note","context":{"yacht_id":"85fe1119-..."},"payload":{"warranty_id":"<CLAIM_ID>","note_text":"Serial confirmed: AT-2024-998877."}}'

# Read entity
curl https://backend.celeste7.ai/v1/entity/warranty/<CLAIM_ID>?yacht_id=85fe1119-... \
  -H "Authorization: Bearer $TOKEN"
```

---

## Live backend test results — 2026-04-16

All tests run against `backend.celeste7.ai` (`d5a5de92`). Auth via MASTER Supabase JWT (`qvzmkaamzaqxpzbewjxe`).

| Test | Action | Role | HTTP/Result | PASS/FAIL |
|------|--------|------|-------------|-----------|
| T01 | Entity read (new claim) | chief_engineer | 200, all fields populated | **PASS** |
| T02 | `file_warranty_claim` | crew | FORBIDDEN — `required_roles: [chief_engineer, chief_officer, captain, manager]` | **PASS** |
| T03 | `add_warranty_note` | chief_engineer | success, note linked to claim (using `warranty_id`) | **PASS** |
| T04 | `compose_warranty_email` | chief_engineer | success, `email_draft.to = warranty@atlascopco.com` | **PASS** |
| T05 | `submit_warranty_claim` | chief_engineer | success, `new_status: submitted` | **PASS** |
| T06 | `approve_warranty_claim` | captain | success, `new_status: approved`, `approved_amount: 4500.0` | **PASS** |
| T06b | `approve_warranty_claim` | crew | FORBIDDEN — `required_roles: [captain, manager]` | **PASS** |
| T07 | Entity read (approved claim) | crew | 200, `status: approved`, `approved_amount: 4500.0`, `email_draft.to: warranty@atlascopco.com` | **PASS** |
| T08 | Ledger events | — | 6 warranty events: create, note, email, submit, approve, view×3 | **PASS** |
| T09 | Notifications | — | Rows written to `pms_notifications` (no frontend surface yet) | **PASS (DB only)** |
| T10 | Notes on entity | chief_engineer | 1 note visible when using correct `warranty_id` field | **PASS** |
| T11 | `file_warranty_claim` | chief_engineer | success, WC-2026-007 | **PASS** |
| T12 | `submit_warranty_claim` | chief_engineer | success, submitted | **PASS** |
| T13 | `reject_warranty_claim` | captain | success, `new_status: rejected`, rejection_reason on entity | **PASS** |
| T14 | `file_warranty_claim` | captain | success, WC-2026-008 | **PASS** |
| T15 | `submit_warranty_claim` | crew | FORBIDDEN — `required_roles: [chief_engineer, chief_officer, captain]` | **PASS** |
| T16 | `reject_warranty_claim` | crew | FORBIDDEN — `required_roles: [captain, manager]` | **PASS** |
| T17 | `draft_warranty_claim` | crew | success, WC-2026-009 — crew CAN draft | **PASS** |

**Ledger event breakdown for claim `e329dde0-c159-4cc1-b9d5-d5ca4a9f0c1b`:**
```
[create      ] file_warranty_claim       | role=chief_engineer | 03:14:00
[update      ] add_warranty_note         | role=chief_engineer | 03:15:07
[update      ] compose_warranty_email    | role=chief_engineer | 03:16:02
[status_change] submit_warranty_claim   | role=chief_engineer | 03:16:56
[approval    ] approve_warranty_claim    | role=captain        | 03:17:14
[view        ] view_warranty_claim       | role=crew           | 03:17:15
```

**To query via backend:**
```bash
curl "https://backend.celeste7.ai/v1/ledger/events?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598&entity_id=<claim_id>&entity_type=warranty" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Known gaps — do not claim these work

| Gap | Status | Who should fix |
|-----|--------|---------------|
| Email body not displayed in UI | **FIXED** 2026-04-18 — `WarrantyContent.tsx:407-414` renders body in `.emailBody` block via `KVSection` children slot. Testid `warranty-email-body`. | WARRANTY04 |
| Email body not editable in-app | Not built (read-only render only) | Follow-up — add textarea + compose_warranty_email_edit action |
| Bcc / CC fields on email draft | Not built | Follow-up — add to `email_draft` data model and compose handler |
| Notification inbox / bell for warranty | **SHIPPED** — `NotificationBell.tsx` routes warranty → `/warranties` | CERTIFICATE01 (platform-wide wire) |
| `close_warranty_claim` prefill mismatch (registry wants `warranty_id`, prefill had `claim_id`) | **FIXED** 2026-04-18 — `entity_prefill.py:114` | WARRANTY04 |
| Equipment / WO ref search picker | Not built | Separate feature — requires `SearchPicker` component |
| Auto email link (NLP match) | Not built | Separate feature — manual email linking only |
| Atomic claim number generation | Race condition risk | Low priority for single vessel |
| Component-level warranty-period tracking (in/out of warranty) | Not built | Cross-domain (needs `pms_equipment.warranty_start_date` + period column) |

---

## For HMAC01 — receipt layer adapter notes

**Domain:** `warranty`  
**Primary table:** `pms_warranty_claims`  
**Read via view:** `v_warranty_enriched` — always use this for reads, filters `is_seed=false`  
**Ledger entity_type:** `warranty`  
**Ledger entity_id field:** `warranty_id` (maps to `id` on the claims table)  

**Receipt trigger events:** `approval` (`approve_warranty_claim`) and `status_change:close` (`close_warranty_claim`)  
**Receipt shape:** Single scope — one claim = one receipt  

**Key fields for receipt body:** `claim_number`, `title`, `vendor_name`, `manufacturer`, `claimed_amount`, `currency`, `approved_amount`, `status`, `drafted_at`, `submitted_at`, `approved_at`, `drafted_by`, `submitted_by`, `approved_by`, `description`  

**HMAC rules that apply:**
- No raw UUIDs in sealed PDF — use HMAC refs for `drafted_by`, `submitted_by`, `approved_by`
- `is_seed` guard: only process claims where `is_seed = false`
- `yacht_id` scope is enforced at DB level (RLS on tenant project `vzsohavtuotocgrfkfyd`)
- No LLM calls — `email_draft.body` is a deterministic Python f-string, no inference in the path

**Audit trail for receipt:** `pms_audit_log WHERE entity_type='warranty' AND entity_id='<claim_id>'`

**Adapter contract questions to answer:**
1. What records? → rows from `v_warranty_enriched` for the given `entity_id` + `yacht_id`
2. Which ledger events? → `approval` and/or `status_change` events from `ledger_events` for the claim
