# TEST ORDER — MANDATORY SEQUENCE

> **Tests MUST be run in this order. Skipping steps = invalid verification.**
>
> Last Updated: 2026-02-17
> Updated By: Claude Opus 4.5

---

## Mandatory Test Sequence

### 1. DB Constraints, RLS, FK
Verify policies match expectations before any logic tests.

```bash
# Supabase schema check
npx supabase db diff --schema public

# RLS policy verification
npx supabase test db
```

### 2. Backend Logic
Handler state validation, role checks.

```bash
# Python backend tests
cd ../image-processing && pytest tests/ -v

# Specific receiving tests
pytest tests/test_receiving_handler.py -v
```

### 3. Frontend UX Parity
Playwright E2E tests.

```bash
# All Playwright tests
cd apps/web && npx playwright test

# Specific receiving tests
npx playwright test tests/playwright/receiving-*.spec.ts

# UI regression tests
npx playwright test tests/playwright/spotlight-*.spec.ts
```

### 4. OCR End-to-End
Fake invoice upload → extraction → database.

```bash
# OCR pipeline test
cd ../image-processing && pytest tests/multi_role_test.py -v

# Full E2E with Docker
docker-compose -f docker-compose.ocr.yml up -d && pytest tests/e2e/
```

---

## Quick Verification Commands

```bash
# TypeScript build check
npm run build

# TypeScript type check only
npx tsc --noEmit

# Lint check
npm run lint

# All unit tests
npm test
```

---

## Test Results Template

Copy this when reporting results:

```markdown
| Suite | Passed | Failed | Notes |
|-------|--------|--------|-------|
| DB/RLS | x/x | x | |
| Backend | x/x | x | |
| Playwright E2E | x/x | x | |
| OCR Pipeline | x/x | x | |
| Build | PASS/FAIL | - | |
```

---

## Current Test Results (2026-02-17)

| Suite | Passed | Failed | Notes |
|-------|--------|--------|-------|
| receiving-plus-button-journey | 9/9 | 0 | Fixed |
| receiving-COMPREHENSIVE | 8/10 | 2 | Crew user missing, handler not deployed |
| receiving-simple-test | 1/1 | 0 | |
| receiving-lens-ui-smoke | 1/1 | 0 | |
| Build | PASS | - | PR #330 merged |

---

## Known Issues

- [ ] Crew test user not in Supabase auth (`crew.test@alex-short.com`)
- [ ] Handler fix not deployed to staging (reject→accept test fails against remote)

---

## Do NOT Proceed Unless

1. Build passes (`npm run build` exits 0)
2. TypeScript has no errors (`npx tsc --noEmit` exits 0)
3. Relevant test suite passes
4. Screenshot verification for UI changes
