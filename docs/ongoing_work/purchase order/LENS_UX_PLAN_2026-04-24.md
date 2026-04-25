# Purchase Order Lens — UX Card Redesign

**Author:** PURCHASE05
**Date:** 2026-04-24
**Companion to:** `/Users/celeste7/Desktop/lens_card_upgrades.md`
**Follows patterns established in:** cert (PR #676/#681), document, work order specs in that file.

---

## 1. What is the "hero" of a Purchase Order?

- Cert lens hero = the stored PDF (the certificate itself).
- Doc lens hero = the file (manual / SOP).
- Work-order lens hero = the checklist + procedure.
- **PO lens hero = the line items table + the invoice document.** A PO's identity is "we bought *these things* for *this price* from *this supplier*". Everything else is context.

Two-column hero layout when both are present; line items always visible, invoice slides in from the right after upload.

---

## 2. DB column audit (pms_purchase_orders)

| Column | Type | Rendering | Notes |
|---|---|---|---|
| id | uuid | **Backend** | Never shown to users |
| yacht_id | uuid | FE via FK | Resolve via MASTER DB: `fleet_registry.yacht_name` |
| supplier_id | uuid | FE via FK | Resolve via TENANT `pms_suppliers.name` + `.email` + `.phone` + `.contact_name` + `.preferred` |
| po_number | text | **Frontend** — primary identifier, mono |
| status | text | **Frontend** — pill (draft / submitted / approved / ordered / partially_received / received / cancelled) |
| ordered_at | timestamptz | **Frontend** — header date |
| received_at | timestamptz | **Frontend** — header date (only show when `status` ∈ received / partially_received) |
| currency | text | **Frontend** — pill + column next to total |
| metadata | jsonb | Backend (search) + `metadata.notes` surfaces in Notes tab |
| approved_by | uuid | FE via FK | Resolve via `auth_users_profiles.name` + `auth_users_roles.role` |
| approved_at | timestamptz | **Frontend** — only when approved |
| approval_notes | text | **Frontend** — under Notes tab, tagged "approval note" |
| received_by | uuid | FE via FK | Resolve to name + role; only show when received |
| receiving_notes | text | **Frontend** — under Notes tab, tagged "receiving note" |
| ordered_by | uuid | FE via FK | Resolve to name + role — this is the requester (closest to "Requested By" in typical POs) |
| deleted_at / deleted_by / deletion_reason | | **Frontend** — Audit Trail only, only when soft-deleted; strikethrough styling |
| is_seed | boolean | **Backend** — not shown; filter from list |
| created_at / updated_at | timestamptz | **Frontend** — Audit Trail |

**Child tables** (already confirmed in schema):
- `pms_purchase_order_items` (id, part_id FK→pms_parts, description, quantity_ordered, quantity_received, unit_price, currency, metadata) — the hero
- `pms_suppliers` (name, contact_name, email, phone, preferred) — populates the Supplier tab
- `pms_attachments` where `entity_type='purchase_order'` — supporting docs + invoice (category='invoice' for the invoice specifically, per PR #685 upload_invoice handler)
- `ledger_events` where `entity_type='purchase_order'` — Audit Trail

No PO-specific `pms_purchase_order_notes` or `pms_purchase_order_history` tables exist today. Notes live in `metadata.notes` (append-only stream with timestamps — added by the `add_po_note` handler in PR #670). Audit trail comes from `ledger_events`.

---

## 3. Header metadata (top strip, current UX retained but enriched)

```
╔══════════════════════════════════════════════════════════════════════════╗
║  PO-S45-po-1773980223139                              ┌──────────────┐   ║
║                                                        │  ▼  Actions  │   ║
║  Palmer Marine Supply Ltd.                             └──────────────┘   ║
║                                                                            ║
║  [ received ]  [ EUR ]     Ordered  17 Mar 2026   Received  29 Mar 2026   ║
║                                                                            ║
║  Total  €4,728    ·  8 items                                              ║
║                                                                            ║
║  Requested by  Alex Short  (Chief Engineer)                               ║
║  Approved by   Jane Doe    (Captain)            17 Mar 2026                ║
║  Received by   Mark Smith  (Chief Officer)      29 Mar 2026                ║
╚══════════════════════════════════════════════════════════════════════════╝
```

- Title row: `po_number` mono, subtitle = `supplier_name`.
- Pills: `status` (colour-coded via existing palette) + `currency` (neutral).
- Details row: `ordered_at`, `received_at`, computed total, item count.
- Person rows: `ordered_by / approved_by / received_by` → name + role via `auth_users_profiles` + `auth_users_roles` (pattern documented at top of cert spec). Strikethrough only when soft-deleted (from `deleted_at`).
- **Department** is NOT a column on `pms_purchase_orders` — intentionally omitted. If CEO wants it, derive from the requester's `auth_users_roles.department` and render after the name.

---

## 4. Horizontal tabs (match work-order pattern, replace current vertical flow)

```
╔════════ HEADER STRIP ═════════════════════════════════════════════════════╗
╠═══════════════════════════════════════════════════════════════════════════╣
║  Items │ Invoice │ Supplier │ Related Parts │ Supporting Docs │ Notes │ Audit Trail
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║            (content area — renders selected tab)                           ║
║                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

### Tab 1 — Items (default open)

Table rendered directly in the card, tokenised, sortable per column:

| Line | Part | Description | Qty ordered | Qty received | Unit price | Line total |
|---|---|---|---|---|---|---|
| 1 | `@ FLT-0033 Fuel filter` (link) | ... | 3 | 3 | €42.00 | €126.00 |
| 2 | — (no part linked) | Shipping charge | 1 | 1 | €35.00 | €35.00 |
| ... | | | | | | |
| | | **Total** | | | | **€4,728.00** |

- Part column = `FETCH WHERE pms_parts.id = item.part_id → pms_parts.part_number + pms_parts.name`, rendered as a clickable link to the Part lens. If `part_id` is NULL (freeform line), no link.
- Qty received < Qty ordered → amber highlight on the row.
- Qty received = 0 on all rows + status=received → red flag ("status says received but nothing logged").
- Bottom row: computed total (validated against `total_amount` if present on the PO).
- **Actions on the Items tab:** `Add Item` button (already wired — PR #685 handler `add_item_to_purchase`, draft-only), line-level `Edit` / `Remove` on each row for drafts.

### Tab 2 — Invoice

- If an attachment with `category='invoice'` exists: render inline via signed URL from `pms-finance-documents` bucket (same signed-URL path as cert PDFs). Scrollable iframe, full-width within the card.
- If none exists: clear empty state + CTA `Upload Invoice` (already wired to upload_invoice handler in PR #685).
- Above the render: filename, upload date, uploaded-by name+role.

### Tab 3 — Supplier

Shallow readonly panel pulling from `pms_suppliers` row via `supplier_id`:

```
  Palmer Marine Supply Ltd.          ★ Preferred supplier
  Contact  John Palmer
  Email    orders@palmermarine.co.uk
  Phone    +44 23 8099 1234
  Address  12 Empress Dock, Southampton SO14 3FG
  Service contracts  3 active  (link to Service Contracts lens)
```

No edit from the PO card (suppliers own their mutation flow elsewhere). Purely contextual.

### Tab 4 — Related Parts (mirrors cert's "Related Equipment")

Parts touched by this PO — derived from `pms_purchase_order_items.part_id`, de-duplicated. Each row clickable to the Part lens (same UX as cert → equipment):

```
@ FLT-0033 — Fuel filter element
Perkins     Consumable · primary fuel filter                 [ Visit ]
```

Format matches the cert spec `@ code — name / manufacturer / description(first-80-chars)`.

**Reverse FK:** when adding an item to a PO, the Part lens's "Linked POs" section should surface this PO (standard bidirectional visibility). Part-lens side is out-of-scope here but flagged.

### Tab 5 — Supporting Documents (renamed from "attachments", per cert spec)

Attachments from `pms_attachments` where `entity_type='purchase_order'` AND `category != 'invoice'` (invoice is its own tab). Delivery notes, quotations, shipping docs, etc. Upload popup must state clearly: **"Use the Invoice tab to attach the supplier invoice. This tab is for quotations, delivery notes, and other supporting paperwork."**

### Tab 6 — Notes

Append-only stream from `metadata.notes` (handler `add_po_note` — PR #670). Each note:

```
──────────────────────────────────────────
[17 Mar 2026 09:42]  Alex Short · Chief Engineer
Delivery date confirmed for end of month. Supplier will email tracking Monday.
──────────────────────────────────────────
```

Surface existing `approval_notes` (with tag "Approval note · Jane Doe · Captain") and `receiving_notes` ("Receiving note · Mark Smith · Chief Officer") in the same stream, chronologically merged.

"Add note" button at the top — uses the now-wired `add_po_note` popup (PR #685 field_metadata fix).

### Tab 7 — Audit Trail

Rows from `ledger_events` where `entity_type='purchase_order'` and `entity_id = <po_id>`, chronological descending:

```
17 Mar 2026  Jane Doe (Captain)           approved purchase order
17 Mar 2026  Alex Short (Chief Engineer)  submitted purchase order
16 Mar 2026  Alex Short (Chief Engineer)  added item: Fuel filter × 3
16 Mar 2026  Alex Short (Chief Engineer)  added item: Gasket set × 2
15 Mar 2026  Alex Short (Chief Engineer)  created purchase order
```

When soft-deleted (`deleted_at` set): banner at top of card "This purchase order was deleted on {date} by {name} ({role}). Reason: {deletion_reason}". Keep all tabs readable but strikethrough the header title. Matches the file's "we always retain deleted, never truly delete" principle.

---

## 5. Width

Current card width = `lens_panel__fvw3l` (~960px). Cert now uses `.panelWide` (1120px, opt-in, per CERT04 peer msg). PO should also use `.panelWide` — the items table needs the horizontal room, same as cert's PDF hero. No new tokens; reuse the existing responsive wide class.

---

## 6. Actions dropdown — alignment with Issue #14

Already shipped (PR #670 + PR #685). For completeness on this plan:

| KEEP | Status gate | Handler |
|---|---|---|
| Submit | draft → submitted | `submit_purchase_order` |
| Approve | submitted → ordered | `approve_purchase_order` |
| Receive Goods | ordered → received | `mark_po_received` |
| Add PO Note | any | `add_po_note` |
| Update Purchase Status | any non-terminal | `update_purchase_status` |
| Add Item to Purchase | **draft only** (DB-gated in handler) | `add_item_to_purchase` |
| Upload Invoice | any non-deleted | `upload_invoice` |
| Add to Handover | any | cross-domain injected |
| Cancel Purchase Order | any non-terminal | `cancel_purchase_order` |
| Delete Purchase Order | any | `delete_purchase_order` (soft-delete) |

**Hidden** (`_PURCHASE_ORDER_HIDDEN_ACTIONS`): `create_purchase_request`, `track_delivery`, `order_part`.

---

## 7. Tabulated list view (already shipped — PR #679)

10 sortable columns: PO Number · Supplier · Status · Ccy · Items · Total · Requested By · Ordered · Received · Created. Matches the `EntityTableList<T>` generic that every lens now uses.

---

## 8. Filter panel (already shipped — PR #670)

7 fields in tokenised `FilterPanel`: Status + Currency selects; PO Number + Supplier ILIKE text; Ordered-date-range + Received-date-range + Created-date-range.

**Possible additions for v2** (listed in Issue #20 spirit):
- Min / max total amount (numeric range — not yet a filter type; would be the first in the framework, same as CERT04 flagged).
- Requested-by multi-select (crew list per yacht).
- "Has invoice attached" / "No invoice" (derived boolean over `pms_attachments` join).
- Supplier preferred-only boolean.

Deferred until numeric-range + boolean filter types land in the shared framework (CERT04's MVP follow-up note).

---

## 9. What this plan is NOT

- It does not introduce new tables. Everything binds to existing `pms_purchase_orders`, `pms_purchase_order_items`, `pms_suppliers`, `pms_attachments`, `ledger_events`, `auth_users_profiles`, `auth_users_roles`, `fleet_registry`.
- It does not invent a department field on PO. If CEO wants it, it comes via the requester's role table — not a new column.
- It does not introduce numeric-range or boolean filter types — those are a shared-framework change flagged by CERT04.
- It does not change the shared `EntityTableList` or `FilterPanel` components. PO consumes them as a subscriber.

---

## 10. Build order (suggested)

1. **User-name enrichment in /v1/entity/purchase_order/{id}** — resolve `approved_by`, `received_by`, `ordered_by` → name + role via batch auth_users lookup (same shape as entity_routes.py shopping_list branch). Same mechanism as Issue #20 list enrichment from PR #685, but for the single-entity endpoint.
2. **PurchaseOrderContent header strip rebuild** — rich details block, pill row, person rows.
3. **Tab container** — replace vertical sections with horizontal tabs (copy the work-order lens pattern once it lands; if WO05 ships first, consume their TabContainer; if I ship first, build a local one and promote later).
4. **Items tab** — pms_purchase_order_items table render + row-level edit for drafts.
5. **Invoice tab** — signed-URL iframe of `pms-finance-documents` attachment with `category='invoice'`.
6. **Supplier tab** — joined readonly view.
7. **Related Parts tab** — deduped from items.
8. **Supporting Docs tab** — attachment list minus invoice.
9. **Notes tab** — merged stream of `metadata.notes` + `approval_notes` + `receiving_notes`.
10. **Audit Trail tab** — `ledger_events` query.
11. **`.panelWide` class** — opt-in on the PO lens.

Each step is a small PR. Matches the incremental merge cadence the rest of the team is using tonight.
