# Natural Language Testing Plan - Hours of Rest 🎯

**Purpose:** Test REAL user search flow with chaotic input
**Status:** Ready to execute (needs JWT tokens)
**Date:** 2026-01-30

---

## What We're Actually Testing

**NOT testing:** Clean API calls like `POST /v1/actions/execute`
**TESTING:** Real messy user input → GPT → Action → RLS → Precise results

```
User: "show deck crew that didn't sleep enough last tuesday"
  ↓
GPT interprets intent
  ↓
Triggers: get_hours_of_rest + list_crew_warnings  ↓
RLS filters: only deck department, only non-compliant
  ↓
Returns: 2 deck crew with < 10h rest on 2026-01-21  ↓Button renders: "Acknowledge Warning" for each
```

---

## Test Categories

### 1. Natural Language Variations (Same Intent, Different Phrasing)

**Target:** `get_hours_of_rest` action

| Query | Expected Action | Notes |
|-------|----------------|-------|
| "show me my hours of rest" | get_hours_of_rest | Clean baseline |
| "view my rest hours" | get_hours_of_rest | Synonym: view = show |
| "did I get enough sleep" | get_hours_of_rest | Paraphrase |
| "am I compliant with rest" | get_hours_of_rest | Compliance keyword |
| "check if I'm legal to work" | get_hours_of_rest | Legal = compliant |
| "how much did I rest" | get_hours_of_rest | Question form |

**Success Criteria:**
- ✅ All trigger same action
- ✅ Return same data (user's HoR records)
- ✅ Same buttons render ("Log Rest", "View Details")

---

### 2. Misspellings & Typos (Fuzzy Matching)

**Target:** System should handle common mistakes

| Query (Misspelled) | Corrects To | Should Trigger |
|--------------------|-------------|----------------|
| "rest hurs" | "rest hours" | get_hours_of_rest |
| "complaince" | "compliance" | get_hours_of_rest |
| "housr of rest" | "hours of rest" | get_hours_of_rest |
| "dek crew" | "deck crew" | get_hours_of_rest (filtered) |
| "signe monthly report" | "sign monthly report" | sign_monthly_signoff |
| "warnigs" | "warnings" | list_crew_warnings |

**Success Criteria:**
- ✅ Fuzzy matching catches typos
- ✅ Correct action triggered despite spelling
- ✅ Results same as correct spelling

---

### 3. Time Ambiguity (Entity Extraction)

**Target:** Extract and resolve time entities

| Query | Time Entity | Expected Date Range |
|-------|-------------|---------------------|
| "rest hours yesterday" | yesterday | 2026-01-29 |
| "show last week" | last week | 2026-01-20 to 2026-01-26 |
| "this month" | this month | 2026-01-01 to 2026-01-30 |
| "tuesday" | last tuesday | 2026-01-28 |
| "january" | january 2026 | 2026-01-01 to 2026-01-31 |
| "last 7 days" | rolling 7 days | 2026-01-23 to 2026-01-30 |

**Success Criteria:**
- ✅ GPT extracts time entity
- ✅ Converts to start_date/end_date params
- ✅ Results filtered to date range
- ✅ No results outside range

---

### 4. Role-Based Filtering (RLS via Search)

**Scenario:** 3 users search "show rest hours"

| User | Role | Department | Should See |
|------|------|------------|------------|
| **john@deck** | crew | deck | Only john's records |
| **hod@deck** | chief_officer | deck | All deck crew (john + others) |
| **captain@ship** | captain | command | ALL crew (deck + engine + galley) |

**Test Queries:**
```bash
# As crew (john@deck)
"show rest hours this week"
→ Returns: 7 records (only john's)
→ RLS blocks other crew

# As HOD (hod@deck)
"show deck crew rest hours"
→ Returns: 35 records (5 deck crew × 7 days)
→ RLS blocks engine crew

# As captain
"show all crew rest hours"
→ Returns: 105 records (15 total crew × 7 days)
→ RLS allows all departments
```

**Success Criteria:**
- ✅ Crew sees ONLY own records (RLS enforced)
- ✅ HOD sees ONLY same department (deck vs engine isolated)
- ✅ Captain sees ALL (full access)
- ❌ Crew CANNOT see other crew (even if they search for it)

---

### 5. Department RLS (Critical Security Test)

**Scenario:** Deck HOD tries to see Engine crew

| Query | HOD Dept | Should Return | RLS Test |
|-------|----------|---------------|----------|
| "show deck crew rest" | deck | Deck crew ✅ | Allowed |
| "show engine crew rest" | deck | EMPTY or denied ❌ | Blocked |
| "show all crew rest" | deck | Deck only ✅ | Filtered |

**Security Verification:**
```sql
-- Expected RLS policy behavior:
SELECT * FROM pms_hours_of_rest WHERE ...
AND (
  user_id = auth.uid()  -- Crew: own only
  OR (
    is_hod() AND is_same_department(user_id)  -- HOD: same dept
  )
  OR is_captain()  -- Captain: all
)
```

**Success Criteria:**
- ❌ Deck HOD CANNOT see engine crew (403 or empty)
- ✅ Deck HOD sees deck crew
- ✅ Captain overrides department filter

---

### 6. Action Intent Classification (Read vs Write)

**Target:** Distinguish query intent (view vs mutate)

| Query | Intent | Action | Variant |
|-------|--------|--------|---------|
| "show rest hours" | READ | get_hours_of_rest | READ |
| "view warnings" | READ | list_crew_warnings | READ |
| **"log rest hours"** | WRITE | upsert_hours_of_rest | MUTATE |
| **"sign monthly report"** | WRITE | sign_monthly_signoff | MUTATE |
| **"create template"** | WRITE | create_crew_template | MUTATE |

**Success Criteria:**
- ✅ "show/view" → READ actions
- ✅ "log/create/sign" → MUTATE actions
- ✅ Buttons differ based on intent:
  - READ: "View Details", "Download"
  - WRITE: "Log Hours", "Sign Report", "Create"

---

### 7. Precision vs Noise (Exact Results, Not Buried)

**Scenario:** User wants SPECIFIC data, not 1000 rows

| Query | Expected Results | Max Results | Precision |
|-------|------------------|-------------|-----------|
| "rest hours january 15" | 1 record (1 date) | 1 | ✅ EXACT |
| "warnings active" | 3 records (active only) | 3 | ✅ FILTERED |
| "deck crew last tuesday" | 5 records (5 deck crew × 1 day) | 5 | ✅ SCOPED |
| **"rest"** (vague) | ERROR or suggest | 0 | ⚠️ TOO VAGUE |
| **"hours"** (ambiguous) | Clarify: "Hours of rest? Work hours?" | 0 | ⚠️ AMBIGUOUS |

**Fallback Behavior:**
```
User: "rest"

System:
⚠️ Your search "rest" is too vague. Did you mean:
  - Hours of Rest (crew rest periods)
  - Rest Periods (daily rest breaks)
  - Compliance Warnings (rest violations)

Please be more specific.
```

**Success Criteria:**
- ✅ Precise queries return ≤10 exact results
- ✅ Vague queries prompt for clarification (don't return 1000 rows)
- ✅ Results sorted by relevance (most recent first)
- ❌ No "noise" results (unrelated data)

---

### 8. Chaotic Real User Input (Stress Test)

**Target:** Handle messy, contradictory, multi-entity queries

| Chaotic Query | Should Handle |
|---------------|---------------|
| "show me the rest thing from last tuesday when I worked late" | Extract: time=tuesday, domain=rest |
| "did deck crew get their 10 hours or whatever it is" | Extract: dept=deck, threshold=10h |
| "rest hours for john who signed it already i think" | Extract: user=john, status=signed |
| "show all crew but only mine" | Contradiction: resolve to "only mine" |
| "deck and engine hours but just deck" | Contradiction: resolve to "deck" |
| "check if anyone violated mlc last week maybe" | Extract: domain=warnings, time=last_week |

**Expected GPT Behavior:**
```
Query: "show all crew but only mine"

GPT reasoning:
- "all crew" → intent: broad scope
- "only mine" → intent: narrow scope
- Contradiction detected
- Resolve: "only mine" takes precedence (privacy first)

Action: get_hours_of_rest
Params: {user_id: current_user}
```

**Success Criteria:**
- ✅ GPT extracts multiple entities
- ✅ Resolves contradictions (privacy first)
- ✅ Triggers correct action despite mess
- ✅ Returns precise results (not confused by chaos)

---

### 9. Button Rendering Based on Context

**Target:** Show relevant actions based on search results

| Search Query | Results | Buttons Rendered |
|--------------|---------|------------------|
| "show my rest hours" | 7 HoR records | "Log Today", "View Details" |
| "show warnings" | 2 warnings | "Acknowledge", "Dismiss" (if HOD) |
| "monthly signoffs" | 1 unsigned signoff | "Sign Report", "View Summary" |
| "templates" | 3 templates | "Apply Template", "Edit", "Delete" |

**Context-Aware Buttons:**
```json
{
  "available_actions": [
    {
      "action_id": "upsert_hours_of_rest",
      "label": "Log Rest Hours",
      "visible": true,  // User is crew
      "enabled": true,  // Current date not logged yet
      "context": "No record for 2026-01-30"
    },
    {
      "action_id": "sign_monthly_signoff",
      "label": "Sign January Report",
      "visible": true,  // User is HOD
      "enabled": false,  // Crew hasn't signed yet
      "context": "Awaiting crew signature"
    }
  ]
}
```

**Success Criteria:**
- ✅ Buttons match search context
- ✅ Disabled if prerequisites unmet
- ✅ Hidden if role lacks permission
- ✅ Labels describe action clearly

---

## Test Execution Guide

### Prerequisites

1. **Create 3 Test Users:**
```sql
-- Crew (deck department)
INSERT INTO auth.users (email, ...) VALUES ('crew.deck@test.com', ...);
UPDATE auth.users SET raw_user_meta_data = '{"role":"crew","department":"deck"}'::jsonb;

-- HOD (deck department)
INSERT INTO auth.users (email, ...) VALUES ('hod.deck@test.com', ...);
UPDATE auth.users SET raw_user_meta_data = '{"role":"chief_officer","department":"deck"}'::jsonb;

-- Captain (all access)
INSERT INTO auth.users (email, ...) VALUES ('captain@test.com', ...);
UPDATE auth.users SET raw_user_meta_data = '{"role":"captain","department":"command"}'::jsonb;
```

2. **Seed Test Data:**
```sql
-- Create HoR records for multiple users across departments
-- Deck crew: 3 users × 7 days = 21 records
-- Engine crew: 2 users × 7 days = 14 records
-- Include mix of compliant/non-compliant
```

3. **Get JWT Tokens:**
```bash
# Crew token
CREW_JWT=$(curl -X POST $MASTER_SUPABASE_URL/auth/v1/token \
  -H "apikey: $MASTER_ANON_KEY" \
  -d '{"email":"crew.deck@test.com","password":"..."}' \
  | jq -r .access_token)

# HOD token
HOD_JWT=$(curl -X POST $MASTER_SUPABASE_URL/auth/v1/token \
  -H "apikey: $MASTER_ANON_KEY" \
  -d '{"email":"hod.deck@test.com","password":"..."}' \
  | jq -r .access_token)

# Captain token
CAPTAIN_JWT=$(curl -X POST $MASTER_SUPABASE_URL/auth/v1/token \
  -H "apikey: $MASTER_ANON_KEY" \
  -d '{"email":"captain@test.com","password":"..."}' \
  | jq -r .access_token)
```

### Test Execution (Manual)

```bash
# Test 1: Basic query as crew
curl -X POST https://pipeline-core.int.celeste7.ai/api/search/stream \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show me my rest hours last week",
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  }'

# Expected:
# - Triggers: get_hours_of_rest
# - Returns: 7 records (only crew's own)
# - Buttons: "Log Today", "View Details"

# Test 2: Department filtering as HOD
curl -X POST https://pipeline-core.int.celeste7.ai/api/search/stream \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show deck crew rest hours",
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  }'

# Expected:
# - Returns: All deck crew (3 users × 7 days = 21 records)
# - Does NOT return engine crew (RLS blocks)

# Test 3: Cross-department (should FAIL)
curl -X POST https://pipeline-core.int.celeste7.ai/api/search/stream \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show engine crew rest hours",
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  }'

# Expected:
# - Returns: 0 records or 403 error (RLS blocks)
# - Security enforced ✅

# Test 4: Captain all-access
curl -X POST https://pipeline-core.int.celeste7.ai/api/search/stream \
  -H "Authorization: Bearer $CAPTAIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "show all crew rest hours",
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  }'

# Expected:
# - Returns: All departments (deck + engine = 35 records)
# - Full access ✅

# Test 5: Chaotic input
curl -X POST https://pipeline-core.int.celeste7.ai/api/search/stream \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "did i sleep enough last tuesday or am i in trouble",
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  }'

# Expected:
# - GPT understands: time=tuesday, intent=compliance_check
# - Triggers: get_hours_of_rest (for tuesday) + list_crew_warnings
# - Returns: 1 HoR record + any warnings
# - Precise, not noise ✅
```

---

## Success Metrics

### Query Understanding (GPT Layer)
- ✅ 90%+ queries trigger correct action
- ✅ Handles 80%+ misspellings
- ✅ Resolves 90%+ time entities correctly
- ✅ Detects read vs write intent 95%+

### RLS Enforcement (Security Layer)
- ✅ 100% crew isolation (cannot see others)
- ✅ 100% department isolation (HOD deck ≠ engine)
- ✅ 100% captain override (sees all)
- ❌ 0% unauthorized access (zero tolerance)

### Result Precision (Data Layer)
- ✅ Specific queries return ≤10 results
- ✅ Results match query intent 95%+
- ✅ No "noise" results (irrelevant data)
- ✅ Sorted by relevance

### Button Rendering (UI Layer)
- ✅ Buttons match user role
- ✅ Buttons match result context
- ✅ Disabled when prerequisites unmet
- ✅ Labels describe action clearly

---

## Failure Modes to Test

### 1. Ambiguity
```
Query: "hours"
Expected: Clarification prompt
Actual: Should NOT return work hours + rest hours + equipment hours
```

### 2. Contradiction
```
Query: "show all but only mine"
Expected: Resolve to "mine" (privacy first)
Actual: Should NOT return all crew
```

### 3. RLS Bypass Attempt
```
Query: "show user_id=other-crew-uuid rest hours"
Expected: RLS blocks (returns own only)
Actual: Should NOT return other crew's data
```

### 4. Invalid Time
```
Query: "show rest tuesday" (but today is Monday)
Expected: Last tuesday (6 days ago)
Actual: Should NOT return next tuesday
```

### 5. Department Typo
```
Query: "dek crew rest" (misspelled deck)
Expected: Fuzzy match to "deck"
Actual: Should NOT return 0 results
```

---

## Next Steps After Testing

1. **Document Failures:** Track which queries fail → improve GPT prompts
2. **Improve Keywords:** Add synonyms to `search_keywords` in registry
3. **Refine RLS:** Tighten policies if any leaks found
4. **Optimize Precision:** Tune result ranking/filtering
5. **E2E with Playwright:** Automate these tests in UI

---

## Conclusion

This is the **REAL test** - not clean API calls, but **chaotic user chaos** → **precise results**.

**Pass Criteria:**
- User searches "show deck crew that didn't sleep enough tuesday"
- GPT extracts: department=deck, threshold<10h, date=tuesday
- RLS filters: only deck (HOD sees all deck, captain sees all)
- Returns: 2 specific records (John & Sarah on deck, 9h rest on 2026-01-28)
- Buttons: "Acknowledge Warning", "View Details"
- **NOT 1000 rows of noise**

**This is production readiness** ✅

---

**Created By:** Claude Sonnet 4.5
**Date:** 2026-01-30
**Status:** Ready to execute (needs JWT tokens)
**Priority:** HIGH - This validates the REAL user experience
