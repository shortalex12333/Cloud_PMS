# Day 2: Backend API Hardening

**Date:** 2026-02-10
**Status:** STARTING NOW ⏳

---

## Goal

**Zero 404s, Zero 500s, <2s p95 response time**

Test ALL backend endpoints exhaustively:
- Valid inputs
- Invalid inputs
- Edge cases
- Authentication variants
- RBAC for all roles
- Performance under load

---

## Hours 1-4: Exhaustive API Testing

### Endpoints to Test:

**Search & Actions:**
- [ ] POST /search
- [ ] GET /v1/actions/list
- [ ] POST /v1/actions/execute

**Parts Lens:**
- [ ] POST /v1/parts/upload-image
- [ ] POST /v1/parts/update-image
- [ ] POST /v1/parts/delete-image
- [ ] GET /v1/parts/suggestions
- [ ] GET /v1/parts/low-stock

**Core:**
- [ ] GET /health
- [ ] GET /version

### Test Matrix:

For each endpoint, test:
1. **Valid request** → Should return 200/201
2. **Missing auth** → Should return 401
3. **Invalid JWT** → Should return 401
4. **Wrong yacht_id** → Should return 403
5. **Invalid payload** → Should return 400
6. **Missing required fields** → Should return 400

### Performance Tests:

- [ ] 10 concurrent requests
- [ ] 50 concurrent requests
- [ ] Measure p50, p95, p99 latency
- [ ] Check for memory leaks
- [ ] Check for connection pool exhaustion

---

## Hours 5-8: Fixes

### Identify and Fix:

1. **All 404s** → Fix routing
2. **All 500s** → Fix crashes
3. **All 403s** (when should be 200) → Fix RBAC
4. **Slow queries** (>2s) → Add indexes

### Fix Strategy:

- Fix immediately
- Test fix
- Document fix
- Commit
- Move to next issue

---

## Success Criteria

- [ ] Zero 404s on valid requests
- [ ] Zero 500s on any input
- [ ] All RBAC rules working correctly
- [ ] p95 response time < 2s
- [ ] All endpoints documented
- [ ] Test coverage >80%

---

**Starting:** Now
**Target Completion:** 8 hours
