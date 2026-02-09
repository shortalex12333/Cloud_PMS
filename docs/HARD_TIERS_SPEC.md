# Hard Tiers Ranking Specification

**Version:** 1.0
**Date:** 2026-02-05
**Status:** Implemented

## Overview

Hard Tiers replaces the previous "magic math" approach (multiplicative domain weight boosts) with a deterministic, transparent ranking system. Results are sorted by discrete tiers, making ranking behavior predictable and debuggable.

## ORDER BY Hierarchy

Results are sorted by these criteria in order:

```sql
ORDER BY
    CASE WHEN exact_id_match THEN 0 ELSE 1 END ASC,      -- Tier 1
    CASE WHEN explicit_domain_match THEN 0 ELSE 1 END ASC,  -- Tier 2
    recency_ts DESC NULLS LAST,                          -- Tier 3
    fused_score DESC                                     -- Tier 4
```

### Tier 1: Exact ID Match

If the query matches an `ident_norm` value (normalized identifier), those results sort first.

**ident_norm per domain:**
| Domain | Source Field | Example |
|--------|--------------|---------|
| work_order | wo_number | WO-12345 |
| fault | fault_code | FLT-001 |
| equipment | code | EQ-ABC-123 |
| part | part_number | PN-54321 |
| inventory | part_number | PN-54321 |
| receiving | vendor_reference | VR-2026-001 |
| purchase_order | po_number | PO-98765 |
| certificate | certificate_number | CERT-001 |
| shopping_item | part_number | PN-54321 |
| warranty_claim | claim_number | WC-2026-001 |

**Normalization:** `UPPER(REGEXP_REPLACE(value, '[\s\-_]+', '', 'g'))`

### Tier 2: Explicit Domain Match

If the user specifies a domain token (e.g., "WO:" prefix), results from that domain sort next.

**Domain token parsing (in orchestrator):**
- `WO:`, `WorkOrder:` → work_order
- `Part:`, `PN:` → part
- `Equipment:`, `EQ:` → equipment
- `Email:` → email
- `Note:` → note, work_order_note
- `Doc:`, `Document:` → document
- `Fault:` → fault
- `Only` suffix → filter-only mode (exclude other domains)

### Tier 3: Recency

More recent results sort higher within their tier.

**recency_ts per domain:**
| Domain | Source Field |
|--------|--------------|
| work_order | updated_at |
| work_order_note | created_at |
| note | created_at |
| fault | detected_at (fallback: created_at) |
| equipment | updated_at |
| part | updated_at |
| inventory | updated_at |
| receiving | received_date |
| purchase_order | ordered_at |
| supplier | updated_at |
| certificate | updated_at |
| email | received_at |
| document | updated_at |
| handover_item | created_at |
| shopping_item | updated_at |
| warranty_claim | created_at |

### Tier 4: Relevance Score

Finally, results are sorted by `fused_score` (trigram + vector combined score).

## Quality Gates

Before tier sorting, results must pass quality gates:

```sql
WHERE trigram_score >= 0.30 OR vector_score >= 0.75
```

This filters out low-relevance noise before applying tier logic.

## Display Tiers (UI)

For UI presentation, results are grouped into 4 display tiers:

| Tier | Criteria | Badge |
|------|----------|-------|
| 1 | exact_id_match = TRUE | "Exact Match" |
| 2 | explicit_domain_match = TRUE | Domain name |
| 3 | recency_ts within 30 days | "Recent" |
| 4 | Everything else | - |

## RPC Implementation

The `hyper_search_multi` RPC returns these fields:

```sql
-- New return columns
exact_id_match BOOLEAN,
explicit_domain_match BOOLEAN,
recency_ts TIMESTAMPTZ,
tier INT
```

**New parameters:**
- `p_explicit_types text[]` - Domain types from parsed tokens
- `p_filter_only boolean` - TRUE if "Only" suffix present
- `p_id_query text` - Normalized query for ident_norm matching

## Stage-1 Merge

The Python `stage1_merge` module provides:

1. **Email thread collapse** - Keep highest-scoring email per thread_id
2. **Tier annotations** - Add `tier` and `tier_reason` fields
3. **Sort verification** - Re-apply Hard Tiers sort after collapse

**Deprecated features (removed):**
- Domain weight multipliers (1.25x, 1.50x, etc.)
- Recency decay formula (0.9^days)
- Intent detection for "diagnostic" queries

## Database Schema

```sql
-- Added to search_index
ALTER TABLE search_index ADD COLUMN recency_ts TIMESTAMPTZ;
ALTER TABLE search_index ADD COLUMN ident_norm TEXT;

-- Indexes
CREATE INDEX ix_si_recency ON search_index(recency_ts DESC NULLS LAST);
CREATE INDEX ix_si_ident_norm ON search_index(ident_norm) WHERE ident_norm IS NOT NULL;
```

## Learned Preferences (Future)

The `search_term_domain_stats` table tracks user click patterns for personalized ranking:

```sql
CREATE TABLE search_term_domain_stats (
    id UUID PRIMARY KEY,
    term_hash TEXT NOT NULL,          -- MD5 of normalized search term
    domain TEXT NOT NULL,             -- object_type
    user_id UUID,                     -- NULL = org-level
    org_id UUID NOT NULL,
    click_count INT DEFAULT 0,
    last_click_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Priority:** User-level stats > Org-level stats > Default

## Migration Path

1. Add `recency_ts` and `ident_norm` columns
2. Run backfill script for existing rows
3. Update RPC with Hard Tiers ORDER BY
4. Update stage1_merge to remove magic boosts
5. Deploy and verify with canary queries

## Canary Queries

Test these queries to verify Hard Tiers:

| Query | Expected Tier 1 |
|-------|-----------------|
| `WO-12345` | Work order with that number |
| `PN-54321` | Part or inventory with that number |
| `WO: pump` | Work orders about pumps |
| `Part Only: seal` | Only parts matching "seal" |
| `previous issues` | Recent notes/WOs first |
