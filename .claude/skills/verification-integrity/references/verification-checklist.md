# Verification Checklist

**Complete pre-flight and post-flight checks for every verification cycle.**

---

## Pre-Verification Checklist

Run BEFORE executing tests or verification commands.

### Environment Ready

```
[ ] Docker/services running?
    └── docker ps | grep -E "api|postgres|redis"
    └── If empty: docker compose up -d

[ ] Correct port exposed?
    └── curl -s http://localhost:8000/health || echo "WRONG PORT"
    └── Check: docker ps --format "{{.Ports}}"

[ ] Database accessible?
    └── docker exec postgres pg_isready -U postgres
    └── If fails: check POSTGRES_* env vars

[ ] Database seeded with test data?
    └── Check: SELECT COUNT(*) FROM <table>;
    └── If empty: run seed script

[ ] Auth tokens configured?
    └── echo $JWT_TOKEN | cut -d. -f2 | base64 -d | jq '.exp'
    └── Compare to: date +%s

[ ] Environment variables set?
    └── docker exec api env | grep -E "DATABASE|REDIS|API_KEY"
    └── Check .env.local exists and is mounted

[ ] Migrations applied?
    └── Check: SELECT * FROM schema_migrations ORDER BY version DESC LIMIT 5;
    └── If missing: supabase db push / alembic upgrade head
```

### Test Quality

```
[ ] Test file exists and is not empty?
    └── wc -l tests/test_<feature>.py

[ ] Test is not skipped?
    └── grep -c "@skip\|@pytest.mark.skip" tests/test_<feature>.py
    └── Should be 0

[ ] Assertions are present?
    └── grep -c "assert" tests/test_<feature>.py
    └── Should be > 0

[ ] Testing what I actually changed?
    └── Compare test file paths to changed file paths
    └── Related tests should exist

[ ] Not over-mocked?
    └── grep -c "@patch\|@mock" tests/test_<feature>.py
    └── High count = suspicious
```

---

## Post-Failure Checklist

Run AFTER a test fails to determine if it's a REAL failure.

### HTTP 4xx Errors

```
┌─────────────────────────────────────────────────────────────────────┐
│  GOT 401 UNAUTHORIZED                                               │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Is Authorization header present in request?                    │
│  [ ] Is token format correct? (Bearer <token>)                      │
│  [ ] Is token expired? (check exp claim)                            │
│  [ ] Is token signed with correct secret?                           │
│                                                                     │
│  If ANY unchecked → FALSE FAILURE (auth issue, not code)            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  GOT 403 FORBIDDEN                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Does user have required role for this endpoint?                │
│  [ ] Is RLS policy correct for this operation?                      │
│  [ ] Is yacht_id in JWT matching resource's yacht_id?               │
│                                                                     │
│  If ANY unchecked → FALSE FAILURE (permission issue, not code)      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  GOT 404 NOT FOUND                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Is route registered? (check OpenAPI schema)                    │
│  [ ] Is router mounted in main app?                                 │
│  [ ] Is URL path correct? (/v1/ vs /api/v1/ vs /api/)               │
│  [ ] Does resource exist in database?                               │
│  [ ] Is RLS blocking the SELECT?                                    │
│                                                                     │
│  If ANY unchecked → FALSE FAILURE (routing/data issue, not code)    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  GOT 405 METHOD NOT ALLOWED                                         │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Is test using correct HTTP method? (GET vs POST vs PUT)        │
│  [ ] Does endpoint support this method?                             │
│                                                                     │
│  If ANY unchecked → FALSE FAILURE (wrong method, not code)          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  GOT 422 UNPROCESSABLE ENTITY                                       │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Does request body match expected schema?                       │
│  [ ] Are required fields present?                                   │
│  [ ] Are field types correct? (string vs int vs uuid)               │
│                                                                     │
│  If ANY unchecked → FALSE FAILURE (bad test payload, not code)      │
└─────────────────────────────────────────────────────────────────────┘
```

### HTTP 5xx Errors

```
┌─────────────────────────────────────────────────────────────────────┐
│  GOT 500 INTERNAL SERVER ERROR                                      │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Check container logs: docker logs api --tail 50                │
│  [ ] Is it a missing env var? (KeyError in logs)                    │
│  [ ] Is it a database connection issue?                             │
│  [ ] Is it a missing dependency? (ImportError)                      │
│  [ ] Is it a migration issue? (column does not exist)               │
│                                                                     │
│  If config/env issue → FALSE FAILURE                                │
│  If actual exception in business logic → REAL FAILURE               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  GOT 502/503/504 GATEWAY ERRORS                                     │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Is upstream service running?                                   │
│  [ ] Is network configured correctly?                               │
│  [ ] Is service still starting up?                                  │
│                                                                     │
│  Almost always FALSE FAILURE (infrastructure, not code)             │
└─────────────────────────────────────────────────────────────────────┘
```

### Other Failures

```
┌─────────────────────────────────────────────────────────────────────┐
│  CONNECTION REFUSED                                                 │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Is service running? docker ps                                  │
│  [ ] Is port correct? (8000 vs 8080 vs 3000)                        │
│  [ ] Is host correct? (localhost vs 127.0.0.1 vs container name)    │
│  [ ] Is Docker network configured?                                  │
│                                                                     │
│  Almost always FALSE FAILURE                                        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  TIMEOUT ERROR                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Manual curl completes in reasonable time?                      │
│  [ ] Is CI runner overloaded?                                       │
│  [ ] Is test timeout too aggressive?                                │
│  [ ] Is there a deadlock or infinite loop?                          │
│                                                                     │
│  If manual curl fast → FALSE FAILURE (test config)                  │
│  If manual curl slow → Investigate code                             │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  ASSERTION ERROR                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Does expected value match CURRENT spec? (not old spec)         │
│  [ ] Is test comparing right things?                                │
│  [ ] Is test data seeded correctly?                                 │
│  [ ] Is previous test polluting state?                              │
│                                                                     │
│  If test expects old behavior → FALSE FAILURE (update test)         │
│  If test expects current behavior → REAL FAILURE                    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  FLAKY (PASSES SOMETIMES)                                           │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Is there a race condition in TEST (not code)?                  │
│  [ ] Is test order-dependent?                                       │
│  [ ] Is test using shared mutable state?                            │
│  [ ] Is test relying on timing?                                     │
│                                                                     │
│  Usually FALSE FAILURE (test quality issue)                         │
│  Rarely: actual race condition in code                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Post-Success Checklist

Run AFTER a test passes to determine if it's a REAL success.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TEST REPORTED "PASS"                                               │
├─────────────────────────────────────────────────────────────────────┤
│  [ ] Did test actually RUN? (not skipped)                           │
│      └── pytest output should NOT show "SKIPPED"                    │
│      └── grep -i "skip" in test output                              │
│                                                                     │
│  [ ] Are ASSERTIONS present in test code?                           │
│      └── grep "assert" tests/test_<feature>.py                      │
│      └── If 0 assertions → FALSE SUCCESS                            │
│                                                                     │
│  [ ] Do assertions check CONTENT (not just type/length)?            │
│      └── assert len(x) > 0  ← WEAK (false success risk)             │
│      └── assert x[0]["id"] == expected_id  ← STRONG                 │
│                                                                     │
│  [ ] Is response BODY correct (not just status code)?               │
│      └── assert status == 200  ← WEAK                               │
│      └── assert body["success"] == True  ← BETTER                   │
│      └── assert body["data"]["id"] == expected  ← STRONG            │
│                                                                     │
│  [ ] Did REAL code run (not mocked away)?                           │
│      └── If @patch on the function under test → FALSE SUCCESS       │
│      └── Mock only EXTERNAL dependencies                            │
│                                                                     │
│  [ ] Would this test CATCH A REGRESSION?                            │
│      └── If behavior changed, would test fail?                      │
│      └── If test always passes regardless → FALSE SUCCESS           │
│                                                                     │
│  ALL CHECKED? → REAL SUCCESS                                        │
│  ANY UNCHECKED? → FALSE SUCCESS — strengthen the test               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Commands Reference

### Pre-Flight

```bash
# Check services
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check health
curl -s http://localhost:8000/health | jq

# Check env vars
docker exec api env | sort | grep -E "DATABASE|REDIS|JWT|API"

# Check database
docker exec postgres psql -U postgres -c "SELECT COUNT(*) FROM pms_work_orders;"

# Check migrations
docker exec postgres psql -U postgres -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 3;"

# Check token validity
echo $JWT | cut -d. -f2 | base64 -d 2>/dev/null | jq '{exp: .exp, now: now} | .exp > .now'
```

### Post-Failure Diagnosis

```bash
# Container logs
docker logs api --tail 100 2>&1 | grep -i error

# Route check
curl -s http://localhost:8000/openapi.json | jq '.paths | keys[]' | grep -i <endpoint>

# Auth debug
curl -v -H "Authorization: Bearer $JWT" http://localhost:8000/v1/protected 2>&1 | head -30

# Database query check
docker exec postgres psql -U postgres -c "EXPLAIN ANALYZE SELECT * FROM pms_work_orders WHERE id = 'uuid';"

# RLS check
docker exec postgres psql -U postgres -c "SELECT tablename, policyname, cmd FROM pg_policies WHERE tablename = 'pms_work_orders';"
```

### Post-Success Verification

```bash
# Count assertions
grep -c "assert" tests/test_<feature>.py

# Count mocks
grep -c "@patch\|@mock\|Mock(" tests/test_<feature>.py

# Check for skips
grep -i "skip" tests/test_<feature>.py

# Check for empty tests
grep -A3 "def test_" tests/test_<feature>.py | grep -B1 "pass$"

# Run single test isolated
pytest tests/test_<feature>.py::test_<name> -v --tb=short
```

---

## Verification Report Template

After completing verification, document results:

```markdown
## Verification Report: [Feature/Test Name]

**Date:** YYYY-MM-DD
**Verifier:** [Agent/Human]

### Pre-Flight
- [ ] Environment ready
- [ ] Services running
- [ ] Auth configured
- [ ] Data seeded

### Test Execution
- **Command:** `pytest tests/test_x.py -v`
- **Result:** PASS / FAIL
- **Duration:** X seconds

### Signal Analysis

**If FAIL:**
- [ ] Checked auth configuration
- [ ] Checked route registration
- [ ] Checked environment variables
- [ ] Checked database state
- [ ] Reviewed container logs

**Verdict:** REAL FAILURE / FALSE FAILURE
**Evidence:** [specific reason]

**If PASS:**
- [ ] Test actually ran (not skipped)
- [ ] Assertions present and meaningful
- [ ] Response content verified (not just status)
- [ ] Real code executed (not over-mocked)

**Verdict:** REAL SUCCESS / FALSE SUCCESS
**Evidence:** [specific reason]

### Action Taken
- [What was done based on verdict]

### Confidence
- HIGH / MEDIUM / LOW
- [Reason for confidence level]
```

---

## Integration with GSD Phases

### VERIFICATION MODE Enhanced

Standard verification becomes:

```
1. Run pre-flight checklist
2. Execute tests
3. If FAIL → Run post-failure checklist → Determine REAL vs FALSE
4. If PASS → Run post-success checklist → Determine REAL vs FALSE
5. Document in verification report
6. Only proceed if REAL SUCCESS confirmed
```

### Phase Completion Criteria

A phase is NOT complete until:

```
[ ] All tests pass
[ ] All passes are REAL successes (not false)
[ ] Verification report documented
[ ] No skipped tests in scope
[ ] Assertions cover actual behavior
```

---

## The Golden Rule

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  NEVER TRUST A SIGNAL AT FACE VALUE                                           ║
║                                                                               ║
║  FAIL might mean: auth, routing, env, test quality — not your code            ║
║  PASS might mean: skipped, no assertions, wrong assertions — not correctness  ║
║                                                                               ║
║  ALWAYS ASK: Is this signal telling me what I think it's telling me?          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```
