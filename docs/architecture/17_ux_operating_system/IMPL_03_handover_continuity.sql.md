# IMPLEMENTATION SPEC: Handover Continuity System

> **Document**: `IMPL_03_handover_continuity.sql.md`
> **UX Source**: `06-handover-continuity.md`
> **Priority**: P0 (Foundation)
> **Target DB**: Tenant Database

---

## Overview

This specification implements **Handover as Continuity** defined in `06-handover-continuity.md`. Handover answers ONE question: **"What state is the vessel in right now, and why?"**

Key UX requirements:
- Handover is a **document**, not a workspace
- Auto-assembled from real actions (ledger events)
- Explicitly editable by humans
- Celeste **proposes** additions, users **accept** them
- Export to PDF, sign-off workflow required
- NEVER turns into planning or task management

---

## PART 1: NEW TABLES

### 1.1 `handover_drafts` - Living handover documents

```sql
-- ============================================================================
-- TABLE: handover_drafts
-- Purpose: Auto-assembled handover document that evolves through the shift
-- UX Requirement: "a living draft, auto-assembled from real actions"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    -- Period definition
    shift_date DATE NOT NULL DEFAULT CURRENT_DATE,
    shift_period TEXT NOT NULL,
    -- Values: 'day', 'night', '0800-2000', '2000-0800', 'watch_1', 'watch_2', 'watch_3'

    -- Department/Role scope
    department TEXT NOT NULL,
    -- Values: 'engineering', 'deck', 'interior', 'bridge', 'galley'

    owner_user_id UUID NOT NULL REFERENCES auth.users(id),
    owner_name TEXT NOT NULL,
    owner_role TEXT NOT NULL,

    -- Document state
    status TEXT NOT NULL DEFAULT 'draft',
    -- Values: 'draft', 'pending_review', 'published', 'countersigned', 'archived'

    -- Content assembly
    auto_items_count INTEGER DEFAULT 0,
    -- Count of items proposed by Celeste

    manual_items_count INTEGER DEFAULT 0,
    -- Count of items added manually by user

    rejected_items_count INTEGER DEFAULT 0,
    -- Count of Celeste proposals rejected by user

    -- Summary fields (edited by user)
    executive_summary TEXT,
    -- Optional high-level summary written by user

    outstanding_issues TEXT,
    -- Free text for critical ongoing issues

    -- Sign-off workflow
    signed_by_id UUID REFERENCES auth.users(id),
    signed_by_name TEXT,
    signed_at TIMESTAMPTZ,
    signature_hash TEXT,
    -- SHA256 of snapshot at signing time

    countersigned_by_id UUID REFERENCES auth.users(id),
    countersigned_by_name TEXT,
    countersigned_at TIMESTAMPTZ,

    -- Immutable snapshot (created at publish)
    published_snapshot JSONB,
    -- Complete state at time of publication

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,

    -- Constraints
    UNIQUE(yacht_id, shift_date, shift_period, department),
    CONSTRAINT valid_status CHECK (status IN (
        'draft', 'pending_review', 'published', 'countersigned', 'archived'
    )),
    CONSTRAINT valid_department CHECK (department IN (
        'engineering', 'deck', 'interior', 'bridge', 'galley', 'all'
    ))
);

-- Indexes
CREATE INDEX idx_handover_drafts_yacht_date ON public.handover_drafts(yacht_id, shift_date DESC);
CREATE INDEX idx_handover_drafts_owner ON public.handover_drafts(owner_user_id, status);
CREATE INDEX idx_handover_drafts_status ON public.handover_drafts(yacht_id, status);
CREATE INDEX idx_handover_drafts_pending ON public.handover_drafts(yacht_id, department, status)
    WHERE status = 'pending_review';

-- RLS Policy
ALTER TABLE public.handover_drafts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "handover_drafts_yacht_isolation" ON public.handover_drafts
    FOR ALL USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

### 1.2 `handover_proposed_items` - Celeste-proposed items

```sql
-- ============================================================================
-- TABLE: handover_proposed_items
-- Purpose: Items proposed by Celeste for inclusion in handover
-- UX Requirement: "Celeste may PROPOSE additions, users must ACCEPT them"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_proposed_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    handover_draft_id UUID NOT NULL REFERENCES public.handover_drafts(id) ON DELETE CASCADE,

    -- Source tracking (what triggered the proposal)
    source_type TEXT NOT NULL,
    -- Values: 'ledger_event', 'fault', 'work_order', 'inventory_alert',
    --         'equipment_status', 'search_action', 'recurring_pattern'
    source_id UUID,
    source_entity_type TEXT,
    source_display_name TEXT,

    -- The ledger event that triggered this proposal
    ledger_event_id UUID REFERENCES public.ledger_events(id),

    -- Proposal content
    proposed_title TEXT NOT NULL,
    proposed_summary TEXT NOT NULL,
    proposed_next_action TEXT,
    -- What should the next person do?

    proposed_risk_category TEXT,
    -- Values: 'safety_risk', 'equipment_damage', 'operational_delay',
    --         'regulatory_issue', 'guest_impact', 'other'

    proposed_priority INTEGER DEFAULT 3,
    -- 1=urgent, 2=high, 3=normal

    -- Decision tracking
    decision TEXT NOT NULL DEFAULT 'pending',
    -- Values: 'pending', 'accepted', 'rejected', 'deferred'

    decision_by_id UUID REFERENCES auth.users(id),
    decision_by_name TEXT,
    decision_at TIMESTAMPTZ,
    decision_reason TEXT,
    -- Optional: why rejected/deferred

    -- If accepted, link to the actual handover item
    accepted_item_id UUID,

    -- Timestamps
    proposed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_decision CHECK (decision IN ('pending', 'accepted', 'rejected', 'deferred')),
    CONSTRAINT valid_risk CHECK (proposed_risk_category IN (
        'safety_risk', 'equipment_damage', 'operational_delay',
        'regulatory_issue', 'guest_impact', 'other', NULL
    ))
);

-- Indexes
CREATE INDEX idx_proposed_items_draft ON public.handover_proposed_items(handover_draft_id, decision);
CREATE INDEX idx_proposed_items_pending ON public.handover_proposed_items(handover_draft_id)
    WHERE decision = 'pending';
CREATE INDEX idx_proposed_items_source ON public.handover_proposed_items(source_type, source_id);

-- RLS Policy
ALTER TABLE public.handover_proposed_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "proposed_items_yacht_isolation" ON public.handover_proposed_items
    FOR ALL USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

### 1.3 `handover_accepted_items` - Final accepted items

```sql
-- ============================================================================
-- TABLE: handover_accepted_items
-- Purpose: Items that will appear in the published handover document
-- UX Requirement: "the handover is curated"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_accepted_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    handover_draft_id UUID NOT NULL REFERENCES public.handover_drafts(id) ON DELETE CASCADE,

    -- Origin tracking
    origin_type TEXT NOT NULL,
    -- Values: 'proposed' (from Celeste), 'manual' (user added directly)
    proposed_item_id UUID REFERENCES public.handover_proposed_items(id),

    -- Source reference (what this item is about)
    source_type TEXT,
    source_id UUID,
    source_entity_name TEXT,

    -- Content (editable by user)
    title TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    -- This is the actual handover narrative

    next_action TEXT,
    -- What should the incoming person do?

    -- Classification
    risk_category TEXT,
    priority INTEGER DEFAULT 3,
    -- 1=urgent, 2=high, 3=normal

    -- Attribution
    added_by_id UUID NOT NULL REFERENCES auth.users(id),
    added_by_name TEXT NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Edit tracking (preserve original attribution even after edits)
    last_edited_by_id UUID REFERENCES auth.users(id),
    last_edited_by_name TEXT,
    last_edited_at TIMESTAMPTZ,
    edit_count INTEGER DEFAULT 0,

    -- Display order
    display_order INTEGER DEFAULT 100,

    -- Status within handover
    item_status TEXT DEFAULT 'active',
    -- Values: 'active', 'acknowledged', 'removed'

    acknowledged_by_id UUID REFERENCES auth.users(id),
    acknowledged_by_name TEXT,
    acknowledged_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_item_status CHECK (item_status IN ('active', 'acknowledged', 'removed'))
);

-- Indexes
CREATE INDEX idx_accepted_items_draft ON public.handover_accepted_items(handover_draft_id, item_status);
CREATE INDEX idx_accepted_items_priority ON public.handover_accepted_items(handover_draft_id, priority, display_order);
CREATE INDEX idx_accepted_items_source ON public.handover_accepted_items(source_type, source_id);

-- RLS Policy
ALTER TABLE public.handover_accepted_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "accepted_items_yacht_isolation" ON public.handover_accepted_items
    FOR ALL USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

### 1.4 `handover_signatures` - Sign-off audit trail

```sql
-- ============================================================================
-- TABLE: handover_signatures
-- Purpose: Immutable record of handover sign-offs
-- UX Requirement: "accountability for accepting handover"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.handover_signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    handover_draft_id UUID NOT NULL REFERENCES public.handover_drafts(id),

    -- Signature type
    signature_type TEXT NOT NULL,
    -- Values: 'outgoing', 'incoming', 'supervisor'

    -- Signer details (denormalized for permanence)
    signer_id UUID NOT NULL REFERENCES auth.users(id),
    signer_name TEXT NOT NULL,
    signer_role TEXT NOT NULL,

    -- Signature content
    signature_hash TEXT NOT NULL,
    -- SHA256 of (handover_snapshot + signer_id + timestamp)

    snapshot_hash TEXT NOT NULL,
    -- Hash of the handover content at signing time

    -- Legal acknowledgment
    acknowledgment_text TEXT NOT NULL DEFAULT 'I acknowledge receipt and understanding of this handover.',
    custom_notes TEXT,
    -- Optional notes from signer

    -- Device/location metadata
    signed_from_ip INET,
    signed_from_device TEXT,

    -- Timestamp (immutable)
    signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_signature_type CHECK (signature_type IN ('outgoing', 'incoming', 'supervisor'))
);

-- Indexes
CREATE INDEX idx_handover_signatures_draft ON public.handover_signatures(handover_draft_id, signature_type);
CREATE INDEX idx_handover_signatures_signer ON public.handover_signatures(signer_id, signed_at DESC);

-- RLS Policy (read only for users, insert via RPC)
ALTER TABLE public.handover_signatures ENABLE ROW LEVEL SECURITY;

CREATE POLICY "signatures_yacht_read" ON public.handover_signatures
    FOR SELECT USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

---

## PART 2: NEW COLUMNS ON EXISTING TABLES

### 2.1 Existing `pms_handover` table enhancements

```sql
-- ============================================================================
-- ALTER TABLE: pms_handover (existing table)
-- Migrate to new handover_drafts structure
-- ============================================================================

-- Add reference to new draft system
ALTER TABLE public.pms_handover
ADD COLUMN IF NOT EXISTS draft_id UUID REFERENCES public.handover_drafts(id);

-- Add department scope
ALTER TABLE public.pms_handover
ADD COLUMN IF NOT EXISTS department TEXT DEFAULT 'all';

-- Add countersign fields
ALTER TABLE public.pms_handover
ADD COLUMN IF NOT EXISTS countersigned_by UUID REFERENCES auth.users(id);

ALTER TABLE public.pms_handover
ADD COLUMN IF NOT EXISTS countersigned_at TIMESTAMPTZ;

-- Add legal acknowledgment flag
ALTER TABLE public.pms_handover
ADD COLUMN IF NOT EXISTS legal_notice_shown BOOLEAN DEFAULT FALSE;
```

### 2.2 `pms_handover_items` - Add decision tracking

```sql
-- ============================================================================
-- ALTER TABLE: pms_handover_items (existing table)
-- Add fields for proposal/acceptance workflow
-- ============================================================================

-- Track whether item was proposed by Celeste or manual
ALTER TABLE public.pms_handover_items
ADD COLUMN IF NOT EXISTS origin_type TEXT DEFAULT 'manual';

-- Link to proposed item if applicable
ALTER TABLE public.pms_handover_items
ADD COLUMN IF NOT EXISTS proposed_item_id UUID;

-- Edit tracking
ALTER TABLE public.pms_handover_items
ADD COLUMN IF NOT EXISTS edit_count INTEGER DEFAULT 0;

ALTER TABLE public.pms_handover_items
ADD COLUMN IF NOT EXISTS last_edited_by UUID REFERENCES auth.users(id);

ALTER TABLE public.pms_handover_items
ADD COLUMN IF NOT EXISTS last_edited_at TIMESTAMPTZ;
```

---

## PART 3: RPC FUNCTIONS

### 3.1 `get_or_create_handover_draft()` - Initialize handover

```sql
-- ============================================================================
-- FUNCTION: get_or_create_handover_draft
-- Purpose: Get existing draft or create new one for current shift
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_or_create_handover_draft(
    p_yacht_id UUID,
    p_department TEXT,
    p_shift_period TEXT DEFAULT 'day'
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_draft_id UUID;
    v_user_id UUID;
    v_user_name TEXT;
    v_user_role TEXT;
BEGIN
    v_user_id := auth.uid();

    -- Get user info
    SELECT
        COALESCE(up.name, up.email),
        COALESCE(ur.role, 'member')
    INTO v_user_name, v_user_role
    FROM user_profiles up
    LEFT JOIN user_roles ur ON ur.user_id = up.id AND ur.is_active = TRUE
    WHERE up.id = v_user_id;

    -- Try to find existing draft for today
    SELECT id INTO v_draft_id
    FROM handover_drafts
    WHERE yacht_id = p_yacht_id
    AND shift_date = CURRENT_DATE
    AND shift_period = p_shift_period
    AND department = p_department
    AND status IN ('draft', 'pending_review');

    -- Create new draft if none exists
    IF v_draft_id IS NULL THEN
        INSERT INTO handover_drafts (
            yacht_id,
            shift_date,
            shift_period,
            department,
            owner_user_id,
            owner_name,
            owner_role,
            status
        ) VALUES (
            p_yacht_id,
            CURRENT_DATE,
            p_shift_period,
            p_department,
            v_user_id,
            v_user_name,
            v_user_role,
            'draft'
        )
        RETURNING id INTO v_draft_id;

        -- Auto-populate with recent mutations from ledger
        PERFORM auto_populate_handover_proposals(v_draft_id);
    END IF;

    RETURN v_draft_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_or_create_handover_draft TO authenticated;
```

### 3.2 `auto_populate_handover_proposals()` - Celeste proposes items

```sql
-- ============================================================================
-- FUNCTION: auto_populate_handover_proposals
-- Purpose: Auto-generate handover proposals from ledger events
-- UX Requirement: "Celeste may propose additions"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.auto_populate_handover_proposals(
    p_draft_id UUID
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_draft RECORD;
    v_count INTEGER := 0;
    v_event RECORD;
BEGIN
    -- Get draft details
    SELECT * INTO v_draft FROM handover_drafts WHERE id = p_draft_id;

    -- Find relevant mutation events from today that aren't already proposed
    FOR v_event IN
        SELECT
            le.id as event_id,
            le.entity_type,
            le.entity_id,
            le.entity_display_name,
            le.event_verb,
            le.domain,
            le.context_data,
            le.user_name
        FROM ledger_events le
        WHERE le.yacht_id = v_draft.yacht_id
        AND le.event_date = v_draft.shift_date
        AND le.event_class = 'mutation'
        -- Filter by department relevance
        AND (
            v_draft.department = 'all'
            OR (v_draft.department = 'engineering' AND le.domain IN ('Equipment', 'Faults', 'Work Orders'))
            OR (v_draft.department = 'deck' AND le.domain IN ('Equipment', 'Work Orders'))
            OR (v_draft.department = 'interior' AND le.domain IN ('Inventory', 'Procurement'))
        )
        -- Not already proposed
        AND NOT EXISTS (
            SELECT 1 FROM handover_proposed_items hpi
            WHERE hpi.ledger_event_id = le.id
            AND hpi.handover_draft_id = p_draft_id
        )
        ORDER BY
            -- Prioritize by domain importance
            CASE le.domain
                WHEN 'Faults' THEN 1
                WHEN 'Work Orders' THEN 2
                WHEN 'Equipment' THEN 3
                ELSE 4
            END,
            le.event_timestamp DESC
        LIMIT 20  -- Don't overwhelm with proposals
    LOOP
        INSERT INTO handover_proposed_items (
            yacht_id,
            handover_draft_id,
            source_type,
            source_id,
            source_entity_type,
            source_display_name,
            ledger_event_id,
            proposed_title,
            proposed_summary,
            proposed_next_action,
            proposed_risk_category,
            proposed_priority
        ) VALUES (
            v_draft.yacht_id,
            p_draft_id,
            'ledger_event',
            v_event.entity_id,
            v_event.entity_type,
            v_event.entity_display_name,
            v_event.event_id,
            v_event.entity_display_name,
            v_event.event_verb || ' by ' || v_event.user_name,
            generate_suggested_next_action(v_event.entity_type, v_event.event_verb, v_event.context_data),
            infer_risk_category(v_event.entity_type, v_event.domain, v_event.context_data),
            infer_priority(v_event.entity_type, v_event.domain, v_event.context_data)
        );

        v_count := v_count + 1;
    END LOOP;

    -- Update draft counts
    UPDATE handover_drafts SET
        auto_items_count = v_count,
        updated_at = NOW()
    WHERE id = p_draft_id;

    RETURN v_count;
END;
$$;

-- Helper function: Generate suggested next action
CREATE OR REPLACE FUNCTION public.generate_suggested_next_action(
    p_entity_type TEXT,
    p_event_verb TEXT,
    p_context JSONB
)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    CASE p_entity_type
        WHEN 'work_order' THEN
            CASE p_event_verb
                WHEN 'Created' THEN RETURN 'Review and assign if not already done';
                WHEN 'Started' THEN RETURN 'Monitor progress';
                WHEN 'Blocked' THEN RETURN 'Investigate blocker and resolve';
                WHEN 'Closed' THEN RETURN 'Verify completion quality';
                ELSE RETURN 'Review status';
            END CASE;
        WHEN 'fault' THEN
            CASE p_event_verb
                WHEN 'Created' THEN RETURN 'Assess severity and create work order if needed';
                WHEN 'Acknowledged' THEN RETURN 'Continue monitoring';
                WHEN 'Resolved' THEN RETURN 'Confirm resolution holds';
                ELSE RETURN 'Monitor';
            END CASE;
        WHEN 'equipment' THEN
            RETURN 'Check equipment status at start of shift';
        ELSE
            RETURN 'Review and follow up as needed';
    END CASE;
END;
$$;

-- Helper function: Infer risk category
CREATE OR REPLACE FUNCTION public.infer_risk_category(
    p_entity_type TEXT,
    p_domain TEXT,
    p_context JSONB
)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    -- Safety-related
    IF p_context->>'severity' = 'critical' OR
       p_context->>'status' = 'down' THEN
        RETURN 'safety_risk';
    END IF;

    -- Equipment damage risk
    IF p_domain = 'Equipment' AND p_context->>'status' IN ('maintenance', 'down') THEN
        RETURN 'equipment_damage';
    END IF;

    -- Operational delay
    IF p_domain = 'Work Orders' AND p_context->>'status' = 'blocked' THEN
        RETURN 'operational_delay';
    END IF;

    -- Default
    RETURN 'other';
END;
$$;

-- Helper function: Infer priority
CREATE OR REPLACE FUNCTION public.infer_priority(
    p_entity_type TEXT,
    p_domain TEXT,
    p_context JSONB
)
RETURNS INTEGER
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    -- Urgent (1)
    IF p_context->>'severity' = 'critical' OR p_context->>'priority' = 'critical' THEN
        RETURN 1;
    END IF;

    -- High (2)
    IF p_context->>'severity' = 'high' OR p_context->>'priority' = 'high' THEN
        RETURN 2;
    END IF;

    -- Normal (3)
    RETURN 3;
END;
$$;
```

### 3.3 `decide_handover_proposal()` - Accept/reject proposals

```sql
-- ============================================================================
-- FUNCTION: decide_handover_proposal
-- Purpose: Accept or reject a Celeste-proposed handover item
-- UX Requirement: "Users must accept proposals"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.decide_handover_proposal(
    p_proposed_item_id UUID,
    p_decision TEXT,              -- 'accepted', 'rejected', 'deferred'
    p_reason TEXT DEFAULT NULL,
    p_edited_title TEXT DEFAULT NULL,
    p_edited_summary TEXT DEFAULT NULL,
    p_edited_next_action TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_proposal RECORD;
    v_user_id UUID;
    v_user_name TEXT;
    v_accepted_item_id UUID;
BEGIN
    v_user_id := auth.uid();

    -- Get user name
    SELECT COALESCE(name, email) INTO v_user_name
    FROM user_profiles WHERE id = v_user_id;

    -- Get proposal
    SELECT * INTO v_proposal
    FROM handover_proposed_items WHERE id = p_proposed_item_id;

    IF v_proposal IS NULL THEN
        RAISE EXCEPTION 'Proposal not found';
    END IF;

    -- Update proposal decision
    UPDATE handover_proposed_items SET
        decision = p_decision,
        decision_by_id = v_user_id,
        decision_by_name = v_user_name,
        decision_at = NOW(),
        decision_reason = p_reason
    WHERE id = p_proposed_item_id;

    -- If accepted, create the actual handover item
    IF p_decision = 'accepted' THEN
        INSERT INTO handover_accepted_items (
            yacht_id,
            handover_draft_id,
            origin_type,
            proposed_item_id,
            source_type,
            source_id,
            source_entity_name,
            title,
            summary_text,
            next_action,
            risk_category,
            priority,
            added_by_id,
            added_by_name
        ) VALUES (
            v_proposal.yacht_id,
            v_proposal.handover_draft_id,
            'proposed',
            p_proposed_item_id,
            v_proposal.source_type,
            v_proposal.source_id,
            v_proposal.source_display_name,
            COALESCE(p_edited_title, v_proposal.proposed_title),
            COALESCE(p_edited_summary, v_proposal.proposed_summary),
            COALESCE(p_edited_next_action, v_proposal.proposed_next_action),
            v_proposal.proposed_risk_category,
            v_proposal.proposed_priority,
            v_user_id,
            v_user_name
        )
        RETURNING id INTO v_accepted_item_id;

        -- Link back to proposal
        UPDATE handover_proposed_items SET
            accepted_item_id = v_accepted_item_id
        WHERE id = p_proposed_item_id;

        -- Update draft counts
        UPDATE handover_drafts SET
            auto_items_count = auto_items_count + 1,
            updated_at = NOW()
        WHERE id = v_proposal.handover_draft_id;
    ELSIF p_decision = 'rejected' THEN
        -- Update rejected count
        UPDATE handover_drafts SET
            rejected_items_count = rejected_items_count + 1,
            updated_at = NOW()
        WHERE id = v_proposal.handover_draft_id;
    END IF;

    RETURN COALESCE(v_accepted_item_id, p_proposed_item_id);
END;
$$;

GRANT EXECUTE ON FUNCTION public.decide_handover_proposal TO authenticated;
```

### 3.4 `add_manual_handover_item()` - User adds directly

```sql
-- ============================================================================
-- FUNCTION: add_manual_handover_item
-- Purpose: Allow user to add item directly to handover
-- UX Requirement: "explicit user additions"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.add_manual_handover_item(
    p_draft_id UUID,
    p_title TEXT,
    p_summary TEXT,
    p_next_action TEXT DEFAULT NULL,
    p_risk_category TEXT DEFAULT 'other',
    p_priority INTEGER DEFAULT 3,
    p_source_type TEXT DEFAULT NULL,
    p_source_id UUID DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_draft RECORD;
    v_user_id UUID;
    v_user_name TEXT;
    v_item_id UUID;
BEGIN
    v_user_id := auth.uid();

    -- Get draft and validate access
    SELECT * INTO v_draft FROM handover_drafts WHERE id = p_draft_id;

    IF v_draft IS NULL THEN
        RAISE EXCEPTION 'Handover draft not found';
    END IF;

    -- Get user name
    SELECT COALESCE(name, email) INTO v_user_name
    FROM user_profiles WHERE id = v_user_id;

    -- Insert the item
    INSERT INTO handover_accepted_items (
        yacht_id,
        handover_draft_id,
        origin_type,
        source_type,
        source_id,
        title,
        summary_text,
        next_action,
        risk_category,
        priority,
        added_by_id,
        added_by_name
    ) VALUES (
        v_draft.yacht_id,
        p_draft_id,
        'manual',
        p_source_type,
        p_source_id,
        p_title,
        p_summary,
        p_next_action,
        p_risk_category,
        p_priority,
        v_user_id,
        v_user_name
    )
    RETURNING id INTO v_item_id;

    -- Update draft counts
    UPDATE handover_drafts SET
        manual_items_count = manual_items_count + 1,
        updated_at = NOW()
    WHERE id = p_draft_id;

    RETURN v_item_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.add_manual_handover_item TO authenticated;
```

### 3.5 `publish_handover()` - Finalize and lock

```sql
-- ============================================================================
-- FUNCTION: publish_handover
-- Purpose: Publish handover, create immutable snapshot, require sign-off
-- UX Requirement: "make security measures so crew unable to pass without signing"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.publish_handover(
    p_draft_id UUID,
    p_acknowledgment_text TEXT DEFAULT 'I confirm this handover is accurate and complete to the best of my knowledge.'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_draft RECORD;
    v_user_id UUID;
    v_user_name TEXT;
    v_user_role TEXT;
    v_snapshot JSONB;
    v_snapshot_hash TEXT;
    v_signature_hash TEXT;
BEGIN
    v_user_id := auth.uid();

    -- Get draft
    SELECT * INTO v_draft FROM handover_drafts WHERE id = p_draft_id;

    IF v_draft IS NULL THEN
        RAISE EXCEPTION 'Handover draft not found';
    END IF;

    IF v_draft.status != 'draft' AND v_draft.status != 'pending_review' THEN
        RAISE EXCEPTION 'Handover already published or archived';
    END IF;

    -- Get user info
    SELECT
        COALESCE(up.name, up.email),
        COALESCE(ur.role, 'member')
    INTO v_user_name, v_user_role
    FROM user_profiles up
    LEFT JOIN user_roles ur ON ur.user_id = up.id AND ur.is_active = TRUE
    WHERE up.id = v_user_id;

    -- Build immutable snapshot
    v_snapshot := jsonb_build_object(
        'draft_id', v_draft.id,
        'yacht_id', v_draft.yacht_id,
        'shift_date', v_draft.shift_date,
        'shift_period', v_draft.shift_period,
        'department', v_draft.department,
        'owner', jsonb_build_object(
            'id', v_draft.owner_user_id,
            'name', v_draft.owner_name,
            'role', v_draft.owner_role
        ),
        'executive_summary', v_draft.executive_summary,
        'outstanding_issues', v_draft.outstanding_issues,
        'items', (
            SELECT jsonb_agg(jsonb_build_object(
                'id', hai.id,
                'title', hai.title,
                'summary', hai.summary_text,
                'next_action', hai.next_action,
                'risk_category', hai.risk_category,
                'priority', hai.priority,
                'origin', hai.origin_type,
                'added_by', hai.added_by_name
            ) ORDER BY hai.priority, hai.display_order)
            FROM handover_accepted_items hai
            WHERE hai.handover_draft_id = p_draft_id
            AND hai.item_status = 'active'
        ),
        'statistics', jsonb_build_object(
            'auto_items', v_draft.auto_items_count,
            'manual_items', v_draft.manual_items_count,
            'rejected_proposals', v_draft.rejected_items_count
        ),
        'published_at', NOW()
    );

    -- Generate snapshot hash
    v_snapshot_hash := encode(sha256(v_snapshot::TEXT::bytea), 'hex');

    -- Generate signature hash
    v_signature_hash := encode(sha256(
        (v_snapshot_hash || v_user_id::TEXT || NOW()::TEXT)::bytea
    ), 'hex');

    -- Update draft to published
    UPDATE handover_drafts SET
        status = 'published',
        published_snapshot = v_snapshot,
        signed_by_id = v_user_id,
        signed_by_name = v_user_name,
        signed_at = NOW(),
        signature_hash = v_signature_hash,
        published_at = NOW(),
        updated_at = NOW()
    WHERE id = p_draft_id;

    -- Record signature
    INSERT INTO handover_signatures (
        yacht_id,
        handover_draft_id,
        signature_type,
        signer_id,
        signer_name,
        signer_role,
        signature_hash,
        snapshot_hash,
        acknowledgment_text
    ) VALUES (
        v_draft.yacht_id,
        p_draft_id,
        'outgoing',
        v_user_id,
        v_user_name,
        v_user_role,
        v_signature_hash,
        v_snapshot_hash,
        p_acknowledgment_text
    );

    -- Record to ledger
    PERFORM record_ledger_event(
        p_yacht_id := v_draft.yacht_id,
        p_event_class := 'mutation',
        p_event_verb := 'Signed',
        p_entity_type := 'handover',
        p_entity_id := p_draft_id,
        p_entity_display_name := v_draft.department || ' Handover — ' || v_draft.shift_date::TEXT,
        p_domain := 'Handover',
        p_context_data := jsonb_build_object(
            'signature_hash', v_signature_hash,
            'items_count', COALESCE(jsonb_array_length(v_snapshot->'items'), 0)
        )
    );

    RETURN jsonb_build_object(
        'success', TRUE,
        'draft_id', p_draft_id,
        'signature_hash', v_signature_hash,
        'published_at', NOW(),
        'message', 'Handover published. Awaiting incoming crew countersign.'
    );
END;
$$;

GRANT EXECUTE ON FUNCTION public.publish_handover TO authenticated;
```

### 3.6 `countersign_handover()` - Incoming crew acceptance

```sql
-- ============================================================================
-- FUNCTION: countersign_handover
-- Purpose: Incoming crew acknowledges receipt of handover
-- UX Requirement: "countersign with 'accepted'"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.countersign_handover(
    p_draft_id UUID,
    p_acknowledgment_text TEXT DEFAULT 'I acknowledge receipt and understanding of this handover. Celeste assists but I accept responsibility for verification.'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_draft RECORD;
    v_user_id UUID;
    v_user_name TEXT;
    v_user_role TEXT;
    v_signature_hash TEXT;
BEGIN
    v_user_id := auth.uid();

    -- Get draft
    SELECT * INTO v_draft FROM handover_drafts WHERE id = p_draft_id;

    IF v_draft IS NULL THEN
        RAISE EXCEPTION 'Handover not found';
    END IF;

    IF v_draft.status != 'published' THEN
        RAISE EXCEPTION 'Handover must be published before countersigning';
    END IF;

    IF v_draft.signed_by_id = v_user_id THEN
        RAISE EXCEPTION 'Cannot countersign your own handover';
    END IF;

    -- Get user info
    SELECT
        COALESCE(up.name, up.email),
        COALESCE(ur.role, 'member')
    INTO v_user_name, v_user_role
    FROM user_profiles up
    LEFT JOIN user_roles ur ON ur.user_id = up.id AND ur.is_active = TRUE
    WHERE up.id = v_user_id;

    -- Generate countersignature hash
    v_signature_hash := encode(sha256(
        (v_draft.signature_hash || v_user_id::TEXT || NOW()::TEXT)::bytea
    ), 'hex');

    -- Update draft
    UPDATE handover_drafts SET
        status = 'countersigned',
        countersigned_by_id = v_user_id,
        countersigned_by_name = v_user_name,
        countersigned_at = NOW(),
        updated_at = NOW()
    WHERE id = p_draft_id;

    -- Record countersignature
    INSERT INTO handover_signatures (
        yacht_id,
        handover_draft_id,
        signature_type,
        signer_id,
        signer_name,
        signer_role,
        signature_hash,
        snapshot_hash,
        acknowledgment_text
    ) VALUES (
        v_draft.yacht_id,
        p_draft_id,
        'incoming',
        v_user_id,
        v_user_name,
        v_user_role,
        v_signature_hash,
        encode(sha256((v_draft.published_snapshot)::TEXT::bytea), 'hex'),
        p_acknowledgment_text
    );

    -- Record to ledger
    PERFORM record_ledger_event(
        p_yacht_id := v_draft.yacht_id,
        p_event_class := 'mutation',
        p_event_verb := 'Countersigned',
        p_entity_type := 'handover',
        p_entity_id := p_draft_id,
        p_entity_display_name := v_draft.department || ' Handover — ' || v_draft.shift_date::TEXT,
        p_domain := 'Handover',
        p_context_data := jsonb_build_object(
            'countersign_hash', v_signature_hash,
            'incoming_crew', v_user_name
        )
    );

    RETURN jsonb_build_object(
        'success', TRUE,
        'draft_id', p_draft_id,
        'countersign_hash', v_signature_hash,
        'countersigned_at', NOW(),
        'message', 'Handover accepted. You are now responsible for this shift.'
    );
END;
$$;

GRANT EXECUTE ON FUNCTION public.countersign_handover TO authenticated;
```

---

## PART 4: STORAGE BUCKETS

### 4.1 Handover Exports Bucket

```sql
-- ============================================================================
-- STORAGE: handover_exports bucket
-- Purpose: Store exported handover PDFs
-- ============================================================================

-- Create bucket via Supabase Dashboard or API:
-- Bucket name: handover_exports
-- Public: FALSE
-- File size limit: 10MB
-- Allowed MIME types: application/pdf

-- Storage structure:
-- handover_exports/{yacht_id}/{year}/{month}/{department}_{date}_{shift}.pdf
-- Example: handover_exports/yacht_123/2025/01/engineering_2025-01-14_day.pdf

-- RLS Policy
CREATE POLICY "handover_exports_read" ON storage.objects
    FOR SELECT
    USING (
        bucket_id = 'handover_exports'
        AND (storage.foldername(name))[1] = (
            SELECT yacht_id::TEXT FROM public.user_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "handover_exports_insert" ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'handover_exports'
        AND (storage.foldername(name))[1] = (
            SELECT yacht_id::TEXT FROM public.user_profiles WHERE id = auth.uid()
        )
    );
```

---

## PART 5: RLS POLICIES

```sql
-- ============================================================================
-- RLS POLICIES: All handover tables
-- ============================================================================

-- handover_drafts: Full CRUD for yacht members
CREATE POLICY "handover_drafts_select" ON public.handover_drafts
    FOR SELECT USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "handover_drafts_insert" ON public.handover_drafts
    FOR INSERT WITH CHECK (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "handover_drafts_update" ON public.handover_drafts
    FOR UPDATE USING (
        yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND status IN ('draft', 'pending_review')  -- Can't modify published
    );

-- handover_proposed_items: Read all, decide own
CREATE POLICY "proposed_items_select" ON public.handover_proposed_items
    FOR SELECT USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "proposed_items_update" ON public.handover_proposed_items
    FOR UPDATE USING (
        yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND decision = 'pending'
    );

-- handover_accepted_items: Full CRUD while draft
CREATE POLICY "accepted_items_select" ON public.handover_accepted_items
    FOR SELECT USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "accepted_items_insert" ON public.handover_accepted_items
    FOR INSERT WITH CHECK (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "accepted_items_update" ON public.handover_accepted_items
    FOR UPDATE USING (
        yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND EXISTS (
            SELECT 1 FROM handover_drafts hd
            WHERE hd.id = handover_draft_id
            AND hd.status IN ('draft', 'pending_review')
        )
    );

-- handover_signatures: Read only (insert via RPC)
CREATE POLICY "signatures_select" ON public.handover_signatures
    FOR SELECT USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

---

## PART 6: API CONTRACT

### 6.1 Handover Document Format

```typescript
interface HandoverDocument {
  id: string;
  shift_date: string;
  shift_period: string;
  department: string;
  status: 'draft' | 'pending_review' | 'published' | 'countersigned' | 'archived';

  owner: {
    id: string;
    name: string;
    role: string;
  };

  // Content
  executive_summary?: string;
  outstanding_issues?: string;

  // Proposals (Celeste-generated, pending decision)
  pending_proposals: Array<{
    id: string;
    title: string;
    summary: string;
    next_action?: string;
    risk_category?: string;
    priority: number;
    source: {
      type: string;
      id: string;
      display_name: string;
    };
  }>;

  // Accepted items (will appear in published document)
  items: Array<{
    id: string;
    title: string;
    summary: string;
    next_action?: string;
    risk_category?: string;
    priority: number;
    origin: 'proposed' | 'manual';
    added_by: string;
    editable: boolean;
  }>;

  // Statistics
  statistics: {
    auto_items: number;
    manual_items: number;
    rejected_proposals: number;
  };

  // Sign-off (if published)
  signatures?: {
    outgoing?: {
      name: string;
      role: string;
      signed_at: string;
      hash: string;
    };
    incoming?: {
      name: string;
      role: string;
      signed_at: string;
      hash: string;
    };
  };
}
```

---

## PART 7: VALIDATION CHECKLIST

Before deployment, verify:

- [ ] `handover_drafts` table created with all status states
- [ ] `handover_proposed_items` auto-populated from ledger events
- [ ] `handover_accepted_items` preserves edit attribution
- [ ] `handover_signatures` creates immutable sign-off record
- [ ] `get_or_create_handover_draft()` auto-populates proposals
- [ ] `decide_handover_proposal()` tracks accept/reject with reason
- [ ] `publish_handover()` creates immutable snapshot
- [ ] `countersign_handover()` requires different user
- [ ] Users cannot countersign their own handover
- [ ] Published handovers cannot be edited
- [ ] PDF export includes signature hashes
- [ ] Legal notice shown before signing
- [ ] All decisions recorded to ledger

---

## RELATED DOCUMENTS

- `06-handover-continuity.md` - UX requirements source
- `05-ledger-and-proof.md` - Ledger integration
- `IMPL_02_ledger_proof.sql.md` - Ledger implementation
- `IMPL_05_role_departments.sql.md` - Department groupings
