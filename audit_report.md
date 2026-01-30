# Prepare Module Safety Audit Report

**Generated**: 2026-01-30 12:44:55 UTC
**Status**: ⚠️ CONFLICTS DETECTED

---

## Executive Summary

- **Total Entity Types Extracted**: 18
- **Total Entity Mappings**: 20
- **Total Capabilities**: 8
- **Total Conflicts**: 47

### ⚠️ Conflicts Detected

- **Unmapped Entities**: 15 (extracted but no capability)
- **Unused Mappings**: 17 (mapped but not extracted)
- **Ambiguous Names**: 15 (need renaming)

---

## Unmapped Entities

These entity types are **extracted** but have **no capability mapping**:

- `action` ← No capability (add to lens)
- `brand` ← No capability (add to lens)
- `certificate` ← No capability (add to lens)
- `diagnostic` ← No capability (add to lens)
- `equipment` ← No capability (add to lens)
- `high exhaust temperature` ← No capability (add to lens)
- `making noise` ← No capability (add to lens)
- `maritime_term` ← No capability (add to lens)
- `measurement` ← No capability (add to lens)
- `model` ← No capability (add to lens)
- `observation` ← No capability (add to lens)
- `part` ← No capability (add to lens)
- `person` ← No capability (add to lens)
- `seems hot` ← No capability (add to lens)
- `system` ← No capability (add to lens)

**Resolution**: Create capability for each entity or remove from extraction patterns.

## Unused Mappings

These entity types have **capability mappings** but are **not extracted**:

- `COMPONENT_NAME` → `graph_node_search` (no extraction pattern)
- `DOCUMENT_QUERY` → `documents_search` (no extraction pattern)
- `EMAIL_SEARCH` → `email_threads_search` (no extraction pattern)
- `EMAIL_SUBJECT` → `email_threads_search` (no extraction pattern)
- `ENTITY_LOOKUP` → `graph_node_search` (no extraction pattern)
- `EQUIPMENT_NAME` → `equipment_by_name_or_model` (no extraction pattern)
- `EQUIPMENT_TYPE` → `fault_by_fault_code` (no extraction pattern)
- `MANUAL_SEARCH` → `documents_search` (no extraction pattern)
- `MANUFACTURER` → `part_by_part_number_or_name` (no extraction pattern)
- `MODEL_NUMBER` → `equipment_by_name_or_model` (no extraction pattern)
- `PART_NAME` → `part_by_part_number_or_name` (no extraction pattern)
- `PART_NUMBER` → `part_by_part_number_or_name` (no extraction pattern)
- `PROCEDURE_SEARCH` → `documents_search` (no extraction pattern)
- `STOCK_QUERY` → `inventory_by_location` (no extraction pattern)
- `SYSTEM_NAME` → `graph_node_search` (no extraction pattern)
- `WORK_ORDER_ID` → `work_order_by_id` (no extraction pattern)
- `WO_NUMBER` → `work_order_by_id` (no extraction pattern)

**Resolution**: Add extraction patterns or remove unused mappings.

## Ambiguous Entity Names

These entity names are **ambiguous** and may conflict across lenses:

- `PART_NUMBER` → `part_by_part_number_or_name`
- `PART_NAME` → `part_by_part_number_or_name`
- `LOCATION` → `inventory_by_location`
- `STOCK_QUERY` → `inventory_by_location`
- `EQUIPMENT_TYPE` → `fault_by_fault_code`
- `DOCUMENT_QUERY` → `documents_search`
- `MANUAL_SEARCH` → `documents_search`
- `PROCEDURE_SEARCH` → `documents_search`
- `SYSTEM_NAME` → `graph_node_search`
- `COMPONENT_NAME` → `graph_node_search`
- `WORK_ORDER_ID` → `work_order_by_id`
- `WO_NUMBER` → `work_order_by_id`
- `EQUIPMENT_NAME` → `equipment_by_name_or_model`
- `MODEL_NUMBER` → `equipment_by_name_or_model`
- `EMAIL_SEARCH` → `email_threads_search`

**Resolution**: Rename to be lens-specific (e.g., `LOCATION` → `PART_STORAGE_LOCATION`, `CREW_LOCATION`).

## Proposed Lens Ownership

Based on entity naming patterns, here's the proposed lens ownership:

### Document Lens

Entities: 3

- `DOCUMENT_QUERY` → `documents_search`
- `MANUAL_SEARCH` → `documents_search`
- `PROCEDURE_SEARCH` → `documents_search`

### Email Lens

Entities: 2

- `EMAIL_SEARCH` → `email_threads_search`
- `EMAIL_SUBJECT` → `email_threads_search`

### Equipment Lens

Entities: 4

- `EQUIPMENT_NAME` → `equipment_by_name_or_model`
- `EQUIPMENT_TYPE` → `fault_by_fault_code`
- `MODEL_NUMBER` → `equipment_by_name_or_model`
- `SYSTEM_NAME` → `graph_node_search`

### Fault Lens

Entities: 2

- `FAULT_CODE` → `fault_by_fault_code`
- `SYMPTOM` → `fault_by_fault_code`

### Part Lens

Entities: 4

- `MANUFACTURER` → `part_by_part_number_or_name`
- `PART_NAME` → `part_by_part_number_or_name`
- `PART_NUMBER` → `part_by_part_number_or_name`
- `STOCK_QUERY` → `inventory_by_location`

### Unknown Lens

Entities: 3

- `COMPONENT_NAME` → `graph_node_search`
- `ENTITY_LOOKUP` → `graph_node_search`
- `LOCATION` → `inventory_by_location`

### Work Order Lens

Entities: 2

- `WORK_ORDER_ID` → `work_order_by_id`
- `WO_NUMBER` → `work_order_by_id`

---

## Pre-Migration Checklist

Before proceeding with the lens-based refactor:

- [ ] Resolve all unmapped entities
- [ ] Remove or fix unused mappings
- [ ] Rename ambiguous entity names
- [ ] Verify lens ownership assignments
- [ ] Document entity-to-lens mapping
- [ ] Update test coverage for each lens
