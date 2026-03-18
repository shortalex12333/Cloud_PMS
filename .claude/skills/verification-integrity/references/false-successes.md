# False Success Patterns

**Reference document for detecting successes that aren't real successes.**

---

## Definition

A **false success** is when a test or verification step passes, but the code being tested is actually incorrect or untested. The success signal is misleading.

---

## The Danger

False successes are **more dangerous** than false failures because:
- False failure: You investigate, find the issue, move on
- False success: You ship broken code with confidence

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  A FALSE SUCCESS IS WORSE THAN A FALSE FAILURE                                ║
║  You ship broken code thinking it works                                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Pattern Taxonomy

### 1. Test Didn't Actually Run

#### 1.1 Skipped Test

**Signal:** Test suite shows "PASS" or no failures

**False Because:** Test was skipped, never executed.

**Detection:**
```bash
# Look for skip markers
pytest tests/ -v 2>&1 | grep -i skip
# Count skipped
pytest tests/ -v 2>&1 | grep -c "SKIPPED"
```

**Common Skip Patterns:**
```python
@pytest.mark.skip(reason="TODO: fix later")  # DANGER
@pytest.mark.skipif(os.getenv("CI"), reason="Skip in CI")  # DANGER
@unittest.skip("Not implemented")  # DANGER
```

**Fix:**
```python
# Remove skip and fix the test
# @pytest.mark.skip  ← DELETE THIS
def test_critical_behavior():
    ...
```

---

#### 1.2 Conditional Skip That Always Triggers

**Signal:** Test passes in CI, never actually runs

**False Because:** Skip condition is always true.

**Detection:**
```python
# This always skips in CI
@pytest.mark.skipif(os.getenv("CI") == "true", reason="...")
# CI always sets CI=true, so test never runs where it matters
```

**Fix:**
```python
# Run in CI, skip only locally if needed
@pytest.mark.skipif(not os.getenv("CI"), reason="Integration test, CI only")
```

---

#### 1.3 Test Commented Out

**Signal:** Test count decreasing over time

**False Because:** Test exists but is commented.

**Detection:**
```bash
# Find commented tests
grep -r "# def test_" tests/
grep -r "# async def test_" tests/
```

**Fix:**
- Uncomment and fix the test
- Or delete it entirely (don't leave zombie code)

---

### 2. Assertions Missing or Meaningless

#### 2.1 No Assertions

**Signal:** Test completes without error

**False Because:** Nothing was verified.

**Detection:**
```python
# This "passes" but verifies nothing
def test_create_user():
    response = client.post("/users", json={"name": "test"})
    # WHERE ARE THE ASSERTIONS?
```

**Fix:**
```python
def test_create_user():
    response = client.post("/users", json={"name": "test"})
    assert response.status_code == 201
    assert response.json()["name"] == "test"
    assert "id" in response.json()
```

---

#### 2.2 Assert True/Pass

**Signal:** Test passes always

**False Because:** Assertion can never fail.

**Detection:**
```python
# These always pass
assert True
assert 1 == 1
self.assertTrue(True)
pass
```

**Fix:**
```python
# Assert on actual behavior
assert response.status_code == 200
assert len(items) == expected_count
```

---

#### 2.3 Assert on Length Only

**Signal:** Test passes when items exist

**False Because:** Items might be wrong items.

**Detection:**
```python
# Passes even if items are garbage
assert len(response.json()) > 0
assert len(users) == 5
```

**Fix:**
```python
# Assert on content
users = response.json()
assert len(users) == 5
assert users[0]["email"] == "expected@email.com"
assert all(u["status"] == "active" for u in users)
```

---

#### 2.4 Assert on Type Only

**Signal:** Test passes when type matches

**False Because:** Value might be wrong.

**Detection:**
```python
# Passes even if wrong value
assert isinstance(result, dict)
assert type(user) == User
```

**Fix:**
```python
# Assert on content
assert isinstance(result, dict)
assert result["status"] == "success"
assert result["data"]["id"] == expected_id
```

---

### 3. Response Status Without Body Check

#### 3.1 200 OK But Wrong Data

**Signal:** HTTP 200

**False Because:** Response body is garbage.

**Detection:**
```python
# Only checks status
assert response.status_code == 200
# Response body could be {"error": "something went wrong"} and still pass!
```

**Real World Example:**
```json
// HTTP 200 but this is NOT success
{
  "success": false,
  "error": "User not found"
}
```

**Fix:**
```python
assert response.status_code == 200
data = response.json()
assert data["success"] == True
assert "user" in data
assert data["user"]["id"] == expected_id
```

---

#### 3.2 201 Created But Wrong Entity

**Signal:** HTTP 201

**False Because:** Created wrong thing or malformed entity.

**Detection:**
```python
# Only checks status
response = client.post("/orders", json=order_data)
assert response.status_code == 201
# But was the order created CORRECTLY?
```

**Fix:**
```python
response = client.post("/orders", json=order_data)
assert response.status_code == 201
created_order = response.json()
assert created_order["total"] == expected_total
assert created_order["items"] == order_data["items"]

# ALSO verify in database
db_order = db.query(Order).filter_by(id=created_order["id"]).first()
assert db_order is not None
assert db_order.total == expected_total
```

---

#### 3.3 204 No Content After Wrong Deletion

**Signal:** HTTP 204

**False Because:** Might have deleted wrong thing.

**Detection:**
```python
# Only checks status
response = client.delete(f"/users/{user_id}")
assert response.status_code == 204
# But did we delete the RIGHT user?
```

**Fix:**
```python
# Verify before
user_before = db.query(User).filter_by(id=user_id).first()
assert user_before is not None

# Delete
response = client.delete(f"/users/{user_id}")
assert response.status_code == 204

# Verify after
user_after = db.query(User).filter_by(id=user_id).first()
assert user_after is None

# Verify others NOT deleted
other_users = db.query(User).filter(User.id != user_id).count()
assert other_users == original_count - 1
```

---

### 4. Over-Mocking

#### 4.1 Mocked the Thing You're Testing

**Signal:** Test passes instantly

**False Because:** Real code never ran.

**Detection:**
```python
# You're testing create_user but mocked it!
@patch("app.services.user_service.create_user")
def test_create_user(mock_create):
    mock_create.return_value = {"id": 1}
    result = create_user({"name": "test"})
    # This tests the MOCK, not the real function
```

**Fix:**
```python
# Don't mock the thing under test
# Mock only external dependencies
@patch("app.services.user_service.send_email")  # Mock this
def test_create_user(mock_email):
    result = create_user({"name": "test"})  # Test this for real
    assert result["id"] is not None
    mock_email.assert_called_once()
```

---

#### 4.2 Mocked Database, Never Tested Queries

**Signal:** Test passes but queries are wrong

**False Because:** SQL never executed.

**Detection:**
```python
# Database completely mocked
@patch("app.db.session.query")
def test_get_users(mock_query):
    mock_query.return_value.all.return_value = [mock_user]
    users = get_users()
    # Query syntax could be completely wrong and this passes
```

**Fix:**
```python
# Use real test database
def test_get_users(test_db):
    # Seed real data
    test_db.add(User(name="test"))
    test_db.commit()

    # Test real query
    users = get_users()
    assert len(users) == 1
    assert users[0].name == "test"
```

---

#### 4.3 Mocked External Service Responses

**Signal:** Test passes but integration is broken

**False Because:** External service behaves differently.

**Detection:**
```python
# Mock returns perfect data
@patch("app.clients.stripe.charge")
def test_payment(mock_charge):
    mock_charge.return_value = {"status": "succeeded"}
    # Real Stripe returns different structure, different errors
```

**Fix:**
```python
# Use VCR/recorded responses from real API
# Or at minimum, use realistic mock data
@patch("app.clients.stripe.charge")
def test_payment(mock_charge):
    # Use actual Stripe response structure
    mock_charge.return_value = {
        "id": "ch_xxx",
        "object": "charge",
        "amount": 2000,
        "status": "succeeded",
        "payment_method_details": {...}
    }
```

---

### 5. Test State Pollution

#### 5.1 Depends on Previous Test's State

**Signal:** Test passes in suite, fails alone

**False Because:** Relies on state from previous test.

**Detection:**
```bash
# Run alone
pytest tests/test_user.py::test_update -v  # FAILS
# Run in order
pytest tests/test_user.py -v  # PASSES
```

**Fix:**
```python
# Each test creates its own state
def test_update_user(test_db):
    # Create user IN THIS TEST
    user = User(name="original")
    test_db.add(user)
    test_db.commit()

    # Now test update
    updated = update_user(user.id, {"name": "new"})
    assert updated.name == "new"
```

---

#### 5.2 Shared Mutable State

**Signal:** Tests interfere with each other

**False Because:** Success depends on run order.

**Detection:**
```python
# Module-level mutable state
users_cache = {}  # DANGER: shared between tests

def test_a():
    users_cache["a"] = User(...)

def test_b():
    # Might see test_a's data or not, depending on order
```

**Fix:**
```python
# Use fixtures with proper scope
@pytest.fixture
def users_cache():
    cache = {}
    yield cache
    cache.clear()

def test_a(users_cache):
    users_cache["a"] = User(...)

def test_b(users_cache):
    # Fresh cache, isolated
```

---

### 6. Snapshot/Golden File Issues

#### 6.1 Snapshot Approved Without Review

**Signal:** Snapshot test passes

**False Because:** Snapshot was wrong when approved.

**Detection:**
```bash
# Check snapshot history
git log --oneline -- **/__snapshots__/
# Was it reviewed or auto-approved?
```

**Fix:**
- Always review snapshot diffs manually
- Never auto-approve in CI
- Add comments explaining what snapshot should contain

---

#### 6.2 Snapshot Masks All Differences

**Signal:** Snapshot passes with wildcards

**False Because:** Wildcards hide real issues.

**Detection:**
```javascript
// Too many wildcards
expect(response).toMatchSnapshot({
  id: expect.any(String),
  timestamp: expect.any(String),
  data: expect.any(Object),  // This could be ANYTHING
});
```

**Fix:**
```javascript
// Be specific
expect(response).toMatchSnapshot({
  id: expect.any(String),
  timestamp: expect.any(String),
  // Data should have specific shape
});
expect(response.data.status).toBe("active");
```

---

## False Success Decision Tree

```
SUCCESS RECEIVED
      │
      ├── Was test skipped?
      │     └── YES → FALSE SUCCESS: Enable test
      │
      ├── Are assertions present?
      │     └── NO → FALSE SUCCESS: Add assertions
      │
      ├── Do assertions check CONTENT (not just type/length)?
      │     └── NO → FALSE SUCCESS: Strengthen assertions
      │
      ├── Is response body checked (not just status)?
      │     └── NO → FALSE SUCCESS: Check body
      │
      ├── Did real code run (not mocked away)?
      │     └── NO → FALSE SUCCESS: Reduce mocking
      │
      ├── Is test isolated (no state pollution)?
      │     └── NO → FALSE SUCCESS: Fix isolation
      │
      └── All good?
            └── YES → REAL SUCCESS
```

---

## Quick Detection Commands

```bash
# Find skipped tests
pytest tests/ -v 2>&1 | grep -i skip

# Find tests without assertions
grep -rL "assert" tests/*.py | grep "test_"

# Find mocked tests
grep -r "@patch" tests/ | wc -l
grep -r "@mock" tests/ | wc -l

# Find empty test functions
grep -A2 "def test_" tests/*.py | grep -B1 "pass$"

# Find status-only checks
grep -r "status_code ==" tests/ | grep -v "json()"
```
