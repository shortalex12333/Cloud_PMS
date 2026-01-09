# Cloud_PMS Architecture Analysis

**Date:** 2026-01-08
**Branch:** universal_v1
**Status:** Pre-Implementation Analysis

---

## Executive Summary

This document maps the current Cloud_PMS architecture and identifies conflicts with the new P0 action specifications from `/action_specifications/`.

**Key Finding:** The existing codebase has behavioral tracking systems (confidence scoring, evidence flags, nudge budgets) that **VIOLATE** the new design philosophy which explicitly forbids:
- Confidence scores (0-100)
- Behavioral tracking (time-on-page, scroll depth, copied text)
- ML predictions
- Proactive nudges

**Action Required:** Refactor situation engine and action gating to use **entity-based context** with **query intent parsing** and **simple data mapping** instead.

---

## Current Architecture

### 1. Backend Structure (`/apps/api/`)

#### 1.1 Action Router (`/apps/api/action_router/`)

**Purpose:** Single endpoint for all user-initiated mutations.

**Endpoint:** `POST /v1/actions/execute`

**Flow:**
```
1. Validate JWT (extract user context)
2. Validate action exists in registry
3. Validate yacht isolation (RLS enforcement)
4. Validate role permissions
5. Validate required fields
6. Validate schema (if defined)
7. Dispatch to handler (INTERNAL or N8N)
8. Log execution
9. Return result
```

**Key Files:**
- `router.py` - Main FastAPI router with execute_action endpoint
- `registry.py` - ACTION_REGISTRY with ActionDefinition (action_id, label, endpoint, handler_type, allowed_roles, required_fields, schema_file)
- `validators/` - JWT, yacht, role, field, schema validators
- `dispatchers/` - internal_dispatcher (local handlers), n8n_dispatcher (webhooks)

**Request Model:**
```python
class ActionRequest(BaseModel):
    action: str
    context: Dict[str, Any]  # yacht_id, entity_id, etc.
    payload: Dict[str, Any]  # action-specific params
```

**Response Model:**
```python
class ActionResponse(BaseModel):
    status: str  # "success" or "error"
    action: str
    result: Dict[str, Any] = None
    error_code: str = None
    message: str = None
```

#### 1.2 Action Registry (`/apps/api/actions/action_registry.py`)

**Purpose:** Central registry for all microactions with READ/MUTATE classification.

**Architecture:**
- 67+ actions across 10+ domains
- READ actions: Can be primary, no signature required
- MUTATE actions: Dropdown only, require signature + preview_diff + audit

**Domains:**
- inventory (view, edit, reorder)
- manual (view sections, related docs)
- equipment (view, history, parts, faults, manual)
- work_orders (view, create, update, complete, assign, add notes/photos/parts)
- fault (view, diagnose, report, history, suggest parts)
- handover (add items, edit sections, export)
- hours_of_rest (view, update, export, compliance)
- purchasing (create, approve, track, upload invoice)
- checklists (view, mark complete, add notes/photos)
- shipyard (worklist, tasks, progress, tag for survey)
- fleet (summary, open vessel, export)
- predictive (insights, smart summary)
- mobile (view attachments, upload photo, record voice note)

**Action Definition:**
```python
@dataclass
class Action:
    action_id: str
    label: str
    variant: ActionVariant  # READ or MUTATE
    domain: str
    ui: ActionUI  # primary, dropdown_only, icon
    execution: ActionExecution  # handler, timeout, requires_entity_id
    mutation: Optional[ActionMutation]  # requires_signature, preview_diff, reversible
    audit: ActionAudit  # level (NONE, BASIC, FULL), retention_days
    entity_types: List[str]  # which entities this action applies to
```

**Validation Rules:**
- READ actions cannot have mutation config
- MUTATE actions must have mutation config
- Primary actions MUST be READ
- MUTATE actions should be dropdown_only

#### 1.3 Action Gating (`/apps/api/actions/action_gating.py`)

⚠️ **CONFLICT WITH NEW SPECS**

**Current Implementation:**
- Uses confidence-based gating (0-1 score)
- ExecutionClass: AUTO, SUGGEST, CONFIRM
- GATED_ACTIONS: Always require confirmation (compliance, financial, destructive)
- STATE_CHANGING_ACTIONS: Require confirmation if confidence < 0.85
- READ_ONLY_ACTIONS: Can auto-execute if confidence >= 0.85

**Code:**
```python
def get_execution_class(action: str, confidence: float = 1.0) -> ExecutionClass:
    if action in GATED_ACTIONS:
        return ExecutionClass.CONFIRM

    if action in READ_ONLY_ACTIONS:
        if confidence >= AUTO_EXECUTE_THRESHOLD:  # 0.85
            return ExecutionClass.AUTO
        else:
            return ExecutionClass.SUGGEST

    if action in STATE_CHANGING_ACTIONS:
        if confidence >= AUTO_EXECUTE_THRESHOLD:
            return ExecutionClass.SUGGEST
        else:
            return ExecutionClass.CONFIRM

    return ExecutionClass.CONFIRM
```

**Problem:** This violates the new philosophy:
- NO confidence scores
- NO auto-execution based on behavioral tracking
- Every mutation requires explicit user control

**New Approach (from specs):**
- Query intent parsing (explicit queries only)
- Entity-based actions (actions adjacent to entities)
- Simple data mapping (deterministic pre-fill, no ML)
- Explicit user control (trigger → form → preview → sign → commit)

#### 1.4 Handlers (`/apps/api/handlers/`)

**Purpose:** Domain-specific READ action handlers.

**Files:**
- `work_order_handlers.py` - view_work_order, view_work_order_history, view_work_order_checklist, open_work_order
- `fault_handlers.py` - view_fault, diagnose_fault, run_diagnostic, view_fault_history, suggest_parts
- `equipment_handlers.py` - (assumed to exist)
- `inventory_handlers.py` - (assumed to exist)
- `list_handlers.py` - (assumed to exist)

**Handler Pattern:**
```python
class WorkOrderHandlers:
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client)

    async def view_work_order(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        builder = ResponseBuilder("view_work_order", entity_id, "work_order", yacht_id)

        # Query database
        # Normalize data
        # Add computed fields
        # Add attached files
        # Add available actions

        return builder.build()
```

**Response Structure:**
```python
{
    "status": "success",
    "action": "view_work_order",
    "entity_id": "uuid",
    "entity_type": "work_order",
    "yacht_id": "uuid",
    "data": {...},  # Entity data
    "files": [...],  # Attached files with signed URLs
    "available_actions": [...],  # Actions user can take
    "pagination": {...},  # If applicable
    "timestamp": "2026-01-08T..."
}
```

#### 1.5 Microaction Service (`/apps/api/microaction_service.py`)

⚠️ **CONFLICT WITH NEW SPECS**

**Purpose:** FastAPI service for microaction extraction and intent parsing.

**Components:**
- MicroActionExtractor - Pattern-based action detection
- IntentParser - Semantic query understanding
- SituationEngine - Situation detection (v1)
- GraphRAG services - Population and query

**Security:**
- JWT validation (Supabase)
- Yacht signature verification (optional)

**Conflict:**
```python
def get_action_chips(query: str, primary_action: str, confidence: float) -> Dict:
    return {
        'primary': {
            'action': primary_action,
            'confidence': round(confidence, 2),  # ⚠️ CONFIDENCE SCORE
            'label': primary_action.replace('_', ' ').title()
        },
        'execution_class': 'auto' if confidence >= 0.8 else 'suggest',  # ⚠️ AUTO-EXECUTION
        'suggestion_worthy': confidence < 0.8
    }
```

**Problem:** Uses confidence scoring for auto-execution decisions - violates new specs.

---

### 2. Frontend Structure (`/apps/web/src/`)

#### 2.1 Type Definitions (`/apps/web/src/types/`)

##### `situation.ts`

⚠️ **MAJOR CONFLICT WITH NEW SPECS**

**Current Implementation:**
```typescript
export type SituationState =
  | 'IDLE'      // No active situation
  | 'CANDIDATE' // Result selected but not opened
  | 'ACTIVE'    // Entity opened
  | 'COOLDOWN'  // Action completed
  | 'RESOLVED'; // Closed

export interface SituationEvidence {
  opened_manual: boolean;
  viewed_history: boolean;
  mutation_prepared: boolean;
  mutation_committed: boolean;
  handover_added: boolean;
  repeated_queries_count: number;  // ⚠️ BEHAVIORAL TRACKING
}

export interface SituationContext {
  state: SituationState;
  confidence_points: number;  // ⚠️ CONFIDENCE SCORE
  phase: SituationPhase;
  evidence: SituationEvidence;  // ⚠️ EVIDENCE TRACKING
  nudge_last_shown_at?: number;  // ⚠️ NUDGE TRACKING
  nudge_dismissed: Record<string, boolean>;  // ⚠️ NUDGE TRACKING
  nudge_budget_remaining: number;  // ⚠️ NUDGE BUDGET
  // ... plus entity context
}
```

**Problem:** This is a full behavioral surveillance system - explicitly forbidden by new specs.

**What to Keep:**
- Entity context (yacht_id, user_id, role, primary_entity_type, primary_entity_id, domain)
- State (simplified)
- Session tracking (session_id, created_at, last_activity_at)

**What to Remove:**
- confidence_points
- evidence (all tracking)
- phase (inferred from evidence)
- nudge_* (all nudging)

##### `actions.ts`

**Current Implementation:**
- 67 MicroAction types
- Complete ACTION_REGISTRY with metadata
- Side effect types (read_only, optimistic, mutation_light, mutation_heavy)
- Purpose clusters (fix_something, do_maintenance, inventory_parts, handover_communication, etc.)

**This is GOOD** - matches new specs for action registry.

---

### 3. Database Schema (`/database/migrations/`)

#### `01_core_tables_v2_secure.sql`

**Current Tables:**
- `yachts` - Vessel data
- `user_profiles` - User data linked to auth.users
- `user_roles` - Role assignments (chief_engineer, eto, captain, manager, vendor, crew, deck, interior)
- `api_tokens` - Device tokens, API keys
- `yacht_signatures` - Yacht install signatures

**Helper Functions:**
- `get_user_role(p_user_id, p_yacht_id)` - Get active role
- `is_hod(p_user_id, p_yacht_id)` - Check if HOD-level role

**RLS Policies:**
- Users can view/update own profile
- Users can view own roles
- Only HODs can manage roles
- Users can view/manage own tokens
- Users can view assigned yacht

**Missing Tables (needed for P0 actions):**
- `work_orders` - Work order records
- `work_order_notes` - Notes attached to WOs
- `work_order_parts` - Parts assigned to WOs
- `faults` - Fault records
- `parts` - Parts/inventory items
- `part_usage` - Part usage log
- `handover` - Handover entries
- `documents` - Document metadata
- `attachments` - File attachments (photos, docs)
- `audit_log` - Audit trail for all mutations

---

## Conflicts Summary

### 🔴 Critical Conflicts

1. **`/apps/api/actions/action_gating.py`**
   - Uses confidence scoring (0-1)
   - Auto-execution based on confidence thresholds
   - **Violates:** "No confidence scores", "Explicit control always"

2. **`/apps/web/src/types/situation.ts`**
   - Full behavioral tracking (evidence flags, confidence_points, nudge_budget)
   - Inferred phase from evidence
   - **Violates:** "No behavioral tracking", "No proactive nudges"

3. **`/apps/api/microaction_service.py`**
   - Returns confidence scores in action chips
   - Auto-execution logic based on confidence
   - **Violates:** "No ML predictions", "No confidence intervals"

### 🟡 Moderate Conflicts

4. **`/apps/api/situation_engine.py`**
   - Pattern detection (RECURRENT_SYMPTOM, HIGH_RISK_EQUIPMENT)
   - Palliative keyword detection
   - **May violate:** "Simple data mapping" (but might be OK if deterministic)

### ✅ Good (Aligned with Specs)

- Action registry structure (READ/MUTATE classification)
- Handler pattern (ResponseBuilder, entity-based)
- Database schema (RLS, roles, audit)
- Frontend action types (67 microactions)

---

## Refactoring Plan

### Phase 1: Remove Behavioral Tracking

1. **Refactor `situation.ts`:**
   - Remove: confidence_points, evidence, phase, nudge_*
   - Keep: entity context, state (simplified), session tracking
   - Add: query_intent (from intent parser)

2. **Refactor `action_gating.py`:**
   - Remove: confidence thresholds, ExecutionClass.AUTO
   - Replace with: entity-type-based gating (actions allowed per entity type)
   - Rule: Actions appear only in entity detail views, never in search

3. **Refactor `microaction_service.py`:**
   - Remove: confidence from get_action_chips
   - Replace with: direct action buttons (no suggestions, no auto-execution)

### Phase 2: Implement Entity-Based Action Gating

1. **Create `action_policy.py`:**
   - Define which actions are allowed per entity type
   - Define which actions require signature
   - Define entry conditions (fault page, equipment page, work order page)

2. **Update handlers:**
   - Add `get_available_actions(entity_type, entity_state)` method
   - Return only actions that make sense for current entity state
   - Example: "Create Work Order" only appears on fault/equipment pages, not in search

### Phase 3: Implement Simple Pre-fill Logic

1. **Create `prefill_logic.py`:**
   - Deterministic mapping (no ML)
   - Example: `title = f"{location} - {equipment_name} - {fault_code}"`
   - Example: `priority = fault.severity if exists else "normal"`

2. **Update action handlers:**
   - Add pre-fill endpoints that return form data
   - Example: `GET /v1/actions/create_work_order_from_fault/prefill?fault_id=xxx`

### Phase 4: Add Database Tables for P0 Actions

1. **Migration `02_p0_actions_tables.sql`:**
   - work_orders
   - work_order_notes
   - work_order_parts
   - faults
   - parts
   - part_usage
   - handover
   - documents
   - attachments
   - audit_log

---

## Next Steps

1. ✅ Read and understand all 8 P0 action specifications
2. ✅ Map current codebase structure
3. 🔄 Document architecture conflicts (THIS DOCUMENT)
4. ⏳ Define canonical JSON contracts for 8 P0 actions
5. ⏳ Design new situation state system (without confidence/behavioral tracking)
6. ⏳ Design new action gating system (entity-based, no confidence)
7. ⏳ Implement database migrations for P0 actions
8. ⏳ Implement each P0 action end-to-end

---

## Open Questions

1. **Situation Engine:** Should we keep pattern detection (RECURRENT_SYMPTOM) or remove it entirely? (Spec says "simple data mapping" but pattern matching might be OK if deterministic)

2. **Intent Parser:** How do we classify queries as "action intent" vs "information intent" without confidence scores? (Answer: Use explicit keywords like "create", "add", "mark" - binary classification)

3. **Search Results:** Should search results show entity previews with NO actions, and clicking opens entity detail page which THEN shows actions? (Answer from specs: YES - "Search = previews only, Actions only in entity detail views")

---

**END OF ARCHITECTURE ANALYSIS**
