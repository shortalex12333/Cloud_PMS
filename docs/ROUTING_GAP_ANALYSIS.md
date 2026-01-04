# ROUTING GAP ANALYSIS
## Columns That SHOULD Be Searchable But Are NOT Routed

---

## PRIORITY 1: Part/Inventory Columns (Most Critical)

These columns contain part data users search for, but FREE_TEXT doesn't route here.

| Table | Column | Should Accept | Currently Routes | Gap |
|-------|--------|---------------|------------------|-----|
| pms_parts | part_number | PART_NUMBER, FREE_TEXT | PART_NUMBER | **FREE_TEXT** |
| pms_parts | manufacturer | MANUFACTURER, FREE_TEXT | MANUFACTURER | **FREE_TEXT** |
| pms_parts | description | DOCUMENT_QUERY, FREE_TEXT | NONE | **DOCUMENT_QUERY, FREE_TEXT** |
| pms_parts | category | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_parts | model_compatibility | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_parts | metadata | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_parts | search_embedding | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_parts | embedding_text | FREE_TEXT | NONE | **FREE_TEXT** |
| v_inventory | name | FREE_TEXT | PART_NAME | **FREE_TEXT** |
| v_inventory | part_number | PART_NUMBER, FREE_TEXT | PART_NUMBER | **FREE_TEXT** |
| v_inventory | manufacturer | MANUFACTURER, FREE_TEXT | NONE | **MANUFACTURER, FREE_TEXT** |
| v_inventory | description | DOCUMENT_QUERY, FREE_TEXT | NONE | **DOCUMENT_QUERY, FREE_TEXT** |
| v_inventory | category | FREE_TEXT | NONE | **FREE_TEXT** |
| v_inventory | equipment | EQUIPMENT_NAME, FREE_TEXT | NONE | **EQUIPMENT_NAME, FREE_TEXT** |
| v_inventory | system | FREE_TEXT, SYSTEM_NAME | NONE | **FREE_TEXT, SYSTEM_NAME** |
| v_inventory | location | STOCK_LOCATION, FREE_TEXT | STOCK_LOCATION | **FREE_TEXT** |
| pms_inventory_stock | location | STOCK_LOCATION, FREE_TEXT | NONE | **STOCK_LOCATION, FREE_TEXT** |
| pms_inventory_stock | last_counted_at | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_inventory_stock | metadata | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_purchase_order_items | description | DOCUMENT_QUERY, FREE_TEXT | NONE | **DOCUMENT_QUERY, FREE_TEXT** |
| pms_purchase_order_items | metadata | FREE_TEXT | NONE | **FREE_TEXT** |

---

## PRIORITY 2: Equipment/System Columns

| Table | Column | Should Accept | Currently Routes | Gap |
|-------|--------|---------------|------------------|-----|
| pms_equipment | name | EQUIPMENT_NAME, FREE_TEXT | EQUIPMENT_NAME | **FREE_TEXT** |
| pms_equipment | code | FAULT_CODE, FREE_TEXT | NONE | **FAULT_CODE, FREE_TEXT** |
| pms_equipment | description | DOCUMENT_QUERY, FREE_TEXT | NONE | **DOCUMENT_QUERY, FREE_TEXT** |
| pms_equipment | location | FREE_TEXT, EQUIPMENT_LOCATION | EQUIPMENT_LOCATION | **FREE_TEXT** |
| pms_equipment | manufacturer | MANUFACTURER, FREE_TEXT | NONE | **MANUFACTURER, FREE_TEXT** |
| pms_equipment | model | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_equipment | serial_number | SERIAL_NUMBER, FREE_TEXT | SERIAL_NUMBER | **FREE_TEXT** |
| pms_equipment | installed_date | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_equipment | criticality | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_equipment | system_type | FREE_TEXT, SYSTEM_NAME | NONE | **FREE_TEXT, SYSTEM_NAME** |
| pms_equipment | metadata | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_equipment | attention_reason | FREE_TEXT | NONE | **FREE_TEXT** |
| pms_equipment | attention_updated_at | FREE_TEXT | NONE | **FREE_TEXT** |
| equipment | name | EQUIPMENT_NAME, FREE_TEXT | NONE | **EQUIPMENT_NAME, FREE_TEXT** |
| equipment | code | FAULT_CODE, FREE_TEXT | NONE | **FAULT_CODE, FREE_TEXT** |
| equipment | description | DOCUMENT_QUERY, FREE_TEXT | NONE | **DOCUMENT_QUERY, FREE_TEXT** |
| equipment | location | FREE_TEXT, EQUIPMENT_LOCATION | NONE | **FREE_TEXT, EQUIPMENT_LOCATION** |
| equipment | manufacturer | MANUFACTURER, FREE_TEXT | NONE | **MANUFACTURER, FREE_TEXT** |
| equipment | model | FREE_TEXT | NONE | **FREE_TEXT** |
| equipment | serial_number | SERIAL_NUMBER, FREE_TEXT | NONE | **SERIAL_NUMBER, FREE_TEXT** |
| equipment_aliases | alias | SYMPTOM_NAME, FREE_TEXT | NONE | **SYMPTOM_NAME, FREE_TEXT** |
| equipment_aliases | alias_type | FREE_TEXT | NONE | **FREE_TEXT** |
| graph_nodes | properties | FREE_TEXT | NONE | **FREE_TEXT** |
| graph_nodes | extraction_source | FREE_TEXT | NONE | **FREE_TEXT** |
| graph_nodes | embedding | FREE_TEXT | NONE | **FREE_TEXT** |

---

## PRIORITY 3: Document/Content Columns

| Table | Column | Should Accept | Currently Routes | Gap |
|-------|--------|---------------|------------------|-----|
| document_chunks | text | DOCUMENT_QUERY, FREE_TEXT | NONE | **DOCUMENT_QUERY, FREE_TEXT** |
| document_chunks | embedding | FREE_TEXT | NONE | **FREE_TEXT** |
| document_chunks | metadata | FREE_TEXT | NONE | **FREE_TEXT** |
| document_chunks | content | DOCUMENT_QUERY, FREE_TEXT | NONE | **DOCUMENT_QUERY, FREE_TEXT** |
| document_chunks | graph_extracted_at | FREE_TEXT | NONE | **FREE_TEXT** |
| document_chunks | section_title | SECTION_NAME, FREE_TEXT | NONE | **SECTION_NAME, FREE_TEXT** |
| document_chunks | doc_type | DOC_TYPE | NONE | **DOC_TYPE** |
| document_chunks | system_tag | FREE_TEXT, SYSTEM_NAME | NONE | **FREE_TEXT, SYSTEM_NAME** |
| document_chunks | graph_extract_status | FREE_TEXT | NONE | **FREE_TEXT** |
| document_chunks | graph_extract_error | FREE_TEXT | NONE | **FREE_TEXT** |
| document_chunks | section_type | SECTION_NAME, FREE_TEXT | NONE | **SECTION_NAME, FREE_TEXT** |
| document_chunks | graph_extract_ts | FREE_TEXT | NONE | **FREE_TEXT** |
| search_document_chunks | text | DOCUMENT_QUERY, FREE_TEXT | NONE | **DOCUMENT_QUERY, FREE_TEXT** |
| search_document_chunks | embedding | FREE_TEXT | NONE | **FREE_TEXT** |
| search_document_chunks | metadata | FREE_TEXT | NONE | **FREE_TEXT** |
| search_document_chunks | graph_extracted_at | FREE_TEXT | NONE | **FREE_TEXT** |
| search_document_chunks | section_title | SECTION_NAME, FREE_TEXT | SECTION_NAME | **FREE_TEXT** |
| search_document_chunks | system_tag | FREE_TEXT, SYSTEM_NAME | NONE | **FREE_TEXT, SYSTEM_NAME** |
| search_document_chunks | graph_extract_status | FREE_TEXT | NONE | **FREE_TEXT** |
| search_document_chunks | graph_extract_error | FREE_TEXT | NONE | **FREE_TEXT** |
| search_document_chunks | section_type | SECTION_NAME, FREE_TEXT | NONE | **SECTION_NAME, FREE_TEXT** |
| search_document_chunks | graph_extract_ts | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | source | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | original_path | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | filename | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | content_type | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | sha256 | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | storage_path | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | indexed_at | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | metadata | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | system_path | FREE_TEXT, SYSTEM_NAME | NONE | **FREE_TEXT, SYSTEM_NAME** |
| documents | doc_type | DOC_TYPE | NONE | **DOC_TYPE** |
| documents | oem | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | model | FREE_TEXT | NONE | **FREE_TEXT** |
| documents | system_type | FREE_TEXT, SYSTEM_NAME | NONE | **FREE_TEXT, SYSTEM_NAME** |
| doc_metadata | source | FREE_TEXT | NONE | **FREE_TEXT** |
| doc_metadata | original_path | FREE_TEXT | NONE | **FREE_TEXT** |
| doc_metadata | filename | FREE_TEXT | NONE | **FREE_TEXT** |
| doc_metadata | content_type | FREE_TEXT | NONE | **FREE_TEXT** |
| doc_metadata | sha256 | FREE_TEXT | NONE | **FREE_TEXT** |
| doc_metadata | storage_path | FREE_TEXT | NONE | **FREE_TEXT** |
| doc_metadata | indexed_at | FREE_TEXT | NONE | **FREE_TEXT** |
| doc_metadata | metadata | FREE_TEXT | NONE | **FREE_TEXT** |
| doc_metadata | system_path | FREE_TEXT, SYSTEM_NAME | NONE | **FREE_TEXT, SYSTEM_NAME** |
| doc_metadata | doc_type | DOC_TYPE | NONE | **DOC_TYPE** |
| doc_metadata | oem | FREE_TEXT | NONE | **FREE_TEXT** |
| doc_metadata | model | FREE_TEXT | NONE | **FREE_TEXT** |
| doc_metadata | system_type | FREE_TEXT, SYSTEM_NAME | NONE | **FREE_TEXT, SYSTEM_NAME** |
| maintenance_facts | action | FREE_TEXT | NONE | **FREE_TEXT** |
| maintenance_facts | interval_description | DOCUMENT_QUERY, FREE_TEXT | NONE | **DOCUMENT_QUERY, FREE_TEXT** |
| maintenance_facts | properties | FREE_TEXT | NONE | **FREE_TEXT** |

---

## GAP SUMMARY BY ENTITY TYPE

How many columns SHOULD accept each entity type but currently have NO route:

| Entity Type | Columns That Should Accept | Currently Routed | GAP |
|-------------|---------------------------|------------------|-----|
| CANONICAL_ENTITY | 2 | 1 | **1** |
| DOCUMENT_QUERY | 24 | 1 | **23** |
| DOC_TYPE | 5 | 1 | **4** |
| EQUIPMENT_LOCATION | 3 | 1 | **2** |
| EQUIPMENT_NAME | 38 | 2 | **36** |
| FAULT_CODE | 8 | 1 | **7** |
| FREE_TEXT | 514 | 3 | **511** |
| MANUFACTURER | 7 | 2 | **5** |
| NODE_TYPE | 4 | 1 | **3** |
| PRIORITY | 4 | 1 | **3** |
| SECTION_NAME | 8 | 1 | **7** |
| SERIAL_NUMBER | 3 | 1 | **2** |
| SEVERITY | 4 | 1 | **3** |
| STATUS | 9 | 2 | **7** |
| STOCK_LOCATION | 2 | 1 | **1** |
| SYMPTOM_NAME | 11 | 2 | **9** |
| SYSTEM_NAME | 15 | 3 | **12** |

---

## CRITICAL FINDING

**FREE_TEXT entity type:**
- Columns that SHOULD accept: 514
- Columns currently routed: 3
- **GAP: 511 columns unreachable via FREE_TEXT**

This means when a user types a general search query (no specific entity type detected),
the search only hits 3 columns instead of 514.

**Coverage: 0.6%**