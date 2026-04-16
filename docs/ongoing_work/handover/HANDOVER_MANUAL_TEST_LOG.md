# Handover — Manual Test Log

**Tester:** ___________________  
**Date:** 2026-04-16  
**App URL:** https://app.celeste7.ai  
**Backend:** https://pipeline-core.int.celeste7.ai  
**Render commit:** `cb599501` (CORS fix #565 + all handover wiring deployed)

Fill in Y / N / ERR for each check. Paste console errors directly into the ERR cells or the notes section at the bottom of each scenario.

---

## Test credentials

| Role | Email | Password | DB role | Department |
|------|-------|----------|---------|------------|
| Crew | `crew.test@alex-short.com` | `Password2!` | crew | general |
| HOD (Chief Eng) | `hod.test@alex-short.com` | `Password2!` | chief_engineer | engineering |
| Captain | `captain.tenant@alex-short.com` | `Password2!` | captain | deck |
| Fleet Manager | `fleet-test-1775570624@celeste7.ai` | `Password2!` | manager (BROKEN — TENANT JWT, backend expects MASTER) | interior |

---

## Browser console setup

Open DevTools → Console before every scenario. Paste this to intercept API calls:

```javascript
const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const r = await _origFetch(...args);
  const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
  if (url.includes('/actions/execute') || url.includes('/v1/') || url.includes('/api/')) {
    const clone = r.clone();
    clone.json().then(d => console.log(`[API ${r.status}]`, url.split('/').slice(-3).join('/'), JSON.stringify(d).slice(0, 300))).catch(() => {});
  }
  return r;
};
```

---

## Fixed since last session (PRs #523–#565)

| Bug | Fix | PR |
|-----|-----|----|
| HandoverDraftPanel hitting MASTER DB for all CRUD | All 6 supabase calls replaced with Render API fetch() | #523 |
| `add_to_handover` category rejected `critical/standard/low` | category_map normalisation in dispatcher + handler | #523 |
| `crew` role blocked from adding items | Added `crew` to `allowed_roles` in registry | #523 |
| All ledger/audit gaps (edit, delete, sign, countersign) | `_write_handover_event` + `_get_role_users` helpers, cascade on every mutation | #525 |
| `_notify_hod_for_countersign` queried wrong table (`auth_users_profiles.role` doesn't exist) | Fixed to `auth_users_roles` | #525 |
| Countersign role check `"hod"` is not a real DB role | Changed to `["chief_engineer", "chief_officer", "captain", "manager"]` | #527 |
| Entity handler returned empty sections (document showed "No handover content available") | Fallback to `v_handover_draft_complete` joined on `draft_id` | #549 |
| Sign button misconfigured — wrong action ID, missing export_id | Rewired to direct `/submit` and `/countersign` HTTP routes | #549 |
| `microactions/handlers/handover.ts` + `useNeedsAttention.ts` hitting MASTER | Routed through Render API | #529 |
| Hardcoded rgba/hex in HandoverDraftPanel + HandoverQueueView | Replaced with design tokens from tokens.css | #530 |
| CORS: PATCH/DELETE blocked by `allow_methods` | Added PATCH/PUT/DELETE to CORS config | #565 |
| Playwright shard-49 timeout (15s vs 120s LLM pipeline) | Per-shard timeout override to 180s | #535 |

---

## Role matrix (who can do what)

| Action | crew | chief_engineer | captain | manager |
|--------|------|----------------|---------|---------|
| View Queue tab | Y | Y | Y | Y |
| + Add from Queue | Y | Y | Y | Y |
| View Draft Items | Y (own only) | Y (own only) | Y (own only) | Y (own only) |
| Edit draft item | Y (own only) | Y (own only) | Y (own only) | Y (own only) |
| Delete draft item | Y (own only) | Y (own only) | Y (own only) | Y (own only) |
| Add Note | Y | Y | Y | Y |
| Add from entity lens | Y | Y | Y | Y |
| Export handover | Y | Y | Y | Y |
| Sign outgoing (submit) | N | Y | Y | Y |
| Countersign (HOD) | N | Y | Y | Y |
| Receive critical cascade | N | Y | Y | N |
| Receive countersign cascade | N | N | Y | Y |

---

## Limits

| Constraint | Value |
|-----------|-------|
| Summary min length | 3 characters |
| Summary max length | 2000 characters |
| LLM export timeout | Up to 120s (GPT-4o-mini pipeline) |
| CORS allowed methods | GET, POST, PATCH, PUT, DELETE, OPTIONS |
| Draft item ownership | `added_by = user_id` — only creator can edit/delete |
| Export sections shape | `{id, title, content, items[], is_critical, order}` — pydantic `Section` model |
| Signature payload | `{image_base64, signed_at, signer_name, signer_id}` — pydantic `SignatureData` model |
| Delete = soft delete | Sets `deleted_at`, never removes row |
| `handover_entries` | Immutable — no DELETE policy, cannot be removed |
| Max queue items | 200 per fetch |

---

## Pre-flight

| # | Check | Result | Console / Notes |
|---|-------|--------|-----------------|
| P1 | App loads at `app.celeste7.ai` — no blank screen | | |
| P2 | Log in as **crew** (`crew.test@alex-short.com` / `Password2!`) — lands on dashboard | | |
| P3 | Sidebar shows **Handover** link under OPERATIONS | | |
| P4 | Open DevTools → Console tab. No red errors on load | | |
| P5 | No `400` from `qvzmkaamzaqxpzbewjxe.supabase.co` in console (MASTER DB error) | | If present: `useNeedsAttention.ts` still hitting MASTER |

---

## Scenario 1 — Crew views handover queue

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 1.1 | Click **Handover** in sidebar | Sidebar nav, OPERATIONS section | `/handover-export` loads, two tabs visible | | |
| 1.2 | Queue tab active by default | Tab bar | "Queue" has teal underline | | |
| 1.3 | Header shows stats | Below tab bar | "Handover Queue — N items detected · M added to draft" | | |
| 1.4 | **Open Faults** section | Expandable, red icon | Count badge, expand shows items or "No items" | | |
| 1.5 | **Overdue Work Orders** section | Expandable, amber icon | Same pattern | | |
| 1.6 | **Low Stock Parts** section | Expandable, teal icon | Items show: name + "N on hand · min N" meta | | |
| 1.7 | **Pending Purchase Orders** section | Expandable, grey icon | Same pattern | | |
| 1.8 | **Refresh** button | Top-right | Spinner, counts may update | | |

**Notes / errors for Scenario 1:**
```

```

---

## Scenario 2 — Crew adds item from queue

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 2.1 | Expand Low Stock Parts | Click section header | Items list expands | | |
| 2.2 | Click **+ Add** on any item | Right side of item row | Button flips to **✓ Added** (teal bg) | | |
| 2.3 | Counter updates | Header stats | "M added to draft" increases by 1 | | |
| 2.4 | Add a second item | Different row | Same flip | | |
| 2.5 | Reload page | F5 / Cmd+R | Previously-added items show ✓ Added (not + Add) | | |

**Edge case — click + Add twice rapidly:**
| 2.6 | Double-click + Add | Same row | Should not create duplicate. Button disabled during request. | | |

**Notes / errors for Scenario 2:**
```

```

---

## Scenario 3 — Crew views draft items

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 3.1 | Click **Draft Items** tab | Tab bar | Panel loads | | |
| 3.2 | Header: "My Handover Draft" | Top of panel | Shows "N items · crew" | | |
| 3.3 | Items visible (NOT empty) | Item list area | Grouped by day, Today expanded | | |
| 3.4 | Each item has icon + summary | Item row | Entity type icon (⚠ fault, 🔧 WO, 📦 part) + text | | |
| 3.5 | **Export Handover** button visible | Bottom area | Teal-outlined | | |
| 3.6 | **+ Add Note** button visible | Next to Export | Secondary style | | |

**If "0 items" but Queue says "N added to draft":**
- Console → check `GET` request to `/v1/handover/items`
- If `400` from `qvzmkaamzaqxpzbewjxe` → MASTER DB bug
- If `200` with `items: []` → `added_by` mismatch (different user ID)
- If CORS error → PATCH/DELETE may fail later too (PR #565 not deployed)

**Notes / errors for Scenario 3:**
```

```

---

## Scenario 4 — Crew edits a draft item

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 4.1 | Click any item in Draft list | Item row | Edit popup opens | | |
| 4.2 | **Summary** textarea pre-filled | Popup body | Shows current summary text, not blank | | |
| 4.3 | **Category** dropdown works | Select field | Options: Critical, Standard, Low | | |
| 4.4 | **Status** radio buttons | Radio group | On Going / Not Started / Requires Parts | | |
| 4.5 | **Section** dropdown (Add Note only) | Select field | Engineering / Deck / Interior / Command | | |
| 4.6 | Change summary → click **Save Changes** | Primary button | Popup closes, toast "Handover note updated" | | |
| 4.7 | List reflects changed summary | Item row | New text visible | | |

**Edge case — CORS on PATCH:**
| 4.8 | Console shows no CORS error on `PATCH` to `pipeline-core.int.celeste7.ai` | Network tab | 200 response, no `Access-Control` block | | If blocked: PR #565 not deployed |

**Edge case — edit someone else's item:**
| 4.9 | HOD cannot edit crew's item | Login as HOD, navigate to Draft Items | HOD sees their OWN items only (different `added_by`) — crew's items don't appear | | |

**Notes / errors for Scenario 4:**
```

```

---

## Scenario 5 — Crew deletes a draft item

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 5.1 | Click item → popup → click **Delete** | Red text, bottom-right of popup footer | Confirmation popup: trash icon + "Delete this handover note?" | | |
| 5.2 | Message says source entity unaffected | Confirmation body | "The source Fault will not be affected" (for entity-linked items) | | |
| 5.3 | Click **Delete Note** | Red button in confirmation | Popup closes, toast "Handover note deleted" | | |
| 5.4 | Item gone from list | Item list | Disappeared, count decreased | | |
| 5.5 | Reload → item stays gone | F5 | Does not reappear (soft-deleted in DB) | | |

**Edge case — CORS on DELETE:**
| 5.6 | Console shows no CORS error on `DELETE` | Network tab | 200 response | | If blocked: PR #565 not deployed |

**Notes / errors for Scenario 5:**
```

```

---

## Scenario 6 — Crew adds standalone note

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 6.1 | Click **+ Add Note** | Draft Items tab | Modal opens with BLANK fields | | |
| 6.2 | Type summary (min 3 chars) | Textarea | "Engine room bilge check before departure" | | |
| 6.3 | Select Category: **Critical** | Dropdown | Selected | | |
| 6.4 | Select Section: **Engineering** | Dropdown | Options: Engineering, Deck, Interior, Command | | |
| 6.5 | Click **Add to Handover** | Primary button | Modal closes, toast "Handover note added" | | |
| 6.6 | Note appears under "Today" | Draft list | Your typed summary visible | | |

**Edge case — empty summary:**
| 6.7 | Leave summary blank → click Add | Primary button | Error toast "summary must be at least 3 characters" or validation blocks | | |

**Edge case — 2-char summary:**
| 6.8 | Type "OK" (2 chars) → submit | Primary button | Should be rejected (min 3) | | |

**Notes / errors for Scenario 6:**
```

```

---

## Scenario 7 — Add to Handover from entity lens

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 7.1 | Sidebar → **Faults** → click any fault | Fault detail lens | IdentityStrip + sections load | | |
| 7.2 | Click action dropdown (SplitButton or "..." menu) | Top-right of lens | Dropdown list of available actions | | |
| 7.3 | **Add to Handover** in dropdown | Action list | Present, not greyed out | | |
| 7.4 | Click it | Dropdown item | Toast confirmation, item queued | | |
| 7.5 | Navigate to `/handover-export` → Draft Items | Sidebar → Handover | Fault appears in draft | | |

**Check each entity type:**

| Entity | Sidebar link | "Add to Handover" visible? | Click works? | Notes |
|--------|-------------|---------------------------|-------------|-------|
| Fault | Faults | | | |
| Work Order | Work Orders | | | |
| Equipment | Equipment | | | |
| Part / Inventory | Parts / Inventory | | | |
| Certificate | Certificates | | | |

**Notes / errors for Scenario 7:**
```

```

---

## Scenario 8 — View generated handover document

**Switch to:** `captain.tenant@alex-short.com` / `Password2!`  
**Navigate to:** `app.celeste7.ai/handover-export/d885e181-de1e-4e6b-b79f-6c975073e2d6`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 8.1 | Page loads | URL bar | No blank page, no spinner stuck | | |
| 8.2 | IdentityStrip shows | Top of page | Title, status pill, department | | |
| 8.3 | **"Technical Handover Report"** header | White document block | Vessel name, doc number THR-NNNN, date | | |
| 8.4 | **Table of Contents** | Below header | Departments listed with item counts (e.g., "Deck (4 items)") | | |
| 8.5 | **Department sections** render | Below TOC | Teal left border, section title, numbered items | | |
| 8.6 | **Item content** is LLM text | Item body | "You need to..." professional language | | |
| 8.7 | **Entity links** visible | Below items | "View Fault →" / "View Work Order →" in teal | | |
| 8.8 | **Clicking entity link** navigates | Link click | Opens the source fault/WO/equipment page | | |
| 8.9 | **Signature block** at bottom | End of document | "Prepared By" / "Reviewed By" two columns | | |
| 8.10 | **NOT** "No handover content available" | Document area | Real sections, not empty message | | |

**If "No handover content available":**
- Console → `GET /v1/entity/handover_export/{id}`
- Check `sections` in response — should be array with items
- If `sections: []` → `entity_routes.py:624` fallback failed — `draft_id` might be NULL

**Notes / errors for Scenario 8:**
```

```

---

## Scenario 9 — Sign handover (outgoing user)

**Login:** `captain.tenant@alex-short.com` / `Password2!`  
**Requires:** Export with `review_status = pending_review`.  
If none available, paste "need pending_review export reset" in notes.

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 9.1 | **Sign Handover** button visible | IdentityStrip top-right | Shield icon + "Sign Handover" | | |
| 9.2 | Click → **canvas modal** opens | Modal overlay | White 416×160 canvas, instruction text | | |
| 9.3 | **Draw** with mouse | Canvas area | Black ink follows mouse, smooth strokes | | |
| 9.4 | **Clear** resets canvas | Bottom-left button | Canvas goes white | | |
| 9.5 | **Cancel** closes modal | Bottom-right | No state change, no toast | | |
| 9.6 | Draw → **Confirm & Sign** | Blue button | Toast: "Handover signed — HOD notified for countersignature" | | |
| 9.7 | Status pill changes | IdentityStrip | "Pending Review" → "Pending Hod Signature" | | |
| 9.8 | Sign button disappears | IdentityStrip | Gone — replaced by Export PDF or Countersign | | |

**Edge case — crew tries to sign:**
| 9.9 | Log in as crew → same page | Different role | **No** "Sign Handover" button visible at all | | |

**Edge case — sign already-signed export:**
| 9.10 | Reload page after signing | Same URL | Status is "Pending Hod Signature", no sign button | | |

**Where the signature popup appears:**
- ONLY on `/handover-export/{id}` page, inside `HandoverContent.tsx`
- The IdentityStrip's `SplitButton` opens it
- Does NOT appear on the draft panel, queue tab, or any entity lens
- Modal is center-screen with dark backdrop (40% opacity)

**Notes / errors for Scenario 9:**
```

```

---

## Scenario 10 — Countersign (HOD reviews and signs)

**Login:** `captain.tenant@alex-short.com` / `Password2!` (or `hod.test@alex-short.com`)  
**Requires:** Same export from Scenario 9 in `pending_hod_signature` state.

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 10.1 | Button reads **Countersign Handover** | IdentityStrip | Different label from "Sign Handover" | | |
| 10.2 | Click → canvas modal | Modal | Same canvas, DIFFERENT instruction text | | |
| 10.3 | Modal says **"countersign and complete"** | Modal body | Not "submit this handover" | | |
| 10.4 | Draw + **Confirm & Sign** | Blue button | Toast: "Handover countersigned — rotation complete" | | |
| 10.5 | Status → **Complete** (green pill) | IdentityStrip | Green | | |
| 10.6 | **No more action buttons** | IdentityStrip | Read-only. No sign, no countersign. | | |

**Edge case — crew tries to countersign:**
| 10.7 | Log in as crew → same page (pending_hod_signature) | Different role | No countersign button visible | | |

**Edge case — countersign on wrong state:**
| 10.8 | Countersign on `pending_review` (not yet submitted) | API call | 400 "Not awaiting countersign" | | |

**Notes / errors for Scenario 10:**
```

```

---

## Scenario 11 — Export PDF

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 11.1 | Click dropdown on action button | SplitButton arrow | Dropdown opens | | |
| 11.2 | Click **Export PDF** | Dropdown item | Browser print dialog (`window.print()`) | | |
| 11.3 | Print preview | Print dialog | A4 layout, document visible, not blank | | |

**Notes / errors for Scenario 11:**
```

```

---

## Scenario 12 — Signature popup visibility rules

Which actions show a popup and which fire directly?

| # | Action | Login as | Expected behaviour | Y / N / ERR | Console errors |
|---|--------|----------|-------------------|-------------|----------------|
| 12.1 | + Add from Queue | crew | **No popup** — fires directly, toast confirms | | |
| 12.2 | Add Note | crew | **Popup** — form with summary/category/section fields | | |
| 12.3 | Edit draft item | crew | **Popup** — edit form with pre-filled fields | | |
| 12.4 | Delete draft item | crew | **Popup** — confirmation "Delete this handover note?" | | |
| 12.5 | Export Handover | crew | **No popup** — loading state, then toast + redirect | | |
| 12.6 | Sign Handover | captain | **Canvas popup** — draw signature, Confirm & Sign | | |
| 12.7 | Countersign | captain | **Canvas popup** — same canvas, different text | | |
| 12.8 | Export PDF | any | **No popup** — browser print dialog | | |

**Notes / errors for Scenario 12:**
```

```

---

## DB / Ledger spot check (run after Scenarios 2-10)

```bash
# Acquire captain token
TOKEN=$(curl -s -X POST "https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw" \
  -H "Content-Type: application/json" \
  -d '{"email":"captain.tenant@alex-short.com","password":"Password2!"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# Check handover items for this user
curl -s "https://pipeline-core.int.celeste7.ai/v1/handover/items" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'count={d[\"count\"]}')"

# Check ledger events for all handover actions
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT action, count(*), max(created_at)::date FROM ledger_events WHERE action IN ('critical_item_added','edit_draft_item','draft_item_deleted','requires_countersignature','handover_countersigned','save_draft_edits') GROUP BY action ORDER BY action;"

# Check a specific export
EXPORT_ID="d885e181-de1e-4e6b-b79f-6c975073e2d6"
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT review_status, user_signed_at IS NOT NULL as user_signed, hod_signed_at IS NOT NULL as hod_signed, signed_storage_url IS NOT NULL as has_signed_url FROM handover_exports WHERE id='$EXPORT_ID';"
```

| # | DB check | Expected | Y / N / ERR |
|---|----------|----------|-------------|
| DB1 | `handover_items` count > 0 for captain | Items exist | |
| DB2 | `ledger_events` has `critical_item_added` rows | Present after adding critical item | |
| DB3 | `ledger_events` has `requires_countersignature` rows | Present after submit/sign | |
| DB4 | `ledger_events` has `handover_countersigned` rows | Present after countersign | |
| DB5 | Export row has `user_signed_at` + `hod_signed_at` | Both NOT NULL after full lifecycle | |
| DB6 | `signed_storage_url` is NOT NULL | Signed HTML uploaded to storage | |

---

## HMAC01 notes (receipt-layer integration)

| # | What HMAC01 needs to know |
|---|--------------------------|
| H1 | Ledger `entity_type` = `handover_export` or `handover_item`, `entity_id` = UUID |
| H2 | Key actions: `add_to_handover`, `edit_draft_item`, `draft_item_deleted`, `items_marked_exported`, `save_draft_edits`, `requires_countersignature`, `handover_countersigned`, `critical_item_added` |
| H3 | `proof_hash` generated by `routes/handlers/ledger_utils.py:64-74` — SHA-256 |
| H4 | Primary tables: `handover_items` (draft), `handover_exports` (generated doc), `handover_drafts` + `handover_draft_sections` + `handover_draft_items` (LLM output) |
| H5 | Signed actions: submit + countersign carry signature payload `{image_base64, signed_at, signer_name, signer_id}` |
| H6 | Receipt shapes: **single** = one handover export with both signatures. **period** = season's handovers as bundle (not yet built). |
| H7 | Current hash: `handover_exports.document_hash` = SHA-256 of rendered HTML. Needs PAdES-B-LT + HMAC ref replacement. |
| H8 | Storage: bucket `handover-exports`, paths `{yacht_id}/original/{draft_id}_{ts}.html` and `{yacht_id}/signed/{export_id}.html` |
| H9 | `handover_entries` has no DELETE policy — immutable truth seeds. Perfect for receipt integrity. |
| H10 | No raw UUIDs in sealed PDFs — use HMAC refs per CLAUDE.md rule |

---

## Known gaps (honest)

| Gap | Impact | Notes |
|-----|--------|-------|
| Incoming crew acknowledgment (3rd sign) | No "received" confirmation from replacement | DB columns + backend route exist, no UI button |
| PDF export = `window.print()` | Browser-native, no server PDF | WeasyPrint in microservice could be wired |
| Vessel-level handover | Not built | Only crew-level (one user's items) |
| Incoming user selector | Not built | No dropdown to nominate replacement at export time |
| Cert/warranty auto-surface in Queue | Not built | Queue only shows faults/WOs/parts/POs |
| Signature block is static | No SIGNED ✓ timestamps | Data exists in entity response but not rendered dynamically |
| `edit_draft_item` entity_type mismatch | Audit row says `handover_export` but carries `handover_item` id | Navigation from ledger panel may 404 for this event type only |
| Manager test account broken | TENANT JWT, backend expects MASTER | Test infra gap — needs MASTER-registered manager user |

---

## Overall verdict

| Area | Result | Blocking? | Notes |
|------|--------|-----------|-------|
| Pre-flight | | | |
| Queue loads | | | |
| + Add from Queue | | | |
| Draft Items — view | | | |
| Draft Items — edit (PATCH) | | | |
| Draft Items — delete (DELETE) | | | |
| Draft Items — add note | | | |
| Add from Fault lens | | | |
| Add from WO lens | | | |
| Add from Equipment lens | | | |
| Add from Part lens | | | |
| Add from Certificate lens | | | |
| Document renders (sections) | | | |
| Sign outgoing (canvas) | | | |
| Countersign (HOD canvas) | | | |
| PDF export | | | |
| Signature popup rules | | | |

---

## All console errors (paste everything)

```

```

## Questions for HANDOVER01

```

```
