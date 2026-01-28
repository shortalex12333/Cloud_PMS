# REPOSITORY ORIENTATION: STEP 6 - SYSTEM INTENT

**Date:** 2026-01-22
**Purpose:** Document who uses this, what problem it solves, why micro-actions exist
**Status:** Truth documented

---

## WHO ARE THE USERS?

### Primary Users: Yacht Crew

**Roles (from microaction_registry.ts:40, 132-134):**

1. **Crew** (`crew`, `member`) - General crew members
   - Report faults
   - Add notes and photos
   - View equipment manuals
   - Check stock levels

2. **Engineers** (`engineer`, `2nd_engineer`) - Technical staff
   - Diagnose faults
   - Execute maintenance work
   - Log part usage
   - Complete work orders
   - Update equipment status

3. **Senior Engineers** (`chief_engineer`, `eto`) - Technical leadership
   - Create work orders
   - Assign work
   - Approve maintenance plans
   - Tag equipment for surveys

4. **Officers** (`chief_officer`, `captain`) - Command staff
   - Approve work orders
   - Review compliance status
   - Export reports for audits
   - Manage fleet-level operations

5. **Shore-Based** (`manager`, `admin`) - Shore support
   - Approve purchases
   - Track delivery status
   - Review compliance across fleet
   - Generate audit reports

### User Context: Maritime Environment

**Operational Constraints:**
- ⚛️ **Limited connectivity** - Intermittent internet at sea
- 🕐 **24/7 operations** - Ships never stop
- 👥 **Multi-national crews** - Language barriers, varying technical expertise
- 📱 **Mobile-first** - Engineers work with tablets/phones in engine rooms
- 🔧 **High-stress environment** - Urgent repairs, safety-critical equipment
- 📋 **Strict compliance** - ISO 9001, SOLAS, flag state regulations

**User Needs:**
- **Fast:** Minimal clicks to report fault or log part usage
- **Simple:** No technical jargon, visual guides
- **Contextual:** Right actions offered at right time (based on entity status)
- **Offline-capable:** Work offline, sync when connected (NOT YET IMPLEMENTED)
- **Audit-ready:** Every action logged for compliance (PARTIALLY IMPLEMENTED)

---

## WHAT PROBLEM DOES THIS SYSTEM SOLVE?

### Problem Statement

**Traditional yacht maintenance is reactive, paper-based, and compliance-fragile.**

**Pain Points:**

1. **Reactive Maintenance**
   - Equipment fails unexpectedly
   - No historical data on faults
   - Difficult to identify recurring issues
   - Downtime costs hundreds of thousands per day

2. **Paper-Based Systems**
   - Work orders written on paper
   - Parts usage tracked in spreadsheets
   - Compliance reports assembled manually before audits
   - Prone to loss, errors, incomplete records

3. **Knowledge Silos**
   - Senior engineer knows how to fix specific equipment
   - Junior engineers don't have access to that knowledge
   - Equipment manuals stored as PDFs, hard to search
   - Tribal knowledge lost when crew changes

4. **Compliance Risk**
   - Auditors require proof of maintenance (ISO 9001, SOLAS)
   - Missing audit logs = fines, detentions, insurance issues
   - Hours of rest tracking required by law (crew fatigue)
   - Survey items must be tracked (flag state requirements)

5. **Inventory Chaos**
   - Parts ordered late (no stock tracking)
   - Duplicate orders (no visibility into pending deliveries)
   - Critical spares missing (no low-stock alerts)
   - Budget overruns (no purchase approval workflow)

### Solution: CelesteOS Cloud PMS

**Vision:** AI-assisted, context-aware maintenance system that guides crew through correct actions at correct times.

**Core Capabilities:**

1. **Natural Language Interface**
   - Crew: "The generator is overheating"
   - System: Extracts entity (generator), problem (overheating), offers actions: [diagnose_fault, view_history, view_manual]
   - Crew: Clicks [diagnose_fault]
   - System: Returns diagnostic steps, suggests parts

2. **Micro-Actions: Granular Workflow Steps**
   - Break complex workflows into small, executable actions
   - Each action: Single purpose, clear inputs, predictable outputs
   - Actions are context-aware (only shown when relevant)
   - Examples: `report_fault`, `diagnose_fault`, `create_work_order_from_fault`, `mark_work_order_complete`

3. **Audit Trail by Default**
   - Every mutation creates audit log entry (PARTIALLY IMPLEMENTED)
   - Compliance reports generated automatically
   - Forensics: Who did what, when, why

4. **Knowledge Embedded**
   - Equipment manuals RAG-indexed (Retrieval-Augmented Generation)
   - AI diagnosis suggests likely causes + parts
   - Historical fault patterns inform current diagnosis

5. **Multi-Yacht Isolation**
   - Single Postgres database, RLS enforces yacht boundaries
   - Yacht A cannot see Yacht B's data
   - Shared codebase, tenant-isolated data

---

## WHY MICRO-ACTIONS EXIST

### Design Philosophy

**Micro-actions are the atomic units of maintenance work.**

**Why Not Monolithic Forms?**

Traditional PMS systems have:
- ❌ Complex multi-page forms
- ❌ Unclear what's required vs optional
- ❌ No guidance on what to do next
- ❌ All-or-nothing submission (lose progress if form crashes)

**Micro-Action Benefits:**

1. **Single Responsibility**
   - `report_fault`: Only creates fault, nothing else
   - `diagnose_fault`: Only adds diagnosis, doesn't create work order
   - `create_work_order_from_fault`: Only creates work order, doesn't assign crew

   **Why:** Easier to understand, test, debug, maintain

2. **Context-Aware Offering**
   - Frontend: "Fault status = diagnosed → offer [create_work_order_from_fault, suggest_parts]"
   - Frontend: "Fault status = open → offer [diagnose_fault, add_note]"
   - Frontend: "Work order status = in_progress → offer [add_part, log_hours, mark_complete]"

   **Why:** User only sees relevant actions, reducing cognitive load

3. **Role-Based Access**
   - `report_fault`: Any crew member (G0: always allowed)
   - `diagnose_fault`: Any role (G0: always allowed)
   - `create_work_order_from_fault`: HOD only (G1: role-based)
   - `approve_purchase`: HOD only (G1: role-based)

   **Why:** Enforces organizational hierarchy, prevents unauthorized actions

4. **Status-Based Gating**
   - `create_work_order_from_fault`: Requires fault status = ['diagnosed', 'acknowledged', 'open']
   - `suggest_parts`: Requires fault status = ['diagnosed']
   - `mark_work_order_complete`: Requires work order status = ['in_progress', 'assigned']

   **Why:** Enforces correct workflow order, prevents out-of-sequence actions

5. **Testability**
   - Each action has defined inputs (`requiredFields`)
   - Each action has expected outputs (`expectedChanges`)
   - Each action has known edge cases (`edgeCases`)

   **Why:** Automated testing possible (PARTIALLY IMPLEMENTED)

6. **AI-Friendly**
   - Natural language query → AI extracts entity + intent → System maps to micro-action
   - Example: "Log 5 liters of oil used for generator maintenance"
     - Entity: generator
     - Intent: log part usage
     - Action: `log_part_usage`
     - Payload: `{part_id: 'oil', quantity: 5, work_order_id: 'xxx'}`

   **Why:** AI can orchestrate complex workflows by chaining micro-actions

---

## BUSINESS CONTEXT

### Industry: Superyacht Management

**Market:**
- **Vessel type:** Private superyachts (30m - 100m+)
- **Crew size:** 6-50 crew per yacht
- **Fleet size:** 1-50+ yachts per management company
- **Maintenance budget:** $500k - $5M per yacht per year
- **Downtime cost:** $50k - $500k per day (charter cancellations, reputational damage)

**Compliance Requirements:**

1. **ISO 9001** (Quality Management)
   - Documented maintenance procedures
   - Audit trail for all work performed
   - Corrective action tracking

2. **SOLAS** (Safety of Life at Sea)
   - Critical equipment maintenance logs
   - Safety equipment inspections
   - Emergency drills documented

3. **Flag State Regulations**
   - Varies by yacht registration (Cayman, Marshall Islands, UK, etc.)
   - Annual surveys (hull, machinery, safety equipment)
   - Audit readiness (inspectors can board at any time)

4. **Hours of Rest (Maritime Labour Convention)**
   - Crew must have minimum rest periods
   - Violations = fines, detentions
   - Must be tracked and reported

5. **ISM Code** (International Safety Management)
   - Documented Safety Management System
   - Non-conformities tracked and resolved
   - Management review of incidents

### Regulatory Risk

**Non-compliance consequences:**
- 💰 **Fines:** $10k - $500k per violation
- 🚢 **Detention:** Port state control can detain vessel until compliance restored
- 📄 **Certification loss:** Can lose flag state certificates (vessel cannot operate)
- 💼 **Insurance issues:** Insurers require proof of maintenance
- 🔍 **Charter impact:** Clients require compliance documentation before booking

**Why this system matters:** Audit-ready by default. Every action logged, compliance reports generated automatically.

---

## SYSTEM ARCHITECTURE INTENT

### Two-Database Model

**MASTER DB:**
- **Purpose:** Fleet registry, user authentication, tenant routing
- **Tables:** `fleet_registry`, `user_accounts`, `db_registry`, `security_events`
- **Why:** Centralized user management, cross-yacht visibility for fleet managers

**TENANT DB:**
- **Purpose:** Per-yacht PMS data (equipment, faults, work orders, parts)
- **Tables:** `pms_equipment`, `pms_faults`, `pms_work_orders`, `pms_parts`, etc.
- **RLS:** Enforces `yacht_id` isolation (Yacht A cannot see Yacht B's data)
- **Why:** Tenant isolation, compliance with data privacy regulations

### RLS (Row-Level Security) Intent

**Goal:** Multi-tenant isolation at database level.

**Why NOT per-tenant databases?**
- ❌ Operational overhead (100+ yachts = 100+ databases)
- ❌ Cross-yacht queries impossible (fleet managers need aggregated views)
- ❌ Schema migrations require updating 100+ databases

**Why RLS?**
- ✅ Single database, single schema
- ✅ RLS policies enforce tenant boundaries
- ✅ Fleet managers can query across yachts (with permission)
- ✅ Simplified operations (one database to maintain)

**RLS Policy Pattern:**
```sql
CREATE POLICY "Yacht isolation" ON pms_faults
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);
```

**How it works:**
1. User authenticates → JWT contains `yacht_id`
2. Backend sets session variable: `SET app.current_yacht_id = 'xxx'`
3. All queries filtered by RLS policy
4. User can only see/modify rows where `yacht_id` matches their yacht

**Status:** RLS policies exist, NOT TESTED (0/64 actions tested).

---

## NL→ACTION PIPELINE INTENT

### Vision: Conversational Maintenance

**User:** "The generator is overheating"

**System Flow:**

1. **NL Extraction (GPT-4o-mini):**
   ```
   Input: "The generator is overheating"
   Output: {
     entity_type: "equipment",
     entity_name: "generator",
     problem: "overheating",
     intent: "report_issue"
   }
   ```

2. **Entity Lookup (Database):**
   ```sql
   SELECT id FROM pms_equipment
   WHERE yacht_id = 'xxx'
   AND (name ILIKE '%generator%' OR type = 'generator')
   LIMIT 1
   ```

3. **Action Offering (Registry):**
   ```
   Entity: equipment (generator)
   Problem: overheating
   Possible actions:
   - report_fault (create fault for this equipment)
   - view_equipment_history (see past issues)
   - view_manual (look up troubleshooting steps)
   - diagnose_fault (if fault already exists)
   ```

4. **User Selection:**
   - User clicks [Report Fault]

5. **Action Execution:**
   ```http
   POST /v1/actions/execute
   {
     "action": "report_fault",
     "payload": {
       "equipment_id": "xxx",
       "description": "Generator overheating",
       "priority": "high"
     }
   }
   ```

6. **AI Diagnosis (Auto-Run):**
   - `diagnose_fault` action auto-runs (because `triggers.autoRun = true`)
   - System queries fault code database
   - Returns: "Likely cause: Coolant low. Check coolant level, inspect for leaks."

7. **Next Actions Offered:**
   - `suggest_parts`: Coolant, hoses, gaskets
   - `create_work_order_from_fault`: Create maintenance work order
   - `view_manual`: View generator manual section on cooling system

**Status:** NL→Action pipeline works (64/64 tests pass), but AI diagnosis quality unknown.

---

## WHY THIS SYSTEM EXISTS (USER STORIES)

### Story 1: Junior Engineer Fixing Fault

**User:** Junior engineer (2nd engineer)

**Scenario:** Generator shows fault code E420

**Without CelesteOS:**
1. Engineer sees fault code on display
2. Searches for paper manual (10 minutes)
3. Finds fault code table, reads "Coolant temperature high"
4. Doesn't know what to check first
5. Calls chief engineer (who is off-duty)
6. Waits for guidance (30 minutes)
7. Eventually resolves issue (total: 1 hour)

**With CelesteOS:**
1. Engineer: "Generator fault E420"
2. System: Shows fault history (happened twice before, both times resolved by adding coolant)
3. System: Offers [Diagnose Fault] action
4. Engineer: Clicks [Diagnose Fault]
5. System: "Likely cause: Coolant low. Check coolant level, add coolant if below minimum."
6. Engineer: Adds coolant, fault clears
7. Engineer: Clicks [Resolve Fault] with note "Added 2L coolant"
8. System: Creates audit log entry (total: 10 minutes)

**Value:** 50-minute time savings, reduced downtime, junior engineer empowered without senior guidance.

---

### Story 2: Compliance Audit

**User:** Captain

**Scenario:** Port state control inspector boards yacht, requests maintenance records

**Without CelesteOS:**
1. Inspector: "Show me all generator maintenance in past 12 months"
2. Captain: Searches paper files (30 minutes)
3. Finds some work orders, missing others
4. Engineer manually compiles list (1 hour)
5. Inspector: "Show me parts usage for this work order"
6. Engineer: "That's in a different spreadsheet" (30 minutes to find)
7. Inspector: Identifies missing audit trail, issues deficiency
8. Result: Vessel detained until deficiency resolved (cost: $50k+ per day)

**With CelesteOS:**
1. Inspector: "Show me all generator maintenance in past 12 months"
2. Captain: Opens CelesteOS, exports equipment history report
3. System: Generates PDF with all work orders, parts used, photos, completion signatures (30 seconds)
4. Inspector: Reviews, satisfied
5. Result: No deficiency, vessel clears inspection

**Value:** Compliance risk eliminated, $50k+ detention cost avoided.

---

### Story 3: Budget Planning

**User:** Fleet manager (shore-based)

**Scenario:** Planning annual maintenance budget for 10-yacht fleet

**Without CelesteOS:**
1. Manager: Requests maintenance data from each yacht
2. Engineers: Manually compile spreadsheets (2 hours per yacht)
3. Manager: Aggregates 10 spreadsheets (4 hours)
4. Identifies: Generator maintenance costs vary wildly across fleet (why?)
5. Cannot identify root cause (incomplete data)
6. Budgets based on historical averages (inaccurate)

**With CelesteOS:**
1. Manager: Opens fleet summary dashboard
2. System: Shows aggregated maintenance costs by equipment type across all yachts
3. Identifies: Yacht 5 generator costs 3x fleet average
4. Drills down: Yacht 5 had recurring coolant leak (fault closed as resolved, but recurred 5 times)
5. Action: Authorize generator replacement on Yacht 5
6. Budget: Accurate forecast based on real data

**Value:** Data-driven decisions, proactive equipment replacement, budget accuracy.

---

## WHAT THIS SYSTEM IS NOT

**NOT a traditional CMMS** (Computerized Maintenance Management System)
- Traditional CMMS: Complex, desktop-based, requires training
- CelesteOS: Simple, mobile-first, AI-guided

**NOT a document management system**
- Purpose: Actionable maintenance workflows, not file storage
- Documents are context (manuals, invoices), not primary focus

**NOT an ERP** (Enterprise Resource Planning)
- Purpose: Maintenance + inventory, not accounting/HR/payroll
- Purchasing workflow exists, but financial management is external

**NOT a real-time monitoring system**
- Does NOT integrate with equipment sensors (yet)
- Reactive + preventive maintenance, not predictive (yet)

**NOT offline-first** (yet)
- Requires internet connection
- Offline-capable is roadmap, not implemented

---

## FUTURE VISION (Not Implemented)

### Predictive Maintenance

**Goal:** Predict equipment failures before they occur.

**How:**
- IoT sensors on equipment (temperature, vibration, runtime hours)
- ML model: Analyze patterns, predict failures
- System: Auto-creates preventive work orders before failure

**Status:** NOT IMPLEMENTED

---

### Offline-First

**Goal:** Work offline, sync when connected.

**How:**
- PWA (Progressive Web App) with service worker
- IndexedDB local storage
- Conflict resolution when syncing

**Status:** NOT IMPLEMENTED

---

### Fleet-Wide Analytics

**Goal:** Cross-yacht insights for fleet managers.

**How:**
- Aggregate fault patterns across fleet
- Identify common issues
- Benchmark yacht performance

**Status:** PARTIALLY IMPLEMENTED (fleet summary exists, analytics missing)

---

## SUMMARY: SYSTEM INTENT

**Who Uses This:**
- Yacht crew (crew, engineers, officers, shore managers)
- Maritime environment (24/7 ops, limited connectivity, compliance-critical)

**What Problem It Solves:**
- Reactive maintenance → Proactive + AI-assisted
- Paper-based → Digital audit trail
- Knowledge silos → Embedded expertise
- Compliance risk → Audit-ready by default
- Inventory chaos → Real-time stock tracking

**Why Micro-Actions Exist:**
- Atomic units of work (single responsibility)
- Context-aware offering (right actions at right time)
- Role/status-based gating (enforce workflows)
- Testable and AI-friendly

**Business Context:**
- Superyacht industry
- $500k - $5M maintenance budgets per yacht
- Compliance-critical (ISO 9001, SOLAS, flag state regulations)
- Non-compliance = fines, detentions, insurance issues

**Architecture Intent:**
- Two-database model (MASTER for users, TENANT for PMS data)
- RLS for multi-tenant isolation (single database, yacht boundaries enforced)
- NL→Action pipeline (conversational interface for crew)

**What This System Is:**
- AI-assisted maintenance system
- Mobile-first, context-aware
- Audit-ready by default

**What This System Is Not:**
- NOT traditional CMMS (too complex)
- NOT document management (documents are context)
- NOT ERP (maintenance + inventory only)
- NOT real-time monitoring (yet)
- NOT offline-first (yet)

---

**Status:** Repository orientation complete (STEPS 1-6 documented).

**Truth:** We now understand what this system is, who it's for, and why it exists.

**Next:** Use these 6 documents to guide verification, testing, and handover.
