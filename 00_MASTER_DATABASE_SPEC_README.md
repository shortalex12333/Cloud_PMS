# CELESTEOS DATABASE COMPLETE SPECIFICATION
**Master Index & Implementation Guide**

## OVERVIEW

This master specification defines the complete CelesteOS database architecture for all 67+ micro-actions, situational states, and user journeys.

**Total Specification Lines:** 10,000+ (across all files)
**Database:** PostgreSQL 15+ (Supabase)
**Security:** Row Level Security (RLS) on ALL tables
**Audit:** Complete accountability trail
**User Roles:** 9 distinct roles with capability matrix

---

## SPECIFICATION FILES

### 1. DATABASE_SCHEMA_EXECUTION_SPEC.md (Part 1)
**Lines:** 588
**Contains:**
- Core domain tables (Yachts, Users, Equipment, Faults, Work Orders)
- User role definitions and capability matrix
- Foreign key patterns and RLS policies
- Basic audit trail structure

### 2. DATABASE_SCHEMA_EXECUTION_SPEC_PART2.md
**Lines:** 565
**Contains:**
- Notes (timeline pattern)
- Parts & Inventory
- Inventory Transactions (ledger pattern)
- Handover (shift communication)
- Documents (manuals, SOPs, drawings)

### 3. DATABASE_SCHEMA_EXECUTION_SPEC_PART3.md
**Lines:** 883
**Contains:**
- Document Chunks (RAG/semantic search)
- Shopping List (procurement queue with state machine)
- Purchase Orders
- Receiving Sessions (Checkbox = Truth pattern)
- Complete Audit Log structure
- User role decision matrix
- Signature requirements

### 4. COMPLETE_ACTION_CATALOG_SPEC.md
**Lines:** 1,175+
**Contains:**
- Complete action taxonomy (67+ actions)
- Customer journey specifications
- Guard rails and error handling
- Multi-stage action flows
- Undo/cancel patterns
- Detailed examples: diagnose_fault, create_work_order, show_manual_section

### 5. ACTION_SYSTEM_ARCHITECTURE.md (Pre-existing)
**Contains:**
- Action registry and offering logic
- Query intent parsing
- Document context extraction
- Triggering logic and thresholds
- Entity-action matrix

### 6. ACTION_TRIGGERS_AND_FLOWS.md (Pre-existing)
**Contains:**
- Visual entity relationship diagrams
- Complete trigger conditions matrix
- SQL trigger queries
- Cross-entity action flows
- Situational state machines

### 7. HANDOVER_IMPLEMENTATION_PLAN.md (Pre-existing)
**Contains:**
- Complete handover feature specification
- Frontend modal patterns
- API contracts
- Display components

---

## KEY IMPLEMENTATION PATTERNS

### PATTERN 1: Row Level Security (RLS)
**EVERY table MUST:**
```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view on own yacht" ON table_name
    FOR SELECT TO authenticated
    USING (yacht_id IN (
        SELECT yacht_id FROM user_profiles WHERE id = auth.uid()
    ));
```

### PATTERN 2: Audit Trail
**HIGH-RISK mutations MUST create audit log:**
```sql
INSERT INTO pms_audit_log (
    yacht_id, action, entity_type, entity_id,
    user_id, user_role, old_values, new_values,
    changes_summary, signature, created_at
) VALUES (...);
```

### PATTERN 3: Multi-Stage Actions
**Stages:**
1. Prefill (READ - fetch context)
2. User edits (NO MUTATION - form state)
3. Preview (READ - show effects)
4. Execute (MUTATE - BEGIN/COMMIT transaction)
5. Success (READ - confirmation)

### PATTERN 4: Checkbox = Truth (Receiving)
**CRITICAL RULE:**
```sql
-- Only process checked items
FOR item IN
    SELECT * FROM receiving_items
    WHERE receiving_session_id = $session_id
    AND checked = TRUE  -- CHECKBOX = TRUTH
LOOP
    -- Process item
END LOOP;
```

### PATTERN 5: Situational State Machines
**States:**
- Shopping List: CANDIDATE → ACTIVE → COMMITTED → FULFILLED
- Receiving: CANDIDATE → ACTIVE → REVIEW → COMMITTED
- Finance: Shadow of Shopping List + Receiving

---

## USER ROLE CAPABILITIES

| Role | View | Create Faults | Create WO | Close WO | Approve $ | Commit Receiving |
|------|------|---------------|-----------|----------|-----------|------------------|
| Crew | ✅ | ✅ | ❌ | ❌ | $0 | ❌ |
| Engineer | ✅ | ✅ | ✅ | ❌ | $0 | ❌ |
| 2nd Engineer | ✅ | ✅ | ✅ | ✅* | $500 | ✅* |
| Chief Engineer | ✅ | ✅ | ✅ | ✅ | $5,000 | ✅ |
| Captain | ✅ | ✅ | ✅ | ✅ | $50,000 | ✅ |
| Admin | ✅ | ✅ | ✅ | ✅ | ∞ | ✅ |

*Conditional: 2nd Engineer can close WO only if hours < 8, commit receiving only if value < $1000

---

## CRITICAL SECURITY RULES

1. **NEVER bypass yacht isolation** - Every query MUST filter by user's yacht_id
2. **NEVER bypass RLS** - Use service role with extreme caution
3. **ALWAYS validate user role** - Check permissions before mutations
4. **ALWAYS create audit logs** - For high-risk actions
5. **ALWAYS use transactions** - BEGIN/COMMIT for multi-table mutations

---

## DATABASE CONNECTION

```bash
# Supabase credentials
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**WARNING:** Service role bypasses RLS. Only use in trusted backend functions.

---

## MIGRATION ORDER

1. Create extensions (uuid-ossp, vector)
2. Create core tables (yachts, user_profiles)
3. Create equipment tables
4. Create fault tables
5. Create work order tables
6. Create parts & inventory tables
7. Create document tables
8. Create shopping list tables
9. Create receiving tables
10. Create audit log table
11. Create all indexes
12. Create all RLS policies
13. Create helper functions
14. Create triggers

---

## ACTION IMPLEMENTATION CHECKLIST

For EACH action (67+ total):

- [ ] Define classification (READ/MUTATE_LOW/MUTATE_MEDIUM/MUTATE_HIGH)
- [ ] Define allowed roles
- [ ] Define entity contexts (where action appears)
- [ ] Define situational states (when action is available)
- [ ] Define database tables affected
- [ ] Define prefill query (if applicable)
- [ ] Define preview query (if applicable)
- [ ] Define execute transaction (exact SQL)
- [ ] Define audit log entry
- [ ] Define error handling (10+ scenarios)
- [ ] Define undo/cancel pattern
- [ ] Define signature requirement
- [ ] Define follow-up actions

---

## NEXT STEPS

1. **Review all specification files** - Understand complete architecture
2. **Create migration SQL** - Implement all tables with RLS
3. **Implement backend handlers** - One file per action cluster
4. **Create frontend modals** - Following exact patterns
5. **Test with real user journeys** - All roles, all edge cases
6. **Deploy to production** - With complete audit trail

---

## MAINTENANCE

**When adding NEW actions:**
1. Add to COMPLETE_ACTION_CATALOG_SPEC.md
2. Update ACTION_SYSTEM_ARCHITECTURE.md (action registry)
3. Create handler function in appropriate cluster file
4. Add frontend modal/component
5. Update user role matrix if new permissions needed
6. Add RLS policy if new table created
7. Document in this README

**When modifying EXISTING actions:**
1. Update specification docs first
2. Update database schema if table changes needed
3. Update handler function
4. Update frontend component
5. Test all user roles
6. Document breaking changes

---

## SUPPORT

Questions? Issues? Contact the development team.

This specification is CANONICAL and COMPLETE.
All implementation MUST follow these patterns exactly.

**Last Updated:** 2026-01-11
**Version:** 1.0 Final
