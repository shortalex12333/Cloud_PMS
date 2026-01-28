# Handover Bucket System — Feasibility Analysis

> **Document**: `ANALYSIS_feasibility.md`
> **Created**: 2026-01-14
> **Purpose**: Gap analysis between 18_handover_buckets requirements, current schema, and existing IMPL_03
> **For**: Claude B implementation planning

---

## Executive Summary

The 18_handover_buckets folder contains a **comprehensive behavioral specification** for the handover system that is **more detailed and structured** than the existing IMPL_03_handover_continuity.sql.md specification.

Key differences:
- **18_handover_buckets**: Domain-code driven, 6 presentation buckets, 28 domain codes, 7-stage generation pipeline
- **IMPL_03**: Department-based, simpler status machine, ledger-event driven proposals

**Recommendation**: Treat 18_handover_buckets as the **authoritative specification**. Revise IMPL_03 to conform.

---

## Part 1: Current Schema Capabilities

### What Already Exists (Cloud_PMS codebase)

| Component | Location | Status |
|-----------|----------|--------|
| `pms_handover` table | DATABASE_SCHEMA_COMPLETE.sql | Basic implementation |
| `pms_handover_items` table | DATABASE_SCHEMA_COMPLETE.sql | Basic implementation |
| `auto_add_fault_to_handover()` | DATABASE_SCHEMA_V3_COMPLETE.sql | Trigger function |
| `add_to_handover` handler | handlers/handover_handlers.py | API endpoint |
| HandoverCard component | components/cards/HandoverCard.tsx | Frontend |
| AddToHandoverModal | components/modals/AddToHandoverModal.tsx | Frontend |

### Current `pms_handover` Table Structure

```
id                  UUID (pk)
yacht_id            UUID
entity_type         TEXT (polymorphic)
entity_id           UUID
title               TEXT
description         TEXT
priority            TEXT
category            TEXT
auto_added          BOOLEAN
auto_add_reason     TEXT
acknowledged_by     UUID[]
status              TEXT ('active', 'acknowledged', 'resolved', 'archived')
created_by          UUID
created_at          TIMESTAMPTZ
```

### Gap: Missing Columns in Current Schema

| Required by 18_handover_buckets | Exists? | Notes |
|--------------------------------|---------|-------|
| `primary_domain` (e.g., ENG-01) | NO | Critical gap - domain taxonomy |
| `secondary_domains[]` | NO | Multi-domain support |
| `presentation_bucket` | NO | 6-bucket taxonomy |
| `suggested_owner_roles[]` | NO | Role-based biasing |
| `risk_tags[]` | NO | Risk hierarchy |
| `source_event_ids[]` | NO | Ledger linkage |
| `source_document_ids[]` | NO | Document linkage |
| `classification_flagged` | NO | User disputes taxonomy |
| `narrative_text` | Partial | As `description` |

---

## Part 2: 18_handover_buckets vs IMPL_03 Comparison

### Schema Differences

| Aspect | 18_handover_buckets | IMPL_03 | Resolution |
|--------|---------------------|---------|------------|
| **Entry storage** | `handover_entries` (raw truth seeds) | No equivalent - items go straight to drafts | Add `handover_entries` table |
| **Draft table** | `handover_drafts` with `period_start/end` | `handover_drafts` with `shift_date/period` | Prefer 18's time-range model |
| **State machine** | DRAFT → IN_REVIEW → ACCEPTED → SIGNED → EXPORTED | draft → pending_review → published → countersigned → archived | Align to 18's naming |
| **Sections** | `handover_draft_sections` with `bucket_name` | No equivalent | Add sections table |
| **Items** | `handover_draft_items` with `domain_code`, `confidence_level` | `handover_accepted_items` with simpler structure | Merge concepts |
| **Edit tracking** | `handover_draft_edits` table | Edit columns on items | Add dedicated table |
| **Sign-off** | `handover_signoffs` with outgoing/incoming | `handover_signatures` with type field | Both work, prefer 18's clarity |
| **Exports** | `handover_exports` with recipients | Not defined | Add exports table |

### Domain Taxonomy Gap

**18_handover_buckets defines 28 domain codes:**

Engineering (10):
- ENG-01: Propulsion / Main Engines
- ENG-02: Power Generation / Generators
- ENG-03: Electrical Distribution / Shore Power
- ENG-04: HVAC / Refrigeration / Climate
- ENG-05: Plumbing / Freshwater / Blackwater
- ENG-06: Fuel Systems / Bunkering
- ENG-07: Hydraulics / Stabilisation
- ENG-08: Fire Detection / Suppression
- ENG-09: Safety Systems / Alarms / Bilge
- ENG-10: General Machinery

ETO/AV-IT (6):
- ETO-01: Navigation / Bridge Electronics
- ETO-02: IT / Networks / Cybersecurity
- ETO-03: AV / Entertainment / Cinema
- ETO-04: CCTV / Access Control
- ETO-05: Monitoring / Alarm Integration
- ETO-06: Radio / Satellite / Comms

Deck (6):
- DECK-01: Deck Machinery / Cranes / Davits
- DECK-02: Mooring / Anchoring
- DECK-03: Tenders / Water Toys / PWC
- DECK-04: Exterior Maintenance / Hull
- DECK-05: Bridge / Navigation Watchkeeping
- DECK-06: Safety Equipment / LSA

Interior (4):
- INT-01: Guest Services / Requests / Preferences
- INT-02: Housekeeping / Laundry
- INT-03: Galley / Provisions / F&B
- INT-04: Stores / Inventory / Consumables

Admin (6):
- ADM-01: Compliance / Certificates / Inspections
- ADM-02: Crew Admin / Rotations / Training
- ADM-03: Budget / Finance / Expenses
- ADM-04: Procurement / Vendors
- ADM-05: Port / Agent / Logistics
- ADM-06: Insurance / Claims

Command (3) - Auto-generated:
- CMD-01: Operational Risk State
- CMD-02: Guest Experience State
- CMD-03: Vessel Readiness State

**IMPL_03 has only 5 departments**: engineering, deck, interior, bridge, galley

**Resolution**: Create domain_codes reference table and update IMPL_03.

---

## Part 3: Required New Tables (from 18_handover_buckets)

### 3.1 `handover_entries` - RAW TRUTH SEEDS (NEW)

```sql
CREATE TABLE handover_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_user_id UUID NOT NULL,
    created_by_role TEXT NOT NULL,

    -- Domain taxonomy
    primary_domain TEXT NOT NULL,           -- e.g., 'ENG-01'
    secondary_domains TEXT[],               -- optional overlap
    presentation_bucket TEXT NOT NULL,      -- e.g., 'Engineering'

    -- Role biasing
    suggested_owner_roles TEXT[],           -- inferred from domain + overlap

    -- Risk hierarchy
    risk_tags TEXT[],                       -- Safety-Critical, Compliance-Critical, etc.

    -- Content
    narrative_text TEXT NOT NULL,           -- user-authored or edited

    -- Source tracking
    source_event_ids UUID[],                -- ledger events
    source_document_ids UUID[],             -- emails, files, etc.

    -- Status
    status TEXT NOT NULL DEFAULT 'candidate', -- candidate / suppressed / resolved
    classification_flagged BOOLEAN DEFAULT FALSE,

    CONSTRAINT valid_status CHECK (status IN ('candidate', 'suppressed', 'resolved')),
    CONSTRAINT valid_bucket CHECK (presentation_bucket IN (
        'Command', 'Engineering', 'ETO_AVIT', 'Deck', 'Interior', 'Admin_Compliance'
    ))
);
```

### 3.2 `handover_draft_sections` - BUCKET STRUCTURE (NEW)

```sql
CREATE TABLE handover_draft_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES handover_drafts(id),

    bucket_name TEXT NOT NULL,              -- Command / Engineering / etc.
    section_order INTEGER NOT NULL,         -- display order

    UNIQUE(draft_id, bucket_name)
);
```

### 3.3 `handover_draft_edits` - EDIT AUDIT TRAIL (NEW)

```sql
CREATE TABLE handover_draft_edits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL,
    draft_item_id UUID NOT NULL,

    edited_by_user_id UUID NOT NULL,
    edited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    original_text TEXT NOT NULL,
    edited_text TEXT NOT NULL,
    edit_reason TEXT
);
```

### 3.4 `handover_exports` - EXPORT RECORDS (NEW)

```sql
CREATE TABLE handover_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL,

    export_type TEXT NOT NULL,              -- pdf / html / email
    storage_path TEXT NOT NULL,

    exported_by_user_id UUID NOT NULL,
    exported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    recipients TEXT[],                      -- for email exports
    document_hash TEXT NOT NULL,

    CONSTRAINT valid_export_type CHECK (export_type IN ('pdf', 'html', 'email'))
);
```

---

## Part 4: IMPL_03 Modifications Required

### 4.1 `handover_drafts` Table Modifications

```sql
-- Replace shift_date + shift_period with time range
ALTER TABLE handover_drafts
ADD COLUMN period_start TIMESTAMPTZ,
ADD COLUMN period_end TIMESTAMPTZ,
ADD COLUMN generated_by_version TEXT;

-- Rename status values to match 18_handover_buckets
-- 'draft' → 'DRAFT'
-- 'pending_review' → 'IN_REVIEW'
-- 'published' → 'ACCEPTED'
-- 'countersigned' → 'SIGNED'
-- Add new: 'EXPORTED'

-- Remove department column (sections now control this)
ALTER TABLE handover_drafts DROP COLUMN department;
```

### 4.2 `handover_draft_items` Table (Revise from IMPL_03's accepted_items)

```sql
-- Rename from handover_accepted_items to handover_draft_items
-- Add new columns:
ADD COLUMN section_bucket TEXT;
ADD COLUMN domain_code TEXT;
ADD COLUMN source_entry_ids UUID[];
ADD COLUMN confidence_level TEXT DEFAULT 'MEDIUM';
ADD COLUMN conflict_flag BOOLEAN DEFAULT FALSE;
ADD COLUMN uncertainty_flag BOOLEAN DEFAULT FALSE;
```

### 4.3 `handover_signoffs` Table (Replace signatures)

```sql
-- Consolidate signature model
CREATE TABLE handover_signoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL,

    outgoing_user_id UUID,
    outgoing_signed_at TIMESTAMPTZ,

    incoming_user_id UUID,
    incoming_signed_at TIMESTAMPTZ,

    document_hash TEXT NOT NULL,

    UNIQUE(draft_id)
);
```

---

## Part 5: Missing RPC Functions

### From 18_handover_buckets API Endpoints

| Endpoint | Required RPC | IMPL_03 Coverage | Status |
|----------|-------------|------------------|--------|
| POST /handover/draft/generate | `generate_handover_draft()` | `get_or_create_handover_draft()` | Needs pipeline logic |
| POST /handover/draft/{id}/review | `enter_review_state()` | Not implemented | NEW |
| PATCH /handover/draft/{id}/item/{id} | `edit_draft_item()` | Not implemented | NEW |
| POST /handover/draft/{id}/merge | `merge_draft_items()` | Not implemented | NEW |
| POST /handover/draft/{id}/accept | `accept_handover()` | `publish_handover()` | Rename + adjust |
| POST /handover/draft/{id}/sign | `countersign_handover()` | `countersign_handover()` | EXISTS |
| POST /handover/draft/{id}/export | `export_handover()` | Not implemented | NEW |
| POST /handover/entry | `create_handover_entry()` | `add_manual_handover_item()` | Refactor |
| POST /handover/entry/{id}/confirm | `confirm_entry()` | `decide_handover_proposal()` | Similar |
| POST /handover/entry/{id}/dismiss | `dismiss_entry()` | `decide_handover_proposal()` | Similar |
| POST /handover/entry/{id}/flag-classification | `flag_classification()` | Not implemented | NEW |

### Missing Functions Count: 6

---

## Part 6: Generation Pipeline Gap Analysis

**18_handover_buckets defines 7-stage pipeline:**

| Stage | Name | IMPL_03 Coverage | Gap |
|-------|------|------------------|-----|
| 1 | Fetch candidate entries | `auto_populate_handover_proposals()` | Needs domain filtering |
| 2 | Domain grouping | Not implemented | NEW - group by domain code |
| 3 | Duplicate detection | Not implemented | NEW - cross-entry matching |
| 4 | Summarisation | Not implemented | NEW - narrative compression |
| 5 | Risk ranking | `infer_priority()` helper | Needs risk tag hierarchy |
| 6 | Command synthesis | Not implemented | NEW - auto-generate CMD buckets |
| 7 | Draft assembly | Partial | Needs section structure |

**Python Job Requirement**: 18_handover_buckets specifies Python jobs for pipeline. Currently only Supabase functions exist.

---

## Part 7: Risk Tag Hierarchy Implementation

### Required Risk Tags (Ordered by severity)

```sql
CREATE TYPE risk_tag AS ENUM (
    'Safety_Critical',        -- Immediate physical danger
    'Compliance_Critical',    -- Regulatory violation risk
    'Guest_Impacting',        -- Affects charter experience
    'Cost_Impacting',         -- Financial consequences
    'Operational_Debt',       -- Future work accumulation
    'Informational'           -- No risk, context only
);
```

### Ranking Function

```sql
CREATE FUNCTION get_risk_rank(tag TEXT)
RETURNS INTEGER AS $$
    SELECT CASE tag
        WHEN 'Safety_Critical' THEN 1
        WHEN 'Compliance_Critical' THEN 2
        WHEN 'Guest_Impacting' THEN 3
        WHEN 'Cost_Impacting' THEN 4
        WHEN 'Operational_Debt' THEN 5
        WHEN 'Informational' THEN 6
        ELSE 999
    END;
$$ LANGUAGE SQL IMMUTABLE;
```

---

## Part 8: Overlap Rules Implementation

### Domain Overlap Matrix (from 04_overlap_rules.md)

When an entry touches multiple domains:

| Primary | Secondary | Rule |
|---------|-----------|------|
| ENG-* | DECK-* | Show in both, Engineering owns |
| ETO-* | ENG-03 (electrical) | Show in both, ETO owns |
| INT-01 | ADM-* | Show in both, Interior owns |
| Any | CMD-* | Never direct - command auto-synthesizes |

### Multi-Owner Resolution

```sql
CREATE FUNCTION resolve_domain_ownership(
    primary_domain TEXT,
    secondary_domains TEXT[]
) RETURNS TEXT[] AS $$
DECLARE
    owners TEXT[] := ARRAY[get_domain_owner(primary_domain)];
    domain TEXT;
BEGIN
    FOREACH domain IN ARRAY COALESCE(secondary_domains, ARRAY[]::TEXT[])
    LOOP
        owners := array_append(owners, get_domain_owner(domain));
    END LOOP;
    RETURN array_distinct(owners);
END;
$$ LANGUAGE plpgsql;
```

---

## Part 9: What IS Possible with Current Schema

### Immediately Feasible (No Schema Changes)

| Capability | Current Support | Notes |
|------------|-----------------|-------|
| Add item to handover | YES | `add_to_handover` action exists |
| View handover items | YES | HandoverCard component exists |
| Auto-add recurring faults | YES | Trigger function exists |
| Acknowledge items | YES | `acknowledged_by[]` array exists |
| Basic filtering | YES | By yacht, entity type |
| Polymorphic entity linking | YES | `entity_type` + `entity_id` |

### Requires Schema Extension

| Capability | Gap | Effort |
|------------|-----|--------|
| Domain code taxonomy | Missing columns | MEDIUM |
| Presentation buckets | Missing enum | LOW |
| Risk tag hierarchy | Missing columns | LOW |
| Source event linking | Missing columns | LOW |
| Draft state machine | Missing tables | MEDIUM |
| Dual sign-off | Missing tables | MEDIUM |
| Edit audit trail | Missing table | LOW |
| Export tracking | Missing table | LOW |
| Command synthesis | Missing pipeline | HIGH |

### Requires New Python Jobs

| Capability | Complexity | Dependencies |
|------------|------------|--------------|
| Draft generation pipeline | HIGH | All new tables, domain mapping |
| Summarisation | MEDIUM | LLM integration, narrative compression |
| Command synthesis | HIGH | Cross-bucket analysis, risk aggregation |
| Export preparation | MEDIUM | PDF rendering, storage integration |

---

## Part 10: Implementation Roadmap for Claude B

### Phase 1: Schema Foundation
1. Create `handover_entries` table with domain taxonomy
2. Create `handover_draft_sections` table
3. Create `handover_draft_edits` table
4. Create `handover_exports` table
5. Modify existing `handover_drafts` to match 18_handover_buckets
6. Create domain_codes reference table with 28 codes
7. Create presentation_bucket enum

### Phase 2: State Machine
1. Implement DRAFT → IN_REVIEW → ACCEPTED → SIGNED → EXPORTED flow
2. Create `enter_review_state()` RPC
3. Create `accept_handover()` RPC (rename from publish)
4. Create `sign_handover()` RPC (rename from countersign)
5. Create state transition guards
6. Implement HTTP 409 for invalid transitions

### Phase 3: Entry Management
1. Create `create_handover_entry()` RPC with domain inference
2. Create `confirm_entry()` / `dismiss_entry()` RPCs
3. Create `flag_classification()` RPC
4. Implement `edit_draft_item()` with audit trail
5. Implement `merge_draft_items()` RPC

### Phase 4: Pipeline Jobs (Python)
1. Draft Generation Job - assemble from entries
2. Domain grouping logic
3. Duplicate detection
4. Risk ranking with tag hierarchy
5. Command synthesis (CMD-01, CMD-02, CMD-03)

### Phase 5: Export System
1. Create `export_handover()` RPC
2. PDF template rendering
3. Email dispatch logic
4. Storage path management
5. Document hash verification

---

## Part 11: Conflicts to Resolve

### Naming Conflicts

| IMPL_03 Name | 18_handover_buckets Name | Resolution |
|--------------|-------------------------|------------|
| `handover_drafts.department` | Removed - use sections | Drop column |
| `handover_accepted_items` | `handover_draft_items` | Rename |
| `handover_proposed_items` | `handover_entries` | Conceptual alignment |
| `handover_signatures` | `handover_signoffs` | Prefer simpler model |
| Status: 'published' | State: 'ACCEPTED' | Use 18's naming |
| Status: 'countersigned' | State: 'SIGNED' | Use 18's naming |

### Conceptual Conflicts

| Aspect | IMPL_03 | 18_handover_buckets | Resolution |
|--------|---------|---------------------|------------|
| Entry origin | Ledger events proposed | User creates + system infers | Hybrid: both sources |
| Department scope | Per-draft | Per-section within draft | Sections model |
| Command bucket | Not implemented | Auto-synthesized | Add synthesis |
| Confidence display | Not implemented | LOW/MEDIUM/HIGH tags | Add column |

---

## Part 12: Non-Negotiables (From 18_handover_buckets)

These MUST be enforced by schema and API:

1. **No cascade delete on handover_entries**
2. **No update on ledger references**
3. **No overwrite of narrative_text after creation**
4. **No deletion of signed drafts**
5. **No export without signoff**
6. **No endpoint may skip acceptance**
7. **No endpoint may modify signed drafts**
8. **No endpoint may create exports before signing**
9. **No endpoint may delete trace records**
10. **No auto-submission of entries** (user must confirm)
11. **No direct modification of Command bucket** (auto-synthesized)
12. **Invalid state transitions return HTTP 409**

---

## Part 13: Recommended IMPL File Structure

Replace IMPL_03 with multiple focused specs:

```
18_handover_buckets/
├── IMPL_01_domain_taxonomy.sql.md      # Domain codes, buckets, mappings
├── IMPL_02_entry_tables.sql.md         # handover_entries, sources
├── IMPL_03_draft_tables.sql.md         # drafts, sections, items, edits
├── IMPL_04_state_machine.sql.md        # State transitions, guards
├── IMPL_05_signoff_export.sql.md       # Signoffs, exports, storage
├── IMPL_06_rpc_functions.sql.md        # All RPC functions
├── IMPL_07_python_jobs.sql.md          # Job specifications
├── IMPL_08_api_endpoints.sql.md        # REST endpoint definitions
├── IMPL_09_rls_policies.sql.md         # All RLS policies
└── IMPL_10_test_cases.sql.md           # Contract test specifications
```

---

## Conclusion

The 18_handover_buckets specification is **comprehensive and production-ready**. The existing schema provides a foundation but requires significant extension. IMPL_03 should be **superseded** by a new implementation aligned to 18_handover_buckets.

**Estimated New Tables**: 4
**Estimated Modified Tables**: 2
**Estimated New RPC Functions**: 12
**Estimated Python Jobs**: 4
**Estimated API Endpoints**: 15

Claude B should treat 18_handover_buckets as the **authoritative behavioral contract** and implement accordingly.

---

## Appendix: Domain Code Quick Reference

| Code | Domain | Bucket |
|------|--------|--------|
| ENG-01 | Propulsion / Main Engines | Engineering |
| ENG-02 | Power Generation / Generators | Engineering |
| ENG-03 | Electrical Distribution / Shore Power | Engineering |
| ENG-04 | HVAC / Refrigeration / Climate | Engineering |
| ENG-05 | Plumbing / Freshwater / Blackwater | Engineering |
| ENG-06 | Fuel Systems / Bunkering | Engineering |
| ENG-07 | Hydraulics / Stabilisation | Engineering |
| ENG-08 | Fire Detection / Suppression | Engineering |
| ENG-09 | Safety Systems / Alarms / Bilge | Engineering |
| ENG-10 | General Machinery | Engineering |
| ETO-01 | Navigation / Bridge Electronics | ETO_AVIT |
| ETO-02 | IT / Networks / Cybersecurity | ETO_AVIT |
| ETO-03 | AV / Entertainment / Cinema | ETO_AVIT |
| ETO-04 | CCTV / Access Control | ETO_AVIT |
| ETO-05 | Monitoring / Alarm Integration | ETO_AVIT |
| ETO-06 | Radio / Satellite / Comms | ETO_AVIT |
| DECK-01 | Deck Machinery / Cranes / Davits | Deck |
| DECK-02 | Mooring / Anchoring | Deck |
| DECK-03 | Tenders / Water Toys / PWC | Deck |
| DECK-04 | Exterior Maintenance / Hull | Deck |
| DECK-05 | Bridge / Navigation Watchkeeping | Deck |
| DECK-06 | Safety Equipment / LSA | Deck |
| INT-01 | Guest Services / Requests / Preferences | Interior |
| INT-02 | Housekeeping / Laundry | Interior |
| INT-03 | Galley / Provisions / F&B | Interior |
| INT-04 | Stores / Inventory / Consumables | Interior |
| ADM-01 | Compliance / Certificates / Inspections | Admin_Compliance |
| ADM-02 | Crew Admin / Rotations / Training | Admin_Compliance |
| ADM-03 | Budget / Finance / Expenses | Admin_Compliance |
| ADM-04 | Procurement / Vendors | Admin_Compliance |
| ADM-05 | Port / Agent / Logistics | Admin_Compliance |
| ADM-06 | Insurance / Claims | Admin_Compliance |
| CMD-01 | Operational Risk State | Command (auto) |
| CMD-02 | Guest Experience State | Command (auto) |
| CMD-03 | Vessel Readiness State | Command (auto) |
