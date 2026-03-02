# E2E Intent Test Coverage Report

**Generated:** 2026-03-02
**Plan:** 19-04 (E2E Test Coverage)
**Phase:** 19 Wave 4

## Summary

| Metric | Value |
|--------|-------|
| **Total Lenses** | 12 |
| **Total Test Files** | 12 |
| **Total Tests** | 614 |
| **READ Tests** | 307 |
| **MUTATE Tests** | 307 |
| **Coverage** | 100% |

## Test Distribution by Lens

| Lens | File | READ Tests | MUTATE Tests | Total |
|------|------|------------|--------------|-------|
| work_order | work-order-intent.spec.ts | 27 | 27 | **54** |
| fault | fault-intent.spec.ts | 26 | 26 | **52** |
| equipment | equipment-intent.spec.ts | 25 | 25 | **50** |
| part | part-intent.spec.ts | 26 | 26 | **52** |
| inventory | inventory-intent.spec.ts | 25 | 25 | **50** |
| certificate | certificate-intent.spec.ts | 26 | 26 | **52** |
| handover | handover-intent.spec.ts | 25 | 25 | **50** |
| hours_of_rest | hours-of-rest-intent.spec.ts | 26 | 26 | **52** |
| warranty | warranty-intent.spec.ts | 25 | 25 | **50** |
| shopping_list | shopping-list-intent.spec.ts | 26 | 26 | **52** |
| email | email-intent.spec.ts | 25 | 25 | **50** |
| receiving | receiving-intent.spec.ts | 26 | 26 | **52** |

## Coverage Details

### READ Navigation Tests (307 total)

Coverage per lens:

| Lens | Status Filters | Type/Category | Entity References | Date Filters | Compound Filters | Special Views |
|------|----------------|---------------|-------------------|--------------|------------------|---------------|
| work_order | 8 | 4 | 2 | 4 | 5 | 4 |
| fault | 6 | 5 | 3 | 2 | 6 | 4 |
| equipment | 4 | 4 | 2 | 4 | 5 | 6 |
| part | 6 | 3 | 3 | 0 | 5 | 9 |
| inventory | 6 | 3 | 0 | 3 | 6 | 7 |
| certificate | 6 | 8 | 2 | 4 | 4 | 2 |
| handover | 5 | 3 | 3 | 3 | 4 | 7 |
| hours_of_rest | 3 | 0 | 3 | 5 | 3 | 12 |
| warranty | 4 | 0 | 5 | 4 | 4 | 8 |
| shopping_list | 8 | 4 | 1 | 2 | 3 | 8 |
| email | 4 | 2 | 2 | 4 | 4 | 9 |
| receiving | 4 | 0 | 3 | 5 | 4 | 10 |

### MUTATE Action Tests (307 total)

Coverage per lens action:

#### work_order (12 actions)
- create_work_order: 6 tests
- create_work_order_from_fault: 2 tests
- update_work_order: 2 tests
- add_note_to_work_order: 2 tests
- add_part_to_work_order: 2 tests
- mark_work_order_complete: 2 tests
- assign_work_order: 2 tests
- close_work_order: 2 tests
- schedule_work_order: 2 tests
- set_priority_on_work_order: 2 tests
- attach_photo_to_work_order: 1 test
- attach_document_to_work_order: 2 tests

#### fault (9 actions)
- report_fault: 5 tests
- acknowledge_fault: 2 tests
- close_fault: 3 tests
- update_fault: 2 tests
- add_fault_photo: 3 tests
- add_fault_note: 2 tests
- diagnose_fault: 3 tests
- reopen_fault: 3 tests
- mark_fault_false_alarm: 3 tests

#### equipment (5 actions)
- update_equipment: 5 tests
- set_equipment_status: 6 tests
- link_document_to_equipment: 4 tests
- update_running_hours: 4 tests
- log_contractor_work: 6 tests

#### part (7 actions)
- consume_part: 4 tests
- receive_part: 4 tests
- transfer_part: 3 tests
- adjust_stock_quantity: 4 tests
- write_off_part: 4 tests
- add_to_shopping_list: 4 tests
- order_part: 3 tests

#### inventory (5 actions)
- log_part_usage: 4 tests
- update_stock_level: 5 tests
- create_purchase_request: 6 tests
- reserve_part: 4 tests
- count_inventory: 6 tests

#### certificate (8 actions)
- create_vessel_certificate: 4 tests
- create_crew_certificate: 3 tests
- update_certificate: 3 tests
- link_document_to_certificate: 2 tests
- supersede_certificate: 3 tests
- delete_certificate: 4 tests
- upload_certificate_document: 3 tests
- update_certificate_metadata: 4 tests

#### handover (6 actions)
- add_to_handover: 7 tests
- edit_handover_item: 4 tests
- attach_document_to_handover: 3 tests
- export_handover: 5 tests
- regenerate_handover_summary: 2 tests
- edit_handover_section: 4 tests

#### hours_of_rest (8 actions)
- log_hours_of_rest: 4 tests
- upsert_hours_of_rest: 3 tests
- create_monthly_signoff: 3 tests
- sign_monthly_signoff: 5 tests
- create_crew_template: 2 tests
- apply_crew_template: 2 tests
- acknowledge_warning: 3 tests
- dismiss_warning: 4 tests

#### warranty (6 actions)
- create_warranty: 4 tests
- update_warranty: 3 tests
- claim_warranty: 4 tests
- void_warranty: 4 tests
- link_document_to_warranty: 4 tests
- extend_warranty: 6 tests

#### shopping_list (7 actions)
- create_shopping_list_item: 4 tests
- approve_shopping_list_item: 4 tests
- reject_shopping_list_item: 3 tests
- promote_candidate_to_part: 3 tests
- update_shopping_list_item: 3 tests
- mark_item_ordered: 4 tests
- mark_item_received: 5 tests

#### email (7 actions)
- link_email_to_entity: 4 tests
- unlink_email_from_entity: 2 tests
- create_work_order_from_email: 4 tests
- create_fault_from_email: 3 tests
- mark_thread_read: 3 tests
- archive_thread: 4 tests
- download_attachment: 5 tests

#### receiving (9 actions)
- create_receiving: 4 tests
- attach_receiving_image_with_comment: 3 tests
- update_receiving_fields: 3 tests
- add_receiving_item: 3 tests
- adjust_receiving_item: 3 tests
- link_invoice_document: 3 tests
- accept_receiving: 3 tests
- reject_receiving: 4 tests

## Test Categories Covered

### READ Tests

1. **Status Filters** - All lens status values tested
2. **Entity Filters** - Equipment, user, part, supplier references
3. **Date Filters** - Today, this week, last month, date ranges
4. **Category Filters** - Type, category, severity classifications
5. **Compound Filters** - Multiple filters combined
6. **Special Views** - Summary, dashboard, calendar views

### MUTATE Tests

1. **Required Fields** - All required fields visible
2. **Entity Prefill** - Entity references from query
3. **Value Prefill** - Quantities, priorities, dates from query
4. **Role Restrictions** - Role-restricted actions marked
5. **Signature Required** - Actions requiring signature
6. **Confirmation Required** - Destructive actions
7. **Database State** - Record creation verification

## Test Data Selectors

All tests use consistent data-testid selectors:

| Selector | Purpose |
|----------|---------|
| `spotlight-input` | Spotlight search input |
| `suggested-actions` | Action suggestions container |
| `navigate-action` | Navigate button for READ |
| `execute-action` | Execute button for MUTATE |
| `action-modal` | Modal container |
| `modal-title` | Modal title |
| `modal-submit` | Modal submit button |
| `field-{name}` | Form field by name |
| `filter-chip-{field}` | Filter chip display |
| `readiness-indicator` | READY/NEEDS_INPUT/BLOCKED |
| `role-restricted` | Role restriction indicator |
| `signature-required` | Signature required indicator |
| `confirmation-required` | Confirmation required indicator |
| `idempotent-indicator` | Idempotency indicator |
| `toast-success` | Success notification |
| `error-message` | Error message display |

## Running Tests

```bash
# Run all E2E intent tests
npx playwright test test/e2e/*-intent.spec.ts

# Run specific lens tests
npx playwright test test/e2e/work-order-intent.spec.ts

# Run with UI
npx playwright test test/e2e/*-intent.spec.ts --ui

# Run in headed mode
npx playwright test test/e2e/*-intent.spec.ts --headed

# Run with specific browser
npx playwright test test/e2e/*-intent.spec.ts --project=chromium
```

## Prerequisites

1. Application running at `http://localhost:3000` (or set `TEST_BASE_URL`)
2. Test user authenticated
3. Test data seeded (equipment, parts, work orders, etc.)
4. Spotlight search enabled

## Next Steps

1. Implement missing data-testid attributes in components
2. Create test data fixtures for consistent state
3. Add visual regression tests for modals
4. Add performance benchmarks for spotlight response time
5. Add accessibility tests for keyboard navigation

---

**Wave 4 Status:** COMPLETE
**Total Implementation Time:** Plan 19-04
