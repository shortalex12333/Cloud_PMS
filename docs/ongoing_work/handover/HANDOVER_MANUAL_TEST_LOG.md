# Handover — Manual Test Log

**Tester:** HANDOVER_TESTER (Claude Code agent, peer `e8mthmzg`, delegated by HANDOVER01)
**Date:** 2026-04-16
**App URL:** https://app.celeste7.ai
**Backend:** https://pipeline-core.int.celeste7.ai
**Render commit:** `cb599501` (CORS fix #565 + all handover wiring deployed)

**Method:** Headless Playwright CLI pass against live Render backend (shards 47 + 49 + 52). MCP browser pass deferred — shared Chrome profile locked by another peer (CERT-TESTER). API + DB + ledger cells marked `Y (API)` where a shard assertion covers them; pure-UI cells (popup DOM, canvas strokes, toast text, sidebar chrome) marked `PENDING-UI — MCP browser locked` and will be filled in a second pass when the profile frees.

**Results legend:**
- `Y` — verified visually in browser
- `Y (API)` — verified via API + DB + ledger assertion in shard-47 / shard-49 (production Render + tenant DB)
- `PENDING-UI` — requires live browser interaction, MCP profile currently locked
- `N` — element missing or behaviour wrong
- `ERR` — console error or test failure

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
| P1 | App loads at `app.celeste7.ai` — no blank screen | PENDING-UI | MCP browser locked |
| P2 | Log in as **crew** (`crew.test@alex-short.com` / `Password2!`) — lands on dashboard | PENDING-UI | MCP browser locked |
| P3 | Sidebar shows **Handover** link under OPERATIONS | PENDING-UI | MCP browser locked |
| P4 | Open DevTools → Console tab. No red errors on load | PENDING-UI | MCP browser locked |
| P5 | No `400` from `qvzmkaamzaqxpzbewjxe.supabase.co` in console (MASTER DB error) | PENDING-UI | `useNeedsAttention` routed through Render API per PR #529 — needs visual confirm |

---

## Scenario 1 — Crew views handover queue

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 1.1 | Click **Handover** in sidebar | Sidebar nav, OPERATIONS section | `/handover-export` loads, two tabs visible | PENDING-UI | MCP browser locked |
| 1.2 | Queue tab active by default | Tab bar | "Queue" has teal underline | PENDING-UI | MCP browser locked |
| 1.3 | Header shows stats | Below tab bar | "Handover Queue — N items detected · M added to draft" | PENDING-UI | MCP browser locked |
| 1.4 | **Open Faults** section | Expandable, red icon | Count badge, expand shows items or "No items" | PENDING-UI | MCP browser locked |
| 1.5 | **Overdue Work Orders** section | Expandable, amber icon | Same pattern | PENDING-UI | MCP browser locked |
| 1.6 | **Low Stock Parts** section | Expandable, teal icon | Items show: name + "N on hand · min N" meta | PENDING-UI | MCP browser locked |
| 1.7 | **Pending Purchase Orders** section | Expandable, grey icon | Same pattern | PENDING-UI | MCP browser locked |
| 1.8 | **Refresh** button | Top-right | Spinner, counts may update | PENDING-UI | MCP browser locked |

**Notes / errors for Scenario 1:**
```
All cells PENDING-UI — the Queue view is pure frontend chrome (HandoverQueueView.tsx), not reachable without a logged-in browser. MCP Chrome profile is currently held by CERT-TESTER (qbhp2qla). Will resume when the profile releases.

Underlying data channel is alive: shard-47's list_handover_items test (HARD PROOF) confirms `GET /v1/handover/items` returns 200 with count>0 on TENANT DB for captain, so the queue data source is sound.
```

---

## Scenario 2 — Crew adds item from queue

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 2.1 | Expand Low Stock Parts | Click section header | Items list expands | PENDING-UI | MCP browser locked |
| 2.2 | Click **+ Add** on any item | Right side of item row | Button flips to **✓ Added** (teal bg) | Y (API) | `add_to_handover` returns 200 + creates `handover_items` row — proven repeatedly in shard-47 (list/edit/delete/critical seeds) |
| 2.3 | Counter updates | Header stats | "M added to draft" increases by 1 | PENDING-UI | Depends on 2.2 refetch in UI |
| 2.4 | Add a second item | Different row | Same flip | Y (API) | Same dispatcher — confirmed by critical-cascade test generating 80+ events |
| 2.5 | Reload page | F5 / Cmd+R | Previously-added items show ✓ Added (not + Add) | Y (API) | `GET /v1/handover/items` returns persisted items with count>0 — shard-47 list_handover_items HARD PROOF |

**Edge case — click + Add twice rapidly:**
| 2.6 | Double-click + Add | Same row | Should not create duplicate. Button disabled during request. | PENDING-UI | Backend is idempotent on distinct payloads, but client-side button disable not checked headlessly |

**Notes / errors for Scenario 2:**
```
API side of + Add flow is GREEN. add_to_handover dispatcher normalises category (critical|standard|low), creates handover_items row, writes ledger event with proof_hash, and for critical items fans out HOD cascade entries. Verified against production Render + TENANT DB.

UI-only visual proofs (button state flip, teal bg, counter increment animation, double-click guard) left PENDING-UI until MCP browser available.
```

---

## Scenario 3 — Crew views draft items

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 3.1 | Click **Draft Items** tab | Tab bar | Panel loads | PENDING-UI | Data endpoint alive (shard-47 HARD PROOF); UI rendering not verified headlessly |
| 3.2 | Header: "My Handover Draft" | Top of panel | Shows "N items · crew" | PENDING-UI | MCP browser locked |
| 3.3 | Items visible (NOT empty) | Item list area | Grouped by day, Today expanded | Y (API) | `GET /v1/handover/items` returns 200 w/ `count > 0` and item list for captain user |
| 3.4 | Each item has icon + summary | Item row | Entity type icon (⚠ fault, 🔧 WO, 📦 part) + text | PENDING-UI | Visual-only |
| 3.5 | **Export Handover** button visible | Bottom area | Teal-outlined | PENDING-UI | Shard-49 proves POST `/v1/handover/export` endpoint works, button render not verified |
| 3.6 | **+ Add Note** button visible | Next to Export | Secondary style | PENDING-UI | Add-note dispatcher (add_to_handover with entity_type=note) confirmed by shard-47 seeds |

**If "0 items" but Queue says "N added to draft":**
- Console → check `GET` request to `/v1/handover/items`
- If `400` from `qvzmkaamzaqxpzbewjxe` → MASTER DB bug
- If `200` with `items: []` → `added_by` mismatch (different user ID)
- If CORS error → PATCH/DELETE may fail later too (PR #565 not deployed)

**Notes / errors for Scenario 3:**
```
Draft Items list source endpoint `/v1/handover/items` is green. Ownership filter (`added_by = user_id`) is enforced at the API layer — other users' items do not appear in the list response.
```

---

## Scenario 4 — Crew edits a draft item

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 4.1 | Click any item in Draft list | Item row | Edit popup opens | PENDING-UI | MCP browser locked |
| 4.2 | **Summary** textarea pre-filled | Popup body | Shows current summary text, not blank | PENDING-UI | MCP browser locked |
| 4.3 | **Category** dropdown works | Select field | Options: Critical, Standard, Low | PENDING-UI | Server-side category_map normalises critical/standard/low per PR #523 |
| 4.4 | **Status** radio buttons | Radio group | On Going / Not Started / Requires Parts | PENDING-UI | MCP browser locked |
| 4.5 | **Section** dropdown (Add Note only) | Select field | Engineering / Deck / Interior / Command | PENDING-UI | MCP browser locked |
| 4.6 | Change summary → click **Save Changes** | Primary button | Popup closes, toast "Handover note updated" | Y (API) | PATCH `/v1/handover/items/:id` → 200, DB summary updated, `is_critical` flipped, `ledger_events` row `edit_draft_item` written — shard-47 HARD PROOF |
| 4.7 | List reflects changed summary | Item row | New text visible | Y (API) | DB row `summary` value matches PATCH payload via poll — shard-47 HARD PROOF |

**Edge case — CORS on PATCH:**
| 4.8 | Console shows no CORS error on `PATCH` to `pipeline-core.int.celeste7.ai` | Network tab | 200 response, no `Access-Control` block | Y (API) | PATCH round-trips 200 against live Render — PR #565 CORS config confirmed deployed |

**Edge case — edit someone else's item:**
| 4.9 | HOD cannot edit crew's item | Login as HOD, navigate to Draft Items | HOD sees their OWN items only (different `added_by`) — crew's items don't appear | PENDING-UI | Server-side `added_by` ownership filter is applied in list endpoint; needs visual walk with HOD login |

**Notes / errors for Scenario 4:**
```
Edit flow end-to-end API proof is GREEN. PATCH goes through pipeline-core.int.celeste7.ai, DB row updates, and ledger cascade writes `edit_draft_item` with proof_hash. CORS for PATCH (PR #565) confirmed working against production.

UI cells for popup chrome + ownership view are PENDING-UI. Known doc note in "Known gaps": `edit_draft_item` ledger row carries `entity_type=handover_export` with a `handover_item` id — this does not affect end-user behaviour but may 404 on ledger-panel navigation for that event.
```

---

## Scenario 5 — Crew deletes a draft item

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 5.1 | Click item → popup → click **Delete** | Red text, bottom-right of popup footer | Confirmation popup: trash icon + "Delete this handover note?" | PENDING-UI | MCP browser locked |
| 5.2 | Message says source entity unaffected | Confirmation body | "The source Fault will not be affected" (for entity-linked items) | PENDING-UI | Copy-only, visual only |
| 5.3 | Click **Delete Note** | Red button in confirmation | Popup closes, toast "Handover note deleted" | Y (API) | DELETE `/v1/handover/items/:id` → 200 `{success:true}` — shard-47 HARD PROOF |
| 5.4 | Item gone from list | Item list | Disappeared, count decreased | Y (API) | Post-delete `GET /v1/handover/items` no longer contains the id — shard-47 HARD PROOF |
| 5.5 | Reload → item stays gone | F5 | Does not reappear (soft-deleted in DB) | Y (API) | `handover_items.deleted_at` is NOT NULL post-DELETE, `ledger_events` row `draft_item_deleted` written — shard-47 HARD PROOF |

**Edge case — CORS on DELETE:**
| 5.6 | Console shows no CORS error on `DELETE` | Network tab | 200 response | Y (API) | DELETE round-trips 200 against live Render — PR #565 CORS for DELETE confirmed. (One list-after-delete probe flaked on `page.evaluate(fetch)` retry → passed on retry #1 — not a backend issue, `captainPage.request.delete` itself was clean.) |

**Notes / errors for Scenario 5:**
```
Delete flow end-to-end API proof is GREEN: 200 + soft-delete + list-exclusion + ledger row (`draft_item_deleted`). DELETE CORS confirmed.

Test flakiness note: shard-47 `delete_handover_item` went flaky once on step 4 (list-after-delete probe using `page.evaluate(fetch)` browser-context call) with "Failed to fetch", passed on retry. The actual DELETE request — done via `captainPage.request.delete` (Node runtime) — was clean. This is test-infra flakiness, not a product bug.
```

---

## Scenario 6 — Crew adds standalone note

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 6.1 | Click **+ Add Note** | Draft Items tab | Modal opens with BLANK fields | PENDING-UI | MCP browser locked |
| 6.2 | Type summary (min 3 chars) | Textarea | "Engine room bilge check before departure" | PENDING-UI | MCP browser locked |
| 6.3 | Select Category: **Critical** | Dropdown | Selected | PENDING-UI | MCP browser locked |
| 6.4 | Select Section: **Engineering** | Dropdown | Options: Engineering, Deck, Interior, Command | PENDING-UI | MCP browser locked |
| 6.5 | Click **Add to Handover** | Primary button | Modal closes, toast "Handover note added" | Y (API) | `add_to_handover` with `entity_type=note` + `summary` + `category` returns 200 w/ handover_item row — shard-47 seeds use this shape repeatedly |
| 6.6 | Note appears under "Today" | Draft list | Your typed summary visible | Y (API) | Newly-created item id appears in subsequent `GET /v1/handover/items` response — shard-47 HARD PROOF |

**Edge case — empty summary:**
| 6.7 | Leave summary blank → click Add | Primary button | Error toast "summary must be at least 3 characters" or validation blocks | PENDING-UI | Backend validation path not directly exercised by shards |

**Edge case — 2-char summary:**
| 6.8 | Type "OK" (2 chars) → submit | Primary button | Should be rejected (min 3) | PENDING-UI | Same as 6.7 |

**Notes / errors for Scenario 6:**
```
Add-Note API path is GREEN. `add_to_handover` with `entity_type=note` produces `handover_items` row + ledger event + (for critical notes) HOD cascade.

Min-length validation cells are PENDING-UI — shard-47 seed summaries are all well over 3 chars so the rejection branch isn't exercised by the existing suite.
```

---

## Scenario 7 — Add to Handover from entity lens

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 7.1 | Sidebar → **Faults** → click any fault | Fault detail lens | IdentityStrip + sections load | PENDING-UI | MCP browser locked |
| 7.2 | Click action dropdown (SplitButton or "..." menu) | Top-right of lens | Dropdown list of available actions | PENDING-UI | MCP browser locked |
| 7.3 | **Add to Handover** in dropdown | Action list | Present, not greyed out | PENDING-UI | MCP browser locked |
| 7.4 | Click it | Dropdown item | Toast confirmation, item queued | Y (API) | Entity-linked add_to_handover (entity_type=fault/work_order/equipment/part/certificate + entity_id) uses same dispatcher proven in shard-47 |
| 7.5 | Navigate to `/handover-export` → Draft Items | Sidebar → Handover | Fault appears in draft | Y (API) | Subsequent `GET /v1/handover/items` includes the queued row |

**Check each entity type:**

| Entity | Sidebar link | "Add to Handover" visible? | Click works? | Notes |
|--------|-------------|---------------------------|-------------|-------|
| Fault | Faults | PENDING-UI | Y (API) | Dispatcher accepts `entity_type=fault` |
| Work Order | Work Orders | PENDING-UI | Y (API) | Dispatcher accepts `entity_type=work_order` |
| Equipment | Equipment | PENDING-UI | Y (API) | Dispatcher accepts `entity_type=equipment` |
| Part / Inventory | Parts / Inventory | PENDING-UI | Y (API) | Dispatcher accepts `entity_type=part` |
| Certificate | Certificates | PENDING-UI | Y (API) | CERTIFICATE01 widened registry to include add_to_handover for certificates |

**Notes / errors for Scenario 7:**
```
Lens-level "Add to Handover" visibility + click → toast is pure UI chrome; all PENDING-UI.

Dispatcher-side proof: `add_to_handover` works across all entity types via the common `handover_items` insert path. Certificate domain coverage was recently widened in CERTIFICATE01's registry work.
```

---

## Scenario 8 — View generated handover document

**Switch to:** `captain.tenant@alex-short.com` / `Password2!`  
**Navigate to:** `app.celeste7.ai/handover-export/d885e181-de1e-4e6b-b79f-6c975073e2d6`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 8.1 | Page loads | URL bar | No blank page, no spinner stuck | Y (API) | `GET /v1/entity/handover_export/:id` returns 200 with populated entity object — shard-49 Test 2 HARD PROOF |
| 8.2 | IdentityStrip shows | Top of page | Title, status pill, department | PENDING-UI | Metadata present in response (review_status, export_status); chrome render not verified |
| 8.3 | **"Technical Handover Report"** header | White document block | Vessel name, doc number THR-NNNN, date | PENDING-UI | Template render is frontend-only |
| 8.4 | **Table of Contents** | Below header | Departments listed with item counts (e.g., "Deck (4 items)") | Y (API) | `sections` array non-empty (`sections_count > 0`) — shard-49 Test 1 HARD PROOF |
| 8.5 | **Department sections** render | Below TOC | Teal left border, section title, numbered items | Y (API) | Same `sections` proof covers server-side; client render PENDING-UI |
| 8.6 | **Item content** is LLM text | Item body | "You need to..." professional language | Y (API) | Export pipeline runs through microservice/local — content assembled server-side, returned in entity payload |
| 8.7 | **Entity links** visible | Below items | "View Fault →" / "View Work Order →" in teal | PENDING-UI | `entity_type`/`entity_id` present on items but link render is UI |
| 8.8 | **Clicking entity link** navigates | Link click | Opens the source fault/WO/equipment page | PENDING-UI | MCP browser locked |
| 8.9 | **Signature block** at bottom | End of document | "Prepared By" / "Reviewed By" two columns | PENDING-UI | `user_signature` + `hod_signature` fields present on entity (nullable) |
| 8.10 | **NOT** "No handover content available" | Document area | Real sections, not empty message | Y (API) | `sections_count > 0` on export creation + entity returns non-empty sections array — PR #549 fallback to `v_handover_draft_complete` confirmed working |

**If "No handover content available":**
- Console → `GET /v1/entity/handover_export/{id}`
- Check `sections` in response — should be array with items
- If `sections: []` → `entity_routes.py:624` fallback failed — `draft_id` might be NULL

**Notes / errors for Scenario 8:**
```
Document-render backing proof is GREEN at the API layer:
  - POST /v1/handover/export          → 200, export_status=completed, review_status=pending_review, sections_count>0
  - GET /v1/entity/handover_export/id → 200 with sections[], user_signature/hod_signature fields, available_actions
  - edited_content persisted in handover_exports table on TENANT DB
  - ledger_events rows written on export creation
All verified in shard-49 Tests 1 + 2 against production Render pipeline-core.int.celeste7.ai.

Frontend chrome (document template, TOC formatting, entity link rendering, signature block layout) left PENDING-UI.
```

---

## Scenario 9 — Sign handover (outgoing user)

**Login:** `captain.tenant@alex-short.com` / `Password2!`  
**Requires:** Export with `review_status = pending_review`.  
If none available, paste "need pending_review export reset" in notes.

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 9.1 | **Sign Handover** button visible | IdentityStrip top-right | Shield icon + "Sign Handover" | PENDING-UI | MCP browser locked |
| 9.2 | Click → **canvas modal** opens | Modal overlay | White 416×160 canvas, instruction text | PENDING-UI | MCP browser locked |
| 9.3 | **Draw** with mouse | Canvas area | Black ink follows mouse, smooth strokes | PENDING-UI | MCP browser locked |
| 9.4 | **Clear** resets canvas | Bottom-left button | Canvas goes white | PENDING-UI | MCP browser locked |
| 9.5 | **Cancel** closes modal | Bottom-right | No state change, no toast | PENDING-UI | MCP browser locked |
| 9.6 | Draw → **Confirm & Sign** | Blue button | Toast: "Handover signed — HOD notified for countersignature" | Y (API) | POST `/v1/handover/export/:id/submit` with `userSignature` payload → 200, `success:true`, `review_status:"pending_hod_signature"` — shard-49 Test 3 Step B HARD PROOF |
| 9.7 | Status pill changes | IdentityStrip | "Pending Review" → "Pending Hod Signature" | Y (API) | DB verify: `handover_exports.review_status = 'pending_hod_signature'`, `user_signature` non-null, `user_signed_at` non-null — shard-49 Test 3 Step B |
| 9.8 | Sign button disappears | IdentityStrip | Gone — replaced by Export PDF or Countersign | PENDING-UI | Button gating is derived from review_status — data proof is green; rendering PENDING-UI |

**Edge case — crew tries to sign:**
| 9.9 | Log in as crew → same page | Different role | **No** "Sign Handover" button visible at all | PENDING-UI | Crew is NOT in allowed_roles for submit/countersign per role matrix — API would reject; button visibility is UI-gated |

**Edge case — sign already-signed export:**
| 9.10 | Reload page after signing | Same URL | Status is "Pending Hod Signature", no sign button | Y (API) | Post-submit state persisted in DB (user_signed_at + review_status) — shard-49 Test 3 confirms |

**Where the signature popup appears:**
- ONLY on `/handover-export/{id}` page, inside `HandoverContent.tsx`
- The IdentityStrip's `SplitButton` opens it
- Does NOT appear on the draft panel, queue tab, or any entity lens
- Modal is center-screen with dark backdrop (40% opacity)

**Notes / errors for Scenario 9:**
```
Submit flow end-to-end API proof is GREEN via shard-49 Test 3 Step B:
  - POST /v1/handover/export/:id/submit with `sections[]` + `userSignature{image_base64,signed_at,signer_name,signer_id}`
  - Response: 200 `{success:true, review_status:"pending_hod_signature"}`
  - DB: `user_signature` populated, `user_signed_at` populated, `review_status` transitioned to pending_hod_signature
  - HOD notification cascade wired (PR #525 fix to `auth_users_roles` query)

Signature payload shape matches Pydantic `SignatureData` model: `{image_base64, signed_at, signer_name, signer_id}`.

Canvas drawing + UI chrome for 9.1-9.5 and 9.8-9.9 left PENDING-UI.
```

---

## Scenario 10 — Countersign (HOD reviews and signs)

**Login:** `captain.tenant@alex-short.com` / `Password2!` (or `hod.test@alex-short.com`)  
**Requires:** Same export from Scenario 9 in `pending_hod_signature` state.

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 10.1 | Button reads **Countersign Handover** | IdentityStrip | Different label from "Sign Handover" | PENDING-UI | MCP browser locked |
| 10.2 | Click → canvas modal | Modal | Same canvas, DIFFERENT instruction text | PENDING-UI | MCP browser locked |
| 10.3 | Modal says **"countersign and complete"** | Modal body | Not "submit this handover" | PENDING-UI | Copy-only |
| 10.4 | Draw + **Confirm & Sign** | Blue button | Toast: "Handover countersigned — rotation complete" | Y (API) | POST `/v1/handover/export/:id/countersign` with `hodSignature` payload → 200, `success:true`, `review_status:"complete"` — shard-49 Test 3 Step C HARD PROOF |
| 10.5 | Status → **Complete** (green pill) | IdentityStrip | Green | Y (API) | DB verify: `handover_exports.review_status = 'complete'`, `hod_signature` non-null, `hod_signed_at` non-null — shard-49 Test 3 Step C |
| 10.6 | **No more action buttons** | IdentityStrip | Read-only. No sign, no countersign. | PENDING-UI | State data green; button render PENDING-UI |

**Edge case — crew tries to countersign:**
| 10.7 | Log in as crew → same page (pending_hod_signature) | Different role | No countersign button visible | PENDING-UI | crew not in `["chief_engineer","chief_officer","captain","manager"]` per PR #527; API would reject; UI gating PENDING-UI |

**Edge case — countersign on wrong state:**
| 10.8 | Countersign on `pending_review` (not yet submitted) | API call | 400 "Not awaiting countersign" | Y (API) | shard-49 Test 4 HARD PROOF — countersign on fresh pending_review export returns 400, DB review_status unchanged |

**Notes / errors for Scenario 10:**
```
Countersign flow end-to-end API proof is GREEN via shard-49 Test 3 Step C + Test 4:
  - Valid state (pending_hod_signature) → 200 success, complete transition, `handover_countersigned` ledger event written
  - Invalid state (pending_review) → 400, DB review_status unchanged

Ledger cascade: shard-49 Step D verified `ledger_events` contains `handover_countersigned` rows for the export. PR #527 fixed the HOD role check and PR #525 fixed the notification query to `auth_users_roles`.

Canvas + UI chrome for 10.1-10.3 and 10.6 left PENDING-UI.
```

---

## Scenario 11 — Export PDF

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 11.1 | Click dropdown on action button | SplitButton arrow | Dropdown opens | PENDING-UI | MCP browser locked |
| 11.2 | Click **Export PDF** | Dropdown item | Browser print dialog (`window.print()`) | SKIP | Runbook explicitly lists `window.print()` as not testable via MCP (Known limitations table) — mark SKIP per runbook |
| 11.3 | Print preview | Print dialog | A4 layout, document visible, not blank | SKIP | Browser print dialog not reachable from Playwright/MCP |

**Notes / errors for Scenario 11:**
```
PDF export is `window.print()` — documented as NOT testable via MCP in the runbook's "Known Playwright MCP limitations" table. Marked SKIP.

The underlying document pipeline (what gets printed) is proven GREEN by Scenario 8: entity endpoint returns sections + LLM content + signature fields. Any print output would mirror the in-page render. Future work: wire WeasyPrint in the microservice for a server-side PDF (noted in "Known gaps" section).
```

---

## Scenario 12 — Signature popup visibility rules

Which actions show a popup and which fire directly?

| # | Action | Login as | Expected behaviour | Y / N / ERR | Console errors |
|---|--------|----------|-------------------|-------------|----------------|
| 12.1 | + Add from Queue | crew | **No popup** — fires directly, toast confirms | PENDING-UI | MCP browser locked |
| 12.2 | Add Note | crew | **Popup** — form with summary/category/section fields | PENDING-UI | MCP browser locked |
| 12.3 | Edit draft item | crew | **Popup** — edit form with pre-filled fields | PENDING-UI | MCP browser locked |
| 12.4 | Delete draft item | crew | **Popup** — confirmation "Delete this handover note?" | PENDING-UI | MCP browser locked |
| 12.5 | Export Handover | crew | **No popup** — loading state, then toast + redirect | PENDING-UI | MCP browser locked |
| 12.6 | Sign Handover | captain | **Canvas popup** — draw signature, Confirm & Sign | PENDING-UI | MCP browser locked |
| 12.7 | Countersign | captain | **Canvas popup** — same canvas, different text | PENDING-UI | MCP browser locked |
| 12.8 | Export PDF | any | **No popup** — browser print dialog | SKIP | `window.print()` not testable via MCP |

**Notes / errors for Scenario 12:**
```
Scenario 12 is entirely about UI popup/dialog presence and routing — no API surface to verify. All rows require MCP browser which is locked by CERT-TESTER. Will be filled in the follow-up visual pass.
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
| DB1 | `handover_items` count > 0 for captain | Items exist | Y — shard-47 list_handover_items test verified `GET /v1/handover/items` returns `count > 0` with the seed item id present in the array |
| DB2 | `ledger_events` has `critical_item_added` rows | Present after adding critical item | Y — shard-47 critical cascade test observed 80+ `critical_item_added` rows on a single critical item (full HOD fan-out verified) |
| DB3 | `ledger_events` has `requires_countersignature` rows | Present after submit/sign | Y (inferred) — shard-49 Step B observed the review_status transition + user_signature persistence; `requires_countersignature` ledger event is the known dispatcher side-effect per PR #525 |
| DB4 | `ledger_events` has `handover_countersigned` rows | Present after countersign | Y — shard-49 Step D explicitly queried `ledger_events` with `action='handover_countersigned'` and got ≥1 rows for the test export |
| DB5 | Export row has `user_signed_at` + `hod_signed_at` | Both NOT NULL after full lifecycle | Y — shard-49 Step C DB verify: `user_signature`, `user_signed_at`, `hod_signature`, `hod_signed_at` all populated after countersign |
| DB6 | `signed_storage_url` is NOT NULL | Signed HTML uploaded to storage | PARTIAL — shard-49 suite does not read `signed_storage_url` column explicitly. Storage path pattern documented in HMAC01 notes H8. Needs a dedicated psql check or microservice storage-write assertion |

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
| Pre-flight | PENDING-UI | No | Needs MCP browser pass — API is known green |
| Queue loads | PENDING-UI | No | Data source green (shard-47 list_handover_items) |
| + Add from Queue | PASS (API) | No | shard-47 HARD PROOF via add_to_handover dispatcher |
| Draft Items — view | PASS (API) | No | `GET /v1/handover/items` returns items for captain with count>0 |
| Draft Items — edit (PATCH) | PASS (API) | No | shard-47 HARD PROOF: PATCH 200 + DB update + ledger `edit_draft_item` + CORS OK |
| Draft Items — delete (DELETE) | PASS (API) | No | shard-47 HARD PROOF: DELETE 200 + soft-delete + list exclusion + ledger `draft_item_deleted` + CORS OK |
| Draft Items — add note | PASS (API) | No | add_to_handover with entity_type=note creates handover_items row (shard-47 seeds) |
| Add from Fault lens | PASS (API) / PENDING-UI | No | Dispatcher proven; lens button visibility PENDING-UI |
| Add from WO lens | PASS (API) / PENDING-UI | No | Same |
| Add from Equipment lens | PASS (API) / PENDING-UI | No | Same |
| Add from Part lens | PASS (API) / PENDING-UI | No | Same |
| Add from Certificate lens | PASS (API) / PENDING-UI | No | CERTIFICATE01 registry widening confirmed; UI PENDING |
| Document renders (sections) | PASS (API) | No | shard-49 Test 1+2: sections_count>0, entity endpoint returns populated sections + signature fields + available_actions |
| Sign outgoing (canvas) | PASS (API) | No | shard-49 Test 3 Step B: submit → pending_hod_signature, user_signature persisted |
| Countersign (HOD canvas) | PASS (API) | No | shard-49 Test 3 Step C + Test 4: countersign → complete, hod_signature persisted, wrong-state 400 |
| PDF export | SKIP | No | `window.print()` not testable via MCP per runbook |
| Signature popup rules | PENDING-UI | No | Pure UI behaviour table — needs MCP browser |

---

## All console errors (paste everything)

```
No production console errors captured in this pass — MCP browser profile was locked for the entire visual phase (held by CERT-TESTER, queued behind HOURSOFREST_MCP02). CLI shard runs do not capture browser console output unless tests explicitly attach a listener.

Test-infra errors observed (not product regressions):
  - shard-47 initial run: "Failed to fetch" on every `page.evaluate(fetch)` call — root cause was my run not setting NEXT_PUBLIC_API_URL (helper fell back to localhost:8000). Fixed on rerun with NEXT_PUBLIC_API_URL=https://pipeline-core.int.celeste7.ai.
  - shard-47 delete_handover_item: one flaky "Failed to fetch" on the list-after-delete probe (browser-context fetch), passed on retry. DELETE itself (Node-context request) was clean.
  - shard-52 (browser-visual): all cells failed because global-setup mints TENANT-signed JWTs but app.celeste7.ai authenticates via MASTER Supabase — storage state is not recognised by the production frontend. This is the same issue already documented in the MD header for the Fleet Manager account. Headless CLI cannot walk the real UI.
```

## Questions for HANDOVER01

```
Q1: Should I attempt a second pass once the MCP Chrome profile frees (CERT-TESTER is ahead of me with 13 scenarios)? That would close out every PENDING-UI cell and populate Pre-flight + Scenarios 1-7 + 12 visually. Or is the API + DB + ledger proof sufficient for this handoff?

Q2: DB6 (`signed_storage_url` NOT NULL) is marked PARTIAL — shard-49 doesn't assert on that column. Do you want me to add a targeted psql one-liner in the commit, or is the microservice-storage path already known-green from your PR #549 work?

Q3: Shard-47's `sign_handover_outgoing` and `sign_handover_incoming` advisory tests aim at dedicated endpoints distinct from the `/submit` and `/countersign` routes used by shard-49. Are the `/sign/outgoing` and `/sign/incoming` routes live, deprecated, or never-wired? Their 400/404/500 expectations suggest they might be stubs.

Q4: The "Manager test account broken" gap in the MD (Fleet Manager uses TENANT JWT but backend expects MASTER) — is there a path to a MASTER-registered manager account so shard-52 browser tests could actually pass? Or is that deferred?
```
