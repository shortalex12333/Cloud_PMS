# Receiving — Actions Matrix

Source of truth: `apps/api/action_router/registry.py` (12 receiving actions).  
Lens render: `apps/web/src/components/lens-v2/entity/ReceivingContent.tsx`.  
Dispatch: `apps/api/action_router/dispatchers/internal_dispatcher.py` →
`apps/api/handlers/receiving_handlers.py` (v1) +
`apps/api/routes/handlers/receiving_handler.py` (Phase 4).

| # | action_id | Variant | Required fields | Allowed roles | DB tables touched | Registry line |
|---|-----------|---------|-----------------|---------------|-------------------|---------------|
| 1 | `create_receiving` | MUTATE | yacht_id | crew, deckhand, steward, chef, bosun, engineer, eto, chief_engineer, chief_officer, chief_steward, purser, captain, manager (ALL) | INSERT pms_receiving + ledger_events | 1302 |
| 2 | `attach_receiving_image_with_comment` | MUTATE | yacht_id, receiving_id, storage_path | ALL | INSERT pms_attachments + ledger_events | 1325 |
| 3 | `extract_receiving_candidates` | READ (advisory) | yacht_id, receiving_id, document_id | HOD+purser+captain+manager | None (read-only OCR) | 1348 |
| 4 | `update_receiving_fields` | MUTATE | yacht_id, receiving_id | HOD+purser+captain+manager | UPDATE pms_receiving + ledger_events | 1366 |
| 5 | `add_receiving_item` | MUTATE | yacht_id, receiving_id, quantity_received (one of part_id OR description) | HOD+purser+captain+manager | INSERT pms_receiving_items + ledger_events | 1388 |
| 6 | `adjust_receiving_item` | MUTATE | yacht_id, receiving_id, receiving_item_id | HOD+purser+captain+manager | UPDATE pms_receiving_items + ledger_events | 1411 |
| 7 | `link_invoice_document` | MUTATE | yacht_id, receiving_id, document_id | HOD+purser+captain+manager | INSERT pms_receiving_documents + ledger_events | 1432 |
| 8 | `accept_receiving` | **SIGNED** (PIN/TOTP) | yacht_id, receiving_id, signature | HOD+purser+captain+manager | UPDATE pms_receiving (status→accepted), audit_log + ledger_events. **DOES NOT touch pms_inventory_stock — gap.** | 1453 |
| 9 | `reject_receiving` | MUTATE | yacht_id, receiving_id, reason | ALL crew (discovery role) | UPDATE pms_receiving (status→rejected) + ledger_events | 1473 |
| 10 | `view_receiving_history` | READ | yacht_id, receiving_id | ALL | None | 1492 |
| 11 | `confirm_receiving` | MUTATE (alias of accept w/o signature) | yacht_id, receiving_id | chief_engineer, chief_officer, captain, manager | UPDATE pms_receiving | 3820 |
| 12 | `flag_discrepancy` | MUTATE | yacht_id, receiving_id, reason | ALL crew | INSERT note / flag + ledger_events | 3860 |

## Role groups (canonical aliases)

| Group | Roles |
|---|---|
| ALL crew | crew, deckhand, steward, chef, bosun, engineer, eto, chief_engineer, chief_officer, chief_steward, purser, captain, manager |
| HOD+purser+captain+manager | chief_engineer, chief_officer, purser, captain, manager |
| HOD+captain | chief_engineer, chief_officer, captain |

(Citation: `apps/api/action_router/registry.py:1305, 1392, 1456, 3825`.)

## Signature ladder

`apps/api/handlers/receiving_handlers.py:1206-1397` (`_accept_receiving_adapter`) implements PREPARE/EXECUTE split:
- **PREPARE** (no signature): returns intent + `signature_required: True` so the frontend renders the PIN modal.
- **EXECUTE** (signature payload required): verifies PIN+TOTP, marks `accepted`, writes `auth_signatures` row + ledger_events. Refuses if status not in `('draft', 'in_review')` or zero line items.

`EntityLensPage.tsx:153-167` (`safeExecute`) intercepts `requires_signature: true` actions to display the PIN modal before dispatching to the backend.

## Reject reasons

`reject_receiving` accepts a `reason` string (`registry.py:1488`). Frontend dropdown values (suggested):
- `damaged_in_transit`
- `wrong_item_received`
- `quantity_short`
- `quantity_over`
- `expired_or_perished`
- `invoice_mismatch`
- `other` (with free-text continuation)

(Currently the lens passes a free-text reason via `ActionPopup`. Tightening to a dropdown is a UX improvement, not a functional gap.)

## Lens primary button

`ReceivingContent.tsx:181-187` calls `confirm_receiving` (action #11) on the primary "Confirm Receipt" button. This is the **unsigned** path. The signed path (`accept_receiving`, action #8) is exposed in the dropdown and triggers the PIN modal via `safeExecute`. This split reflects two real-world flows:
- Quick crew confirmation (unsigned) — useful when the HOD already inspected and just clicks confirm.
- Formal sign-off (signed) — required for compliance/audit; the moment that updates status to `accepted` with cryptographic provenance.

## Frontend → backend wiring

```
ReceivingContent.tsx (button click)
    └→ executeAction(action_id, payload)         [useEntityLensContext]
        └→ safeExecute()                         [EntityLensPage.tsx:153]
            ├─ if requires_signature → show PIN modal first
            └→ POST /v1/actions/execute          [pipeline-core]
                └→ action_router/registry.py     [validate role, fields]
                    └→ internal_dispatcher.py    [route by action_id]
                        ├─ v1 actions → handlers/receiving_handlers.py
                        └─ Phase 4   → routes/handlers/receiving_handler.py
                            └→ table writes + ledger_events
```
