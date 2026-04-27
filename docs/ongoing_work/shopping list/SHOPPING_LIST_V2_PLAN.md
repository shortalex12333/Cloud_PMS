# Shopping List V2 — Document Model Plan
**Owner:** SHOPPING05 | **Status:** PLANNING | **Date:** 2026-04-27

---

## The Real User Journey

**Who:** Chief Engineer (CE). Sometimes Chief Officer for deck supplies.

**What they actually do today:**
1. Walk the vessel over days/weeks — mentally noting what is low, broken, or needed
2. Open a Word doc. Add rows: name / quantity / unit price / supplier / URL / reason
3. Build the list until it is worth sending (10–20 items typically)
4. Email it to the Purser or shore agent
5. The Purser/agent places the order, arranges shipping
6. Items arrive through receiving — checked off manually

**What we are replacing that with:**
1. CE opens "New Shopping List" → names it → gets a table editor
2. Adds rows inline — searches existing parts or types new candidates
3. Saves as DRAFT. Returns later. Adds more rows.
4. When ready: "Submit for Approval" → HOD notified (one notification, not per-item)
5. HOD opens the list. Reviews each row. Approves or rejects individual lines (with reason)
6. HOD clicks "Approve List" → list status = hod_approved → PDF generated → Purser notified
7. Purser/Captain clicks "Convert to Purchase Order" → creates PO from all approved lines
8. PO domain (PURCHASE05) handles supplier selection, ordering, receiving writeback

---

## Current State — What Exists

### Tables
| Table | State | Notes |
|---|---|---|
| `pms_shopping_list_items` | **IN USE** | 48 columns, full lifecycle, all items are orphaned (no parent list) |
| `shopping_list_items` | **LEGACY/DEAD** | Old simpler table (15 cols, `status IN (pending/ordered/cancelled)`) — ignore |
| `v_shopping_list_enriched` | View on pms_shopping_list_items | Fine, keep |
| `pms_purchase_orders` | PURCHASE05 domain | No `source_shopping_list_id` column yet |
| `pms_purchase_order_items` | PURCHASE05 domain | No `shopping_list_item_id` FK yet |

### Key DB functions / triggers on `pms_shopping_list_items`
- `rpc_insert_shopping_list_item` — RPC for INSERT (bypasses some RLS)
- `enforce_shopping_list_edit_rules` — BEFORE UPDATE trigger (blocks bad transitions)
- `log_shopping_list_state_change` — AFTER INSERT/UPDATE (writes state history)
- `f1_cache_invalidate('shopping_item')` — cache busting

### Current status CHECK constraint (OBSTACLE — see below)
```sql
CHECK (status = ANY (ARRAY[
  'candidate', 'under_review', 'approved', 'ordered',
  'partially_fulfilled', 'fulfilled', 'installed'
]))
-- MISSING: 'rejected'
```

### Current `_convert_to_po` (internal_dispatcher.py:3714)
- Grabs ALL `status='approved'` items by `yacht_id`
- Optionally filters by `item_ids` list
- Creates `pms_purchase_orders` row + `pms_purchase_order_items` rows
- Marks shopping items as `status='ordered'`
- **Does NOT know about a shopping list document** — no `shopping_list_id` concept
- **Does NOT write `order_id` or `order_line_number` back** (PR #726 pending — PURCHASE05)

---

## Known Obstacles

### OBSTACLE 1: No `pms_shopping_lists` header table
**Impact:** Everything. Items have no parent document. The `/shopping-list` page shows individual item rows, not lists.
**Fix:** Migration — create `pms_shopping_lists`. Add `shopping_list_id` FK (nullable) to `pms_shopping_list_items`. Nullable so 1,117 staging rows are untouched.

### OBSTACLE 2: `'rejected'` is NOT a valid item status
**Current behaviour:** Rejection sets `rejected_at` timestamp + `rejected_by` UUID. Item status stays `'candidate'` or `'under_review'`. This is invisible in status-based queries.
**Impact:** HOD rejects a line → item status still looks like `candidate` → confusing in the list table editor. `convert_to_po` already skips non-approved items, so functionally OK, but UX is broken.
**Fix:** Migration — ALTER the CHECK constraint to add `'rejected'`. Update `enforce_shopping_list_edit_rules` trigger to allow `candidate → rejected` and `under_review → rejected`. Add `'rejected'` to `SHOPPING_LIST_STATUS_FLOW` in handlers.

### OBSTACLE 3: Trigger blocks `candidate → approved` direct transition
**Current constraint in trigger:**
```sql
IF OLD.status = 'candidate' AND NEW.status NOT IN ('candidate', 'under_review') THEN
  RAISE EXCEPTION '...'  -- blocks direct candidate → approved
```
**Impact:** When HOD reviews a list, they want to approve items directly (many are obviously needed). Currently the API must: move item to `under_review` then `approved` — two round trips per item.
**Fix:** Update trigger to allow `candidate → approved` (HOD direct approve). The `under_review` state remains available for "send back to requester for more info" but is not mandatory.

### OBSTACLE 4: `convert_to_po` has no `shopping_list_id` concept
**Impact:** After we add the header document, `convert_to_po` must operate on a specific list, not all approved items across the vessel. Currently it would convert items from ANY list on the vessel in one call.
**Fix:** Update `_convert_to_po` in `internal_dispatcher.py` to:
- Accept `shopping_list_id` param
- Filter items by `shopping_list_id`
- Write `source_shopping_list_id` on the `pms_purchase_orders` row
- Mark the `pms_shopping_lists` row as `status='converted_to_po'`
Requires PURCHASE05 coordination — they own `_convert_to_po`.

### OBSTACLE 5: `pms_purchase_orders` has no `source_shopping_list_id`
**Impact:** No way to trace "this PO came from SL-042". The Purser/Captain can't see which shopping list spawned a PO.
**Fix:** Migration — add `source_shopping_list_id uuid REFERENCES pms_shopping_lists(id) ON DELETE SET NULL`.
PURCHASE05 must write it in `_convert_to_po`.

### OBSTACLE 6: `pms_purchase_order_items` has no `shopping_list_item_id`
**Impact:** When a PO line is received via Receiving flow, the shopping list item's `quantity_received` is updated via `pms_receiving_line_items.shopping_list_item_id` (that FK already exists). So receiving writeback works today. However, from the PO side, there's no link from a PO line back to the shopping list item — the Purser can't see "this line came from SL-042 item 3."
**Fix (MVP):** Add `shopping_list_item_id uuid REFERENCES pms_shopping_list_items(id) ON DELETE SET NULL` to `pms_purchase_order_items`. PURCHASE05 writes it during `_convert_to_po`.

### OBSTACLE 7: `rpc_insert_shopping_list_item` doesn't accept `shopping_list_id`
**Impact:** The RPC function signature is fixed. We can't pass `shopping_list_id` through it.
**Fix:** Two options:
  (a) ALTER FUNCTION to add `p_shopping_list_id` param — migration required
  (b) Do the INSERT directly via `pms_shopping_list_items.insert()` (service key, bypasses RLS) and skip the RPC — simpler, no migration
Decision: Use option (b) for new list-scoped item creation. RPC stays for the legacy single-item flow.

### OBSTACLE 8: `/shopping-list` page shows items, not lists
**Impact:** The entire page navigation changes. Currently: table of individual items. After: table of list documents (SL number, name, department, status, item count, total). Clicking a list → opens the list document (table editor). Clicking an item row within the list → opens item lens card.
**Fix:** New page component for list-level table. Existing `ShoppingListContent.tsx` becomes the item detail lens (unchanged). New `ShoppingListDocContent.tsx` for the list document lens.

### OBSTACLE 9: PDF generation
**Ledger PDF** uses PyMuPDF (`fitz`) — see `ledger_routes.py:418`. Same approach works here.
**For MVP:** New endpoint `POST /v1/shopping-list/export-pdf` in a new route file. Generates PDF inline (not a separate microservice). Returns as `application/pdf` stream.
**PDF content:** Header block (SL number, vessel, department, created by, submitted by, approved by, dates). Line items table (Part / Part# / Qty / Unit / Unit price / Line total / Status / Rejection reason). Footer (estimated total, currency, approval statement).

---

## Required Migrations

### M1 — Create `pms_shopping_lists` header table
```sql
CREATE TABLE pms_shopping_lists (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id            uuid NOT NULL REFERENCES yacht_registry(id) ON DELETE CASCADE,
  list_number         text NOT NULL,  -- SL-2026-001
  name                text NOT NULL,
  department          text,           -- engine / deck / galley / interior / bridge / general
  status              text NOT NULL DEFAULT 'draft'
                      CHECK (status IN ('draft','submitted','hod_approved','converted_to_po','cancelled')),
  currency            text NOT NULL DEFAULT 'EUR',
  estimated_total     numeric(12,2),  -- sum of approved line totals, updated on item changes
  notes               text,
  created_by          uuid NOT NULL,
  created_at          timestamptz NOT NULL DEFAULT now(),
  submitted_at        timestamptz,
  submitted_by        uuid,
  approved_by         uuid,
  approved_at         timestamptz,
  converted_to_po_id  uuid REFERENCES pms_purchase_orders(id) ON DELETE SET NULL,
  converted_at        timestamptz,
  deleted_at          timestamptz,
  deleted_by          uuid,
  is_seed             boolean DEFAULT false
);
CREATE UNIQUE INDEX idx_sl_number ON pms_shopping_lists(yacht_id, list_number);
CREATE INDEX idx_sl_status ON pms_shopping_lists(yacht_id, status) WHERE deleted_at IS NULL;
-- RLS: service_role full access; authenticated users can see own yacht's lists
ALTER TABLE pms_shopping_lists ENABLE ROW LEVEL SECURITY;
CREATE POLICY sl_service_full ON pms_shopping_lists TO service_role USING (true) WITH CHECK (true);
CREATE POLICY sl_yacht_select ON pms_shopping_lists FOR SELECT TO authenticated
  USING (has_yacht_access(yacht_id));
CREATE POLICY sl_yacht_insert ON pms_shopping_lists FOR INSERT TO authenticated
  WITH CHECK (has_yacht_access(yacht_id));
CREATE POLICY sl_yacht_update ON pms_shopping_lists FOR UPDATE TO authenticated
  USING (has_yacht_access(yacht_id)) WITH CHECK (has_yacht_access(yacht_id));
```

### M2 — Add `shopping_list_id` to `pms_shopping_list_items`
```sql
ALTER TABLE pms_shopping_list_items
  ADD COLUMN shopping_list_id uuid REFERENCES pms_shopping_lists(id) ON DELETE SET NULL;
CREATE INDEX idx_sli_list_id ON pms_shopping_list_items(shopping_list_id) WHERE shopping_list_id IS NOT NULL;
```

### M3 — Add `rejected` to item status CHECK constraint
```sql
ALTER TABLE pms_shopping_list_items
  DROP CONSTRAINT pms_shopping_list_items_status_check;
ALTER TABLE pms_shopping_list_items
  ADD CONSTRAINT pms_shopping_list_items_status_check
  CHECK (status = ANY (ARRAY[
    'candidate','under_review','approved','rejected',
    'ordered','partially_fulfilled','fulfilled','installed'
  ]));
```

### M4 — Update `enforce_shopping_list_edit_rules` trigger
Allow: `candidate → approved` (HOD direct approve) and `candidate/under_review → rejected`.
```sql
-- Replace trigger function body (see implementation section)
```

### M5 — Add `source_shopping_list_id` to `pms_purchase_orders`
```sql
ALTER TABLE pms_purchase_orders
  ADD COLUMN source_shopping_list_id uuid REFERENCES pms_shopping_lists(id) ON DELETE SET NULL;
```

### M6 — Add `shopping_list_item_id` to `pms_purchase_order_items`
```sql
ALTER TABLE pms_purchase_order_items
  ADD COLUMN shopping_list_item_id uuid REFERENCES pms_shopping_list_items(id) ON DELETE SET NULL;
```

### M7 — Auto-number trigger for `pms_shopping_lists`
```sql
CREATE OR REPLACE FUNCTION generate_sl_number()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  next_num int;
BEGIN
  SELECT COALESCE(MAX(
    CAST(SPLIT_PART(list_number, '-', 3) AS int)
  ), 0) + 1
  INTO next_num
  FROM pms_shopping_lists
  WHERE yacht_id = NEW.yacht_id
    AND list_number LIKE 'SL-' || EXTRACT(YEAR FROM now()) || '-%';
  NEW.list_number := 'SL-' || EXTRACT(YEAR FROM now()) || '-' || LPAD(next_num::text, 3, '0');
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_sl_number BEFORE INSERT ON pms_shopping_lists
  FOR EACH ROW WHEN (NEW.list_number IS NULL OR NEW.list_number = '')
  EXECUTE FUNCTION generate_sl_number();
```

---

## New Backend Actions Required

| Action ID | Handler | Who | What |
|---|---|---|---|
| `create_shopping_list` | New | All crew | Creates `pms_shopping_lists` row, returns `list_id` |
| `add_item_to_list` | New | All crew | Inserts `pms_shopping_list_items` with `shopping_list_id` |
| `update_list_item` | New | Requester (while draft) | Updates qty/price/notes on a line item |
| `delete_list_item` | Extends existing `delete_shopping_item` | Requester/HOD | Soft-delete a line item from the list |
| `submit_shopping_list` | New | CE/Requester | DRAFT → SUBMITTED, notify HOD |
| `hod_review_list_item` | Replaces per-item approve/reject | HOD/Captain | Sets item status approved/rejected+reason in one call |
| `approve_shopping_list` | New | HOD/Captain | SUBMITTED → HOD_APPROVED, generate PDF, notify Purser |
| `export_shopping_list_pdf` | New | CE/HOD/Purser/Captain | Stream PDF of list |

### Existing actions to update
- `approve_shopping_list_item` — still valid for single-item approve from item lens
- `reject_shopping_list_item` — still valid but now writes `status='rejected'` (not just `rejected_at`)
- `convert_to_po` (PURCHASE05) — accept `shopping_list_id`, filter by list, write back FKs

---

## Frontend Changes

### Page: `/shopping-list` (existing)
**Before:** Table of individual items.
**After:** Table of list documents.
Columns: SL # / Name / Department / Status / Items (count) / Approved / Est. Total / Created By / Date

### New page or panel: Shopping List Document
URL: `/shopping-list/[id]` — OR — as EntityLensPage with new `shopping_list_doc` entity type.
Contains:
- Header strip: SL number, name, department, status, submitted by, approved by, dates
- Inline table editor (rows = line items)
  - Columns: Part / Part# / Qty / Unit / Unit Price / Total / Status chip / Reason
  - "+ Add Row" button
  - Existing part search in Part column (auto-fills Part#, Unit, Price)
  - Free-text for candidate parts
- Primary action (SplitButton):
  - Draft: "Submit for Approval" + dropdown (Export Draft PDF, Cancel List)
  - Submitted (HOD view): "Approve List" + dropdown (Reject All, Export PDF)
  - HOD_Approved: "Convert to Purchase Order" + dropdown (Export PDF)

### Parts/Inventory lens — "Add to Shopping List"
- Opens list picker modal: shows existing DRAFT lists for this vessel
- User selects list + quantity
- Auto-fills from parts record
- Appends row to selected list via `add_item_to_list` action

### Notifications
- Submit → HOD gets notification (one per list, not per item)
- HOD Approve → Purser/Captain get notification ("SL-042 approved, ready to convert")

---

## PDF Structure

```
┌─────────────────────────────────────────────────────────┐
│  [VESSEL NAME]              SHOPPING REQUISITION        │
│  SL-2026-042                                            │
│  "Engine Room Q2 Restock"                               │
│                                                         │
│  Department:  Engine          Currency: EUR             │
│  Requested by: J. Smith (Chief Engineer)                │
│  Submitted:    2026-04-22                               │
│  Approved by:  M. Jones (Captain)  on 2026-04-24        │
├──────┬──────────────┬─────┬──────┬─────────┬───────────┤
│  #   │ Description  │ Qty │ Unit │ Unit £  │ Total     │
├──────┼──────────────┼─────┼──────┼─────────┼───────────┤
│  1   │ M8x30 Bolt   │ 50  │ ea   │ €0.12   │ €6.00  ✓ │
│  2   │ Oil Filter X │  2  │ ea   │ €45.00  │ €90.00 ✓ │
│  3   │ EU→UK Plug   │ 10  │ ea   │ €3.50   │ REJECTED  │
│      │              │     │ Reason: already in stock    │
├──────┴──────────────┴─────┴──────┴─────────┴───────────┤
│  Approved Total: €96.00                                 │
│  Items: 3 requested, 2 approved, 1 rejected             │
│                                                         │
│  Approved by signature: _________________ Date: _______ │
└─────────────────────────────────────────────────────────┘
```

---

## Build Order (sequenced to avoid blockers)

### Phase 1 — DB Migrations (no app changes, TENANT only)
1. M1 — create `pms_shopping_lists` + RLS + auto-number trigger
2. M2 — add `shopping_list_id` to items (nullable)
3. M3 — add `rejected` to item status CHECK
4. M4 — update trigger to allow `candidate→approved` and `*→rejected`
5. M5 — add `source_shopping_list_id` to `pms_purchase_orders`
6. M6 — add `shopping_list_item_id` to `pms_purchase_order_items`

### Phase 2 — Backend new actions (no frontend yet)
7. `create_shopping_list` handler + registry + prefill
8. `add_item_to_list` handler (bypasses RPC, direct insert with `shopping_list_id`)
9. `update_list_item` handler
10. `submit_shopping_list` handler + notification
11. `hod_review_list_item` handler (approve OR reject in one call)
12. `approve_shopping_list` handler + notification
13. `export_shopping_list_pdf` route (PyMuPDF, inline, no microservice)
14. Update `_convert_to_po` (PURCHASE05) to accept `shopping_list_id`

### Phase 3 — Frontend
15. `/shopping-list` page → list-of-lists table
16. `/shopping-list/[id]` document page with inline table editor
17. Parts lens "Add to Shopping List" → list picker modal

### Phase 4 — Wire and verify
18. Full wire-walk: create list → add items → submit → HOD approve → PDF → convert to PO
19. Notifications verified via psql
20. Ledger events verified

---

## Coordination Required

| Peer | What |
|---|---|
| **PURCHASE05** | Update `_convert_to_po` to accept `shopping_list_id`, write `source_shopping_list_id` on PO, write `shopping_list_item_id` on PO line items. Migrations M5+M6 land before their handler change. |
| **EQUIPMENT05** | No change needed. |
| **RECEIVING05** | No change needed. `pms_receiving_line_items.shopping_list_item_id` already exists and works. |

---

## What We Are NOT Building (MVP)

- Excel/CSV export — PDF only
- Email sending from within the app — user exports PDF and emails themselves
- Recurring weekly notifications for candidate parts once list model exists (superseded by the list document tracking)
- Supplier selection on the shopping list — that belongs on the PO (Purser's job)
- Budget/cost centre — not in scope

---

## Open Questions (answered)

| # | Question | Answer |
|---|---|---|
| 1 | Does Purser exist as a system user? | May not in staging. Export PDF for email. |
| 2 | Header document? | Yes — named, dated, department. |
| 3 | Approval granularity? | HOD approves/rejects individual lines. |
| 4 | Export format? | PDF only. |
| 5 | List = named document? | Yes. CE names it intentionally. |
| 6 | Convert to PO model? | Entire approved list → one PO. PURCHASE05 owns the PO side. |
| 7 | Parts lens "Add to Shopping List"? | Picks from existing DRAFT lists. |
| 8 | PDF triggers? | Available at DRAFT (for review) and HOD_APPROVED (final). |
