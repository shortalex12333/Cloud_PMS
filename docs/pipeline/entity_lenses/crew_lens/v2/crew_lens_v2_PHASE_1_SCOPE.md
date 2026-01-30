# Crew Lens v2 - PHASE 1: SCOPE

**Version**: v2.0
**Status**: DESIGN COMPLETE
**Date**: 2026-01-30
**Template**: Certificate Lens v2 (Gold Standard)

---

## EXECUTIVE SUMMARY

The Crew Lens governs all operations for yacht crew management: viewing profiles, managing roles, tracking work assignments, and accessing crew qualifications (certificates).

### Key Metrics

| Metric | Value |
|--------|-------|
| Primary Tables | 4 (auth_users_profiles, auth_users_roles, pms_crew_certificates, pms_work_orders) |
| Actions Defined | 10 (3 self-service, 7 HOD/management) |
| Scenarios Documented | 8 |
| Role Tiers | 3 (Self, HOD, Captain/Manager) |
| New Migrations Required | 0 (all tables deployed) |

---

## GUIDING PRINCIPLES

### Backend Authority
- All crew actions originate from `/v1/actions/execute`
- Frontend renders exactly what `/v1/actions/list` returns
- Server derives yacht_id and role from JWT; client yacht_id is ignored
- RLS enforces yacht isolation and role gating

### Single Surface
- No navigation to "/crew" or crew pages
- Search bar drives intent: "John Smith profile", "assign chief engineer role", "my assigned work orders"
- Focus entity card → Backend returns context-valid actions → UI renders buttons

### Immutable Audit
- Every mutation writes to `pms_audit_log`
- Signature invariant: `{}` for non-signed actions (no SIGNED actions in Crew Lens v2)
- Role assignments are soft-revoked (`is_active=false`), never deleted

---

## USER INTENTS & SCENARIOS

### Scenario 1: Crew Member Views Own Profile
**Intent**: "Show my profile"

**User Query Examples**:
- "my profile"
- "view my details"
- "what's my role"

**Flow**:
1. User types "my profile" in search
2. System returns Crew card for current user
3. User clicks card → Focus
4. Backend returns `view_my_profile` action
5. User clicks "View Profile" → Shows: name, email, roles, yacht, status
6. Available follow-up: `update_my_profile`, `view_assigned_work_orders`

**Step Reduction**: Traditional = 5 steps (navigate → crew → find self → click → view). Celeste = 2 steps (search → view).

**Success Criteria**:
- Crew member can only see their own profile (RLS enforced)
- Roles shown with valid_from/valid_until dates
- Status badge shows "Active" or "Inactive"

---

### Scenario 2: Crew Member Updates Own Name
**Intent**: "Update my display name"

**User Query Examples**:
- "update my profile"
- "change my name"
- "edit my details"

**Flow**:
1. User types "update my profile"
2. System returns Crew card for current user
3. User clicks card → Focus → Backend returns `update_my_profile` action
4. User clicks "Edit Profile" → Modal shows: name (editable), metadata (optional)
5. User updates name → Submit → 200 OK
6. Audit log entry created with signature=`{}`
7. Profile refreshes with new name

**Field Classification**:
- name: OPTIONAL (can update)
- email: BACKEND_AUTO (cannot change)
- yacht_id: BACKEND_AUTO (immutable)
- metadata: OPTIONAL (JSON field for future extensions)

**Step Reduction**: 60% (Traditional = 5 steps, Celeste = 2 steps)

**Success Criteria**:
- User can only update their own profile (403 if attempt to edit others)
- Email and yacht_id are immutable
- Audit log records old_values and new_values

---

### Scenario 3: HOD Views All Crew Members
**Intent**: "List all crew on yacht"

**User Query Examples**:
- "list crew"
- "show all crew members"
- "who's on board"
- "crew roster"

**Flow**:
1. HOD types "list crew"
2. System returns multiple Crew cards (one per crew member)
3. Cards show: name, primary role, status badge (Active/Inactive)
4. HOD clicks any card → Focus → Backend returns HOD-specific actions:
   - `view_crew_member_details`
   - `assign_role`
   - `revoke_role`
   - `view_crew_certificates`
   - `view_crew_work_history`
   - `update_crew_member_status` (Captain/Manager only)

**Step Reduction**: 57% (Traditional = 7 steps, Celeste = 3 steps)

**Success Criteria**:
- Only HOD/Captain/Manager can list all crew (crew role sees 403)
- Yacht isolation enforced (cannot see crew from other yachts)
- Cards sorted by: active first, then by name

---

### Scenario 4: HOD Assigns Chief Engineer Role
**Intent**: "Assign chief_engineer role to John Smith"

**User Query Examples**:
- "assign chief engineer role to John Smith"
- "make John Smith chief engineer"
- "promote John to HOD"

**Flow**:
1. HOD types "assign chief engineer role to John Smith"
2. System extracts: person_name=John Smith, role=chief_engineer, action_intent=assign_role
3. Backend returns Crew card for John Smith + `assign_role` action auto-populated
4. HOD clicks "Assign Role" → Modal shows:
   - User: John Smith (pre-filled, read-only)
   - Role: chief_engineer (dropdown: crew, chief_engineer, eto, captain, manager, purser, deck, interior)
   - Valid From: NOW (default, editable)
   - Valid Until: NULL (optional expiry date)
5. HOD confirms → 200 OK
6. INSERT into `auth_users_roles` with is_active=true
7. Audit log entry: action=assign_role, signature=`{}`

**Field Classification**:
- user_id: CONTEXT (from focused entity)
- yacht_id: BACKEND_AUTO (from JWT)
- role: REQUIRED (user selects from dropdown)
- valid_from: BACKEND_AUTO (default NOW, user can override)
- valid_until: OPTIONAL (NULL = no expiry)
- assigned_by: BACKEND_AUTO (auth.uid())

**Step Reduction**: 50% (Traditional = 8 steps, Celeste = 4 steps)

**Success Criteria**:
- Only HOD can assign roles (crew → 403)
- Duplicate role assignment rejected (409 if user already has active role)
- Role is validated against CHECK constraint
- Audit log captures who assigned and when

---

### Scenario 5: HOD Revokes Role
**Intent**: "Revoke chief_engineer role from John Smith"

**User Query Examples**:
- "revoke John Smith's chief engineer role"
- "remove John's HOD access"
- "demote John Smith"

**Flow**:
1. HOD types "revoke John Smith chief engineer"
2. System returns Crew card for John Smith + `revoke_role` action
3. HOD clicks "Revoke Role" → Modal shows:
   - User: John Smith (pre-filled)
   - Current Roles: chief_engineer (active) (dropdown to select which role to revoke)
   - Reason: (optional text field)
4. HOD selects role and confirms → 200 OK
5. UPDATE `auth_users_roles` SET is_active=false WHERE id=<role_id>
6. Audit log entry: action=revoke_role, signature=`{}`

**Field Classification**:
- role_id: REQUIRED (which role assignment to revoke)
- reason: OPTIONAL (audit trail context)
- revoked_by: BACKEND_AUTO (auth.uid())
- revoked_at: BACKEND_AUTO (NOW)

**Step Reduction**: 44% (Traditional = 9 steps, Celeste = 5 steps)

**Success Criteria**:
- Only HOD can revoke roles (crew → 403)
- Role is soft-deleted (is_active=false), not removed
- Audit log preserves full history
- Cannot revoke if user has only one role (400)

---

### Scenario 6: Captain Views Crew Member's Certificates
**Intent**: "View John Smith's certificates"

**User Query Examples**:
- "show John Smith certificates"
- "what certifications does John have"
- "view John's qualifications"

**Flow**:
1. Captain types "show John Smith certificates"
2. System returns Crew card for John Smith
3. Captain clicks card → Focus → Backend returns `view_crew_certificates` action
4. Captain clicks "View Certificates" → Displays:
   - List of crew certificates from `pms_crew_certificates` WHERE person_name='John Smith'
   - Shows: certificate_type, certificate_number, issuing_authority, expiry_date, status
   - Expiry warnings for certificates expiring within 90 days
5. Escape hatch: Click certificate → Navigate to Certificate Lens (focus that cert)

**Step Reduction**: 50% (Traditional = 8 steps, Celeste = 4 steps)

**Success Criteria**:
- Only HOD/Captain/Manager can view crew certificates (crew sees 403)
- Certificates filtered by yacht_id (RLS enforced)
- Expiring certificates highlighted (< 90 days)
- Escape hatch to Certificate Lens works

---

### Scenario 7: Crew Member Views Assigned Work Orders
**Intent**: "Show my assigned work orders"

**User Query Examples**:
- "my work orders"
- "what's assigned to me"
- "my tasks"
- "my open WOs"

**Flow**:
1. Crew member types "my work orders"
2. System returns `view_assigned_work_orders` action auto-triggered
3. UI displays:
   - List of WOs from `pms_work_orders` WHERE assigned_to=auth.uid()
   - Shows: wo_number, title, priority, status, due_date, equipment_name
   - Sorted by: priority (emergency → critical → high → medium → low), then due_date
4. Escape hatch: Click WO → Navigate to Work Order Lens (focus that WO)

**Step Reduction**: 62% (Traditional = 8 steps, Celeste = 3 steps)

**Success Criteria**:
- Crew can only see their own assigned WOs (RLS enforced)
- Filters: status NOT IN ('completed', 'cancelled'), deleted_at IS NULL
- Priority sorting: emergency=1, critical=2, high=3, medium=4, low=5
- Escape hatch to Work Order Lens works

---

### Scenario 8: Captain Deactivates Crew Member
**Intent**: "Deactivate John Smith (crew member leaving yacht)"

**User Query Examples**:
- "deactivate John Smith"
- "mark John as inactive"
- "remove John from active crew"

**Flow**:
1. Captain types "deactivate John Smith"
2. System returns Crew card for John Smith + `update_crew_member_status` action
3. Captain clicks "Deactivate" → Confirmation modal:
   - User: John Smith
   - Current Status: Active
   - New Status: Inactive (toggle)
   - Reason: (optional text field for audit)
4. Captain confirms → 200 OK
5. UPDATE `auth_users_profiles` SET is_active=false WHERE id=<user_id>
6. Audit log entry: action=update_crew_member_status, signature=`{}`

**Field Classification**:
- user_id: CONTEXT (from focused entity)
- is_active: REQUIRED (boolean)
- reason: OPTIONAL (audit context)
- updated_by: BACKEND_AUTO (auth.uid())

**Step Reduction**: 42% (Traditional = 7 steps, Celeste = 4 steps)

**Success Criteria**:
- Only Captain/Manager can update status (HOD sees 403)
- Deactivated users cannot log in
- RLS policies filter inactive users
- Audit log preserves reason

---

## MICRO-ACTIONS SUMMARY

| # | Action ID | Label | Allowed Roles | Variant | Tables Written |
|---|-----------|-------|---------------|---------|----------------|
| 1 | `view_my_profile` | View My Profile | All Crew | READ | None |
| 2 | `update_my_profile` | Edit My Profile | All Crew | MUTATE | auth_users_profiles, audit |
| 3 | `view_assigned_work_orders` | My Work Orders | All Crew | READ | None |
| 4 | `list_crew_members` | List Crew | HOD, Captain, Manager | READ | None |
| 5 | `view_crew_member_details` | View Crew Details | HOD, Captain, Manager | READ | None |
| 6 | `assign_role` | Assign Role | HOD, Captain, Manager | MUTATE | auth_users_roles, audit |
| 7 | `revoke_role` | Revoke Role | HOD, Captain, Manager | MUTATE | auth_users_roles, audit |
| 8 | `view_crew_certificates` | View Certificates | HOD, Captain, Manager | READ | None |
| 9 | `view_crew_work_history` | View Work History | HOD, Captain, Manager | READ | None |
| 10 | `update_crew_member_status` | Activate/Deactivate | Captain, Manager | MUTATE | auth_users_profiles, audit |

**Role Strings**:
- crew, chief_engineer, chief_officer, purser, captain, manager
- HOD = chief_engineer | chief_officer | purser
- All HOD actions also include captain and manager

---

## SEARCH KEYWORDS & ENTITY EXTRACTION

### Domain Keywords
- "crew", "member", "user", "profile", "role", "assign", "revoke", "activate", "deactivate"
- "my profile", "my details", "my work orders", "my tasks"
- "list crew", "crew roster", "who's on board"

### Action-Specific Keywords

| Action | Keywords |
|--------|----------|
| `view_my_profile` | "my profile", "my details", "view my info" |
| `update_my_profile` | "update my profile", "change my name", "edit my details" |
| `view_assigned_work_orders` | "my work orders", "my tasks", "assigned to me" |
| `list_crew_members` | "list crew", "crew roster", "all crew", "who's on board" |
| `assign_role` | "assign role", "make", "promote", "grant" |
| `revoke_role` | "revoke role", "remove", "demote", "revoke" |
| `view_crew_certificates` | "view certificates", "show certs", "qualifications" |
| `view_crew_work_history` | "work history", "completed work orders", "past tasks" |
| `update_crew_member_status` | "deactivate", "activate", "enable", "disable" |

### Entity Extraction Rules

From query text, extract:
- **person_name**: "John Smith", "Jane Doe" (matches auth_users_profiles.name)
- **role**: "chief_engineer", "captain", "manager", "crew", etc.
- **action_intent**: "assign", "revoke", "view", "update", "deactivate"
- **status**: "active", "inactive"

**Examples**:
- "assign chief engineer role to John Smith"
  - person_name=John Smith, role=chief_engineer, action_intent=assign_role
- "show my profile"
  - action_intent=view_my_profile, user_id=auth.uid()
- "deactivate Jane Doe"
  - person_name=Jane Doe, action_intent=update_crew_member_status, is_active=false

---

## ESCAPE HATCHES

| From Crew Lens | To Lens | Trigger | Entity Link |
|----------------|---------|---------|-------------|
| view_crew_certificates | Certificate Lens | Click certificate row | person_name match |
| view_crew_work_history | Work Order Lens | Click WO row | assigned_to match |
| view_assigned_work_orders | Work Order Lens | Click WO row | assigned_to=self |

---

## SUCCESS METRICS

### Step Reduction
| Scenario | Traditional Steps | Celeste Steps | Reduction |
|----------|-------------------|---------------|-----------|
| View own profile | 5 | 2 | 60% |
| Update own profile | 5 | 2 | 60% |
| List all crew | 7 | 3 | 57% |
| Assign role | 8 | 4 | 50% |
| Revoke role | 9 | 5 | 44% |
| View crew certs | 8 | 4 | 50% |
| View assigned WOs | 8 | 3 | 62% |
| Deactivate crew | 7 | 4 | 42% |
| **Average** | **7.1** | **3.4** | **53%** |

### Audit Completeness
- ✅ Every mutation writes to `pms_audit_log`
- ✅ Signature invariant: `{}` for all crew actions (no SIGNED actions)
- ✅ old_values and new_values captured for UPDATE operations
- ✅ user_id, yacht_id, action, entity_type, entity_id always present

### RLS Correctness
- ✅ Self-only profile access (crew can only view/update own profile)
- ✅ HOD can manage roles (assign/revoke)
- ✅ Captain/Manager can update crew status
- ✅ Yacht isolation enforced (cannot see crew from other yachts)
- ✅ Inactive users filtered by RLS

---

## NON-NEGOTIABLES

1. **Backend Authority**: UI never invents actions. Buttons come from `/v1/actions/list`.
2. **Single Surface**: No navigation to "/crew" pages. Search bar drives all.
3. **Server Context**: yacht_id and role derived from JWT. Client yacht_id ignored.
4. **RLS Enforcement**: All queries go through RLS. Service role bypasses only where necessary.
5. **Error Mapping**: 400=validation, 403=RLS, 404=not found, 409=conflict. Never 500.
6. **Audit Invariant**: signature=`{}` for all crew actions. Never NULL.
7. **Soft Delete**: Roles revoked with is_active=false, never deleted.

---

## NEXT STEPS

- [ ] PHASE 2: DB Ground Truth (map to existing tables, field classifications, RLS verification)
- [ ] PHASE 3: Entity Graph (crew → certificates, crew → work orders)
- [ ] PHASE 4: Actions (detailed payload schemas, response envelopes)
- [ ] PHASE 5: Scenarios (detailed flows with example payloads)
- [ ] PHASE 6: SQL Backend (exact queries, parameterization, ownership checks)
- [ ] PHASE 7: RLS Matrix (role × action × expected outcome)
- [ ] PHASE 8: Gaps & Migrations (verify no new migrations needed)

---

**END OF PHASE 1: SCOPE**
