# Receiving — Documentation Index

| Doc | Purpose |
|---|---|
| `receiving_errors.md` | Original issues file from CEO |
| `RECEIVING_BUGFIX_LOG.md` | Each bug → root cause → fix → file:line citation. Single source of truth for "what changed and why". |
| `RECEIVING_DATA_CONTRACT.md` | API ↔ lens field map, table inventory, RLS posture, wire diagram. |
| `RECEIVING_ACTIONS_MATRIX.md` | All 12 receiving actions: roles, signatures, tables touched, registry line numbers. |
| `RECEIVING_AUDIT.md` | Repo structure audit: live vs dead vs ambiguous files, naming risks, repeated logic. |
| `RECEIVING_INVENTORY_GAP.md` | The biggest open functional gap: accept_receiving doesn't update pms_inventory_stock. |

## Quick reference — what shipped 2026-04-23

- 404 on card open → fixed (page now uses `EntityLensPage` → tenant DB via Render)
- UUID exposed in list titles / received_by → fixed (vendor_name fallback, name resolution)
- Action buttons unwired → fixed (lens reads `availableActions` from API)
- Filtering thin → added vendor_name + po_number filters
- Lens contract bugs (notes type, missing po_id/yacht_name/audit_history/total_items) → fixed

## What did NOT ship (flagged for next sprint)

- Inventory stock increment on accept_receiving (see `RECEIVING_INVENTORY_GAP.md`)
- Money line in lens (`total` + `currency` returned but not rendered)
- Discrepancy reason dropdown (currently free-text)
- Removal of ambiguous tables `pms_receiving_draft_lines`, `pms_receiving_events`, `pms_receiving_line_items`, `pms_receiving_sessions` — pending owner sign-off
