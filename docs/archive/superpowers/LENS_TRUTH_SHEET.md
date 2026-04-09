# Lens Truth Sheet
**Generated:** 2026-03-11
**Purpose:** Single reference for all 12 lenses — exact DB tables, display fields, role-gated actions, success criteria.

---

## How to read this

**Tables** = verified from actual SELECT statements in handlers + FINAL docs.
**Display fields** = what LensContent renders, mapped to actual DB column names.
**Success** = the minimum fields that must be non-null for the lens to be useful (not the error state).
**Actions by role** = from `lens_matrix.json`. `[]` = all roles. Named roles = restricted.

---

## 1. Work Order ✅ Endpoint exists

**Endpoint:** `GET /v1/entity/work_order/{id}`
**Status:** Working

### Tables
| Table | Key Columns |
|-------|-------------|
| `pms_work_orders` | `id`, `wo_number`, `title`, `description`, `status`, `priority`, `type`, `equipment_id`, `equipment_name`, `assigned_to`, `due_date`, `completed_at`, `fault_id`, `yacht_id` |
| `pms_work_order_notes` | `id`, `note_text`, `note_type`, `created_by`, `created_at` |
| `pms_work_order_parts` | `id`, `part_id`, `quantity`, `notes` + join `pms_parts(id, name, part_number, location)` |
| `pms_work_order_checklist` | `id`, `title`, `is_completed`, `completed_by`, `sequence` |
| `pms_audit_log` | `id`, `action`, `old_values`, `new_values`, `user_id`, `created_at` |

### Display fields
`wo_number`, `title`, `status`, `priority`, `type`, `equipment_name`, `assigned_to_name`, `due_date`, `notes[]`, `parts[]`, `checklist[]`, `available_actions[]`

### Success = these are non-null
`id`, `title`, `status`

### Actions by role
| Action | Restricted to |
|--------|--------------|
| `create_work_order` | all roles |
| `update_work_order` | all roles |
| `add_note_to_work_order` | all roles |
| `add_part_to_work_order` | all roles |
| `mark_work_order_complete` | all roles (requires signature) |
| `schedule_work_order` | all roles |
| `set_priority_on_work_order` | all roles |
| `attach_photo_to_work_order` | all roles |
| `attach_document_to_work_order` | all roles |
| `assign_work_order` | chief_engineer, captain, manager |
| `close_work_order` | chief_engineer, captain, manager |
| `create_work_order_from_fault` | all roles (requires signature) |

---

## 2. Fault ✅ Endpoint exists

**Endpoint:** `GET /v1/entity/fault/{id}`
**Status:** Working

### Tables
| Table | Key Columns |
|-------|-------------|
| `pms_faults` | `id`, `title`, `description`, `severity`, `equipment_id`, `equipment_name`, `reported_at`, `reporter`/`reported_by`, `status`, `has_work_order`, `ai_diagnosis`, `fault_code`, `yacht_id` |

### Display fields
`title`, `description`, `severity`, `status`, `equipment_name`, `reporter`, `reported_at`, `has_work_order`, `ai_diagnosis`

### Success = these are non-null
`id`, `title`, `severity`, `status`

### Actions by role
| Action | Restricted to |
|--------|--------------|
| `report_fault` | all roles |
| `add_fault_photo` | all roles |
| `add_fault_note` | all roles |
| `acknowledge_fault` | chief_engineer, captain, manager |
| `close_fault` | chief_engineer, captain, manager (requires resolution field) |
| `update_fault` | chief_engineer, captain, manager |
| `diagnose_fault` | chief_engineer, captain, manager |
| `reopen_fault` | chief_engineer, captain, manager |
| `mark_fault_false_alarm` | chief_engineer, captain, manager |

---

## 3. Equipment ✅ Endpoint exists

**Endpoint:** `GET /v1/entity/equipment/{id}`
**Status:** Working

### Tables
| Table | Key Columns |
|-------|-------------|
| `pms_equipment` | `id`, `name`, `manufacturer`, `model`, `serial_number`, `location`, `status`, `category`, `install_date`, `last_service_date`, `running_hours`, `risk_score`, `yacht_id` |

### Display fields
`name`, `manufacturer`, `model`, `serial_number`, `location`, `status`, `category`, `install_date`, `last_service_date`, `running_hours`

### Success = these are non-null
`id`, `name`, `status`

### Actions by role
| Action | Restricted to |
|--------|--------------|
| `update_running_hours` | all roles |
| `log_contractor_work` | all roles |
| `link_document_to_equipment` | all roles |
| `update_equipment` | chief_engineer, captain, manager |
| `set_equipment_status` | chief_engineer, captain, manager |

---

## 4. Part / Inventory ✅ Endpoint exists

**Endpoint:** `GET /v1/entity/part/{id}` (inventory maps to same endpoint)
**Status:** Working

### Tables
| Table | Key Columns |
|-------|-------------|
| `pms_parts` | `id`, `name`, `part_number`, `quantity_on_hand`, `minimum_quantity`, `location`, `category`, `unit`, `manufacturer`, `description`, `last_counted_at`, `last_counted_by`, `metadata` (jsonb: unit_cost, supplier), `yacht_id` |

### Display fields
`part_name` ← `name`, `part_number`, `stock_quantity` ← `quantity_on_hand`, `min_stock_level` ← `minimum_quantity`, `location`, `unit_cost` ← `metadata.unit_cost`, `supplier` ← `metadata.supplier`, `category`, `manufacturer`

### Success = these are non-null
`id`, `part_name`, `stock_quantity`

### Actions by role (part lens)
| Action | Restricted to |
|--------|--------------|
| `consume_part` | all roles (requires work_order_id) |
| `receive_part` | all roles |
| `transfer_part` | all roles |
| `add_to_shopping_list` | all roles |
| `adjust_stock_quantity` | chief_engineer, captain, manager (requires signature) |
| `write_off_part` | chief_engineer, captain, manager (requires signature) |
| `order_part` | chief_engineer, captain, manager |

---

## 5. Receiving ✅ Endpoint exists

**Endpoint:** `GET /v1/entity/receiving/{id}`
**Status:** Working

### Tables
| Table | Key Columns |
|-------|-------------|
| `pms_receiving` | `id`, `vendor_name`, `vendor_reference`, `received_date`, `status`, `total`, `currency`, `notes`, `received_by`, `yacht_id` |

### Display fields
`vendor_name`, `status`, `received_date`, `total`, `currency`, `notes`, `received_by`

### Success = these are non-null
`id`, `vendor_name`, `status`

### Actions by role
| Action | Restricted to |
|--------|--------------|
| `create_receiving` | all roles |
| `attach_receiving_image_with_comment` | all roles |
| `extract_receiving_candidates` | all roles (advisory only) |
| `update_receiving_fields` | all roles |
| `add_receiving_item` | all roles |
| `adjust_receiving_item` | all roles |
| `link_invoice_document` | all roles |
| `accept_receiving` | all roles (requires signature) |
| `reject_receiving` | all roles |

---

## 6. Certificate ❌ Endpoint missing

**Endpoint:** `GET /v1/entity/certificate/{id}` — **TO ADD**

### Tables
| Table | Key Columns | Used when |
|-------|-------------|-----------|
| `pms_vessel_certificates` | `id`, `yacht_id`, `certificate_type`, `certificate_name`, `certificate_number`, `issuing_authority`, `issue_date`, `expiry_date`, `last_survey_date`, `next_survey_due`, `status`, `document_id`, `properties`, `created_at` | `domain = vessel` |
| `pms_crew_certificates` | `id`, `yacht_id`, `person_name`, `person_node_id`, `certificate_type`, `certificate_number`, `issuing_authority`, `issue_date`, `expiry_date`, `document_id`, `properties`, `created_at` | `domain = crew` |

**Lookup strategy:** Try `pms_vessel_certificates` first. If 404, try `pms_crew_certificates`. Set `domain` field in response.

### Display fields → DB column mapping
| Response field | Vessel column | Crew column |
|----------------|---------------|-------------|
| `name` | `certificate_name` | `certificate_type` (no name field) |
| `certificate_type` | `certificate_type` | `certificate_type` |
| `issuing_authority` | `issuing_authority` | `issuing_authority` |
| `issue_date` | `issue_date` | `issue_date` |
| `expiry_date` | `expiry_date` | `expiry_date` |
| `status` | `status` | (compute from expiry_date) |
| `certificate_number` | `certificate_number` | `certificate_number` |
| `notes` | `properties.notes` | `properties.notes` |
| `crew_member_id` | — | `person_node_id` |

### Success = these are non-null
`id`, `name`, `certificate_type`, `expiry_date`

### Actions by role
| Action | Restricted to |
|--------|--------------|
| `create_vessel_certificate` | chief_engineer, captain, manager |
| `create_crew_certificate` | chief_engineer, captain, manager |
| `update_certificate` | chief_engineer, captain, manager |
| `link_document_to_certificate` | chief_engineer, captain, manager |
| `upload_certificate_document` | chief_engineer, captain, manager |
| `update_certificate_metadata` | chief_engineer, captain, manager |
| `supersede_certificate` | chief_engineer, captain, manager (requires signature) |
| `delete_certificate` | manager only |

---

## 7. Document ❌ Endpoint missing

**Endpoint:** `GET /v1/entity/document/{id}` — **TO ADD**

### Tables
| Table | Key Columns |
|-------|-------------|
| `doc_metadata` | `id`, `yacht_id`, `filename`, `storage_path`, `content_type`, `deleted_at`, `title`, `description`, `classification`, `equipment_id`, `equipment_name`, `tags`, `created_at`, `created_by` |

**Note:** Filter `deleted_at IS NULL`. The `url` field is NOT stored — it must be generated as a signed URL from `storage_path`. For v1, return `storage_path` as `url` and let the frontend handle it.

### Display fields → DB column mapping
| Response field | DB column |
|----------------|-----------|
| `filename` | `filename` |
| `title` | `title` (fallback: `filename`) |
| `description` | `description` |
| `mime_type` | `content_type` |
| `file_size` | `file_size` (may not exist — return null) |
| `url` | generate signed URL from `storage_path`, or return `storage_path` |
| `classification` | `classification` |
| `equipment_id` | `equipment_id` |
| `equipment_name` | `equipment_name` |
| `created_at` | `created_at` |
| `created_by` | `created_by` |

### Success = these are non-null
`id`, `filename`, `mime_type`

### Actions by role
| Action | Restricted to |
|--------|--------------|
| `upload_document` | all roles |
| `update_document` | all roles |
| `add_document_tags` | all roles |
| `get_document_url` | all roles |
| `reclassify_document` | chief_engineer, captain, manager |
| `delete_document` | chief_engineer, captain, manager (requires signature) |

---

## 8. Hours of Rest ❌ Endpoint missing

**Endpoint:** `GET /v1/entity/hours_of_rest/{id}` — **TO ADD**

### Tables
| Table | Key Columns |
|-------|-------------|
| `pms_hours_of_rest` | `id`, `user_id`, `record_date`, `rest_periods` (jsonb array), `total_rest_hours`, `total_work_hours`, `is_daily_compliant`, `is_weekly_compliant`, `weekly_rest_hours`, `daily_compliance_notes`, `weekly_compliance_notes`, `yacht_id`, `created_at`, `updated_at` |

**rest_periods shape:** `[{start: "HH:MM", end: "HH:MM", hours: float}]` — stored as JSON, may be a string requiring `json.loads()`.

### Display fields → DB column mapping
| Response field | DB column |
|----------------|-----------|
| `crew_name` | `user_id` (no name stored — use user_id as fallback, join auth_users_profiles if needed) |
| `date` | `record_date` |
| `total_rest_hours` | `total_rest_hours` |
| `total_work_hours` | `total_work_hours` |
| `is_compliant` | `is_daily_compliant` |
| `status` | derive: `is_daily_compliant ? 'compliant' : 'non_compliant'` |
| `verified_by` | `verified_by` (may not exist — null OK) |
| `verified_at` | `verified_at` (may not exist — null OK) |
| `rest_periods` | `rest_periods` (parse JSON if string) |

### Success = these are non-null
`id`, `date`, `total_rest_hours`, `is_compliant`

### Actions by role
| Action | Restricted to |
|--------|--------------|
| `log_hours_of_rest` | all roles |
| `upsert_hours_of_rest` | all roles |
| `create_crew_template` | all roles |
| `apply_crew_template` | all roles |
| `acknowledge_warning` | all roles |
| `sign_monthly_signoff` | all roles (requires signature) |
| `create_monthly_signoff` | chief_engineer, captain, manager |
| `dismiss_warning` | chief_engineer, captain, manager |

---

## 9. Shopping List ❌ Endpoint missing

**Endpoint:** `GET /v1/entity/shopping_list/{id}` — **TO ADD**

### Tables
| Table | Key Columns |
|-------|-------------|
| `pms_shopping_list_items` | `id`, `yacht_id`, `part_name`, `part_number`, `manufacturer`, `unit`, `quantity_requested`, `urgency`, `status`, `source_type`, `required_by_date`, `created_by`, `created_at`, `rejected_at`, `is_candidate_part`, `candidate_promoted_to_part_id` |

**Note:** The `id` in search results IS a `pms_shopping_list_items.id`. Each item is its own entity. The lens renders item details (not a bundle). Use `items: [item]` as a single-item array for the component.

### Display fields → DB column mapping
| Response field | DB column |
|----------------|-----------|
| `title` | `part_name` |
| `status` | `status` |
| `requester_name` | `created_by` (user_id — join auth_users_profiles.name if feasible, else use as-is) |
| `approver_name` | `approved_by` (may not exist — null OK) |
| `created_at` | `created_at` |
| `approved_at` | `approved_at` (may not exist — null OK) |
| `items` | `[this item]` — array of one |

Item fields: `id`, `part_name`, `part_number`, `quantity_requested`, `status`, `urgency`, `required_by_date`, `is_candidate_part`

### Success = these are non-null
`id`, `title` (part_name), `status`

### Actions by role
| Action | Restricted to |
|--------|--------------|
| `create_shopping_list_item` | all roles |
| `update_shopping_list_item` | all roles |
| `mark_item_received` | all roles |
| `approve_shopping_list_item` | chief_engineer, captain, manager |
| `reject_shopping_list_item` | chief_engineer, captain, manager |
| `promote_candidate_to_part` | chief_engineer, captain, manager |
| `mark_item_ordered` | chief_engineer, captain, manager |

---

## 10. Warranty ❌ Endpoint missing

**Endpoint:** `GET /v1/entity/warranty/{id}` — **TO ADD**

### Tables
| Table | Key Columns |
|-------|-------------|
| `pms_warranties` | `id`, `yacht_id`, `warranty_number`, `equipment_id`, `equipment_name`, `supplier`/`supplier_name`, `start_date`, `end_date`/`expiry_date`, `status`, `coverage_details`/`coverage`, `terms_conditions`/`terms`, `created_at` |

**Column name uncertainty:** `supplier` vs `supplier_name`, `end_date` vs `expiry_date`, `coverage_details` vs `coverage`. Use `SELECT *` and map with fallbacks.

### Display fields → DB column mapping
| Response field | DB column (try in order) |
|----------------|--------------------------|
| `title` | `warranty_number` → `name` → `id[:8]` |
| `equipment_id` | `equipment_id` |
| `equipment_name` | `equipment_name` |
| `supplier` | `supplier_name` → `supplier` |
| `start_date` | `start_date` |
| `expiry_date` | `expiry_date` → `end_date` |
| `status` | `status` |
| `coverage` | `coverage_details` → `coverage` |
| `terms` | `terms_conditions` → `terms` |

### Success = these are non-null
`id`, `title` (warranty_number), `status`

### Actions by role
| Action | Restricted to |
|--------|--------------|
| `create_warranty` | chief_engineer, captain, manager |
| `update_warranty` | chief_engineer, captain, manager |
| `claim_warranty` | chief_engineer, captain, manager |
| `link_document_to_warranty` | chief_engineer, captain, manager |
| `extend_warranty` | chief_engineer, captain, manager |
| `void_warranty` | manager only |

---

## 11. Handover Export ❌ Endpoint missing

**Endpoint:** `GET /v1/entity/handover_export/{id}` — **TO ADD**

### Tables
| Table | Key Columns |
|-------|-------------|
| `handover_exports` | `id`, `yacht_id`, `original_storage_url`, `edited_content`, `review_status`, `created_at`, `user_signature`, `user_signed_at`, `hod_signature`, `hod_signed_at`, `draft_id`, `export_type`, `exported_at`, `exported_by_user_id`, `document_hash`, `export_status`, `file_name` |

**Sections:** Stored in `edited_content` (JSON). Parse and return as `sections`.
**Signature:** The component uses `data.userSignature` (camelCase) — return both `user_signature` and `userSignature`.

### Display fields → DB column mapping
| Response field | DB column |
|----------------|-----------|
| `sections` | parse `edited_content` as JSON → `.sections` array |
| `userSignature` | `user_signature` (jsonb) |
| `user_signature` | `user_signature` |
| `review_status` | `review_status` |
| `yacht_id` | `yacht_id` |
| `created_at` | `created_at` |
| `submitted_at` | `exported_at` |

### Success = these are non-null
`id`, `yacht_id`, `review_status`

### Actions (from handover lens_matrix — handover export uses handover actions)
| Action | Restricted to |
|--------|--------------|
| `edit_handover_section` | all roles |
| `regenerate_handover_summary` | all roles |
| `export_handover` | all roles (requires confirmation) |
| `add_to_handover` | all roles |
| `edit_handover_item` | all roles |
| `attach_document_to_handover` | all roles |

---

## 12. Purchase Order ❌ Endpoint missing

**Endpoint:** `GET /v1/entity/purchase_order/{id}` — **TO ADD**
**Note:** Used by `/purchasing/[id]` page (custom — not RouteShell).

### Tables
| Table | Key Columns |
|-------|-------------|
| `pms_purchase_orders` | `id`, `yacht_id`, `po_number`, `status`, `supplier_name`/`vendor_name`, `order_date`, `expected_delivery`/`expected_delivery_date`, `total_amount`/`total`, `currency`, `notes`, `created_at` |
| `pms_purchase_order_items` | `id`, `purchase_order_id`, `part_id`, `quantity_ordered`, `quantity_received`, `name`/`part_name`/`description`, `unit_price`, `currency` |

### Display fields → DB column mapping
| Response field | DB column (try in order) |
|----------------|--------------------------|
| `po_number` | `po_number` |
| `supplier_name` | `supplier_name` → `vendor_name` |
| `status` | `status` |
| `order_date` | `order_date` → `created_at` |
| `expected_delivery` | `expected_delivery` → `expected_delivery_date` |
| `total_amount` | `total_amount` → `total` |
| `currency` | `currency` (default: USD) |
| `notes` | `notes` |
| `items[]` | from `pms_purchase_order_items` joined by `purchase_order_id` |

### Success = these are non-null
`id`, `po_number`, `status`

---

## Summary

| # | Lens | Endpoint | Status | Min success fields |
|---|------|----------|--------|--------------------|
| 1 | work_order | `/v1/entity/work_order/{id}` | ✅ Working | id, title, status |
| 2 | fault | `/v1/entity/fault/{id}` | ✅ Working | id, title, severity, status |
| 3 | equipment | `/v1/entity/equipment/{id}` | ✅ Working | id, name, status |
| 4 | part/inventory | `/v1/entity/part/{id}` | ✅ Working | id, part_name, stock_quantity |
| 5 | receiving | `/v1/entity/receiving/{id}` | ✅ Working | id, vendor_name, status |
| 6 | certificate | `/v1/entity/certificate/{id}` | ❌ Missing | id, name, certificate_type, expiry_date |
| 7 | document | `/v1/entity/document/{id}` | ❌ Missing | id, filename, mime_type |
| 8 | hours_of_rest | `/v1/entity/hours_of_rest/{id}` | ❌ Missing | id, date, total_rest_hours, is_compliant |
| 9 | shopping_list | `/v1/entity/shopping_list/{id}` | ❌ Missing | id, title (part_name), status |
| 10 | warranty | `/v1/entity/warranty/{id}` | ❌ Missing | id, title (warranty_number), status |
| 11 | handover_export | `/v1/entity/handover_export/{id}` | ❌ Missing | id, yacht_id, review_status |
| 12 | purchase_order | `/v1/entity/purchase_order/{id}` | ❌ Missing | id, po_number, status |
