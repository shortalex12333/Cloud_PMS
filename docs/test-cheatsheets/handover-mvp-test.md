# Handover MVP — Test Cheat Sheet

**Date:** 2026-04-15  
**Author:** HANDOVER01  
**URL:** `app.celeste7.ai/handover-export`  
**Backend:** `pipeline-core.int.celeste7.ai`  
**DB:** TENANT — `vzsohavtuotocgrfkfyd.supabase.co`

---

## Test users

| Role | Email | Password | DB role | Department | What they can do |
|---|---|---|---|---|---|
| Crew | `engineer.test@alex-short.com` | `Password2!` | `crew` | general | Add items, draft CRUD, export, sign outgoing |
| HOD | `captain.tenant@alex-short.com` | `Password2!` | `chief_engineer` | engineering | Everything crew can + countersign |
| Captain | `x@alex-short.com` | `Password2!` | `captain` | deck | Everything HOD can + receives countersign cascade |
| Fleet Manager | `fleet-test-1775570624@celeste7.ai` | `Password2!` | `manager` | interior | Receives countersign cascade |

---

## Scenario 1: Add item from Queue tab

**Where:** `/handover-export` → Queue tab  
**Who:** Any role (including crew)  
**Steps:**
1. Open `/handover-export`
2. Queue tab shows 4 sections: Open Faults / Overdue Work Orders / Low Stock Parts / Pending Purchase Orders
3. Click `+ Add` on any row

**Y/N checklist:**

| Check | Expected | If it fails |
|---|---|---|
| Queue tab loads with item counts | 4 sections, counter badges | Backend `GET /v1/actions/handover/queue` not responding — check Render logs |
| `+ Add` button is visible | Every row has it | Action registry `add_to_handover` doesn't include the user's role — check `registry.py:905` |
| Click `+ Add` → button flips to `✓ Added` | Instant, teal background | `POST /v1/actions/execute` failed — check console for 400/403. If 403: role not in `allowed_roles`. If 400: `required_fields` validation |
| "N items detected · M added to draft" counter updates | M increases by 1 | Optimistic state — if it doesn't update, the fetch response shape changed |
| Item appears in Draft Items tab | Switch tabs, item should be listed | `GET /v1/handover/items` returns empty — could be Render endpoint down, or `added_by` filter mismatch |

**Edge case:** If console shows `400 from qvzmkaamzaqxpzbewjxe.supabase.co` → that's MASTER DB, not our code. Check `useNeedsAttention.ts` — it should use Render API, not direct Supabase. If this error appears, PR #529 wasn't deployed.

**Files:**
- Frontend Queue: `apps/web/src/components/handover/HandoverQueueView.tsx`
- Action handler (Add path): `apps/web/src/components/handover/HandoverQueueView.tsx:306`
- Backend queue endpoint: `apps/api/routes/p0_actions_routes.py:2264`
- Backend add dispatcher: `apps/api/action_router/dispatchers/internal_dispatcher.py:705`
- Registry entry: `apps/api/action_router/registry.py:905`

---

## Scenario 2: Add item from entity lens (Fault, Work Order, Equipment, Part, Certificate)

**Where:** Any entity detail page (e.g., `/faults/{id}`)  
**Who:** Any role  
**Steps:**
1. Open any fault/WO/equipment/part/certificate detail page
2. Click the actions dropdown (SplitButton in the IdentityStrip)
3. Look for "Add to Handover" in the dropdown list
4. Click it

**Y/N checklist:**

| Check | Expected | If it fails |
|---|---|---|
| "Add to Handover" appears in dropdown | Present in list, not greyed out | Backend `get_available_actions` didn't inject it — check `entity_actions.py:131` cross-domain map |
| Clicking it fires an action popup or executes directly | Toast "Added to handover" | Microaction handler at `lib/microactions/handlers/handover.ts:16` uses Render API — check if 403/400 in console |
| Item appears in Draft Items tab at `/handover-export` | Navigate there, check | Same as Scenario 1 draft check |

**Confirmed working on production (2026-04-15):**
```
fault:       add_to_handover ✓
work_order:  add_to_handover ✓
equipment:   add_to_handover ✓
part:        add_to_handover ✓
certificate: add_to_handover ✓
```

**Files:**
- Cross-domain injection: `apps/api/action_router/entity_actions.py:131–138`
- Microaction handler: `apps/web/src/lib/microactions/handlers/handover.ts:16–91`

---

## Scenario 3: Draft Items — view, edit, delete, add note

**Where:** `/handover-export` → Draft Items tab  
**Who:** Any role  
**Steps:**
1. Switch to Draft Items tab
2. Items grouped by day (Today expanded, older collapsed)
3. Click any item → edit popup opens
4. Click "Add Note" → create standalone note
5. Click "Delete" on any item → confirm → item removed

**Y/N checklist:**

| Check | Expected | If it fails |
|---|---|---|
| Draft Items tab loads items | Items appear grouped by day | `GET /v1/handover/items` on Render — check network tab for 401/500. Token expired? Render down? |
| Shows "0 items" despite Queue showing "N added to draft" | BUG — items exist but the read fails | Likely `NEXT_PUBLIC_API_URL` env var not set on Vercel → falls back to wrong URL |
| Click item → edit popup | Summary, category, status, section fields shown | Frontend popup logic in `HandoverDraftPanel.tsx:302` |
| Save edit → summary changes | Toast "Handover note updated" | `PATCH /v1/handover/items/{id}` failed — check 404 (item not owned by this user) or 400 (payload shape) |
| Delete → confirm → item disappears | Toast "Handover note deleted" | `DELETE /v1/handover/items/{id}` failed — check ownership (`added_by` mismatch) |
| Add Note → modal with blank fields | Summary required (min 3 chars) | Summary under 3 chars → "summary must be at least 3 characters" from backend |
| Category "Critical" works | Item marked with red badge | Backend normalises `critical → urgent` and sets `is_critical=true` |

**Edge case:** HOD cannot edit/delete crew member's item. This is by design — `added_by = user_id` filter enforces ownership. Only the item creator can modify it.

**Files:**
- Frontend Draft panel: `apps/web/src/components/handover/HandoverDraftPanel.tsx`
- Fetch items: `HandoverDraftPanel.tsx:508` → `GET /v1/handover/items`
- PATCH handler: `apps/api/routes/handover_export_routes.py:936`
- DELETE handler: `apps/api/routes/handover_export_routes.py:978`

---

## Scenario 4: Export → generate document

**Where:** `/handover-export` → Draft Items tab → Export button  
**Who:** Any role  
**Steps:**
1. Ensure Draft Items tab has at least 1 item
2. Click "Export Handover" button
3. Wait (LLM pipeline takes 30–120 seconds)
4. Toast appears with "View" action → click to see document

**Y/N checklist:**

| Check | Expected | If it fails |
|---|---|---|
| Export button visible | Bottom-left of Draft Items | Only shows when `items.length > 0` |
| Click → loading state | "Exporting..." spinner | `POST /v1/handover/export` called |
| Success toast | "Handover exported — N items" with "View" button | If timeout: LLM microservice at `handover-export.onrender.com` is slow/down. Check Render dashboard. |
| Click "View" → document page | Full document: cover, TOC, sections, items, signature block | Navigates to `/handover-export/{export_id}` |
| Document body NOT empty | Sections with items, not "No handover content available" | Entity handler fallback to `v_handover_draft_complete` — check `entity_routes.py:624–665` |

**Edge case:** If microservice is down, fallback runs (basic HTML, no LLM summaries). Feature flag: `HANDOVER_USE_MICROSERVICE=true` on Render.

**Files:**
- Export trigger: `HandoverDraftPanel.tsx:610`
- Backend export route: `apps/api/routes/handover_export_routes.py:63`
- Microservice client: `apps/api/services/handover_microservice_client.py`
- Entity handler (sections): `apps/api/routes/entity_routes.py:594–665`

---

## Scenario 5: View generated document

**Where:** `/handover-export/{export_id}`  
**Who:** Any role on the yacht  
**Steps:**
1. Navigate to the export URL
2. Document loads with: cover header, table of contents, department sections, items, signature block

**Y/N checklist:**

| Check | Expected | If it fails |
|---|---|---|
| Document header shows | "Technical Handover Report", vessel name, doc number, date | Entity handler returned data correctly |
| Table of Contents | Lists each section with item count | `sections[]` array populated — if empty, check `entity_routes.py:624` fallback |
| Section items render | Each item has numbered reference, content text, entity link | Items mapped from `summary_text → content` in entity handler |
| Entity links ("View Fault →") | Teal links that navigate to the source entity | `entity_url` field populated in `handover_draft_items` |
| Signature block at bottom | "Prepared By" + "Reviewed By" columns | Static layout in `HandoverContent.tsx:493–515` |

**What you won't see (not yet built):**
- Dynamic signature states (SIGNED ✓ / Pending) — the signature block is static HTML
- Third column "Accepted By" for incoming crew — not yet wired

**Files:**
- Page: `apps/web/src/app/handover-export/[id]/page.tsx`
- Component: `apps/web/src/components/lens-v2/entity/HandoverContent.tsx`
- Entity endpoint: `apps/api/routes/entity_routes.py:594`

---

## Scenario 6: Sign handover (outgoing user)

**Where:** `/handover-export/{export_id}` → "Sign Handover" button  
**Who:** Captain, Chief Engineer, Chief Officer, Manager (HOD+ roles only — `registry.py:2693`)  
**When:** `review_status === 'pending_review'`

**Steps:**
1. Open a handover export that has `review_status = pending_review`
2. "Sign Handover" button appears in the IdentityStrip action slot
3. Click → signature canvas modal appears
4. Draw signature → click "Confirm & Sign"

**Y/N checklist:**

| Check | Expected | If it fails |
|---|---|---|
| "Sign Handover" button visible | Shows for HOD+ when status is pending_review | `canSignOutgoing` check at `HandoverContent.tsx:116` — verify `review_status` is correct AND user role is in `['chief_engineer', 'chief_officer', 'captain', 'manager']` |
| Button NOT visible for crew role | Crew cannot see it | Correct — `sign_handover` requires HOD+ roles per registry |
| Click → canvas modal | 416x160 white canvas with "Draw your signature" | Modal at `HandoverContent.tsx:698` |
| Draw + click "Confirm & Sign" | Toast "Handover signed — HOD notified for countersignature" | Calls `POST /v1/handover/export/{id}/submit` at `HandoverContent.tsx:242` |
| After sign: status changes to amber "Pending Hod Signature" | Page refetches, pill colour changes | `refetch()` at line 267 re-calls entity endpoint |
| "Sign Handover" button disappears | Replaced by "Export PDF" or "Countersign" | `canSignOutgoing` is now false (status changed) |

**Edge case — "Already submitted" error:** If you reload and try to sign again after already submitting → backend returns 400 "Already submitted" at `handover_export_routes.py:776`.

**Edge case — crew tries to sign:** The button won't show. If they somehow POST directly to `/submit`, it would succeed (the submit route doesn't have a role check — it only checks review_status). This is an acceptable MVP gap because the button is invisible.

**Signature popup belongs:** On the `/handover-export/{id}` page, inside the `HandoverContent` component. The IdentityStrip's `SplitButton` opens it. It does NOT appear on the draft panel or queue tab.

**Files:**
- Button render: `HandoverContent.tsx:407–419`
- Modal: `HandoverContent.tsx:698–790`
- Submit handler: `HandoverContent.tsx:184–268`
- Backend submit: `apps/api/routes/handover_export_routes.py:755–811`

---

## Scenario 7: Countersign (HOD reviews and signs)

**Where:** `/handover-export/{export_id}` → "Countersign Handover" button  
**Who:** Chief Engineer, Chief Officer, Captain, Manager  
**When:** `review_status === 'pending_hod_signature'`

**Steps:**
1. HOD receives ledger notification "Handover requires your countersignature"
2. Clicks notification → lands on `/handover-export/{export_id}`
3. "Countersign Handover" button visible (different label from Sign)
4. Click → canvas modal → draw signature → confirm

**Y/N checklist:**

| Check | Expected | If it fails |
|---|---|---|
| Button shows "Countersign Handover" (not "Sign") | Dynamic label from `signButtonLabel` at `HandoverContent.tsx:179` | `canCountersign` is false — check `review_status` is `pending_hod_signature` AND user role is HOD+ |
| Modal says "Draw your signature to countersign and complete" | Different text from outgoing sign | `HandoverContent.tsx:712–713` |
| Click confirm → toast "Handover countersigned — rotation complete" | Status transitions to `complete` | `POST /v1/handover/export/{id}/countersign` at `HandoverContent.tsx:224` |
| After countersign: document is READ-ONLY | No edit buttons, no sign buttons | `canSign` is false, `isEditable` is false |
| Captain + Manager receive ledger notification | "Handover countersigned and complete. Rotation closed." | Cascade at `handover_export_routes.py:894–911` |

**Edge case — wrong role tries to countersign:** 403 from backend. Check: `handover_export_routes.py:838` — `["chief_engineer", "chief_officer", "captain", "manager"]`. If role is `crew` or `engineer`, they get 403.

**Edge case — countersign on wrong state:** 400 "Not awaiting countersign" — export must be in `pending_hod_signature` state.

**Files:**
- Countersign detection: `HandoverContent.tsx:117–118`
- Backend route: `apps/api/routes/handover_export_routes.py:814–872`
- Cascade: `handover_export_routes.py:878–911`

---

## Scenario 8: Ledger notification navigation

**Where:** Ledger panel (sidebar)  
**Who:** Any role that received a notification  
**Steps:**
1. HOD/Captain sees notification in ledger panel
2. Click the notification
3. Should land on the exact handover export page

**Y/N checklist:**

| Check | Expected | If it fails |
|---|---|---|
| Critical item added → HOD gets notification | "Critical handover item added: {summary}" | `internal_dispatcher.py:828–854` fires for `chief_engineer/chief_officer/captain` on yacht |
| Handover submitted → HOD gets notification | "Handover {id} submitted and requires your countersignature" | `_notify_hod_for_countersign` at `handover_export_routes.py:1262` |
| Countersigned → Captain+Manager gets notification | "Handover countersigned and complete" | `handover_export_routes.py:894` |
| Click any notification → navigates to correct page | `/handover-export/{export_id}` | Every ledger row has `entity_id` + `entity_type` — 100% verified in DB |

**If navigation goes to wrong page:** Check `entity_id` on the `ledger_events` row in DB. If it's a `handover_item` ID but `entity_type` is `handover_export`, the route will 404. Known imperfection for `edit_draft_item` and `draft_item_deleted` events — does NOT affect the critical notification paths (submit, countersign, critical item).

---

## Scenario 9: Critical item — immediate HOD cascade

**Where:** Anywhere "Add to Handover" with category = "critical"  
**Who:** Any role adding the item  
**Steps:**
1. Add a handover item with category set to "critical"
2. HODs on the yacht get an immediate ledger notification

**Y/N checklist:**

| Check | Expected | If it fails |
|---|---|---|
| Add critical item → HODs notified within seconds | `ledger_events` rows with `action='critical_item_added'` | Check `internal_dispatcher.py:828` — queries `auth_users_roles` for `chief_engineer/chief_officer/captain`. If 0 users match, no cascade fires. |
| Notification says what was added | "Critical handover item added: {summary first 100 chars}" | `internal_dispatcher.py:849` |
| Notification carries entity_id | Clicking navigates to the item | `entity_id=handover_id` at `internal_dispatcher.py:845` |

---

## Limits and known gaps (honest)

| What | Status | Why |
|---|---|---|
| **Incoming crew acknowledgment (3rd sign)** | Not wired in UI | DB columns exist (`incoming_user_id`, `incoming_signed_at`). Backend route exists (`/sign/incoming`). No frontend button for it yet. |
| **PDF export** | `window.print()` only | Works but uses browser print dialog. No server-side PDF generation. WeasyPrint is installed in the microservice — could be wired. |
| **Vessel-level handover** | Not built | Only crew-level (scoped to one user's items). Vessel-level would pull all crew + certs + warranties. Separate scope. |
| **Incoming user selector** | Not built | When exporting, no dropdown to nominate the replacement crew member. Currently implicit. |
| **Cert/warranty auto-surfacing in Queue** | Not built | Queue only shows: Open Faults, Overdue WOs, Low Stock Parts, Pending POs. Expiring certs and open warranty claims not surfaced. |
| **Entity type mismatch on edit/delete events** | Known | `draft_item_deleted` and `edit_draft_item` write `entity_type='handover_export'` but carry a `handover_item` id. Not user-facing — audit trail only. |
| **crew role cannot sign** | By design | `sign_handover` requires HOD+ roles. A deckhand creates the handover but the HOD level signs it for quality gate. |
| **Signature block is static** | Known | Shows "Prepared By / Reviewed By" as static text. Not yet dynamic (SIGNED ✓ with timestamps). The data is there in the entity response (`user_signature`, `hod_signature`). |

---

## HMAC01 notes — what the receipt adapter needs

The handover domain adapter needs to provide answers to two questions:
1. **What records?** — `handover_exports` row + `handover_draft_sections` + `handover_draft_items` + both signatures
2. **Which ledger events?** — `export_ready_for_review`, `requires_countersignature`, `handover_countersigned`

The two shapes from the receipt layer spec:
- **single** — one handover export with both signatures and the deltas it covered. Triggered on countersign completion.
- **period** — a season's handovers as a bundle. Triggered on rotation or ownership change. Not yet implemented.

Current hash mechanism: `handover_exports.document_hash` — SHA-256 of rendered HTML. This needs to be replaced by the PAdES-B-LT + HMAC ref system from the universal envelope.

Ledger events already carry `proof_hash` (generated by `build_ledger_event` at `routes/handlers/ledger_utils.py:64–74`).

Reference docs:
- Handover domain README: `docs/explanations/LENS_DOMAINS/handover.md`
- Warranty domain README (adapter example): `docs/explanations/LENS_DOMAINS/warranty.md`
- Receipt layer spec: `/Users/celeste7/Downloads/celesteos-receipt-layer (2).html`

---

## Quick smoke test script

Run from terminal after setting credentials:

```bash
API="https://pipeline-core.int.celeste7.ai"
ANON="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw"

TOKEN=$(curl -s -X POST "https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON" -H "Content-Type: application/json" \
  -d '{"email":"x@alex-short.com","password":"Password2!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 1. Add note
curl -s -X POST "$API/v1/actions/execute" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"add_to_handover","context":{},"payload":{"entity_type":"note","summary":"Smoke test","category":"standard"}}' | python3 -m json.tool

# 2. List items
curl -s "$API/v1/handover/items" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'count={d[\"count\"]}')"

# 3. Fetch an export entity (replace ID)
curl -s "$API/v1/entity/handover_export/d885e181-de1e-4e6b-b79f-6c975073e2d6" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'sections={len(d.get(\"sections\",[]))} status={d.get(\"review_status\")}')"
```
