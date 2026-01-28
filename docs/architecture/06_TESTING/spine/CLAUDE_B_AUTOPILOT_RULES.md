# CLAUDE_B_AUTOPILOT_RULES - Autonomous Testing Protocol

**Generated:** 2026-01-13
**Purpose:** Operating rules for 4-hour autonomous testing sessions

---

## Session Configuration

```
MAX_SESSION_DURATION: 4 hours
CHECKPOINT_INTERVAL: 30 minutes
EVIDENCE_CAPTURE: Required for all mutations
COMMIT_REQUIRED: After each verified fix
```

---

## MUST DO (Non-Negotiable)

### 1. Always Reproduce Locally First

Before any fix:
```bash
# 1. Start local backend
cd /Users/celeste7/Documents/Cloud_PMS/apps/api
uvicorn api.pipeline_service:app --reload --port 8000

# 2. Start local frontend
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm run dev

# 3. Reproduce the issue locally
# 4. Only then apply fix
```

**Rule:** Never fix production without local reproduction.

---

### 2. Add/Modify Automated Test When Fixing Bugs

For every bug fix:
```
1. Write failing test that reproduces bug
2. Apply fix
3. Verify test passes
4. Commit test + fix together
```

Test location pattern:
```
apps/api/tests/test_<module>.py
apps/web/src/__tests__/<component>.test.tsx
```

---

### 3. Capture Evidence for All Mutations

For MUTATE_LOW/MEDIUM/HIGH actions:

```markdown
## Evidence: <action_name>

### Request
```json
POST /v1/actions/execute
{...}
```

### Response
```json
{"success": true, ...}
```

### DB Before
```sql
SELECT * FROM <table> WHERE id = '<id>';
-- <result>
```

### DB After
```sql
SELECT * FROM <table> WHERE id = '<id>';
-- <result showing change>
```

### Audit Log
```sql
SELECT * FROM audit_log WHERE entity_id = '<id>' ORDER BY created_at DESC LIMIT 1;
-- <audit entry>
```
```

---

### 4. Commit Format

```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description>

- <bullet point 1>
- <bullet point 2>

Evidence: <link to AUTOPILOT_LOG.md section>
Test: <test file if applicable>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

Types: `fix`, `feat`, `test`, `docs`, `refactor`
Scopes: `auth`, `search`, `pms`, `tenant`, `frontend`, `api`

---

### 5. Checkpoint Every 30 Minutes

At each checkpoint:
1. Update AUTOPILOT_LOG.md with progress
2. Commit any pending changes
3. Run test suite
4. Record pass/fail counts

---

### 6. Verify Before Claiming Success

For each test case:
```
[ ] API returns expected status code
[ ] Response body matches expected structure
[ ] DB state changed correctly (for mutations)
[ ] Audit log entry created (for mutations)
[ ] No console errors (for frontend tests)
```

---

## MUST NEVER (Violations)

### 1. Never Assume - Always Verify

```
BAD:  "The function probably exists"
GOOD: "SELECT proname FROM pg_proc WHERE proname = 'get_my_bootstrap';" → verified exists
```

Always run the verification query/command.

---

### 2. Never Change Architecture Without ADR

If a fix requires:
- New table or column
- New RPC function
- Changed auth flow
- New environment variable
- Modified API contract

Then STOP and:
1. Document proposed change
2. Add to UNKNOWNS section in AUTOPILOT_LOG.md
3. Flag for human review
4. Do NOT implement

---

### 3. Never Hardcode Tenant IDs

```python
# BAD
yacht_id = "TEST_YACHT_001"

# GOOD
yacht_id = user.yacht_id  # From JWT claim
```

All tenant resolution must go through auth middleware.

---

### 4. Never Skip Error Handling

```python
# BAD
result = await client.search(query)
return result

# GOOD
try:
    result = await client.search(query)
    if not result.success:
        logger.error(f"Search failed: {result.error}")
        raise HTTPException(status_code=500, detail="Search failed")
    return result
except Exception as e:
    logger.exception("Unexpected error in search")
    raise HTTPException(status_code=500, detail="Internal error")
```

---

### 5. Never Modify Production Database Directly

```
BAD:  Run INSERT/UPDATE directly on production Supabase
GOOD: Create migration file, apply via migration process
```

Exception: Test data seeding in designated test tenant only.

---

### 6. Never Push Without Tests Passing

```bash
# Before push
npm run test        # Frontend tests
pytest              # Backend tests
npm run typecheck   # TypeScript
npm run lint        # Linting

# All must pass before push
```

---

## Decision Trees

### DT1: Error Encountered

```
Error encountered
    │
    ├── Is it in ERROR_PLAYBOOK.md?
    │   ├── YES → Follow playbook steps
    │   └── NO  → Add to UNKNOWNS, document symptoms
    │
    ├── Can reproduce locally?
    │   ├── YES → Debug and fix
    │   └── NO  → Document exact reproduction steps that fail
    │
    └── Fix requires architecture change?
        ├── YES → STOP, flag for human review
        └── NO  → Implement fix with test
```

### DT2: Test Case Failure

```
Test fails
    │
    ├── Is it environment issue? (missing env var, wrong URL)
    │   ├── YES → Check ENVIRONMENT_CONTRACT.md, fix config
    │   └── NO  → Continue
    │
    ├── Is it data issue? (missing test data)
    │   ├── YES → Seed required data, document in log
    │   └── NO  → Continue
    │
    └── Is it code bug?
        ├── YES → Write failing test, fix, verify, commit
        └── NO  → Document exact failure for human review
```

### DT3: New Feature Needed

```
Feature needed for test
    │
    ├── Is it in ACTION_TEST_MATRIX.md?
    │   ├── YES → Implement according to spec
    │   └── NO  → STOP, flag for human review
    │
    └── Requires new table/column/RPC?
        ├── YES → STOP, flag for human review
        └── NO  → Implement with full test coverage
```

---

## Evidence Requirements by Classification

### READ Actions
```
Required:
- API request/response
- No DB mutation verification needed
```

### MUTATE_LOW Actions
```
Required:
- API request/response
- DB before/after for affected row
- audit_log entry
```

### MUTATE_MEDIUM Actions
```
Required:
- API request/response
- DB before/after for affected row
- audit_log entry
- Related table changes (e.g., work_order_parts when adding part)
```

### MUTATE_HIGH Actions
```
Required:
- API request/response
- DB before/after for ALL affected tables
- audit_log entry
- Signature verification (if applicable)
- Full audit trail
```

---

## Logging Protocol

### Console Output Format
```
[HH:MM:SS] [LEVEL] [COMPONENT] Message
```

Example:
```
[14:32:15] [INFO] [TEST] Starting test: create_work_order
[14:32:16] [PASS] [TEST] create_work_order - WO created with ID abc123
[14:32:16] [INFO] [DB] Verified audit_log entry created
```

### AUTOPILOT_LOG.md Entry Format
```markdown
## Run: 2026-01-13T14:30:00Z

### Summary
- Tests run: 20
- Passed: 18
- Failed: 2
- Skipped: 0

### Commits
- abc1234: fix(auth): correct JWT validation

### Failed Tests
| Test | Error | Action |
|------|-------|--------|
| test_search | 401 Unauthorized | Added to UNKNOWNS |

### Unknowns
| Item | Command to Resolve |
|------|-------------------|
| JWT secret mismatch | Verify MASTER_SUPABASE_JWT_SECRET in Render |
```

---

## Recovery Procedures

### If Session Crashes
1. Read last checkpoint from AUTOPILOT_LOG.md
2. Verify last committed state
3. Resume from last successful test

### If Database Corrupted
1. STOP all testing
2. Document exact state
3. Flag for human intervention
4. Do NOT attempt to fix

### If Auth Breaks
1. Re-run B1-B3 from GO_NO_GO_CHECKLIST.md
2. Verify env vars match ENVIRONMENT_CONTRACT.md
3. Check Supabase status page

---

## Session Boundaries

### What This Session CAN Do
- Run tests from ACTION_TEST_MATRIX.md
- Fix bugs found during testing
- Add tests for bugs fixed
- Seed test data in TEST_YACHT_001 tenant
- Update documentation for clarity

### What This Session CANNOT Do
- Change database schema
- Add new environment variables
- Modify auth flow
- Change API contracts
- Access production data (non-test tenants)
- Deploy to production

---

## Exit Criteria

### Successful Exit
- All GO_NO_GO_CHECKLIST.md checks pass
- Minimum 15 microactions tested (per checklist)
- All MUTATE actions have evidence captured
- AUTOPILOT_LOG.md updated with final summary
- All changes committed

### Failed Exit
- Document blocking issue
- Commit all progress made
- Update AUTOPILOT_LOG.md with failure reason
- List UNKNOWNS for human review

---

**Last Updated:** 2026-01-13
