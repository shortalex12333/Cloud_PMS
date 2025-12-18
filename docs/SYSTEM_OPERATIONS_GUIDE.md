# CelesteOS System Operations Guide

**Last Updated:** December 2024
**Purpose:** Complete operational reference for developers returning to the project

---

## TABLE OF CONTENTS

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Ports & URLs](#3-ports--urls)
4. [Technology Stack](#4-technology-stack)
5. [Supabase Tables](#5-supabase-tables)
6. [API Endpoints](#6-api-endpoints)
7. [Webhooks & n8n](#7-webhooks--n8n)
8. [67 Micro-Actions](#8-67-micro-actions)
9. [12 Card Types](#9-12-card-types)
10. [User Journeys](#10-user-journeys)
11. [Authentication Flow](#11-authentication-flow)
12. [Environment Variables](#12-environment-variables)
13. [Frontend Pages](#13-frontend-pages)
14. [Development Quick Start](#14-development-quick-start)

---

## 1. SYSTEM OVERVIEW

**CelesteOS** is an AI-driven engineering intelligence platform for superyachts.

### What It Does:
- **Search** - Semantic search across manuals, faults, work orders, parts
- **Diagnose** - AI-powered fault diagnosis with manual references
- **Maintain** - Work order management, PMS scheduling
- **Inventory** - Parts tracking, ordering, stock management
- **Handover** - Automated crew handover document generation
- **Compliance** - Hours of rest (MLC), survey prep, audit trails
- **Predict** - ML-based predictive maintenance

### Core Concept:
Users interact via **67 micro-actions** across **12 card types**. Every action flows through a centralized action router that validates permissions, executes the action, and logs for audit.

---

## 2. ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Search Page  │  │  Dashboard   │  │  List Views  │  │   Settings   │ │
│  │ (Spotlight)  │  │ (Control Ctr)│  │ (Faults/WOs) │  │ (Integrations│ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js 14)                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ React Components → Hooks → API Clients → Supabase Auth             │ │
│  │                                                                    │ │
│  │ Key Hooks:                                                         │ │
│  │ • useActionHandler() - Execute 67 micro-actions                    │ │
│  │ • useCelesteSearch() - Streaming semantic search                   │ │
│  │ • useDashboardData() - Dashboard metrics                           │ │
│  │ • useAuth() - Authentication state                                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌──────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│   SUPABASE (Auth)    │ │   CLOUD API      │ │   SEARCH ENGINE      │
│  ┌────────────────┐  │ │  (Python/Fast)   │ │  (Python/Render)     │
│  │ Authentication │  │ │ ┌──────────────┐ │ │ ┌────────────────┐   │
│  │ JWT Tokens     │  │ │ │Action Router │ │ │ │Semantic Search │   │
│  │ User Sessions  │  │ │ │POST /execute │ │ │ │Intent Detection│   │
│  └────────────────┘  │ │ └──────────────┘ │ │ │Entity Extraction│  │
└──────────────────────┘ └────────┬─────────┘ └──────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
┌──────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│   n8n WORKFLOWS      │ │   PREDICTIVE     │ │   SUPABASE DB        │
│  (Automation)        │ │   ENGINE         │ │  (PostgreSQL)        │
│ ┌──────────────────┐ │ │  (Python/Render) │ │ ┌────────────────┐   │
│ │ 67 action flows  │ │ │ ┌──────────────┐ │ │ │ 25+ Tables     │   │
│ │ Webhooks         │ │ │ │Risk Scoring  │ │ │ │ pgvector       │   │
│ │ DB operations    │ │ │ │Predictions   │ │ │ │ RLS Policies   │   │
│ └──────────────────┘ │ │ └──────────────┘ │ │ └────────────────┘   │
└──────────────────────┘ └──────────────────┘ └──────────────────────┘
```

---

## 3. PORTS & URLs

### Development

| Service | Port | URL |
|---------|------|-----|
| Frontend (Next.js) | 3000 | `http://localhost:3000` |
| Backend (FastAPI) | 8000 | `http://localhost:8000` |
| Supabase Studio | 54323 | `http://localhost:54323` (local) |

### Production

| Service | URL |
|---------|-----|
| Frontend | `https://celeste7.ai` (Vercel) |
| Backend API | `https://api.celeste7.ai` |
| Supabase | `https://{project}.supabase.co` |
| Search Engine | `https://celesteos-search.onrender.com` |
| Predictive Engine | `https://celesteos-predictive.onrender.com` |
| n8n | Configured per deployment |

---

## 4. TECHNOLOGY STACK

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14.2.0 | React framework (App Router) |
| React | 18.3.0 | UI library |
| TypeScript | 5.3.0 | Type safety |
| Tailwind CSS | 3.4.0 | Styling |
| React Query | 5.90.10 | Server state management |
| Zod | 4.1.12 | Schema validation |
| React Hook Form | 7.66.1 | Form management |
| Radix UI | Various | Accessible primitives |
| Lucide React | 0.344.0 | Icons |
| Sonner | 2.0.7 | Toast notifications |

### Backend
| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Runtime |
| FastAPI | API framework |
| Supabase Client | Database access |
| PyJWT | Token validation |

### Database
| Technology | Purpose |
|------------|---------|
| PostgreSQL 15 | Primary database |
| pgvector | Vector embeddings |
| Supabase | Hosting + Auth + RLS |

### External Services
| Service | Purpose |
|---------|---------|
| OpenAI | Embeddings (text-embedding-3-small) |
| Microsoft Graph | Outlook integration |
| n8n | Workflow automation |

---

## 5. SUPABASE TABLES

### Core Tables

```sql
-- YACHT (vessel records)
yachts (
  id uuid PRIMARY KEY,
  name text,
  imo text,                    -- IMO number
  mmsi text,                   -- Maritime ID
  flag_state text,
  length_m numeric(6,2),
  signature text UNIQUE,       -- Install key (SHA) for routing
  status text                  -- 'active', 'inactive', 'demo'
)

-- USERS (crew members)
users (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,            -- Multi-tenant isolation
  email text UNIQUE,
  name text,
  role text,                   -- 'chief_engineer', 'eto', 'captain', etc.
  is_active boolean
)

-- USER TOKENS (API/device tokens)
user_tokens (
  id uuid PRIMARY KEY,
  user_id uuid FK,
  yacht_id uuid FK,
  token_hash text,             -- NEVER store raw tokens
  token_type text,             -- 'api', 'device', 'refresh'
  expires_at timestamptz
)
```

### PMS (Maintenance) Tables

```sql
-- EQUIPMENT (systems/components)
equipment (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  parent_id uuid FK,           -- Hierarchical (subsystems)
  name text,
  code text,                   -- Tag label (ME1, GEN2)
  manufacturer text,
  model text,
  serial_number text,
  location text,               -- 'engine_room', 'aft', etc.
  criticality text,            -- 'low', 'medium', 'high'
  system_type text             -- 'main_engine', 'generator', etc.
)

-- WORK ORDERS (maintenance tasks)
work_orders (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  equipment_id uuid FK,
  title text,
  description text,
  type text,                   -- 'scheduled', 'corrective', 'unplanned'
  priority text,               -- 'routine', 'important', 'critical'
  status text,                 -- 'planned', 'in_progress', 'completed'
  due_date date,
  frequency jsonb,             -- {type: 'hours'|'days', value: int}
  created_by uuid FK,
  assigned_to uuid FK
)

-- FAULTS (equipment failures)
faults (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  equipment_id uuid FK,
  fault_code text,
  title text,
  description text,
  severity text,               -- 'low', 'medium', 'high'
  detected_at timestamptz,
  resolved_at timestamptz,
  work_order_id uuid FK        -- Linked corrective WO
)

-- WORK ORDER HISTORY (completion records)
work_order_history (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  work_order_id uuid FK,
  completed_by uuid FK,
  completed_at timestamptz,
  notes text,
  hours_logged int,
  parts_used jsonb,            -- [{part_id, quantity}]
  status_on_completion text
)
```

### Inventory Tables

```sql
-- PARTS (spare parts catalog)
parts (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  name text,
  part_number text,
  manufacturer text,
  description text,
  category text,               -- 'filter', 'gasket', 'belt', etc.
  model_compatibility jsonb    -- ['CAT3516', 'MTU4000']
)

-- STOCK LOCATIONS (physical storage)
stock_locations (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  name text,                   -- 'Engine Room Locker A'
  deck text,
  position text                -- Shelf/bin labels
)

-- STOCK LEVELS (current inventory)
stock_levels (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  part_id uuid FK,
  location_id uuid FK,
  quantity int,
  min_quantity int,
  max_quantity int,
  last_counted_at timestamptz
)

-- SUPPLIERS (vendors)
suppliers (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  name text,
  email text,
  phone text,
  preferred boolean
)

-- PURCHASE ORDERS
purchase_orders (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  supplier_id uuid FK,
  po_number text,
  status text,                 -- 'draft', 'sent', 'received', 'closed'
  ordered_at timestamptz,
  currency text
)

purchase_order_lines (
  id uuid PRIMARY KEY,
  purchase_order_id uuid FK,
  part_id uuid FK,
  quantity_ordered int,
  quantity_received int,
  unit_price numeric
)
```

### Handover & Compliance Tables

```sql
-- HANDOVER DRAFTS
handover_drafts (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  period_start date,
  period_end date,
  title text,
  description text,            -- AI-generated summary
  created_by uuid FK,
  status text                  -- 'draft', 'finalised'
)

-- HANDOVER ITEMS (linked content)
handover_items (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  handover_id uuid FK,
  source_type text,            -- 'work_order', 'fault', 'note', etc.
  source_id uuid,
  summary text,
  importance text              -- 'low', 'normal', 'high'
)

-- HOURS OF REST (MLC compliance)
hours_of_rest_records (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  user_id uuid FK,
  date date,
  hours_worked numeric(5,2),
  hours_of_rest numeric(5,2),
  violations boolean,
  notes text
)
```

### Document & Search Tables

```sql
-- DOCUMENTS (ingested files)
documents (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  source text,                 -- 'nas', 'email', 'upload'
  filename text,
  content_type text,
  storage_path text,
  equipment_ids uuid[],
  tags text[],                 -- 'manual', 'schematic', etc.
  indexed boolean
)

-- DOCUMENT CHUNKS (for vector search)
document_chunks (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  document_id uuid FK,
  chunk_index int,
  text text,
  page_number int,
  embedding vector(1536),      -- pgvector
  equipment_ids uuid[],
  fault_codes text[]
)

-- SEARCH QUERIES (analytics)
search_queries (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  user_id uuid FK,
  query_text text,
  interpreted_intent text,
  entities jsonb,
  latency_ms int,
  success boolean
)

-- EVENT LOG (audit trail)
event_log (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  user_id uuid FK,
  event_type text,             -- 'create_work_order', 'login', etc.
  entity_type text,
  entity_id uuid,
  metadata jsonb
)
```

### Graph RAG Tables (Optional)

```sql
-- GRAPH NODES
graph_nodes (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  node_type text,              -- 'equipment', 'part', 'fault', etc.
  ref_table text,
  ref_id uuid,
  label text,
  properties jsonb
)

-- GRAPH EDGES
graph_edges (
  id uuid PRIMARY KEY,
  yacht_id uuid FK,
  from_node_id uuid FK,
  to_node_id uuid FK,
  edge_type text,              -- 'USES_PART', 'HAS_FAULT', etc.
  weight numeric
)
```

---

## 6. API ENDPOINTS

### Frontend API Routes (`/api/integrations/`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/integrations/outlook/auth-url` | Generate Microsoft OAuth URL |
| GET | `/api/integrations/outlook/callback` | Exchange OAuth code for tokens |
| POST | `/api/integrations/outlook/disconnect` | Revoke Outlook access |
| GET | `/api/integrations/outlook/status` | Check integration status |

### Backend Action Router

**Main Endpoint:** `POST /v1/actions/execute`

```json
// Request
{
  "action": "create_work_order",
  "context": {
    "yacht_id": "uuid",
    "equipment_id": "uuid"
  },
  "payload": {
    "title": "Replace oil filter",
    "description": "Scheduled maintenance",
    "type": "scheduled",
    "priority": "routine",
    "due_date": "2024-12-25"
  }
}

// Response (Success)
{
  "status": "success",
  "action": "create_work_order",
  "result": {
    "work_order_id": "uuid",
    "created_at": "2024-12-18T10:00:00Z"
  }
}

// Response (Error)
{
  "status": "error",
  "action": "create_work_order",
  "error_code": "PERMISSION_DENIED",
  "message": "Role 'crew' cannot create critical work orders"
}
```

### Search Engine

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/search` | Semantic search with intent detection |
| GET | `/v1/search/suggestions` | Autocomplete suggestions |

### Predictive Engine

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/predictive/state` | All equipment risk scores |
| GET | `/v1/predictive/state/{equipment_id}` | Detailed analysis |
| POST | `/v1/predictive/maintenance` | Generate recommendations |

---

## 7. WEBHOOKS & n8n

### n8n Workflow Webhooks

Actions that route through n8n workflows:

| Action | Webhook Path |
|--------|--------------|
| `create_work_order` | `/webhook/create_work_order` |
| `add_to_handover` | `/webhook/add_to_handover` |
| `add_document_to_handover` | `/webhook/add_document_to_handover` |
| `add_part_to_handover` | `/webhook/add_part_to_handover` |
| `add_predictive_to_handover` | `/webhook/add_predictive_to_handover` |
| `export_handover` | `/webhook/export_handover` |
| `order_part` | `/webhook/order_part` |

### Workflow Templates

Located in `/backend/n8n-workflows/`:

- `master-create-workflow.json` - Create operations
- `master-update-workflow.json` - Update operations
- `master-view-workflow.json` - Read operations
- `master-export-workflow.json` - Export to PDF/Excel
- `master-linking-workflow.json` - Entity linking
- `master-rag-workflow.json` - RAG pipeline

### Workflow Structure

```
1. Webhook Trigger (POST)
2. JWT Validation
3. Authentication Check
4. Database Insert/Update (Supabase)
5. Audit Logging
6. Response Return
```

---

## 8. 67 MICRO-ACTIONS

### By Category

#### FAULT & DIAGNOSIS (9 actions)
| Action | Label | Side Effect | Notes |
|--------|-------|-------------|-------|
| `diagnose_fault` | Diagnose Fault | read_only | AI diagnostic |
| `report_fault` | Report Fault | mutation_heavy | Requires confirmation |
| `show_manual_section` | View Manual | read_only | |
| `view_fault_history` | View History | read_only | |
| `suggest_parts` | Suggest Parts | read_only | AI suggestion |
| `create_work_order_from_fault` | Create Work Order | mutation_heavy | Requires confirmation |
| `add_fault_note` | Add Note | mutation_light | |
| `add_fault_photo` | Add Photo | mutation_light | |
| `link_equipment_to_fault` | Link Equipment | mutation_light | |

#### WORK ORDER / PMS (11 actions)
| Action | Label | Side Effect | Notes |
|--------|-------|-------------|-------|
| `create_work_order` | Create Work Order | mutation_heavy | Requires confirmation |
| `view_work_order_history` | View History | read_only | |
| `mark_work_order_complete` | Mark Done | mutation_heavy | Requires confirmation |
| `complete_work_order` | Complete Work Order | mutation_heavy | Requires confirmation |
| `add_work_order_note` | Add Note | mutation_light | |
| `add_work_order_photo` | Add Photo | mutation_light | |
| `add_parts_to_work_order` | Add Parts | mutation_light | |
| `link_parts_to_work_order` | Link Parts | mutation_light | |
| `view_work_order_checklist` | Show Checklist | read_only | |
| `assign_work_order` | Assign Task | mutation_light | HOD only |
| `approve_work_order` | Approve Task | mutation_heavy | HOD only |

#### EQUIPMENT (6 actions)
| Action | Label | Side Effect | Notes |
|--------|-------|-------------|-------|
| `view_equipment_details` | View Equipment | read_only | |
| `view_equipment_history` | View History | read_only | |
| `view_equipment_parts` | View Parts | read_only | |
| `view_linked_faults` | View Faults | read_only | |
| `view_equipment_manual` | Open Manual | read_only | |
| `add_equipment_note` | Add Note | mutation_light | |

#### INVENTORY / PARTS (9 actions)
| Action | Label | Side Effect | Notes |
|--------|-------|-------------|-------|
| `view_part_stock` | Check Stock | read_only | |
| `add_part` | Add Part | mutation_heavy | Requires confirmation |
| `order_part` | Order Part | mutation_heavy | Requires confirmation |
| `view_part_location` | View Storage Location | read_only | |
| `view_part_usage` | View Usage History | read_only | |
| `log_part_usage` | Log Usage | mutation_light | |
| `edit_part_quantity` | Edit Quantity | mutation_heavy | Audit required |
| `scan_part_barcode` | Scan Barcode | read_only | |
| `view_linked_equipment` | View Equipment | read_only | |

#### HANDOVER (6 actions)
| Action | Label | Side Effect | Notes |
|--------|-------|-------------|-------|
| `add_to_handover` | Add to Handover | mutation_light | |
| `add_document_to_handover` | Add Document | mutation_light | |
| `add_predictive_insight_to_handover` | Add Insight | mutation_light | |
| `edit_handover_section` | Edit Section | mutation_light | |
| `export_handover` | Export PDF | read_only | |
| `regenerate_handover_summary` | Regenerate Summary | mutation_light | AI summary |

#### DOCUMENT (3 actions)
| Action | Label | Side Effect |
|--------|-------|-------------|
| `view_document` | Open Document | read_only |
| `view_related_documents` | Related Docs | read_only |
| `view_document_section` | View Section | read_only |

#### HOURS OF REST / COMPLIANCE (4 actions)
| Action | Label | Side Effect | Notes |
|--------|-------|-------------|-------|
| `view_hours_of_rest` | View Hours | read_only | |
| `update_hours_of_rest` | Update Hours | mutation_heavy | Requires confirmation |
| `export_hours_of_rest` | Export Logs | read_only | |
| `view_compliance_status` | Check Compliance | read_only | MLC check |

#### PURCHASING / SUPPLIER (7 actions)
| Action | Label | Side Effect | Notes |
|--------|-------|-------------|-------|
| `create_purchase_request` | Create Purchase | mutation_heavy | Requires confirmation |
| `add_item_to_purchase` | Add Item | mutation_light | |
| `approve_purchase` | Approve | mutation_heavy | HOD only |
| `upload_invoice` | Upload Invoice | mutation_light | |
| `track_delivery` | Track Delivery | read_only | |
| `log_delivery_received` | Log Delivery | mutation_heavy | Updates inventory |
| `update_purchase_status` | Update Status | mutation_light | |

#### OPERATIONAL CHECKLISTS (4 actions)
| Action | Label | Side Effect |
|--------|-------|-------------|
| `view_checklist` | View Checklist | read_only |
| `mark_checklist_item_complete` | Mark Complete | mutation_light |
| `add_checklist_note` | Add Note | mutation_light |
| `add_checklist_photo` | Add Photo | mutation_light |

#### SHIPYARD / REFIT (5 actions)
| Action | Label | Side Effect | Notes |
|--------|-------|-------------|-------|
| `view_worklist` | View Worklist | read_only | |
| `add_worklist_task` | Add Task | mutation_heavy | |
| `update_worklist_progress` | Update Progress | mutation_light | |
| `export_worklist` | Export Worklist | read_only | |
| `tag_for_survey` | Tag for Survey | mutation_light | HOD only |

#### FLEET / MANAGEMENT (3 actions)
| Action | Label | Side Effect |
|--------|-------|-------------|
| `view_fleet_summary` | View Fleet | read_only |
| `open_vessel` | Open Vessel | read_only |
| `export_fleet_summary` | Export Summary | read_only |

#### PREDICTIVE / SMART SUMMARY (2 actions)
| Action | Label | Side Effect |
|--------|-------|-------------|
| `request_predictive_insight` | Predictive Insight | read_only |
| `view_smart_summary` | View Summary | read_only |

#### MOBILE-SPECIFIC (2 actions)
| Action | Label | Side Effect |
|--------|-------|-------------|
| `upload_photo` | Upload Photo | mutation_light |
| `record_voice_note` | Voice Note | mutation_light |

#### EDIT ACTIONS (10 actions)
| Action | Label | Side Effect | Notes |
|--------|-------|-------------|-------|
| `edit_work_order_details` | Edit Work Order | mutation_heavy | Requires confirmation |
| `edit_equipment_details` | Edit Equipment | mutation_heavy | HOD only |
| `edit_part_details` | Edit Part Info | mutation_light | HOD only |
| `edit_purchase_details` | Edit Purchase | mutation_heavy | Requires confirmation |
| `edit_invoice_amount` | Edit Invoice Amount | mutation_heavy | HOD only, audit required |
| `edit_fault_details` | Edit Fault | mutation_light | |
| `edit_note` | Edit Note | mutation_light | |
| `delete_item` | Delete Item | mutation_heavy | Soft delete |
| `scan_equipment_barcode` | Scan Equipment | read_only | |

### Side Effect Types

| Type | Description | UI Behavior |
|------|-------------|-------------|
| `read_only` | No database changes | Immediate execution |
| `mutation_light` | Minor updates (notes, photos) | Immediate with toast |
| `mutation_heavy` | Critical changes | Confirmation dialog |

### Role Restrictions

**HOD (Head of Department) Only:**
- `assign_work_order`
- `approve_work_order`
- `approve_purchase`
- `edit_equipment_details`
- `edit_part_details`
- `edit_invoice_amount`
- `tag_for_survey`

**HOD Roles:**
- chief_engineer
- eto
- captain
- manager

---

## 9. 12 CARD TYPES

| Card Type | Description | Key Actions |
|-----------|-------------|-------------|
| `fault` | Equipment failure | diagnose, add_note, create_work_order |
| `work_order` | Maintenance task | complete, add_note, assign |
| `equipment` | System/component | view_details, view_history, add_note |
| `part` | Inventory item | check_stock, order, log_usage |
| `handover` | Crew handover doc | add_item, edit_section, export |
| `document` | Manual/schematic | view, view_related |
| `hor_table` | Hours of rest | view, update, export |
| `purchase` | Purchase order | approve, add_item, track |
| `checklist` | Operational checklist | mark_complete, add_note |
| `worklist` | Shipyard task list | add_task, update_progress |
| `fleet_summary` | Multi-vessel overview | open_vessel, export |
| `smart_summary` | AI-generated brief | view |

---

## 10. USER JOURNEYS

### Journey 1: Diagnose a Fault

```
1. User searches: "generator overheating"
2. Search returns fault cards with confidence scores
3. User clicks "Diagnose Fault" action
4. AI analyzes fault, returns:
   - Root cause analysis
   - Manual sections
   - Historical similar faults
   - Suggested parts
5. User clicks "Create Work Order"
6. Work order pre-filled from fault context
7. User confirms → Work order created
8. Optional: Add to handover
```

### Journey 2: Complete Work Order

```
1. User opens Work Orders list
2. Filters by "in_progress" status
3. Clicks work order card
4. Views checklist (if procedural)
5. Completes each checklist item
6. Adds photo (before/after)
7. Logs parts used
8. Clicks "Complete Work Order"
9. Adds completion notes
10. Confirms → Status updated, inventory adjusted
```

### Journey 3: Order Parts

```
1. User searches for part or scans barcode
2. Views current stock level
3. Stock below minimum → "Order Part" appears
4. Clicks "Order Part"
5. Selects supplier (or uses preferred)
6. Sets quantity, delivery date
7. Confirms → Purchase request created
8. HOD approves purchase
9. Vendor delivers parts
10. User clicks "Log Delivery Received"
11. Inventory automatically updated
```

### Journey 4: Create Handover

```
1. User opens Handover section
2. System shows items auto-flagged:
   - Recent faults
   - Open work orders
   - Critical notes
   - Predictive alerts
3. User reviews each item
4. Adjusts importance levels
5. Adds manual notes
6. Clicks "Export PDF"
7. Handover document generated
8. Shared with incoming crew
```

### Journey 5: HOD Dashboard Review

```
1. HOD logs in → Redirected to Dashboard
2. Control Center shows 8 modules:
   - Work Orders (pending/overdue)
   - Fault Activity (recent/critical)
   - Equipment Status (health %)
   - Inventory (low stock alerts)
   - Crew Notes (recent entries)
   - Predictive Risks (high-risk equipment)
   - Document Expiry (certificates)
   - Handover Status (draft/ready)
3. HOD clicks module to expand
4. Takes inline actions (approve, assign)
5. Drills down to detail pages
```

---

## 11. AUTHENTICATION FLOW

### Login Flow

```
1. User enters email/password
2. Frontend calls Supabase Auth signIn()
3. Supabase validates credentials
4. Returns JWT + refresh token
5. Frontend stores session
6. JWT contains: user_id, yacht_id, role, exp
7. User redirected based on role:
   - HOD → /dashboard
   - Crew → /search
```

### Token Refresh

```
1. API call made
2. Frontend checks: token expires in < 5 minutes?
3. If yes → call Supabase refreshSession()
4. New JWT obtained
5. Original API call proceeds with fresh token
```

### JWT Structure

```json
{
  "sub": "user-uuid",
  "email": "crew@yacht.com",
  "role": "chief_engineer",
  "yacht_id": "yacht-uuid",
  "exp": 1734567890,
  "iat": 1734481490
}
```

### Role Hierarchy

| Role | Level | Access |
|------|-------|--------|
| `manager` | HOD | Full access, fleet view |
| `captain` | HOD | Full access, single yacht |
| `chief_engineer` | HOD | Full technical access |
| `eto` | HOD | Electrical/technical focus |
| `crew` | Standard | Basic operations |
| `deck` | Standard | Deck-specific |
| `interior` | Standard | Interior-specific |
| `vendor` | External | Limited PO/delivery |

---

## 12. ENVIRONMENT VARIABLES

### Required Variables

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret

# Cloud API
NEXT_PUBLIC_CLOUD_API_URL=https://api.celeste7.ai
CLOUD_API_URL=https://api.celeste7.ai

# Search Engine
SEARCH_ENGINE_URL=https://celesteos-search.onrender.com
SEARCH_ENGINE_SERVICE_TOKEN=xxx

# Predictive Engine
PREDICTIVE_ENGINE_URL=https://celesteos-predictive.onrender.com
PREDICTIVE_ENGINE_SERVICE_TOKEN=xxx
```

### Optional Variables

```env
# n8n
N8N_URL=https://n8n.yourdomain.com
N8N_API_KEY=xxx

# OpenAI (for embeddings)
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536

# Feature Flags
ENABLE_GRAPHRAG=true
ENABLE_PREDICTIVE=true
ENABLE_SEARCH_STREAMING=true

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
LOG_LEVEL=info
```

### Frontend-Specific (NEXT_PUBLIC_)

```env
NEXT_PUBLIC_APP_NAME=CelesteOS
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_ENABLE_ANALYTICS=false
```

---

## 13. FRONTEND PAGES

### Page Structure

| Route | Component | Purpose | Auth |
|-------|-----------|---------|------|
| `/` | redirect | Redirects to /search | - |
| `/login` | LoginContent | Authentication | Public |
| `/search` | SearchContent | Spotlight search | Required |
| `/dashboard` | DashboardContent | Control Center | HOD only |
| `/briefing` | BriefingContent | Pre-departure brief | HOD only |
| `/settings` | SettingsContent | Integrations, prefs | Required |
| `/work-orders` | WorkOrdersList | WO list view | Required |
| `/faults` | FaultsList | Fault list view | Required |
| `/parts` | PartsList | Inventory list | Required |

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `SpotlightSearch` | `/components/spotlight/` | Main search UI |
| `ControlCenter` | `/components/dashboard/` | Dashboard modules |
| `ActionButton` | `/components/actions/` | Execute micro-actions |
| `*Card` | `/components/cards/` | 12 card type renderers |
| `*Modal` | `/components/modals/` | 21+ action modals |

---

## 14. DEVELOPMENT QUICK START

### Prerequisites

- Node.js 18+
- Python 3.11+
- Supabase account (or local)

### Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local with your credentials
npm run dev
# → http://localhost:3000
```

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
uvicorn src.action_router.router:app --reload --port 8000
# → http://localhost:8000
```

### Database Setup

```bash
# Run migrations against Supabase
psql -h db.xxx.supabase.co -U postgres -d postgres \
  -f database/migrations/00_enable_extensions.sql
psql -h db.xxx.supabase.co -U postgres -d postgres \
  -f database/migrations/01_core_tables.sql
```

### Useful Commands

```bash
# Frontend
npm run build          # Production build
npm run lint           # ESLint check
npm run type-check     # TypeScript check

# Git
git status
git log --oneline -10
```

---

## QUICK REFERENCE CHEAT SHEET

### Most Used Hooks

```typescript
// Auth
const { user } = useAuth();
const isManager = isHOD(user);

// Actions
const { executeAction, isLoading } = useActionHandler();
await executeAction('create_work_order', { context, payload });

// Search
const { query, results, handleQueryChange, search } = useCelesteSearch();

// Dashboard
const { data, isLoading } = useDashboardData();
```

### Most Used Components

```tsx
// Action Button
<ActionButton action="create_work_order" context={{ equipment_id }} />

// Card
<WorkOrderCard workOrder={wo} actions={['complete', 'add_note']} />

// Modal
<CreateWorkOrderModal open={open} onOpenChange={setOpen} context={ctx} />
```

### File Locations

| Need | Location |
|------|----------|
| Add new action | `types/actions.ts` → ACTION_REGISTRY |
| Add new card type | `components/cards/` |
| Add new modal | `components/modals/` |
| Add new hook | `hooks/` |
| Add new API route | `app/api/` |
| Modify styles | `styles/globals.css` or Tailwind classes |
| Modify theme | `styles/design-system.ts` |

---

*Document generated from codebase analysis. Keep updated as system evolves.*
