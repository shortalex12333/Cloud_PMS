# Test Setup - Natural Language Search Testing

Complete setup for testing Hours of Rest with realistic user queries.

## Quick Start

```bash
# 1. Create test users (run on MASTER database)
psql "postgresql://postgres:$MASTER_DB_PASSWORD@db.qvzmkaamzaqxpzbewjxe.supabase.co:5432/postgres" \
  -f tests/setup/01_create_test_users.sql

# 2. Seed realistic data (run on TENANT_1 database)
psql "postgresql://postgres:$TENANT_1_DB_PASSWORD@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres" \
  -f tests/setup/02_seed_realistic_hor_data.sql

# 3. Generate JWT tokens
./tests/setup/03_generate_jwt_tokens.sh

# 4. Run natural language tests
./tests/setup/04_run_natural_language_tests.sh
```

## Files

### 01_create_test_users.sql
Creates 6 test users with different roles and departments:
- **Deck Department:**
  - `john.deck@test.celeste7.ai` (crew)
  - `sarah.deck@test.celeste7.ai` (crew)
  - `hod.deck@test.celeste7.ai` (chief_officer)
- **Engine Department:**
  - `tom.engine@test.celeste7.ai` (crew)
  - `hod.engine@test.celeste7.ai` (chief_engineer)
- **Command:**
  - `captain@test.celeste7.ai` (captain)

All passwords: See script output

### 02_seed_realistic_hor_data.sql
Creates realistic test data:
- **42 HoR records** (3 users × 14 days)
- **4 compliance violations** (realistic non-compliant scenarios)
- **4 active warnings** (auto-created for violations)
- **2 schedule templates** (4-on-8-off watch, day work)

### 03_generate_jwt_tokens.sh
Generates JWT tokens for all test users via Supabase auth API.
Saves to `tests/setup/.env.test` for use in tests.

### 04_run_natural_language_tests.sh
Automated test suite covering:
- Basic queries (baseline)
- Misspellings (fuzzy matching)
- Time ambiguity (entity extraction)
- Department RLS (security)
- Precision (not buried in noise)
- Chaotic input (stress test)

## Test Users

| Email | Password | Role | Department | Use Case |
|-------|----------|------|------------|----------|
| john.deck@test.celeste7.ai | TestDeck123! | crew | deck | Basic crew queries, sees own data only |
| sarah.deck@test.celeste7.ai | TestDeck123! | crew | deck | Has 2 violations (non-compliant) |
| hod.deck@test.celeste7.ai | TestHOD123! | chief_officer | deck | Sees deck crew, NOT engine |
| tom.engine@test.celeste7.ai | TestEngine123! | crew | engine | Engine crew, isolated from deck |
| hod.engine@test.celeste7.ai | TestHOD123! | chief_engineer | engine | Sees engine crew, NOT deck |
| captain@test.celeste7.ai | TestCaptain123! | captain | command | Sees ALL departments |

## Test Data Summary

### Hours of Rest Records
```
Total: 42 records
├─ Deck (28 records)
│  ├─ John:  14 days (13 compliant, 1 violation)
│  └─ Sarah: 14 days (12 compliant, 2 violations)
└─ Engine (14 records)
   └─ Tom:   14 days (13 compliant, 1 violation)
```

### Compliance Violations
```
Total: 4 violations (10% non-compliant)
├─ John (deck):   Tuesday last week (9.0h rest)
├─ Sarah (deck):  9 days ago (8.5h rest)
├─ Sarah (deck):  3 days ago (8.5h rest)
└─ Tom (engine):  5 days ago (9.5h rest)
```

### Warnings
```
Total: 4 active warnings
├─ John:  1 warning  (severity: warning)
├─ Sarah: 2 warnings (severity: critical)
└─ Tom:   1 warning  (severity: warning)
```

## Natural Language Test Cases

### Category 1: Basic Queries
```
"show me my hours of rest"
"view my rest hours"
"am I compliant with rest requirements"
```

### Category 2: Misspellings
```
"show my rest hurs"           → fuzzy match to "hours"
"veiw my complaince"          → fuzzy match to "compliance"
"dek crew rest"               → fuzzy match to "deck"
```

### Category 3: Time Ambiguity
```
"show my rest last week"      → extract: time = last 7 days
"rest hours yesterday"        → extract: time = 1 day ago
"this month"                  → extract: time = month to date
```

### Category 4: Department RLS (CRITICAL)
```
# As Deck HOD:
"show deck crew rest"         → Returns: 28 records (deck only) ✅
"show engine crew rest"       → Returns: 0 records (RLS blocks) ✅

# As Captain:
"show all crew rest"          → Returns: 42 records (all depts) ✅
```

### Category 5: Precision
```
"deck crew warnings active"   → Returns: 3 specific warnings (not 1000 rows)
"who didn't get enough rest"  → Returns: 4 specific violations (precise)
```

### Category 6: Chaotic Input
```
"show me deck crew that didn't sleep enough last tuesday"
→ GPT extracts: dept=deck, threshold<10h, time=tuesday
→ Returns: Specific non-compliant records
→ NOT buried in noise ✅
```

## Expected Results

### RLS Enforcement
| User | Query | Should See |
|------|-------|------------|
| John (crew) | "show rest hours" | 14 records (own only) |
| HOD Deck | "show deck crew rest" | 28 records (deck dept) |
| HOD Deck | "show engine crew rest" | 0 records (RLS blocks) ❌ |
| Captain | "show all crew rest" | 42 records (all depts) |

### Precision (Not Noise)
| Query | Max Results | Actual Expected |
|-------|-------------|-----------------|
| "rest hours yesterday" | 1 | 1 specific date |
| "warnings active" | 10 | 3-4 warnings |
| "deck crew last week" | 20 | 14 records (2 users × 7 days) |

## Verification

After running all scripts:

```bash
# Verify test users exist
psql $MASTER_DB_URL -c "
SELECT email, raw_user_meta_data->>'role' as role
FROM auth.users
WHERE email LIKE '%@test.celeste7.ai';"

# Verify HoR data exists
psql $TENANT_1_DB_URL -c "
SELECT COUNT(*) as total,
       SUM(CASE WHEN is_daily_compliant THEN 1 ELSE 0 END) as compliant
FROM pms_hours_of_rest
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';"

# Verify JWT tokens generated
cat tests/setup/.env.test
```

## Cleanup

To remove test data:

```bash
# Delete test users
psql $MASTER_DB_URL -c "
DELETE FROM auth.users
WHERE email LIKE '%@test.celeste7.ai';"

# Delete test HoR records
psql $TENANT_1_DB_URL -c "
DELETE FROM pms_hours_of_rest
WHERE user_id IN (
  'a1111111-1111-1111-1111-111111111111',
  'a2222222-2222-2222-2222-222222222222',
  'a4444444-4444-4444-4444-444444444444'
);"
```

## Troubleshooting

### JWT generation fails
- Check MASTER_SUPABASE_URL is correct
- Verify MASTER_ANON_KEY is valid
- Ensure test users were created (run script 01)

### Tests fail with 403
- RLS policies may not be configured
- Check user has correct role/department metadata
- Verify JWT token is valid (not expired)

### No search results
- Check if data was seeded (run script 02)
- Verify yacht_id matches test data
- Check if search endpoint exists

### Wrong results (RLS not enforced)
- Verify RLS policies are enabled on tables
- Check `is_hod()` and `is_captain()` functions exist
- Test with `SET ROLE authenticated` in psql

## Next Steps

1. **Run setup scripts** (follow Quick Start)
2. **Verify all tests pass** (should be 100%)
3. **Build frontend UI** to call these endpoints
4. **Add Playwright E2E tests** for full workflows
5. **Monitor production** for real user queries

---

**Created:** 2026-01-30
**Status:** Ready to execute
**Purpose:** Real user chaos → Precise results testing
