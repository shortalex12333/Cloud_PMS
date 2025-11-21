# CelesteOS - Unified Architecture Documentation

**Version:** 2.0 (Post-Merge)
**Date:** 2025-11-21
**Status:** Production-Ready Architecture

---

## Executive Summary

CelesteOS is a cloud-first AI-driven engineering intelligence platform for superyachts. This document represents the **unified architecture** resulting from the merge of two development streams:

- **Branch 1 (consolidated-merge):** Python backend implementation, action router, authentication, and integration layer
- **Branch 2 (read-repo-files):** Comprehensive micro-action specifications, routing rules, and view patterns

This architecture supports **67 micro-actions** across **12 card types**, orchestrated through a unified router → workflow → frontend contract.

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Micro-Action Framework](#2-micro-action-framework)
3. [Routing & Workflow Layer](#3-routing--workflow-layer)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Backend Architecture](#5-backend-architecture)
6. [Database Schema](#6-database-schema)
7. [Security & Isolation](#7-security--isolation)
8. [API Contracts](#8-api-contracts)
9. [Implementation Phases](#9-implementation-phases)
10. [File Organization](#10-file-organization)

---

## 1. System Architecture

### 1.1 Cloud-First Philosophy

**All computation occurs in the cloud.** The vessel's NAS acts only as a gateway for document ingestion.

```
┌─────────────────────────────────────────────────────────────┐
│  VESSEL (NAS + Local Agent)                                 │
│  - Read-only SMB access to documentation                    │
│  - SHA256 verification of documents                         │
│  - Upload to cloud storage                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓ (TLS 1.3)
┌─────────────────────────────────────────────────────────────┐
│  CLOUD INFRASTRUCTURE                                        │
│                                                              │
│  ┌────────────────┐    ┌────────────────┐                  │
│  │ Object Storage │    │ Vector DB      │                  │
│  │ (S3/MinIO)     │───>│ (pgvector)     │                  │
│  └────────────────┘    └────────────────┘                  │
│           │                     │                            │
│           ↓                     ↓                            │
│  ┌─────────────────────────────────────┐                   │
│  │ Search Engine + RAG                  │                   │
│  │ - Entity extraction                  │                   │
│  │ - Graph traversal                    │                   │
│  │ - Semantic search                    │                   │
│  └─────────────────────────────────────┘                   │
│           │                                                  │
│           ↓                                                  │
│  ┌─────────────────────────────────────┐                   │
│  │ Action Router (Python)               │                   │
│  │ - JWT validation                     │                   │
│  │ - Role-based access control          │                   │
│  │ - Yacht isolation enforcement        │                   │
│  │ - Dispatchers: n8n, internal         │                   │
│  └─────────────────────────────────────┘                   │
│           │                                                  │
│           ↓                                                  │
│  ┌─────────────────────────────────────┐                   │
│  │ n8n Workflow Engine (67 workflows)   │                   │
│  │ - Action execution                   │                   │
│  │ - Database mutations                 │                   │
│  │ - Audit logging                      │                   │
│  └─────────────────────────────────────┘                   │
│           │                                                  │
│           ↓                                                  │
│  ┌─────────────────────────────────────┐                   │
│  │ Supabase Database (PostgreSQL + RLS) │                   │
│  │ - Per-yacht isolation                │                   │
│  │ - Audit trail                        │                   │
│  └─────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js 15 + React 19)                           │
│  - Search interface                                         │
│  - Dynamic card rendering                                   │
│  - Micro-action buttons                                     │
│  - Dashboard widgets                                        │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Per-Yacht Isolation Model

Each yacht receives:
- **Dedicated S3 bucket** for document storage
- **Unique yacht_signature** (cryptographic identity)
- **Row-Level Security (RLS)** in database
- **Separate encryption keys**
- **No cross-tenant access** (enforced at multiple layers)

### 1.3 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 15, React 19, TypeScript | User interface, search, actions |
| **Backend Router** | Python 3.11, FastAPI | Action routing, validation |
| **Workflow Engine** | n8n (self-hosted) | Action execution, orchestration |
| **Database** | Supabase (PostgreSQL + pgvector) | Data storage, vector search |
| **Authentication** | Supabase Auth, JWT | User authentication |
| **Storage** | S3/MinIO | Document storage (per yacht) |
| **Search** | RAG + Graph traversal | Semantic search, entity extraction |
| **Deployment** | Vercel (frontend), Hetzner VPS (backend) | Hosting |

---

## 2. Micro-Action Framework

### 2.1 What is a Micro-Action?

A **micro-action** is an atomic, user-initiated operation that:
- Has a **specific intent** (view, create, update, delete, export)
- Operates on a **specific entity** (work order, fault, part, equipment)
- Produces a **predictable side effect** (read-only, mutation-light, mutation-heavy)
- Can be **context-aware** (pre-filled with search context)

### 2.2 The 67 Canonical Micro-Actions

**Organized into 7 Purpose Clusters:**

| Cluster | Count | Description | Examples |
|---------|-------|-------------|----------|
| **fix_something** | 8 | Diagnose and resolve faults | `diagnose_fault`, `create_work_order_from_fault`, `suggest_parts` |
| **do_maintenance** | 16 | Execute planned maintenance | `create_work_order`, `mark_work_order_complete`, `assign_work_order` |
| **manage_equipment** | 8 | Understand equipment state | `view_equipment_details`, `view_equipment_history`, `edit_equipment_details` |
| **control_inventory** | 8 | Manage spare parts | `view_part_stock`, `order_part`, `log_part_usage` |
| **communicate_status** | 11 | Handovers and reporting | `add_to_handover`, `export_handover`, `regenerate_handover_summary` |
| **comply_audit** | 5 | Regulatory compliance | `view_hours_of_rest`, `update_hours_of_rest`, `export_hours_of_rest` |
| **procure_suppliers** | 9 | Purchasing and procurement | `create_purchase_request`, `approve_purchase`, `edit_invoice_amount` |

**Complete Registry:** See `docs/micro-actions/MICRO_ACTION_REGISTRY.md`

### 2.3 Side Effect Classification

| Type | Count | Behavior | Examples |
|------|-------|----------|----------|
| **read_only** | 29 (43%) | No database changes, safe to retry | `view_equipment_details`, `view_part_stock` |
| **mutation_light** | 23 (34%) | Minor edits (notes, photos) | `add_work_order_note`, `add_fault_photo` |
| **mutation_heavy** | 15 (22%) | Creates/updates/deletes records, requires confirmation | `create_work_order`, `edit_invoice_amount`, `delete_item` |

### 2.4 The 12 Card Types

Actions are offered based on **card type** (the entity being displayed):

| Card Type | Primary Use Case | Key Actions |
|-----------|------------------|-------------|
| `fault` | Fault/alarm display | `diagnose_fault`, `create_work_order_from_fault`, `suggest_parts` |
| `work_order` | Maintenance tasks | `mark_work_order_complete`, `assign_work_order`, `edit_work_order_details` |
| `equipment` | Equipment profiles | `view_equipment_details`, `view_equipment_history`, `create_work_order` |
| `part` | Inventory items | `view_part_stock`, `order_part`, `view_part_location` |
| `handover` | Knowledge transfer | `edit_handover_section`, `export_handover`, `regenerate_handover_summary` |
| `document` | Manuals, SOPs | `view_document`, `view_document_section`, `add_document_to_handover` |
| `hor_table` | Hours of rest compliance | `view_hours_of_rest`, `update_hours_of_rest`, `export_hours_of_rest` |
| `purchase` | Purchase orders | `create_purchase_request`, `approve_purchase`, `edit_invoice_amount` |
| `checklist` | Operational checklists | `view_checklist`, `mark_checklist_item_complete` |
| `worklist` | Shipyard snag lists | `add_worklist_task`, `tag_for_survey`, `export_worklist` |
| `fleet_summary` | Multi-vessel overview | `view_fleet_summary`, `open_vessel` |
| `smart_summary` | AI-generated briefing | `view_smart_summary`, `add_to_handover`, `request_predictive_insight` |

**Complete Mapping:** See `docs/micro-actions/ACTION_OFFERING_MAP.md`

### 2.5 The 14 View Patterns (READ Dimension)

Actions define WHAT users DO, but **view patterns** define HOW users SEE data.

| Pattern | Intent | Example Query | Priority |
|---------|--------|---------------|----------|
| `filter_by_location` | Items in specific location | "parts in Box 3" | HIGH |
| `filter_by_status` | Items in specific state | "overdue tasks" | HIGH |
| `filter_by_time` | Items in time range | "faults this week" | HIGH |
| `filter_by_equipment` | Items for equipment | "WOs for Generator 1" | HIGH |
| `filter_by_person` | Items for person | "my tasks" | MEDIUM |
| `group_by` | Items organized | "WOs grouped by equipment" | MEDIUM |
| `search_results` | Find by keyword | "search coolant" | HIGH |
| `dashboard` | Overview widgets | "engineering dashboard" | MEDIUM |
| `compare` | Compare entities/periods | "this month vs last" | LOW |
| `hierarchy` | Tree structure | "equipment tree" | LOW |

**Complete Analysis:** See `docs/micro-actions/VIEWING_PATTERNS_ANALYSIS.md`

---

## 3. Routing & Workflow Layer

### 3.1 The Unified Router Contract

**All micro-actions follow the same JSON envelope:**

#### Request Format
```json
{
  "action_name": "create_work_order",
  "user_id": "uuid-456",
  "yacht_id": "uuid-789",
  "context": {
    "equipment_id": "uuid-123",
    "title": "Service main engine coolant",
    "priority": "high",
    "due_date": "2025-11-25"
  },
  "timestamp": "2025-11-21T14:30:00Z"
}
```

#### Response Format
```json
{
  "success": true,
  "message": "Work order created successfully",
  "data": {
    "work_order_id": "uuid-new",
    "created_at": "2025-11-21T14:30:15Z"
  },
  "error": null
}
```

### 3.2 Action Router (Python Backend)

**Location:** `backend/src/action_router/`

**Key Components:**

| Component | Purpose | File |
|-----------|---------|------|
| **Router** | Main entry point, coordinates validation & dispatch | `router.py` |
| **Registry** | Maps action_name → handler | `registry.py` |
| **Validators** | JWT, role, yacht, schema validation | `validators/` |
| **Dispatchers** | n8n webhook, internal execution | `dispatchers/` |

**Validation Pipeline:**
```
Request → JWT Validation → Role Check → Yacht Isolation → Schema Validation → Dispatch
```

**Validators:**
- `jwt_validator.py`: Verifies JWT signature, expiry
- `role_validator.py`: Checks user role permissions
- `yacht_validator.py`: Enforces yacht isolation
- `schema_validator.py`: Validates action payload against JSON schema
- `field_validator.py`: Custom field validations

### 3.3 n8n Workflow Architecture

**Total Workflows:** 67 (one per micro-action)

**Workflow Template:**
```json
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "webhook",
      "webhookPath": "/api/actions/create_work_order"
    },
    {
      "name": "Validate JWT",
      "type": "function",
      "code": "validate_jwt(request.headers.authorization)"
    },
    {
      "name": "Check Role",
      "type": "if",
      "condition": "user.role in ['chief_engineer', 'captain', 'manager']"
    },
    {
      "name": "Execute Database Mutation",
      "type": "postgres",
      "query": "INSERT INTO work_orders ..."
    },
    {
      "name": "Create Audit Log",
      "type": "postgres",
      "query": "INSERT INTO audit_log ..."
    },
    {
      "name": "Send Notification",
      "type": "email",
      "condition": "priority === 'critical'"
    }
  ]
}
```

**Audit-Sensitive Actions:**
- `edit_invoice_amount`: Requires reason, logs old/new value, notifies if >$500
- `approve_purchase`: Requires HOD role, creates approval audit trail
- `update_hours_of_rest`: Logs all changes for MLC compliance

**See:** `docs/ACTION_ROUTER_IMPLEMENTATION.md`

### 3.4 Intent Detection & Action Offering Rules

**The Decision Tree:**

```
User Query
  ↓
Intent Classification (view/create/update/export/delete)
  ↓
Entity Detection (equipment/fault/part/WO/document)
  ↓
Context Determination (at sea/port/shipyard/guest trip)
  ↓
Role Validation (crew/HOD/management)
  ↓
ACTION OFFERING RULES Applied
  ↓
Card Type Generated
  ↓
Actions Filtered & Offered
  ↓
Frontend Renders Card + Action Buttons
```

**Example:**
```
Query: "E047 overheat on main engine"
  → Intent: diagnose_fault (inferred from fault code)
  → Entity: equipment_id (extracted), fault_code: "E047"
  → Card Type: fault
  → Actions Offered: diagnose_fault, show_manual_section, create_work_order_from_fault, suggest_parts
```

**Complete Rules:** See `docs/micro-actions/ACTION_OFFERING_RULES.md`

---

## 4. Frontend Architecture

### 4.1 Technology Stack

```
Framework:   Next.js 15.0.0 (App Router, RSC)
UI Library:  React 19.0.0
Language:    TypeScript 5.3.0
Styling:     Tailwind CSS 3.4.0
Icons:       Lucide React
Database:    Supabase (PostgreSQL + Auth)
Auth:        Supabase Auth (JWT)
State:       React hooks + Context API
Testing:     Jest + React Testing Library
```

### 4.2 Directory Structure

```
frontend/
├── src/
│   ├── app/                      # Next.js app router pages
│   │   ├── layout.tsx           # Root layout
│   │   ├── page.tsx             # Home (redirects to /search)
│   │   ├── search/page.tsx      # Main search interface
│   │   ├── dashboard/page.tsx   # Dashboard with widgets
│   │   ├── login/page.tsx       # Authentication
│   │   ├── settings/page.tsx    # Settings & integrations
│   │   └── integrations/        # OAuth callbacks
│   │
│   ├── components/
│   │   ├── SearchBar.tsx        # Universal search input
│   │   ├── ResultCard.tsx       # Dynamic card renderer
│   │   ├── MicroActions.tsx     # Action button system
│   │   ├── DashboardLayout.tsx  # Layout wrapper
│   │   ├── SettingsModal.tsx    # Settings panel
│   │   ├── withAuth.tsx         # Auth HOC
│   │   └── DashboardWidgets/
│   │       ├── WorkOrderStatus.tsx
│   │       ├── EquipmentOverview.tsx
│   │       ├── InventoryStatus.tsx
│   │       └── PredictiveOverview.tsx
│   │
│   ├── contexts/
│   │   └── AuthContext.tsx      # Authentication context
│   │
│   ├── hooks/
│   │   ├── useAuth.ts           # Auth hook
│   │   └── useSearch.ts         # Search hook
│   │
│   ├── lib/
│   │   ├── api.ts               # Typed API client (modular)
│   │   ├── apiClient.ts         # Base API client
│   │   ├── actionClient.ts      # Action execution client
│   │   ├── auth.ts              # Auth utilities
│   │   ├── supabase.ts          # Supabase client
│   │   └── utils.ts             # Utilities
│   │
│   ├── types/
│   │   ├── actions.ts           # 67 action type definitions (996 lines)
│   │   ├── search.ts            # Search types
│   │   ├── dashboard.ts         # Dashboard types
│   │   └── index.ts             # Shared types
│   │
│   └── __tests__/
│       └── api.test.ts          # API tests
│
├── package.json
├── tsconfig.json
└── tailwind.config.ts
```

### 4.3 Key Components

#### SearchBar Component
**File:** `frontend/src/components/SearchBar.tsx`

- Debounced search (300ms delay)
- Entity extraction hints
- Example queries for empty state
- Loading states

#### ResultCard Component
**File:** `frontend/src/components/ResultCard.tsx`

- Dynamic renderer for 12 card types
- Icon and color mapping per type
- Score badge (hidden by default)
- Integrates MicroActions component

#### MicroActions Component
**File:** `frontend/src/components/MicroActions.tsx`

- Renders action buttons based on card type
- Handles confirmation dialogs for mutation_heavy actions
- Integrates with actionClient for execution
- Visual distinction: read-only (blue), mutation-light (gray), mutation-heavy (orange)

### 4.4 Type System

**File:** `frontend/src/types/actions.ts` (996 lines)

**Complete action registry with metadata:**

```typescript
export const ACTION_REGISTRY: Record<MicroAction, ActionMetadata> = {
  diagnose_fault: {
    action_name: 'diagnose_fault',
    label: 'Diagnose Fault',
    cluster: 'fix_something',
    side_effect_type: 'read_only',
    icon: 'AlertTriangle',
    description: 'Analyze fault code and provide diagnostic guidance',
  },
  // ... 66 more actions
}
```

**Helper functions:**
```typescript
getActionMetadata(action: MicroAction): ActionMetadata
getActionsForCard(cardType: CardType): MicroAction[]
requiresConfirmation(action: MicroAction): boolean
canPerformAction(action: MicroAction, userRole: string): boolean
```

### 4.5 Authentication Flow

```
User visits /search
  ↓
withAuth HOC checks session
  ↓
If no session → redirect to /login
  ↓
User logs in via Supabase Auth
  ↓
JWT stored in localStorage
  ↓
All API requests include: Authorization: Bearer <jwt>
  ↓
Backend validates JWT, extracts user_id, yacht_id, role
```

**Session Management:**
- Access token: 24-hour expiry
- Refresh token: 30-day validity
- Auto-refresh on token expiry

---

## 5. Backend Architecture

### 5.1 Python Action Router

**Entry Point:** `backend/src/action_router/router.py`

**Core Flow:**
```python
@app.post("/api/actions/{action_name}")
async def execute_action(action_name: str, payload: ActionPayload):
    # 1. Validate JWT
    user = await jwt_validator.validate(request.headers.authorization)

    # 2. Check role permissions
    if not role_validator.can_perform(user.role, action_name):
        return {"success": False, "error": "Insufficient permissions"}

    # 3. Enforce yacht isolation
    if user.yacht_id != payload.yacht_id:
        return {"success": False, "error": "Cross-tenant access denied"}

    # 4. Validate schema
    await schema_validator.validate(action_name, payload.context)

    # 5. Dispatch to n8n or internal handler
    result = await dispatcher.dispatch(action_name, payload)

    return result
```

### 5.2 Dispatchers

**n8n Dispatcher** (`dispatchers/n8n_dispatcher.py`):
- Forwards requests to n8n webhooks
- Maps action_name → webhook URL
- Handles retries and timeouts

**Internal Dispatcher** (`dispatchers/internal_dispatcher.py`):
- For read-only actions that don't need n8n
- Direct database queries
- No audit logging required

### 5.3 Integration Layer

**Location:** `backend/src/integrations/`

| Integration | Purpose | File |
|-------------|---------|------|
| **Supabase** | Database queries, RLS enforcement | `supabase.py` |
| **Search Engine** | Entity extraction, semantic search | `search_engine.py` |
| **Predictive Engine** | ML-based maintenance predictions | `predictive_engine.py` |

### 5.4 Middleware

**Authentication Middleware** (`middleware/auth.py`):
- Validates JWT on all protected routes
- Extracts user context (user_id, yacht_id, role)
- Enforces yacht isolation at middleware level

**Tests:** `backend/tests/test_auth_middleware.py`

---

## 6. Database Schema

### 6.1 Core Tables (Implemented)

#### yachts
```sql
CREATE TABLE yachts (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    imo TEXT,                          -- International Maritime Org ID
    signature TEXT UNIQUE NOT NULL,    -- Cryptographic identity
    nas_root_path TEXT,
    status TEXT CHECK (status IN ('active', 'inactive', 'demo')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    yacht_id UUID REFERENCES yachts(id),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT CHECK (role IN ('chief_engineer', 'eto', 'captain', 'manager', 'vendor', 'crew', 'deck', 'interior')),
    auth_provider TEXT DEFAULT 'password',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### user_tokens
```sql
CREATE TABLE user_tokens (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    yacht_id UUID REFERENCES yachts(id),
    token_hash TEXT NOT NULL,          -- SHA256, never plaintext
    token_type TEXT CHECK (token_type IN ('api', 'device', 'refresh')),
    issued_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    metadata JSONB
);
```

**Migration:** `database/migrations/01_core_tables_v2_secure.sql`

### 6.2 Required Tables (To Be Implemented)

**Phase 1 Priority:**

```sql
-- Fault management
CREATE TABLE faults (
    id UUID PRIMARY KEY,
    yacht_id UUID REFERENCES yachts(id),
    equipment_id UUID,
    fault_code TEXT,
    description TEXT,
    severity TEXT CHECK (severity IN ('minor', 'medium', 'critical')),
    resolved BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Work orders
CREATE TABLE work_orders (
    id UUID PRIMARY KEY,
    yacht_id UUID REFERENCES yachts(id),
    equipment_id UUID,
    status TEXT CHECK (status IN ('draft', 'open', 'in_progress', 'completed', 'cancelled')),
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT CHECK (priority IN ('routine', 'important', 'critical')),
    due_date DATE,
    assigned_to UUID REFERENCES users(id),
    created_by UUID REFERENCES users(id),
    completed_at TIMESTAMPTZ
);

-- Parts inventory
CREATE TABLE parts_inventory (
    id UUID PRIMARY KEY,
    yacht_id UUID REFERENCES yachts(id),
    part_name TEXT NOT NULL,
    part_number TEXT,
    stock_level INT DEFAULT 0,
    min_level INT DEFAULT 0,
    storage_location TEXT,
    preferred_supplier TEXT
);

-- Handovers
CREATE TABLE handovers (
    id UUID PRIMARY KEY,
    yacht_id UUID REFERENCES yachts(id),
    title TEXT,
    period_start DATE,
    period_end DATE,
    status TEXT CHECK (status IN ('draft', 'completed')),
    created_by UUID REFERENCES users(id)
);

CREATE TABLE handover_items (
    id UUID PRIMARY KEY,
    handover_id UUID REFERENCES handovers(id),
    source_type TEXT,
    source_id UUID,
    summary TEXT,
    importance TEXT CHECK (importance IN ('low', 'normal', 'high'))
);

-- Audit logging
CREATE TABLE audit_log (
    id UUID PRIMARY KEY,
    entity_type TEXT,
    entity_id UUID,
    action TEXT,
    field TEXT,
    old_value JSONB,
    new_value JSONB,
    reason TEXT,
    user_id UUID REFERENCES users(id),
    yacht_id UUID REFERENCES yachts(id),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    severity TEXT CHECK (severity IN ('low', 'normal', 'high'))
);
```

**See:** `docs/specs/table_configs.md` for complete schema

### 6.3 Row-Level Security (RLS)

**All tables enforce per-yacht isolation:**

```sql
-- Enable RLS
ALTER TABLE work_orders ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their yacht's data
CREATE POLICY yacht_isolation_policy ON work_orders
    FOR ALL
    USING (yacht_id = current_setting('app.current_yacht_id')::UUID);

-- Policy: Read-only for vendors
CREATE POLICY vendor_read_only ON work_orders
    FOR SELECT
    USING (yacht_id = current_setting('app.current_yacht_id')::UUID
           AND current_setting('app.user_role') = 'vendor');
```

**See:** `database/SECURITY_ARCHITECTURE.md`

---

## 7. Security & Isolation

### 7.1 Multi-Layer Security Model

```
┌──────────────────────────────────────────┐
│ Layer 1: Transport Security              │
│ - TLS 1.3 for all connections           │
│ - Certificate pinning (mobile)          │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│ Layer 2: Authentication                  │
│ - JWT with 24-hour expiry               │
│ - Refresh token rotation                │
│ - Yacht signature validation            │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│ Layer 3: Authorization                   │
│ - Role-based access control (RBAC)      │
│ - Action-level permissions              │
│ - Context-aware restrictions            │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│ Layer 4: Data Isolation                  │
│ - Per-yacht S3 buckets                  │
│ - Row-Level Security (RLS)              │
│ - Yacht ID enforcement in middleware    │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│ Layer 5: Audit Trail                     │
│ - All mutations logged                  │
│ - Sensitive actions require reason      │
│ - Immutable audit log                   │
└──────────────────────────────────────────┘
```

### 7.2 Threat Mitigations

| Threat | Mitigation | Implementation |
|--------|-----------|----------------|
| Unauthorized yacht access | Per-yacht signatures + RLS | `yacht_validator.py`, RLS policies |
| Token theft | Short expiry + refresh rotation | `jwt_validator.py` |
| Cross-tenant leakage | Yacht ID checks at all layers | Middleware, validators, RLS |
| Invoice fraud | Audit logging + HOD approval | `edit_invoice_amount` workflow |
| NAS tampering | SHA256 verification | Local agent |
| Privilege escalation | RBAC + action permissions | `role_validator.py` |

**See:** `docs/architecture/security.md`

---

## 8. API Contracts

### 8.1 Search API

**Endpoint:** `POST /v1/search`

**Request:**
```json
{
  "query": "E047 overheat main engine",
  "filters": {
    "card_types": ["fault", "work_order", "document"],
    "time_range": "last_7_days"
  }
}
```

**Response:**
```json
{
  "success": true,
  "intent": "diagnose_fault",
  "entities": {
    "equipment_id": "uuid-123",
    "fault_code": "E047"
  },
  "results": [
    {
      "card_type": "fault",
      "title": "Fault E047 - High Coolant Temperature",
      "score": 0.95,
      "entities": {...},
      "actions": [
        {"action_name": "diagnose_fault", "label": "Diagnose Fault", ...},
        {"action_name": "create_work_order_from_fault", ...}
      ]
    }
  ]
}
```

### 8.2 Action Execution API

**Endpoint:** `POST /api/actions/{action_name}`

**Headers:**
```
Authorization: Bearer <jwt_token>
X-Yacht-Signature: <yacht_signature>
Content-Type: application/json
```

**Request Body:**
```json
{
  "action_name": "create_work_order",
  "user_id": "uuid-456",
  "yacht_id": "uuid-789",
  "context": {
    "equipment_id": "uuid-123",
    "title": "Service main engine",
    "priority": "high",
    "due_date": "2025-11-25"
  },
  "timestamp": "2025-11-21T14:30:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Work order created successfully",
  "data": {
    "work_order_id": "uuid-new",
    "created_at": "2025-11-21T14:30:15Z"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "message": "User role 'crew' cannot create work orders",
    "details": {"required_role": "chief_engineer"}
  }
}
```

### 8.3 Audit Log Contract

**For audit-sensitive actions** (e.g., `edit_invoice_amount`):

```json
{
  "entity_type": "invoice",
  "entity_id": "uuid-555",
  "action": "edit_invoice_amount",
  "field": "invoice_amount",
  "old_value": 1250.00,
  "new_value": 1320.00,
  "reason": "Corrected based on final supplier quote",
  "user_id": "uuid-456",
  "yacht_id": "uuid-789",
  "timestamp": "2025-11-21T15:50:00Z",
  "severity": "high"
}
```

**See:** `docs/specs/action-endpoint-contract.md`

---

## 9. Implementation Phases

### Phase 1: Foundation (IMMEDIATE PRIORITY)

**Goal:** End-to-end flow for 10 critical actions

**Scope:**
- ✅ Complete TypeScript type system (67 actions)
- ✅ Python action router with validators
- ⚡ Build 5 core n8n workflows
- ⚡ Create modal/form components
- ⚡ Implement 5 database tables (work_orders, faults, parts, handovers, audit_log)

**10 Core Actions:**
1. `view_equipment_details` (read)
2. `view_part_stock` (read)
3. `create_work_order` (mutation_heavy)
4. `mark_work_order_complete` (mutation_light)
5. `add_to_handover` (mutation_light)
6. `add_work_order_note` (mutation_light)
7. `order_part` (mutation_heavy)
8. `edit_work_order_details` (mutation_heavy, audit)
9. `edit_invoice_amount` (mutation_heavy, audit + notification)
10. `diagnose_fault` (read + AI)

**Timeline:** 2-3 weeks

### Phase 2: Scale to Full Action Set (HIGH PRIORITY)

**Goal:** All 67 actions functional

**Scope:**
- All 12 card components
- All 67 n8n workflows
- All modal/form components
- Role-based access control fully enforced
- Complete database schema

**Timeline:** 4-6 weeks

### Phase 3: View Patterns & Filters (MEDIUM PRIORITY)

**Goal:** Enable all 14 viewing/filtering patterns

**Scope:**
- Filter UI components
- View pattern query builders
- Grouped/aggregated views
- Search refinement

**Timeline:** 3-4 weeks

### Phase 4: Advanced Features (LOW PRIORITY)

**Goal:** Polish and premium features

**Scope:**
- Bulk operations
- Comparison views
- Hierarchical views
- Dashboard customization
- Mobile app optimization

**Timeline:** 4-6 weeks

**See:** `docs/architecture/IMPLEMENTATION_ARCHITECTURE.md`

---

## 10. File Organization

### 10.1 Repository Structure

```
/Cloud_PMS/
├── docs/                          # Documentation (organized)
│   ├── ARCHITECTURE_UNIFIED.md    # This file
│   ├── START_HERE.md             # Getting started guide
│   ├── /micro-actions/           # Micro-action specifications
│   │   ├── MICRO_ACTION_REGISTRY.md
│   │   ├── ACTION_OFFERING_MAP.md
│   │   ├── ACTION_OFFERING_RULES.md
│   │   ├── VIEWING_PATTERNS_ANALYSIS.md
│   │   └── ...
│   ├── /specs/                   # Technical specifications
│   │   ├── api-spec.md
│   │   ├── search-engine-spec.md
│   │   ├── table_configs.md
│   │   └── ...
│   ├── /architecture/            # Architecture docs
│   │   ├── architecture.md
│   │   ├── IMPLEMENTATION_ARCHITECTURE.md
│   │   ├── security.md
│   │   └── ...
│   ├── /domain/                  # Domain knowledge
│   │   ├── glossary.md
│   │   ├── predictive-maintenance.md
│   │   └── ...
│   ├── /design/                  # Design & UX
│   │   ├── foundations.md
│   │   ├── web-ux.md
│   │   └── ...
│   └── /integration/             # Integration docs
│       ├── INTEGRATION_FLOWS.md
│       └── INTEGRATION_LAYER.md
│
├── backend/                      # Python backend
│   ├── src/
│   │   ├── action_router/       # Action routing & validation
│   │   ├── integrations/        # External integrations
│   │   └── middleware/          # Middleware (auth, etc.)
│   ├── tests/
│   └── requirements.txt
│
├── frontend/                     # Next.js frontend
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # React components
│   │   ├── contexts/            # React contexts
│   │   ├── hooks/               # Custom hooks
│   │   ├── lib/                 # Utilities & clients
│   │   ├── types/               # TypeScript types
│   │   └── __tests__/           # Tests
│   └── package.json
│
├── database/                     # Database scripts
│   ├── migrations/              # SQL migrations
│   ├── README.md
│   └── SECURITY_ARCHITECTURE.md
│
├── .env.example                  # Environment variables template
├── .github/                      # GitHub templates
└── README.md                     # Project README
```

### 10.2 Key Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| `docs/ARCHITECTURE_UNIFIED.md` | Comprehensive architecture (this file) | All engineers |
| `docs/START_HERE.md` | Getting started guide | New developers |
| `docs/micro-actions/MICRO_ACTION_REGISTRY.md` | 67 micro-action specifications | Frontend + backend |
| `docs/micro-actions/ACTION_OFFERING_RULES.md` | Intent-based action offering logic | Backend + AI team |
| `docs/specs/api-spec.md` | REST API specification | Frontend + backend |
| `docs/architecture/security.md` | Security architecture | DevOps + security |
| `database/SECURITY_ARCHITECTURE.md` | Database RLS policies | Backend + DBA |

---

## Conclusion

This unified architecture represents the **complete integration** of:
- ✅ 67 micro-actions across 7 purpose clusters
- ✅ 12 card types with dynamic action offering
- ✅ Python action router with validation pipeline
- ✅ n8n workflow orchestration (67 workflows planned)
- ✅ Next.js frontend with TypeScript
- ✅ Supabase database with RLS
- ✅ Multi-layer security model
- ✅ Comprehensive documentation

**Current Status:** Phase 1 (Foundation) - 60% complete

**Next Steps:**
1. Implement 5 core n8n workflows
2. Build modal/form components
3. Complete 5 Phase 1 database tables
4. Test end-to-end: Search → Action → Database
5. Deploy to staging environment

**For New Developers:** Start with `docs/START_HERE.md`

---

**Last Updated:** 2025-11-21
**Maintained By:** CelesteOS Core Team
**Version:** 2.0 (Post-Merge Unified Architecture)
