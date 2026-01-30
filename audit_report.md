# Prepare Module Audit Report

**Date**: 2026-01-30 12:03:35

---

## Summary

- **Total Entity Types**: 18
- **Total Entity Mappings**: 20
- **Total Capabilities**: 8
- **Total Intents**: 154
- **Total Query Intents**: 7
- **Total Conflicts**: 48

## ⚠️ Conflicts Detected

### Unmapped Entity Types (16)
Entity types extracted but no capability mapping:

- `action`
- `brand`
- `certificate`
- `diagnostic`
- `equipment`
- `fault_code`
- `high exhaust temperature`
- `making noise`
- `maritime_term`
- `measurement`
- `model`
- `observation`
- `part`
- `person`
- `seems hot`
- `system`

### Unused Entity Mappings (17)
Entity mappings that don't have extraction patterns:

- `component_name`
- `document_query`
- `email_search`
- `email_subject`
- `entity_lookup`
- `equipment_name`
- `equipment_type`
- `manual_search`
- `manufacturer`
- `model_number`
- `part_name`
- `part_number`
- `procedure_search`
- `stock_query`
- `system_name`
- `wo_number`
- `work_order_id`

### Ambiguous Entity Names (15)
Entity names that may belong to multiple lenses:

- `PART_NUMBER` → `part_by_part_number_or_name` (column: `part_number`)
- `PART_NAME` → `part_by_part_number_or_name` (column: `name`)
- `LOCATION` → `inventory_by_location` (column: `location`)
- `STOCK_QUERY` → `inventory_by_location` (column: `name`)
- `EQUIPMENT_TYPE` → `fault_by_fault_code` (column: `equipment_type`)
- `DOCUMENT_QUERY` → `documents_search` (column: `content`)
- `MANUAL_SEARCH` → `documents_search` (column: `content`)
- `PROCEDURE_SEARCH` → `documents_search` (column: `content`)
- `SYSTEM_NAME` → `graph_node_search` (column: `label`)
- `COMPONENT_NAME` → `graph_node_search` (column: `label`)
- `WORK_ORDER_ID` → `work_order_by_id` (column: `wo_number`)
- `WO_NUMBER` → `work_order_by_id` (column: `wo_number`)
- `EQUIPMENT_NAME` → `equipment_by_name_or_model` (column: `name`)
- `MODEL_NUMBER` → `equipment_by_name_or_model` (column: `model`)
- `EMAIL_SEARCH` → `email_threads_search` (column: `latest_subject`)

## Proposed Lens Ownership

### document_lens (3 entities)

- `DOCUMENT_QUERY` → capability: `documents_search`
- `MANUAL_SEARCH` → capability: `documents_search`
- `PROCEDURE_SEARCH` → capability: `documents_search`

### email_lens (2 entities)

- `EMAIL_SEARCH` → capability: `email_threads_search`
- `EMAIL_SUBJECT` → capability: `email_threads_search`

### equipment_lens (4 entities)

- `EQUIPMENT_NAME` → capability: `equipment_by_name_or_model`
- `EQUIPMENT_TYPE` → capability: `fault_by_fault_code`
- `MODEL_NUMBER` → capability: `equipment_by_name_or_model`
- `SYSTEM_NAME` → capability: `graph_node_search`

### fault_lens (2 entities)

- `FAULT_CODE` → capability: `fault_by_fault_code`
- `SYMPTOM` → capability: `fault_by_fault_code`

### part_lens (4 entities)

- `MANUFACTURER` → capability: `part_by_part_number_or_name`
- `PART_NAME` → capability: `part_by_part_number_or_name`
- `PART_NUMBER` → capability: `part_by_part_number_or_name`
- `STOCK_QUERY` → capability: `inventory_by_location`

### unknown_lens (3 entities)

- `COMPONENT_NAME` → capability: `graph_node_search`
- `ENTITY_LOOKUP` → capability: `graph_node_search`
- `LOCATION` → capability: `inventory_by_location`

### work_order_lens (2 entities)

- `WORK_ORDER_ID` → capability: `work_order_by_id`
- `WO_NUMBER` → capability: `work_order_by_id`

## Capability Details

### `documents_search` (3 entities)

- Entity: `DOCUMENT_QUERY`, Column: `content`
- Entity: `MANUAL_SEARCH`, Column: `content`
- Entity: `PROCEDURE_SEARCH`, Column: `content`

### `email_threads_search` (2 entities)

- Entity: `EMAIL_SUBJECT`, Column: `latest_subject`
- Entity: `EMAIL_SEARCH`, Column: `latest_subject`

### `equipment_by_name_or_model` (2 entities)

- Entity: `EQUIPMENT_NAME`, Column: `name`
- Entity: `MODEL_NUMBER`, Column: `model`

### `fault_by_fault_code` (3 entities)

- Entity: `FAULT_CODE`, Column: `code`
- Entity: `SYMPTOM`, Column: `name`
- Entity: `EQUIPMENT_TYPE`, Column: `equipment_type`

### `graph_node_search` (3 entities)

- Entity: `ENTITY_LOOKUP`, Column: `label`
- Entity: `SYSTEM_NAME`, Column: `label`
- Entity: `COMPONENT_NAME`, Column: `label`

### `inventory_by_location` (2 entities)

- Entity: `LOCATION`, Column: `location`
- Entity: `STOCK_QUERY`, Column: `name`

### `part_by_part_number_or_name` (3 entities)

- Entity: `PART_NUMBER`, Column: `part_number`
- Entity: `PART_NAME`, Column: `name`
- Entity: `MANUFACTURER`, Column: `manufacturer`

### `work_order_by_id` (2 entities)

- Entity: `WORK_ORDER_ID`, Column: `wo_number`
- Entity: `WO_NUMBER`, Column: `wo_number`

## Intent Taxonomy

### analytics (8 intents)

- `view_failure_stats`
- `What machines fail the most?`
- `view_maintenance_stats`
- `How many WOs this month?`
- `view_inventory_stats`
- `What parts are low on stock?`
- `view_compliance_stats`
- `How is our compliance?`

### communicate_status (16 intents)

- `add_to_handover`
- `Add this to the handover`
- `add_document_to_handover`
- `Add this document to handover`
- `add_predictive_insight_to_handover`
- `Add this insight to handover`
- `edit_handover_section`
- `Edit the engine room section`
- `export_handover`
- `Export the handover as PDF`
- `regenerate_handover_summary`
- `Regenerate the AI summary`
- `upload_photo`
- `Upload a photo`
- `record_voice_note`
- `Record a voice note`

### comply_audit (10 intents)

- `view_hours_of_rest`
- `Show my hours of rest`
- `update_hours_of_rest`
- `Log my hours for today`
- `export_hours_of_rest`
- `Export HOR for the month`
- `view_compliance_status`
- `Who hasn`
- `
        `
- `,              # `

### control_inventory (18 intents)

- `view_part_stock`
- `How many oil filters do we have?`
- `add_part`
- `Add a new part to inventory`
- `order_part`
- `Order 2 MTU fuel filters`
- `view_part_location`
- `Where is the impeller stored?`
- `view_part_usage`
- `How many have we used?`
- `log_part_usage`
- `Log that I used 2 filters`
- `edit_part_quantity`
- `Update stock to 5`
- `scan_part_barcode`
- `Scan this barcode`
- `view_linked_equipment`
- `What equipment uses this part?`

### do_maintenance (24 intents)

- `create_work_order`
- `Create work order for oil change`
- `view_work_order_history`
- `Show me past work orders`
- `mark_work_order_complete`
- `Mark WO-123 as complete`
- `complete_work_order`
- `add_work_order_note`
- `Add a note to this work order`
- `add_work_order_photo`
- `Add a photo to this work order`
- `add_parts_to_work_order`
- `Add filter to work order`
- `link_parts_to_work_order`
- `view_work_order_checklist`
- `Show the checklist for this WO`
- `assign_work_order`
- `Assign this to 2nd engineer`
- `edit_work_order_details`
- `Change the priority to high`
- `view_checklist`
- `Show the inspection checklist`
- `mark_checklist_item_complete`
- `Mark step 3 as done`

### fix_something (18 intents)

- `diagnose_fault`
- `What`
- `
        `
- `,                # `
- `
        `
- `,         # `
- `
        `
- `,          # `
- `
        `
- `,               # `
- `
        `
- `,# `
- `
        `
- `,              # `
- `
        `
- `,             # `
- `
        `
- `,     # `

### manage_certificates (22 intents)

- `list_vessel_certificates`
- `Show all vessel certificates`
- `list_crew_certificates`
- `Show all crew certificates`
- `get_certificate_details`
- `Show ISM certificate details`
- `view_certificate_history`
- `Show certificate history`
- `find_expiring_certificates`
- `What certificates expire this month?`
- `create_vessel_certificate`
- `Create new class certificate`
- `create_crew_certificate`
- `Create STCW certificate for John`
- `update_certificate`
- `Update certificate expiry date`
- `link_document_to_certificate`
- `Link PDF to ISM certificate`
- `supersede_certificate`
- `Supersede class certificate`
- `delete_certificate`
- `Delete certificate`

### manage_equipment (16 intents)

- `view_equipment_details`
- `Show me the generator details`
- `view_equipment_history`
- `What work has been done on this?`
- `view_equipment_parts`
- `What parts are linked to this?`
- `view_linked_faults`
- `What faults has this had?`
- `view_equipment_manual`
- `Show me the generator manual`
- `add_equipment_note`
- `Add a note to this equipment`
- `request_predictive_insight`
- `When will this likely fail?`
- `view_smart_summary`
- `Give me a summary of this equipment`

### procure_suppliers (14 intents)

- `create_purchase_request`
- `Start a purchase request`
- `add_item_to_purchase`
- `Add filters to the order`
- `approve_purchase`
- `Approve this purchase`
- `upload_invoice`
- `Upload the invoice`
- `track_delivery`
- `Where is my order?`
- `log_delivery_received`
- `Mark the delivery as received`
- `update_purchase_status`
- `Update purchase status`

### search_documents (8 intents)

- `find_document`
- `Find the MTU manual`
- `view_document`
- `Open the maintenance schedule`
- `view_related_documents`
- `Show related documents`
- `view_document_section`
- `Show the overheating section`

## Query Intents (GraphRAG)

- `ADD_TO_HANDOVER` = `"add_to_handover"`
- `CREATE_WORK_ORDER` = `"create_work_order"`
- `DIAGNOSE_FAULT` = `"diagnose_fault"`
- `EQUIPMENT_HISTORY` = `"equipment_history"`
- `FIND_DOCUMENT` = `"find_document"`
- `FIND_PART` = `"find_part"`
- `GENERAL_SEARCH` = `"general_search"`

