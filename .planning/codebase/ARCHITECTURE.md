# CelesteOS PMS - Architecture Overview

## System Pattern: Monorepo with Distributed Apps

CelesteOS is organized as a **monorepo** containing multiple applications that work in concert:

```
/apps
  /web       → Next.js frontend (TypeScript/React)
  /api       → FastAPI backend (Python)
  /test-automation  → Playwright E2E tests
```

**Database**: Supabase PostgreSQL (cloud-hosted, RLS-enabled)

---

## Architecture Layers

### Layer 1: Frontend (Next.js)

**Location**: `/apps/web`

- **Framework**: Next.js with App Router (React 18+)
- **Auth**: Supabase Auth (JWT-based with session management)
- **State Management**: React Context API + hooks
- **UI Components**: Custom Tailwind CSS components
- **API Communication**: Fetch-based with `/apps/web/src/app/api/*` proxy routes

**Data Flow to Backend**:
```
User Action in UI
  ↓
React Component state update
  ↓
/apps/web/src/app/api/v1/actions/execute endpoint (proxy)
  ↓
Forward to Python API /v1/actions/execute
```

### Layer 2: API (FastAPI Backend)

**Location**: `/apps/api`

Core FastAPI application serving all business logic:

- **Primary Endpoint**: `POST /v1/actions/execute` (Action Router)
- **Auth**: JWT validation + Supabase RLS policy enforcement
- **Database Client**: Supabase Python client (async)
- **Handler Pattern**: Domain-based handler modules

**Entry Points**:
- `router.py` - Main action dispatch router
- Multiple route files in `/routes/` for specialized endpoints
- Handlers in `/handlers/` for domain-specific logic

### Layer 3: Database (Supabase PostgreSQL)

**Architecture**:
- Multi-tenant schema with Row-Level Security (RLS)
- Yacht-scoped isolation via `tenant_id`
- Real-time capabilities via Supabase Realtime
- Secure data access through RLS policies

**Connection**:
```
Python: /apps/api/db/tenant_pg_gateway.py
  ↓
Supabase PostgreSQL
  ↓
RLS enforces tenant isolation
```

---

## Action Router Pattern: The Core Request Pipeline

The **Action Router** is the single entry point for all user-initiated mutations in CelesteOS.

### Request Flow

```
POST /v1/actions/execute
  {
    "action": "add_part_to_inventory",
    "context": {"yacht_id": "yacht-123", "user_id": "user-456"},
    "payload": {
      "part_name": "Alternator",
      "quantity": 5,
      "supplier_id": "supplier-789"
    }
  }
```

### 7-Stage Validation Pipeline

1. **JWT Validation** - Extract user identity and yacht context
   - Validator: `/apps/api/action_router/validators/jwt_validator.py`
   - Failure: 401 Unauthorized

2. **Action Registry Lookup** - Verify action exists and is deployed
   - Registry: `/apps/api/action_router/registry.py` (SINGLE SOURCE OF TRUTH)
   - Failure: 404 Not Found

3. **Yacht Isolation** - Validate user has access to requested yacht
   - Validator: `/apps/api/action_router/validators/rls_entity_validator.py`
   - Failure: 403 Forbidden

4. **Role Permission Check** - Verify user role can execute action
   - Validator: `/apps/api/action_router/validators/role_validator.py`
   - Failure: 403 Forbidden

5. **Required Fields Validation** - Check all mandatory fields present
   - Validator: `/apps/api/action_router/validators/field_validator.py`
   - Failure: 400 Bad Request

6. **Schema Validation** - Validate payload matches action schema
   - Validator: `/apps/api/action_router/validators/schema_validator.py`
   - Failure: 400 Bad Request

7. **Context Gating** - Check context-based preconditions
   - Example: Entity type must exist before mutation
   - Failure: 409 Conflict

### Handler Dispatch

After validation, request dispatches to appropriate handler:

```
Action: "create_equipment_record"
  ↓
Handler Type: INTERNAL (deprecated n8n, all handlers now internal)
  ↓
Dispatch to: /apps/api/handlers/equipment_handlers.py::create_equipment_handler()
  ↓
Execute business logic + database mutations
  ↓
Return result with execution_id, status, data
```

### Action Variant System

Actions are classified by mutation level (from registry):

- **READ** (0 mutations)
  - Safe to execute multiple times
  - Returns cached data when available
  - Examples: `list_work_orders`, `search_parts`

- **MUTATE** (1-n mutations, standard)
  - Standard create/update operations
  - Most actions in system
  - Examples: `update_part_stock`, `create_work_order`

- **SIGNED** (requires cryptographic signature)
  - Highest security level
  - Requires PIN + TOTP challenge + payload signature
  - Examples: `mark_work_order_complete` (in future)

---

## Lens System: 16 Domain-Specific Views

The **Lens System** provides multi-perspective views of yacht PMS data. Each lens represents a complete domain with:
- Entity definition
- State machine
- Action contracts
- Database schema
- RLS policies
- Search/indexing

### 16 Entity Lenses

| Lens | Purpose | Handler | Status |
|------|---------|---------|--------|
| **Certificate Lens** | Safety certificates, expiry tracking | `certificate_handlers.py` | ✓ Production |
| **Crew Lens** | Crew profiles, certifications, hours | `crew_handlers.py` | ✓ Production |
| **Equipment Lens** | Onboard equipment inventory | `equipment_handlers.py` | ✓ Production |
| **Document Lens** | PMS documents, specs, manuals | `document_handlers.py` | ✓ Production |
| **Fault Lens** | Equipment faults, status, lifecycle | `fault_handlers.py` + `fault_mutation_handlers.py` | ✓ Production |
| **Hours of Rest Lens** | Crew duty hours, rest calculations | `hours_of_rest_handlers.py` | ✓ Production |
| **Inventory Item Lens** | Spare parts, stock levels | `part_handlers.py` | ✓ Production |
| **Part Lens** | Part specifications, sourcing | `part_handlers.py` | ✓ Production |
| **Handover Lens** | Watch handover documentation | `handover_handlers.py` | ✓ Production |
| **Warranty Lens** | Equipment warranties, coverage | `warranty_handlers.py` | ✓ Production |
| **Work Order Lens** | Maintenance tasks | `work_order_handlers.py` + `work_order_mutation_handlers.py` | ✓ Production |
| **Situation Lens** | Ongoing situations, incidents | `situation_handlers.py` | ✓ Production |
| **Shopping List Lens** | Parts to procure | `shopping_list_handlers.py` | ✓ Production |
| **Receiving Lens** | Parts received from suppliers | `receiving_handlers.py` | ✓ Production |
| **Document Comment Lens** | Annotations on documents | `document_comment_handlers.py` | ✓ Production |
| **P1 Compliance Lens** | Regulatory compliance tracking | `p1_compliance_handlers.py` | ✓ Production |

### Lens Structure

Each lens has complete specification in `/docs/pipeline/entity_lenses/[lens_name]/`:

```
[lens_name]/
  v1/
    [lens]_v1_FINAL.md              # Version 1 specification
  v2/ or v3/
    [lens]_v[N]_PHASE_0_EXTRACTION_GATE.md
    [lens]_v[N]_PHASE_1_SCOPE.md
    [lens]_v[N]_PHASE_2_DB_TRUTH.md
    [lens]_v[N]_PHASE_3_ENTITY_GRAPH.md
    [lens]_v[N]_PHASE_4_ACTIONS.md
    [lens]_v[N]_PHASE_5_SCENARIOS.md
    [lens]_v[N]_PHASE_6_SQL_BACKEND.md
    [lens]_v[N]_PHASE_7_RLS_MATRIX.md
    [lens]_v[N]_PHASE_8_GAPS_MIGRATIONS.md
    [lens]_v[N]_FINAL.md
```

### Example: Fault Lens Phases

**Phase 0 - Extraction Gate**: What data do we extract from emails?
```
- Symptom description
- Affected equipment
- Severity assessment
- Affected crew members
```

**Phase 1 - Scope**: What are all valid states and transitions?
```
States: REPORTED → ACKNOWLEDGED → IN_PROGRESS → RESOLVED → CLOSED
```

**Phase 2 - DB Truth**: What tables and constraints?
```
faults (id, yaml_id, tenant_id, equipment_id, status, ...)
fault_actions (id, fault_id, action, actor_id, timestamp, ...)
```

**Phase 3 - Entity Graph**: Relationships to other lenses?
```
Fault → Equipment (many-to-one)
Fault → Work Order (one-to-many creation)
Fault → Crew (many-to-many affected)
```

**Phase 4 - Actions**: What mutations are allowed?
```
create_fault, update_fault_status, assign_fault,
add_fault_comment, schedule_fault_work_order
```

**Phase 5 - Scenarios**: Test cases and flows
```
Scenario: "Engine overheating"
  - Report fault from engine room
  - Assign to Chief Engineer
  - Create work order
  - Track resolution
```

**Phase 6 - SQL Backend**: Implement schema and functions
```
SQL migrations, indexes, stored procedures
```

**Phase 7 - RLS Matrix**: Who can see/modify what?
```
Engineer: see all faults, create, update own
HOD: see all, approve assignments
Captain: see critical only, update status
```

**Phase 8 - Gaps & Migrations**: Production deployment
```
Data migration scripts
Backfill operations
Validation checks
```

---

## Data Flow: User Intent → Micro-Action → Handler → Database

### Complete Request Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER INTENT (Next.js Frontend)                           │
├─────────────────────────────────────────────────────────────┤
│ User clicks "Report Equipment Fault"                         │
│ Form captures: equipment_id, symptom_text, severity         │
└────────────────┬──────────────────────────────────────────────┘
                 │
┌────────────────┴──────────────────────────────────────────────┐
│ 2. MICRO-ACTION EXTRACTION                                    │
├────────────────────────────────────────────────────────────────┤
│ Frontend calls /v1/actions/execute with:                      │
│   {                                                             │
│     "action": "create_fault",                                 │
│     "context": {                                              │
│       "yacht_id": "celeste-2024",                            │
│       "user_id": "user-456",                                 │
│       "role": "Engineer"                                     │
│     },                                                         │
│     "payload": {                                              │
│       "equipment_id": "engine-001",                          │
│       "symptom_text": "Overheating detected",               │
│       "severity": "HIGH"                                     │
│     }                                                          │
│   }                                                             │
└────────────────┬──────────────────────────────────────────────┘
                 │
┌────────────────┴──────────────────────────────────────────────┐
│ 3. ACTION ROUTER VALIDATION PIPELINE                         │
├────────────────────────────────────────────────────────────────┤
│ /v1/actions/execute endpoint:                                │
│                                                                │
│ ① JWT Validation                                             │
│    - Verify user token valid                                │
│    - Extract decoded claims (user_id, role, etc.)          │
│                                                                │
│ ② Action Registry Lookup                                     │
│    - Lookup "create_fault" in registry.py                   │
│    - Confirm action exists and is deployed                 │
│                                                                │
│ ③ Yacht Isolation                                            │
│    - Verify user has access to "celeste-2024"              │
│    - Check RLS entity validator                             │
│                                                                │
│ ④ Role Permission                                            │
│    - Confirm "Engineer" role allowed for "create_fault"     │
│    - Check against allowed_roles in registry                │
│                                                                │
│ ⑤ Required Fields                                            │
│    - Verify all required fields present in payload          │
│    - equipment_id: REQUIRED ✓                               │
│    - symptom_text: REQUIRED ✓                               │
│                                                                │
│ ⑥ Schema Validation                                          │
│    - Validate payload matches action schema                 │
│    - Type checking, format validation                       │
│                                                                │
│ ⑦ Context Gating                                             │
│    - Check preconditions (e.g., equipment exists)           │
│    - Query: SELECT id FROM equipment WHERE id = $1          │
│                                                                │
│ All validations pass → proceed to handler                    │
└────────────────┬──────────────────────────────────────────────┘
                 │
┌────────────────┴──────────────────────────────────────────────┐
│ 4. HANDLER DISPATCH & EXECUTION                              │
├────────────────────────────────────────────────────────────────┤
│ action_router/dispatchers/internal_dispatcher.py:             │
│                                                                │
│ dispatch("create_fault", context, payload)                   │
│   ↓                                                             │
│ Import handler: fault_handlers.py::create_fault_handler()    │
│   ↓                                                             │
│ Handler logic:                                                 │
│   1. Generate fault ID (uuid)                               │
│   2. Build fault record:                                     │
│      {                                                         │
│        "id": "fault-789",                                   │
│        "tenant_id": "celeste-2024",                        │
│        "equipment_id": "engine-001",                        │
│        "reported_by": "user-456",                          │
│        "status": "REPORTED",                               │
│        "severity": "HIGH",                                 │
│        "symptom_description": "Overheating detected",     │
│        "created_at": "2026-02-17T10:30:00Z",             │
│        "updated_at": "2026-02-17T10:30:00Z"              │
│      }                                                         │
│   3. Execute database insert:                               │
│      INSERT INTO faults (...) VALUES (...)                 │
│      RETURNING *                                             │
│   4. Fire dependent micro-actions (if any):                │
│      - notify_equipment_owner                              │
│      - index_fault_for_search                              │
│   5. Return execution_id and created fault                 │
└────────────────┬──────────────────────────────────────────────┘
                 │
┌────────────────┴──────────────────────────────────────────────┐
│ 5. DATABASE MUTATION (Supabase PostgreSQL)                   │
├────────────────────────────────────────────────────────────────┤
│ INSERT INTO faults (                                          │
│   id, tenant_id, equipment_id, reported_by, status,         │
│   severity, symptom_description, created_at, updated_at    │
│ ) VALUES (                                                    │
│   'fault-789', 'celeste-2024', 'engine-001', 'user-456',   │
│   'REPORTED', 'HIGH', 'Overheating detected',              │
│   '2026-02-17T10:30:00Z', '2026-02-17T10:30:00Z'         │
│ )                                                             │
│ RETURNING *;                                                  │
│                                                                │
│ RLS Policy Check:                                             │
│   - User role (Engineer) can CREATE in faults table?        │
│   - tenant_id must match user's yacht                       │
│   - Both checks pass → INSERT succeeds                      │
│                                                                │
│ Database triggers (if any):                                  │
│   - Update equipment.last_fault_date                        │
│   - Create audit log entry                                  │
│   - Publish Realtime event                                  │
└────────────────┬──────────────────────────────────────────────┘
                 │
┌────────────────┴──────────────────────────────────────────────┐
│ 6. RESPONSE & FRONTEND UPDATE                                │
├────────────────────────────────────────────────────────────────┤
│ Handler returns:                                              │
│   {                                                             │
│     "status": "success",                                     │
│     "action": "create_fault",                               │
│     "execution_id": "exec-123456",                          │
│     "result": {                                              │
│       "id": "fault-789",                                   │
│       "status": "REPORTED",                                │
│       "created_at": "2026-02-17T10:30:00Z"                │
│     }                                                         │
│   }                                                             │
│                                                                │
│ Action Router validation middleware logs:                     │
│   - execution_id: exec-123456                              │
│   - action: create_fault                                   │
│   - duration: 234ms                                         │
│   - user_id: user-456                                      │
│   - yacht_id: celeste-2024                                │
│                                                                │
│ Frontend receives response:                                   │
│   - Update local state with new fault                       │
│   - Show success toast                                      │
│   - Refresh fault list                                      │
│   - Navigate to fault detail view                           │
└────────────────────────────────────────────────────────────────┘
```

---

## Handler Architecture

### Handler Module Organization

**Location**: `/apps/api/handlers/`

Handlers are organized by domain lens, not by CRUD operation:

```
handlers/
  ├── fault_handlers.py               # Fault lens reads
  ├── fault_mutation_handlers.py      # Fault lens creates/updates
  ├── equipment_handlers.py            # Equipment lens
  ├── part_handlers.py                 # Part lens
  ├── work_order_handlers.py           # Work order reads
  ├── work_order_mutation_handlers.py  # Work order mutations
  ├── receiving_handlers.py            # Receiving lens
  ├── shopping_list_handlers.py        # Shopping list operations
  ├── hours_of_rest_handlers.py        # Hours of rest tracking
  ├── handover_handlers.py             # Watch handover
  ├── certificate_handlers.py          # Certificates
  ├── document_handlers.py             # PMS documents
  ├── document_comment_handlers.py     # Document annotations
  ├── warranty_handlers.py             # Warranty tracking
  ├── situation_handlers.py            # Situation tracking
  ├── list_handlers.py                 # List/search operations
  ├── p1_compliance_handlers.py        # Regulatory compliance
  ├── p1_purchasing_handlers.py        # Purchase orders
  ├── p2_mutation_light_handlers.py    # Lightweight mutations
  ├── p3_read_only_handlers.py         # Read-only operations
  ├── admin_handlers.py                # Admin operations
  ├── secure_admin_handlers.py         # Secure admin operations
  ├── secure_document_handlers.py      # Secure document access
  ├── context_navigation_handlers.py   # Context nav helpers
  └── db_client.py                     # Database access layer
```

### Handler Function Signature

```python
async def create_fault(
    payload: dict,
    context: dict,
    validation_result: ValidationResult
) -> dict:
    """
    Execute create_fault micro-action.

    Args:
        payload: {
            "equipment_id": str,
            "symptom_text": str,
            "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
        }
        context: {
            "yacht_id": str,
            "user_id": str,
            "role": str,
            "tenant_id": str
        }
        validation_result: Pre-validated fields

    Returns:
        {
            "id": "fault-xxx",
            "status": "REPORTED",
            "created_at": "...",
            ...
        }
    """
    # Implementation details
    pass
```

### Handler Responsibilities

1. **Business Logic** - Apply domain rules
2. **Data Transformation** - Convert payload to database format
3. **Database Mutations** - INSERT/UPDATE/DELETE operations
4. **State Validation** - Check state machine transitions
5. **Side Effects** - Trigger dependent actions, notifications
6. **Error Handling** - Raise appropriate exceptions
7. **Audit Logging** - Record all mutations

---

## Middleware Stack

### Authentication Middleware

**File**: `/apps/api/middleware/auth.py`

- Extracts JWT from Authorization header
- Validates token signature
- Decodes claims → user_id, role, yacht_id
- Passes context to downstream validators

### State Machine Middleware

**File**: `/apps/api/action_router/middleware/state_machine.py`

- Enforces state transitions in entity state machines
- Examples:
  - Faults: REPORTED → IN_PROGRESS (only HOD can transition)
  - Work Orders: OPEN → IN_PROGRESS → COMPLETED
  - Certificates: VALID → EXPIRING_SOON → EXPIRED

### Validation Middleware

**File**: `/apps/api/action_router/middleware/validation_middleware.py`

- Runs all 7-stage validation pipeline
- Returns ValidationResult object
- Passes to handler if all checks pass

---

## Summary: Three-Tier Data Flow

```
FRONTEND (Next.js)
    ↓
    └─→ User forms → /v1/actions/execute (proxy)

API GATEWAY (FastAPI)
    ↓
    └─→ Action Router (validators, dispatchers)

BACKEND HANDLERS (Domain Logic)
    ↓
    └─→ Handler modules (business logic)

DATABASE (Supabase PostgreSQL)
    ↓
    └─→ RLS-protected multi-tenant schema
```

**Key Insight**: The Action Router is the **gatekeeper** - all user-initiated mutations flow through it, enforcing consistent validation and authorization across all 16 domain lenses.
