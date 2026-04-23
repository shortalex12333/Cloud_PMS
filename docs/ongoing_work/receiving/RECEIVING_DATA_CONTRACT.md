# Receiving — Data Contract

Last verified: 2026-04-23 against tenant DB `vzsohavtuotocgrfkfyd` and live code.

## Tables (tenant DB)

| Table | Purpose | Key FKs |
|---|---|---|
| `pms_receiving` | One row per receiving event | `yacht_id` → yacht_registry, `received_by` → auth_users_profiles, `linked_work_order_id` → pms_work_orders |
| `pms_receiving_items` | Line items within an event | `receiving_id` → pms_receiving, `part_id` → pms_parts |
| `pms_receiving_documents` | Linked PDFs / packing slips | `receiving_id`, `document_id` |
| `pms_receiving_attachments` | Photos | `receiving_id` |
| `pms_attachments` (generic) | Catch-all for photos via entity_type='receiving' | `entity_type`, `entity_id`, `yacht_id` |

NB: there is **NO `pms_inventory` table**. Parts catalog is `pms_parts`. Stock levels are `pms_inventory_stock`.

## RLS posture (verified via `pg_policies`)

All four receiving tables have:
- SELECT scoped via `has_yacht_access(yacht_id)` or `(yacht_id = get_user_yacht_id_from_roles())`
- INSERT/UPDATE for HOD roles only (`is_hod_from_roles(...)`)
- DELETE: yacht-scope only on `pms_receiving`; not allowed via API
- `service_role` policy with `USING true` for backend access

Backend additionally enforces `.eq("yacht_id", yacht_id)` in every read — defense in depth.

## Wire diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  /receiving (list)                                              │
│  apps/web/src/app/receiving/page.tsx                            │
│      │                                                          │
│      └──FilteredEntityList → useFilteredEntityList              │
│              │                                                  │
│              GET pipeline-core.int.celeste7.ai                  │
│                  /api/vessel/{vessel_id}/domain/receiving       │
│                  /records?status=...&q=...                      │
│              │                                                  │
│              vessel_surface_routes.py:get_domain_records        │
│                  → get_tenant_client(tenant_key_alias)          │
│                  → table('pms_receiving').select('*')           │
│                       .eq('yacht_id', y).order('created_at')    │
│                  → _format_record('receiving', row)             │
│                                                                 │
│  /receiving?id=XYZ (overlay) or /receiving/[id] (deep link)     │
│      │                                                          │
│      └──EntityLensPage(entityType='receiving') → useEntityLens  │
│              │                                                  │
│              GET pipeline-core.int.celeste7.ai                  │
│                  /v1/entity/receiving/{id}                      │
│              │                                                  │
│              entity_routes.py:get_receiving_entity              │
│                  → table('pms_receiving').select('*')           │
│                       .eq('id', id).eq('yacht_id', y)           │
│                  → table('pms_receiving_items').select(cols)    │
│                  → _get_attachments('receiving', id, y)         │
│                  → table('auth_users_profiles')  [received_by]  │
│                  → table('yacht_registry')       [yacht_name]   │
│                  → table('pms_purchase_orders')  [po_id]        │
│                  → table('ledger_events')        [audit]        │
│                  → get_available_actions('receiving', e, role)  │
└─────────────────────────────────────────────────────────────────┘
```

## API → lens field map

Backend response key (`entity_routes.py:1407-1418`) → lens reader (`ReceivingContent.tsx`).

| Response key | Source | Lens reader | Display |
|---|---|---|---|
| `id` | `pms_receiving.id` | not displayed | URL only |
| `vendor_name` | `pms_receiving.vendor_name` | `ReceivingContent.tsx:80` | IdentityStrip "Supplier" |
| `vendor_reference` | `pms_receiving.vendor_reference` | `:81` | Detail "Supplier Ref" (mono) |
| `po_number` | `pms_receiving.po_number` | `:78` | IdentityStrip "PO Reference" |
| `po_id` | join → `pms_purchase_orders.id` | `:79,156` | Click target for PO link |
| `received_date` | `pms_receiving.received_date` | (subtitle) | List subtitle |
| `status` | `pms_receiving.status` | `:77,116` | IdentityStrip pill |
| `total` | `pms_receiving.total` | not yet rendered | gap — see RECEIVING_AUDIT.md §"Lens display gaps" |
| `currency` | `pms_receiving.currency` | (with total) | gap |
| `notes` | `pms_receiving.notes` (text string) | `:89-99` | NotesSection — wrapped to single row |
| `received_by` | resolved name from `auth_users_profiles.name` | `:83,137` | Detail "Received By" — name (UUID never sent) |
| `yacht_name` | join → `yacht_registry.name` | `:84,139-141` | Detail "Vessel" |
| `items` | `pms_receiving_items` rows | `:88,197-223` | PartsSection (packing list) |
| `total_items` | `len(items)` | `:85,119-122` | Header pill "{n} Items" |
| `created_at` / `updated_at` | timestamps | `:97,228` | Audit context |
| `invoice_images` | filtered subset of attachments | (lens reads `attachments` instead) | currently unused at lens level |
| `attachments` | `_get_attachments('receiving', id, y)` | `:90,232-238` | AttachmentsSection |
| `related_entities` | `[parts, purchase_order]` | `:92,257-269` | DocRowsSection "Related Work" |
| `audit_history` | `ledger_events` last 50 | `:91,240-245` | AuditTrailSection |
| `available_actions` | `get_available_actions(...)` | `useEntityLensContext` | SplitButton + dropdown |

## List endpoint response fields (per record)

From `vessel_surface_routes.py:_format_record('receiving', row)`:

```json
{
  "id": "<uuid>",
  "ref": "PO 12345" | "RCV-4f79dc",
  "title": "Acme Supplies Ltd" | "Received 11 Feb 2026" | "Draft Receiving",
  "status": "draft" | "in_review" | "accepted" | "rejected",
  "vendor_name": "Acme Supplies Ltd" | "",
  "po_number": "12345" | "",
  "received_date": "2026-02-11" | null,
  "meta": "Acme Supplies Ltd · DRAFT"
}
```

Frontend adapter `apps/web/src/features/receiving/adapter.ts:23-60` maps:
- `entityRef` ← `raw.ref` (drives `EntityRecordRow` rendering)
- `title` ← `raw.vendor_name` || `raw.title` || "Draft Receiving"
- `subtitle` ← join of `[status, dateDisplay, "PO {n}"]`
- `statusVariant` ← derived from status (`rejected → critical`, `in_review → pending`, `accepted → signed`)

## Status enum (DB-enforced)

`pms_receiving.status` CHECK: `('draft', 'in_review', 'accepted', 'rejected')`. Match the frontend filter options exactly (`filter-config.ts:206-212`).
