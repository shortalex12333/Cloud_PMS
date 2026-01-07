# SQL Layer Validation - Database Audit Report

## Executive Summary

**VALIDATION STATUS: CANNOT PROCEED WITHOUT DATA SEEDING**

The current database lacks the data diversity required for meaningful SQL layer validation.
Multiple user-specified test cases are **impossible** with current data.

---

## Critical Gaps

### 1. v_inventory NOT SEARCHABLE

**Problem:** `v_inventory` view exists but is NOT configured in `column_config.py`

- View has columns: location, quantity, min_quantity, needs_reorder
- But SQL layer cannot query it
- User queries like "inventory box 2d" will fail at TABLE ROUTING, not data matching

**Impact:** All inventory-based queries fail before execution

### 2. Location Format Mismatch

**Problem:** Expected location format does not exist in database

| User Example | Expected Format | Actual Data |
|-------------|-----------------|-------------|
| "inventory box 2d" | box 2d, 2d | Agent - Monaco, Shipyard, Yacht |
| "inventory box 4a" | box 4a, 4a | Agent - Palma, Agent - Antibes |
| "locker 3B" | locker 3B | (no locker locations exist) |

**Impact:** Location-based filtering CANNOT work

### 3. No Out-of-Stock Items

**Problem:** Zero items with quantity <= 0

| Metric | Count |
|--------|-------|
| Out of stock (qty <= 0) | 0 |
| Low stock (0 < qty <= 2) | 36 |
| Normal stock (qty > 2) | 214 |
| NULL quantity | 93 |

**Impact:** "out of stock" queries return empty (correct but untestable)

### 4. No "Pending" Work Order Status

**Problem:** Work orders use different status values

| Expected | Actual Data |
|----------|-------------|
| pending | planned |
| in_progress | in_progress |
| completed | completed |

**Impact:** "pending work orders" queries fail semantic filter

### 5. No Priority Diversity

**Problem:** All work orders have priority = "routine"

| Priority | Count |
|----------|-------|
| routine | 50 |
| high | 0 |
| critical | 0 |

**Impact:** Priority-based filtering untestable

---

## Table Coverage Summary

| Table | Rows | Searchable | Notes |
|-------|------|------------|-------|
| pms_parts | 343 | YES | No location column |
| v_inventory | 343 | **NO** | Not in column_config |
| pms_equipment | 50 | YES | Has location |
| pms_work_orders | 50 | YES | No pending status |
| pms_faults | 50 | YES | Good coverage |
| pms_suppliers | 50 | YES | Limited fields |
| symptom_aliases | 37 | YES | Good coverage |
| graph_nodes | 109 | YES | |
| graph_edges | 68 | N/A | Not directly searchable |
| search_document_chunks | 47166 | Partial | Vector search only |

---

## Required Seeding

### Minimum Data Requirements

1. **Add v_inventory to column_config.py**
   - Map location, quantity, needs_reorder columns
   - Support LOCATION entity type
   - Support qty <= 0 filter for OUT_OF_STOCK

2. **Create location-based test data**
   - Add stock records with locations: BOX-2A, BOX-2B, BOX-2C, BOX-2D, BOX-4A, LOCKER-3B
   - At least 5-10 items per location

3. **Create out-of-stock test data**
   - Add 10+ stock records with quantity = 0
   - Add 10+ stock records with quantity < min_quantity (needs_reorder = true)

4. **Add "pending" status mapping**
   - Either add "pending" to work_order_status enum
   - OR map "planned" to PENDING semantic filter

5. **Add priority diversity**
   - Update some work orders to high/critical priority

---

## Architectural Issues

### Filter Dictionary Mismatch

The filter dictionary defines semantic predicates that may not match database values:

| Filter | Expected Behavior | Database Reality |
|--------|-------------------|------------------|
| OUT_OF_STOCK | quantity <= 0 | No items match |
| PENDING | status = 'pending' | Status = 'planned' |
| OVERDUE | due_date < NOW | Needs verification |

### ID Recognizer Gaps

| Pattern | Coverage | Gap |
|---------|----------|-----|
| EQUIPMENT_CODE | ME-S-001 format works | |
| FAULT_CODE | E047 works | |
| LOCATION_CODE | "4A" recognized | But no "BOX-2D" pattern |
| PART_NUMBER | Multi-segment works | |

---

## Recommendation

1. **DO NOT proceed with 1500 tests until data is seeded**
2. **Add v_inventory to column_config FIRST**
3. **Seed location/stock/status test data**
4. **Then run hostile validation**

Tests run against missing data prove nothing except that the system correctly returns empty results for missing data - which is trivially true and provides no information about correctness.
