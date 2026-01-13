# CelesteOS Action System Architecture
## Complete Formal Specification

**Date:** 2026-01-11
**Purpose:** Define how user queries, entity context, document viewing, and situations trigger the right actions at the right time

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Entities](#core-entities)
3. [Action Registry](#action-registry)
4. [Entity-Action Matrix](#entity-action-matrix)
5. [Situational States](#situational-states)
6. [Query Intent → Action Offering](#query-intent--action-offering)
7. [Document Viewing → Context Building](#document-viewing--context-building)
8. [Triggering Logic & Thresholds](#triggering-logic--thresholds)
9. [Database Schema](#database-schema)
10. [Implementation Rules](#implementation-rules)

---

## 1. System Overview

### Architecture Principle

```
User Input (Query/Document View/Entity Page)
          ↓
    [Intent Parser]
          ↓
    [Entity Context Builder]
          ↓
    [Action Offering Engine] ← [Situational State Machine]
          ↓
    [Available Actions List]
          ↓
    User Selects Action
          ↓
    [Pre-fill Engine]
          ↓
    User Confirms/Edits
          ↓
    [Execution Engine]
          ↓
    [Audit Trail]
```

### Core Doctrine

- **No ML predictions** - Simple deterministic logic only
- **Entity-based** - Actions appear adjacent to entities
- **Explicit intent** - User triggers, never automatic
- **Preview mutations** - Show effects before commit
- **Situational awareness** - Context determines available actions
- **Audit everything** - Who, what, when, why logged

---

## 2. Core Entities

### Entity Taxonomy

```typescript
enum EntityType {
  // Physical Assets
  EQUIPMENT = 'equipment',
  PART = 'part',

  // Operational Records
  FAULT = 'fault',
  WORK_ORDER = 'work_order',

  // Documentation
  DOCUMENT = 'document',
  DOCUMENT_CHUNK = 'document_chunk',

  // Procurement & Finance
  SHOPPING_LIST_ITEM = 'shopping_list_item',
  PURCHASE_ORDER = 'purchase_order',
  RECEIVING_SESSION = 'receiving_session',

  // Communication
  HANDOVER = 'handover',

  // Special
  SEARCH_RESULT = 'search_result',  // Ephemeral entity
}
```

### Entity Properties (Actionability Map)

Each entity has properties that determine action availability:

| Entity | Key Properties | Determines Actions |
|--------|----------------|-------------------|
| **Fault** | severity, status, equipment_id, work_order_id | create_wo, add_to_handover, show_manual |
| **Equipment** | model, manual_available, fault_count | show_manual, create_wo |
| **Work Order** | status, parts_list, fault_id, notes | add_note, add_part, mark_complete |
| **Part** | stock_level, critical_threshold, location | check_stock, order_part, log_usage |
| **Document Chunk** | section, fault_code_refs, equipment_refs | show_manual, add_to_handover |
| **Shopping List Item** | state, quantity, part_id, order_id | approve, receive, cancel |
| **Receiving Session** | state, items, order_id | confirm_item, mark_discrepancy |
| **Handover** | category, priority, entity_ref, acknowledged | acknowledge, view_source |

---

## 3. Action Registry

### Action Classification

```typescript
enum ActionType {
  READ = 'read',           // No mutation (show_manual, check_stock)
  MUTATE = 'mutate',       // Creates/updates data (create_wo, log_parts)
  SITUATIONAL = 'situational',  // Only available in specific state (receiving, shopping list)
}

enum ActionPriority {
  P0 = 'p0',  // Core operations
  P1 = 'p1',  // Important but not critical
  P2 = 'p2',  // Nice to have
}
```

### Complete Action Registry

| Action ID | Type | Priority | Entry Conditions | Output |
|-----------|------|----------|-----------------|--------|
| `show_manual_section` | READ | P0 | Equipment + manual exists | Opens PDF to section |
| `create_work_order_from_fault` | MUTATE | P0 | Fault exists | WO record |
| `add_note_to_work_order` | MUTATE | P0 | WO active | Note record |
| `add_part_to_work_order` | MUTATE | P0 | WO exists | Part-WO link |
| `mark_work_order_complete` | MUTATE | P0 | WO in_progress | Status change |
| `check_stock_level` | READ | P0 | Part exists | Stock data |
| `log_part_usage` | MUTATE | P0 | WO + parts added | Inventory transaction |
| `add_to_handover` | MUTATE | P0 | Any entity | Handover item |
| `receive_items` | SITUATIONAL | P0 | Shopping List ORDERED | Receiving session |
| `approve_shopping_items` | SITUATIONAL | P0 | Shopping List CANDIDATE + HOD role | Status change |
| `scan_packing_slip` | SITUATIONAL | P0 | Camera + intent | Receiving draft |

---

## 4. Entity-Action Matrix

### Primary Action Offering by Entity

```
FAULT
├── create_work_order_from_fault ← fault.work_order_id IS NULL
├── add_to_handover              ← fault.severity IN ('critical', 'high') OR fault.recurring = TRUE
├── show_manual_section          ← equipment.manual_available = TRUE
└── view_related_work_order      ← fault.work_order_id IS NOT NULL

EQUIPMENT
├── create_work_order            ← Always available (planned maintenance)
├── show_manual                  ← equipment.manual_available = TRUE
├── add_to_handover              ← equipment.status = 'down' OR equipment.critical = TRUE
└── view_faults                  ← equipment.fault_count > 0

WORK_ORDER
├── add_note                     ← wo.status IN ('candidate', 'in_progress')
├── add_part                     ← wo.status IN ('candidate', 'in_progress', 'pending_parts')
├── log_part_usage               ← wo.parts_added.length > 0 AND wo.parts_logged.length < wo.parts_added.length
├── mark_complete                ← wo.status = 'in_progress'
├── add_to_handover              ← wo.status IN ('in_progress', 'blocked', 'pending_parts')
└── show_manual_section          ← wo.equipment.manual_available = TRUE

PART
├── check_stock_level            ← Always visible (READ)
├── add_to_work_order            ← Context: User viewing WO + Part
├── add_to_shopping_list         ← part.stock_level < part.minimum_threshold OR part.stock_level = 0
├── log_usage                    ← Context: Part used in WO
└── order_part                   ← part.stock_level < part.critical_threshold

DOCUMENT_CHUNK
├── show_full_document           ← Always available
├── add_to_handover              ← manual_section = 'critical' OR user_flagged = TRUE
└── link_to_fault               ← doc.fault_code_refs.length > 0

SHOPPING_LIST_ITEM
├── approve                      ← item.state = 'CANDIDATE' AND user.role = 'HOD'
├── edit_quantity                ← item.state IN ('CANDIDATE', 'ACTIVE')
├── remove                       ← item.state = 'CANDIDATE'
├── receive                      ← item.state = 'COMMITTED' (ordered)
└── reorder                      ← item.state = 'MISSING'

RECEIVING_SESSION
├── confirm_item                 ← session.state = 'ACTIVE' AND item.checked = FALSE
├── mark_discrepancy             ← session.state = 'ACTIVE' AND item.delivered ≠ item.expected
├── mark_installed               ← session.state = 'ACTIVE' AND item.checked = TRUE
├── upload_packing_slip          ← session.state = 'CANDIDATE'
└── commit_receiving             ← session.items.filter(checked=TRUE).length > 0

HANDOVER
├── acknowledge                  ← handover.acknowledged_at IS NULL AND user = handover.owner
├── view_source_entity           ← handover.entity_id IS NOT NULL
└── archive                      ← handover.age > 7 days OR handover.source_resolved = TRUE
```

---

## 5. Situational States

### Receiving Situation

```typescript
interface ReceivingSituation {
  states: 'IDLE' | 'CANDIDATE' | 'ACTIVE' | 'REVIEW' | 'COMMITTED';

  // State machine
  transitions: {
    IDLE → CANDIDATE:     user uploads packing slip OR selects order
    CANDIDATE → ACTIVE:   user confirms order match
    ACTIVE → REVIEW:      user ticks ≥1 item
    REVIEW → COMMITTED:   user confirms & saves
    COMMITTED → IDLE:     session complete
  };

  // Actions available per state
  actions: {
    IDLE:      ['scan_packing_slip', 'select_order'],
    CANDIDATE: ['confirm_order', 'upload_more', 'cancel'],
    ACTIVE:    ['check_item', 'edit_quantity', 'mark_discrepancy', 'mark_installed'],
    REVIEW:    ['view_summary', 'back_to_active', 'commit'],
    COMMITTED: ['view_receipt', 'download_labels'],
  };
}
```

**Triggering Conditions:**

```sql
-- Entry: User intent explicit
WHERE user_query LIKE '%receive%' OR user_query LIKE '%delivery%'
   OR user_clicks_camera_icon = TRUE
   OR user_on_order_page AND clicks 'Receive Items'

-- State: ACTIVE (checkbox table visible)
WHERE receiving_session.state = 'ACTIVE'
  AND receiving_session.items.length > 0

-- Constraint: Checkbox = truth
WHERE receiving_item.checked = TRUE  -- Only checked items mutate inventory
```

### Shopping List Situation

```typescript
interface ShoppingListSituation {
  states: 'CANDIDATE' | 'ACTIVE' | 'COMMITTED' | 'PARTIALLY_FULFILLED' | 'FULFILLED' | 'INSTALLED' | 'MISSING';

  // Item-level state machine
  transitions: {
    CANDIDATE → ACTIVE:               HOD reviews
    ACTIVE → COMMITTED:               HOD approves + order issued
    COMMITTED → PARTIALLY_FULFILLED:  Some items received
    COMMITTED → FULFILLED:            All items received
    COMMITTED → INSTALLED:            Items installed immediately
    COMMITTED → MISSING:              Items not received / damaged
  };

  // Actions per state
  actions: {
    CANDIDATE:             ['view', 'edit_qty', 'assign_supplier', 'remove', 'add_note'],
    ACTIVE:                ['approve', 'reject', 'group_with_others', 'assign_urgency'],
    COMMITTED:             ['view_order', 'attach_docs', 'prepare_receiving'],
    PARTIALLY_FULFILLED:   ['receive_remaining', 'mark_missing'],
    FULFILLED:             ['view_only', 'audit_export'],
    INSTALLED:             ['view_linked_wo', 'audit_trail'],
    MISSING:               ['re_add_to_list', 'cancel', 'attach_notes'],
  };
}
```

**Additive Capture Points (Shopping List Entry):**

```sql
-- From Inventory
WHERE part.stock_level < part.minimum_threshold
   OR part.stock_level = 0
   AND user_clicks 'Add to Shopping List'

-- From Work Order Completion
WHERE work_order.status = 'completing'
  AND parts_used NOT IN inventory.parts
  AND user_selects 'Add missing parts to shopping list'

-- From Receiving
WHERE receiving_item.status IN ('missing', 'damaged', 'incorrect')
  AND user_toggles 'Re-add to shopping list'

-- Manual
WHERE user_on_shopping_list_page
  AND user_clicks '+ Add Item'
```

### Finance Situation

```typescript
interface FinanceSituation {
  // Finance is NOT a separate situation
  // It is the SHADOW of Shopping List + Receiving

  spend_posting_rules: {
    intent:     shopping_list.state = 'CANDIDATE',     // No spend yet
    commitment: shopping_list.state = 'COMMITTED',      // Order issued, not spent
    actual:     receiving.state = 'COMMITTED' OR installed = TRUE,  // Money actually spent
  };

  finance_events: {
    shopping_item_approved:   'commitment created',
    receiving_item_checked:   'spend posted',
    item_installed:           'spend posted (skip inventory)',
    item_missing:             'commitment reversed',
  };
}
```

---

## 6. Query Intent → Action Offering

### Intent Classification Engine

```typescript
interface QueryIntent {
  type: 'information' | 'action' | 'navigation';
  action_keywords: string[];
  entity_keywords: string[];
  confidence: 'explicit' | 'inferred' | 'ambiguous';
}

// Intent Parser (Simple, No ML)
function parseQueryIntent(query: string): QueryIntent {
  const lowerQuery = query.toLowerCase();

  // Explicit action keywords
  const actionKeywords = {
    create_wo: ['create', 'new', 'make'] + ['work order', 'wo', 'job'],
    add_note: ['add', 'log', 'note', 'comment'],
    log_parts: ['log', 'record'] + ['parts', 'usage', 'used'],
    check_stock: ['check', 'how many', 'stock', 'inventory'],
    receive: ['receive', 'delivery', 'arrived', 'shipment'],
    order: ['order', 'buy', 'purchase', 'shopping'],
    handover: ['handover', 'brief', 'shift', 'next shift'],
  };

  // Entity keywords
  const entityKeywords = {
    equipment: ['generator', 'engine', 'pump', 'hvac', 'gearbox'],
    fault: ['fault', 'error', 'alarm', 'overheat', 'leak'],
    part: ['filter', 'gasket', 'seal', 'belt', 'spare'],
    document: ['manual', 'procedure', 'schematic', 'diagram'],
  };

  // Match logic (deterministic)
  let intent: QueryIntent = {
    type: 'information',
    action_keywords: [],
    entity_keywords: [],
    confidence: 'ambiguous',
  };

  // Explicit action detection
  for (const [action, keywords] of Object.entries(actionKeywords)) {
    if (keywords.some(kw => lowerQuery.includes(kw))) {
      intent.type = 'action';
      intent.action_keywords.push(action);
      intent.confidence = 'explicit';
    }
  }

  // Entity detection
  for (const [entity, keywords] of Object.entries(entityKeywords)) {
    if (keywords.some(kw => lowerQuery.includes(kw))) {
      intent.entity_keywords.push(entity);
    }
  }

  // If no action keywords but has entity → information query
  if (intent.action_keywords.length === 0 && intent.entity_keywords.length > 0) {
    intent.type = 'information';
    intent.confidence = 'inferred';
  }

  return intent;
}
```

### Action Offering Rules

```typescript
interface ActionOffering {
  location: 'beneath_search' | 'entity_dropdown' | 'contextual_prompt';
  actions: Action[];
  pre_filled: boolean;
}

function offerActions(intent: QueryIntent, searchResults: Entity[]): ActionOffering {
  // Rule 1: Explicit action query → Direct action beneath search
  if (intent.type === 'action' && intent.confidence === 'explicit') {
    return {
      location: 'beneath_search',
      actions: mapIntentToActions(intent.action_keywords),
      pre_filled: true,  // Use search context to pre-fill
    };
  }

  // Rule 2: Information query → Actions in entity dropdown
  if (intent.type === 'information') {
    return {
      location: 'entity_dropdown',
      actions: searchResults.map(entity => getActionsForEntity(entity)),
      pre_filled: true,  // Use entity data to pre-fill
    };
  }

  // Rule 3: Ambiguous → Show results, actions in dropdown only
  return {
    location: 'entity_dropdown',
    actions: [],
    pre_filled: false,
  };
}
```

**Examples:**

| Query | Intent Type | Offered Actions | Location |
|-------|-------------|----------------|----------|
| "create work order for generator 2" | action (explicit) | `create_work_order_from_fault` | Beneath search bar |
| "generator 2 status" | information | None directly, user clicks entity first | N/A |
| "generator 2" (user clicks entity) | N/A (navigation) | `create_wo`, `show_manual`, `view_faults` | Entity dropdown |
| "MTU overheating" | information | Shows fault, actions in dropdown | Entity page → dropdown |
| "add to handover" | action (explicit) | `add_to_handover` (requires entity selection) | Beneath search (modal opens) |
| "receive delivery" | action (explicit) | `scan_packing_slip`, `select_order` | Receiving screen |

---

## 7. Document Viewing → Context Building

### Document Viewing as Action Trigger

When user views a document (PDF manual, procedure), the system builds context for action offering.

```typescript
interface DocumentContext {
  document_id: string;
  current_section: string;
  current_page: number;

  // Extracted references (from chunking/indexing)
  fault_code_refs: string[];        // e.g., ['MTU-OVHT-01', 'CAT-COOL-02']
  equipment_refs: string[];         // e.g., ['Generator 2', 'Main Engine']
  part_refs: string[];              // e.g., ['Thermostat', 'Coolant Filter']

  // User behavior (simple, not tracked over time)
  time_on_section: number;          // Seconds (only for current session)
  user_scrolled_to_bottom: boolean; // Simple flag
}

// Action offering based on document context
function offerActionsFromDocument(context: DocumentContext): Action[] {
  const actions: Action[] = [];

  // Always available: Add to Handover (if section is critical)
  if (context.current_section.includes('Safety') ||
      context.current_section.includes('Critical') ||
      context.fault_code_refs.length > 0) {
    actions.push({
      id: 'add_to_handover',
      pre_fill: {
        title: `Manual Reference: ${context.document_id} - ${context.current_section}`,
        summary_text: `Section ${context.current_section} flagged as important for next shift.`,
        category: 'important_info',
      },
    });
  }

  // If fault codes referenced → Offer "Create WO" or "View Fault"
  if (context.fault_code_refs.length > 0) {
    context.fault_code_refs.forEach(code => {
      const fault = findFaultByCode(code);
      if (fault && !fault.work_order_id) {
        actions.push({
          id: 'create_work_order_from_fault',
          context: { fault_id: fault.id },
          pre_fill: { /* from fault data */ },
        });
      }
    });
  }

  // If parts referenced → Offer "Check Stock"
  if (context.part_refs.length > 0) {
    context.part_refs.forEach(partName => {
      const part = findPartByName(partName);
      if (part) {
        actions.push({
          id: 'check_stock_level',
          context: { part_id: part.id },
        });
      }
    });
  }

  return actions;
}
```

**Key Principle:** Document viewing builds entity context (fault codes, equipment, parts), which then triggers the normal entity-action offering engine. Documents are NOT a special case—they're just another entity type.

---

## 8. Triggering Logic & Thresholds

### Threshold-Based Action Offering

```typescript
// Inventory thresholds trigger shopping list actions
interface InventoryThresholds {
  critical: number;    // Immediate action required
  low: number;         // Warning, should order soon
  minimum: number;     // Reorder point
}

// Threshold evaluation
function evaluateInventoryActions(part: Part): Action[] {
  const actions: Action[] = [];
  const stock = part.stock_level;
  const thresholds = part.thresholds;

  // Critical: Stock at or below critical threshold
  if (stock <= thresholds.critical) {
    actions.push({
      id: 'add_to_shopping_list',
      urgency: 'critical',
      pre_fill: {
        quantity: thresholds.minimum - stock,
        reason: `Critical stock: ${stock} units (critical threshold: ${thresholds.critical})`,
      },
    });
  }

  // Low: Stock below minimum threshold
  else if (stock < thresholds.minimum) {
    actions.push({
      id: 'add_to_shopping_list',
      urgency: 'normal',
      pre_fill: {
        quantity: thresholds.minimum - stock,
        reason: `Low stock: ${stock} units (min threshold: ${thresholds.minimum})`,
      },
    });
  }

  // Always available: Check stock
  actions.push({ id: 'check_stock_level' });

  return actions;
}

// Fault recurrence triggers handover
function evaluateFaultActions(fault: Fault): Action[] {
  const actions: Action[] = [];

  // Recurring fault → Add to handover
  if (fault.occurrence_count >= 3 && fault.last_occurrence_within_days <= 7) {
    actions.push({
      id: 'add_to_handover',
      urgency: 'high',
      pre_fill: {
        category: 'ongoing_fault',
        priority: 'high',
        summary_text: `${fault.code} occurred ${fault.occurrence_count} times in last 7 days.`,
      },
    });
  }

  // Critical severity without WO → Create WO
  if (fault.severity === 'critical' && !fault.work_order_id) {
    actions.push({
      id: 'create_work_order_from_fault',
      urgency: 'critical',
    });
  }

  return actions;
}

// Work order age triggers completion reminder
function evaluateWorkOrderActions(wo: WorkOrder): Action[] {
  const actions: Action[] = [];
  const age_days = (Date.now() - wo.created_at) / (1000 * 60 * 60 * 24);

  // In progress for >7 days without note → Passive reminder
  if (wo.status === 'in_progress' && age_days > 7 && wo.notes.length === 0) {
    // NOTE: This is NOT a proactive nudge
    // It's just a visual indicator on the WO card
    wo.ui_flags.push('add_note_reminder');
  }

  // In progress + parts added but not logged → Warning on completion
  if (wo.status === 'in_progress' && wo.parts_added.length > 0 && wo.parts_logged.length === 0) {
    actions.push({
      id: 'log_part_usage',
      context: { work_order_id: wo.id },
      note: 'Parts added but not logged. Log before completing.',
    });
  }

  return actions;
}
```

### Threshold Configuration Table

| Entity | Threshold Type | Value | Triggers Action |
|--------|---------------|-------|----------------|
| Part | critical_stock | 0-2 units | `add_to_shopping_list` (critical urgency) |
| Part | low_stock | < minimum | `add_to_shopping_list` (normal) |
| Fault | recurrence | 3+ in 7 days | `add_to_handover` (high priority) |
| Fault | severity | critical + no WO | `create_work_order` |
| Work Order | age | >7 days + no notes | Visual reminder flag |
| Work Order | parts | added but not logged | `log_part_usage` before complete |
| Handover | acknowledgment | >1 hour unacknowledged | Reminder badge |
| Receiving | unresolved_items | >0 after 24 hours | HOD notification |

---

## 9. Database Schema

### Core Tables

#### 9.1 Entity Tables

```sql
-- Equipment
CREATE TABLE pms_equipment (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  name TEXT NOT NULL,
  manufacturer TEXT,
  model TEXT,
  location TEXT,
  manual_available BOOLEAN DEFAULT FALSE,
  manual_document_id UUID REFERENCES pms_documents(id),
  status TEXT CHECK (status IN ('operational', 'down', 'maintenance')),
  critical BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Faults
CREATE TABLE pms_faults (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  equipment_id UUID REFERENCES pms_equipment(id),
  code TEXT NOT NULL,  -- e.g., MTU-OVHT-01
  title TEXT NOT NULL,
  description TEXT,
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'diagnosed', 'resolved')),
  work_order_id UUID REFERENCES pms_work_orders(id),
  occurrence_count INTEGER DEFAULT 1,
  last_occurrence TIMESTAMPTZ DEFAULT NOW(),
  reported_by UUID NOT NULL REFERENCES auth.users(id),
  reported_at TIMESTAMPTZ DEFAULT NOW(),
  acknowledged_by UUID REFERENCES auth.users(id),
  acknowledged_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_faults_yacht_status ON pms_faults(yacht_id, status);
CREATE INDEX idx_faults_equipment ON pms_faults(equipment_id, status);
CREATE INDEX idx_faults_recurrence ON pms_faults(yacht_id, occurrence_count DESC, last_occurrence DESC);

-- Work Orders
CREATE TABLE pms_work_orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  number TEXT NOT NULL UNIQUE,  -- WO-2024-001
  title TEXT NOT NULL,
  description TEXT,
  equipment_id UUID REFERENCES pms_equipment(id),
  fault_id UUID REFERENCES pms_faults(id),
  location TEXT,
  priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'critical')),
  status TEXT DEFAULT 'candidate' CHECK (status IN ('candidate', 'in_progress', 'blocked', 'pending_parts', 'completed')),
  assigned_to UUID REFERENCES auth.users(id),
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  completed_by UUID REFERENCES auth.users(id),
  outcome TEXT CHECK (outcome IN ('resolved', 'partial', 'unsuccessful')),
  time_spent_hours DECIMAL(5,2),
  last_activity TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_work_orders_yacht_status ON pms_work_orders(yacht_id, status);
CREATE INDEX idx_work_orders_equipment ON pms_work_orders(equipment_id, status);
CREATE INDEX idx_work_orders_assigned ON pms_work_orders(assigned_to, status);

-- Work Order Notes
CREATE TABLE pms_work_order_notes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  work_order_id UUID NOT NULL REFERENCES pms_work_orders(id) ON DELETE CASCADE,
  category TEXT DEFAULT 'update' CHECK (category IN ('update', 'diagnosis', 'action', 'issue')),
  content TEXT NOT NULL,
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wo_notes_wo ON pms_work_order_notes(work_order_id, created_at DESC);

-- Parts
CREATE TABLE pms_parts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  name TEXT NOT NULL,
  part_number TEXT,
  manufacturer TEXT,
  model TEXT,
  category TEXT,
  location TEXT,
  stock_level INTEGER DEFAULT 0,
  critical_threshold INTEGER DEFAULT 0,
  low_threshold INTEGER DEFAULT 5,
  minimum_threshold INTEGER DEFAULT 10,
  unit_cost DECIMAL(10,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_parts_yacht ON pms_parts(yacht_id);
CREATE INDEX idx_parts_stock ON pms_parts(yacht_id, stock_level);
CREATE INDEX idx_parts_critical ON pms_parts(yacht_id, stock_level, critical_threshold) WHERE stock_level <= critical_threshold;

-- Work Order Parts (Planning)
CREATE TABLE pms_work_order_parts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  work_order_id UUID NOT NULL REFERENCES pms_work_orders(id) ON DELETE CASCADE,
  part_id UUID NOT NULL REFERENCES pms_parts(id),
  quantity_planned INTEGER NOT NULL,
  quantity_used INTEGER DEFAULT 0,
  added_by UUID NOT NULL REFERENCES auth.users(id),
  added_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wo_parts_wo ON pms_work_order_parts(work_order_id);

-- Inventory Transactions (Usage)
CREATE TABLE pms_inventory_transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  part_id UUID NOT NULL REFERENCES pms_parts(id),
  transaction_type TEXT NOT NULL CHECK (transaction_type IN ('receive', 'usage', 'adjustment', 'transfer')),
  quantity INTEGER NOT NULL,  -- Positive for receive, negative for usage
  work_order_id UUID REFERENCES pms_work_orders(id),
  location TEXT,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT
);

CREATE INDEX idx_inventory_tx_part ON pms_inventory_transactions(part_id, timestamp DESC);
CREATE INDEX idx_inventory_tx_wo ON pms_inventory_transactions(work_order_id);

-- Documents
CREATE TABLE pms_documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID REFERENCES yachts(id),  -- NULL for manufacturer manuals
  title TEXT NOT NULL,
  manufacturer TEXT,
  model TEXT,
  document_type TEXT CHECK (document_type IN ('manual', 'procedure', 'schematic', 'certificate')),
  storage_path TEXT NOT NULL,  -- Supabase storage path
  upload_date TIMESTAMPTZ DEFAULT NOW(),
  uploaded_by UUID REFERENCES auth.users(id)
);

-- Document Chunks (For search + context)
CREATE TABLE pms_document_chunks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id UUID NOT NULL REFERENCES pms_documents(id) ON DELETE CASCADE,
  page_number INTEGER,
  section_title TEXT,
  content TEXT NOT NULL,
  embedding VECTOR(1536),  -- For semantic search
  fault_code_refs TEXT[],  -- Array of fault codes mentioned
  equipment_refs TEXT[],   -- Array of equipment names mentioned
  part_refs TEXT[]         -- Array of part names mentioned
);

CREATE INDEX idx_doc_chunks_doc ON pms_document_chunks(document_id);
CREATE INDEX idx_doc_chunks_embedding ON pms_document_chunks USING ivfflat (embedding vector_cosine_ops);
```

#### 9.2 Handover Tables

```sql
-- Handover (Parent)
CREATE TABLE pms_handover (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  shift_date DATE NOT NULL,
  shift_period TEXT CHECK (shift_period IN ('day', 'night', '0800-2000', '2000-0800')),
  created_by UUID NOT NULL REFERENCES auth.users(id),
  published_at TIMESTAMPTZ,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  snapshot JSONB,  -- Immutable copy after publish
  signed_by UUID REFERENCES auth.users(id),
  signed_at TIMESTAMPTZ
);

CREATE INDEX idx_handover_yacht_date ON pms_handover(yacht_id, shift_date DESC);

-- Handover Items
CREATE TABLE pms_handover_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  handover_id UUID REFERENCES pms_handover(id) ON DELETE CASCADE,
  yacht_id UUID NOT NULL REFERENCES yachts(id),

  -- Source
  source_type TEXT NOT NULL CHECK (source_type IN ('work_order', 'fault', 'equipment', 'document', 'inventory', 'manual_note')),
  source_id UUID,  -- Polymorphic reference

  -- Ownership
  owner_id UUID NOT NULL REFERENCES auth.users(id),
  owner_name TEXT NOT NULL,

  -- Risk & Priority
  risk_category TEXT CHECK (risk_category IN ('safety_risk', 'equipment_damage', 'operational_delay', 'regulatory_issue', 'other')),
  priority INTEGER DEFAULT 3 CHECK (priority BETWEEN 1 AND 3),  -- 1=urgent, 2=high, 3=normal

  -- Content
  title TEXT NOT NULL,
  summary_text TEXT NOT NULL,
  next_action TEXT NOT NULL,

  -- Status
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'acknowledged', 'archived')),

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  published_at TIMESTAMPTZ,
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by UUID REFERENCES auth.users(id),
  archived_at TIMESTAMPTZ,

  -- Immutability flag
  is_published BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_handover_items_handover ON pms_handover_items(handover_id, status);
CREATE INDEX idx_handover_items_owner ON pms_handover_items(owner_id, status);
CREATE INDEX idx_handover_items_priority ON pms_handover_items(yacht_id, priority, created_at DESC);
```

#### 9.3 Shopping List & Procurement Tables

```sql
-- Shopping List Items
CREATE TABLE pms_shopping_list (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  part_id UUID REFERENCES pms_parts(id),  -- NULL for candidate parts
  candidate_part_name TEXT,  -- If part_id NULL, this is required
  quantity INTEGER NOT NULL,

  -- Source trigger (audit trail)
  source_type TEXT CHECK (source_type IN ('inventory_low', 'work_order_usage', 'receiving_discrepancy', 'manual_add')),
  source_id UUID,  -- work_order_id, receiving_item_id, etc.

  -- Status
  state TEXT DEFAULT 'CANDIDATE' CHECK (state IN (
    'CANDIDATE',           -- Created but not reviewed
    'ACTIVE',             -- Under review by HOD
    'COMMITTED',          -- Approved and ordered
    'PARTIALLY_FULFILLED', -- Some received
    'FULFILLED',          -- All received
    'INSTALLED',          -- Installed immediately (skip inventory)
    'MISSING'             -- Not received / damaged
  )),

  -- Order linkage
  purchase_order_id UUID REFERENCES pms_purchase_orders(id),

  -- Metadata
  supplier TEXT,
  urgency TEXT CHECK (urgency IN ('normal', 'high', 'critical')),
  notes TEXT,

  -- Audit
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  approved_by UUID REFERENCES auth.users(id),
  approved_at TIMESTAMPTZ,
  ordered_at TIMESTAMPTZ,

  -- Finance boundary
  committed_cost DECIMAL(10,2),  -- Order issued
  actual_cost DECIMAL(10,2)      -- Received/installed
);

CREATE INDEX idx_shopping_list_yacht_state ON pms_shopping_list(yacht_id, state);
CREATE INDEX idx_shopping_list_part ON pms_shopping_list(part_id, state);
CREATE INDEX idx_shopping_list_order ON pms_shopping_list(purchase_order_id);

-- Purchase Orders
CREATE TABLE pms_purchase_orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  po_number TEXT NOT NULL UNIQUE,
  supplier_name TEXT NOT NULL,
  order_date DATE NOT NULL,
  expected_delivery DATE,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'ordered', 'partial', 'fulfilled', 'cancelled')),
  total_amount DECIMAL(10,2),
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_purchase_orders_yacht ON pms_purchase_orders(yacht_id, status);
```

#### 9.4 Receiving Tables

```sql
-- Receiving Sessions
CREATE TABLE pms_receiving_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  purchase_order_id UUID REFERENCES pms_purchase_orders(id),

  -- Source
  packing_slip_image TEXT[],  -- Array of Supabase storage paths
  packing_slip_ocr_text TEXT,

  -- Status
  status TEXT DEFAULT 'CANDIDATE' CHECK (status IN ('CANDIDATE', 'ACTIVE', 'REVIEW', 'COMMITTED')),

  -- Audit
  created_by UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  committed_at TIMESTAMPTZ,
  committed_by UUID REFERENCES auth.users(id)
);

CREATE INDEX idx_receiving_sessions_yacht ON pms_receiving_sessions(yacht_id, status);

-- Receiving Items
CREATE TABLE pms_receiving_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  receiving_session_id UUID NOT NULL REFERENCES pms_receiving_sessions(id) ON DELETE CASCADE,

  -- Matching
  shopping_list_item_id UUID REFERENCES pms_shopping_list(id),
  part_id UUID REFERENCES pms_parts(id),
  candidate_part_name TEXT,

  -- Quantities
  expected_quantity INTEGER,
  delivered_quantity INTEGER,

  -- Verification
  checked BOOLEAN DEFAULT FALSE,  -- Checkbox = truth

  -- Discrepancy
  status TEXT CHECK (status IN ('ok', 'missing', 'damaged', 'incorrect')),
  discrepancy_notes TEXT,
  discrepancy_photos TEXT[],  -- Supabase paths

  -- Installation
  installed BOOLEAN DEFAULT FALSE,
  work_order_id UUID REFERENCES pms_work_orders(id),

  -- Storage
  location TEXT,

  -- Audit
  checked_by UUID REFERENCES auth.users(id),
  checked_at TIMESTAMPTZ
);

CREATE INDEX idx_receiving_items_session ON pms_receiving_items(receiving_session_id);
CREATE INDEX idx_receiving_items_checked ON pms_receiving_items(receiving_session_id, checked);
```

#### 9.5 Action Registry Table

```sql
-- Action Registry (Configuration)
CREATE TABLE pms_action_registry (
  id TEXT PRIMARY KEY,  -- e.g., 'create_work_order_from_fault'
  action_type TEXT NOT NULL CHECK (action_type IN ('read', 'mutate', 'situational')),
  priority TEXT NOT NULL CHECK (priority IN ('p0', 'p1', 'p2')),
  name TEXT NOT NULL,
  description TEXT,

  -- Entry conditions (JSON config)
  entry_conditions JSONB,  -- e.g., {"entity_types": ["fault"], "requires": ["equipment_id"]}

  -- Pre-fill template (JSON)
  prefill_template JSONB,  -- e.g., {"title": "${equipment.name} - ${fault.code}"}

  active BOOLEAN DEFAULT TRUE
);

-- Example data
INSERT INTO pms_action_registry (id, action_type, priority, name, entry_conditions, prefill_template) VALUES
('show_manual_section', 'read', 'p0', 'View Manual Section',
  '{"entity_types": ["fault", "equipment"], "requires": {"equipment.manual_available": true}}',
  '{"document_id": "${equipment.manual_document_id}", "section": "${fault.code}"}'),

('create_work_order_from_fault', 'mutate', 'p0', 'Create Work Order',
  '{"entity_types": ["fault"], "excludes": {"fault.work_order_id": "NOT NULL"}}',
  '{"title": "${equipment.name} - ${fault.code}", "equipment_id": "${fault.equipment_id}", "priority": "${fault.severity}"}');
```

#### 9.6 Audit Log Table

```sql
-- Universal Audit Log
CREATE TABLE pms_audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID REFERENCES yachts(id),

  -- Entity
  entity_type TEXT NOT NULL,  -- 'work_order', 'fault', 'inventory', etc.
  entity_id UUID NOT NULL,

  -- Action
  action TEXT NOT NULL,  -- 'created', 'updated', 'completed', 'logged_parts', etc.

  -- Context
  details JSONB,  -- Flexible JSON for action-specific data

  -- User
  user_id UUID NOT NULL REFERENCES auth.users(id),
  user_name TEXT NOT NULL,

  -- Timestamp
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_entity ON pms_audit_log(entity_type, entity_id, timestamp DESC);
CREATE INDEX idx_audit_log_yacht ON pms_audit_log(yacht_id, timestamp DESC);
CREATE INDEX idx_audit_log_user ON pms_audit_log(user_id, timestamp DESC);
```

---

## 10. Implementation Rules

### 10.1 Action Offering Algorithm

```typescript
/**
 * Core algorithm for determining which actions to offer
 *
 * Inputs:
 * - User query (optional)
 * - Current entity (optional)
 * - Current situation state (optional)
 * - User role
 *
 * Output:
 * - List of available actions with pre-fill data
 */
function getAvailableActions(context: ActionContext): AvailableAction[] {
  const actions: AvailableAction[] = [];

  // Step 1: If user query exists, parse intent
  if (context.query) {
    const intent = parseQueryIntent(context.query);

    // Explicit action query → Direct action offering
    if (intent.type === 'action' && intent.confidence === 'explicit') {
      const actionIds = mapIntentToActionIds(intent.action_keywords);
      actionIds.forEach(id => {
        actions.push(buildAction(id, context));
      });
      return actions;  // Return early for explicit actions
    }
  }

  // Step 2: Entity-based action offering
  if (context.entity) {
    const entityActions = getActionsForEntity(context.entity);
    entityActions.forEach(actionConfig => {
      // Evaluate entry conditions
      if (evaluateEntryConditions(actionConfig.entry_conditions, context.entity)) {
        actions.push(buildAction(actionConfig.id, context));
      }
    });
  }

  // Step 3: Situational action offering
  if (context.situation) {
    const situationActions = getActionsForSituation(context.situation);
    situationActions.forEach(actionConfig => {
      actions.push(buildAction(actionConfig.id, context));
    });
  }

  // Step 4: Threshold-based action offering
  if (context.entity) {
    const thresholdActions = evaluateThresholds(context.entity);
    actions.push(...thresholdActions);
  }

  // Step 5: Role-based filtering
  return actions.filter(action => userHasPermission(context.user_role, action.id));
}

// Entry condition evaluation (simple boolean logic)
function evaluateEntryConditions(conditions: any, entity: any): boolean {
  if (!conditions) return true;

  // Check required fields
  if (conditions.requires) {
    for (const [field, value] of Object.entries(conditions.requires)) {
      const entityValue = getNestedProperty(entity, field);
      if (value === 'NOT NULL' && !entityValue) return false;
      if (value !== 'NOT NULL' && entityValue !== value) return false;
    }
  }

  // Check exclusions
  if (conditions.excludes) {
    for (const [field, value] of Object.entries(conditions.excludes)) {
      const entityValue = getNestedProperty(entity, field);
      if (value === 'NOT NULL' && entityValue) return false;
      if (value !== 'NOT NULL' && entityValue === value) return false;
    }
  }

  return true;
}
```

### 10.2 Pre-fill Engine

```typescript
/**
 * Pre-fills action forms using entity data
 *
 * Uses template strings with variable substitution
 * No ML, just simple data mapping
 */
function buildPreFillData(actionId: string, context: ActionContext): Record<string, any> {
  const template = getPreFillTemplate(actionId);
  if (!template) return {};

  const preFill: Record<string, any> = {};

  for (const [field, templateStr] of Object.entries(template)) {
    // Simple variable substitution: ${entity.field}
    preFill[field] = substituteVariables(templateStr, context);
  }

  return preFill;
}

// Example templates (from action_registry)
const preFillTemplates = {
  create_work_order_from_fault: {
    title: '${equipment.name} - ${fault.code}',
    equipment_id: '${fault.equipment_id}',
    location: '${equipment.location}',
    description: '${fault.description}\n\nOccurrences: ${fault.occurrence_count} in last 30 days',
    priority: '${fault.severity}',
  },

  add_to_handover: {
    title: {
      fault: '${equipment.name} - ${fault.code}',
      work_order: 'WO-${work_order.number} - ${work_order.title}',
      equipment: '${equipment.name}',
    },
    category: {
      fault: 'ongoing_fault',
      work_order: 'work_in_progress',
      equipment: 'equipment_status',
    },
    priority: {
      fault: '${fault.severity === "critical" ? "urgent" : "normal"}',
      work_order: '${work_order.priority}',
    },
  },
};
```

### 10.3 Mutation Pipeline

```typescript
/**
 * Standard mutation flow for all MUTATE actions
 *
 * 1. Pre-fill form
 * 2. User edits (optional)
 * 3. Preview (show effects)
 * 4. User confirms
 * 5. Execute mutation
 * 6. Audit log
 * 7. Confirmation
 */
async function executeMutation(actionId: string, formData: any, context: ActionContext): Promise<Result> {
  // Step 1: Validate
  const validation = validateFormData(actionId, formData);
  if (!validation.valid) {
    return { success: false, errors: validation.errors };
  }

  // Step 2: Check duplicate (if applicable)
  if (shouldCheckDuplicate(actionId)) {
    const duplicate = await checkDuplicate(actionId, formData, context);
    if (duplicate) {
      return { success: false, duplicate, prompt: 'duplicate_warning' };
    }
  }

  // Step 3: Execute mutation (transaction)
  const result = await db.transaction(async (tx) => {
    // Main mutation
    const entity = await createOrUpdateEntity(tx, actionId, formData, context);

    // Side effects (if any)
    await executeSideEffects(tx, actionId, entity, formData, context);

    // Audit log
    await createAuditLog(tx, {
      entity_type: getEntityType(actionId),
      entity_id: entity.id,
      action: actionId,
      details: formData,
      user_id: context.user_id,
      user_name: context.user_name,
    });

    return entity;
  });

  // Step 4: Return success
  return { success: true, entity: result };
}
```

### 10.4 Situational State Transitions

```typescript
/**
 * State machine for situational actions
 */
interface StateMachine {
  currentState: string;
  allowedTransitions: Record<string, string[]>;
  allowedActions: Record<string, string[]>;
}

const receivingStateMachine: StateMachine = {
  currentState: 'IDLE',
  allowedTransitions: {
    IDLE: ['CANDIDATE'],
    CANDIDATE: ['ACTIVE', 'IDLE'],
    ACTIVE: ['REVIEW', 'CANDIDATE'],
    REVIEW: ['COMMITTED', 'ACTIVE'],
    COMMITTED: ['IDLE'],
  },
  allowedActions: {
    IDLE: ['scan_packing_slip', 'select_order'],
    CANDIDATE: ['confirm_order', 'upload_more', 'cancel'],
    ACTIVE: ['check_item', 'edit_quantity', 'mark_discrepancy', 'mark_installed'],
    REVIEW: ['view_summary', 'back_to_active', 'commit'],
    COMMITTED: ['view_receipt', 'download_labels'],
  },
};

function transitionState(currentState: string, action: string, stateMachine: StateMachine): string {
  const allowed = stateMachine.allowedTransitions[currentState];
  const nextState = getNextStateForAction(action);

  if (!allowed.includes(nextState)) {
    throw new Error(`Invalid transition: ${currentState} → ${nextState} via ${action}`);
  }

  return nextState;
}
```

---

## Summary: The Complete Flow

```
USER ACTION
     ↓
┌────────────────────────────────────────────────────────┐
│ 1. INTENT PARSING                                      │
│    - Query keywords → Action intent                    │
│    - Entity navigation → Entity context                │
│    - Document viewing → Reference extraction           │
└────────────────┬───────────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────────┐
│ 2. CONTEXT BUILDING                                    │
│    - Current entity (if any)                           │
│    - Current situation state (if any)                  │
│    - User role & permissions                           │
│    - Threshold evaluations                             │
└────────────────┬───────────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────────┐
│ 3. ACTION OFFERING ENGINE                              │
│    - Query action registry                             │
│    - Evaluate entry conditions                         │
│    - Filter by role permissions                        │
│    - Build pre-fill data                               │
└────────────────┬───────────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────────┐
│ 4. USER INTERACTION                                    │
│    - Actions displayed (search bar / dropdown / page)  │
│    - User selects action                               │
│    - Form opens (pre-filled)                           │
│    - User edits (optional)                             │
│    - Preview shown (for mutations)                     │
└────────────────┬───────────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────────┐
│ 5. EXECUTION                                           │
│    - Validate input                                    │
│    - Check duplicates (if applicable)                  │
│    - Execute mutation (transaction)                    │
│    - Create audit log                                  │
│    - Trigger side effects (notifications, etc.)        │
└────────────────┬───────────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────────┐
│ 6. CONFIRMATION & STATE UPDATE                         │
│    - Show success message                              │
│    - Update entity state (if applicable)               │
│    - Update situation state (if applicable)            │
│    - Return to previous view or entity page            │
└────────────────────────────────────────────────────────┘
```

---

**END OF ARCHITECTURE SPECIFICATION**

This document defines the complete action system. Implementation must adhere to these rules to maintain system integrity and user trust.
