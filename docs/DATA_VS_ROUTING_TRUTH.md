# DATA vs ROUTING: The Truth

## The Distinction You Correctly Identified

| Issue | Description | Fix Required |
|-------|-------------|--------------|
| **Column has data, no route** | BUG - search logic wrong | Fix routing |
| **Column has no data, no route** | NOT A BUG | Populate data first |
| **Column has no data, has route** | Wasteful but not broken | Populate or remove route |

---

## TABLES WITH DATA (9 tables)

### pms_parts (250 rows)
| Column | Has Data | Has Route | Status |
|--------|----------|-----------|--------|
| part_number | YES | YES (PART_NUMBER) | OK |
| name | YES | YES (PART_NAME) | OK |
| manufacturer | YES | YES (MANUFACTURER) | OK |
| description | YES | NO | **BUG - NEEDS ROUTE** |
| category | YES | NO | **BUG - NEEDS ROUTE** |
| model_compatibility | YES | NO | Consider routing |
| metadata | YES | NO | Consider routing |

### v_inventory (250 rows)
| Column | Has Data | Has Route | Status |
|--------|----------|-----------|--------|
| part_number | YES | YES (PART_NUMBER) | OK |
| name | YES | YES (PART_NAME) | OK |
| location | YES | YES (STOCK_LOCATION) | OK |
| manufacturer | YES | NO | **BUG - NEEDS ROUTE** |
| description | YES | NO | **BUG - NEEDS ROUTE** |
| category | YES | NO | **BUG - NEEDS ROUTE** |
| equipment | YES | NO | **BUG - NEEDS ROUTE** |
| system | YES | NO | **BUG - NEEDS ROUTE** |

### graph_nodes (106 rows)
| Column | Has Data | Has Route | Status |
|--------|----------|-----------|--------|
| label | YES | YES (EQUIPMENT_NAME, etc) | OK |
| normalized_label | YES | YES (CANONICAL_ENTITY) | OK |
| node_type | YES | YES (NODE_TYPE) | OK |
| extraction_source | YES | NO | Consider routing |
| properties | YES | NO | Consider routing |

### search_document_chunks (4036 rows)
| Column | Has Data | Has Route | Status |
|--------|----------|-----------|--------|
| content | YES | YES (DOCUMENT_QUERY) | OK |
| section_title | **NO** | YES (SECTION_NAME) | Data needs population |
| doc_type | **NO** | YES (DOC_TYPE) | Data needs population |
| system_tag | **NO** | NO | Data needs population |
| graph_extract_status | YES | NO | Consider routing |

### symptom_aliases (37 rows)
| Column | Has Data | Has Route | Status |
|--------|----------|-----------|--------|
| alias | YES | YES (SYMPTOM_NAME) | OK |
| symptom_code | YES | NO | Consider routing |

### search_fault_code_catalog (2 rows)
| Column | Has Data | Has Route | Status |
|--------|----------|-----------|--------|
| code | YES | YES (FAULT_CODE) | OK |
| severity | YES | YES (SEVERITY) | OK |
| description | **NO** | NO | Data needs population |
| symptoms | YES | NO | **BUG - NEEDS ROUTE** |
| causes | YES | NO | **BUG - NEEDS ROUTE** |
| diagnostic_steps | YES | NO | **BUG - NEEDS ROUTE** |
| resolution_steps | YES | NO | **BUG - NEEDS ROUTE** |

### entity_staging (904 rows)
| Column | Has Data | Has Route | Status |
|--------|----------|-----------|--------|
| entity_type | YES | NO | Consider routing |
| entity_value | YES | NO | **BUG - NEEDS ROUTE** |
| canonical_label | YES | NO | **BUG - NEEDS ROUTE** |
| status | YES | NO | Consider routing |

### maintenance_facts (4 rows)
| Column | Has Data | Has Route | Status |
|--------|----------|-----------|--------|
| action | YES | NO | **BUG - NEEDS ROUTE** |
| interval_description | **NO** | NO | Data needs population |

---

## TABLES WITHOUT DATA (3 tables) - NEED POPULATION FIRST

| Table | Rows | Columns | Action |
|-------|------|---------|--------|
| pms_equipment | 0 | 13 | **POPULATE DATA** |
| pms_work_orders | 0 | 9 | **POPULATE DATA** |
| pms_suppliers | 0 | 7 | **POPULATE DATA** |

---

## ACTUAL BUGS (Data exists, route missing)

These are the REAL bugs - columns with data that search can't reach:

| Table | Column | Sample Data | Priority |
|-------|--------|-------------|----------|
| pms_parts | description | "High-pressure fuel..." | HIGH |
| pms_parts | category | "Engine Room" | HIGH |
| v_inventory | manufacturer | "Cummins" | HIGH |
| v_inventory | description | "Fuel filter..." | HIGH |
| v_inventory | category | "Engine Room" | HIGH |
| v_inventory | equipment | "Generator 1" | HIGH |
| v_inventory | system | "Electrical System" | HIGH |
| search_fault_code_catalog | symptoms | ["vibration", "noise"] | MEDIUM |
| search_fault_code_catalog | causes | ["worn bearing"] | MEDIUM |
| search_fault_code_catalog | diagnostic_steps | [...] | MEDIUM |
| search_fault_code_catalog | resolution_steps | [...] | MEDIUM |
| entity_staging | entity_value | (904 entities) | MEDIUM |
| entity_staging | canonical_label | (904 labels) | MEDIUM |
| maintenance_facts | action | "oil change" | LOW |

**Total: 14 columns with data that need routing**

---

## DATA NEEDS POPULATION

Before routing would help, these columns need data:

| Table | Column | Currently | Need |
|-------|--------|-----------|------|
| search_document_chunks | section_title | EMPTY | Extract from PDFs |
| search_document_chunks | doc_type | EMPTY | Classify documents |
| search_document_chunks | system_tag | EMPTY | Tag with system |
| search_fault_code_catalog | description | EMPTY | Add descriptions |
| maintenance_facts | interval_description | EMPTY | Add text intervals |
| pms_equipment | * | 0 rows | Import equipment list |
| pms_work_orders | * | 0 rows | Import work orders |
| pms_suppliers | * | 0 rows | Import suppliers |

---

## CORRECTED SUMMARY

| Category | Count | Action |
|----------|-------|--------|
| Columns with data AND route | ~15 | OK |
| **Columns with data, NO route** | **14** | **FIX ROUTING** |
| Columns without data, no route | ~500 | Populate data first |
| Tables completely empty | 3 | Populate data first |

**The 0.6% FREE_TEXT coverage I claimed was misleading.**

The real issue is:
- 14 columns have data but can't be searched
- 500+ columns are empty (need data first)
- 3 entire tables are empty (need data first)

---

## IMMEDIATE FIXES (Routing for existing data)

Add these to ENTITY_SOURCE_MAP["FREE_TEXT"]:

```python
# pms_parts
SearchSource("pms_parts", "description", MatchType.ILIKE, Wave.WAVE_1),
SearchSource("pms_parts", "category", MatchType.ILIKE, Wave.WAVE_1),

# v_inventory
SearchSource("v_inventory", "manufacturer", MatchType.ILIKE, Wave.WAVE_1),
SearchSource("v_inventory", "description", MatchType.ILIKE, Wave.WAVE_1),
SearchSource("v_inventory", "category", MatchType.ILIKE, Wave.WAVE_1),
SearchSource("v_inventory", "equipment", MatchType.ILIKE, Wave.WAVE_1),
SearchSource("v_inventory", "system", MatchType.ILIKE, Wave.WAVE_1),

# search_fault_code_catalog
SearchSource("search_fault_code_catalog", "symptoms", MatchType.ILIKE, Wave.WAVE_1),
SearchSource("search_fault_code_catalog", "causes", MatchType.ILIKE, Wave.WAVE_1),

# entity_staging
SearchSource("entity_staging", "entity_value", MatchType.ILIKE, Wave.WAVE_2),
SearchSource("entity_staging", "canonical_label", MatchType.ILIKE, Wave.WAVE_2),

# maintenance_facts
SearchSource("maintenance_facts", "action", MatchType.ILIKE, Wave.WAVE_2),
```

## DATA POPULATION PRIORITY

1. **pms_equipment** - Critical for equipment searches
2. **search_document_chunks.section_title** - Enables section navigation
3. **search_document_chunks.doc_type** - Enables doc type filtering
4. **pms_work_orders** - Enables work order tracking
5. **pms_suppliers** - Enables supplier lookup
