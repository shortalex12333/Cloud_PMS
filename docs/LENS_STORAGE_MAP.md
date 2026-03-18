# Lens ↔ Storage Map

> What each lens loads, from where, and what's ready.

---

## Buckets

```
Bucket                     Policies   Limit    MIME Types
─────────────────────────  ────────   ─────    ──────────
documents                  11         500 MB   Any
pms-part-photos            10         10 MB    jpeg, png, webp, heic
pms-receiving-images       13         20 MB    jpeg, png, webp, heic, pdf
pms-label-pdfs             14         50 MB    pdf
pms-discrepancy-photos     8          10 MB    jpeg, png, heic
pms-work-order-photos      0 ⚠️       50 MB    jpeg, png, gif, webp
pms-finance-documents      3          10 MB    pdf, jpeg, png
handover-exports           2          50 MB    pdf, html, json
```

⚠️ `pms-work-order-photos` has **zero RLS policies** — blocked for all authenticated users.

All buckets are **private**. Every file needs a signed URL.

---

## Per-Lens Breakdown

### Work Order

```
MEDIA
  before/after photos    → pms-work-order-photos     ⚠️ BLOCKED (0 policies)
                           pms_attachments WHERE entity_type='work_order'
  checklist photos       → pms-work-order-photos     ⚠️ BLOCKED (0 policies)
                           pms_work_order_checklist.photo_url

LINKS (already in endpoint)
  → Equipment            pms_work_orders.equipment_id
  → Fault                pms_work_orders.fault_id
  → Parts                pms_work_order_parts.part_id (joined)
```

### Fault

```
MEDIA
  evidence photos        → pms-discrepancy-photos    ✅ ready to sign
                           pms_attachments WHERE entity_type='fault' → storage_path
  thumbnails             → pms-discrepancy-photos    ✅ ready to sign
                           pms_attachments.thumbnail_path

LINKS (already in endpoint)
  → Equipment            pms_faults.equipment_id

LINKS (needs query)
  → Work Order           reverse FK: pms_work_orders.fault_id
```

### Equipment

```
MEDIA
  equipment photos       → pms-discrepancy-photos    ⚠️ bucket not confirmed
                           pms_attachments WHERE entity_type='equipment' → storage_path
  nameplate photo        → (same bucket)             path in DB
  manuals/docs           → documents                 ⚠️ bucket not confirmed
                           pms_equipment_documents.storage_path

LINKS (needs reverse FK queries)
  → Certificates         pms_certificates.equipment_id
  → Open Faults          pms_faults.equipment_id
  → Work Orders          pms_work_orders.equipment_id
```

### Part

```
MEDIA
  hero photo             → pms-part-photos           ✅ READY
                           pms_parts.image_storage_path + image_bucket
  additional photos      → pms-part-photos           needs iteration
                           pms_parts.photo_paths (jsonb array)
  label PDF              → pms-label-pdfs            needs join
                           pms_label_generations.pdf_storage_path

LINKS (needs queries)
  → Equipment            via pms_work_order_parts → pms_work_orders.equipment_id
  → Receiving            reverse FK: pms_receiving_items.part_id
  → Purchase Orders      reverse FK: pms_purchase_order_items.part_id
```

### Receiving

```
MEDIA
  invoice/delivery photo → pms-receiving-images      ✅ READY
                           pms_image_uploads.storage_path + storage_bucket
  stock-in photo         → pms-receiving-images      ⚠️ bucket not confirmed
                           pms_inventory_transactions.photo_storage_path
  label PDF              → pms-label-pdfs            needs join
                           pms_label_generations via receiving_id

LINKS (already in endpoint)
  → Purchase Order       pms_receiving.po_number
  → Parts                pms_receiving_items.part_id
```

### Certificate

```
MEDIA
  certificate doc        → documents                 needs join
                           pms_certificates.document_id → doc_metadata.storage_path

LINKS (already in endpoint)
  → Equipment            pms_certificates.equipment_id
```

### Document

```
MEDIA
  document file          → documents (default)       ✅ READY
                           doc_metadata.storage_path
                           (storage_bucket NULL for 3,004 rows → assume 'documents')
                           (storage_bucket = 'pms-label-pdfs' for 5 rows)

LINKS (already in endpoint)
  → Equipment            doc_metadata.equipment_id
```

### Purchase Order

```
MEDIA
  finance docs           → pms-finance-documents     no data yet
                           pms_attachments WHERE entity_type='purchase_order'

LINKS (already in endpoint)
  → Parts                pms_purchase_order_items.part_id

LINKS (needs query)
  → Receiving            reverse FK: pms_receiving.po_number
```

### Handover Export

```
MEDIA
  HTML report            → handover-exports          ⚠️ PATH NOT IN DB
                           handover_exports.storage_bucket = 'handover-exports'
                           handover_exports.storage_path = NULL
                           actual path: handovers/{yacht}/{export_id}_{ts}.html
  signatures             → inline (base64/URL)       ✅ already in endpoint

LINKS
  (none)
```

### Shopping List

```
MEDIA
  (none)

LINKS (needs check)
  → Parts                pms_shopping_list_items.part_id (if column exists)
```

### Hours of Rest

```
MEDIA
  (none)

LINKS
  (none)
```

### Warranty

```
MEDIA
  claim docs             → pms-finance-documents     no data yet
                           pms_attachments WHERE entity_type='warranty'

LINKS (already in endpoint)
  → Equipment            pms_warranty_claims.equipment_id
  → Fault                pms_warranty_claims.fault_id
  → Work Order           pms_warranty_claims.work_order_id
```

---

## Status Legend

```
✅ READY         path + bucket both in DB, just needs signed URL generation
⚠️ BLOCKED       bucket exists but 0 RLS policies — service key only
⚠️ bucket issue  path in DB but bucket column missing or NULL
needs join       path is in a related table, endpoint needs an extra query
needs query      reverse FK lookup required
no data yet      table/bucket empty for test yacht
```

---

## Gaps

```
#  What                                              Fix
─  ────                                              ───
1  pms_attachments has no storage_bucket column       add column or hardcode entity_type→bucket map
2  handover_exports.storage_path is NULL              write path back on export
3  doc_metadata.storage_bucket NULL (3,004 rows)      backfill with 'documents'
4  pms_inventory_transactions — no bucket col         infer pms-receiving-images
5  pms_equipment_documents — bucket unknown           clarify assignment
6  pms-work-order-photos — 0 RLS policies             add policies
```
