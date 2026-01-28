# Glossary - CelesteOS Cloud PMS

**Quick reference for all terms used in this codebase**

**Audience:** New engineers
**Purpose:** Define every term, acronym, and concept
**When to use:** Whenever you see a term you don't recognize

---

## Core Concepts

### Microaction
**What it is:** A user-triggered mutation with natural language detection, contextual awareness, and audit trail.

**Example:**
```json
POST /v1/actions/execute
{
  "action": "create_work_order",  ← Microaction name
  "context": {
    "yacht_id": "...",  ← Automatic from JWT
    "user_id": "..."    ← Automatic from JWT
  },
  "payload": {
    "title": "Replace oil filter"  ← User input
  }
}
```

**Why not just REST?**
- Microactions include context automatically (yacht_id, user_id)
- Natural language triggers ("create a work order" → create_work_order)
- Guard rails enforced at all layers
- Audit trail required

**How many?** 64 total microactions in the system

**Where defined?** `tests/fixtures/microaction_registry.ts`

---

### Situation
**What it is:** The user's current focus state in the UI.

**States:**
- **IDLE** - User on main search surface (no entity selected)
- **CANDIDATE** - User hovered/selected entity (preview mode)
- **ACTIVE** - User opened entity detail (ContextPanel visible)

**Why it matters:**
- Situations provide context for actions
- Example: User viewing Fault F-123 (ACTIVE) → Clicks "Create Work Order" → Action pre-fills fault_id from situation

**State transitions:**
```
IDLE
  → (user clicks search result)
  → CANDIDATE
  → (user presses Enter or double-clicks)
  → ACTIVE
  → (user closes panel)
  → IDLE
```

**Where implemented?** `apps/web/src/contexts/SurfaceContext.tsx` and `apps/web/src/hooks/useSituationState.ts`

---

### Yacht
**What it is:** A vessel (boat/ship). One client = one yacht.

**NOT "customer":** The yacht is the tenant, not the customer.
**NOT "company":** Each yacht is isolated (not a company with multiple yachts in one DB).

**Examples:**
- M/Y Eclipse (123m superyacht)
- M/Y Luna (115m superyacht)
- S/Y Black Pearl (106m sailing yacht)

**Why it matters:**
- All data is scoped to one yacht
- Multi-tenant architecture: Each yacht has isolated data
- RLS enforces yacht_id filtering

**Test Yacht:** `85fe1119-b04c-41ac-80f1-829d23322598` (used in all tests)

---

### Tenant
**What it is:** One yacht's isolated database.

**Architecture:**
- **Master DB** - User accounts, yacht registry, auth
- **Tenant DB** - One yacht's PMS data (work orders, faults, equipment, parts)

**Multi-tenant isolation:**
- Each yacht's data is completely isolated
- RLS (Row Level Security) enforces yacht_id filtering
- No cross-yacht queries possible

**Example:**
```
Yacht A (tenant_id: yacht-a-uuid)
  → Tenant DB A (pms_work_orders, pms_faults, pms_equipment...)

Yacht B (tenant_id: yacht-b-uuid)
  → Tenant DB B (pms_work_orders, pms_faults, pms_equipment...)

No overlap. User on Yacht A cannot see Yacht B's data.
```

---

### Master DB
**What it is:** Central database storing user accounts, yacht registry, and authentication.

**Contains:**
- User accounts (email, password hash, role)
- Yacht registry (yacht name, owner, subscription)
- OAuth tokens
- Tenant keys (which Supabase instance for each yacht)

**Location:** Supabase project (shared across all yachts)

**Tables:**
- `user_profiles` (user_id, yacht_id, name, role, email)
- `yachts` (yacht_id, name, owner, tenant_key_alias)
- `oauth_tokens` (user_id, provider, access_token, refresh_token)

**NOT for PMS data:** Work orders, faults, equipment, parts are in Tenant DB.

---

### Tenant DB
**What it is:** One yacht's PMS (Planned Maintenance System) data.

**Contains:**
- pms_work_orders
- pms_faults
- pms_equipment
- pms_parts
- pms_audit_log
- pms_work_order_notes
- pms_checklists
- ... (all pms_* tables)

**Location:** Supabase project (separate per yacht, or same instance with RLS)

**Isolation:** RLS policies enforce yacht_id filtering on all queries.

---

### RLS (Row Level Security)
**What it is:** PostgreSQL feature that automatically filters queries by yacht_id.

**How it works:**
```sql
-- Policy on pms_work_orders table
CREATE POLICY "yacht_isolation" ON pms_work_orders
FOR ALL
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);

-- This query:
SELECT * FROM pms_work_orders;

-- Becomes this automatically:
SELECT * FROM pms_work_orders WHERE yacht_id = 'yacht-a-uuid';
```

**Why it matters:**
- Prevents cross-yacht data leaks
- Enforced at database level (not just application)
- Every query MUST include yacht_id in WHERE clause
- If missing yacht_id → No rows returned (fail-safe)

**Testing implication:** All test queries must include yacht_id filter.

---

### Soft Delete
**What it is:** Marking rows as deleted without actually deleting them.

**How it works:**
```sql
-- Hard delete (BLOCKED by policy)
DELETE FROM pms_work_orders WHERE id = '...';
-- Error: Policy prevents hard deletes

-- Soft delete (REQUIRED)
UPDATE pms_work_orders
SET deleted_at = NOW(),
    deleted_by = 'user-uuid',
    deletion_reason = 'User requested deletion'
WHERE id = '...';
```

**Why:**
- Audit trail preserved
- Can restore if needed
- Compliance requirement (ISO 9001)

**Schema pattern:** All tables have:
- `deleted_at` (timestamptz, nullable)
- `deleted_by` (uuid, nullable)
- `deletion_reason` (text, nullable)

**Query pattern:** Always filter out soft-deleted rows:
```sql
SELECT * FROM pms_work_orders
WHERE yacht_id = '...'
  AND deleted_at IS NULL;  ← Filter soft-deleted
```

---

### Mutation Proof
**What it is:** A test that verifies database state actually changed.

**Pattern:**
```typescript
// 1. BEFORE - Query database
const { data: before } = await supabase
  .from('pms_work_orders')
  .select('*')
  .eq('title', 'Test WO');
expect(before).toHaveLength(0);  // Row doesn't exist yet

// 2. EXECUTE - Call action
await executeAction('create_work_order', {...});

// 3. AFTER - Query database again
const { data: after } = await supabase
  .from('pms_work_orders')
  .select('*')
  .eq('title', 'Test WO')
  .single();
expect(after).toBeTruthy();  // Row now exists
expect(after.status).toBe('planned');  // Correct values

// 4. AUDIT - Verify audit log
const { data: audit } = await supabase
  .from('pms_audit_log')
  .select('*')
  .eq('entity_id', after.id);
expect(audit).toHaveLength(1);  // Audit entry exists
```

**Why important:** HTTP 200 doesn't mean database changed. This test proves it.

**Gold standard:** `tests/e2e/mutation_proof_create_work_order.spec.ts`

---

## UI Components

### SpotlightSearch
**What it is:** Apple Spotlight-style search bar (always visible, centered).

**Location:** `apps/web/src/components/spotlight/SpotlightSearch.tsx`

**Features:**
- Natural language query input
- Action button rendering (when action detected)
- Search results display
- Rolling placeholder suggestions

**User flow:**
1. User types: "create a work order"
2. Backend detects action
3. Button appears: "Create Work Order"
4. User clicks → Modal opens

---

### ContextPanel
**What it is:** Slide-out panel from right side showing entity details.

**Location:** `apps/web/src/app/app/ContextPanel.tsx`

**When shown:**
- User has ACTIVE situation (opened an entity)

**Contains:**
- Entity details (work order, fault, equipment, part, etc.)
- Action buttons (Mark Complete, Edit, Delete, etc.)
- Related data (notes, parts, history)

**Example:**
```
┌──────────────────────────┐
│ WO-1234: Oil Change      │
│ Status: Open             │
├──────────────────────────┤
│ [✅ Complete] [✏️ Edit]  │
├──────────────────────────┤
│ Description: ...         │
│ Notes: ...               │
└──────────────────────────┘
```

---

### Action Modal
**What it is:** Pop-up dialog for action forms.

**Triggered by:** Clicking action button

**Contains:**
- Form fields (title, description, priority, etc.)
- Validation (required fields marked)
- Submit/Cancel buttons

**Example Flow:**
1. User clicks "Create Work Order" button
2. Modal opens with form
3. User fills fields
4. User clicks "Create"
5. Modal closes, toast appears

---

### Toast Notification
**What it is:** Temporary notification message (success/error).

**Library:** `sonner` (React toast library)

**Examples:**
- ✅ "Work order created"
- ❌ "Title is required"
- ⚠️ "Equipment not found"

**Duration:** 3-5 seconds (auto-dismiss)

---

## API & Backend

### Action Router
**What it is:** Backend endpoint that routes all microaction requests.

**Endpoint:** `POST /v1/actions/execute`

**Location:** `apps/api/routes/p0_actions_routes.py` (4160 lines, 81 handlers)

**Request format:**
```json
{
  "action": "create_work_order",
  "context": {"yacht_id": "...", "user_id": "..."},
  "payload": {"title": "...", "description": "..."}
}
```

**Response format:**
```json
{
  "status": "success",  // or "error"
  "work_order_id": "...",
  "message": "Work order created"
}
```

---

### JWT (JSON Web Token)
**What it is:** Authentication token containing user identity and yacht access.

**Structure:**
```json
{
  "sub": "user-uuid",  // User ID
  "yacht_id": "yacht-uuid",  // Which yacht user has access to
  "role": "engineer",  // User role
  "iat": 1234567890,  // Issued at
  "exp": 1234571490   // Expires
}
```

**Flow:**
1. User logs in → Supabase Auth issues JWT
2. Frontend stores JWT in memory
3. Every API call includes: `Authorization: Bearer {JWT}`
4. Backend validates JWT → Extracts user_id, yacht_id
5. All queries filtered by yacht_id (RLS)

**Testing:** Tests use service role key (bypasses JWT validation)

---

### Handler
**What it is:** Python function that implements one microaction.

**Location:** `apps/api/routes/p0_actions_routes.py`

**Pattern:**
```python
elif action in ("create_work_order", "create_wo"):
    # 1. Validate required fields
    title = payload.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    # 2. Transform data
    priority = map_priority(payload.get("priority"))

    # 3. Write to database
    wo_data = {
        "yacht_id": yacht_id,
        "title": title,
        "status": "planned",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = db_client.table("pms_work_orders").insert(wo_data).execute()

    # 4. Return response
    return {"status": "success", "work_order_id": result.data[0]["id"]}
```

**Where to find:** Search for `action == "your_action_name"`

---

### GPT-4o-mini Extraction
**What it is:** LLM that detects microactions from natural language queries.

**Endpoint:** `POST /search`

**Flow:**
```
User types: "create a work order for the generator"
  ↓
POST /search {"query": "..."}
  ↓
GPT-4o-mini analyzes query
  ↓
Returns: {
  "actions": [{"action": "create_work_order", ...}],
  "results": [...]
}
  ↓
Frontend shows "Create Work Order" button
```

**Why it matters:** This is how natural language queries become microactions.

---

## Database

### pms_work_orders
**What it is:** Main table for maintenance work orders.

**Key columns:**
- `id` (uuid, PK)
- `yacht_id` (uuid, FK, RLS enforced)
- `equipment_id` (uuid, FK to pms_equipment)
- `fault_id` (uuid, FK to pms_faults)
- `title` (text, required)
- `status` (text: planned, open, in_progress, completed, cancelled)
- `priority` (text: routine, critical, emergency)
- `created_by`, `updated_by`, `completed_by` (uuid, FK to users)
- `created_at`, `updated_at`, `completed_at` (timestamptz)
- `deleted_at`, `deleted_by`, `deletion_reason` (soft delete)

**Total columns:** 29

**See:** DATABASE_RELATIONSHIPS.md for full schema

---

### pms_audit_log
**What it is:** THE ONLY audit table. Immutable log of all mutations.

**Key columns:**
- `id` (uuid, PK)
- `yacht_id` (uuid, RLS enforced)
- `action` (text: microaction name)
- `entity_type` (text: work_order, fault, equipment, part, etc.)
- `entity_id` (uuid: ID of affected entity)
- `user_id` (uuid: who performed action)
- `old_values` (jsonb: state before, null for creates)
- `new_values` (jsonb: state after)
- `signature` (jsonb: {user_id, timestamp, action, execution_id})
- `metadata` (jsonb: additional context)
- `created_at` (timestamptz, immutable)

**Critical:** No updates or deletes allowed (immutable audit trail)

**Why it matters:** Compliance requirement (ISO 9001, SOLAS)

**Current gap:** Many actions don't write to audit log (verification finding)

---

### pms_equipment
**What it is:** Asset registry (engines, pumps, HVAC, electrical, etc.)

**Hierarchical:** Self-referential `parent_id` enables tree structure
- Main Engine (parent_id: null)
  - Fuel Pump (parent_id: main-engine-uuid)
    - Fuel Filter (parent_id: fuel-pump-uuid)

**Key fields:**
- `name`, `code`, `manufacturer`, `model`, `serial_number`
- `location`, `criticality`, `status`
- `attention_flag` (boolean: red flag for operator)

**See:** DATABASE_RELATIONSHIPS.md

---

### pms_faults
**What it is:** Equipment failures/faults reported by crew.

**Lifecycle:**
1. Crew reports fault (status: reported)
2. Engineer acknowledges (status: acknowledged)
3. Engineer diagnoses (status: diagnosed)
4. Work order created (work_order_id set)
5. Work order completed (status: resolved)

**Links to:** pms_equipment (fault on which equipment), pms_work_orders (fix action)

---

### pms_parts
**What it is:** Parts catalog + inventory tracking.

**Features:**
- Semantic search (`search_embedding` vector column)
- Inventory tracking (`quantity_on_hand`, `minimum_quantity`)
- Model compatibility (`model_compatibility` text array)

**Key trap:** Column is `quantity_on_hand`, NOT `current_quantity`

---

## Testing Terms

### E2E Test
**What it is:** End-to-end test simulating real user interaction.

**Tool:** Playwright

**Example:**
```typescript
test('create work order full journey', async ({ page }) => {
  await page.goto('/app');
  await page.fill('[data-testid="spotlight-input"]', 'create a work order');
  await page.click('button:has-text("Create Work Order")');
  await page.fill('[name="title"]', 'Test WO');
  await page.click('button:has-text("Create")');
  await page.waitForSelector('.toast:has-text("created")');
});
```

**Why important:** Tests the full customer journey, not just API.

---

### Playwright
**What it is:** Browser automation framework for E2E tests.

**Features:**
- Simulates real user (clicks, types, waits)
- Cross-browser (Chrome, Firefox, Safari)
- Screenshots, videos on failure
- Debug mode with inspector

**Run tests:**
```bash
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts
```

---

### Unit Test
**What it is:** Test of a single function in isolation.

**NOT used much in this project.** We focus on mutation proofs and E2E tests.

---

### Regression Test
**What it is:** Test that ensures previously-working features still work.

**Goal:** Run all 64 mutation proof tests nightly to catch regressions.

---

## HTTP Status Codes

### 200 OK
**What it means:** Handler executed without crashing.

**DOES NOT MEAN:**
- ❌ Database was updated
- ❌ Audit log was created
- ❌ Action succeeded

**ONLY MEANS:** Python code didn't throw an exception.

**Always verify database state after 200!**

---

### 400 Bad Request
**What it means:** User sent invalid input.

**Examples:**
- Missing required field: `{"error": "title is required"}`
- Invalid enum value: `{"error": "status must be one of: planned, open, completed"}`
- Validation failed: `{"error": "title too long (max 200 chars)"}`

**This is EXPECTED behavior, not a bug!** Test for 400 responses.

---

### 401 Unauthorized
**What it means:** No JWT token or invalid JWT.

**Examples:**
- Missing Authorization header
- Expired JWT
- Invalid signature

**User action:** Redirect to login

---

### 403 Forbidden
**What it means:** Authenticated but not authorized for this resource.

**Examples:**
- User trying to access different yacht's data
- User role doesn't have permission for this action

**Difference from 401:**
- 401 = "Who are you?" (not logged in)
- 403 = "I know who you are, but you can't do this"

---

### 404 Not Found
**What it means:** Referenced entity doesn't exist.

**Examples:**
- Invalid equipment_id: `{"error": "Equipment not found"}`
- Invalid work_order_id: `{"error": "Work order not found"}`

**This is EXPECTED behavior, not a bug!** Test for 404 responses.

---

### 500 Internal Server Error
**What it means:** Unexpected server error (this IS a bug).

**Examples:**
- Unhandled exception
- Database connection failed
- Null pointer error

**User action:** Show error message, retry button, alert developers

---

## Acronyms

**API** - Application Programming Interface
**DB** - Database
**E2E** - End-to-End (testing)
**FK** - Foreign Key
**HVAC** - Heating, Ventilation, Air Conditioning
**ISO** - International Organization for Standardization
**JWT** - JSON Web Token
**NL** - Natural Language
**OEM** - Original Equipment Manufacturer
**P/N** - Part Number
**PK** - Primary Key
**PMS** - Planned Maintenance System
**REST** - Representational State Transfer
**RLS** - Row Level Security
**SOLAS** - Safety of Life at Sea (maritime regulation)
**SQL** - Structured Query Language
**UI** - User Interface
**URL** - Uniform Resource Locator
**UX** - User Experience
**UUID** - Universally Unique Identifier
**WO** - Work Order

---

## File Extensions

**.md** - Markdown (documentation)
**.py** - Python (backend code)
**.ts** - TypeScript (frontend code, tests)
**.tsx** - TypeScript + JSX (React components)
**.js** - JavaScript (utility scripts)
**.json** - JSON (configuration, data)
**.sql** - SQL (database queries, migrations)
**.spec.ts** - Test file (Playwright)
**.config.js** - Configuration file

---

## Common Patterns

### `yacht_id`
**Pattern:** Always UUID, always required, always RLS-filtered

**Usage:**
```typescript
const { data } = await supabase
  .from('pms_work_orders')
  .select('*')
  .eq('yacht_id', YACHT_ID);  ← ALWAYS include this
```

---

### `created_by` / `updated_by` / `completed_by`
**Pattern:** Track who performed each action

**Values:** UUID of user from Master DB

**Usage:**
```python
wo_data = {
    "created_by": user_id,  ← From JWT
    "created_at": datetime.now(timezone.utc).isoformat()
}
```

---

### `deleted_at` / `deleted_by` / `deletion_reason`
**Pattern:** Soft delete (never hard delete)

**Usage:**
```sql
UPDATE pms_work_orders
SET deleted_at = NOW(),
    deleted_by = 'user-uuid',
    deletion_reason = 'User requested deletion'
WHERE id = '...';
```

**Query:**
```sql
SELECT * FROM pms_work_orders
WHERE yacht_id = '...'
  AND deleted_at IS NULL;  ← Filter soft-deleted rows
```

---

### `metadata` (JSONB)
**Pattern:** Extensible key-value storage

**Examples:**
```json
{
  "photos": ["https://...", "https://..."],
  "sensor_data": {"temperature": 85, "pressure": 30},
  "custom_field_1": "value"
}
```

**Query:**
```sql
SELECT * FROM pms_equipment
WHERE metadata->>'custom_field_1' = 'value';
```

---

## Quick Reference

**Most Common Terms You'll See:**
1. Microaction - User-triggered mutation (64 total)
2. Situation - User focus state (IDLE/CANDIDATE/ACTIVE)
3. Yacht - The vessel (one client)
4. Tenant - One yacht's isolated database
5. RLS - Row Level Security (yacht_id filtering)
6. Soft Delete - Mark as deleted, don't delete
7. Mutation Proof - Test that verifies database changed
8. JWT - Auth token with user_id + yacht_id
9. SpotlightSearch - Main search bar
10. ContextPanel - Slide-out entity details panel

**If you see a term not listed here:** Ask the team or add it to this glossary!

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Maintained By:** Engineering Team
**How to Update:** Add new terms as you encounter them
