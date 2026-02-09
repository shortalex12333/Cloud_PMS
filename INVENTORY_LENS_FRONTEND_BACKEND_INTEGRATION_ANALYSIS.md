# Inventory Lens - Frontend/Backend Integration Analysis
## Deep Dive: Payload → Rendering → Action Execution → Role Compliance

**Date**: 2026-02-07
**Analysis Scope**: End-to-end user journeys from backend API → frontend rendering → action execution
**Status**: 🔴 CRITICAL ISSUES IDENTIFIED

---

## Executive Summary

### What I Found

**Documentation is excellent** ✅
- Clear UX Flow Analysis
- Detailed User Journeys
- Well-defined P0 Action Contracts
- 16 inventory actions documented (11 MUTATE, 5 READ)

**Entity Extraction is working** ✅
- Entities being extracted correctly (STOCK_STATUS, EQUIPMENT_NAME, PART, etc.)
- Confidence scores reasonable (0.72-0.80)
- Capability mapping active (inventory_by_location selected)

**Critical Backend Execution Failure** 🔴
- API returns **ZERO inventory/part results** even when queries are correct
- Entities extracted → Capabilities selected → **SQL query returns empty results**
- Only returns Work Order or Equipment results, never actual parts/inventory items

**Actions are generic/outdated** ⚠️
- `available_actions` shows old action names: `view_stock`, `reorder`, `adjust_quantity`
- P0 Action Contracts define: `check_stock_level`, `log_part_usage`, `add_to_shopping_list`
- Mismatch between documentation and implementation

---

## Table of Contents

1. [Documentation Review](#1-documentation-review)
2. [API Response Analysis](#2-api-response-analysis)
3. [Critical Issues Identified](#3-critical-issues-identified)
4. [Expected vs Actual Comparison](#4-expected-vs-actual-comparison)
5. [Frontend Requirements](#5-frontend-requirements)
6. [Action Execution & Role Policies](#6-action-execution--role-policies)
7. [Comprehensive Test Scenarios](#7-comprehensive-test-scenarios)
8. [Recommendations](#8-recommendations)

---

## 1. Documentation Review

### 1.1 UX Flow Analysis (INVENTORY_LENS_UX_FLOW_ANALYSIS.md)

**Core Philosophy**:
- Context-driven activation (lens activates when user focuses on a part, not navigation)
- 3 Adaptation Mechanisms:
  1. **Contextual Activation**: Triggered by part detail view, search results, equipment related parts
  2. **Situation Modifier**: UI adapts based on stock status (low/out/adequate)
  3. **Merge Logic**: Prevents duplicate shopping list requests

**6 Core Actions** (from UX doc):
1. `log_part_usage` - Record consumption
2. `add_to_shopping_list` - Request reorder
3. `update_stock_count` - Manual adjustment
4. `edit_part_details` - Update metadata
5. `view_usage_history` - Show consumption timeline
6. `archive_part` - Soft delete (Captain/HoD signature)

**Dynamic Action Reordering**:
- **Normal state** (green badge): Primary = [Log Usage]
- **Low stock state** (yellow badge): Primary = [Add to Shopping List] (promoted)
- **Out of stock** (red badge): Primary = [Add to Shopping List] (promoted, critical)

**Pre-fill Intelligence**:
```javascript
// Low stock auto-calculates
{
  quantity_requested: minimum_quantity - quantity_on_hand,
  urgency: qty === 0 ? 'critical' : 'normal',
  source_notes: "Auto-suggested: Stock below minimum"
}
```

**Success Criteria from UX doc**:
- ✅ Action reordering based on stock status
- ✅ Pre-fill forms from context
- ✅ Merge duplicate shopping list requests
- ✅ ONE dismissible banner (not annoying)
- ✅ Capture the WHY (adjustment reason, usage notes required)

---

### 1.2 User Journeys (inventory_cluster_journeys.md)

**16 Actions Defined**:

| Action | Type | Risk | Signature | Financial Impact |
|--------|------|------|-----------|------------------|
| add_part | MUTATE | MEDIUM | ❌ | Yes |
| adjust_inventory | MUTATE | MEDIUM | ❌ | Yes |
| update_part | MUTATE | LOW | ❌ | No |
| delete_part | MUTATE | MEDIUM | ❌ | Yes |
| transfer_part | MUTATE | LOW | ❌ | No |
| generate_part_label | MUTATE | LOW | ❌ | No |
| log_part_usage | MUTATE | LOW | ❌ | Yes |
| start_receiving_session | MUTATE | LOW | ❌ | No |
| check_in_item | MUTATE | LOW | ❌ | No |
| commit_receiving_session | MUTATE | HIGH | ✅ | Yes |
| scan_barcode | READ | - | ❌ | No |
| search_parts | READ | - | ❌ | No |
| check_stock_level | READ | - | ❌ | No |
| show_storage_location | READ | - | ❌ | No |
| show_parts_needing_reorder | READ | - | ❌ | No |
| view_part_history | READ | - | ❌ | No |

**Key Guardrails**:
- ❌ NO silent state transitions
- ❌ NO implicit commits
- ❌ NO derived state without storage
- ❌ NO system-inferred mutations
- ✅ Adjustment reason required (min 10 chars)
- ✅ Usage notes required (min 10 chars)
- ✅ Cannot go negative
- ✅ Cannot delete if active WO/shopping list references

**Role Restrictions**:
- `delete_part`: Chief Engineer or Captain only
- All others: Any engineer

---

### 1.3 P0 Action Contracts (P0_ACTION_CONTRACTS.md)

#### Action #6: `check_stock_level`

**Type**: READ
**Purpose**: "Look in the storeroom, not ask computer to guess"
**Signature**: No

**Execute Response Schema**:
```json
{
  "status": "success",
  "action": "check_stock_level",
  "result": {
    "part": {
      "id": "uuid",
      "name": "string",
      "part_number": "string",
      "category": "string",
      "description": "string",
      "unit": "each|kg|L|m"
    },
    "stock": {
      "quantity_on_hand": number,
      "minimum_quantity": number,
      "maximum_quantity": number,
      "stock_status": "IN_STOCK|LOW_STOCK|OUT_OF_STOCK|OVERSTOCKED",
      "location": "string",
      "last_counted_at": "datetime",
      "last_counted_by": "string"
    },
    "usage_stats": {
      "last_30_days": number,
      "average_monthly": number,
      "estimated_runout_days": integer
    },
    "pending_orders": []
  }
}
```

#### Action #7: `log_part_usage`

**Type**: MUTATE
**Purpose**: "State 'I took this from stores and used it for this job'"
**Signature**: No

**Has 3 endpoints**:
1. `/v1/actions/log_part_usage/prefill` - GET with query params
2. `/v1/actions/log_part_usage/preview` - POST before execution
3. `/v1/actions/execute` - POST to commit

**Prefill Response**:
```json
{
  "status": "success",
  "prefill_data": {
    "part_id": "uuid",
    "part_name": "MTU Coolant Thermostat",
    "part_number": "MTU-12345",
    "unit": "each",
    "stock_available": 2,
    "work_order_id": "uuid",
    "work_order_number": "WO-2024-089",
    "suggested_quantity": 1,
    "usage_reason": "work_order"
  }
}
```

**Preview Response**:
```json
{
  "status": "success",
  "preview": {
    "action": "log_part_usage",
    "summary": "You are about to log part usage:",
    "changes": {
      "part": "MTU Coolant Thermostat (MTU-12345)",
      "quantity": "1 each",
      "work_order": "WO-2024-089",
      "used_by": "John Smith",
      "used_at": "2026-01-08 14:35 UTC"
    },
    "side_effects": [
      "Inventory will be DEDUCTED by 1 each",
      "Part usage log entry will be created",
      "Stock level will change from 2 → 1",
      "Audit log entry will be created"
    ],
    "inventory_changes": [
      {
        "part": "MTU Coolant Thermostat (MTU-12345)",
        "current_stock": 2,
        "after_usage": 1,
        "warning": null
      }
    ],
    "requires_signature": false,
    "warnings": []
  }
}
```

---

## 2. API Response Analysis

### 2.1 Test Setup

**Endpoint Tested**: `POST https://pipeline-core.int.celeste7.ai/webhook/search`
**Authentication**: JWT token (crew.tenant@alex-short.com)
**Test Date**: 2026-02-07

### 2.2 Test Queries

#### Test 1: "parts low in stock"

**Expected**:
- Domain: inventory
- Entities: `STOCK_STATUS: low stock`
- Results: List of parts where `quantity_on_hand < minimum_quantity`
- Actions: `check_stock_level`, `add_to_shopping_list`

**Actual Response**:
```json
{
  "success": true,
  "query": "parts low in stock",
  "results": [],  // ❌ ZERO RESULTS
  "total_count": 0,
  "available_actions": [
    {"action": "view_stock", "label": "View Stock"},
    {"action": "reorder", "label": "Reorder"},
    {"action": "transfer_stock", "label": "Transfer Stock"},
    {"action": "adjust_quantity", "label": "Adjust Quantity"}
  ],
  "entities": [
    {
      "type": "inventory",
      "value": "in stock",  // ❌ WRONG - should be "low stock"
      "confidence": 0.8,
      "extraction_type": "STOCK_STATUS"
    }
  ],
  "plans": [
    {
      "capability": "inventory_by_location",
      "entity_type": "STOCK_STATUS",
      "entity_value": "in stock",
      "search_column": "name",
      "blocked": false
    }
  ]
}
```

**Issues**:
1. ❌ **Entity extraction error**: Extracted "in stock" instead of "low stock"
2. ❌ **Zero results**: No parts returned despite database having 232 low stock parts (from tenant_data_catalog.md)
3. ⚠️  **Action names don't match**: `view_stock`, `reorder` vs expected `check_stock_level`, `add_to_shopping_list`

---

#### Test 2: "oil filters"

**Expected**:
- Entities: `PART: oil filters`
- Results: List of parts matching "oil filters"
- Actions: `check_stock_level`, `view_part_details`

**Actual Response**:
```json
{
  "success": true,
  "query": "oil filters",
  "results": [],  // ❌ ZERO RESULTS
  "total_count": 0,
  "entities": [
    {
      "type": "equipment",  // ⚠️  Classified as equipment not part
      "value": "oil filters",
      "confidence": 0.8,
      "extraction_type": "EQUIPMENT_NAME"
    }
  ]
}
```

**Issues**:
1. ❌ **Zero results**: Database should have oil filter parts
2. ⚠️  **Entity type mismatch**: Classified as `equipment` instead of `part`

---

#### Test 4: "fire extinguisher out of stock"

**Expected**:
- Entities: `PART: fire extinguisher`, `STOCK_STATUS: out of stock`
- Results: Fire Extinguisher 6kg Dry Powder (Survitec) - 0/9 OUT OF STOCK
- Actions: `check_stock_level`, `add_to_shopping_list` (promoted, critical)

**Actual Response**:
```json
{
  "success": true,
  "query": "fire extinguisher out of stock",
  "results": [
    {
      "id": "5aef5ae4-4fca-414e-9fea-2ac6970c3de9",
      "type": "pms_work_orders",  // ❌ WRONG TABLE
      "title": "Fire Extinguisher Check",
      "subtitle": "Inspect and service fire extinguishers"
    }
  ],
  "total_count": 1,
  "entities": [
    {"type": "equipment", "value": "Fire Extinguisher"},
    {"type": "inventory", "value": "out of stock", "extraction_type": "STOCK_STATUS"},
    {"type": "inventory", "value": "out of stock", "extraction_type": "OUT_OF_STOCK"}
  ],
  "plans": [
    {"capability": "equipment_by_name_or_model", ...},
    {"capability": "inventory_by_location", "entity_type": "STOCK_STATUS", ...},
    {"capability": "inventory_by_location", "entity_type": "OUT_OF_STOCK", ...},
    {"capability": "work_order_by_id", ...}
  ]
}
```

**Issues**:
1. ✅ **Entity extraction correct**: Got `STOCK_STATUS: out of stock` and `OUT_OF_STOCK: out of stock`
2. ✅ **Capability mapping correct**: Selected `inventory_by_location` for both entity types
3. ❌ **Execution failure**: `inventory_by_location` capability ran but returned NO results
4. ❌ **Wrong result type**: Returned Work Order instead of the actual part inventory item
5. 🔴 **Critical**: Database has "Fire Extinguisher 6kg Dry Powder (Survitec) - 0/9 OUT" but API didn't return it

---

### 2.3 API Response Structure

**Actual fields returned**:
```json
{
  "success": boolean,
  "query": string,
  "results": [],
  "total_count": number,
  "available_actions": [],
  "entities": [],
  "plans": [],
  "timing_ms": {},
  "results_by_domain": {},
  "prepare_debug": {},
  "code_version": string
}
```

**Missing fields** (vs documentation expectations):
- ❌ `domain` field (domain detection result)
- ❌ `intent` field (user intent)
- ❌ `microactions` (structured action definitions)
- ❌ `stock_status_modifier` (for UI adaptation)
- ❌ `prefill_data` (for intelligent form pre-filling)

---

## 3. Critical Issues Identified

### 🔴 ISSUE #1: Inventory SQL Query Returns Zero Results

**Severity**: CRITICAL
**Impact**: Inventory Lens is non-functional

**Evidence**:
- Query: "parts low in stock" → 0 results (should return 232 parts per tenant_data_catalog.md)
- Query: "fire extinguisher out of stock" → 0 inventory results (database has "Fire Extinguisher 6kg Dry Powder" at 0/9)
- Query: "oil filters" → 0 results (database should have oil filter parts)

**Root Cause Analysis**:
1. ✅ Entity extraction working (extracts STOCK_STATUS, EQUIPMENT_NAME, PART)
2. ✅ Capability mapping working (selects `inventory_by_location`)
3. ❌ **SQL execution failing**: `inventory_by_location` capability runs but returns empty result set

**Hypothesis**:
- Table name mismatch: Capability might be querying wrong table (e.g., `parts` vs `pms_parts`)
- Schema mismatch: Column names don't match (e.g., `quantity_on_hand` vs `current_quantity_onboard`)
- RLS policy blocking: User's JWT might not have permissions to read `pms_parts`
- Yacht ID filtering: Query might be filtering by wrong yacht_id

**Files to inspect**:
- `/apps/api/execute/table_capabilities.py` - Check `inventory_by_location` SQL query
- `/apps/api/prepare/capability_composer.py` - Check entity → capability mapping
- `/database/migrations/` - Verify `pms_parts` table schema

---

### 🔴 ISSUE #2: Entity Extraction Errors

**Severity**: HIGH
**Impact**: Wrong entities → wrong capabilities → wrong results

**Evidence**:
- Query: "parts **low** in stock" → Extracted: "**in** stock" (missed "low")
- Lost the critical "low" modifier that changes intent from "show all inventory" to "show LOW stock only"

**Root Cause**:
- Entity extraction pattern not matching compound phrases correctly
- "low stock" should be extracted as single STOCK_STATUS entity
- Pattern likely splitting into "low" (ignored?) + "stock" (extracted)

**Fix Required**:
- Add compound anchor: "low stock", "low in stock", "parts low in stock" → STOCK_STATUS: low_stock
- See LENS_IMPLEMENTATION_GUIDE.md: "Compound anchors: 'parts low in stock'"

---

### ⚠️  ISSUE #3: Action Names Don't Match Documentation

**Severity**: MEDIUM
**Impact**: Frontend can't use documented P0 Action Contracts

**Evidence**:

| API Returns | P0 Contract Expects | UX Doc Expects |
|-------------|---------------------|----------------|
| `view_stock` | `check_stock_level` | `check_stock_level` |
| `reorder` | `add_to_shopping_list` | `add_to_shopping_list` |
| `adjust_quantity` | `adjust_inventory` | `update_stock_count` |
| `transfer_stock` | `transfer_part` | - |

**Impact**:
- Frontend developer reads P0_ACTION_CONTRACTS.md
- Implements handlers for `check_stock_level`
- API returns `view_stock`
- Mismatch → frontend can't find handler → buttons don't work

**Fix Required**:
- Standardize on P0 Action Contract names
- Update `available_actions` to return `check_stock_level` not `view_stock`
- Update action router registry

---

### ⚠️  ISSUE #4: No Domain/Intent Detection in Response

**Severity**: MEDIUM
**Impact**: Frontend can't adapt UI based on domain

**Evidence**:
- API response has no `domain` field
- API response has no `intent` field
- LENS_IMPLEMENTATION_GUIDE.md expects: "Banner: show domain/intent/mode"

**Frontend needs**:
- `domain: "inventory"` → Show inventory-specific UI
- `intent: "check_stock"` → vs `intent: "log_usage"` → Different primary actions
- `mode: "low_stock"` → Yellow banner, promoted [Add to Shopping List]

**Current state**:
- Frontend has to infer domain from entity types
- Frontend has to infer intent from query text
- No explicit stock_status_modifier signal

---

### ⚠️  ISSUE #5: No Prefill Data in Response

**Severity**: MEDIUM
**Impact**: Cannot implement intelligent form pre-filling

**UX doc requires**:
```javascript
// When low stock, pre-fill shopping list form:
{
  quantity_requested: minimum_quantity - quantity_on_hand,  // Auto-calculate
  urgency: qty === 0 ? 'critical' : 'normal',
  source_notes: "Auto-suggested: Stock below minimum"
}
```

**Current state**:
- `/webhook/search` returns NO prefill data
- P0 Action Contract defines `/v1/actions/log_part_usage/prefill` endpoint
- But `/webhook/search` doesn't include this in response

**Fix Required**:
- Include `prefill_data` object in API response when action is selected
- OR: Frontend makes separate call to `/v1/actions/{action}/prefill` after user clicks button

---

### ⚠️  ISSUE #6: Action Execution Endpoints Unknown

**Severity**: MEDIUM
**Impact**: Cannot execute actions from frontend

**P0 Contract defines**:
- Prefill: `GET /v1/actions/log_part_usage/prefill`
- Preview: `POST /v1/actions/log_part_usage/preview`
- Execute: `POST /v1/actions/execute`

**Questions**:
1. Are these endpoints implemented?
2. Do they match the schema in P0_ACTION_CONTRACTS.md?
3. Do they enforce role restrictions (delete_part = Chief Engineer only)?
4. Do they validate (min 10 char notes, positive quantities, etc.)?

**Files to inspect**:
- `/apps/api/routes/p0_actions_routes.py` - Check route definitions
- `/apps/api/handlers/inventory_handlers.py` - Check handler implementation

---

## 4. Expected vs Actual Comparison

### 4.1 User Journey: "Check Low Stock Parts"

**User Query**: "parts low in stock"

#### EXPECTED (from documentation):

**1. Entity Extraction**:
- `STOCK_STATUS: low stock`

**2. Domain/Intent Detection**:
- Domain: `inventory`
- Intent: `check_stock`
- Mode: `low_stock_filter`

**3. Capability Selection**:
- `inventory_by_location` with filter: `quantity_on_hand < minimum_quantity`

**4. Execute Results**:
```json
{
  "results": [
    {
      "id": "uuid",
      "type": "pms_parts",
      "name": "Hydraulic Oil Filter",
      "part_number": "DANFOSS-HYD-001",
      "manufacturer": "Danfoss",
      "quantity_on_hand": 5,
      "minimum_quantity": 24,
      "stock_status": "LOW_STOCK",
      "location": "Engine Room",
      "unit": "each"
    },
    {
      "id": "uuid",
      "type": "pms_parts",
      "name": "Raw Water Pump Seal Kit",
      "part_number": "GRUNDFOS-SEAL-KIT",
      "manufacturer": "Grundfos",
      "quantity_on_hand": 4,
      "minimum_quantity": 12,
      "stock_status": "LOW_STOCK",
      "location": "Engine Room",
      "unit": "each"
    }
    // ... 232 total low stock parts
  ],
  "total_count": 232
}
```

**5. Microactions**:
```json
{
  "microactions": [
    {
      "id": "check_stock_level",
      "label": "View Stock Levels",
      "variant": "READ",
      "primary": false
    },
    {
      "id": "add_to_shopping_list",
      "label": "Add to Shopping List",
      "variant": "MUTATE",
      "primary": true,  // PROMOTED for low stock
      "style": "warning"
    }
  ]
}
```

**6. UI Rendering**:
- Yellow banner: "⚠️  232 parts low in stock"
- Table with columns: Part Name, Part #, Mfr, Stock (5/24), Location
- Low stock badge (yellow) on each row
- Primary button: [Add to Shopping List] (yellow, promoted)

---

#### ACTUAL (from API testing):

**1. Entity Extraction**:
- ❌ `STOCK_STATUS: in stock` (WRONG - missing "low")

**2. Domain/Intent Detection**:
- ❌ No `domain` field
- ❌ No `intent` field
- ❌ No `mode` field

**3. Capability Selection**:
- ✅ `inventory_by_location` selected
- ❌ Searched for "in stock" not "low stock"

**4. Execute Results**:
```json
{
  "results": [],  // ❌ EMPTY
  "total_count": 0
}
```

**5. Actions**:
```json
{
  "available_actions": [
    {"action": "view_stock", "label": "View Stock"},
    {"action": "reorder", "label": "Reorder"}
  ]
}
```
- ⚠️  Wrong action names (view_stock vs check_stock_level)
- ❌ No indication of which is primary
- ❌ No `variant` field
- ❌ No `style` hint for UI

**6. UI Rendering**:
- ❌ Cannot render: zero results
- ❌ Cannot show banner: no stock status modifier
- ❌ Cannot prioritize actions: no primary flag

---

### 4.2 User Journey: "Log Part Usage"

**User Context**: Viewing Work Order WO-2024-089 → Clicks "MTU Coolant Thermostat" part

#### EXPECTED (from UX doc):

**1. Lens Activation**:
- User in Work Order lens
- Clicks related part
- Inventory lens activates WITH CONTEXT:
  - `source_work_order_id = WO-2024-089`
  - `source_context = "work_order"`

**2. Microactions** (context-aware):
```json
{
  "microactions": [
    {
      "id": "log_part_usage",
      "label": "Log Usage",
      "variant": "MUTATE",
      "primary": true,  // PRIMARY because from WO context
      "prefill_endpoint": "/v1/actions/log_part_usage/prefill?part_id={uuid}&work_order_id={wo_uuid}"
    },
    {
      "id": "check_stock_level",
      "label": "Check Stock",
      "variant": "READ",
      "primary": false
    }
  ]
}
```

**3. User Clicks [Log Usage]**:
- Frontend calls prefill endpoint
- Backend returns:
```json
{
  "prefill_data": {
    "part_id": "uuid",
    "part_name": "MTU Coolant Thermostat",
    "unit": "each",
    "stock_available": 2,
    "work_order_id": "WO-2024-089",
    "work_order_number": "WO-2024-089",
    "suggested_quantity": 1,
    "usage_reason": "work_order"
  }
}
```

**4. Modal Opens**:
- Quantity field: `1` (pre-filled)
- Work Order: `WO-2024-089` (pre-filled, read-only)
- Usage Reason: `work_order` (pre-selected)
- Notes: (empty, optional)

**5. User Types "Replaced faulty thermostat" → Clicks [Preview]**:
- Frontend calls preview endpoint
- Backend returns:
```json
{
  "preview": {
    "summary": "You are about to log part usage:",
    "changes": {
      "part": "MTU Coolant Thermostat (MTU-12345)",
      "quantity": "1 each",
      "work_order": "WO-2024-089"
    },
    "side_effects": [
      "Inventory will be DEDUCTED by 1 each",
      "Stock level will change from 2 → 1"
    ],
    "inventory_changes": [{"current_stock": 2, "after_usage": 1}],
    "warnings": ["⚠️  Stock will be LOW after this usage (below minimum: 3)"]
  }
}
```

**6. Frontend shows preview modal**:
- "Are you sure?"
- Shows side effects
- Shows stock warning (yellow)
- [Cancel] [Confirm]

**7. User Clicks [Confirm]**:
- Frontend calls execute endpoint
- Backend:
  - Validates (quantity > 0, stock >= quantity)
  - Deducts stock: 2 → 1
  - Creates usage log entry
  - Creates audit log entry
  - Returns success

**8. Frontend updates**:
- Success toast: "✓ Usage logged"
- Part stock updates: 2 → 1
- Badge changes: green → yellow (now low stock)
- [Add to Shopping List] promoted to primary

---

#### ACTUAL (unknown - needs testing):

**Questions**:
1. ❓ Does `/v1/actions/log_part_usage/prefill` endpoint exist?
2. ❓ Does it return the expected schema?
3. ❓ Does preview endpoint exist and work?
4. ❓ Does execute endpoint atomically:
   - Deduct inventory
   - Create usage log
   - Create audit log
   - Validate sufficient stock?
5. ❓ Does it enforce role restrictions?
6. ❓ Does it require min 10 char notes?

**Next Steps**: Test action execution endpoints directly

---

## 5. Frontend Requirements

### 5.1 Required Fields in API Response

For frontend to render Inventory Lens correctly, API response MUST include:

#### A) Search Results
```json
{
  "results": [
    {
      "id": "uuid",
      "type": "pms_parts",  // Explicit table name
      "name": "Hydraulic Oil Filter",
      "part_number": "DANFOSS-HYD-001",
      "manufacturer": "Danfoss",
      "category": "Hydraulic",
      "quantity_on_hand": 5,
      "minimum_quantity": 24,
      "maximum_quantity": null,
      "stock_status": "LOW_STOCK",  // Calculated: IN_STOCK|LOW_STOCK|OUT_OF_STOCK|OVERSTOCKED
      "location": "Engine Room",
      "unit": "each",
      "last_counted_at": "2026-01-15T10:30:00Z",
      "last_counted_by": "John Smith",
      "description": "Hydraulic system oil filter for deck cranes"
    }
  ]
}
```

#### B) Domain/Intent Detection
```json
{
  "domain": "inventory",
  "intent": "check_stock",  // check_stock | log_usage | adjust_stock | add_part
  "mode": "low_stock_filter"  // Optional modifier for UI adaptation
}
```

#### C) Microactions (Structured)
```json
{
  "microactions": [
    {
      "id": "check_stock_level",  // Matches P0 Action Contract
      "label": "Check Stock Level",
      "variant": "READ",
      "primary": false,
      "endpoints": {
        "execute": "/v1/actions/execute"
      },
      "requires_signature": false,
      "allowed_roles": ["all"]
    },
    {
      "id": "add_to_shopping_list",
      "label": "Add to Shopping List",
      "variant": "MUTATE",
      "primary": true,  // Promoted for low stock
      "style": "warning",  // yellow button
      "endpoints": {
        "prefill": "/v1/actions/add_to_shopping_list/prefill?part_id={id}",
        "preview": "/v1/actions/add_to_shopping_list/preview",
        "execute": "/v1/actions/execute"
      },
      "requires_signature": false,
      "allowed_roles": ["engineer", "chief_engineer", "captain"]
    },
    {
      "id": "log_part_usage",
      "label": "Log Usage",
      "variant": "MUTATE",
      "primary": false,
      "endpoints": {
        "prefill": "/v1/actions/log_part_usage/prefill?part_id={id}&work_order_id={wo_id}",
        "preview": "/v1/actions/log_part_usage/preview",
        "execute": "/v1/actions/execute"
      },
      "requires_signature": false
    }
  ]
}
```

#### D) Prefill Data (Optional, per action)
```json
{
  "prefill_context": {
    "source_work_order_id": "uuid",
    "source_equipment_id": "uuid",
    "stock_modifier": "low_stock",  // Triggers auto-calculation
    "suggested_actions": {
      "add_to_shopping_list": {
        "quantity_requested": 19,  // min - current
        "urgency": "normal",
        "source_notes": "Auto-suggested: Stock below minimum"
      }
    }
  }
}
```

---

### 5.2 Frontend Rendering Logic

#### Component: InventoryLensBanner

**Purpose**: Show stock status alert (one dismissible banner)

**Input**: API response `mode` field + result `stock_status`

**Logic**:
```typescript
if (mode === 'low_stock_filter' || results.some(r => r.stock_status === 'LOW_STOCK')) {
  showBanner({
    type: 'warning',  // yellow
    message: `⚠️  ${lowStockCount} parts low in stock`,
    action: {
      label: 'Add All to Shopping List',
      onClick: () => bulkAddToShoppingList()
    },
    dismissible: true
  });
}

if (results.some(r => r.stock_status === 'OUT_OF_STOCK')) {
  showBanner({
    type: 'error',  // red
    message: `🚨 ${outOfStockCount} parts OUT OF STOCK`,
    action: {
      label: 'Create Urgent Shopping List',
      onClick: () => createUrgentShoppingList()
    },
    dismissible: true
  });
}
```

---

#### Component: InventoryTable

**Columns**:
| Column | Source Field | Rendering |
|--------|--------------|-----------|
| Status Badge | `stock_status` | 🟢 IN_STOCK / 🟡 LOW_STOCK / 🔴 OUT |
| Part Name | `name` | Bold, clickable |
| Part Number | `part_number` | Monospace font |
| Manufacturer | `manufacturer` | Plain text |
| Stock | `quantity_on_hand` / `minimum_quantity` | "5/24 ea" (color-coded) |
| Location | `location` | With location icon |
| Last Counted | `last_counted_at` | Relative time "15 days ago" |

**Badge Color Logic**:
```typescript
function getStockBadge(part) {
  if (part.stock_status === 'OUT_OF_STOCK') {
    return { color: 'red', label: 'OUT', icon: '🔴' };
  }
  if (part.stock_status === 'LOW_STOCK') {
    return { color: 'yellow', label: 'LOW', icon: '🟡' };
  }
  if (part.stock_status === 'OVERSTOCKED') {
    return { color: 'blue', label: 'OVER', icon: '🔵' };
  }
  return { color: 'green', label: 'OK', icon: '🟢' };
}
```

---

#### Component: InventoryActions

**Purpose**: Show microaction buttons with dynamic prioritization

**Input**: `microactions` array from API

**Logic**:
```typescript
// Sort actions: primary first
const sortedActions = microactions.sort((a, b) => {
  if (a.primary && !b.primary) return -1;
  if (!a.primary && b.primary) return 1;
  return 0;
});

// Render
sortedActions.map(action => (
  <Button
    key={action.id}
    variant={action.primary ? 'primary' : 'secondary'}
    color={action.style || 'default'}  // yellow for warning
    onClick={() => executeAction(action)}
    disabled={!hasRole(action.allowed_roles)}
  >
    {action.label}
  </Button>
));
```

**Example Rendering** (low stock part):
```
[Add to Shopping List] (yellow, primary)
[Check Stock Level] (gray, secondary)
[Log Usage] (gray, secondary)
```

---

### 5.3 Stock Status UI Adaptation

**State Machine**:
```
stock_status = "IN_STOCK"
  → Badge: 🟢 Green "OK"
  → Primary Action: [Log Usage]
  → Banner: None

stock_status = "LOW_STOCK"
  → Badge: 🟡 Yellow "LOW"
  → Primary Action: [Add to Shopping List] (promoted)
  → Banner: "⚠️  Stock below minimum" (dismissible, yellow)

stock_status = "OUT_OF_STOCK"
  → Badge: 🔴 Red "OUT"
  → Primary Action: [Add to Shopping List] (promoted)
  → Banner: "🚨 OUT OF STOCK - Urgent reorder needed" (dismissible, red)
  → Disable: [Log Usage] (can't use what doesn't exist)

stock_status = "OVERSTOCKED"
  → Badge: 🔵 Blue "OVER"
  → Primary Action: [Transfer Stock] or [Adjust Quantity]
  → Banner: None (overstocked is informational, not urgent)
```

---

## 6. Action Execution & Role Policies

### 6.1 P0 Actions Implementation Checklist

#### ✅ Action: `check_stock_level` (READ)

**Backend Handler**: `/apps/api/handlers/inventory_handlers.py` - `check_stock_level_execute`

**Endpoint**: `POST /v1/actions/execute`
```json
{
  "action": "check_stock_level",
  "context": {"yacht_id": "uuid", "user_id": "uuid", "role": "engineer"},
  "payload": {"part_id": "uuid"}
}
```

**Expected Response**:
```json
{
  "status": "success",
  "action": "check_stock_level",
  "result": {
    "part": {...},
    "stock": {
      "quantity_on_hand": 5,
      "minimum_quantity": 24,
      "stock_status": "LOW_STOCK",
      "location": "Engine Room",
      "last_counted_at": "2026-01-15T10:30:00Z",
      "last_counted_by": "John Smith"
    },
    "usage_stats": {
      "last_30_days": 15,
      "average_monthly": 15,
      "estimated_runout_days": 10
    }
  }
}
```

**Role Policy**: All roles can execute (READ action)

**Test**: ✅ Implemented (from inventory_handlers.py lines 42-165)

---

#### ✅ Action: `log_part_usage` (MUTATE)

**Backend Handler**: `/apps/api/handlers/inventory_handlers.py` - `log_part_usage_execute`

**Endpoints**:
1. Prefill: `GET /v1/actions/log_part_usage/prefill?part_id={uuid}&work_order_id={uuid}`
2. Preview: `POST /v1/actions/log_part_usage/preview`
3. Execute: `POST /v1/actions/execute`

**Validations**:
- ✅ Quantity > 0
- ✅ Sufficient stock (cannot go negative)
- ✅ Work order exists (if work_order_id provided)
- ⚠️  Notes NOT required (contrast: User Journey doc says "min 10 chars" required)

**Atomic Operations**:
1. Lock part row (prevent race conditions)
2. Check sufficient stock
3. Deduct quantity: `current_quantity_onboard -= quantity`
4. Create usage log entry in `pms_part_usage`
5. Create audit log entry in `pms_audit_log`
6. Commit transaction

**Role Policy**: All engineer roles

**Test**: ✅ Implemented (lines 354-564)

**⚠️  DISCREPANCY FOUND**:
- User Journey doc says: "Usage notes required (min 10 chars)"
- Handler code: `notes` is optional in schema (line 251: `Optional[str]`)
- **FIX**: Add validation to require notes when usage_reason="other"

---

#### ❓ Action: `add_to_shopping_list` (MUTATE)

**Expected Endpoints**:
1. Prefill: `GET /v1/actions/add_to_shopping_list/prefill?part_id={uuid}`
2. Preview: `POST /v1/actions/add_to_shopping_list/preview`
3. Execute: `POST /v1/actions/execute`

**Expected Prefill Response** (low stock part):
```json
{
  "prefill_data": {
    "part_id": "uuid",
    "part_name": "Hydraulic Oil Filter",
    "part_number": "DANFOSS-HYD-001",
    "quantity_requested": 19,  // Auto-calculated: min - current
    "source_type": "inventory_low",
    "urgency": "normal",  // or "critical" if qty = 0
    "source_notes": "Auto-suggested: Stock below minimum (5/24)"
  }
}
```

**Merge Logic** (from UX doc):
```sql
-- If pending request exists
IF EXISTS (
  SELECT 1 FROM pms_shopping_list_items
  WHERE part_id = <current_part>
  AND status = 'pending'
) THEN
  -- MERGE: Update existing request
  UPDATE pms_shopping_list_items
  SET quantity_requested = quantity_requested + <new_qty>
  WHERE part_id = <current_part> AND status = 'pending'

ELSIF EXISTS (
  SELECT 1 FROM pms_shopping_list_items
  WHERE part_id = <current_part>
  AND status IN ('approved', 'ordered')
) THEN
  -- CREATE NEW with warning
  INSERT INTO pms_shopping_list_items ...
  SHOW WARNING: "Existing order in progress - creating additional request"

ELSE
  -- CREATE FIRST request
  INSERT INTO pms_shopping_list_items ...
END IF
```

**Status**: ❓ Need to verify if implemented

---

#### ❓ Action: `adjust_inventory` / `update_stock_count` (MUTATE)

**Backend Handler**: ❓ (name conflict: `adjust_inventory` vs `update_stock_count`)

**Expected Validation**:
- ✅ Reason required (min 10 chars)
- ✅ New quantity >= 0 (cannot go negative)
- ✅ Creates inventory transaction log
- ✅ Creates audit log

**Role Policy**: All engineer roles

**Status**: ❓ Need to verify endpoint exists

---

#### ❓ Action: `delete_part` / `archive_part` (MUTATE)

**Backend Handler**: ❓

**Expected Validation**:
- ✅ Chief Engineer or Captain only (role restriction)
- ✅ Check for active references:
  - Block if part in active work orders
  - Block if part in active shopping list
- ✅ Soft delete (set `deleted_at`, not hard delete)

**Status**: ❓ Need to verify implementation

---

### 6.2 Role-Based Access Control Matrix

| Action | Crew | Deckhand | Engineer | Chief Engineer | Captain |
|--------|------|----------|----------|----------------|---------|
| check_stock_level | ✅ | ✅ | ✅ | ✅ | ✅ |
| log_part_usage | ❌ | ✅ | ✅ | ✅ | ✅ |
| add_to_shopping_list | ❌ | ✅ | ✅ | ✅ | ✅ |
| adjust_inventory | ❌ | ❌ | ✅ | ✅ | ✅ |
| delete_part | ❌ | ❌ | ❌ | ✅ | ✅ |
| transfer_part | ❌ | ✅ | ✅ | ✅ | ✅ |
| commit_receiving_session | ❌ | ❌ | ❌ | ✅ | ✅ |

**Implementation**:
- Middleware validates JWT role
- Handler checks `allowed_roles` from action definition
- Returns 403 Forbidden if role not allowed

**Test Cases Needed**:
1. Crew tries to log usage → 403
2. Deckhand tries to delete part → 403
3. Engineer tries to delete part → 403
4. Chief Engineer deletes part → 200 OK

---

## 7. Comprehensive Test Scenarios

### 7.1 End-to-End Journey Tests

#### Test Scenario 1: Engineer Checks Low Stock Parts

**User**: Engineer (role: engineer)
**Entry Point**: Dashboard → "Low Stock Alert" notification

**Steps**:
1. User clicks notification
2. Frontend: `POST /webhook/search` with query: "parts low in stock"
3. Backend:
   - Extract entities: `STOCK_STATUS: low stock`
   - Map to capability: `inventory_by_location`
   - Execute SQL: `SELECT * FROM pms_parts WHERE yacht_id = X AND quantity_on_hand < minimum_quantity`
   - Return 232 parts
4. Frontend renders:
   - Yellow banner: "⚠️  232 parts low in stock"
   - Table with 232 rows
   - Each row has 🟡 LOW badge
   - Primary action: [Add to Shopping List] (yellow)
5. User clicks [Add to Shopping List] on "Hydraulic Oil Filter"
6. Frontend: `GET /v1/actions/add_to_shopping_list/prefill?part_id={uuid}`
7. Backend returns:
   ```json
   {
     "quantity_requested": 19,
     "urgency": "normal",
     "source_notes": "Auto-suggested: Stock below minimum (5/24)"
   }
   ```
8. Modal opens with pre-filled values
9. User clicks [Preview]
10. Frontend: `POST /v1/actions/add_to_shopping_list/preview`
11. Backend returns preview with merge warning: "Existing pending request for 10 units. This will add 19 more (total: 29)"
12. User clicks [Confirm]
13. Frontend: `POST /v1/actions/execute`
14. Backend:
    - Merges request: `UPDATE quantity_requested = 10 + 19 = 29`
    - Returns success
15. Frontend shows success toast: "✓ Added to shopping list (merged with existing request)"

**Expected Result**: ✅ Stock visibility → intelligent prefill → merge logic → no duplicates

**Current Status**: 🔴 FAILS at step 3 (zero results returned)

---

#### Test Scenario 2: Engineer Logs Part Usage from Work Order

**User**: Engineer (role: engineer)
**Entry Point**: Work Order WO-2024-089 → "Parts Needed" section

**Steps**:
1. User viewing Work Order detail page
2. Sees "Parts Needed: MTU Coolant Thermostat (2 in stock)"
3. User clicks part name
4. Frontend: Opens Inventory Lens in modal/side panel
   - Passes context: `source_work_order_id=WO-2024-089`
5. Inventory Lens activates with part detail
6. **Primary action reordered**: [Log Usage] is PRIMARY (because from WO context)
7. User clicks [Log Usage]
8. Frontend: `GET /v1/actions/log_part_usage/prefill?part_id={uuid}&work_order_id=WO-2024-089`
9. Backend returns:
   ```json
   {
     "part_name": "MTU Coolant Thermostat",
     "stock_available": 2,
     "work_order_number": "WO-2024-089",
     "suggested_quantity": 1,
     "usage_reason": "work_order"
   }
   ```
10. Modal opens:
    - Quantity: `1` (pre-filled, focused)
    - Work Order: `WO-2024-089` (read-only, pre-filled)
    - Usage Reason: `work_order` (pre-selected)
    - Notes: (empty)
11. User types "Replaced faulty thermostat"
12. User clicks [Preview]
13. Frontend: `POST /v1/actions/log_part_usage/preview`
14. Backend returns:
    ```json
    {
      "preview": {
        "side_effects": [
          "Stock will change from 2 → 1",
          "Usage logged to WO-2024-089"
        ],
        "warnings": ["⚠️  Stock will be LOW after (below min: 3)"]
      }
    }
    ```
15. Preview modal shows warning in yellow
16. User clicks [Confirm]
17. Frontend: `POST /v1/actions/execute`
18. Backend:
    - Locks part row
    - Validates: stock (2) >= quantity (1) ✅
    - Deducts: 2 - 1 = 1
    - Creates usage log linked to WO-2024-089
    - Creates audit log
    - Commits
19. Frontend:
    - Success toast: "✓ Usage logged"
    - Part detail updates: stock 2 → 1
    - Badge changes: 🟢 → 🟡 (now low stock)
    - **Actions reorder**: [Add to Shopping List] promoted to PRIMARY
    - Yellow banner appears: "⚠️  Low stock: 1 remaining (reorder at 3)"

**Expected Result**: ✅ Context-aware activation → intelligent prefill → preview with warning → stock update → UI adaptation

**Current Status**: ❓ Unknown (need to test action endpoints)

---

#### Test Scenario 3: Chief Engineer Deletes Obsolete Part

**User**: Chief Engineer (role: chief_engineer)
**Entry Point**: Part detail page for "Old Hydraulic Hose (HYD-OLD-001)"

**Steps**:
1. User views part: stock = 0, min = 0 (obsolete)
2. Sees action: [Delete Part] (only visible to Chief Engineer+)
3. User clicks [Delete Part]
4. Confirmation modal:
   ```
   Delete Part HYD-OLD-001?

   ⚠️  This will soft-delete the part.
   Part will no longer appear in searches.

   Reason: [required, text area]
   ```
5. User enters: "Obsolete. Replaced by HYD-3875."
6. User clicks [Confirm Delete]
7. Frontend: `POST /v1/actions/execute`
8. Backend:
   - Validates role: chief_engineer ✅
   - Checks active references:
     - Active WOs: 0 ✅
     - Active shopping list: 0 ✅
   - Soft deletes: `UPDATE pms_parts SET deleted_at = NOW()`
   - Creates audit log
9. Frontend: Redirects to parts list (part no longer exists)

**Role Test**:
- Repeat with Engineer role → Should see 403 or hide [Delete Part] button

**Expected Result**: ✅ Role enforcement → validation → soft delete

**Current Status**: ❓ Unknown (need to verify delete_part handler exists)

---

### 7.2 Negative Test Cases

#### Negative Test 1: Insufficient Stock

**Scenario**: User tries to log usage of 10 units when only 2 available

**Steps**:
1. User enters quantity: 10
2. User clicks [Preview]
3. Backend validation:
   ```python
   if part.quantity_on_hand < quantity:
       raise ValidationError("Insufficient stock")
   ```
4. Returns error:
   ```json
   {
     "status": "error",
     "error_code": "INSUFFICIENT_STOCK",
     "message": "Only 2 units available, cannot deduct 10"
   }
   ```
5. Frontend shows error toast
6. User must correct quantity

**Expected**: ✅ Validation prevents negative stock

---

#### Negative Test 2: Delete Part with Active References

**Scenario**: Chief Engineer tries to delete part that's in active WO

**Steps**:
1. Part "Coolant Filter" is in Work Order WO-2024-090 (status: in_progress)
2. Chief Engineer clicks [Delete Part]
3. Backend validation:
   ```sql
   SELECT COUNT(*) FROM work_order_parts
   WHERE part_id = X AND work_order_id IN (
     SELECT id FROM pms_work_orders WHERE status != 'completed'
   )
   -- Returns 1
   ```
4. Returns error:
   ```json
   {
     "status": "error",
     "error_code": "ACTIVE_REFERENCES",
     "message": "Cannot delete. Part is referenced in active work orders: WO-2024-090"
   }
   ```
5. Frontend shows error

**Expected**: ✅ Referential integrity enforced

---

#### Negative Test 3: Role Restriction

**Scenario**: Deckhand tries to adjust inventory

**Steps**:
1. Deckhand views part
2. [Adjust Quantity] button is hidden (frontend role check)
3. If bypassed (API call directly):
4. Backend validates:
   ```python
   allowed_roles = ["engineer", "chief_engineer", "captain"]
   if user.role not in allowed_roles:
       raise PermissionError("403 Forbidden")
   ```
5. Returns 403

**Expected**: ✅ Role enforcement (frontend + backend)

---

## 8. Recommendations

### 8.1 CRITICAL (Must Fix for Launch)

#### 🔴 Priority 1: Fix Inventory SQL Query

**Issue**: `inventory_by_location` capability returns zero results

**Files to inspect**:
1. `/apps/api/execute/table_capabilities.py` - Check SQL query
2. `/apps/api/execute/capability_executor.py` - Check execution logic

**Expected SQL** (simplified):
```sql
SELECT
  p.id, p.name, p.part_number, p.manufacturer, p.category,
  p.quantity_on_hand, p.minimum_quantity, p.location, p.unit,
  CASE
    WHEN p.quantity_on_hand = 0 THEN 'OUT_OF_STOCK'
    WHEN p.quantity_on_hand <= p.minimum_quantity THEN 'LOW_STOCK'
    WHEN p.quantity_on_hand > p.maximum_quantity THEN 'OVERSTOCKED'
    ELSE 'IN_STOCK'
  END as stock_status
FROM pms_parts p
WHERE p.yacht_id = $1
  AND p.deleted_at IS NULL
  AND ($2::text IS NULL OR p.name ILIKE '%' || $2 || '%')
ORDER BY p.name
```

**Test**:
```sql
-- Manual test with real yacht_id
SELECT * FROM pms_parts
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND deleted_at IS NULL
LIMIT 10;
```

**Action**:
1. Find the actual SQL in `table_capabilities.py`
2. Test query directly in database
3. Fix table name / column name mismatches
4. Verify RLS policies allow crew.tenant@alex-short.com to read

---

#### 🔴 Priority 2: Fix Entity Extraction - Compound Phrases

**Issue**: "parts **low** in stock" → extracted as "**in** stock" (lost "low")

**File**: `/apps/api/entity_extraction_loader.py`

**Fix**: Add compound anchors to CORE_STOCK_STATUS gazetteer:
```python
CORE_STOCK_STATUS = {
    # Existing
    'low stock', 'out of stock', 'critically low', ...

    # Add compound variants
    'parts low in stock',
    'parts low on hand',
    'items low in stock',
    'low stock parts',
    'parts below minimum',
    ...
}
```

**Test**:
```python
query = "parts low in stock"
entities = extract_entities(query)
assert entities[0] == {
    "type": "inventory",
    "value": "low stock",  # or "parts low in stock"
    "extraction_type": "STOCK_STATUS"
}
```

---

#### 🔴 Priority 3: Standardize Action Names

**Issue**: API returns `view_stock`, docs expect `check_stock_level`

**Files to update**:
1. `/apps/api/action_router/registry.py` - Update action_id definitions
2. Update all handler references

**Before**:
```python
{
    "action": "view_stock",
    "label": "View Stock"
}
```

**After**:
```python
{
    "action_id": "check_stock_level",  // Match P0 contract
    "label": "Check Stock Level",
    "variant": "READ",
    "endpoints": {
        "execute": "/v1/actions/execute"
    }
}
```

---

### 8.2 HIGH (Important for UX)

#### 🟡 Priority 4: Add Domain/Intent/Mode to Response

**File**: `/apps/api/routes/orchestrated_search_routes.py` (or equivalent)

**Add to response**:
```python
response = {
    "success": True,
    "query": query,
    "domain": detected_domain,  // "inventory" | "equipment" | "work_order"
    "intent": detected_intent,  // "check_stock" | "log_usage" | "add_part"
    "mode": stock_status_modifier,  // "low_stock_filter" | "out_of_stock_filter" | None
    "results": results,
    "microactions": microactions,
    ...
}
```

**Domain Detection Logic**:
```python
def detect_domain(entities):
    entity_types = [e['extraction_type'] for e in entities]

    if 'STOCK_STATUS' in entity_types or 'PART' in entity_types:
        return 'inventory'
    elif 'WORK_ORDER_ID' in entity_types:
        return 'work_order'
    elif 'EQUIPMENT_NAME' in entity_types:
        return 'equipment'
    else:
        return 'unknown'
```

---

#### 🟡 Priority 5: Implement Prefill Endpoints

**For each MUTATE action, implement**:
```
GET /v1/actions/{action_id}/prefill?part_id={uuid}&context={...}
```

**Example**: `log_part_usage`
```python
@router.get("/v1/actions/log_part_usage/prefill")
async def log_part_usage_prefill(
    part_id: str,
    work_order_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    part = await get_part(part_id)
    work_order = await get_work_order(work_order_id) if work_order_id else None

    return {
        "status": "success",
        "prefill_data": {
            "part_id": part_id,
            "part_name": part.name,
            "stock_available": part.quantity_on_hand,
            "work_order_id": work_order_id,
            "work_order_number": work_order.number if work_order else None,
            "suggested_quantity": 1,
            "usage_reason": "work_order" if work_order else "other"
        }
    }
```

---

#### 🟡 Priority 6: Add Merge Logic to add_to_shopping_list

**File**: `/apps/api/handlers/shopping_list_handlers.py` (create if not exists)

**Implement**:
```python
async def add_to_shopping_list_execute(part_id, quantity_requested, ...):
    # Check for existing pending request
    existing = await db.query(
        "SELECT * FROM pms_shopping_list_items "
        "WHERE part_id = $1 AND yacht_id = $2 AND status = 'pending'",
        part_id, yacht_id
    )

    if existing:
        # MERGE: Update existing
        await db.execute(
            "UPDATE pms_shopping_list_items "
            "SET quantity_requested = quantity_requested + $1 "
            "WHERE id = $2",
            quantity_requested, existing.id
        )
        return {
            "status": "success",
            "message": f"Merged with existing request (total: {existing.quantity_requested + quantity_requested})",
            "merged": True
        }

    # Check for approved/ordered
    in_progress = await db.query(
        "SELECT * FROM pms_shopping_list_items "
        "WHERE part_id = $1 AND yacht_id = $2 AND status IN ('approved', 'ordered')",
        part_id, yacht_id
    )

    if in_progress:
        # CREATE NEW with warning
        new_id = await db.execute("INSERT INTO pms_shopping_list_items ...")
        return {
            "status": "success",
            "message": "Created new request",
            "warning": f"Existing order in progress ({in_progress.quantity_requested} units)",
            "merged": False
        }

    # CREATE FIRST
    new_id = await db.execute("INSERT INTO pms_shopping_list_items ...")
    return {"status": "success", "merged": False}
```

---

### 8.3 MEDIUM (Polish & Validation)

#### 🟢 Priority 7: Add Validation for Notes/Reason

**File**: `/apps/api/handlers/inventory_handlers.py`

**Update `log_part_usage_execute`**:
```python
# Add validation
if usage_reason == "other" and (not notes or len(notes.strip()) < 10):
    return ResponseBuilder.error(
        action="log_part_usage",
        error_code="NOTES_REQUIRED",
        message="Detailed notes required when usage reason is 'other' (min 10 characters)"
    )
```

**Update `adjust_inventory`** (when implemented):
```python
if not reason or len(reason.strip()) < 10:
    return ResponseBuilder.error(
        action="adjust_inventory",
        error_code="REASON_REQUIRED",
        message="Adjustment reason required (min 10 characters)"
    )
```

---

#### 🟢 Priority 8: Implement Role Restrictions

**Middleware**: `/apps/api/middleware/auth.py`

**Add helper**:
```python
def check_action_permission(action_id: str, user_role: str) -> bool:
    """Check if user role can execute action"""

    role_permissions = {
        "delete_part": ["chief_engineer", "captain"],
        "commit_receiving_session": ["chief_engineer", "captain"],
        "adjust_inventory": ["engineer", "chief_engineer", "captain"],
        # All others: any engineer+
    }

    allowed = role_permissions.get(action_id, ["engineer", "chief_engineer", "captain"])
    return user_role in allowed
```

**Use in handlers**:
```python
@router.post("/v1/actions/execute")
async def execute_action(action_id: str, payload: dict, user=Depends(get_current_user)):
    if not check_action_permission(action_id, user.role):
        raise HTTPException(403, "Role not authorized for this action")

    # Execute...
```

---

### 8.4 Testing Checklist

**Unit Tests**:
- [ ] Entity extraction: "parts low in stock" → STOCK_STATUS: low stock
- [ ] Entity extraction: "fire extinguisher out of stock" → STOCK_STATUS: out of stock + PART: fire extinguisher
- [ ] SQL query returns results: `inventory_by_location` with yacht_id
- [ ] Stock status calculation: 0 → OUT, 5/24 → LOW, 30/24 → IN_STOCK
- [ ] Merge logic: pending request exists → merge
- [ ] Merge logic: approved request exists → create new + warn
- [ ] Validation: insufficient stock → error
- [ ] Validation: notes required when usage_reason="other"
- [ ] Role restriction: deckhand cannot delete_part
- [ ] Role restriction: chief_engineer can delete_part

**Integration Tests**:
- [ ] End-to-end: Search "parts low in stock" → Returns 232 results
- [ ] End-to-end: Click [Add to Shopping List] → Prefill correct quantity
- [ ] End-to-end: Log usage from WO → Context preserved → Stock updated
- [ ] End-to-end: Delete part with active WO → Blocked

**Frontend Tests** (when implemented):
- [ ] Badge color: OUT=red, LOW=yellow, IN=green
- [ ] Action reordering: Low stock → [Add to Shopping List] primary
- [ ] Banner: Show warning for low stock, dismissible
- [ ] Preview modal: Show side effects + warnings
- [ ] Success toast: After action executes

---

## Conclusion

### What Works ✅
1. **Documentation is excellent**: UX Flow, User Journeys, P0 Contracts are clear and comprehensive
2. **Entity extraction foundation**: Entities being extracted with reasonable confidence
3. **Capability mapping**: Correct capabilities selected based on entities
4. **Action handler (partial)**: `check_stock_level` and `log_part_usage` implemented

### Critical Blockers 🔴
1. **SQL query returns zero results**: Inventory lens is non-functional
2. **Entity extraction errors**: "low stock" → "in stock" (missing compound phrases)
3. **Action name mismatches**: API vs documentation inconsistency

### Missing Components ⚠️
1. Domain/Intent/Mode detection in response
2. Prefill endpoints for intelligent form pre-population
3. Merge logic for shopping list requests
4. Role-based action filtering
5. Frontend UI components (not built yet per LENS_IMPLEMENTATION_GUIDE)

### Recommendations Priority
1. 🔴 **CRITICAL**: Fix SQL query (Priority 1) - Enables basic functionality
2. 🔴 **CRITICAL**: Fix entity extraction (Priority 2) - Correct intent detection
3. 🔴 **CRITICAL**: Standardize action names (Priority 3) - Frontend can implement
4. 🟡 **HIGH**: Add domain/intent to response (Priority 4) - UX adaptation
5. 🟡 **HIGH**: Implement prefill endpoints (Priority 5) - Intelligent forms
6. 🟡 **HIGH**: Add merge logic (Priority 6) - Prevent duplicates
7. 🟢 **MEDIUM**: Validation (Priority 7) - Data quality
8. 🟢 **MEDIUM**: Role restrictions (Priority 8) - Security

### Next Steps
1. Inspect `/apps/api/execute/table_capabilities.py` to find SQL query
2. Test SQL directly in database to verify data exists
3. Fix table/column name mismatches
4. Re-run API payload tests
5. Verify results are returned
6. Continue with entity extraction fixes
7. Implement missing endpoints
8. Build frontend UI components

---

**Analysis Complete**: 2026-02-07
**Files Created**:
- INVENTORY_LENS_FRONTEND_BACKEND_INTEGRATION_ANALYSIS.md
- /scratchpad/test_api_payloads.py
- /scratchpad/test_1-5_response.json

**Status**: 🔴 CRITICAL ISSUES IDENTIFIED - Backend execution failure blocking all inventory functionality
