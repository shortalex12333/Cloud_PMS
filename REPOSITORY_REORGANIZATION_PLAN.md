# REPOSITORY REORGANIZATION PLAN

**Current state:** 79 markdown files at root, excessive documentation, confusing structure
**Target state:** Self-explanatory structure with clear file responsibilities

Date: 2026-01-22

---

## PROPOSED STRUCTURE

```
BACK_BUTTON_CLOUD_PMS/
│
├── README.md                     ← Entry point (kept at root)
│
├── docs/                         ← All current product documentation
│   ├── ARCHITECTURE.md
│   ├── DATABASE_RELATIONSHIPS.md
│   ├── DEPLOYMENT_ARCHITECTURE.md
│   ├── CUSTOMER_JOURNEY_FRAMEWORK.md
│   ├── FRAMEWORK_OVERVIEW.md
│   ├── GLOSSARY.md
│   ├── MICROACTIONS_EXPLAINED.md
│   ├── SITUATIONS_EXPLAINED.md
│   ├── LOCAL_SETUP.md
│   ├── ONBOARDING.md
│   ├── QUICK_REFERENCE.md
│   ├── TESTING_STANDARDS.md
│   ├── TEST_COVERAGE_REPORT.md
│   └── KNOWN_ISSUES.md
│
├── handover/                     ← CRITICAL HANDOVER DOCS (formerly _HANDOVER/)
│   ├── README.md                 ← Start here for new engineers
│   ├── SYSTEM_INVENTORY.md       ← What exists, why it exists
│   ├── SECURITY_INVARIANTS.md    ← What must never be broken
│   ├── MATURITY_ASSESSMENT.md    ← Brutally honest status
│   ├── HANDOVER.md               ← If you had 1 week, what would you do?
│   ├── 01_STATUS.md              ← Current numbers
│   ├── 02_WHATS_LEFT.md          ← Task list
│   ├── 03_HOW_TO_RUN.md          ← Commands
│   └── 04_KNOWN_TRAPS.md         ← Common issues
│
├── database/                     ← Database schemas and migrations
│   ├── README.md                 ← Database architecture overview
│   ├── master_migrations/        ← Master DB migrations
│   │   ├── MIGRATION_ORDER.md
│   │   ├── 000_create_fleet_registry.sql
│   │   ├── 001_create_user_accounts.sql
│   │   └── ...
│   ├── tenant_migrations/        ← Tenant DB migrations (renamed from migrations/)
│   │   ├── 00_enable_extensions.sql
│   │   ├── 01_core_tables_v2_secure.sql
│   │   ├── 02_p0_actions_tables_REVISED.sql
│   │   └── ...
│   └── security/                 ← Security documentation
│       ├── rls_model.md          ← How RLS works
│       ├── token_lifecycle.md    ← Token flow
│       └── threat_model.md       ← Security threats and mitigations
│
├── backend/                      ← Backend implementation docs (NEW)
│   ├── action_execution_flow.md
│   ├── nl_pipeline.md
│   └── error_handling.md
│
├── verification/                 ← Verification system (meta-system, moved from root)
│   ├── README.md                 ← What the verification system is
│   ├── MULTI_AGENT_VERIFICATION_PLAN.md
│   ├── VERIFICATION_METHODOLOGY.md
│   ├── ACTION_VERIFICATION_GUIDE.md
│   ├── ACTION_VERIFICATION_TEMPLATE.md
│   ├── QUICK_VERIFY_TEMPLATE.md
│   ├── AGENT_1_COMPLETE.md
│   ├── AGENT_1_HANDOFF.md
│   ├── AGENT_1_ORCHESTRATOR_COMPLETE.md
│   ├── AGENT_2_HANDOFF.md
│   ├── AGENT_2_PROMPT.md
│   ├── AGENT_3_COMPLETION_VERIFIED.md
│   ├── AGENT_3_HANDOFF.md
│   ├── AGENT_3_PROMPT.md
│   ├── AGENT_4_PROMPT.md
│   ├── AGENT_4_READY_TO_LAUNCH.md
│   ├── AGENT_COMMUNICATION_PROTOCOL.md
│   ├── AGENT_LAUNCH_STANDARD.md
│   ├── AGENT_PROGRESS.md
│   ├── WATCHDOG_AGENT_SPEC.md
│   ├── WATCHDOG_CHECKLIST.md
│   ├── WATCHDOG_PROMPT.md
│   ├── WATCHDOG_SYSTEM_COMPLETE.md
│   ├── WATCHDOG_SYSTEM_READY.md
│   ├── LAUNCH_AGENTS_README.md
│   ├── LAUNCH_WITH_WATCHDOG.md
│   ├── QUICK_LAUNCH.md
│   ├── AUTONOMOUS_VERIFICATION_SYSTEM_READY.md
│   ├── QUICK_START_VERIFICATION.md
│   ├── PREVENTING_AI_OVERWHELM.md
│   ├── README_VERIFICATION_SYSTEM.md
│   ├── VERIFICATION_DASHBOARD.md
│   └── findings/                 ← Verification results (moved from _VERIFICATION/)
│       ├── AGENT_3_WAITING.md
│       ├── COMPREHENSIVE_FAULT_REPORT.md
│       ├── CREATE_WORK_ORDER_DEEP_DIVE.md
│       ├── EXECUTIVE_SUMMARY_CREATE_WO.md
│       ├── MUTATION_PROOFS.md
│       ├── PATTERN_ANALYSIS.md
│       ├── PATTERN_FIXES.md
│       ├── PHASE_1_FINDINGS.md
│       ├── RELATED_ISSUES.md
│       ├── verify_add_note.md
│       ├── verify_assign_work_order.md
│       ├── verify_create_work_order.md
│       ├── verify_get_work_order_details.md
│       └── verify_mark_fault_resolved.md
│
├── apps/                         ← Application source code (unchanged)
│   ├── api/
│   └── web/
│
├── tests/                        ← Test suite (unchanged)
│   ├── e2e/
│   ├── helpers/
│   └── fixtures/
│
├── scripts/                      ← Utility scripts (unchanged)
│
├── _archive/                     ← Historical docs (unchanged, Git history sufficient)
│
├── .env.example                  ← Environment variables template
├── .gitignore
├── package.json
├── playwright.config.ts
├── render.yaml
└── docker-compose.yml
```

---

## CHANGES REQUIRED

### Move to `docs/`

**From root:**
- ARCHITECTURE.md
- DATABASE_RELATIONSHIPS.md
- DEPLOYMENT_ARCHITECTURE.md
- CUSTOMER_JOURNEY_FRAMEWORK.md
- FRAMEWORK_OVERVIEW.md
- GLOSSARY.md
- MICROACTIONS_EXPLAINED.md
- SITUATIONS_EXPLAINED.md
- LOCAL_SETUP.md
- ONBOARDING.md
- QUICK_REFERENCE.md
- TESTING_STANDARDS.md
- TEST_COVERAGE_REPORT.md
- KNOWN_ISSUES.md

**Total:** 14 files moved

---

### Move to `handover/`

**From root:**
- SYSTEM_INVENTORY.md (just created)
- SECURITY_INVARIANTS.md (just created)
- MATURITY_ASSESSMENT.md (just created)
- HANDOVER.md (just created)

**From _HANDOVER/:**
- README.md
- 01_STATUS.md
- 02_WHATS_LEFT.md
- 03_HOW_TO_RUN.md
- 04_KNOWN_TRAPS.md

**Total:** 9 files moved

**Delete _HANDOVER/ folder after move**

---

### Rename `database/migrations/` to `database/tenant_migrations/`

**Why:** Clarify that these are tenant DB migrations, not master DB migrations.

---

### Create `database/security/`

**New files:**
1. `rls_model.md` - Extracted from SECURITY_INVARIANTS.md (RLS section)
2. `token_lifecycle.md` - Extracted from SECURITY_INVARIANTS.md (Token section)
3. `threat_model.md` - Extracted from SECURITY_INVARIANTS.md (Threat model section)

**Or:** Create symlinks to relevant sections of SECURITY_INVARIANTS.md

---

### Create `backend/`

**New files:**
1. `action_execution_flow.md` - How action handlers work
2. `nl_pipeline.md` - How NL→Action mapping works
3. `error_handling.md` - Error handling patterns

**Content:** Extract from SYSTEM_INVENTORY.md, ARCHITECTURE.md

---

### Create `verification/`

**Move from root:**
- All AGENT_*.md files (19 files)
- All WATCHDOG_*.md files (5 files)
- All VERIFICATION_*.md files (4 files)
- All LAUNCH_*.md files (3 files)
- All QUICK_*_VERIFICATION.md files (2 files)
- AUTONOMOUS_VERIFICATION_SYSTEM_READY.md
- PREVENTING_AI_OVERWHELM.md
- MULTI_AGENT_VERIFICATION_PLAN.md
- AGENT_PROGRESS.md

**Move from _VERIFICATION/ to verification/findings/:**
- All verification result files (15 files)

**Total:** 48 files moved

**Delete _VERIFICATION/ folder after move**

---

### Keep at Root

**Essential files only:**
- README.md (entry point)
- briefing.md (project briefing)
- .env.example
- .gitignore
- package.json
- playwright.config.ts
- render.yaml
- docker-compose.yml
- build.sh

**Total:** 9 files at root (down from 79)

---

### Delete from Root (Redundant)

**Old handover files superseded by new handover/:**
- ENGINEER_HANDOVER.md (superseded by handover/HANDOVER.md)
- REPOSITORY_MAP.md (superseded by this reorganization)

**Total:** 2 files deleted

---

## FILE RESPONSIBILITY MATRIX

| File | Single Responsibility | Why It Exists |
|------|----------------------|---------------|
| README.md | Entry point, quick start | First file engineers see |
| handover/README.md | Start here for handover | Onboarding new engineers |
| handover/SYSTEM_INVENTORY.md | What exists, why | Complete inventory |
| handover/SECURITY_INVARIANTS.md | What must never be broken | Security rules |
| handover/MATURITY_ASSESSMENT.md | Brutally honest status | Reality check |
| handover/HANDOVER.md | Week 1 plan for new engineer | Actionable guidance |
| docs/ARCHITECTURE.md | System architecture | High-level design |
| docs/DATABASE_RELATIONSHIPS.md | DB schema relationships | Data model |
| database/README.md | Database overview | DB architecture |
| database/security/rls_model.md | How RLS works | Security model |
| backend/action_execution_flow.md | How actions execute | Backend internals |
| verification/README.md | What verification system is | Meta-system docs |

**No duplicate concepts across files.**
**Each file has a single responsibility.**

---

## REDUNDANCY ELIMINATION

### Duplicate Concepts Found

1. **Architecture:**
   - ARCHITECTURE.md
   - DEPLOYMENT_ARCHITECTURE.md
   - FRAMEWORK_OVERVIEW.md

   **Resolution:** Keep ARCHITECTURE.md (high-level), DEPLOYMENT_ARCHITECTURE.md (ops-specific). FRAMEWORK_OVERVIEW.md → merge into ARCHITECTURE.md.

2. **Handover:**
   - ENGINEER_HANDOVER.md (old)
   - _HANDOVER/* (old)
   - handover/* (new)

   **Resolution:** Delete ENGINEER_HANDOVER.md. Move _HANDOVER/* to handover/.

3. **Testing:**
   - TESTING_STANDARDS.md
   - TEST_COVERAGE_REPORT.md
   - ACTION_VERIFICATION_GUIDE.md (verification system)
   - ACTION_VERIFICATION_TEMPLATE.md (verification system)

   **Resolution:** Keep TESTING_STANDARDS.md and TEST_COVERAGE_REPORT.md in docs/. Move ACTION_VERIFICATION_* to verification/.

4. **Quick Start:**
   - README.md
   - QUICK_REFERENCE.md
   - QUICK_START_VERIFICATION.md

   **Resolution:** Keep README.md at root. Move QUICK_REFERENCE.md to docs/. Move QUICK_START_VERIFICATION.md to verification/.

---

## IMPLEMENTATION COMMANDS

```bash
# Create new directories
mkdir -p handover
mkdir -p docs
mkdir -p database/security
mkdir -p backend
mkdir -p verification/findings

# Move files to handover/
mv SYSTEM_INVENTORY.md handover/
mv SECURITY_INVARIANTS.md handover/
mv MATURITY_ASSESSMENT.md handover/
mv HANDOVER.md handover/
mv _HANDOVER/* handover/
rmdir _HANDOVER

# Move files to docs/
mv ARCHITECTURE.md docs/
mv DATABASE_RELATIONSHIPS.md docs/
mv DEPLOYMENT_ARCHITECTURE.md docs/
mv CUSTOMER_JOURNEY_FRAMEWORK.md docs/
mv FRAMEWORK_OVERVIEW.md docs/
mv GLOSSARY.md docs/
mv MICROACTIONS_EXPLAINED.md docs/
mv SITUATIONS_EXPLAINED.md docs/
mv LOCAL_SETUP.md docs/
mv ONBOARDING.md docs/
mv QUICK_REFERENCE.md docs/
mv TESTING_STANDARDS.md docs/
mv TEST_COVERAGE_REPORT.md docs/
mv KNOWN_ISSUES.md docs/

# Rename database/migrations/ to database/tenant_migrations/
mv database/migrations database/tenant_migrations

# Move verification files
mv AGENT_*.md verification/
mv WATCHDOG_*.md verification/
mv VERIFICATION_*.md verification/
mv LAUNCH_*.md verification/
mv AUTONOMOUS_VERIFICATION_SYSTEM_READY.md verification/
mv PREVENTING_AI_OVERWHELM.md verification/
mv MULTI_AGENT_VERIFICATION_PLAN.md verification/
mv QUICK_START_VERIFICATION.md verification/
mv QUICK_VERIFY_TEMPLATE.md verification/
mv AGENT_PROGRESS.md verification/
mv _VERIFICATION/* verification/findings/
rmdir _VERIFICATION

# Delete redundant files
rm ENGINEER_HANDOVER.md
rm REPOSITORY_MAP.md

# Create placeholder READMEs
echo "# Database Documentation" > database/README.md
echo "# Backend Implementation Documentation" > backend/README.md
echo "# Verification System (Meta-System)" > verification/README.md
```

---

## BEFORE / AFTER COMPARISON

### BEFORE (79 files at root)

```
BACK_BUTTON_CLOUD_PMS/
├── README.md
├── ENGINEER_HANDOVER.md
├── ARCHITECTURE.md
├── DATABASE_RELATIONSHIPS.md
├── DEPLOYMENT_ARCHITECTURE.md
├── CUSTOMER_JOURNEY_FRAMEWORK.md
├── FRAMEWORK_OVERVIEW.md
├── GLOSSARY.md
├── MICROACTIONS_EXPLAINED.md
├── SITUATIONS_EXPLAINED.md
├── LOCAL_SETUP.md
├── ONBOARDING.md
├── QUICK_REFERENCE.md
├── TESTING_STANDARDS.md
├── TEST_COVERAGE_REPORT.md
├── KNOWN_ISSUES.md
├── AGENT_1_COMPLETE.md
├── AGENT_2_HANDOFF.md
├── AGENT_3_HANDOFF.md
├── AGENT_4_PROMPT.md
├── WATCHDOG_AGENT_SPEC.md
├── VERIFICATION_METHODOLOGY.md
├── MULTI_AGENT_VERIFICATION_PLAN.md
├── ... (56 more files at root)
├── _HANDOVER/
│   ├── README.md
│   ├── 01_STATUS.md
│   ├── 02_WHATS_LEFT.md
│   ├── 03_HOW_TO_RUN.md
│   └── 04_KNOWN_TRAPS.md
├── _VERIFICATION/
│   ├── verify_create_work_order.md
│   ├── PATTERN_ANALYSIS.md
│   └── ... (13 more files)
└── ...
```

**Problems:**
- ❌ 79 files at root (overwhelming)
- ❌ No clear entry point
- ❌ Meta-docs (Agent/Watchdog) mixed with product docs
- ❌ Handover docs scattered
- ❌ No clear file organization

---

### AFTER (9 files at root)

```
BACK_BUTTON_CLOUD_PMS/
├── README.md                     ← Entry point
├── briefing.md                   ← Project briefing
├── .env.example
├── .gitignore
├── package.json
├── playwright.config.ts
├── render.yaml
├── docker-compose.yml
├── build.sh
│
├── handover/                     ← CRITICAL: Read this first
│   ├── README.md
│   ├── SYSTEM_INVENTORY.md
│   ├── SECURITY_INVARIANTS.md
│   ├── MATURITY_ASSESSMENT.md
│   ├── HANDOVER.md
│   ├── 01_STATUS.md
│   ├── 02_WHATS_LEFT.md
│   ├── 03_HOW_TO_RUN.md
│   └── 04_KNOWN_TRAPS.md
│
├── docs/                         ← Product documentation
│   ├── ARCHITECTURE.md
│   ├── DATABASE_RELATIONSHIPS.md
│   └── ... (12 more docs)
│
├── database/                     ← Database schemas
│   ├── README.md
│   ├── master_migrations/
│   ├── tenant_migrations/        ← Renamed from migrations/
│   └── security/
│       ├── rls_model.md
│       ├── token_lifecycle.md
│       └── threat_model.md
│
├── backend/                      ← Backend implementation docs
│   ├── action_execution_flow.md
│   ├── nl_pipeline.md
│   └── error_handling.md
│
├── verification/                 ← Verification system (meta-system)
│   ├── README.md
│   ├── MULTI_AGENT_VERIFICATION_PLAN.md
│   ├── AGENT_*.md (19 files)
│   ├── WATCHDOG_*.md (5 files)
│   └── findings/
│       ├── PATTERN_ANALYSIS.md
│       ├── verify_*.md (5 files)
│       └── ... (10 more files)
│
├── apps/                         ← Source code
├── tests/                        ← Test suite
├── scripts/                      ← Utility scripts
└── _archive/                     ← Historical docs
```

**Benefits:**
- ✅ 9 files at root (down from 79)
- ✅ Clear entry point (README.md → handover/)
- ✅ Meta-docs separated from product docs
- ✅ Handover docs consolidated
- ✅ Self-explanatory structure

---

## VALIDATION CRITERIA

**After reorganization, answer these questions:**

1. **Can a new engineer find the entry point in <10 seconds?**
   - ✅ Yes: README.md at root says "Read handover/ first"

2. **Can a new engineer find handover docs in <30 seconds?**
   - ✅ Yes: handover/ folder at top level

3. **Can a new engineer distinguish product docs from meta-docs?**
   - ✅ Yes: docs/ = product, verification/ = meta

4. **Can a new engineer find database migrations?**
   - ✅ Yes: database/tenant_migrations/ and database/master_migrations/

5. **Can a new engineer understand security model?**
   - ✅ Yes: handover/SECURITY_INVARIANTS.md + database/security/

6. **Is there duplicate documentation?**
   - ✅ No: Redundant files merged or deleted

---

## ROLLOUT PLAN

**Phase 1:** Create new structure (30 min)
```bash
# Run all mkdir and mv commands above
```

**Phase 2:** Update cross-references (30 min)
```bash
# Update README.md to point to handover/
# Update handover/README.md to reference correct file paths
# Update docs that reference moved files
```

**Phase 3:** Verify (15 min)
```bash
# Check all internal links work
# Check no broken references
# Check new structure is self-explanatory
```

**Phase 4:** Commit (5 min)
```bash
git add .
git commit -m "Reorganize repository structure: consolidate docs, separate meta-docs, create handover/"
git push
```

**Total time:** 80 minutes

---

**This reorganization will make the repository self-explanatory and reduce cognitive load for new engineers.**
