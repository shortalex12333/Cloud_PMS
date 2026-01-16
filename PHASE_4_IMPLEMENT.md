# PHASE 4: IMPLEMENT

**Prerequisite:** PHASE_3_DESIGN.md exists and user approved

**Objective:** Execute the design. Write actual code.

**DO:** Create files, modify code per design
**DO NOT:** Run tests yet, deviate from design

---

## SAFETY GUARDRAILS

### Before Writing Any Code:
1. **Verify you're modifying the correct file** - Read it first
2. **Never write DELETE statements** unless cleaning up TEST_* prefixed data
3. **Never change expectedStatus** to accept failures (200 stays 200)
4. **Use TypeScript strict mode** - catch errors at compile time

### Forbidden Patterns:
```typescript
// NEVER DO THIS:
.delete().eq('yacht_id', id)           // Deletes all yacht data
.delete().eq('work_order_id', id)      // Deletes all order data
expect(response.status).toBe(404)      // When spec says 200
expect(response.status).toBe(500)      // Accept crashes as normal

// ALWAYS DO THIS INSTEAD:
.delete().like('name', 'TEST_%')       // Only test data
expect(response.status).toBe(200)      // Per specification
```

### Self-Check Before Proceeding:
After each file modification, ask:
- Did I create any DELETE without TEST_* filter? If yes, UNDO.
- Did I change any expectedStatus? If yes, UNDO.
- Does this match PHASE_3_DESIGN.md exactly? If no, STOP.

---

## TASK

Follow PHASE_3_DESIGN.md exactly:

1. **Create test fixtures:**
```bash
# Create the files designed in Phase 3
```

2. **Update tests to use fixtures:**
```bash
# Modify test files per design
```

3. **Fix handlers (if designed):**
```bash
# Add validation, error handling per design
```

4. **Create database migrations (if designed):**
```bash
# Create SQL files per design
```

---

## IMPLEMENTATION RULES

1. **Follow the design** - Don't improvise
2. **One file at a time** - Complete each before moving on
3. **No test running** - That's Phase 5
4. **Commit nothing yet** - That's after Phase 5

---

## OUTPUT REQUIRED

Create file: `/Users/celeste7/Documents/Cloud_PMS/PHASE_4_CHANGES.md`

```markdown
# Phase 4 Report: Implementation

## Files Created

### /tests/e2e/fixtures/testData.ts
```typescript
[actual code you wrote]
```
Status: CREATED

### [next file]
...

## Files Modified

### /tests/e2e/microactions/vigorous_test_matrix.spec.ts
Changes:
- Line X: Changed fake UUID to getTestWorkOrderId()
- Line Y: Added import for fixtures

### [next file]
...

## Database Migrations (if any)

### /supabase/migrations/XXXXXX_[name].sql
```sql
[actual SQL]
```

## Summary
- Files created: X
- Files modified: Y
- Lines changed: ~Z
```

---

## STOP CONDITION

When all implementation is complete, STOP and say:

"Phase 4 complete. Changes at /Users/celeste7/Documents/Cloud_PMS/PHASE_4_CHANGES.md. Ready for Phase 5 testing."

**DO NOT run tests or commit without user approval.**
