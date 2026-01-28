# Shopping List Lens v1 - Microaction Catalog

**Date**: 2026-01-28
**Status**: ✅ Production Ready
**Actions**: 5 shopping list microactions
**For**: Product managers, QA engineers, frontend engineers

---

## Table of Contents

1. [Catalog Overview](#catalog-overview)
2. [Information Dimensions](#information-dimensions)
3. [Action 1: create_shopping_list_item](#action-1-create_shopping_list_item)
4. [Action 2: approve_shopping_list_item](#action-2-approve_shopping_list_item)
5. [Action 3: reject_shopping_list_item](#action-3-reject_shopping_list_item)
6. [Action 4: promote_candidate_to_part](#action-4-promote_candidate_to_part)
7. [Action 5: view_shopping_list_history](#action-5-view_shopping_list_history)
8. [Role Permission Matrix](#role-permission-matrix)
9. [Field Reference](#field-reference)

---

## Catalog Overview

This catalog documents all 5 shopping list microactions using 12 standard information dimensions:

1. **Identification** - Action ID, label, variant
2. **Access Control** - Allowed roles, denied roles
3. **Interface** - Required fields, optional fields, endpoint
4. **Triggers** - User actions that invoke this
5. **Preconditions** - State requirements before execution
6. **Validation Rules** - Field and business logic validation
7. **Side Effects** - Database changes, notifications, integrations
8. **Related Actions** - Upstream/downstream actions
9. **Success States** - Expected outcomes when successful
10. **Error States** - Common failure modes and codes
11. **UI Surfacing** - Where/how this appears in UI
12. **Examples** - Complete request/response pairs

---

## Information Dimensions

### Dimension Descriptions

**1. Identification**
- `action_id`: Unique identifier for API calls
- `label`: Human-readable name for UI
- `variant`: Type (READ, MUTATE, SIGNED)
- `domain`: Grouping category

**2. Access Control**
- `allowed_roles`: Roles that can execute this action
- `denied_roles`: Roles explicitly blocked
- `permission_check`: How authorization is enforced

**3. Interface**
- `endpoint`: API endpoint (if action-specific)
- `required_fields`: Fields that must be present
- `optional_fields`: Fields that may be present
- `response_fields`: Fields returned on success

**4. Triggers**
- User actions that cause this to be invoked
- UI events (button clicks, form submissions)
- Background events (cron, webhooks)

**5. Preconditions**
- State requirements before action can execute
- Resource existence checks
- Status validations

**6. Validation Rules**
- Field-level validation (type, format, range)
- Business logic validation
- Cross-field dependencies

**7. Side Effects**
- Primary database writes
- Secondary database writes (audit logs, history)
- External integrations (emails, notifications)
- State transitions

**8. Related Actions**
- Upstream actions (must happen before)
- Downstream actions (commonly follow)
- Alternative actions (either/or scenarios)

**9. Success States**
- HTTP status code (200, 201, 204)
- Response body structure
- Database state after completion

**10. Error States**
- Common failure scenarios
- HTTP error codes (400, 403, 404, 409, 500)
- Error messages and recovery steps

**11. UI Surfacing**
- Page/screen location
- Button/menu placement
- Conditional visibility rules
- User journey context

**12. Examples**
- Complete curl commands
- Request/response JSON
- Error scenarios with actual messages

---

## Action 1: create_shopping_list_item

### 1. Identification

- **Action ID**: `create_shopping_list_item`
- **Label**: "Add to Shopping List"
- **Variant**: MUTATE
- **Domain**: shopping_list

### 2. Access Control

- **Allowed Roles**: crew, chief_engineer, chief_officer, captain, manager
- **Denied Roles**: None (all authenticated users can create)
- **Permission Check**: Router checks JWT role against allowed_roles list

### 3. Interface

**Endpoint**: `POST /v1/actions/execute`

**Required Fields**:
- `part_name` (string) - Name of the part/item
- `quantity_requested` (integer) - Number of units needed
- `source_type` (enum) - Origin of request: 'manual_add', 'maintenance_plan', 'fault_report', 'inspection'

**Optional Fields**:
- `part_number` (string) - Manufacturer part number
- `manufacturer` (string) - Brand/manufacturer name
- `unit` (string) - Unit of measurement (default: 'piece')
- `urgency` (enum) - Priority level: 'normal', 'urgent', 'critical' (default: 'normal')
- `notes` (text) - Additional context or instructions
- `is_candidate_part` (boolean) - Mark as candidate for parts catalog (default: false)

**Response Fields**:
- `shopping_list_item_id` (uuid) - Newly created item ID
- `part_name` (string)
- `quantity_requested` (integer)
- `status` (string) - Always 'candidate' on creation
- `created_at` (timestamp)

### 4. Triggers

**User Actions**:
- Click "Add to Shopping List" button on equipment page
- Submit shopping list request form
- Import from maintenance plan
- Create from fault report recommendation

**UI Flows**:
1. User identifies needed part during inspection
2. Opens shopping list form
3. Fills required fields (part_name, quantity, source)
4. Optionally adds part number, urgency, notes
5. Submits form

### 5. Preconditions

- ✅ User must be authenticated (valid JWT)
- ✅ User must belong to specified yacht
- ✅ User must have allowed role (crew or above)
- ✅ No existing identical item with same part_name in 'candidate' status (soft rule, allows duplicates)

### 6. Validation Rules

**Field Validation**:
- `part_name`: NOT NULL, length > 0
- `quantity_requested`: Integer > 0
- `source_type`: Must be in ['manual_add', 'maintenance_plan', 'fault_report', 'inspection']
- `urgency`: Must be in ['normal', 'urgent', 'critical']
- `unit`: String, any value (default 'piece')

**Business Logic**:
- If `source_type='maintenance_plan'`, consider linking to maintenance record
- If `is_candidate_part=true`, validate that part_name not already in pms_parts

### 7. Side Effects

**Primary Write**:
```sql
INSERT INTO pms_shopping_list_items (
    id, yacht_id, part_name, quantity_requested, source_type,
    status, created_by, created_at, updated_at
) VALUES (...);
```

**Secondary Writes**:
- `pms_shopping_list_state_history`: Log initial state (NULL → candidate)
- `pms_audit_log`: Record action execution

**Notifications**: None

**Integrations**: None

### 8. Related Actions

**Upstream**: None (entry point action)

**Downstream**:
- `approve_shopping_list_item` - HOD approves this item
- `reject_shopping_list_item` - HOD rejects this item
- `promote_candidate_to_part` - Engineer promotes to parts catalog

**Alternatives**: None

### 9. Success States

**HTTP Status**: 200 OK

**Response**:
```json
{
  "success": true,
  "action_id": "create_shopping_list_item",
  "entity_type": "shopping_list_item",
  "data": {
    "shopping_list_item_id": "abc-123",
    "part_name": "Oil Filter - Main Engine",
    "quantity_requested": 2,
    "status": "candidate",
    "created_at": "2026-01-28T12:00:00Z"
  }
}
```

**Database State**:
- New row in `pms_shopping_list_items` with status='candidate'
- New row in `pms_shopping_list_state_history` (NULL → candidate)
- New row in `pms_audit_log`

### 10. Error States

**400 Bad Request**:
- Missing required field: `{"detail": "Missing required field(s): part_name"}`
- Invalid quantity: `{"detail": "quantity_requested must be greater than 0"}`
- Invalid source_type: `{"detail": "source_type must be one of: manual_add, maintenance_plan, fault_report, inspection"}`

**403 Forbidden**:
- User role not in allowed_roles: `{"detail": "User role 'guest' not authorized for action create_shopping_list_item"}`

**404 Not Found**:
- Invalid yacht_id: `{"detail": "Yacht not found"}`

**500 Internal Server Error**:
- Database connection failure
- Unexpected exception

### 11. UI Surfacing

**Location**:
- **Equipment Page**: "Add to Shopping List" button next to each equipment item
- **Shopping List Page**: "Add Item" button in header
- **Maintenance Plan Page**: "Order Parts" button on plan details
- **Fault Report Page**: "Request Part" button on fault details

**Visibility Rules**:
- Visible to all authenticated users (crew and above)
- Disabled if user is inactive or wrong yacht
- Shows form modal on click

**User Journey**:
1. User navigates to equipment/maintenance/fault page
2. Identifies part needed
3. Clicks "Add to Shopping List" button
4. Form opens with pre-filled part_name (if from equipment context)
5. User fills quantity_requested, selects source_type
6. Optional: Adds part_number, urgency, notes
7. Clicks "Submit"
8. Success: Item appears in shopping list with status "Pending Approval"
9. Failure: Error message displays inline in form

### 12. Examples

**Example 1: Basic Request (Crew)**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_shopping_list_item",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "part_name": "Oil Filter - Main Engine",
      "quantity_requested": 2,
      "source_type": "maintenance_plan"
    }
  }'
```

**Response**:
```json
{
  "success": true,
  "action_id": "create_shopping_list_item",
  "entity_type": "shopping_list_item",
  "data": {
    "shopping_list_item_id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
    "part_name": "Oil Filter - Main Engine",
    "quantity_requested": 2,
    "status": "candidate",
    "created_at": "2026-01-28T12:00:00Z"
  }
}
```

**Example 2: Detailed Request (Chief Engineer)**
```json
{
  "action": "create_shopping_list_item",
  "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
  "payload": {
    "part_name": "Hydraulic Pump Seal Kit",
    "part_number": "HPK-2584-A",
    "manufacturer": "Caterpillar",
    "quantity_requested": 1,
    "unit": "kit",
    "source_type": "fault_report",
    "urgency": "urgent",
    "notes": "Starboard stabilizer hydraulic leak - requires immediate replacement",
    "is_candidate_part": true
  }
}
```

**Example 3: Error - Missing Required Field**
```bash
# Request missing quantity_requested
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_shopping_list_item",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "part_name": "Oil Filter",
      "source_type": "manual_add"
    }
  }'
```

**Response (400)**:
```json
{
  "detail": "Missing required field(s): quantity_requested"
}
```

---

## Action 2: approve_shopping_list_item

### 1. Identification

- **Action ID**: `approve_shopping_list_item`
- **Label**: "Approve Item"
- **Variant**: MUTATE
- **Domain**: shopping_list

### 2. Access Control

- **Allowed Roles**: chief_engineer, chief_officer, captain, manager, purser (HoD only)
- **Denied Roles**: crew, deckhand, steward, engineer, eto
- **Permission Check**:
  1. Router checks JWT role against allowed_roles
  2. Handler explicitly calls `is_hod()` RPC (defense-in-depth)

### 3. Interface

**Endpoint**: `POST /v1/actions/execute`

**Required Fields**:
- `item_id` (uuid) - Shopping list item to approve
- `quantity_approved` (integer) - Number of units approved

**Optional Fields**:
- `approval_notes` (text) - Reason or context for approval

**Response Fields**:
- `shopping_list_item_id` (uuid)
- `status` (string) - 'approved'
- `quantity_approved` (integer)
- `approved_at` (timestamp)

### 4. Triggers

**User Actions**:
- Click "Approve" button on shopping list item
- Bulk approve multiple items
- Approve from approval workflow queue

**UI Flows**:
1. HOD reviews shopping list
2. Clicks "Approve" on item row
3. Modal opens with quantity_approved pre-filled (defaults to quantity_requested)
4. Optionally adjusts quantity or adds approval notes
5. Confirms approval

### 5. Preconditions

- ✅ User must be HoD role
- ✅ Item must exist and belong to user's yacht
- ✅ Item status must be 'candidate' or 'under_review'
- ✅ Item must NOT be already approved (approved_at IS NULL)
- ✅ Item must NOT be rejected (rejected_at IS NULL)

### 6. Validation Rules

**Field Validation**:
- `item_id`: Valid UUID, item must exist
- `quantity_approved`: Integer > 0 AND ≤ quantity_requested

**Business Logic**:
- Cannot approve item with status='approved'
- Cannot approve rejected item (rejected_at NOT NULL)
- quantity_approved cannot exceed quantity_requested

**Role Enforcement**:
```python
is_hod_result = db.rpc("is_hod", {"p_user_id": user_id, "p_yacht_id": yacht_id})
if not is_hod_result.data:
    return 403 "Only HoD can approve shopping list items"
```

### 7. Side Effects

**Primary Write**:
```sql
UPDATE pms_shopping_list_items SET
    status = 'approved',
    quantity_approved = :quantity_approved,
    approved_by = :user_id,
    approved_at = NOW(),
    updated_by = :user_id,
    updated_at = NOW()
WHERE id = :item_id;
```

**Secondary Writes**:
- `pms_shopping_list_state_history`: Log transition (candidate → approved)
- `pms_audit_log`: Record approval action with user_id

**Notifications**:
- Email to requester (crew member) confirming approval
- Procurement team notification (if integrated)

**Integrations**:
- May trigger procurement workflow
- May update inventory forecast

### 8. Related Actions

**Upstream**:
- `create_shopping_list_item` - Item must be created first

**Downstream**:
- `promote_candidate_to_part` - Approved candidates can be promoted

**Alternatives**:
- `reject_shopping_list_item` - HOD can reject instead of approve

### 9. Success States

**HTTP Status**: 200 OK

**Response**:
```json
{
  "success": true,
  "action_id": "approve_shopping_list_item",
  "entity_id": "abc-123",
  "entity_type": "shopping_list_item",
  "data": {
    "shopping_list_item_id": "abc-123",
    "part_name": "Oil Filter - Main Engine",
    "status": "approved",
    "quantity_approved": 2,
    "approved_at": "2026-01-28T12:05:00Z"
  }
}
```

**Database State**:
- `pms_shopping_list_items`: status='approved', approved_by/approved_at set
- `pms_shopping_list_state_history`: New row (candidate → approved)
- `pms_audit_log`: New row with action='approve_shopping_list_item'

### 10. Error States

**400 Bad Request**:
- Invalid status: `{"detail": "Cannot approve item with status 'approved'. Expected: candidate or under_review."}`
- Already rejected: `{"detail": "Item is already rejected"}`
- Quantity too high: `{"detail": "quantity_approved (5) exceeds quantity_requested (2)"}`

**403 Forbidden**:
- User not HOD: `{"detail": "Only HoD (chief engineer, chief officer, captain, manager) can approve shopping list items"}`

**404 Not Found**:
- Item doesn't exist: `{"detail": "Shopping list item not found: abc-123"}`
- Wrong yacht: `{"detail": "Access denied"}`

### 11. UI Surfacing

**Location**:
- **Shopping List Page**: "Approve" button on each row (HOD only)
- **Approval Queue Page**: Bulk approve checkboxes
- **Item Detail Page**: "Approve" button in header

**Visibility Rules**:
- Visible only to HOD roles
- Hidden for crew/engineer roles
- Disabled if item already approved or rejected
- Shows approval history badge if approved

**User Journey**:
1. HOD navigates to Shopping List page
2. Sees items with status "Pending Approval"
3. Reviews item details (part_name, quantity, requester, notes)
4. Clicks "Approve" button
5. Modal opens with quantity_approved defaulting to quantity_requested
6. Optional: Adjusts quantity, adds approval notes
7. Clicks "Confirm Approval"
8. Success: Item status changes to "Approved", badge updates
9. Requester receives email notification

### 12. Examples

**Example 1: Basic Approval**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve_shopping_list_item",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "item_id": "6c54dadb-894c-4bb5-b547-5787b180e9d5",
      "quantity_approved": 3
    }
  }'
```

**Response (200 OK)**:
```json
{
  "success": true,
  "action_id": "approve_shopping_list_item",
  "entity_id": "6c54dadb-894c-4bb5-b547-5787b180e9d5",
  "entity_type": "shopping_list_item",
  "data": {
    "shopping_list_item_id": "6c54dadb-894c-4bb5-b547-5787b180e9d5",
    "status": "approved",
    "quantity_approved": 3,
    "approved_at": "2026-01-28T12:05:32Z"
  }
}
```

**Example 2: Approval with Notes**
```json
{
  "action": "approve_shopping_list_item",
  "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
  "payload": {
    "item_id": "abc-123",
    "quantity_approved": 2,
    "approval_notes": "Approved for Q1 procurement cycle. Order through preferred supplier XYZ Marine."
  }
}
```

**Example 3: Error - CREW Attempting Approval**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve_shopping_list_item",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "item_id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
      "quantity_approved": 2
    }
  }'
```

**Response (403 Forbidden)**:
```json
{
  "detail": "Only HoD (chief engineer, chief officer, captain, manager) can approve shopping list items"
}
```

---

## Action 3: reject_shopping_list_item

### 1. Identification

- **Action ID**: `reject_shopping_list_item`
- **Label**: "Reject Item"
- **Variant**: MUTATE
- **Domain**: shopping_list

### 2. Access Control

- **Allowed Roles**: chief_engineer, chief_officer, captain, manager, purser (HoD only)
- **Denied Roles**: crew, deckhand, steward, engineer, eto
- **Permission Check**:
  1. Router checks JWT role against allowed_roles
  2. Handler explicitly calls `is_hod()` RPC

### 3. Interface

**Endpoint**: `POST /v1/actions/execute`

**Required Fields**:
- `item_id` (uuid) - Shopping list item to reject
- `rejection_reason` (text) - Reason for rejection (NOT NULL)

**Optional Fields**:
- `rejection_notes` (text) - Additional context

**Response Fields**:
- `shopping_list_item_id` (uuid)
- `status` (string) - Remains 'candidate' or 'under_review'
- `rejected` (boolean) - true
- `rejection_reason` (text)
- `rejected_at` (timestamp)

### 4. Triggers

**User Actions**:
- Click "Reject" button on shopping list item
- Select rejection reason from dropdown
- Bulk reject multiple items

**UI Flows**:
1. HOD reviews shopping list
2. Identifies item that should not be procured
3. Clicks "Reject" button
4. Modal opens requiring rejection_reason
5. Selects reason from common options or enters custom
6. Confirms rejection

### 5. Preconditions

- ✅ User must be HoD role
- ✅ Item must exist and belong to user's yacht
- ✅ Item status must be 'candidate' or 'under_review'
- ✅ Item must NOT be already rejected (rejected_at IS NULL)
- ✅ Item must NOT be approved (status != 'approved')

### 6. Validation Rules

**Field Validation**:
- `item_id`: Valid UUID, item must exist
- `rejection_reason`: NOT NULL, length > 0

**Business Logic**:
- Cannot reject if already rejected (rejected_at NOT NULL)
- Cannot reject if approved (status='approved')
- Rejection is terminal (cannot undo)

**Role Enforcement**:
```python
is_hod_result = db.rpc("is_hod", {"p_user_id": user_id, "p_yacht_id": yacht_id})
if not is_hod_result.data:
    return 403 "Only HoD can reject shopping list items"
```

### 7. Side Effects

**Primary Write**:
```sql
UPDATE pms_shopping_list_items SET
    rejected_by = :user_id,
    rejected_at = NOW(),
    rejection_reason = :rejection_reason,
    rejection_notes = :rejection_notes,
    updated_by = :user_id,
    updated_at = NOW()
WHERE id = :item_id;
```

**Note**: Status does NOT change. Rejection marked by `rejected_at` timestamp.

**Secondary Writes**:
- `pms_audit_log`: Record rejection action

**Notifications**:
- Email to requester (crew member) with rejection reason

**Integrations**: None

### 8. Related Actions

**Upstream**:
- `create_shopping_list_item` - Item must be created first

**Downstream**:
- None (rejection is terminal)

**Alternatives**:
- `approve_shopping_list_item` - HOD can approve instead of reject

### 9. Success States

**HTTP Status**: 200 OK

**Response**:
```json
{
  "success": true,
  "action_id": "reject_shopping_list_item",
  "entity_id": "abc-123",
  "entity_type": "shopping_list_item",
  "data": {
    "shopping_list_item_id": "abc-123",
    "status": "candidate",
    "rejected": true,
    "rejection_reason": "Duplicate request - already ordered in previous cycle",
    "rejected_at": "2026-01-28T12:10:00Z"
  }
}
```

**Database State**:
- `pms_shopping_list_items`: rejected_by/rejected_at set, rejection_reason set
- `pms_audit_log`: New row with action='reject_shopping_list_item'
- Status remains unchanged (candidate or under_review)

### 10. Error States

**400 Bad Request**:
- Already rejected: `{"detail": "Item is already rejected"}`
- Cannot reject approved: `{"detail": "Cannot reject item with status 'approved'. Expected: candidate or under_review."}`
- Missing reason: `{"detail": "rejection_reason is required"}`

**403 Forbidden**:
- User not HOD: `{"detail": "Only HoD (chief engineer, chief officer, captain, manager) can reject shopping list items"}`

**404 Not Found**:
- Item doesn't exist: `{"detail": "Shopping list item not found: abc-123"}`

### 11. UI Surfacing

**Location**:
- **Shopping List Page**: "Reject" button on each row (HOD only)
- **Approval Queue Page**: "Reject" option in bulk actions
- **Item Detail Page**: "Reject" button in header

**Visibility Rules**:
- Visible only to HOD roles
- Hidden for crew/engineer roles
- Disabled if item already rejected or approved
- Shows rejection badge with reason if rejected

**User Journey**:
1. HOD reviews shopping list
2. Identifies item that should not be procured (duplicate, already have stock, not needed, etc.)
3. Clicks "Reject" button
4. Modal opens with rejection_reason field (required)
5. Selects from common reasons:
   - "Duplicate request"
   - "Already in stock"
   - "Not required"
   - "Budget constraints"
   - "Alternative solution available"
   - "Custom" (free text)
6. Optional: Adds rejection_notes for context
7. Clicks "Confirm Rejection"
8. Success: Item marked as rejected, badge shows reason
9. Requester receives email with rejection reason

### 12. Examples

**Example 1: Basic Rejection**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "reject_shopping_list_item",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "item_id": "4cd17356-1760-4605-9d2c-3b418c3a8197",
      "rejection_reason": "Duplicate request - already ordered in previous cycle"
    }
  }'
```

**Response (200 OK)**:
```json
{
  "success": true,
  "action_id": "reject_shopping_list_item",
  "entity_id": "4cd17356-1760-4605-9d2c-3b418c3a8197",
  "entity_type": "shopping_list_item",
  "data": {
    "shopping_list_item_id": "4cd17356-1760-4605-9d2c-3b418c3a8197",
    "status": "candidate",
    "rejected": true,
    "rejection_reason": "Duplicate request - already ordered in previous cycle",
    "rejected_at": "2026-01-28T12:10:15Z"
  }
}
```

**Example 2: Rejection with Notes**
```json
{
  "action": "reject_shopping_list_item",
  "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
  "payload": {
    "item_id": "abc-123",
    "rejection_reason": "Alternative solution available",
    "rejection_notes": "Can use universal filter part #UF-500 which we already have in stock. No need to order OEM specific filter."
  }
}
```

**Example 3: Error - CREW Attempting Rejection**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "reject_shopping_list_item",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "item_id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26",
      "rejection_reason": "Not needed"
    }
  }'
```

**Response (403 Forbidden)**:
```json
{
  "detail": "Only HoD (chief engineer, chief officer, captain, manager) can reject shopping list items"
}
```

---

## Action 4: promote_candidate_to_part

### 1. Identification

- **Action ID**: `promote_candidate_to_part`
- **Label**: "Promote to Parts Catalog"
- **Variant**: MUTATE
- **Domain**: shopping_list

### 2. Access Control

- **Allowed Roles**: chief_engineer, manager (Engineers only)
- **Denied Roles**: crew, deckhand, steward, engineer, eto, chief_officer, chief_steward, purser, captain
- **Permission Check**:
  1. Router checks JWT role against allowed_roles
  2. Handler explicitly calls `is_engineer()` RPC

### 3. Interface

**Endpoint**: `POST /v1/actions/execute`

**Required Fields**:
- `item_id` (uuid) - Shopping list item to promote

**Optional Fields**: None

**Response Fields**:
- `shopping_list_item_id` (uuid)
- `part_id` (uuid) - Newly created part ID
- `promoted_at` (timestamp)
- `is_candidate_part` (boolean) - false after promotion

### 4. Triggers

**User Actions**:
- Click "Add to Parts Catalog" button on candidate item
- Bulk promote multiple candidates
- Promote from parts management page

**UI Flows**:
1. Engineer reviews shopping list
2. Identifies candidate items (is_candidate_part=true)
3. Clicks "Promote to Parts Catalog" button
4. Confirmation modal with part details preview
5. Confirms promotion
6. New part created in catalog
7. Shopping list item linked to new part

### 5. Preconditions

- ✅ User must be engineer role (chief_engineer or manager)
- ✅ Item must exist and belong to user's yacht
- ✅ Item must have is_candidate_part=true
- ✅ Item must NOT be already promoted (candidate_promoted_to_part_id IS NULL)
- ✅ Part name should not already exist in pms_parts (soft rule, allows duplicates)

### 6. Validation Rules

**Field Validation**:
- `item_id`: Valid UUID, item must exist

**Business Logic**:
- is_candidate_part must be true
- Cannot promote if already promoted (candidate_promoted_to_part_id NOT NULL)
- Creates atomic transaction (part insert + shopping list update)

**Role Enforcement**:
```python
is_engineer_result = db.rpc("is_engineer", {"p_user_id": user_id, "p_yacht_id": yacht_id})
if not is_engineer_result.data:
    return 403 "Only engineers can promote candidates to parts catalog"
```

### 7. Side Effects

**Primary Write 1** (Insert Part):
```sql
INSERT INTO pms_parts (
    id, yacht_id, name, part_number, manufacturer, unit,
    quantity_on_hand, created_at, updated_at
) VALUES (:new_part_id, :yacht_id, :part_name, :part_number, :manufacturer, :unit, 0, NOW(), NOW());
```

**Primary Write 2** (Update Shopping List Item):
```sql
UPDATE pms_shopping_list_items SET
    part_id = :new_part_id,
    is_candidate_part = false,
    candidate_promoted_to_part_id = :new_part_id,
    promoted_by = :user_id,
    promoted_at = NOW(),
    updated_by = :user_id,
    updated_at = NOW()
WHERE id = :item_id;
```

**Secondary Writes**:
- `pms_audit_log`: Record promotion action

**Notifications**:
- Email to requester confirming part added to catalog

**Integrations**:
- Part now appears in inventory management system
- Can be used for future maintenance planning

### 8. Related Actions

**Upstream**:
- `create_shopping_list_item` - Item must be created with is_candidate_part=true

**Downstream**:
- Part can now be used in maintenance plans
- Part can be linked to equipment
- Part inventory can be managed

**Alternatives**: None

### 9. Success States

**HTTP Status**: 200 OK

**Response**:
```json
{
  "success": true,
  "action_id": "promote_candidate_to_part",
  "entity_id": "abc-123",
  "entity_type": "shopping_list_item",
  "data": {
    "shopping_list_item_id": "abc-123",
    "part_id": "9fa6dda8-e4a8-45ff-b90e-bc48eacaa56b",
    "promoted_at": "2026-01-28T12:15:42Z",
    "is_candidate_part": false
  }
}
```

**Database State**:
- `pms_parts`: New row created with quantity_on_hand=0
- `pms_shopping_list_items`: promoted_by/promoted_at set, is_candidate_part=false, candidate_promoted_to_part_id set
- `pms_audit_log`: New row with action='promote_candidate_to_part'

### 10. Error States

**400 Bad Request**:
- Not a candidate: `{"detail": "Item is not a candidate part (already in catalog)"}`
- Already promoted: `{"detail": "Item already promoted to part: 9fa6dda8-..."}`

**403 Forbidden**:
- User not engineer: `{"detail": "Only engineers (chief engineer, ETO, engineer, manager) can promote candidates to parts catalog"}`

**404 Not Found**:
- Item doesn't exist: `{"detail": "Shopping list item not found: abc-123"}`

**500 Internal Server Error**:
- Transaction failure (part insert or shopping list update failed)

### 11. UI Surfacing

**Location**:
- **Shopping List Page**: "Promote to Parts" button on candidate items (engineer only)
- **Parts Management Page**: "Add from Shopping List" shows candidates
- **Item Detail Page**: "Promote" button in header (if candidate)

**Visibility Rules**:
- Visible only to engineer roles (chief_engineer, manager)
- Hidden for all other roles including HOD
- Only shown for items with is_candidate_part=true
- Disabled if already promoted

**Badge/Indicator**:
- Candidate items show "Candidate Part" badge
- After promotion shows "In Parts Catalog" badge with link

**User Journey**:
1. Engineer navigates to Shopping List page
2. Filters by "Candidate Parts" or sees badge indicator
3. Reviews candidate part details (part_name, part_number, manufacturer)
4. Clicks "Promote to Parts Catalog" button
5. Confirmation modal shows:
   - "This will create a new part in the catalog:"
   - Part name, number, manufacturer
   - Initial quantity: 0
6. Engineer confirms
7. Success: Part created, link shown in shopping list item
8. Engineer can now navigate to parts catalog to manage inventory

### 12. Examples

**Example 1: Basic Promotion**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $CHIEF_ENGINEER_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "promote_candidate_to_part",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "item_id": "ed77743d-1108-44e1-ba18-a60b255fd9b2"
    }
  }'
```

**Response (200 OK)**:
```json
{
  "success": true,
  "action_id": "promote_candidate_to_part",
  "entity_id": "ed77743d-1108-44e1-ba18-a60b255fd9b2",
  "entity_type": "shopping_list_item",
  "data": {
    "shopping_list_item_id": "ed77743d-1108-44e1-ba18-a60b255fd9b2",
    "part_id": "9fa6dda8-e4a8-45ff-b90e-bc48eacaa56b",
    "promoted_at": "2026-01-28T12:15:42Z",
    "is_candidate_part": false
  }
}
```

**Example 2: Error - CREW Attempting Promotion**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "promote_candidate_to_part",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "item_id": "288ee9e6-2e3c-43d5-9e01-83a04f2d5d26"
    }
  }'
```

**Response (403 Forbidden)**:
```json
{
  "detail": "Only engineers (chief engineer, ETO, engineer, manager) can promote candidates to parts catalog"
}
```

**Example 3: Error - Not a Candidate**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $CHIEF_ENGINEER_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "promote_candidate_to_part",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "item_id": "regular-item-not-candidate"
    }
  }'
```

**Response (400 Bad Request)**:
```json
{
  "detail": "Item is not a candidate part (already in catalog)"
}
```

---

## Action 5: view_shopping_list_history

### 1. Identification

- **Action ID**: `view_shopping_list_history`
- **Label**: "View History"
- **Variant**: READ
- **Domain**: shopping_list

### 2. Access Control

- **Allowed Roles**: crew, chief_engineer, chief_officer, captain, manager (all authenticated)
- **Denied Roles**: None
- **Permission Check**: Router checks JWT authentication

### 3. Interface

**Endpoint**: `POST /v1/actions/execute` or `GET /v1/shopping-list/:item_id/history`

**Required Fields**:
- `item_id` (uuid) - Shopping list item to view history for

**Optional Fields**: None

**Response Fields**:
- `item_id` (uuid)
- `history` (array) - Array of state transition objects:
  - `from_status` (string)
  - `to_status` (string)
  - `changed_by` (uuid)
  - `changed_by_name` (string)
  - `changed_at` (timestamp)
  - `notes` (text)

### 4. Triggers

**User Actions**:
- Click "View History" button on shopping list item
- Click history icon in item row
- Navigate to item detail page (auto-shows history)

### 5. Preconditions

- ✅ User must be authenticated
- ✅ Item must exist and belong to user's yacht

### 6. Validation Rules

**Field Validation**:
- `item_id`: Valid UUID, item must exist

**Business Logic**: None (read-only)

### 7. Side Effects

**Reads**:
```sql
SELECT * FROM pms_shopping_list_state_history
WHERE shopping_list_item_id = :item_id
ORDER BY changed_at ASC;
```

**Writes**: None (read-only action)

### 8. Related Actions

**Upstream**: Any action that modifies shopping list item

**Downstream**: None

### 9. Success States

**HTTP Status**: 200 OK

**Response**:
```json
{
  "success": true,
  "item_id": "abc-123",
  "history": [
    {
      "from_status": null,
      "to_status": "candidate",
      "changed_by": "user-1",
      "changed_by_name": "John Doe",
      "changed_at": "2026-01-28T12:00:00Z",
      "notes": null
    },
    {
      "from_status": "candidate",
      "to_status": "approved",
      "changed_by": "user-2",
      "changed_by_name": "Jane Smith",
      "changed_at": "2026-01-28T12:05:00Z",
      "notes": "Approved for Q1 procurement"
    }
  ]
}
```

### 10. Error States

**404 Not Found**:
- Item doesn't exist: `{"detail": "Shopping list item not found: abc-123"}`

### 11. UI Surfacing

**Location**:
- **Shopping List Page**: History icon in each row
- **Item Detail Page**: History timeline at bottom
- **Audit Log Page**: Linked from audit entries

**User Journey**:
1. User views shopping list
2. Clicks history icon on item row
3. Modal/sidebar opens showing timeline
4. Timeline shows each status change with timestamp and user

### 12. Examples

**Example**:
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "view_shopping_list_history",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "item_id": "abc-123"
    }
  }'
```

---

## Role Permission Matrix

| Action | CREW | Engineer/ETO | Chief Engineer | Chief Officer | Purser | Captain | Manager |
|--------|------|-------------|----------------|---------------|--------|---------|---------|
| create_shopping_list_item | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| approve_shopping_list_item | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| reject_shopping_list_item | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| promote_candidate_to_part | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| view_shopping_list_history | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Legend**:
- ✅ = Allowed
- ❌ = Denied (returns 403 Forbidden)

---

## Field Reference

### Required Fields Summary

| Field | Type | Used In | Validation |
|-------|------|---------|------------|
| part_name | string | create | NOT NULL, length > 0 |
| quantity_requested | integer | create | > 0 |
| source_type | enum | create | IN ('manual_add', 'maintenance_plan', 'fault_report', 'inspection') |
| item_id | uuid | approve, reject, promote, view_history | Valid UUID, exists |
| quantity_approved | integer | approve | > 0, ≤ quantity_requested |
| rejection_reason | text | reject | NOT NULL, length > 0 |

### Optional Fields Summary

| Field | Type | Used In | Default |
|-------|------|---------|---------|
| part_number | string | create | NULL |
| manufacturer | string | create | NULL |
| unit | string | create | 'piece' |
| urgency | enum | create | 'normal' |
| notes | text | create | NULL |
| is_candidate_part | boolean | create | false |
| approval_notes | text | approve | NULL |
| rejection_notes | text | reject | NULL |

### Enum Values

**source_type**:
- `manual_add` - Manually added by crew
- `maintenance_plan` - Generated from maintenance schedule
- `fault_report` - Requested from fault report
- `inspection` - Identified during inspection

**urgency**:
- `normal` - Standard procurement cycle
- `urgent` - Expedited procurement needed
- `critical` - Emergency procurement required

**status** (shopping list item):
- `candidate` - Initial state, awaiting approval
- `under_review` - Being reviewed by HOD
- `approved` - Approved for procurement

**Rejection**:
- Marked by `rejected_at` timestamp (not status change)
- `rejection_reason` required

---

## Summary

Shopping List Lens v1 provides **5 microactions** that enable a complete role-based shopping list workflow:

1. **CREW** can create items and view history
2. **HOD** can approve or reject items
3. **ENGINEERS** can promote approved candidates to parts catalog
4. **ALL** can view history for audit trail

This catalog provides complete documentation for:
- Product managers planning features
- QA engineers writing test cases
- Frontend engineers building UI
- Backend engineers maintaining handlers
