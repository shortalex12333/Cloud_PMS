# CelesteOS Action Router

The Action Router is the **central gateway** for all user-initiated mutations in CelesteOS.

## Overview

**Single Endpoint:** `POST /v1/actions/execute`

All frontend actions (button clicks, form submissions) go through this single endpoint, which:
1. Validates the request (JWT, permissions, data)
2. Dispatches to the appropriate handler (internal or n8n)
3. Logs the execution for audit trail
4. Returns the result

## Architecture

```
Frontend Button Click
    ↓
POST /v1/actions/execute
    ↓
Action Router
    ├── 1. JWT Validation
    ├── 2. Action Registry Lookup
    ├── 3. Yacht Isolation Check
    ├── 4. Role Permission Check
    ├── 5. Required Fields Validation
    ├── 6. JSON Schema Validation
    ├── 7. Dispatch to Handler
    │       ├── Internal (Supabase)
    │       └── n8n (Workflows)
    ├── 8. Log Execution
    └── 9. Return Result
```

## Components

### 1. Registry (`registry.py`)
- Single source of truth for all actions
- Defines 13 core actions
- Maps action_id → endpoint, handler type, roles, required fields

### 2. Validators (`validators/`)
- **JWT Validator**: Validates Supabase JWT and extracts user context
- **Yacht Validator**: Ensures yacht isolation
- **Role Validator**: Checks role permissions
- **Field Validator**: Validates required fields
- **Schema Validator**: Validates against JSON schemas

### 3. Dispatchers (`dispatchers/`)
- **Internal Dispatcher**: Fast actions via direct Supabase calls
- **n8n Dispatcher**: Complex workflows via n8n webhooks

### 4. Logger (`logger.py`)
- Logs all action executions to `action_logs` table
- Sanitizes sensitive data
- Provides action statistics

### 5. Router (`router.py`)
- Main FastAPI router with `/execute` endpoint
- Orchestrates validation → dispatch → logging flow
- Error handling and HTTP response mapping

## Usage

### Backend Integration

Add the Action Router to your FastAPI app:

```python
from fastapi import FastAPI
from src.action_router import router as action_router

app = FastAPI()
app.include_router(action_router)
```

### Frontend Integration

Execute an action from the frontend:

```typescript
import { executeAction } from '@/lib/actions/actionClient';

const result = await executeAction('add_note', {
  yacht_id: currentYacht.id,
  equipment_id: equipment.id,
  note_text: userInput,
});

if (result.status === 'success') {
  toast.success('Note added');
} else {
  toast.error(result.message);
}
```

## Request Format

```json
{
  "action": "add_note",
  "context": {
    "yacht_id": "uuid",
    "equipment_id": "uuid"
  },
  "payload": {
    "note_text": "Leak found near coolant outlet."
  }
}
```

**Headers:**
```
Authorization: Bearer <supabase-jwt-token>
Content-Type: application/json
```

## Response Format

### Success Response
```json
{
  "status": "success",
  "action": "add_note",
  "result": {
    "note_id": "uuid",
    "created_at": "2025-11-20T12:34:56Z"
  }
}
```

### Error Response
```json
{
  "status": "error",
  "error_code": "missing_field",
  "message": "Missing required field: equipment_id",
  "action": "add_note"
}
```

## HTTP Status Codes

- **200**: Success
- **400**: Missing fields, invalid schema, validation error
- **401**: Invalid/expired JWT
- **403**: Permission denied, yacht mismatch
- **404**: Action not found
- **500**: Internal server error
- **502**: Handler/n8n failure

## Supported Actions

### Notes
- `add_note` - Add note to equipment
- `add_note_to_work_order` - Add note to work order

### Work Orders
- `create_work_order` - Create new work order (n8n)
- `create_work_order_fault` - Create work order from fault (n8n)
- `close_work_order` - Close work order

### Handovers
- `add_to_handover` - Add equipment to handover (n8n)
- `add_document_to_handover` - Add document (n8n)
- `add_part_to_handover` - Add part (n8n)
- `add_predictive_to_handover` - Add predictive insight (n8n)
- `edit_handover_section` - Edit section
- `export_handover` - Export to PDF (n8n)

### Documents
- `open_document` - Get signed URL

### Inventory
- `order_part` - Order part (n8n)

## Security Features

1. **JWT Validation**: Every request validates Supabase JWT
2. **Yacht Isolation**: All actions filtered by yacht_id
3. **RBAC**: Role-based access control per action
4. **Input Sanitization**: All text fields sanitized
5. **Action Logging**: Complete audit trail
6. **Supabase RLS**: Row-Level Security as final safety net

## Environment Variables

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

# n8n Integration
N8N_BASE_URL=https://n8n.yourdomain.com
N8N_AUTH_TOKEN=your-n8n-webhook-token
```

## Testing

Run tests:
```bash
pytest backend/tests/action_router/
```

## Adding a New Action

1. **Add to Registry** (`registry.py`):
```python
"my_action": ActionDefinition(
    action_id="my_action",
    label="My Action",
    endpoint="/v1/my-endpoint",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["Engineer", "HOD"],
    required_fields=["yacht_id", "item_id"],
    schema_file="my_action.json",
),
```

2. **Add Handler** (if INTERNAL):
   - Add function to `dispatchers/internal_dispatcher.py`
   - Add to `INTERNAL_HANDLERS` dict

3. **Add Workflow** (if N8N):
   - Create n8n workflow with webhook
   - Add webhook path to `dispatchers/n8n_dispatcher.py`

4. **Add Schema** (optional):
   - Create JSON schema in `schemas/my_action.json`

5. **Test**:
   - Add unit tests
   - Add integration tests
   - Test from frontend

## Monitoring

The Action Router logs metrics to Supabase:
- Total actions executed
- Success/error rates
- Latency per action
- Top actions by volume

Use `get_action_stats(yacht_id, hours=24)` to retrieve statistics.

## Documentation

See `/docs/` for detailed documentation:
- `ACTION_ROUTER_IMPLEMENTATION.md` - Complete implementation guide
- `ACTION_INTEGRATION_AUDIT.md` - Action mapping and audit
- `TASK_9_ACTION_INTEGRATION_DELIVERY.md` - Delivery documentation

## License

Copyright © 2025 CelesteOS
