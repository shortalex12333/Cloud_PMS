# False Failure Patterns

**Reference document for diagnosing failures that aren't real failures.**

---

## Definition

A **false failure** is when a test or verification step fails, but the code being tested is actually correct. The failure is caused by something other than the code.

---

## Pattern Taxonomy

### 1. Authentication & Authorization Failures

#### 1.1 Missing Auth Token

**Signal:** `401 Unauthorized`

**False Because:** Code works, but test didn't provide authentication.

**Detection:**
```bash
# Check if request includes auth header
curl -v http://localhost:8000/api/protected 2>&1 | grep -i authorization
# If no Authorization header, that's the problem
```

**Fix:**
```bash
# Add auth header
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/protected
```

---

#### 1.2 Expired Token

**Signal:** `401 Unauthorized` or `403 Forbidden`

**False Because:** Code works, token just expired.

**Detection:**
```bash
# Decode JWT and check exp claim
echo $TOKEN | cut -d. -f2 | base64 -d | jq '.exp'
# Compare to current timestamp
date +%s
```

**Fix:**
```bash
# Refresh token before test
export TOKEN=$(curl -X POST .../auth/refresh | jq -r '.access_token')
```

---

#### 1.3 Wrong Role/Permissions

**Signal:** `403 Forbidden`

**False Because:** Endpoint works, user just lacks permission.

**Detection:**
```bash
# Check user role
echo $TOKEN | cut -d. -f2 | base64 -d | jq '.role'
# Is this role in allowed_roles for the endpoint?
```

**Fix:**
```bash
# Use a user with correct role for test
export TOKEN=$ADMIN_TOKEN  # or engineer, captain, etc.
```

---

### 2. Routing & Endpoint Failures

#### 2.1 Route Not Mounted

**Signal:** `404 Not Found`

**False Because:** Handler code exists, but router not included in app.

**Detection:**
```bash
# Check OpenAPI schema for route
curl -s http://localhost:8000/openapi.json | jq '.paths | keys[]' | grep -i prepare
# If not listed, route isn't mounted
```

**Fix:**
```python
# In main app (e.g., pipeline_service.py)
app.include_router(actions_router, prefix="/v1/actions")
```

---

#### 2.2 Wrong HTTP Method

**Signal:** `405 Method Not Allowed`

**False Because:** Endpoint exists, test using wrong method.

**Detection:**
```bash
# Check what methods are allowed
curl -X OPTIONS http://localhost:8000/api/resource -v 2>&1 | grep Allow
# Compare to what test is using
```

**Fix:**
```bash
# Use correct method
curl -X POST ...  # not GET
```

---

#### 2.3 Wrong URL Path

**Signal:** `404 Not Found`

**False Because:** Endpoint exists at different path.

**Detection:**
```bash
# Check actual registered routes
curl -s http://localhost:8000/openapi.json | jq '.paths | keys[]'
# Find the correct path
```

**Common Mistakes:**
- `/api/v1/` vs `/v1/`
- `/users` vs `/user`
- Trailing slash: `/api/` vs `/api`

---

### 3. Environment & Configuration Failures

#### 3.1 Wrong Port

**Signal:** `Connection refused`

**False Because:** Service running, but on different port.

**Detection:**
```bash
# What port is service listening on?
docker ps --format "{{.Names}} {{.Ports}}"
# Or check process
lsof -i :8000
```

**Fix:**
```bash
# Use correct port
curl http://localhost:8080/...  # not 8000
```

---

#### 3.2 Service Not Running

**Signal:** `Connection refused` or `No route to host`

**False Because:** Code is fine, service just not started.

**Detection:**
```bash
# Is container running?
docker ps | grep api
# Is process running?
ps aux | grep uvicorn
```

**Fix:**
```bash
docker compose up -d api
# Or
./scripts/local-dev.sh start
```

---

#### 3.3 Missing Environment Variable

**Signal:** `500 Internal Server Error` with KeyError or similar

**False Because:** Code is correct, env var not set.

**Detection:**
```bash
# Check container env
docker exec api env | grep DATABASE
# Check for required vars
grep -r "os.environ" apps/api/ | head -20
```

**Fix:**
```bash
# Set missing env var
export DATABASE_URL=postgresql://...
# Or add to .env file
```

---

#### 3.4 Database Not Seeded

**Signal:** `404 Not Found` or empty response

**False Because:** Query works, but no data to return.

**Detection:**
```bash
# Check if data exists
docker exec postgres psql -U postgres -c "SELECT COUNT(*) FROM users;"
```

**Fix:**
```bash
# Seed test data
docker exec api python scripts/seed_test_data.py
```

---

### 4. Test Framework Failures

#### 4.1 Test Expects Old Behavior

**Signal:** `AssertionError: expected X but got Y`

**False Because:** New code is correct, test expects old behavior.

**Detection:**
- Read the assertion
- Check if expected value matches OLD spec
- Check git history for when expectation was set

**Fix:**
```python
# Update test to match new spec
assert response.status == "active"  # was "pending" in old version
```

---

#### 4.2 Timeout (Not Code Slowness)

**Signal:** `TimeoutError` or test killed

**False Because:** Code isn't slow, test runner is constrained.

**Detection:**
```bash
# Time the operation manually
time curl http://localhost:8000/api/slow-endpoint
# If it completes in reasonable time, test timeout is too short
```

**Fix:**
```python
# Increase timeout
@pytest.mark.timeout(60)  # was 10
def test_slow_operation():
    ...
```

---

#### 4.3 Flaky Test (Race Condition in Test)

**Signal:** Intermittent failure, passes on retry

**False Because:** Code is correct, test has race condition.

**Detection:**
- Run test 10 times, count failures
- If inconsistent, likely flaky
- Check for async operations without proper waits

**Fix:**
```python
# Add proper wait
await asyncio.sleep(0.1)  # or use proper synchronization
# Or use retry decorator for inherently flaky operations
```

---

#### 4.4 Test Pollution (Order Dependency)

**Signal:** Test passes alone, fails in suite

**False Because:** Previous test left state that breaks this test.

**Detection:**
```bash
# Run test alone
pytest tests/test_user.py::test_create -v
# Run full suite
pytest tests/test_user.py -v
# Compare results
```

**Fix:**
```python
# Add proper cleanup
@pytest.fixture(autouse=True)
def reset_state():
    yield
    db.rollback()
```

---

### 5. Infrastructure Failures

#### 5.1 Docker Build Cache Stale

**Signal:** Old behavior despite code change

**False Because:** Container running old code.

**Detection:**
```bash
# Check when image was built
docker images --format "{{.Repository}} {{.CreatedAt}}" | grep api
```

**Fix:**
```bash
docker compose build --no-cache api
docker compose up -d api
```

---

#### 5.2 Database Migration Not Run

**Signal:** Column/table doesn't exist errors

**False Because:** Code expects new schema, DB has old schema.

**Detection:**
```sql
-- Check if column exists
SELECT column_name FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'new_field';
```

**Fix:**
```bash
# Run migrations
supabase db push
# Or
alembic upgrade head
```

---

#### 5.3 Network Partition

**Signal:** `Connection refused` between services

**False Because:** Services work, can't reach each other.

**Detection:**
```bash
# Check if services on same network
docker network inspect celeste-network
```

**Fix:**
```yaml
# Ensure services on same network
services:
  api:
    networks:
      - celeste-network
  db:
    networks:
      - celeste-network
```

---

## False Failure Decision Tree

```
FAILURE RECEIVED
      │
      ├── 401/403?
      │     └── Check: Token present? Valid? Correct role?
      │           └── NO → FALSE FAILURE (auth issue)
      │
      ├── 404?
      │     └── Check: Route in OpenAPI? Correct path?
      │           └── NO → FALSE FAILURE (routing issue)
      │
      ├── 500?
      │     └── Check: Env vars set? DB connected? Migrations run?
      │           └── NO → FALSE FAILURE (config issue)
      │
      ├── Connection refused?
      │     └── Check: Service running? Correct port? Network ok?
      │           └── NO → FALSE FAILURE (infra issue)
      │
      ├── Timeout?
      │     └── Check: Manual curl fast? CI runner slow?
      │           └── YES fast manually → FALSE FAILURE (test timeout)
      │
      ├── Flaky (sometimes passes)?
      │     └── Check: Race condition in test? State pollution?
      │           └── YES → FALSE FAILURE (test quality)
      │
      └── Assertion error?
            └── Check: Does expected value match current spec?
                  └── NO → FALSE FAILURE (outdated test)
```

---

## Quick Diagnostic Commands

```bash
# Auth check
curl -v -H "Authorization: Bearer $TOKEN" $URL 2>&1 | head -30

# Route check
curl -s $BASE/openapi.json | jq '.paths | keys[]'

# Service check
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Env check
docker exec $CONTAINER env | sort

# DB check
docker exec $DB psql -U postgres -c "SELECT version();"

# Network check
docker network inspect $NETWORK | jq '.[0].Containers'

# Manual timing
time curl -s $URL > /dev/null
```
