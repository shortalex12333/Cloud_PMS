# Phase 2 — Lens Inventory & Design Research

**Date:** 2026-03-16
**Status:** Research complete — ready for design
**Author:** Celeste7

---

## 1. Lens Types Identified (14 Total)

| # | Entity Type | Route | Lens Component | Maturity |
|---|------------|-------|----------------|----------|
| 1 | Work Orders | `/work-orders/[id]` | `WorkOrderLensContent.tsx` | Production |
| 2 | Faults | `/faults/[id]` | `FaultLensContent.tsx` | Production |
| 3 | Equipment | `/equipment/[id]` | `EquipmentLensContent.tsx` | Production |
| 4 | Inventory / Parts | `/inventory/[id]` | `PartsLensContent.tsx` | Production |
| 5 | Certificates | `/certificates/[id]` | `CertificateLensContent.tsx` | Production |
| 6 | Documents | `/documents/[id]` | `DocumentLensContent.tsx` | Production |
| 7 | Receiving | `/receiving/[id]` | `ReceivingLensContent.tsx` | Production |
| 8 | Shopping List | `/shopping-list/[id]` | `ShoppingListLensContent.tsx` | Production |
| 9 | Purchase Orders | `/purchasing/[id]` | `PurchaseOrderLensContent.tsx` | Production |
| 10 | Hours of Rest | `/hours-of-rest/[id]` | `HoursOfRestLensContent.tsx` | Production |
| 11 | Handover Notes | `/handover-export/[id]` | `HandoverLensContent.tsx` | Production |
| 12 | Handover Exports | `/handover-export/[id]` | `HandoverExportLensContent.tsx` | Production |
| 13 | Warranties | `/warranties/[id]` | `WarrantyLensContent.tsx` | Production |
| 14 | Email Threads | `/email` | `EmailThreadViewer.tsx` | Inbox only |

---

## 2. Design Groups (for parallel agent work)

### Group A: Core Operations (lens 1-4)

These are the most complex lenses with the most actions and data fields.

| Lens | Data Fields | Actions | Signatures | Complexity |
|------|------------|---------|------------|------------|
| **Work Orders** | wo_number, title, description, status (8 states), priority (4), equipment, assigned_to, due_date, child: parts, notes, attachments, history | Mark Complete, Reassign, Archive, Add Note, Add Part, Add Hours, Edit | PIN+TOTP for completion | Very High |
| **Faults** | fault_number, title, description, status (4), severity (4), equipment, reported_by, timestamps | Add Note, Add Photo, Acknowledge, Close, Reopen, Mark False Alarm, Create WO | None (role-gated) | High |
| **Equipment** | equipment_number, name, description, category, location, manufacturer, model, serial, status (4), maintenance dates | Report Fault, Create WO, Schedule Maintenance | None | Medium |
| **Inventory/Parts** | part_name, part_number, qty_on_hand, min_qty, location, unit, unit_cost, supplier, image_url, stock_movements | Consume, Receive, Transfer, Adjust Stock, Write Off, Add to Shopping List | PIN+TOTP for Write Off | High |

### Group B: Compliance & Supply Chain (lens 5-8)

| Lens | Data Fields | Actions | Signatures | Complexity |
|------|------------|---------|------------|------------|
| **Certificates** | name, type, issuing_authority, issue_date, expiry_date, status (3), certificate_number | Edit, Renew, Archive | None | Low |
| **Documents** | filename, title, description, mime_type, file_size, url, thumbnail_url, classification | Download, Link to Entity, Share, Archive | None | Medium |
| **Receiving** | vendor_name, vendor_ref, po_number, status (4), received_date, total, currency, items[] | Accept, Reject, Edit Items, Add Attachment | Optional signature | Medium |
| **Shopping List** | title, status (4), requester, approver, items[] with urgency levels | Approve, Reject, Order, Add/Remove Item | None (role-gated) | Low |

### Group C: Procurement, Compliance & Special (lens 9-12)

| Lens | Data Fields | Actions | Signatures | Complexity |
|------|------------|---------|------------|------------|
| **Purchase Orders** | po_number, status (8), supplier, order_date, delivery_date, total, items[] | Approve, Cancel, Mark Received, Edit, Add Item | None (role-gated) | Medium |
| **Hours of Rest** | crew_name, date, rest_hours, work_hours, is_compliant, rest_periods[] | Update Record, Add Rest Period, Verify/Approve | None (role-gated) | Medium |
| **Handover Exports** | title, item_count, review_status (3), edited_content{sections[]}, signatures{outgoing, incoming, hod} | Edit Content, Sign (3 tiers), Generate PDF | Canvas + PIN+TOTP for HOD | Very High |
| **Warranties** | title, equipment, supplier, start_date, expiry_date, status (3), coverage, terms | Renew, Claim, Archive | None | Low |

### Not Grouped: Email Threads (lens 14)

Email is an inbox pattern, not a traditional entity lens. Deferred from lens redesign — requires separate messaging UX design.

---

## 3. Universal Lens Structure

Every lens follows this anatomy:

```
┌─────────────────────────────────────────────────────┐
│  LensHeader (56px, fixed)                            │
│  [← Back] [→ Forward]    WORK ORDER    [Related] [×] │
├─────────────────────────────────────────────────────┤
│  LensTitleBlock                                      │
│  WO-1042 — Emergency Valve Replacement               │
│  Engine Room · Assigned to R. Chen                   │
├─────────────────────────────────────────────────────┤
│  VitalSignsRow (5 indicators)                        │
│  [Status: In Progress] [Priority: Critical]          │
│  [Equipment: E-007] [Assigned: R. Chen]              │
│  [Due: 17 Mar 2026]                                  │
├─────────────────────────────────────────────────────┤
│  Description / Summary Block                         │
├─────────────────────────────────────────────────────┤
│  Action Buttons Row                                  │
│  [Mark Complete] [Reassign] [Add Note] [Add Part]    │
├─────────────────────────────────────────────────────┤
│  ─── NOTES ─────────────────────────── [+ Add] ──   │
│  [Note entries...]                                   │
├─────────────────────────────────────────────────────┤
│  ─── PARTS ─────────────────────────── [+ Add] ──   │
│  [Part consumption entries...]                       │
├─────────────────────────────────────────────────────┤
│  ─── ATTACHMENTS ───────────────────── [Upload] ──   │
│  [File cards...]                                     │
├─────────────────────────────────────────────────────┤
│  ─── HISTORY ────────────────────────────────── ──   │
│  [Timeline entries...]                               │
├─────────────────────────────────────────────────────┤
│  ─── RELATED ENTITIES ──────────────────────── ──   │
│  [Entity cards...]                                   │
└─────────────────────────────────────────────────────┘
```

---

## 4. Status/Colour Mappings (Universal)

| Semantic | Colour Token | Entity Examples |
|----------|-------------|-----------------|
| Critical / Error / Expired | `--red` | Non-compliant, out of stock, faulty, expired, critical severity |
| Warning / In Progress / Pending | `--amber` | Pending approval, low stock, maintenance, expiring soon |
| Success / Operational / Complete | `--green` | Completed, operational, in stock, active, compliant |
| Neutral / Draft / Unknown | `--txt3` | Draft, cancelled, unknown status |

---

## 5. Signature Matrix

| Tier | Method | Used By | UI Treatment |
|------|--------|---------|-------------|
| P0 — Inline | Canvas signature image | Handover outgoing/incoming | SignatureCanvas component, modal with drawing pad |
| P1 — Strong | PIN + TOTP | WO completion, Part write-off | Two-step modal: enter PIN → enter TOTP code |
| P2 — Loose | Role check only | Receiving acceptance, some archives | Confirmation modal with checkbox |

---

## 6. Shared Components

| Component | Location | Used By |
|-----------|----------|---------|
| `LensHeader` | `components/lens/LensHeader.tsx` | All lenses |
| `LensTitleBlock` | `components/lens/LensTitleBlock.tsx` | All lenses |
| `VitalSignsRow` | (inline pattern) | All lenses |
| `NotesSection` | `components/lens/sections/NotesSection.tsx` | WO, Faults |
| `PartsSection` | `components/lens/sections/PartsSection.tsx` | WO |
| `AttachmentsSection` | `components/lens/sections/AttachmentsSection.tsx` | All that support files |
| `HistorySection` | `components/lens/sections/HistorySection.tsx` | WO, Faults, Equipment |
| `RelatedEntitiesSection` | `components/lens/sections/RelatedEntitiesSection.tsx` | All lenses |
| `StatusPill` | (shared component) | All lenses |
| `DocumentCard` | `components/documents/DocumentCard.tsx` | Documents, Attachments |
| `SignatureCanvas` | `components/lens/handover-export-sections/SignatureCanvas.tsx` | Handover Exports |

---

## 7. Data Sources by Lens

| Lens | Primary Table | Child Tables | Media/Files |
|------|--------------|-------------|-------------|
| Work Orders | `work_orders` | `work_order_notes`, `work_order_parts`, `work_order_attachments` | Attachment files |
| Faults | `faults` | `fault_notes`, `fault_attachments` | Photos |
| Equipment | `equipment` | — | Equipment images |
| Parts | `parts` / `inventory` | `stock_movements` | Part images |
| Certificates | `certificates` | `certificate_attachments` | Certificate PDFs |
| Documents | `documents` | `document_chunks` | Original files (PDF, DOCX, etc.) |
| Receiving | `receiving` | `receiving_items` | Delivery documents |
| Shopping List | `shopping_lists` | `shopping_list_items` | — |
| Purchase Orders | `purchase_orders` | `purchase_order_items` | PO documents |
| Hours of Rest | `hours_of_rest` | `rest_periods` | — |
| Handover Notes | `handover_items` | — | — |
| Handover Exports | `handover_exports` | `handover_items` (linked) | HTML/PDF exports (2-bucket) |
| Warranties | `warranties` | — | Warranty documents |
| Email | `email_threads` | `email_messages` | Email attachments |

---

## 8. Design Phase Plan

For each lens group (A, B, C), spawn 3 parallel agents:

1. **Agent 1 — Data Baseline:** Read the actual lens component, its types file, and API handler. Document every field that can be displayed, every child entity, every media type.

2. **Agent 2 — Actions & Flows:** Read the action hooks, mutation handlers, and signature mechanisms. Document every button, confirmation modal, workflow state transition, and signature requirement.

3. **Agent 3 — Frontend Design:** Using the design philosophy skill and findings from agents 1 & 2, design the lens prototype. Build HTML prototypes following token system, 44px rows, section anchors, VitalSigns pattern, honest interactivity.

### Execution Order

```
Group A (WO, Faults, Equipment, Parts)     ← Most complex, do first
Group B (Certs, Docs, Receiving, Shopping) ← Medium complexity
Group C (POs, HoR, Handover Export, Warranties) ← Mixed
```

Each group produces 4 HTML prototypes in `.superpowers/brainstorm/6432-1773680335/`.

---

## 9. Cross-Reference

- **Design philosophy:** `docs/superpowers/specs/2026-03-16-frontend-design-philosophy.md`
- **Ledger spec:** `docs/superpowers/specs/2026-03-16-ledger-module-design.md`
- **Handover spec:** `docs/superpowers/specs/2026-03-16-handover-module-design.md`
- **Settings spec:** `docs/superpowers/specs/2026-03-16-settings-module-design.md`
- **Signature mechanism:** `docs/reference_signature_mechanism.md` (if exists)
- **Token values:** `apps/web/src/styles/tokens.css`
- **Lens CSS:** `apps/web/src/styles/lens.css`
