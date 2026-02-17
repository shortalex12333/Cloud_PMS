# CelesteOS PMS - Coding Conventions

This document defines the coding standards and patterns used across the CelesteOS codebase (TypeScript frontend, Python backend, Playwright tests).

---

## Table of Contents

1. [TypeScript Patterns](#typescript-patterns)
2. [Python Patterns](#python-patterns)
3. [Naming Conventions](#naming-conventions)
4. [Error Handling](#error-handling)
5. [Action Registry Pattern](#action-registry-pattern)
6. [Frontend Component Naming](#frontend-component-naming)

---

## TypeScript Patterns

### Type Definitions

- **Interfaces over types for public contracts**: Use `interface` for contracts that will be extended or implemented
  ```typescript
  interface MicroAction {
    action_name: string;
    label: string;
    cluster: PurposeCluster;
    card_types: CardType[];
    side_effect: SideEffectType;
    handler: string;
    requires_confirmation: boolean;
  }
  ```

- **Type aliases for unions and primitives**: Use `type` for discriminated unions, function signatures, and branded types
  ```typescript
  export type SideEffectType = 'read_only' | 'mutation_light' | 'mutation_heavy';
  export type PurposeCluster =
    | 'fix_something'
    | 'do_maintenance'
    | 'manage_equipment'
    | 'control_inventory'
    | 'communicate_status'
    | 'comply_audit'
    | 'procure_suppliers';
  ```

- **Generic types for async operations**:
  ```typescript
  interface ActionResult<T = unknown> {
    success: boolean;
    data?: T;
    error?: ActionError;
  }
  ```

### Handler Functions

- **Naming convention**: `<domain><Action>Handler` or `handle<Domain><Action>`
  ```typescript
  // From faults.ts
  async function diagnoseFault(context: ActionContext): Promise<ActionResult>
  async function suggestParts(context: ActionContext): Promise<ActionResult>
  async function createWorkOrderFromFault(context: ActionContext): Promise<ActionResult>
  ```

- **Handler file organization**: Handlers grouped by domain (faults, workOrders, inventory, etc.)
  ```
  /lib/microactions/handlers/
    ├── faults.ts
    ├── workOrders.ts
    ├── equipment.ts
    ├── inventory.ts
    ├── compliance.ts
    ├── handover.ts
    ├── hours_of_rest.ts
    ├── procurement.ts
    └── index.ts
  ```

- **Handler return patterns**:
  ```typescript
  // Success
  return { success: true, data: result };

  // Failure
  return {
    success: false,
    error: {
      code: 'VALIDATION_ERROR',
      message: 'Invalid input',
      details: { field: 'quantity', reason: 'must be positive' }
    }
  };
  ```

### Registry Patterns (TypeScript)

- **Registry organization**: Actions grouped by purpose cluster
  ```typescript
  const FIX_SOMETHING_ACTIONS: Record<string, MicroAction> = {
    diagnose_fault: { ... },
    show_manual_section: { ... },
    view_fault_history: { ... }
  };

  export const MICROACTION_REGISTRY = {
    ...FIX_SOMETHING_ACTIONS,
    ...DO_MAINTENANCE_ACTIONS,
    ...MANAGE_EQUIPMENT_ACTIONS,
    // ... etc
  };
  ```

- **Registry helpers**:
  ```typescript
  export function getAction(actionId: string): MicroAction | undefined
  export function getActionsForCardType(cardType: CardType): MicroAction[]
  export function getActionsInCluster(cluster: PurposeCluster): MicroAction[]
  ```

---

## Python Patterns

### Dataclass Usage

- **Dataclasses for data structures** with type hints:
  ```python
  from dataclasses import dataclass, field
  from typing import Optional, List, Dict, Any

  @dataclass
  class FieldMetadata:
    """Metadata for a single field in an action."""
    name: str
    classification: FieldClassification
    auto_populate_from: Optional[str] = None
    lookup_required: bool = False
    description: Optional[str] = None
    options: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
      """Convert to dictionary for JSON serialization."""
      return { ... }
  ```

- **Dataclass methods for construction**:
  ```python
  @dataclass
  class ValidationResult:
    valid: bool
    error: Optional[ValidationError] = None
    context: Optional[Dict[str, Any]] = None

    @classmethod
    def success(cls, context: Optional[Dict[str, Any]] = None) -> "ValidationResult":
      """Create a successful validation result."""
      return cls(valid=True, context=context or {})

    @classmethod
    def failure(cls, error_code: str, message: str, ...) -> "ValidationResult":
      """Create a failed validation result."""
      return cls(valid=False, error=ValidationError(...))
  ```

### Enums

- **String Enums for classification**:
  ```python
  class FieldClassification(str, Enum):
    """Field classification for auto-population."""
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    BACKEND_AUTO = "BACKEND_AUTO"
    CONTEXT = "CONTEXT"

  class ActionVariant(str, Enum):
    """Variant of action (mutation level)."""
    READ = "READ"
    MUTATE = "MUTATE"
    SIGNED = "SIGNED"
  ```

### Pydantic Models (API Contracts)

- **BaseModel for API schemas**:
  ```python
  from pydantic import BaseModel, Field, UUID4
  from datetime import datetime

  class NavigationContext(BaseModel):
    """Navigation context state (persisted in DB for audit only)."""
    id: UUID4
    yacht_id: UUID4
    created_by_user_id: UUID4
    created_at: datetime
    ended_at: Optional[datetime] = None
    active_anchor_type: str
    active_anchor_id: UUID4
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    temporal_bias: str = "now"  # now | recent | historical
  ```

### Error Handling (Python)

- **Custom exceptions**:
  ```python
  class ValidationError(Exception):
    """Raised when validation fails."""
    def __init__(self, error_code: str, message: str, field: Optional[str] = None):
      self.error_code = error_code
      self.message = message
      self.field = field
  ```

- **Exception handling in main router**:
  ```python
  try:
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
      raise HTTPException(
        status_code=401,
        detail={
          "status": "error",
          "error_code": jwt_result.error.error_code,
          "message": jwt_result.error.message,
        }
      )
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  ```

---

## Naming Conventions

### File Names

| Type | Pattern | Example |
|------|---------|---------|
| Components | PascalCase | `ContextPanel.tsx`, `DeepLinkHandler.tsx` |
| Handlers (TS) | camelCase | `faults.ts`, `workOrders.ts` |
| Services | camelCase | `supabaseClient.ts`, `emailService.ts` |
| Tests | `*-COMPREHENSIVE.spec.ts` or `*.test.ts` | `receiving-COMPREHENSIVE.spec.ts`, `registry.test.ts` |
| Python modules | snake_case | `action_router.py`, `validation_result.py` |
| API routes | kebab-case in paths | `/app/api/v1/actions/execute/route.ts` |

### Function/Method Names

- **TypeScript handlers**: `verb + noun` in camelCase
  ```typescript
  diagnoseFault()
  suggestParts()
  createWorkOrder()
  markWorkOrderComplete()
  ```

- **Python validators**: `validate_<entity>`
  ```python
  validate_jwt()
  validate_yacht_isolation()
  validate_role_permission()
  validate_required_fields()
  validate_schema()
  ```

- **Test functions**: `<scope>: <behavior>` in describe + it format
  ```typescript
  describe('Microaction Registry', () => {
    it('should have at least 57 registered actions', () => { ... });
    it('should return empty array for invalid card type', () => { ... });
  });
  ```

### Variable Names

- **Boolean prefixes**: `is`, `has`, `should`, `can`, `needs`
  ```typescript
  isActive: boolean
  hasSignatureBadge: boolean
  requiresConfirmation: boolean
  ```

- **Collection names**: Plural
  ```typescript
  const actions: MicroAction[] = getActionsForCardType('fault');
  const errors: ValidationError[] = [];
  ```

- **Enum values**: ALL_CAPS for Python, UPPER_CASE_SNAKE for values
  ```python
  REQUIRED = "REQUIRED"
  BACKEND_AUTO = "BACKEND_AUTO"
  ```

### Action Names (Consistent Across Frontend/Backend)

- **Naming rule**: `verb_noun` in snake_case
  ```
  diagnose_fault
  create_work_order
  add_work_order_note
  mark_work_order_complete
  create_receiving
  add_receiving_item
  accept_receiving
  view_fault_history
  suggest_parts
  ```

---

## Error Handling

### TypeScript Error Pattern

```typescript
interface ActionError {
  code: string;           // e.g., 'VALIDATION_ERROR', 'PERMISSION_DENIED'
  message: string;        // User-facing message
  details?: Record<string, unknown>;  // Additional context
}

interface ActionResult<T = unknown> {
  success: boolean;
  data?: T;
  error?: ActionError;
}

// Usage
if (!result.success) {
  console.error(`Action failed: ${result.error?.code} - ${result.error?.message}`);
  if (result.error?.details) {
    console.error('Details:', result.error.details);
  }
}
```

### Python Error Pattern

```python
@dataclass
class ValidationError:
  """Represents a validation error."""
  error_code: str
  message: str
  field: Optional[str] = None
  details: Optional[Dict[str, Any]] = None

  def to_dict(self) -> Dict[str, Any]:
    result = {
      "error_code": self.error_code,
      "message": self.message,
    }
    if self.field:
      result["field"] = self.field
    if self.details:
      result["details"] = self.details
    return result

@dataclass
class ValidationResult:
  valid: bool
  error: Optional[ValidationError] = None
  context: Optional[Dict[str, Any]] = None

  @classmethod
  def success(cls, context: Optional[Dict[str, Any]] = None) -> "ValidationResult":
    return cls(valid=True, context=context or {})

  @classmethod
  def failure(cls, error_code: str, message: str, ...) -> "ValidationResult":
    return cls(valid=False, error=ValidationError(...))
```

### HTTP Exception Pattern

```python
raise HTTPException(
  status_code=401,
  detail={
    "status": "error",
    "error_code": jwt_result.error.error_code,
    "message": jwt_result.error.message,
    "action": action_id,
  }
)
```

---

## Action Registry Pattern

### Python Backend (Single Source of Truth)

The Python registry in `/apps/api/action_router/registry.py` defines all available actions:

```python
class ActionDefinition:
  """Definition of a single action."""

  def __init__(
    self,
    action_id: str,              # Unique identifier (snake_case)
    label: str,                  # Human-readable label
    endpoint: str,               # Handler function path
    handler_type: HandlerType,   # INTERNAL | N8N (deprecated)
    method: str = "POST",
    allowed_roles: List[str] = None,      # ['Engineer', 'HOD', 'Manager']
    required_fields: List[str] = None,    # ['field1', 'field2']
    schema_file: str = None,              # Path to JSON schema
    domain: str = None,                   # 'receiving', 'work_orders', etc.
    variant: ActionVariant = ActionVariant.MUTATE,  # READ | MUTATE | SIGNED
    search_keywords: List[str] = None,
    field_metadata: List[FieldMetadata] = None,  # For auto-population
    prefill_endpoint: str = None,         # For two-phase actions
    storage_bucket: str = None,           # For file-producing actions
    storage_path_template: str = None,
    context_required: Dict[str, Any] = None,  # Context gating
    signature_roles_required: List[str] = None,  # For SIGNED variant
  ):
    self.action_id = action_id
    self.label = label
    # ... etc
```

#### Field Metadata System

Used for auto-population in prepare/prefill phase:

```python
@dataclass
class FieldMetadata:
  name: str
  classification: FieldClassification  # REQUIRED | OPTIONAL | BACKEND_AUTO | CONTEXT
  auto_populate_from: Optional[str] = None  # 'part', 'equipment', 'query_text', 'stock_calculation'
  lookup_required: bool = False
  description: Optional[str] = None
  options: Optional[List[str]] = None
```

#### Action Variants

```python
class ActionVariant(str, Enum):
  READ = "READ"        # Read-only (view, list) - no side effects
  MUTATE = "MUTATE"    # Standard mutation (create, update) - requires role + field validation
  SIGNED = "SIGNED"    # Requires signature (PIN+TOTP payload) - highest risk
```

#### Handler Types (Deprecated N8N)

```python
class HandlerType(str, Enum):
  INTERNAL = "internal"  # Handled by Python backend
  # N8N = "n8n"  # DEPRECATED 2026-01-27: All handlers are INTERNAL
```

### TypeScript Frontend

The TypeScript registry mirrors the Python registry's action definitions:

```typescript
interface MicroAction {
  action_name: string;        // Matches Python action_id (snake_case)
  label: string;
  cluster: PurposeCluster;    // Grouped by 7 purpose clusters
  card_types: CardType[];     // Where this action appears
  side_effect: SideEffectType;
  description: string;
  handler: string;            // Handler module reference
  requires_confirmation: boolean;
}

const FIX_SOMETHING_ACTIONS: Record<string, MicroAction> = {
  diagnose_fault: {
    action_name: 'diagnose_fault',
    label: 'Diagnose Fault',
    cluster: 'fix_something',
    card_types: ['fault'],
    side_effect: 'read_only',
    description: 'Analyze fault code and provide diagnostic guidance',
    handler: 'fault_handlers.diagnose_fault',
    requires_confirmation: false,
  },
  // ... more actions
};
```

#### Registry Export Format

```typescript
export const MICROACTION_REGISTRY = {
  ...FIX_SOMETHING_ACTIONS,
  ...DO_MAINTENANCE_ACTIONS,
  ...MANAGE_EQUIPMENT_ACTIONS,
  ...CONTROL_INVENTORY_ACTIONS,
  ...COMMUNICATE_STATUS_ACTIONS,
  ...COMPLY_AUDIT_ACTIONS,
  ...PROCURE_SUPPLIERS_ACTIONS,
};

export const TOTAL_ACTIONS = Object.keys(MICROACTION_REGISTRY).length;
```

---

## Frontend Component Naming

### Component File Naming

- **Page components** (in app/[lens]/page.tsx): Match the lens name
  ```
  /app/equipment/[id]/page.tsx
  /app/faults/[id]/page.tsx
  /app/email/inbox/page.tsx
  ```

- **Feature components**: PascalCase, descriptive names
  ```typescript
  ContextPanel.tsx     // Navigation context UI
  DeepLinkHandler.tsx  // Deep link routing logic
  EmailOverlay.tsx     // Email integration overlay
  AuthCallbackClient.tsx
  ```

- **Reusable components**: Single responsibility
  ```typescript
  Modal.tsx
  ActionButton.tsx
  SearchInput.tsx
  RoleIndicator.tsx
  ```

### Component Structure Conventions

```typescript
// Top-level component
export default function ComponentName() {
  return (
    <div data-testid="component-id">
      {/* Implementation */}
    </div>
  );
}

// With helpers
async function helperFunction() { ... }
interface ComponentProps { ... }
```

### Data Attributes for Testing

```typescript
// Standard test IDs
<button data-testid="action-button">Action</button>
<input data-testid="search-input" />
<div role="dialog" data-testid="action-modal">Modal</div>
<div data-testid="user-role">Role Badge</div>
<div data-testid="signature-badge">Requires Signature</div>
<div data-testid="toast-success">Success message</div>

// Aria roles for accessibility
<div role="dialog">Modal</div>
<div role="alert">Error message</div>
<div aria-label="role">...</div>
```

---

## Summary

| Aspect | Rule |
|--------|------|
| **TS Types** | Interface for contracts, Type for unions |
| **TS Handlers** | Grouped by domain, async functions, typed results |
| **TS Registry** | Organized by purpose cluster, Record<string, MicroAction> |
| **Python Models** | Dataclass + type hints for data, Pydantic for APIs |
| **Python Enums** | String enums for classification |
| **Functions** | `verb_noun` pattern (snake_case Python, camelCase TS) |
| **Actions** | `verb_noun` in snake_case across all platforms |
| **Files** | PascalCase (components), camelCase (utils), snake_case (Python) |
| **Errors** | Structured error objects with code, message, details |
| **Registry** | Single source of truth in Python, mirrored in TS |
| **Components** | data-testid attributes, role attributes, descriptive names |
