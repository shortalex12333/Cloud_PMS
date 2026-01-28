# README — Start Here

**Date:** 2026-01-22
**Purpose:** Navigation guide for CelesteOS architecture documentation
**Status:** Living document (updated as layers complete)

---

## What is CelesteOS?

**CelesteOS is "Apple Spotlight for yacht management"** — a search-first control system that morphs dynamically based on user intent.

**Core principle:** One search bar, no navigation, zero presumption. UI activates only after user clicks. Designed for crew working under pressure (gloves, noise, heat, uncertainty).

**Primary avatar:** Sarah (new, unsure, cautious) — we design for the least confident operator doing real work.

---

## How Documentation is Layered

### Layer A: Global Architecture (Foundational — Read First)

**Purpose:** How the system thinks, routes, and preserves context

| File | What It Covers | Read If... |
|------|----------------|------------|
| `00_YOU_ARE_HERE.md` | Action count reconciliation, verification gaps, domain situations | You need to know current system state |
| `02_GLOBAL_ROUTER_FLOW.md` | 4-stage flow: Input → Entity Extraction → Click → Action | You need to understand search → commit path |
| `03_JOURNEY_ARCHITECTURE.md` | Context preservation, action sequences, contradiction detection | You need to understand state + context flow |
| `08_FLOWCHARTS/global_router.md` | Mermaid visualization of global flow | You prefer diagrams to prose |

**Status:** ✅ Locked. Do not modify without explicit design review.

---

### Layer 1: Gold Set User Journeys (Learning Document)

**Purpose:** Shared mental model — covers 80-90% of real use

| File | What It Covers |
|------|----------------|
| `04_USER_JOURNEYS.md` | 7 user narratives (Sarah, Mike, Receiving, Checklist, Chief Engineer, Captain, Stewardess) |
| `05_JOURNEY_PATTERNS.md` | Pattern library — 9 reusable flow shapes (`[SINGLE_STEP]`, `[MULTI_STEP]`, `[AUTO_CREATE]`, etc.) |

**Read these BEFORE cluster documentation.** They establish shared language and flow shapes.

**Status:** ✅ Locked. Terminology and patterns are frozen.

---

### Layer 2: Cluster Journey Batches (Reference by Domain)

**Purpose:** Comprehensive action coverage — one file per canonical cluster

**Batch 1: Core (Lock the MVP)** — ✅ Complete
- `08_FLOWCHARTS/clusters/faults_cluster_journeys.md` (17 actions)
- `08_FLOWCHARTS/clusters/work_orders_cluster_journeys.md` (13 actions)
- `08_FLOWCHARTS/clusters/handover_cluster_journeys.md` (8 actions)

**Batch 2: State-Heavy (Financial Gravity)** — 🚧 In Progress
- `08_FLOWCHARTS/clusters/inventory_cluster_journeys.md`
- `08_FLOWCHARTS/clusters/purchasing_cluster_journeys.md`
- `08_FLOWCHARTS/clusters/equipment_cluster_journeys.md`

**Batch 3: Governance** — ⏳ Pending
- `08_FLOWCHARTS/clusters/checklists_cluster_journeys.md`
- `08_FLOWCHARTS/clusters/compliance_cluster_journeys.md`
- `08_FLOWCHARTS/clusters/shipyard_cluster_journeys.md`

**Batch 4: Support/Future** — ⏳ Pending
- `08_FLOWCHARTS/clusters/documents_cluster_journeys.md`
- `08_FLOWCHARTS/clusters/fleet_cluster_journeys.md`
- `08_FLOWCHARTS/clusters/system_utility_cluster_journeys.md`

**How to read cluster files:**
1. Start with Cluster Contract (boundaries)
2. Read Gold Journey (most common path)
3. Skim Journey Variations (how gold differs)
4. Reference Signature Map (compliance implications)
5. Check Cross-Cluster Relationships (dependencies)

**Status:** Batch 1 locked. Batch 2+ follow validated template.

---

### Layer 3: Purpose Journey Maps (User Intent Navigation)

**Purpose:** Answer "I want to..." queries across clusters

**Files (7 customer purposes):**
- Fix Something
- Do Maintenance
- Manage Equipment
- Control Inventory
- Communicate Status
- Comply & Audit
- Procure

**Status:** ⏳ Not started (begins after Layer 2 complete)

---

### Layer C: Action Cards (Gold Set Micro-Specs)

**Purpose:** Atomic action specs for top actions (inputs, tables, validations, audit)

**Scope:** Top 10 most-used actions + all MUTATE_HIGH actions

**Status:** ⏳ Not started (begins after Layer 2 complete)

---

## What is Locked vs Still Evolving

### ✅ LOCKED (Do Not Modify Without Review)

- **Layer A:** Global router flow, context preservation, 4-stage flow
- **Journey Patterns:** 9 patterns defined in `05_JOURNEY_PATTERNS.md`
- **Terminology:** Journey, cluster journey, action card, pattern, situation, avatar
- **Signature Language:** Only 2 phrases allowed:
  - "Signature required at irreversible commit"
  - "No signature required (informational)"
- **Template Structure:** Cluster Contract, Gold Journey, Variations, Signature Map, STOP conditions
- **NON-NEGOTIABLES:**
  - One MUTATE action committed per user confirmation
  - Atomic transactions: operational table + ledger_events + audit_log (if required)
  - Audit failure = transaction failure (ROLLBACK if audit INSERT fails)

### 🚧 EVOLVING (Active Work)

- **Layer 2:** Cluster journey batches (Batch 2 in progress)
- **Verification Status:** Only 1/71 actions proven to write to DB, 4/71 have audit logs, 0/71 have RLS tests

### ⏳ NOT STARTED

- **Layer 3:** Purpose journey maps
- **Layer C:** Action cards

---

## Critical Context for Contributors

### What CelesteOS Is NOT

❌ Traditional navigation-based yacht software (multiple pages, nested menus)
❌ Presumptive system (no "smart" context guessing)
❌ Workflow automation (actions are atomic, journeys are user-led)
❌ ML prediction engine (deterministic state machine)

### What "Situations" Are

**UI Situations (Exists):** IDLE → CANDIDATE (click) → ACTIVE (commitment signal)
- Equipment Situation
- Document Situation
- Inventory Situation
- Work Order Situation
- Fault Situation

**Operational Contexts (Proposed Placeholders):** At sea, in port, underway, maintenance mode — NOT implemented, NOT driving UX

### Core Principles

1. **"Search is passive. Click is commitment."** — No actions appear in search results
2. **"Silence as a feature"** — Document what does NOT happen
3. **"Design for Sarah"** — Least confident operator under pressure
4. **"One MUTATE per confirmation"** — No silent state transitions

### Signature Philosophy

- **Sign at irreversible commit** (inventory deduction, fault closure, WO completion)
- **Not at intent** (draft, start, assign, add note)
- **Not per step** (multi-step flows sign ONCE at end)
- **Per-action based on meaning** (not strict risk class)

### Authentication & Attestation Policy

CelesteOS supports step-up authentication (PIN) and attestation (signature) for high-impact actions. **MVP uses confirm-only flows.** PIN and signature will be introduced before production without altering journey structure.

- **Step-up auth (PIN):** Session timeout, shared device context, handoff scenarios
- **Attestation (signature):** Irreversible commits, financial settlement, compliance sign-off
- **Threshold-based:** Inventory adjustments >5 units or >$500 require signature

This closes "login theft" loophole without signature fatigue.

---

## Verification Gaps (Critical)

**The blocker to production is NOT feature count — it's verification.**

Current status:
- ✅ 76 actions designed
- ✅ 71 actions in registry
- ⚠️ Only 1/71 actions proven to write to database
- ⚠️ Only 4/71 have audit logs
- ⚠️ 0/71 have RLS tests

**This documentation does NOT fix that gap.** It designs the system completely so "build becomes scaffolding + execution."

---

## Read Order (Recommended)

**For new contributors:**
1. This file (orientation)
2. `04_USER_JOURNEYS.md` (Sarah's journey, Mike's journey)
3. `05_JOURNEY_PATTERNS.md` (pattern library)
4. `02_GLOBAL_ROUTER_FLOW.md` (4-stage flow)
5. One cluster file from Batch 1 (see template structure)

**For implementers:**
1. Cluster journey file for your domain
2. Signature Map (compliance implications)
3. Cross-Cluster Relationships (dependencies)
4. STOP conditions (guardrails)

**For auditors:**
1. `00_YOU_ARE_HERE.md` (verification gaps)
2. Signature Map in each cluster file
3. `03_JOURNEY_ARCHITECTURE.md` (context preservation)

---

## Questions?

If anything contradicts across files, the hierarchy is:
1. This README (orientation)
2. Layer A (global architecture)
3. Layer 1 (gold set)
4. Layer 2 (cluster batches)

If you find drift, flag it immediately. Six weeks of discipline can be undone in one afternoon.

---

**Last Updated:** 2026-01-22 (Batch 1 complete, Batch 2 in progress)
