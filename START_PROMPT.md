# AUTONOMOUS MICROACTION IMPLEMENTATION - START PROMPT

Copy and paste everything below the line into your new Claude session:

---

## YOUR MISSION

You are implementing 57 microactions for CelesteOS, a yacht maintenance management system. You will work autonomously through EVERY action without stopping until all are complete.

**Previous Claude completed `diagnose_fault` as a working template. Follow that exact pattern.**

---

## READ THESE FILES FIRST (IN ORDER)

```
1. /Users/celeste7/CLAUDE.md
   - Project memory, credentials, architecture overview

2. /Users/celeste7/Documents/Cloud_PMS/CONTINUE_ALL_MICROACTIONS.md
   - Your mission checklist (57 actions, 1 done, 56 to go)
   - Step-by-step process for each action

3. /Users/celeste7/Documents/Cloud_PMS/HANDOVER_TO_NEXT_CLAUDE.md
   - What previous Claudes did wrong (don't repeat their mistakes)
```

---

## KEY DOCUMENTATION FOLDERS

| Folder | Contains | Purpose |
|--------|----------|---------|
| `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/` | MICRO_ACTION_REGISTRY.md, ACTION_OFFERING_RULES.md | Action specs and trigger rules |
| `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/04_HANDLERS/` | 16 Python handler files | SOURCE OF TRUTH for implementation logic |
| `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/` | README_PROMPT_2.MD, COMPLETE_ACTION_EXECUTION_CATALOG.md | Full specifications |

---

## KEY CODE FOLDERS

| Folder | Contains | Purpose |
|--------|----------|---------|
| `/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/microactions/handlers/` | TypeScript handlers | Your implementation (verify against Python) |
| `/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/cards/` | FaultCard, WorkOrderCard, EquipmentCard, etc. | Where you ADD buttons |
| `/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/modals/` | Action modals | UI dialogs for actions |
| `/Users/celeste7/Documents/Cloud_PMS/tests/e2e/microactions/` | E2E test files | Where you WRITE tests |

---

## WORKING EXAMPLE: diagnose_fault (COMPLETED)

This action is DONE and working. Use it as your template:

| Component | File | What Was Done |
|-----------|------|---------------|
| Button | `/apps/web/src/components/cards/FaultCard.tsx` | Added "Diagnose" button with Stethoscope icon |
| Modal | `/apps/web/src/components/modals/DiagnoseFaultModal.tsx` | Connected existing modal |
| Handler | `/apps/web/src/lib/microactions/handlers/faults.ts` | Verified matches Python spec |
| E2E Test | `/tests/e2e/microactions/cluster_01_fix_something.spec.ts` | Line 371 - passes with HTTP 200 |
| Provider | `/apps/web/src/providers/MicroactionsProvider.tsx` | Registers all handlers on mount |

---

## UNDERSTANDING TRIGGERS, THRESHOLDS & ALLOWANCES

**Before implementing ANY action, you must understand WHEN it appears and WHO can use it.**

### Files That Define Triggers & Thresholds:

| File | What It Tells You |
|------|-------------------|
| `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/MICRO_ACTION_REGISTRY.md` | action_name, card_type, side_effect_type, cluster |
| `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/ACTION_OFFERING_RULES.md` | TRIGGER CONDITIONS - when action appears, thresholds, role restrictions |
| `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/04_HANDLERS/*.py` | IMPLEMENTATION LOGIC - what the action actually does |
| `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/COMPLETE_ACTION_EXECUTION_CATALOG.md` | THE GOSPEL - 6500 lines of complete action specifications |

### Trigger Example (diagnose_fault):

```
TRIGGER: User views a fault card
THRESHOLD: Fault status = 'open' or 'in_progress'
ROLE ALLOWANCE: Engineer, HOD, Captain
CARD TYPE: fault
SIDE EFFECT: read_only (no database mutation)
```

### Role Hierarchy:

```
Crew        → Limited read-only actions
Engineer    → Most actions (create, update, diagnose)
HOD         → All Engineer + close/approve actions
Captain     → All HOD + export/compliance
Manager     → Same as Captain
```

### Side Effect Types:

| Type | Meaning | Example |
|------|---------|---------|
| read_only | No DB changes, just fetches/displays data | diagnose_fault, view_history |
| mutation_light | Minor DB update (notes, photos, status) | add_note, add_photo |
| mutation_heavy | Creates/deletes records, major changes | create_work_order, close_work_order |

---

## IMPLEMENTATION → TEST → DEPLOY CYCLE

For EACH microaction, follow this exact cycle:

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: UNDERSTAND                                            │
├─────────────────────────────────────────────────────────────────┤
│  1. Read MICRO_ACTION_REGISTRY.md → Find action spec            │
│  2. Read ACTION_OFFERING_RULES.md → Find trigger/threshold      │
│  3. Read Python handler → Understand exact logic                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: IMPLEMENT                                             │
├─────────────────────────────────────────────────────────────────┤
│  4. Verify/Create TypeScript handler (match Python exactly)     │
│  5. Add button to correct card component                        │
│  6. Create/connect modal if needed                              │
│  7. Wire trigger conditions (button shows only when allowed)    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: TEST LOCALLY                                          │
├─────────────────────────────────────────────────────────────────┤
│  8. Run unit tests: npm run test:unit                           │
│  9. Run build check: npm run build                              │
│  10. Run E2E test: npx playwright test [file] --headed          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: DATABASE (IF NEEDED)                                  │
├─────────────────────────────────────────────────────────────────┤
│  11. If new table/column needed:                                │
│      - Create migration: supabase/migrations/[timestamp].sql    │
│      - Push to Supabase: supabase db push                       │
│      - Verify: supabase db diff                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: DEPLOY TO PRODUCTION                                  │
├─────────────────────────────────────────────────────────────────┤
│  12. Commit changes: git add . && git commit -m "feat: [action]"│
│  13. Push to main: git push origin main                         │
│  14. Vercel auto-deploys frontend to app.celeste7.ai            │
│  15. Verify on production: https://app.celeste7.ai              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 6: VERIFY & REPEAT                                       │
├─────────────────────────────────────────────────────────────────┤
│  16. Run E2E against production URL                             │
│  17. Update checklist: Mark [x] in CONTINUE_ALL_MICROACTIONS.md │
│  18. MOVE TO NEXT ACTION - DO NOT STOP                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## THREE TESTING METHODS

| Method | Command | Purpose | When to Use |
|--------|---------|---------|-------------|
| **Unit Tests** | `cd apps/web && npm run test:unit` | Test logic with mocks | After writing handler |
| **Integration Tests** | `cd apps/web && npm run test:integration` | Test against real DB (service key) | After unit tests pass |
| **E2E Tests** | `npx playwright test --headed` | Test with REAL user auth | Final verification |

### E2E Test Pattern:

```typescript
test('action_name works', async ({ page }) => {
  // 1. Login with real credentials
  await page.goto('https://app.celeste7.ai/login');
  await page.fill('[name="email"]', 'x@alex-short.com');
  await page.fill('[name="password"]', 'Password2!');
  await page.click('button[type="submit"]');

  // 2. Navigate to correct card
  await page.goto('/faults'); // or /work-orders, /equipment, etc.

  // 3. Click the action button
  await page.click('[data-action="action_name"]');

  // 4. Verify modal/result
  await expect(page.locator('.modal')).toBeVisible();

  // 5. Verify database updated (for mutations)
  // Check via API or UI feedback
});
```

---

## SQL MIGRATION WORKFLOW

If an action needs new database tables/columns:

```bash
# 1. Create migration file
touch supabase/migrations/$(date +%Y%m%d%H%M%S)_action_name.sql

# 2. Write SQL (example)
cat > supabase/migrations/[timestamp]_action_name.sql << 'EOF'
-- Add column for action
ALTER TABLE pms_faults ADD COLUMN IF NOT EXISTS diagnosis_result jsonb;

-- Add RLS policy
CREATE POLICY "Users can view own yacht diagnosis"
ON pms_faults FOR SELECT
USING (yacht_id = auth.jwt() ->> 'yacht_id');
EOF

# 3. Push to Supabase
supabase db push

# 4. Verify
supabase db diff
```

---

## PRODUCTION DEPLOYMENT

### Frontend (Vercel) - Auto-deploys on push to main:
```bash
git add .
git commit -m "feat(microaction): implement action_name"
git push origin main
# Vercel automatically deploys to https://app.celeste7.ai
```

### Backend API (Render) - If Python handler changes needed:
```bash
# Trigger Render deploy
curl -X POST "https://api.render.com/deploy/srv-d5k0avchg0os738oel2g?key=44vzriKDWhE"
```

### Database (Supabase) - For schema changes:
```bash
supabase db push
```

---

## FOR EACH ACTION YOU MUST:

```
1. READ the spec (MICRO_ACTION_REGISTRY.md)
   - action_name, card_type, side_effect_type, cluster

2. READ the triggers (ACTION_OFFERING_RULES.md)
   - When does button appear?
   - What conditions/thresholds?
   - What role can use it?

3. READ the Python handler (04_HANDLERS/*.py)
   - What does it ACTUALLY do?
   - What database operations?
   - What validation?

4. VERIFY/CREATE TypeScript handler
   - Must match Python EXACTLY
   - Use: import { supabase } from '@/lib/supabaseClient';

5. ADD button to correct card component
   - Match card_type from spec
   - Button appears when trigger conditions met

6. CREATE/CONNECT modal if needed
   - Check if modal exists in /components/modals/
   - Create if missing

7. WRITE E2E test
   - Login with real auth
   - Navigate to card
   - Click button
   - Verify result

8. RUN E2E test
   - npx playwright test [file] --headed
   - MUST PASS before moving on

9. UPDATE checklist in CONTINUE_ALL_MICROACTIONS.md
   - Mark [x] when done

10. MOVE TO NEXT ACTION IMMEDIATELY
```

---

## TEST CREDENTIALS

```
Email: x@alex-short.com
Password: Password2!
Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
```

```
Supabase URL: https://vzsohavtuotocgrfkfyd.supabase.co
Service Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY
```

```
Production URL: https://app.celeste7.ai
```

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION                          │
├─────────────────────────────────────────────────────────────────┤
│  User sees card → Clicks action button → Modal opens            │
│                           ↓                                      │
│  Modal calls TypeScript handler → Handler calls Supabase        │
│                           ↓                                      │
│  Supabase RLS enforces yacht isolation → Data returned          │
│                           ↓                                      │
│  UI updates to show result                                       │
└─────────────────────────────────────────────────────────────────┘

Deployments:
- Frontend: Vercel → https://app.celeste7.ai
- Backend API: Render → pipeline-core.int.celeste7.ai
- Database: Supabase (PostgreSQL + RLS)
```

---

## CORRECT IMPORT PATTERN

**WRONG (causes build errors):**
```typescript
import { createClient } from '@/lib/supabase/server';
```

**CORRECT:**
```typescript
import { supabase } from '@/lib/supabaseClient';
```

---

## RULES - DO NOT BREAK THESE

1. **DO NOT STOP** until all 57 actions complete
2. **DO NOT SKIP** reading the Python handler - it's the source of truth
3. **DO NOT GUESS** what an action should do - read the spec
4. **DO NOT BATCH** actions - complete one fully before starting next
5. **DO NOT FAKE** tests - E2E must actually pass with real auth
6. **DO NOT USE** createClient - use supabase singleton
7. **UPDATE CHECKLIST** after each action completes
8. **REPORT HONESTLY** if something doesn't work

---

## VERIFICATION CHECKPOINTS

After every 5 actions, verify:
- [ ] All 5 buttons appear on correct cards
- [ ] All 5 modals open correctly
- [ ] All 5 E2E tests pass
- [ ] Checklist updated with [x] marks
- [ ] No build errors: `npm run build`

---

## IF YOU GET STUCK

1. Re-read the Python handler - it has the answer
2. Check the working `diagnose_fault` implementation as reference
3. Run build to check for errors: `cd apps/web && npm run build`
4. Check existing modals - many already exist in /components/modals/
5. Ask user ONLY if truly blocked (provide specific error)

---

## START NOW

1. Read /Users/celeste7/CLAUDE.md
2. Read /Users/celeste7/Documents/Cloud_PMS/CONTINUE_ALL_MICROACTIONS.md
3. Begin with `show_manual_section` (next action after diagnose_fault)
4. Follow the 10-step process above
5. Do not stop until all 57 actions have [x] marks

**GO.**
