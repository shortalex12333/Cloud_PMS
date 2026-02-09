# Deployment v2026.02.09.003 - E2E Verification Tests

End-to-end Playwright tests for deployment v2026.02.09.003 (PRs #194-198).

## What's Being Tested

### 1. Work Orders RBAC (PR #194 - CRITICAL)
**File**: `work-orders-rbac.spec.ts`

**Department-based authority:**
- ✅ CREW can close/mutate work orders in THEIR department
- ❌ CREW BLOCKED from other departments' work orders
- ✅ HOD (Engineering) can mutate ANY department (cross-department authority)
- ✅ CAPTAIN can mutate ANY department
- ✅ CAPTAIN + HOD can assign work orders
- ❌ CREW CANNOT assign work orders

### 2. Parts Image Upload (PR #195)
**File**: `parts-image-upload.spec.ts`

**MVP functionality:**
- ✅ Any role (CREW/HOD/CAPTAIN) can upload image to part
- ✅ Update/replace existing image
- ✅ Delete image from part
- ✅ Upload endpoint exists (returns 401/422, not 404)

### 3. Shopping List Entity Extraction (PR #197)
**File**: `shopping-list-extraction.spec.ts`

**Entity extraction from descriptions:**
- ✅ Extract quantity, part type, manufacturer from text
- ✅ User can edit extracted entities before saving
- ✅ Handles complex descriptions (units, multiple parts)
- ✅ All roles can create shopping list items

## Prerequisites

### 1. Environment Variables

```bash
# Master Supabase (for auth)
export MASTER_SUPABASE_ANON_KEY="your-master-anon-key"

# Test user passwords
export CREW_PASSWORD="crew-password"
export HOD_PASSWORD="hod-password"
export CAPTAIN_PASSWORD="captain-password"

# App URL
export APP_URL="https://your-app-url.com"
```

### 2. Test Users

These users must exist in MASTER and TENANT databases:

- **CREW**: crew.tenant@alex-short.com (deck department)
- **HOD**: hod.tenant@alex-short.com (engineering department)
- **CAPTAIN**: captain.tenant@alex-short.com

## Running Tests

### Run All Deployment Tests
```bash
npx playwright test tests/e2e/deployment-v2026-02-09-003/
```

### Run Individual Test Suites
```bash
# Work Orders RBAC only
npx playwright test tests/e2e/deployment-v2026-02-09-003/work-orders-rbac.spec.ts

# Parts Image Upload only
npx playwright test tests/e2e/deployment-v2026-02-09-003/parts-image-upload.spec.ts

# Shopping List Extraction only
npx playwright test tests/e2e/deployment-v2026-02-09-003/shopping-list-extraction.spec.ts
```

### Run in UI Mode (Debug)
```bash
npx playwright test tests/e2e/deployment-v2026-02-09-003/ --ui
```

### Run with Headed Browser (Watch)
```bash
npx playwright test tests/e2e/deployment-v2026-02-09-003/ --headed
```

## Expected Results

### ✅ All Tests Pass (Success Criteria)

1. **Work Orders RBAC**:
   - CREW can close deck work orders ✓
   - CREW blocked from engineering work orders ✓
   - HOD can close any department ✓
   - CAPTAIN/HOD can assign ✓
   - CREW cannot assign ✓

2. **Parts Image Upload**:
   - All roles upload images successfully ✓
   - Update/replace works ✓
   - Delete works ✓
   - Endpoints return 401/422 (not 404) ✓

3. **Shopping List**:
   - Entities extracted from descriptions ✓
   - Users can edit before saving ✓
   - All roles can create items ✓

### ❌ Test Failures (What to Check)

**If Work Orders RBAC fails:**
- Check PR #194 deployed correctly
- Verify `auth_users_roles` table has department column
- Check RLS policies for department filtering
- Verify action_router checks department authority

**If Image Upload fails:**
- Check PR #195 deployed correctly
- Verify `/v1/parts/upload-image` endpoint exists
- Check image storage configuration (S3/Supabase Storage)
- Verify CORS settings for uploads

**If Shopping List fails:**
- Check PR #197 deployed correctly
- Verify entity extraction pipeline running
- Check extraction regex/NLP patterns
- Verify database columns for extracted entities

## Test Data

### Work Order Departments
Tests expect work orders with these departments:
- `deck` (for CREW user testing)
- `engineering` (for cross-department testing)

### Parts
Tests use first available part for image upload.
A 1x1 test PNG is auto-generated if not present.

### Shopping List Test Descriptions
```
- "Need 2x oil filters for Caterpillar engine"
  Expected: qty=2, part_type="oil filter", manufacturer="Caterpillar"

- "5 spark plugs NGK standard"
  Expected: qty=5, part_type="spark plug", manufacturer="NGK"

- "Hydraulic hose 10m Eaton"
  Expected: qty=10, unit="m", part_type="hydraulic hose", manufacturer="Eaton"
```

## Debugging

### View Test Report
```bash
npx playwright show-report
```

### Run with Trace
```bash
npx playwright test tests/e2e/deployment-v2026-02-09-003/ --trace on
```

### Check Logs
```bash
# Render logs for backend errors
# Check for 403/401 responses in Network tab
# Verify JWT in browser DevTools → Application → Local Storage
```

## Success Checklist

- [ ] All 3 test files run without errors
- [ ] CREW department authority enforced correctly
- [ ] Image upload/update/delete working for all roles
- [ ] Entity extraction producing structured data
- [ ] No 404 errors on new endpoints
- [ ] No 500 errors in API responses

---

**Deployment**: v2026.02.09.003
**PRs**: #194 (RBAC), #195 (Images), #196 (CI), #197 (Shopping List), #198 (Triggers)
**Critical Fix**: Department-based work order authority (CREW gating)
