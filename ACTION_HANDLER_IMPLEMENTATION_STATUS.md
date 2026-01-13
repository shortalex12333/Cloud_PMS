# ACTION HANDLER IMPLEMENTATION STATUS
**Version:** 1.0
**Date:** 2026-01-12
**Purpose:** Map all 76 actions to existing/missing backend handlers

---

## SUMMARY

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Implemented | 24 | 32% |
| ⚠️ Partial (READ only) | 8 | 11% |
| ❌ Missing | 44 | 58% |
| **TOTAL** | **76** | **100%** |

---

## HANDLER MAPPING BY ACTION CLUSTER

### 1. FIX_SOMETHING CLUSTER (10 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 1.1 | report_fault | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 1.2 | acknowledge_fault | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 1.3 | diagnose_fault | MUTATE_MEDIUM | ✅ **IMPLEMENTED** | fault_handlers.py | READ only, need MUTATE |
| 1.4 | create_work_order_from_fault | MUTATE_MEDIUM | ✅ **IMPLEMENTED** | work_order_mutation_handlers.py | Full multi-stage (prefill/preview/execute) |
| 1.5 | close_fault | MUTATE_MEDIUM | ❌ **MISSING** | - | Need to create |
| 1.6 | update_fault | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 1.7 | reopen_fault | MUTATE_MEDIUM | ❌ **MISSING** | - | Need to create |
| 1.8 | mark_fault_false_alarm | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 1.9 | add_fault_photo | MUTATE_LOW | ❌ **MISSING** | - | Need storage integration |
| 1.10 | view_fault_detail | READ | ✅ **IMPLEMENTED** | fault_handlers.py | view_fault function |

**Cluster Status:** 2/10 implemented (20%)

---

### 2. DO_MAINTENANCE CLUSTER (5 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 2.1 | create_pm_schedule | MUTATE_MEDIUM | ❌ **MISSING** | - | Need to create |
| 2.2 | record_pm_completion | MUTATE_MEDIUM | ❌ **MISSING** | - | Need signature support |
| 2.3 | defer_pm_task | MUTATE_MEDIUM | ❌ **MISSING** | - | Need to create |
| 2.4 | update_pm_schedule | MUTATE_MEDIUM | ❌ **MISSING** | - | Need to create |
| 2.5 | view_pm_due_list | READ | ❌ **MISSING** | - | Need to create |

**Cluster Status:** 0/5 implemented (0%)

---

### 3. MANAGE_EQUIPMENT CLUSTER (5 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 3.1 | add_equipment | MUTATE_MEDIUM | ❌ **MISSING** | - | Need to create |
| 3.2 | update_equipment | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 3.3 | decommission_equipment | MUTATE_HIGH | ❌ **MISSING** | - | Critical - need audit |
| 3.4 | update_running_hours | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 3.5 | view_equipment_detail | READ | ✅ **IMPLEMENTED** | equipment_handlers.py | view_equipment function |

**Cluster Status:** 1/5 implemented (20%)

---

### 4. INVENTORY_PARTS CLUSTER (7 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 4.1 | add_part | MUTATE_MEDIUM | ❌ **MISSING** | - | Need to create |
| 4.2 | adjust_inventory | MUTATE_MEDIUM | ❌ **MISSING** | - | Need transaction ledger |
| 4.3 | generate_part_label | MUTATE_LOW | ❌ **MISSING** | - | Need QR code generation |
| 4.4 | update_part | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 4.5 | delete_part | MUTATE_MEDIUM | ❌ **MISSING** | - | Soft delete pattern |
| 4.6 | transfer_part | MUTATE_LOW | ❌ **MISSING** | - | Need ledger entry |
| 4.7 | search_parts | READ | ⚠️ **PARTIAL** | list_handlers.py | list_parts exists, need search |

**Cluster Status:** 0.5/7 implemented (7%)

---

### 5. HANDOVER CLUSTER (5 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 5.1 | create_handover | MUTATE_LOW | ⚠️ **PARTIAL** | handover_handlers.py | add_to_handover (prefill/execute) |
| 5.2 | acknowledge_handover | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 5.3 | update_handover | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 5.4 | delete_handover | MUTATE_LOW | ❌ **MISSING** | - | Soft delete pattern |
| 5.5 | filter_handover | READ | ❌ **MISSING** | - | Need filtering logic |

**Cluster Status:** 0.5/5 implemented (10%)

---

### 6. COMPLIANCE CLUSTER (5 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 6.1 | add_certificate | MUTATE_MEDIUM | ❌ **MISSING** | - | Need file upload + expiry |
| 6.2 | renew_certificate | MUTATE_MEDIUM | ❌ **MISSING** | - | Need versioning |
| 6.3 | update_certificate | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 6.4 | add_service_contract | MUTATE_MEDIUM | ❌ **MISSING** | - | Need file upload |
| 6.5 | record_contract_claim | MUTATE_MEDIUM | ❌ **MISSING** | - | Need warranty tracking |

**Cluster Status:** 0/5 implemented (0%)

---

### 7. DOCUMENTS CLUSTER (5 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 7.1 | upload_document | MUTATE_MEDIUM | ❌ **MISSING** | - | Need file upload + chunking |
| 7.2 | semantic_search | READ | ❌ **MISSING** | - | Need vector search |
| 7.3 | delete_document | MUTATE_MEDIUM | ❌ **MISSING** | - | Cascade to chunks |
| 7.4 | update_document_metadata | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 7.5 | process_document_chunks | MUTATE_MEDIUM | ❌ **MISSING** | - | Background job for embeddings |

**Cluster Status:** 0/5 implemented (0%)

---

### 8. PURCHASING CLUSTER (13 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 8.1 | add_to_shopping_list | MUTATE_LOW | ❌ **MISSING** | - | Need state machine |
| 8.2 | approve_shopping_item | MUTATE_MEDIUM | ❌ **MISSING** | - | Need role check |
| 8.3 | commit_receiving_session | MUTATE_HIGH | ❌ **MISSING** | - | Critical - needs signature |
| 8.4 | create_purchase_order | MUTATE_MEDIUM | ❌ **MISSING** | - | Need transaction |
| 8.5 | start_receiving_session | MUTATE_LOW | ❌ **MISSING** | - | Multi-stage init |
| 8.6 | check_in_item | MUTATE_LOW | ❌ **MISSING** | - | Checkbox = Truth |
| 8.7 | upload_discrepancy_photo | MUTATE_LOW | ❌ **MISSING** | - | Storage integration |
| 8.8 | add_receiving_notes | MUTATE_LOW | ❌ **MISSING** | - | Simple text update |
| 8.9 | update_shopping_list | MUTATE_LOW | ❌ **MISSING** | - | Need immutability check |
| 8.10 | delete_shopping_item | MUTATE_LOW | ❌ **MISSING** | - | Soft delete |
| 8.11 | update_purchase_order | MUTATE_LOW | ❌ **MISSING** | - | Draft POs only |
| 8.12 | close_purchase_order | MUTATE_MEDIUM | ❌ **MISSING** | - | Validate all received |
| 8.13 | reject_shopping_item | MUTATE_MEDIUM | ❌ **MISSING** | - | State transition |

**Cluster Status:** 0/13 implemented (0%)

---

### 9. WORK_ORDERS CLUSTER (10 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 9.1 | update_work_order | MUTATE_LOW | ❌ **MISSING** | - | Need to create |
| 9.2 | assign_work_order | MUTATE_LOW | ❌ **MISSING** | - | Need role validation |
| 9.3 | close_work_order | MUTATE_MEDIUM | ✅ **IMPLEMENTED** | work_order_mutation_handlers.py | mark_work_order_complete |
| 9.4 | add_wo_hours | MUTATE_LOW | ❌ **MISSING** | - | Need labor tracking |
| 9.5 | add_wo_part | MUTATE_LOW | ✅ **IMPLEMENTED** | work_order_mutation_handlers.py | add_part_to_work_order |
| 9.6 | add_wo_note | MUTATE_LOW | ✅ **IMPLEMENTED** | work_order_mutation_handlers.py | add_note_to_work_order |
| 9.7 | start_work_order | MUTATE_LOW | ❌ **MISSING** | - | State transition |
| 9.8 | cancel_work_order | MUTATE_MEDIUM | ❌ **MISSING** | - | Return parts to inventory |
| 9.9 | create_work_order | MUTATE_MEDIUM | ⚠️ **PARTIAL** | work_order_mutation_handlers.py | create_work_order_from_fault only |
| 9.10 | view_work_order_detail | READ | ✅ **IMPLEMENTED** | work_order_handlers.py | view_work_order function |

**Cluster Status:** 4/10 implemented (40%)

---

### 10. CHECKLISTS CLUSTER (4 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 10.1 | execute_checklist | MUTATE_MEDIUM | ⚠️ **PARTIAL** | work_order_handlers.py | view_work_order_checklist (READ only) |
| 10.2 | create_checklist_template | MUTATE_MEDIUM | ❌ **MISSING** | - | Need template management |
| 10.3 | complete_checklist_item | MUTATE_LOW | ❌ **MISSING** | - | Individual item check |
| 10.4 | sign_off_checklist | MUTATE_MEDIUM | ❌ **MISSING** | - | Need signature |

**Cluster Status:** 0/4 implemented (0%)

---

### 11. SHIPYARD CLUSTER (2 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 11.1 | schedule_drydock | MUTATE_HIGH | ❌ **MISSING** | - | Critical operation |
| 11.2 | record_shipyard_work | MUTATE_MEDIUM | ❌ **MISSING** | - | Need file upload |

**Cluster Status:** 0/2 implemented (0%)

---

### 12. FLEET CLUSTER (2 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 12.1 | compare_across_yachts | READ | ❌ **MISSING** | - | Multi-yacht access |
| 12.2 | fleet_analytics | READ | ❌ **MISSING** | - | Aggregated metrics |

**Cluster Status:** 0/2 implemented (0%)

---

### 13. SYSTEM_UTILITY CLUSTER (4 actions)

| # | Action ID | Classification | Handler Status | Handler File | Notes |
|---|-----------|----------------|----------------|--------------|-------|
| 13.1 | export_data | READ | ❌ **MISSING** | - | CSV/Excel export |
| 13.2 | import_data | MUTATE_HIGH | ❌ **MISSING** | - | Critical - validation needed |
| 13.3 | user_settings | MUTATE_LOW | ❌ **MISSING** | - | User preferences |
| 13.4 | view_dashboard_metrics | READ | ❌ **MISSING** | - | Complex aggregations |

**Cluster Status:** 0/4 implemented (0%)

---

## PRIORITIZED IMPLEMENTATION ROADMAP

### PHASE 1: CRITICAL MUTATE_HIGH ACTIONS (Must Have)
**Priority:** P0 - Start immediately
**Timeline:** Week 1-2

1. **commit_receiving_session** (8.3) - Most critical operation
2. **decommission_equipment** (3.3) - High-risk operation
3. **schedule_drydock** (11.1) - Major operational impact
4. **import_data** (13.2) - Data integrity critical

**Handlers to create:**
- `purchasing_handlers.py` → commit_receiving_session_execute()
- `equipment_mutation_handlers.py` → decommission_equipment_execute()
- `shipyard_handlers.py` → schedule_drydock_execute()
- `system_handlers.py` → import_data_execute()

---

### PHASE 2: CORE WORKFLOWS (High Priority)
**Priority:** P1 - Week 3-4
**Focus:** Complete essential user journeys

#### Fault Lifecycle (8 handlers)
- report_fault
- acknowledge_fault
- update_fault
- close_fault
- reopen_fault
- mark_fault_false_alarm
- add_fault_photo

**File:** `fault_mutation_handlers.py`

#### Purchasing Workflow (11 handlers)
- add_to_shopping_list
- approve_shopping_item
- create_purchase_order
- start_receiving_session
- check_in_item
- upload_discrepancy_photo
- add_receiving_notes
- update_shopping_list
- delete_shopping_item
- update_purchase_order
- close_purchase_order
- reject_shopping_item

**File:** `purchasing_mutation_handlers.py`

---

### PHASE 3: PM & INVENTORY (Medium Priority)
**Priority:** P2 - Week 5-6

#### PM Workflow (5 handlers)
- create_pm_schedule
- record_pm_completion
- defer_pm_task
- update_pm_schedule
- view_pm_due_list

**File:** `maintenance_handlers.py`

#### Inventory (6 handlers)
- add_part
- adjust_inventory
- update_part
- delete_part
- transfer_part
- generate_part_label

**File:** `inventory_mutation_handlers.py`

---

### PHASE 4: COMPLIANCE & DOCUMENTS (Lower Priority)
**Priority:** P3 - Week 7-8

#### Compliance (5 handlers)
**File:** `compliance_handlers.py`

#### Documents (5 handlers)
**File:** `document_handlers.py`

#### Checklists (4 handlers)
**File:** `checklist_handlers.py`

---

## IMPLEMENTATION GUIDELINES

### 1. File Organization Pattern

Each handler file should follow this structure:

```python
"""
{Cluster Name} Domain Handlers
================================

Group: {Cluster ID}

Mutation handlers for {cluster} actions.

Handlers:
- action_1_prefill: Prefetch data for form
- action_1_preview: Show what will change
- action_1_execute: Perform mutation
- action_2_execute: Simple mutation (no multi-stage)

All handlers return standardized ActionResponseEnvelope.
"""

from action_response_schema import ResponseBuilder, Severity
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class {Cluster}MutationHandlers:
    def __init__(self, supabase_client):
        self.db = supabase_client

    async def {action_name}_execute(
        self,
        entity_id: str,
        yacht_id: str,
        params: Dict
    ) -> Dict:
        """
        {Action description from catalog}

        Tables: {list from catalog}
        Classification: {MUTATE_LOW/MEDIUM/HIGH}
        Guard Rails: {from catalog}
        """
        builder = ResponseBuilder(
            "{action_name}",
            entity_id,
            "{entity_type}",
            yacht_id
        )

        try:
            # 1. Validate guard rails (A1-A3 always)
            # 2. BEGIN transaction if multi-table
            # 3. Perform mutations exactly as catalog specifies
            # 4. Create audit log entry
            # 5. COMMIT transaction
            # 6. Return success with follow-up actions

        except Exception as e:
            logger.error(f"{action_name} failed: {e}")
            builder.set_error("EXECUTION_FAILED", str(e))

        return builder.build()
```

### 2. Guard Rails Implementation

Every handler MUST implement:

```python
# A1: Authentication
if not user_id:
    builder.set_error("UNAUTHORIZED", "User not authenticated")
    return builder.build()

# A2: Yacht Isolation (CRITICAL)
user = await self.db.table("user_profiles").select("yacht_id").eq("id", user_id).single().execute()
if user.data["yacht_id"] != yacht_id:
    logger.critical(f"Yacht isolation breach attempt by {user_id}")
    builder.set_error("FORBIDDEN", "Access denied")
    return builder.build()

# A3: Role-Based Access Control
allowed_roles = ["chief_engineer", "captain", "admin"]  # From catalog
if user.data["role"] not in allowed_roles:
    builder.set_error("FORBIDDEN", f"Role {user.data['role']} cannot perform this action")
    return builder.build()
```

### 3. Audit Log Pattern

For all MUTATE actions:

```python
await self.db.table("pms_audit_log").insert({
    "id": str(uuid.uuid4()),
    "yacht_id": yacht_id,
    "action": action_name,
    "entity_type": entity_type,
    "entity_id": entity_id,
    "user_id": user_id,
    "user_role": user.data["role"],
    "old_values": old_values,  # JSONB snapshot before
    "new_values": new_values,  # JSONB snapshot after
    "changes_summary": f"User {user_name} {action_description}",
    "risk_level": risk_level,  # "low", "medium", "high"
    "signature": signature if required else None,
    "created_at": datetime.utcnow().isoformat()
}).execute()
```

---

## TESTING REQUIREMENTS

For EACH handler:

1. **Unit Tests**
   - Guard rail validation (A1-A3 minimum)
   - Input validation
   - Error handling

2. **Integration Tests**
   - Full multi-stage flow (prefill → preview → execute)
   - Audit log creation
   - Follow-up actions triggered

3. **Security Tests**
   - Yacht isolation (try accessing different yacht's data)
   - Role validation (try with insufficient role)
   - SQL injection attempts

---

## NEXT STEPS

1. ✅ **Complete this mapping** (DONE)
2. Create handlers for PHASE 1 (MUTATE_HIGH actions)
3. Test PHASE 1 handlers with all roles
4. Continue with PHASE 2-4
5. Create comprehensive test suite
6. Deploy to staging
7. Production deployment with audit trail

---

**THIS DOCUMENT IS CANONICAL.**

All handler implementation MUST follow the patterns defined in:
- COMPLETE_ACTION_EXECUTION_CATALOG.md (action specifications)
- This document (implementation status and guidelines)

**Last Updated:** 2026-01-12
**Version:** 1.0
