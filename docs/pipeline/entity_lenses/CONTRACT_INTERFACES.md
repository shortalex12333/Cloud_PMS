# Contract Interfaces

**Status**: v1 - PRODUCTION READY
**Last Updated**: 2026-01-25
**Purpose**: JSON schemas for RAG-to-Lens data contracts

---

# OVERVIEW

These interfaces define the data contracts between:
1. **RAG System** → Entity Lens Selection
2. **Entity Lens** → Action Execution
3. **Action Execution** → Audit/Ledger System
4. **Backend** → Frontend Rendering

---

# 1. RAG RESPONSE INTERFACE

When the RAG system processes a user query, it returns structured entity matches.

```typescript
interface RAGResponse {
  /** Unique execution ID for tracing */
  execution_id: string;  // UUID

  /** Original user query */
  query: string;

  /** Detected query intent */
  intent: QueryIntent;

  /** Matched entities from knowledge graph/vector search */
  entities: EntityMatch[];

  /** Relevant document chunks (if any) */
  chunks: ChunkResult[];

  /** Overall confidence score */
  confidence: number;  // 0.0 - 1.0

  /** Processing metadata */
  metadata: {
    processing_time_ms: number;
    model_used: string;
    yacht_id: string;  // UUID
    user_id: string;   // UUID
  };
}

interface QueryIntent {
  /** Primary intent classification */
  type:
    | 'lookup'           // "Show me X"
    | 'status_check'     // "What's the status of X"
    | 'action_request'   // "Create/Update/Delete X"
    | 'history_query'    // "Faults on X"
    | 'search'           // "Find X"
    | 'comparison'       // "Compare X and Y"
    | 'recommendation';  // "What should I do about X"

  /** Confidence for this intent */
  confidence: number;  // 0.0 - 1.0

  /** If action_request, what action */
  action_hint?: string;  // e.g., "complete_work_order", "add_note"
}

interface EntityMatch {
  /** Entity type (determines lens) */
  entity_type: EntityType;

  /** Entity ID */
  entity_id: string;  // UUID

  /** Display name for results */
  display_name: string;

  /** Match confidence */
  confidence: number;  // 0.0 - 1.0

  /** Match reason (for debugging) */
  match_reason: 'exact' | 'partial' | 'semantic' | 'related';

  /** Preview data for result card */
  preview: Record<string, any>;
}

interface ChunkResult {
  /** Document ID */
  document_id: string;  // UUID

  /** Chunk content */
  content: string;

  /** Chunk metadata */
  metadata: {
    page_number?: number;
    section?: string;
    relevance_score: number;
  };
}

type EntityType =
  | 'work_order'
  | 'equipment'
  | 'fault'
  | 'part'
  | 'shopping_list_item'
  | 'receiving_event'
  | 'document'
  | 'crew'
  | 'certificate';
```

---

# 2. ENTITY CONTEXT INTERFACE

When a lens receives a focused entity, this context is provided.

```typescript
interface EntityContext {
  /** Which lens is active */
  lens: LensName;

  /** The focused entity */
  entity: {
    type: EntityType;
    id: string;  // UUID
  };

  /** Related entities (for escape hatches) */
  related: RelatedEntity[];

  /** If user indicated action intent */
  action_intent?: ActionType;

  /** User context */
  user: {
    id: string;      // UUID
    yacht_id: string;  // UUID
    role: UserRole;
    name: string;
  };

  /** Session context */
  session: {
    id: string;      // UUID
    device_type: 'desktop' | 'tablet' | 'mobile';
    ip_address?: string;
  };
}

interface RelatedEntity {
  /** Relationship type */
  relationship: 'parent' | 'child' | 'linked' | 'reference';

  /** Related entity type */
  entity_type: EntityType;

  /** Related entity ID */
  entity_id: string;  // UUID

  /** Display name */
  display_name: string;

  /** FK column that links them */
  via_column: string;
}

type LensName =
  | 'work_order'
  | 'equipment'
  | 'fault'
  | 'part'
  | 'shopping_list'
  | 'receiving'
  | 'document'
  | 'crew'
  | 'certificate';

type UserRole =
  | 'captain'
  | 'chief_engineer'
  | 'eto'
  | 'manager'
  | 'purser'
  | 'deck'
  | 'interior'
  | 'crew'
  | 'vendor';
```

---

# 3. ACTION REQUEST INTERFACE

When a user triggers an action on a focused entity.

```typescript
interface ActionRequest {
  /** Action being performed */
  action: ActionType;

  /** Target entity */
  entity_type: EntityType;
  entity_id: string;  // UUID

  /** User-provided field values */
  fields: Record<string, any>;

  /** User context */
  user_id: string;   // UUID
  yacht_id: string;  // UUID

  /** Session context for audit */
  session: {
    id: string;
    ip_address?: string;
    device_type: string;
    app_version?: string;
  };

  /** If signature required, included here */
  signature?: SignaturePayload;
}

interface SignaturePayload {
  /** Base64 encoded signature image */
  signature_hash: string;

  /** User who signed */
  signed_by: string;  // UUID

  /** When signed */
  signed_at: string;  // ISO timestamp

  /** User's role at time of signing */
  role_at_signing: UserRole;

  /** Type of signature action */
  signature_type: 'approval' | 'completion' | 'verification' | 'witness';
}

type ActionType =
  // Work Order Actions
  | 'create_work_order'
  | 'update_work_order'
  | 'complete_work_order'
  | 'archive_work_order'
  | 'add_work_order_note'
  | 'assign_work_order'
  // Equipment Actions
  | 'update_equipment_status'
  | 'add_equipment_note'
  | 'create_work_order_for_equipment'
  // Fault Actions
  | 'add_fault_note'
  | 'attach_file_to_fault'
  // Part Actions
  | 'adjust_stock_quantity'
  | 'record_part_consumption'
  | 'add_to_shopping_list'
  // Shopping List Actions
  | 'approve_shopping_list_item'
  | 'reject_shopping_list_item'
  | 'promote_candidate_to_part'
  // Receiving Actions
  | 'start_receiving_event'
  | 'add_line_item'
  | 'complete_receiving_event'
  | 'verify_line_item'
  // Certificate Actions
  | 'create_certificate'
  | 'update_certificate'
  | 'supersede_certificate'
  // Common Actions
  | 'add_note'
  | 'attach_file';
```

---

# 4. ACTION RESPONSE INTERFACE

Result of executing an action.

```typescript
interface ActionResponse {
  /** Did action succeed */
  success: boolean;

  /** Audit log entry ID */
  audit_log_id?: string;  // UUID

  /** Updated entity state (if success) */
  entity_state?: EntityState;

  /** Ledger event (for real-time updates) */
  ledger_event?: LedgerEvent;

  /** If failed, error details */
  errors?: ActionError[];

  /** Performance metadata */
  metadata: {
    execution_time_ms: number;
    tables_affected: string[];
  };
}

interface EntityState {
  /** Entity type */
  entity_type: EntityType;

  /** Entity ID */
  entity_id: string;  // UUID

  /** Current state after action */
  current: Record<string, any>;

  /** What changed */
  changed_fields: string[];
}

interface LedgerEvent {
  /** Event type for UI */
  event: string;  // e.g., 'work_order_completed'

  /** Human-readable message */
  message: string;

  /** Entity reference */
  entity_type: EntityType;
  entity_id: string;  // UUID

  /** Who performed action */
  user_id: string;    // UUID
  user_name: string;

  /** When it happened */
  timestamp: string;  // ISO timestamp

  /** Link to entity */
  link: string;  // e.g., '/work-orders/uuid'

  /** Additional context */
  metadata?: Record<string, any>;
}

interface ActionError {
  /** Error code */
  code:
    | 'VALIDATION_ERROR'
    | 'PERMISSION_DENIED'
    | 'NOT_FOUND'
    | 'CONFLICT'
    | 'BUSINESS_RULE_VIOLATION'
    | 'DATABASE_ERROR';

  /** Human-readable message */
  message: string;

  /** Which field caused error (if applicable) */
  field?: string;

  /** Additional details */
  details?: Record<string, any>;
}
```

---

# 5. FRONTEND RENDER INSTRUCTION

How the frontend should display a focused entity.

```typescript
interface RenderInstruction {
  /** Which component to render */
  component: ComponentType;

  /** Props for the component */
  props: EntityRenderProps;

  /** Available context menu actions */
  context_menu: ContextMenuItem[];

  /** Available escape hatches */
  escape_hatches: EscapeHatch[];

  /** UI hints */
  hints: UIHints;
}

interface EntityRenderProps {
  /** Core entity data */
  entity: Record<string, any>;

  /** Related data (pre-fetched) */
  related: {
    [key: string]: Record<string, any> | Record<string, any>[];
  };

  /** Computed fields */
  computed: {
    [key: string]: any;
  };
}

interface ContextMenuItem {
  /** Action type */
  action: ActionType;

  /** Display label */
  label: string;

  /** Icon name */
  icon: string;

  /** Is action enabled */
  enabled: boolean;

  /** If disabled, why */
  disabled_reason?: string;

  /** Does action require signature */
  requires_signature: boolean;

  /** Does action require confirmation */
  requires_confirmation: boolean;
}

interface EscapeHatch {
  /** Target lens */
  target_lens: LensName;

  /** Target entity type */
  target_entity_type: EntityType;

  /** Display label */
  label: string;  // e.g., "View Equipment"

  /** Icon name */
  icon: string;

  /** Is escape hatch available (FK not null) */
  available: boolean;

  /** If not available, why */
  unavailable_reason?: string;

  /** Target entity preview (if available) */
  preview?: {
    id: string;
    display_name: string;
  };
}

interface UIHints {
  /** Should show attention indicator */
  show_attention: boolean;

  /** Attention level */
  attention_level?: 'info' | 'warning' | 'critical';

  /** Status badge color */
  status_color?: string;

  /** Priority badge */
  priority_badge?: string;

  /** Is entity editable by current user */
  is_editable: boolean;

  /** Is entity locked */
  is_locked: boolean;
}

type ComponentType =
  | 'WorkOrderDetail'
  | 'EquipmentDetail'
  | 'FaultDetail'
  | 'PartDetail'
  | 'ShoppingListItemDetail'
  | 'ReceivingEventDetail'
  | 'DocumentDetail'
  | 'CrewProfileDetail'
  | 'CertificateDetail';
```

---

# 6. AUDIT LOG ENTRY FORMAT

Standard format for all audit log entries.

```typescript
interface AuditLogEntry {
  /** Entry ID */
  id: string;  // UUID

  /** Yacht ID */
  yacht_id: string;  // UUID

  /** What entity was affected */
  entity_type: string;  // e.g., 'work_order', 'fault'
  entity_id: string;    // UUID

  /** What action was performed */
  action: string;  // e.g., 'complete_work_order', 'add_note'

  /** Who performed action */
  user_id: string;  // UUID

  /** State before change (null for INSERT) */
  old_values: Record<string, any> | null;

  /** State after change */
  new_values: Record<string, any>;

  /** Signature (empty object {} if not required) */
  signature: SignaturePayload | {};

  /** Session metadata */
  metadata: {
    session_id: string;
    ip_address?: string;
    device_type?: string;
    app_version?: string;
    source?: string;  // e.g., 'equipment_lens', 'api'
  };

  /** When action occurred */
  created_at: string;  // ISO timestamp
}
```

---

# VALIDATION RULES

## Field Classification Mapping

| Classification | Validation Rule |
|----------------|-----------------|
| REQUIRED | Must be provided, non-null |
| OPTIONAL | May be null or omitted |
| CONTEXT | Derived from current state, not user input |
| BACKEND_AUTO | Set by backend, user cannot modify |
| DEPRECATED | Ignored, not written |

## Signature Rules

| Condition | Signature Required |
|-----------|-------------------|
| Work Order completion | Yes |
| Large stock adjustment (>50%) | Yes |
| Certificate creation | No (but tracked) |
| Note addition | No |
| Receiving event completion | No (but tracked) |

---

# EXAMPLE FLOWS

## Example 1: User queries "complete WO-2026-0045"

**1. RAG Response**:
```json
{
  "execution_id": "abc123",
  "query": "complete WO-2026-0045",
  "intent": {
    "type": "action_request",
    "confidence": 0.95,
    "action_hint": "complete_work_order"
  },
  "entities": [{
    "entity_type": "work_order",
    "entity_id": "uuid-here",
    "display_name": "WO-2026-0045: Generator Oil Change",
    "confidence": 0.98,
    "match_reason": "exact"
  }],
  "confidence": 0.96
}
```

**2. Action Request**:
```json
{
  "action": "complete_work_order",
  "entity_type": "work_order",
  "entity_id": "uuid-here",
  "fields": {
    "completion_notes": "Oil changed, filter replaced"
  },
  "user_id": "user-uuid",
  "yacht_id": "yacht-uuid",
  "signature": {
    "signature_hash": "base64...",
    "signed_by": "user-uuid",
    "signed_at": "2026-01-25T10:30:00Z",
    "role_at_signing": "chief_engineer",
    "signature_type": "completion"
  }
}
```

**3. Action Response**:
```json
{
  "success": true,
  "audit_log_id": "audit-uuid",
  "entity_state": {
    "entity_type": "work_order",
    "entity_id": "uuid-here",
    "current": {
      "status": "completed",
      "completed_at": "2026-01-25T10:30:00Z",
      "completed_by": "user-uuid"
    },
    "changed_fields": ["status", "completed_at", "completed_by"]
  },
  "ledger_event": {
    "event": "work_order_completed",
    "message": "WO-2026-0045 completed by John Smith",
    "entity_type": "work_order",
    "entity_id": "uuid-here",
    "user_id": "user-uuid",
    "user_name": "John Smith",
    "timestamp": "2026-01-25T10:30:00Z",
    "link": "/work-orders/uuid-here"
  }
}
```

---

**END OF CONTRACT INTERFACES**
