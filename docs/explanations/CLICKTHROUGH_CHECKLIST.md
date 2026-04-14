# CelesteOS Cloud PMS — Definitive Clickthrough Checklist

**Purpose:** Exhaustive test of every page, every button, every action, every signature flow, every workflow journey. Verify the FULL round trip: click → modal → fill → submit → API call → DB insert → UI update.

**How to use:**
1. Open site + browser DevTools (Console tab + Network tab)
2. Test 4 times — once per role (Crew, HOD, Captain, Fleet Manager)
3. For every action: fill the form, SUBMIT, check Network for POST status, check Console for errors, check UI for result
4. Mark: PASS (full round trip works) / FAIL (broken) / 403 (permission denied) / STUB (returns NOT_IMPLEMENTED)
5. Paste any console error text in the Console column

**Date:**  
**Environment:** (local / staging / production)  
**Browser:**

---

## TEST ACCOUNTS

| Role | Account Email | Password | Notes |
|------|-------------|----------|-------|
| **Crew** (deckhand/steward) | | | Lowest privilege. Many mutations should 403. |
| **HOD** (chief_engineer) | | | Engineering dept. Can sign handovers, manage WOs. Cannot: adjust stock, decommission, archive. |
| **Captain** | | | Full access. SIGNED actions require PIN. Sees all departments in ledger. |
| **Fleet Manager** | | | Multi-vessel. Test vessel switching. Full access + fleet view. |

---

## ROLE PERMISSION MATRIX

**R = Allowed | X = Expect 403 | S = Signed (PIN required) | — = N/A**

| Action | Crew | HOD | Captain | Fleet Mgr |
|--------|------|-----|---------|-----------|
| View any entity (read) | R | R | R | R |
| report_fault | R | R | R | R |
| add_fault_note | R | R | R | R |
| add_wo_note | R | R | R | R |
| add_equipment_note | R | R | R | R |
| add_part_note | R | R | R | R |
| add_po_note | R | R | R | R |
| add_document_note | R | R | R | R |
| add_warranty_note | R | R | R | R |
| flag_equipment_attention | R | R | R | R |
| upsert_hours_of_rest | R | R | R | R |
| investigate_fault | X | R | R | R |
| resolve_fault | X | R | R | R |
| close_fault | X | R | R | R |
| create_work_order | X | R | R | R |
| start_work_order | X | R | R | R |
| close_work_order | X | R | R | R |
| add_wo_part | X | R | R | R |
| add_wo_hours | X | R | R | R |
| reassign_work_order | X | R | R | R |
| create_work_order_for_equipment | X | R | R | R |
| sign_handover | X | R | R | R |
| add_to_handover | X | R | R | R |
| cancel_po | X | R | R | R |
| upload_document | X | R | R | R |
| accept_receiving | X | R | R | R |
| approve_shopping_list_item | X | R | R | R |
| reject_shopping_list_item | X | R | R | R |
| archive_fault | X | X | S | S |
| archive_work_order | X | X | S | S |
| decommission_equipment | X | X | S | S |
| archive_handover | X | X | S | S |
| adjust_stock_quantity | X | X | S | S |
| write_off_part | X | X | S | S |

**NOTE: Frontend shows ALL buttons to ALL roles.** Backend enforces via 403. If crew clicks "Archive" they'll see a 403 — the button shouldn't be visible but is. Log these as UX bugs.

---

## PART 1: NAVIGATION & SHELL

### 1.1 Login & Auth

| # | Action | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------|------|-----|------|-------|---------|
| 1.1 | Enter valid credentials, Sign In | Redirect to `/` | | | | | |
| 1.2 | Enter invalid credentials | Error message, no redirect | | | | | |
| 1.3 | Forgot Password (if exists) | Reset email sent | | | | | |
| 1.4 | Sign Out (hamburger menu) | `supabase.auth.signOut()`, redirect `/login` | | | | | |

### 1.2 Sidebar Navigation (test every item loads)

| # | Item | URL | Crew | HOD | Capt | Fleet | Console |
|---|------|-----|------|-----|------|-------|---------|
| 1.5 | Vessel Surface | `/` | | | | | |
| 1.6 | Work Orders | `/work-orders` | | | | | |
| 1.7 | Faults | `/faults` | | | | | |
| 1.8 | Equipment | `/equipment` | | | | | |
| 1.9 | Handover | `/handover-export` | | | | | |
| 1.10 | Hours of Rest | `/hours-of-rest` | | | | | |
| 1.11 | Email | `/email` | | | | | |
| 1.12 | Parts / Inventory | `/inventory` | | | | | |
| 1.13 | Shopping List | `/shopping-list` | | | | | |
| 1.14 | Purchase Orders | `/purchasing` | | | | | |
| 1.15 | Receiving | `/receiving` | | | | | |
| 1.16 | Certificates | `/certificates` | | | | | |
| 1.17 | Documents | `/documents` | | | | | |
| 1.18 | Warranties | `/warranties` | | | | | |

### 1.3 Topbar & Global Actions

| # | Action | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------|------|-----|------|-------|---------|
| 1.19 | Click search bar | Search overlay opens | | | | | |
| 1.20 | Press Cmd+K | Search overlay opens | | | | | |
| 1.21 | Type query, press Enter | Results grouped by entity type | | | | | |
| 1.22 | Click a search result | Navigate to entity detail, overlay closes | | | | | |
| 1.23 | Press Esc in search | Overlay closes | | | | | |
| 1.24 | Hamburger > Activity Log | Ledger panel opens (right drawer, 480px) | | | | | |
| 1.25 | Hamburger > Settings | Settings modal opens | | | | | |
| 1.26 | Hamburger > Command Center | **KNOWN BUG: opens search, not command palette** | | | | | |
| 1.27 | Vessel selector (Fleet only) | Dropdown shows all vessels in fleet | — | — | — | | |
| 1.28 | Switch vessel (Fleet only) | All data reloads for new vessel | — | — | — | | |
| 1.29 | Switch to "All Vessels" | Fleet overview mode | — | — | — | | |

### 1.4 Vessel Surface (Home Page)

| # | Action | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------|------|-----|------|-------|---------|
| 1.30 | Page loads | All cards render with live data | | | | | |
| 1.31 | Click Work Order row | Navigate to `/work-orders?id={id}` | | | | | |
| 1.32 | Click "Create Work Order" quick action | Navigate to `/work-orders` | | | | | |
| 1.33 | Click Fault row | Navigate to `/faults?id={id}` | | | | | |
| 1.34 | Click "Log Fault" quick action | Navigate to `/faults` | | | | | |
| 1.35 | Click Parts Below Min row | Navigate to `/inventory?id={id}` | | | | | |
| 1.36 | Click "Add to Shopping List" quick action | Navigate to `/shopping-list` | | | | | |
| 1.37 | Click Last Handover row | Navigate to `/handover-export?id={id}` | | | | | |
| 1.38 | Click Certificate row | Navigate to `/certificates?id={id}` | | | | | |
| 1.39 | Click Recent Activity row | Navigate to correct entity page | | | | | |
| 1.40 | Error state: "Try Again" button | Refetches surface data | | | | | |

### 1.5 Settings Modal

| # | Action | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------|------|-----|------|-------|---------|
| 1.41 | Account tab > Theme dropdown | Theme changes (light/dark/system), persists on reload | | | | | |
| 1.42 | Security tab | Renders | | | | | |
| 1.43 | Apps tab > Connect (Microsoft 365) | OAuth flow or link | | | | | |
| 1.44 | Data tab > Export | Download activity log | | | | | |
| 1.45 | Help tab > Send support message | Opens mailto | | | | | |
| 1.46 | About tab > Terms/Privacy links | Open in new tab | | | | | |
| 1.47 | Esc or X | Settings closes | | | | | |

### 1.6 Ledger Panel

| # | Action | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------|------|-----|------|-------|---------|
| 1.48 | "Me" toggle | Shows only your events | | | | | |
| 1.49 | "Department" toggle | **Crew: own only. HOD: engineering only. Captain: all depts** | | | | | |
| 1.50 | "Reads" eye toggle | Shows/hides read events | | | | | |
| 1.51 | Click day header | Expands/collapses day group | | | | | |
| 1.52 | Click event row | Navigate to entity, panel closes | | | | | |
| 1.53 | Scroll to bottom | Infinite scroll loads more events | | | | | |
| 1.54 | After a mutation (e.g. add note) | New ledger entry appears in panel | | | | | |

---

## PART 2: ENTITY LENSES — EVERY ACTION PER LENS

### 2.1 Work Orders

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.1 | List loads | | Work order rows render | | | | | |
| 2.2 | Click row | | Detail lens opens | | | | | |
| 2.3 | Sort by column | | Re-sorts | | | | | |
| 2.4 | Filter by status | | Filters correctly | | | | | |
| 2.5 | **"Start Work"** primary | `start_work_order` | Status → in_progress | X | | | | |
| 2.6 | **"Mark Complete"** primary | `close_work_order`, payload: `{close_reason}` | Status → completed, ledger entry | X | | | | |
| 2.7 | Dropdown > **Add Note** | `add_wo_note`, payload: `{note_text}` | AddNoteModal opens → type text → submit → note appears in Notes section | | | | | |
| 2.8 | Dropdown > **Add Part** | `add_wo_part`, payload: `{part_id}` | AddPartModal opens → select part → submit → part appears | X | | | | |
| 2.9 | Dropdown > **Add Hours** | `add_wo_hours`, payload: `{hours, description}` | ActionPopup form → submit → hours recorded | X | | | | |
| 2.10 | Dropdown > **Reassign** | `reassign_work_order`, payload: `{assigned_to}` | Person picker → submit → assigned_to changes | X | | | | |
| 2.11 | Dropdown > **Archive** (danger) | `archive_work_order` | **SIGNED (L3 PIN).** Crew+HOD: 403 | X | X | S | S | |
| 2.12 | Notes section > "Add Note" button | Same as 2.7 | Modal opens, submit works | | | | | |
| 2.13 | Attachments > Upload | | **TODO: empty handler, no modal** | | | | | |
| 2.14 | Checklist > check item | | Item state updates | | | | | |
| 2.15 | History > expand | | Change history renders | | | | | |
| 2.16 | Audit Trail > expand | | Ledger events render | | | | | |
| 2.17 | Related button | | Drawer opens with related entities | | | | | |
| 2.18 | Related drawer > click entity | | Navigate to that entity | | | | | |

### 2.2 Faults

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.19 | List loads | | Fault rows render | | | | | |
| 2.20 | Click row | | Detail lens opens | | | | | |
| 2.21 | **"Investigate"** primary | `investigate_fault` (if status=open) | Status → investigating | X | | | | |
| 2.22 | **"Resolve Fault"** primary | `resolve_fault`, payload: `{resolution_notes, resolution}` | Status → resolved, ledger entry | X | | | | |
| 2.23 | **"Close Fault"** primary | `close_fault` (if status=resolved) | Status → closed | X | | | | |
| 2.24 | Dropdown > **Add Note** | `add_fault_note`, payload: `{note_text}` | Modal → type → submit → note in metadata → appears after refetch | | | | | |
| 2.25 | Dropdown > **Archive** (danger) | `archive_fault` | **SIGNED.** Crew+HOD: 403 | X | X | S | S | |
| 2.26 | Notes section > "Add Note" | Same as 2.24 | Works | | | | | |
| 2.27 | Attachments > Upload | | **TODO: empty handler** | | | | | |
| 2.28 | Related button | | Drawer opens | | | | | |

### 2.3 Equipment

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.29 | List loads | | Equipment rows render | | | | | |
| 2.30 | Click row | | Detail lens opens | | | | | |
| 2.31 | **"Create Work Order"** primary | `create_work_order_for_equipment`, payload: `{title, description, priority}` | Priority must be routine/critical (NOT low/medium/high). WO created. | X | | | | |
| 2.32 | Dropdown > **Flag for Attention** | `flag_equipment_attention` | L0 — fires immediately, no modal | | | | | |
| 2.33 | Dropdown > **Add Note** | `add_equipment_note`, payload: `{note_text}` | Modal → submit → note appears | | | | | |
| 2.34 | Dropdown > **Decommission** (danger) | `decommission_equipment` | **SIGNED (L3 PIN).** Crew+HOD: 403 | X | X | S | S | |
| 2.35 | Spare Parts section | | Shows linked parts | | | | | |
| 2.36 | Work Orders section > click WO | | Navigate to work order | | | | | |
| 2.37 | Faults section > click fault | | Navigate to fault | | | | | |
| 2.38 | Certificates section > click cert | | Navigate to certificate | | | | | |
| 2.39 | Related button | | Drawer opens | | | | | |

### 2.4 Handover

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.40 | `/handover-export` loads | | Tabbed: Queue + Draft | | | | | |
| 2.41 | Queue tab renders | | 4 sections: Open Faults, Overdue WOs, Low Stock, Pending Orders | | | | | |
| 2.42 | Queue > expand section | | Items with ref codes shown | | | | | |
| 2.43 | Queue > **"Add to draft"** | `add_to_handover`, payload: `{summary, entity_type, entity_id}` | Item moves to "already queued" state, refetch shows it | X | | | | |
| 2.44 | Draft tab | | Shows items added to draft | | | | | |
| 2.45 | Draft > edit item | | Edit popup saves changes | | | | | |
| 2.46 | Draft > delete item | | Item removed | | | | | |
| 2.47 | Draft > **"Export Handover"** | POST export | Navigate to `/handover-export/[id]` | | | | | |
| 2.48 | Completed lens loads | | Handover document renders | | | | | |
| 2.49 | **"Sign Handover"** primary | `sign_handover` (if status in draft/pending) | **Wet signature canvas (L4).** Draw signature → confirm → `signature: <PNG data URL>` sent | X | | | | |
| 2.50 | Dropdown > **Sign Incoming** | `sign_handover_incoming` | ActionPopup opens | X | | | | |
| 2.51 | Dropdown > **Export PDF** | `window.print()` | Browser print dialog | | | | | |
| 2.52 | Dropdown > **Regenerate Summary** | `regenerate_handover_summary` | Summary regenerated | | | | | |
| 2.53 | Dropdown > **Archive** (danger) | `archive_handover` | **SIGNED.** Crew+HOD: 403 | X | X | S | S | |
| 2.54 | Dropdown > **Delete** (danger) | `delete_handover` | **SIGNED.** Crew+HOD: 403 | X | X | S | S | |

### 2.5 Hours of Rest

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.55 | List loads | | HoR records render with compliance status | | | | | |
| 2.56 | Click row | | Detail opens | | | | | |
| 2.57 | **"Submit Hours"** primary | `upsert_hours_of_rest` (if draft/pending) | Hours recorded | | | | | |
| 2.58 | Compliance alert banner | | Shows if violations detected | | | | | |

### 2.5b Hours of Rest — Monthly Sign-Off (MLC 2006 3-tier)

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.59 | `/hours-of-rest/signoffs` loads | | Signoff list renders | | | | | |
| 2.60 | Click signoff row | | Detail opens | | | | | |
| 2.61 | **"Sign as Crew"** (status=draft) | `sign_monthly_signoff` | Crew signs → status → crew_signed | | | | | |
| 2.62 | **"Counter-Sign as HOD"** (status=crew_signed) | `sign_monthly_signoff` | **Only HOD+ can click.** Crew: button disabled with reason | X | | | | |
| 2.63 | **"Final Sign as Master"** (status=hod_signed) | `sign_monthly_signoff` | **Only Captain can click.** HOD: button disabled with reason | X | X | | | |
| 2.64 | Status=finalized | | Button shows "Finalized" (disabled) | | | | | |

### 2.6 Email

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.65 | `/email` loads | | Thread list renders | | | | | |
| 2.66 | Filter: All / Unlinked / Linked | | List filters correctly | | | | | |
| 2.67 | Click refresh icon | | Threads re-fetched | | | | | |
| 2.68 | Click thread row | | Thread detail in right pane | | | | | |
| 2.69 | **"Link Email"** | LinkEmailModal → select entity → submit | **KNOWN BUG: `link_email` action doesn't exist in registry** | | | | | |
| 2.70 | Esc in LinkEmailModal | | Modal closes | | | | | |

### 2.7 Inventory / Parts

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.71 | `/inventory` loads | | Parts list renders | | | | | |
| 2.72 | Click row | | Detail opens | | | | | |
| 2.73 | View part | | Name, qty, location, manufacturer, status pill | | | | | |
| 2.74 | **Add Note** | `add_part_note`, payload: `{note_text}` | Note saved AND linked to part | | | | | |
| 2.75 | **Reorder** primary (if low stock) | `reorder_part` | ActionPopup → submit | X | | | | |
| 2.76 | **Adjust Stock** primary (if normal) | `adjust_stock_quantity`, payload: `{quantity, reason}` | **SIGNED (L3 PIN).** Crew+HOD: 403 | X | X | S | S | |
| 2.77 | **Write Off Part** | `write_off_part`, payload: `{quantity, reason}` | **SIGNED (L3 PIN+TOTP).** Crew+HOD: 403. Ledger entry must appear. | X | X | S | S | |
| 2.78 | **Log Part Usage** | `log_part_usage` | ActionPopup → submit | X | | | | |

### 2.8 Shopping List

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.79 | `/shopping-list` loads | | Items render with lifecycle progress bar | | | | | |
| 2.80 | Click row | | Detail opens | | | | | |
| 2.81 | **"Submit List"** primary (if draft) | `submit_list` | Status → submitted | X | | | | |
| 2.82 | **"Convert to PO"** primary (if approved) | `convert_to_po` | PO created from list | X | | | | |
| 2.83 | Dropdown > **Approve** | `approve_shopping_list_item`, payload: `{quantity_approved}` | Item approved | X | | | | |
| 2.84 | Dropdown > **Reject** | `reject_shopping_list_item`, payload: `{rejection_reason}` | Item rejected | X | | | | |
| 2.85 | Dropdown > **Archive** (danger) | `archive_list` | Soft delete | X | | | | |

### 2.9 Purchase Orders

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.86 | `/purchasing` loads | | PO list renders | | | | | |
| 2.87 | Click row | | Detail lens opens | | | | | |
| 2.88 | **"Submit"** primary (if draft) | `submit_po` | Status → submitted | X | | | | |
| 2.89 | **"Approve"** primary (if submitted) | `approve_po` | Status → approved | X | | | | |
| 2.90 | **"Receive Goods"** primary (if approved) | `receive_po` | Status → received | X | | | | |
| 2.91 | Dropdown > **Add Note** | `add_po_note`, payload: `{note_text}` | Note saved AND linked to PO | | | | | |
| 2.92 | Dropdown > **Track Delivery** | `track_po_delivery` | Tracking info | X | | | | |
| 2.93 | Dropdown > **Cancel** (danger) | `cancel_po` | Soft delete (deleted_at set) | X | | | | |
| 2.94 | Attachments > Upload | | **TODO: empty handler** | | | | | |

### 2.10 Receiving

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.95 | `/receiving` loads | | List renders | | | | | |
| 2.96 | Click row | | Detail opens | | | | | |
| 2.97 | `/receiving/new` loads | | Upload wizard renders | | | | | |
| 2.98 | **New: select doc type** | Dropdown: Invoice/Packing Slip/Photo/Other | Type selected | | | | | |
| 2.99 | **New: upload file** | Accept: JPG/PNG/HEIC/PDF, max 15MB | File preview shown | | | | | |
| 2.100 | **New: "Upload & Process"** | `create_receiving` + upload | Creates receiving, uploads doc, shows extracted data. 503 → retries 3x with 30s wait. | X | | | | |
| 2.101 | **New: review extracted data** | | Table shows OCR fields (vendor, total, line items) | | | | | |
| 2.102 | **New: "Save to Database"** | Saves + auto-populates line items | Navigate to `/receiving/{id}`, toast "Receiving logged" | | | | | |
| 2.103 | Detail > **"Complete Receiving"** | `accept_receiving` | Status → completed | X | | | | |
| 2.104 | Detail > **"Report Discrepancy"** | `reject_receiving` / `flag_discrepancy` | Discrepancy flagged | X | | | | |

### 2.11 Certificates

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.105 | `/certificates` loads | | List renders with status (valid/expiring/expired) | | | | | |
| 2.106 | Click row | | Detail lens opens | | | | | |
| 2.107 | **"Renew Certificate"** primary | `renew_certificate` (if not revoked) | **STUB: returns NOT_IMPLEMENTED** | | | | | |
| 2.108 | Dropdown > **Add Note** | `add_certificate_note`, payload: `{note_text}` | **KNOWN BUG: may fail (pms_certificates vs pms_vessel_certificates)** | | | | | |
| 2.109 | Dropdown > **Suspend** (danger) | `suspend_certificate` | Soft delete | X | | | | |
| 2.110 | Dropdown > **Revoke** (danger) | `revoke_certificate` | Permanent revocation | X | X | S | S | |

### 2.12 Documents

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.111 | `/documents` loads | | List renders | | | | | |
| 2.112 | Click row | | Detail lens opens | | | | | |
| 2.113 | **Download** primary | Browser download (if file_url exists) | File downloads | | | | | |
| 2.114 | Dropdown > **Add Note** | `add_document_note`, payload: `{note_text}` | Note saved AND linked to document | | | | | |
| 2.115 | Dropdown > **Archive** (danger) | `archive_document` | Soft delete | X | | | | |

### 2.13 Warranties

| # | Action | Payload/Details | Expected | Crew | HOD | Capt | Fleet | Console |
|---|--------|----------------|----------|------|-----|------|-------|---------|
| 2.116 | `/warranties` loads | | List renders | | | | | |
| 2.117 | Click row | | Detail lens opens | | | | | |
| 2.118 | **"Submit Claim"** primary | `file_warranty_claim` (if active/expiring) | Claim filed | X | | | | |
| 2.119 | Dropdown > **Add Note** | `add_warranty_note`, payload: `{note_text}` | Note saved AND linked | | | | | |
| 2.120 | Dropdown > **Archive** (danger) | `archive_warranty` | Soft delete | X | | | | |
| 2.121 | Dropdown > **Void** (danger) | `void_warranty` | Warranty voided | X | X | S | S | |

---

## PART 3: SIGNATURE JOURNEYS

Test each signature level end-to-end. Must be Captain or Fleet Manager for signed actions.

| # | Level | Test Action | Steps | Expected | Capt | Fleet | Console |
|---|-------|-------------|-------|----------|------|-------|---------|
| 3.1 | **L0** (no modal) | `flag_equipment_attention` | Click button. NO modal appears. | Action fires immediately, result in UI | | | |
| 3.2 | **L1** (confirm) | Any standard mutation | Click → ActionPopup with "Confirm" button → click Confirm | Action fires, result in UI | | | |
| 3.3 | **L3** (PIN) | `archive_work_order` | Click → ActionPopup shows 4-digit PIN boxes → enter PIN → click "Verify" | Action fires if PIN correct | | | |
| 3.4 | **L3 wrong PIN** | `archive_work_order` | Enter wrong PIN → submit | Error shown in popup, modal stays open for retry | | | |
| 3.5 | **L3 incomplete PIN** | `archive_work_order` | Enter 3 digits only | "Verify" button disabled | | | |
| 3.6 | **L4** (wet signature) | `sign_handover` | Click → canvas appears → draw signature → enter name → click "Sign" | Signature PNG sent, action fires | | | |
| 3.7 | **L4 clear** | `sign_handover` | Draw signature → click "Clear" | Canvas resets | | | |
| 3.8 | **L4 no name** | `sign_handover` | Draw signature, leave name empty | "Sign" button disabled | | | |

---

## PART 4: WORKFLOW JOURNEYS (Multi-Step)

### 4.1 Fault → Work Order → Complete

| # | Step | Action | Expected | HOD | Capt | Console |
|---|------|--------|----------|-----|------|---------|
| 4.1 | Report a fault | `report_fault` via ReportFaultModal: fill title, description, severity, equipment_id → submit | Fault created, appears in fault list | | | |
| 4.2 | Investigate the fault | Open fault → "Investigate" primary | Status → investigating | | | |
| 4.3 | Create WO from equipment | Open equipment (linked) → "Create Work Order" → fill title, priority (routine/critical) → submit | WO created, linked to equipment | | | |
| 4.4 | Add part to WO | Open WO → "Add Part" → select part → submit | Part appears in WO parts section | | | |
| 4.5 | Add hours to WO | "Add Hours" → fill hours → submit | Hours recorded | | | |
| 4.6 | Complete WO | "Mark Complete" → fill close_reason → submit | Status → completed, ledger entry | | | |
| 4.7 | Resolve fault | Go back to fault → "Resolve" → fill resolution → submit | Status → resolved, ledger entry | | | |
| 4.8 | Close fault | "Close Fault" | Status → closed | | | |

### 4.2 Handover Lifecycle

| # | Step | Action | Expected | HOD | Capt | Console |
|---|------|--------|----------|-----|------|---------|
| 4.9 | View queue | `/handover-export` → Queue tab | Sections show open items | | | |
| 4.10 | Add items to draft | Click "Add to draft" on 2-3 items | Items move to "already queued" | | | |
| 4.11 | Review draft | Draft tab | Added items shown | | | |
| 4.12 | Edit a draft item | Click edit → change text → save | Text updates | | | |
| 4.13 | Export handover | "Export Handover" → submit | Navigate to completed handover lens | | | |
| 4.14 | Outgoing signs | "Sign Handover" → draw on canvas → confirm | Outgoing signature recorded | | | |
| 4.15 | Incoming signs | Dropdown > "Sign Incoming" → ActionPopup | Incoming signature recorded | | | |

### 4.3 Receiving Lifecycle

| # | Step | Action | Expected | HOD | Capt | Console |
|---|------|--------|----------|-----|------|---------|
| 4.16 | Start new receiving | `/receiving/new` → select type → upload photo/invoice | File uploaded, OCR extracted | | | |
| 4.17 | Review extracted data | Table shows vendor, total, line items | Data correct | | | |
| 4.18 | Save to database | "Save to Database" | Navigate to receiving detail, toast shown | | | |
| 4.19 | Complete receiving | "Complete Receiving" | Status → completed | | | |

### 4.4 PO Lifecycle

| # | Step | Action | Expected | HOD | Capt | Console |
|---|------|--------|----------|-----|------|---------|
| 4.20 | Open a draft PO | `/purchasing` → click draft PO | Detail opens | | | |
| 4.21 | Submit PO | "Submit" primary | Status → submitted | | | |
| 4.22 | Approve PO | "Approve" primary | Status → approved | | | |
| 4.23 | Add note | "Add Note" → type → submit | Note appears linked to PO | | | |
| 4.24 | Cancel PO (danger) | "Cancel" → confirm | Soft deleted (deleted_at set) | | | |

### 4.5 HoR Sign-Off Chain (MLC 2006)

| # | Step | Role | Action | Expected | Console |
|---|------|------|--------|----------|---------|
| 4.25 | Crew signs | Crew | Open signoff → "Sign as Crew" | Status → crew_signed | |
| 4.26 | HOD counter-signs | HOD | Open same signoff → "Counter-Sign as HOD" | Status → hod_signed. **Crew should see button disabled.** | |
| 4.27 | Captain final-signs | Captain | Open same signoff → "Final Sign as Master" | Status → finalized. **HOD should see button disabled.** | |

---

## PART 5: MODALS (test from any context)

| # | Modal | Trigger | Fields | Expected | Crew | HOD | Capt | Fleet | Console |
|---|-------|---------|--------|----------|------|-----|------|-------|---------|
| 5.1 | ReportFaultModal | Subbar button on `/faults` | title, description, severity, equipment_id, create_work_order checkbox | `report_fault` fires, fault created | | | | | |
| 5.2 | CreateWorkOrderModal | Subbar button on `/work-orders` | equipment_id, title, description, priority, assigned_to | `create_work_order` fires, WO created | X | | | | |
| 5.3 | AddNoteModal (any entity) | Dropdown "Add Note" or section button | note_text (textarea) | Note saved, appears after refetch | | | | | |
| 5.4 | ActionPopup (read-only, L0) | Any L0 action | None | Fires immediately, no UI | | | | | |
| 5.5 | ActionPopup (form fields) | Action with required_fields | Dynamic fields from backend | Form renders, submit works | | | | | |
| 5.6 | ActionPopup (PIN, L3) | Signed action | 4-digit PIN | PIN entry, verify button | | | S | S | |
| 5.7 | ActionPopup (wet signature, L4) | sign_handover | Canvas + name + date | Draw, sign, confirm | | | | | |
| 5.8 | Any modal > Esc | | | Closes without submitting | | | | | |
| 5.9 | Any modal > click outside | | | Closes without submitting | | | | | |

---

## KNOWN BUGS & LIMITATIONS

| # | Bug | Status | Impact |
|---|-----|--------|--------|
| K.1 | Command Center opens search overlay instead of command palette | Not fixed (parked) | UX — no command surface |
| K.2 | `link_email` action doesn't exist in registry | Not fixed | Email linking silently fails |
| K.3 | `add_certificate_note` — pms_certificates vs pms_vessel_certificates table mismatch | Not fixed (deferred) | Cert notes may 404 |
| K.4 | `renew_certificate` is a stub | By design | Returns NOT_IMPLEMENTED |
| K.5 | `classify_fault`, `suggest_parts` are stubs | By design | Returns NOT_IMPLEMENTED |
| K.6 | Upload buttons on all lenses are empty `() => {}` | TODO — no upload modal component | No file uploads work |
| K.7 | Frontend shows all buttons to all roles — no role gating | By design (backend enforces) | Crew sees buttons they can't use |
| K.8 | PM schedule actions blocked — `pms_maintenance_schedules` table missing | Schema gap | Needs migration |
| K.9 | PO/Document/Warranty note display — unconfirmed if entity endpoint returns notes | Unverified | Notes may save but not display |
| K.10 | Handover "Export PDF" uses `window.print()` not real export | By design | Basic print, no PDF generation |

---

## RESULTS SUMMARY

### Crew
**Tested:** ___ | **PASS:** ___ | **FAIL:** ___ | **403 (expected):** ___ | **403 (unexpected):** ___

### HOD (Chief Engineer)
**Tested:** ___ | **PASS:** ___ | **FAIL:** ___ | **403 (expected):** ___ | **403 (unexpected):** ___

### Captain
**Tested:** ___ | **PASS:** ___ | **FAIL:** ___ | **Signed passed:** ___/___ | **PIN rejected correctly:** ___

### Fleet Manager
**Tested:** ___ | **PASS:** ___ | **FAIL:** ___ | **Vessel switch:** YES / NO | **All vessels view:** YES / NO

### Critical Failures
1.
2.
3.

### Console Errors
1.
2.
3.

### Buttons Visible But Should Be Hidden (Role Gating Gaps)
1.
2.
3.

### Notes

