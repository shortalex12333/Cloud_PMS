# Handover Export System

## Architecture & Implementation Specification

**Version:** 1.0
**Date:** 2026-02-03
**Status:** Implementation-Ready

---

## Purpose

Transform user-authored handover notes into professional, hyperlinked shift handover documents with full audit trail and responsibility transfer.

The system takes **rough operational notes** and produces **polished professional documents** that:

- Summarize vessel state clearly
- Link to source materials (emails, faults, work orders, manuals)
- Track responsibility transfer via dual sign-off
- Remain readable outside Celeste

---

## Core Workflow

```
User Notes → Draft Assembly → Human Review → Dual Sign-off → Professional Export
```

**Phase 1: Note Collection**
- Users add items via `add_to_handover` action
- Items linked to entities (faults, work orders, equipment, emails)
- Stored in `handover_items` (formal handover) or `pms_handover` (quick-add)

**Phase 2: Draft Generation**
- System assembles notes into structured draft
- Groups by presentation bucket (Engineering, Deck, etc.)
- AI may summarize/merge duplicates (retaining source links)
- Creates `handover_drafts` → `handover_draft_sections` → `handover_draft_items`

**Phase 3: Human Review**
- User edits wording (preserving sources)
- Merges/reorders items as needed
- All edits tracked in `handover_draft_edits`
- User confirms content accuracy

**Phase 4: Sign-off**
- Outgoing officer accepts (ACCEPTED state)
- Incoming officer countersigns (SIGNED state)
- Both identities and timestamps recorded
- Content hash locked for tamper detection

**Phase 5: Export**
- Generate HTML/PDF with hyperlinks
- Store in Supabase Storage
- Record in `handover_exports`
- Optional email distribution

---

## Design Principles

1. **Continuity, not planning** - Handover answers "what is the vessel state now"
2. **Nothing enters silently** - Celeste suggests, humans accept
3. **Nothing leaves silently** - Removal requires explicit action
4. **Living draft until signed** - No export before sign-off
5. **Humans own the wording** - Edits allowed, sources preserved
6. **Sign-off is responsibility transfer** - Identity, timestamp, hash

---

## Document Structure

```
00_overview.md            - This document
01_data_model.md          - Database schema and relationships
02_state_machine.md       - Draft lifecycle and transitions
03_api_contracts.md       - Endpoint specifications
04_formatting_engine.md   - HTML/PDF generation
05_hyperlink_system.md    - Deep links to emails/entities
06_compatibility_bridge.md - Legacy table migration
07_security_rls.md        - Row-level security policies
08_implementation_plan.md - Step-by-step rollout
09_test_plan.md           - Acceptance criteria and tests
```

---

## Related Documents

- `/docs/architecture/18_handover_buckets/` - Bucket taxonomy and principles
- `/docs/pipeline/Who We Are.md` - Celeste philosophy and guardrails

---
