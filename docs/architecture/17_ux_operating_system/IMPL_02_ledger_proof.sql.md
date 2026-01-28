# IMPLEMENTATION SPEC: Ledger & Proof System

> **Document**: `IMPL_02_ledger_proof.sql.md`
> **UX Source**: `05-ledger-and-proof.md`, `04-habits-cues-rewards.md`
> **Priority**: P0 (Foundation)
> **Target DB**: Tenant Database

---

## Overview

This specification implements the **Ledger as System Memory** defined in `05-ledger-and-proof.md`. The ledger answers one question only: **"What has actually happened?"**

Key UX requirements:
- Ledger is a LIST, not a table/dashboard
- Grouped by day with anchor counts (mutations/reads)
- Event grammar: **Object — Verb** (no adjectives, no interpretation)
- Reads are collapsed by default, mutations are prominent
- NEVER shows KPIs, progress bars, or judgments

---

## PART 1: NEW TABLES

### 1.1 `ledger_events` - Core event log

```sql
-- ============================================================================
-- TABLE: ledger_events
-- Purpose: Immutable record of all user-visible events
-- UX Requirement: "The ledger records reality, it does not manage it"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.ledger_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    -- Event timing
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_date DATE NOT NULL DEFAULT CURRENT_DATE,
    -- Denormalized for efficient day grouping

    -- Actor attribution (ALWAYS required)
    user_id UUID NOT NULL REFERENCES auth.users(id),
    user_name TEXT NOT NULL,
    user_role TEXT NOT NULL,
    -- Denormalized to preserve history even if user leaves

    -- Event classification
    event_class TEXT NOT NULL,
    -- Values: 'mutation', 'read', 'context'
    -- mutation = changed data (Created, Updated, Closed, Signed)
    -- read = viewed data (Viewed, Opened, Downloaded)
    -- context = navigation (Searched, Navigated)

    event_verb TEXT NOT NULL,
    -- The action verb: 'Created', 'Updated', 'Viewed', 'Closed', 'Signed', etc.

    -- Subject (what was acted upon)
    entity_type TEXT NOT NULL,
    -- Values: 'work_order', 'fault', 'equipment', 'part', 'document',
    --         'inventory', 'handover', 'purchase_order', 'receiving'
    entity_id UUID NOT NULL,
    entity_display_name TEXT NOT NULL,
    -- The display name at time of event (immutable)

    -- Domain grouping
    domain TEXT NOT NULL,
    -- Values: 'Documents', 'Inventory', 'Work Orders', 'Faults', 'Equipment',
    --         'Procurement', 'Handover', 'System'

    -- Optional context
    context_data JSONB DEFAULT '{}',
    -- Additional event-specific data (changes, previous values, etc.)

    -- Proof chain
    proof_hash TEXT,
    -- SHA256(previous_hash + event_data) for tamper detection

    previous_event_id UUID,
    -- Link to previous event for this entity (optional chain)

    -- Session tracking
    session_id TEXT,
    search_session_id UUID,
    -- Link to search_sessions if event originated from search

    -- Immutability enforcement
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_event_class CHECK (event_class IN ('mutation', 'read', 'context')),
    CONSTRAINT valid_domain CHECK (domain IN (
        'Documents', 'Inventory', 'Work Orders', 'Faults', 'Equipment',
        'Procurement', 'Handover', 'System', 'Search'
    ))
);

-- Partition by month for performance (optional for large deployments)
-- CREATE TABLE ledger_events_2024_01 PARTITION OF ledger_events
--     FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Critical indexes for ledger display
CREATE INDEX idx_ledger_events_yacht_date ON public.ledger_events(yacht_id, event_date DESC);
CREATE INDEX idx_ledger_events_yacht_timestamp ON public.ledger_events(yacht_id, event_timestamp DESC);
CREATE INDEX idx_ledger_events_user ON public.ledger_events(user_id, event_timestamp DESC);
CREATE INDEX idx_ledger_events_entity ON public.ledger_events(entity_type, entity_id, event_timestamp DESC);
CREATE INDEX idx_ledger_events_domain ON public.ledger_events(yacht_id, domain, event_date DESC);
CREATE INDEX idx_ledger_events_class ON public.ledger_events(yacht_id, event_class, event_date DESC);
CREATE INDEX idx_ledger_events_mutations ON public.ledger_events(yacht_id, event_date DESC)
    WHERE event_class = 'mutation';

-- RLS Policy
ALTER TABLE public.ledger_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ledger_events_yacht_isolation" ON public.ledger_events
    FOR ALL USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

### 1.2 `ledger_day_anchors` - Pre-computed day summaries

```sql
-- ============================================================================
-- TABLE: ledger_day_anchors
-- Purpose: Pre-computed daily summaries for efficient anchor display
-- UX Requirement: "Wed 14 Jan '25 — 7🟢 4🟠 6⭕"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.ledger_day_anchors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    anchor_date DATE NOT NULL,

    -- Event counts by class
    mutation_count INTEGER NOT NULL DEFAULT 0,
    -- 🟢 Green count (Created, Updated, Closed, Signed)

    read_count INTEGER NOT NULL DEFAULT 0,
    -- 🟠 Orange count (Viewed, Opened)

    context_count INTEGER NOT NULL DEFAULT 0,
    -- ⭕ Neutral count (Searched, Navigated)

    -- Domain breakdown
    domain_counts JSONB DEFAULT '{}',
    -- Format: {"Documents": 3, "Inventory": 5, "Work Orders": 2}

    -- User breakdown (for role-based views)
    user_counts JSONB DEFAULT '{}',
    -- Format: {"user_id_1": {"mutations": 3, "reads": 2}, ...}

    -- Computed at
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, anchor_date)
);

-- Index for anchor lookup
CREATE INDEX idx_ledger_anchors_yacht_date ON public.ledger_day_anchors(yacht_id, anchor_date DESC);

-- RLS Policy
ALTER TABLE public.ledger_day_anchors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ledger_anchors_yacht_isolation" ON public.ledger_day_anchors
    FOR SELECT USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

### 1.3 `ledger_filters` - Ephemeral filter presets (NOT saved states)

```sql
-- ============================================================================
-- TABLE: ledger_filter_presets
-- Purpose: System-defined filter presets (NOT user-saved filters)
-- UX Requirement: "filters reset on exit, no saved filter states"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.ledger_filter_presets (
    id TEXT PRIMARY KEY,
    -- e.g., 'show_mutations', 'show_unresolved', 'my_activity'

    name TEXT NOT NULL,
    description TEXT,

    filter_config JSONB NOT NULL,
    -- Format: {"event_class": ["mutation"], "domains": null, "user_scope": "self"}

    icon TEXT,
    display_order INTEGER DEFAULT 100,
    active BOOLEAN DEFAULT TRUE,

    -- Role restrictions
    required_roles TEXT[],
    -- NULL = available to all, ['captain', 'manager'] = leadership only

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed default filter presets
INSERT INTO public.ledger_filter_presets (id, name, description, filter_config, icon, display_order, required_roles) VALUES
('show_mutations', 'Show mutations', 'Only show events that changed data', '{"event_class": ["mutation"]}', 'edit-2', 10, NULL),
('show_unresolved', 'Show unresolved', 'Only show open/pending items', '{"status_filter": "unresolved"}', 'alert-circle', 20, NULL),
('my_activity', 'My activity', 'Only show my own events', '{"user_scope": "self"}', 'user', 30, NULL),
('department_activity', 'Department activity', 'Show all department events', '{"user_scope": "department"}', 'users', 40, ARRAY['captain', 'manager', 'chief_engineer', 'chief_stew'])
ON CONFLICT (id) DO NOTHING;
```

---

## PART 2: NEW COLUMNS ON EXISTING TABLES

### 2.1 `pms_audit_log` - Enhance for ledger integration

```sql
-- ============================================================================
-- ALTER TABLE: pms_audit_log
-- Add columns for ledger event generation
-- ============================================================================

-- Link to ledger event (1:1 for mutations)
ALTER TABLE public.pms_audit_log
ADD COLUMN IF NOT EXISTS ledger_event_id UUID REFERENCES public.ledger_events(id);

-- Event class classification
ALTER TABLE public.pms_audit_log
ADD COLUMN IF NOT EXISTS event_class TEXT DEFAULT 'mutation';

-- Display name at time of event (immutable)
ALTER TABLE public.pms_audit_log
ADD COLUMN IF NOT EXISTS entity_display_name TEXT;

-- Domain classification
ALTER TABLE public.pms_audit_log
ADD COLUMN IF NOT EXISTS domain TEXT;

-- Index for ledger sync
CREATE INDEX IF NOT EXISTS idx_audit_log_ledger_event
ON public.pms_audit_log(ledger_event_id);
```

### 2.2 All entity tables - Add `last_modified_event_id`

```sql
-- ============================================================================
-- ALTER TABLES: Add proof chain reference
-- Purpose: Link current state to last ledger event
-- ============================================================================

-- Work Orders
ALTER TABLE public.pms_work_orders
ADD COLUMN IF NOT EXISTS last_ledger_event_id UUID;

-- Faults
ALTER TABLE public.pms_faults
ADD COLUMN IF NOT EXISTS last_ledger_event_id UUID;

-- Equipment
ALTER TABLE public.pms_equipment
ADD COLUMN IF NOT EXISTS last_ledger_event_id UUID;

-- Parts
ALTER TABLE public.pms_parts
ADD COLUMN IF NOT EXISTS last_ledger_event_id UUID;

-- Documents
ALTER TABLE public.pms_documents
ADD COLUMN IF NOT EXISTS last_ledger_event_id UUID;

-- Handover
ALTER TABLE public.pms_handover
ADD COLUMN IF NOT EXISTS last_ledger_event_id UUID;

-- Handover Items
ALTER TABLE public.pms_handover_items
ADD COLUMN IF NOT EXISTS last_ledger_event_id UUID;
```

---

## PART 3: RPC FUNCTIONS

### 3.1 `record_ledger_event()` - Core event recording

```sql
-- ============================================================================
-- FUNCTION: record_ledger_event
-- Purpose: Record an event to the immutable ledger
-- UX Requirement: "Every mutation is attributable, reviewable, and immutable"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.record_ledger_event(
    p_yacht_id UUID,
    p_event_class TEXT,           -- 'mutation', 'read', 'context'
    p_event_verb TEXT,            -- 'Created', 'Updated', 'Viewed', etc.
    p_entity_type TEXT,           -- 'work_order', 'fault', etc.
    p_entity_id UUID,
    p_entity_display_name TEXT,
    p_domain TEXT,
    p_context_data JSONB DEFAULT '{}',
    p_search_session_id UUID DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_event_id UUID;
    v_user_id UUID;
    v_user_name TEXT;
    v_user_role TEXT;
    v_previous_event_id UUID;
    v_proof_hash TEXT;
BEGIN
    -- Get current user info
    v_user_id := auth.uid();

    SELECT
        COALESCE(up.name, up.email),
        COALESCE(ur.role, 'member')
    INTO v_user_name, v_user_role
    FROM user_profiles up
    LEFT JOIN user_roles ur ON ur.user_id = up.id AND ur.is_active = TRUE
    WHERE up.id = v_user_id;

    -- Get previous event for this entity (for proof chain)
    SELECT id INTO v_previous_event_id
    FROM ledger_events
    WHERE entity_type = p_entity_type AND entity_id = p_entity_id
    ORDER BY event_timestamp DESC
    LIMIT 1;

    -- Generate proof hash (SHA256 of event data + previous hash)
    v_proof_hash := encode(sha256(
        (COALESCE(v_previous_event_id::TEXT, 'GENESIS') ||
         p_entity_type || p_entity_id::TEXT ||
         p_event_verb || v_user_id::TEXT ||
         NOW()::TEXT)::bytea
    ), 'hex');

    -- Insert ledger event
    INSERT INTO ledger_events (
        yacht_id,
        user_id,
        user_name,
        user_role,
        event_class,
        event_verb,
        entity_type,
        entity_id,
        entity_display_name,
        domain,
        context_data,
        proof_hash,
        previous_event_id,
        search_session_id
    ) VALUES (
        p_yacht_id,
        v_user_id,
        v_user_name,
        v_user_role,
        p_event_class,
        p_event_verb,
        p_entity_type,
        p_entity_id,
        p_entity_display_name,
        p_domain,
        p_context_data,
        v_proof_hash,
        v_previous_event_id,
        p_search_session_id
    )
    RETURNING id INTO v_event_id;

    -- Update day anchor counts
    INSERT INTO ledger_day_anchors (yacht_id, anchor_date, mutation_count, read_count, context_count)
    VALUES (
        p_yacht_id,
        CURRENT_DATE,
        CASE WHEN p_event_class = 'mutation' THEN 1 ELSE 0 END,
        CASE WHEN p_event_class = 'read' THEN 1 ELSE 0 END,
        CASE WHEN p_event_class = 'context' THEN 1 ELSE 0 END
    )
    ON CONFLICT (yacht_id, anchor_date) DO UPDATE SET
        mutation_count = ledger_day_anchors.mutation_count +
            CASE WHEN p_event_class = 'mutation' THEN 1 ELSE 0 END,
        read_count = ledger_day_anchors.read_count +
            CASE WHEN p_event_class = 'read' THEN 1 ELSE 0 END,
        context_count = ledger_day_anchors.context_count +
            CASE WHEN p_event_class = 'context' THEN 1 ELSE 0 END,
        computed_at = NOW();

    RETURN v_event_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.record_ledger_event TO authenticated;
```

### 3.2 `get_ledger_view()` - Retrieve ledger for display

```sql
-- ============================================================================
-- FUNCTION: get_ledger_view
-- Purpose: Retrieve ledger events formatted for UI display
-- UX Requirement: "Chronological list grouped by day"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_ledger_view(
    p_yacht_id UUID,
    p_date_from DATE DEFAULT CURRENT_DATE - INTERVAL '7 days',
    p_date_to DATE DEFAULT CURRENT_DATE,
    p_event_classes TEXT[] DEFAULT NULL,  -- NULL = all, ['mutation'] = mutations only
    p_domains TEXT[] DEFAULT NULL,        -- NULL = all, ['Documents', 'Inventory']
    p_user_scope TEXT DEFAULT 'self',     -- 'self', 'department', 'all'
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    -- Day anchor data
    anchor_date DATE,
    anchor_display TEXT,                   -- "Wed 14 Jan '25"
    mutation_count INTEGER,
    read_count INTEGER,
    context_count INTEGER,

    -- Event data
    event_id UUID,
    event_timestamp TIMESTAMPTZ,
    event_class TEXT,
    event_verb TEXT,
    entity_type TEXT,
    entity_id UUID,
    entity_display_name TEXT,
    domain TEXT,
    user_name TEXT,
    user_role TEXT,
    is_own_event BOOLEAN,
    context_data JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_user_role TEXT;
BEGIN
    v_user_id := auth.uid();

    -- Get user's role for permission check
    SELECT ur.role INTO v_user_role
    FROM user_roles ur
    WHERE ur.user_id = v_user_id AND ur.is_active = TRUE
    LIMIT 1;

    -- Validate user_scope permission
    IF p_user_scope IN ('department', 'all') AND
       v_user_role NOT IN ('captain', 'manager', 'chief_engineer', 'chief_stew') THEN
        p_user_scope := 'self';  -- Downgrade to self if not authorized
    END IF;

    RETURN QUERY
    WITH day_anchors AS (
        SELECT
            da.anchor_date,
            TO_CHAR(da.anchor_date, 'Dy DD Mon ''YY') as anchor_display,
            da.mutation_count,
            da.read_count,
            da.context_count
        FROM ledger_day_anchors da
        WHERE da.yacht_id = p_yacht_id
        AND da.anchor_date BETWEEN p_date_from AND p_date_to
    )
    SELECT
        da.anchor_date,
        da.anchor_display,
        da.mutation_count,
        da.read_count,
        da.context_count,
        le.id as event_id,
        le.event_timestamp,
        le.event_class,
        le.event_verb,
        le.entity_type,
        le.entity_id,
        le.entity_display_name,
        le.domain,
        le.user_name,
        le.user_role,
        (le.user_id = v_user_id) as is_own_event,
        le.context_data
    FROM ledger_events le
    JOIN day_anchors da ON da.anchor_date = le.event_date
    WHERE le.yacht_id = p_yacht_id
    AND le.event_date BETWEEN p_date_from AND p_date_to
    AND (p_event_classes IS NULL OR le.event_class = ANY(p_event_classes))
    AND (p_domains IS NULL OR le.domain = ANY(p_domains))
    AND (
        p_user_scope = 'all'
        OR (p_user_scope = 'self' AND le.user_id = v_user_id)
        OR (p_user_scope = 'department' AND le.user_role = v_user_role)
    )
    ORDER BY le.event_date DESC, le.event_timestamp DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_ledger_view TO authenticated;
```

### 3.3 `get_entity_history()` - Full history for single entity

```sql
-- ============================================================================
-- FUNCTION: get_entity_history
-- Purpose: Get complete event history for a specific entity
-- UX Requirement: "a user can reconstruct what happened"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_entity_history(
    p_entity_type TEXT,
    p_entity_id UUID,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    event_id UUID,
    event_timestamp TIMESTAMPTZ,
    event_verb TEXT,
    user_name TEXT,
    user_role TEXT,
    context_data JSONB,
    proof_hash TEXT,
    is_verified BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
BEGIN
    -- Verify user has access to this entity's yacht
    IF NOT EXISTS (
        SELECT 1 FROM ledger_events le
        WHERE le.entity_type = p_entity_type
        AND le.entity_id = p_entity_id
        AND le.yacht_id = (SELECT yacht_id FROM user_profiles WHERE id = auth.uid())
        LIMIT 1
    ) THEN
        RAISE EXCEPTION 'Entity not found or access denied';
    END IF;

    RETURN QUERY
    SELECT
        le.id as event_id,
        le.event_timestamp,
        le.event_verb,
        le.user_name,
        le.user_role,
        le.context_data,
        le.proof_hash,
        -- Verify proof chain integrity
        (le.proof_hash = encode(sha256(
            (COALESCE(le.previous_event_id::TEXT, 'GENESIS') ||
             le.entity_type || le.entity_id::TEXT ||
             le.event_verb || le.user_id::TEXT ||
             le.event_timestamp::TEXT)::bytea
        ), 'hex')) as is_verified
    FROM ledger_events le
    WHERE le.entity_type = p_entity_type
    AND le.entity_id = p_entity_id
    ORDER BY le.event_timestamp DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_entity_history TO authenticated;
```

### 3.4 `search_ledger()` - Search within ledger

```sql
-- ============================================================================
-- FUNCTION: search_ledger
-- Purpose: Search ledger events with same UX as global search
-- UX Requirement: "Search inside the ledger identical to global search"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.search_ledger(
    p_yacht_id UUID,
    p_query TEXT,
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    event_id UUID,
    event_timestamp TIMESTAMPTZ,
    anchor_date DATE,
    event_class TEXT,
    event_verb TEXT,
    entity_type TEXT,
    entity_id UUID,
    entity_display_name TEXT,
    domain TEXT,
    user_name TEXT,
    relevance_rank INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        le.id,
        le.event_timestamp,
        le.event_date,
        le.event_class,
        le.event_verb,
        le.entity_type,
        le.entity_id,
        le.entity_display_name,
        le.domain,
        le.user_name,
        ROW_NUMBER() OVER (ORDER BY
            -- Exact match on entity name ranks highest
            CASE WHEN le.entity_display_name ILIKE '%' || p_query || '%' THEN 0 ELSE 1 END,
            -- Then by recency
            le.event_timestamp DESC
        )::INTEGER as relevance_rank
    FROM ledger_events le
    WHERE le.yacht_id = p_yacht_id
    AND (p_date_from IS NULL OR le.event_date >= p_date_from)
    AND (p_date_to IS NULL OR le.event_date <= p_date_to)
    AND (
        le.entity_display_name ILIKE '%' || p_query || '%'
        OR le.event_verb ILIKE '%' || p_query || '%'
        OR le.domain ILIKE '%' || p_query || '%'
        OR le.user_name ILIKE '%' || p_query || '%'
        OR le.context_data::TEXT ILIKE '%' || p_query || '%'
    )
    ORDER BY relevance_rank ASC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION public.search_ledger TO authenticated;
```

---

## PART 4: TRIGGERS FOR AUTOMATIC EVENT RECORDING

### 4.1 Work Order Events Trigger

```sql
-- ============================================================================
-- TRIGGER: Record work order events to ledger
-- ============================================================================

CREATE OR REPLACE FUNCTION public.trigger_work_order_ledger_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_event_verb TEXT;
    v_context JSONB;
BEGIN
    -- Determine event verb based on operation
    IF TG_OP = 'INSERT' THEN
        v_event_verb := 'Created';
        v_context := jsonb_build_object(
            'title', NEW.title,
            'priority', NEW.priority,
            'status', NEW.status
        );
    ELSIF TG_OP = 'UPDATE' THEN
        -- Determine specific verb based on what changed
        IF OLD.status != NEW.status THEN
            CASE NEW.status
                WHEN 'completed' THEN v_event_verb := 'Closed';
                WHEN 'in_progress' THEN v_event_verb := 'Started';
                WHEN 'blocked' THEN v_event_verb := 'Blocked';
                ELSE v_event_verb := 'Updated';
            END CASE;
        ELSE
            v_event_verb := 'Updated';
        END IF;

        v_context := jsonb_build_object(
            'changes', jsonb_build_object(
                'status', CASE WHEN OLD.status != NEW.status
                    THEN jsonb_build_object('from', OLD.status, 'to', NEW.status)
                    ELSE NULL END,
                'assigned_to', CASE WHEN OLD.assigned_to IS DISTINCT FROM NEW.assigned_to
                    THEN jsonb_build_object('from', OLD.assigned_to, 'to', NEW.assigned_to)
                    ELSE NULL END
            )
        );
    END IF;

    -- Record to ledger
    NEW.last_ledger_event_id := record_ledger_event(
        p_yacht_id := NEW.yacht_id,
        p_event_class := 'mutation',
        p_event_verb := v_event_verb,
        p_entity_type := 'work_order',
        p_entity_id := NEW.id,
        p_entity_display_name := 'Work Order #' || NEW.number || ' — ' || NEW.title,
        p_domain := 'Work Orders',
        p_context_data := v_context
    );

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_work_order_ledger ON public.pms_work_orders;
CREATE TRIGGER trg_work_order_ledger
    AFTER INSERT OR UPDATE ON public.pms_work_orders
    FOR EACH ROW
    EXECUTE FUNCTION trigger_work_order_ledger_event();
```

### 4.2 Fault Events Trigger

```sql
-- ============================================================================
-- TRIGGER: Record fault events to ledger
-- ============================================================================

CREATE OR REPLACE FUNCTION public.trigger_fault_ledger_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_event_verb TEXT;
    v_context JSONB;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_event_verb := 'Created';
        v_context := jsonb_build_object(
            'title', NEW.title,
            'severity', NEW.severity
        );
    ELSIF TG_OP = 'UPDATE' THEN
        CASE NEW.status
            WHEN 'resolved' THEN v_event_verb := 'Resolved';
            WHEN 'acknowledged' THEN v_event_verb := 'Acknowledged';
            ELSE v_event_verb := 'Updated';
        END CASE;

        v_context := jsonb_build_object(
            'status_change', jsonb_build_object('from', OLD.status, 'to', NEW.status)
        );
    END IF;

    NEW.last_ledger_event_id := record_ledger_event(
        p_yacht_id := NEW.yacht_id,
        p_event_class := 'mutation',
        p_event_verb := v_event_verb,
        p_entity_type := 'fault',
        p_entity_id := NEW.id,
        p_entity_display_name := NEW.title,
        p_domain := 'Faults',
        p_context_data := v_context
    );

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_fault_ledger ON public.pms_faults;
CREATE TRIGGER trg_fault_ledger
    AFTER INSERT OR UPDATE ON public.pms_faults
    FOR EACH ROW
    EXECUTE FUNCTION trigger_fault_ledger_event();
```

### 4.3 Inventory Transaction Events Trigger

```sql
-- ============================================================================
-- TRIGGER: Record inventory events to ledger
-- ============================================================================

CREATE OR REPLACE FUNCTION public.trigger_inventory_ledger_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_event_verb TEXT;
    v_part_name TEXT;
    v_context JSONB;
BEGIN
    -- Get part name
    SELECT name INTO v_part_name FROM pms_parts WHERE id = NEW.part_id;

    -- Determine verb from transaction type
    CASE NEW.transaction_type
        WHEN 'receive' THEN v_event_verb := 'Received';
        WHEN 'usage' THEN v_event_verb := 'Used';
        WHEN 'adjustment' THEN v_event_verb := 'Adjusted';
        WHEN 'transfer' THEN v_event_verb := 'Transferred';
        WHEN 'cycle_count' THEN v_event_verb := 'Counted';
        ELSE v_event_verb := 'Updated';
    END CASE;

    v_context := jsonb_build_object(
        'quantity', NEW.quantity,
        'transaction_type', NEW.transaction_type,
        'work_order_id', NEW.work_order_id,
        'location', NEW.location
    );

    -- Record to ledger (don't update source table, just log)
    PERFORM record_ledger_event(
        p_yacht_id := NEW.yacht_id,
        p_event_class := 'mutation',
        p_event_verb := v_event_verb,
        p_entity_type := 'inventory_transaction',
        p_entity_id := NEW.id,
        p_entity_display_name := v_part_name || ' — ' || NEW.quantity::TEXT || ' units',
        p_domain := 'Inventory',
        p_context_data := v_context
    );

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_inventory_ledger ON public.pms_inventory_transactions;
CREATE TRIGGER trg_inventory_ledger
    AFTER INSERT ON public.pms_inventory_transactions
    FOR EACH ROW
    EXECUTE FUNCTION trigger_inventory_ledger_event();
```

### 4.4 Document View Events (Manual Recording)

```sql
-- ============================================================================
-- FUNCTION: record_document_view
-- Purpose: Record when user views a document (called by API)
-- UX Requirement: "reads are collapsed by default, not hidden"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.record_document_view(
    p_document_id UUID,
    p_page_number INTEGER DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_doc RECORD;
    v_event_id UUID;
BEGIN
    -- Get document info
    SELECT id, yacht_id, title INTO v_doc
    FROM pms_documents WHERE id = p_document_id;

    IF v_doc IS NULL THEN
        RAISE EXCEPTION 'Document not found';
    END IF;

    -- Record read event
    v_event_id := record_ledger_event(
        p_yacht_id := v_doc.yacht_id,
        p_event_class := 'read',
        p_event_verb := 'Viewed',
        p_entity_type := 'document',
        p_entity_id := v_doc.id,
        p_entity_display_name := v_doc.title,
        p_domain := 'Documents',
        p_context_data := jsonb_build_object('page_number', p_page_number)
    );

    RETURN v_event_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.record_document_view TO authenticated;
```

---

## PART 5: RLS POLICIES

```sql
-- ============================================================================
-- RLS POLICIES: Ledger tables
-- ============================================================================

-- Ledger events: Users see only their yacht's events
CREATE POLICY "ledger_events_select" ON public.ledger_events
    FOR SELECT
    USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

-- Ledger events: Insert via RPC only (trigger functions)
CREATE POLICY "ledger_events_insert" ON public.ledger_events
    FOR INSERT
    WITH CHECK (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

-- Ledger events: NO UPDATE OR DELETE (immutable)
-- No policies for UPDATE/DELETE = denied

-- Day anchors: Read only
CREATE POLICY "ledger_anchors_select" ON public.ledger_day_anchors
    FOR SELECT
    USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

---

## PART 6: API CONTRACT

### 6.1 Ledger Display Format

```typescript
// Ledger response format for UI

interface LedgerDayGroup {
  anchor: {
    date: string;           // "2025-01-14"
    display: string;        // "Wed 14 Jan '25"
    mutations: number;      // 🟢 count
    reads: number;          // 🟠 count
    contexts: number;       // ⭕ count
  };

  events: Array<{
    id: string;
    timestamp: string;      // ISO timestamp
    class: 'mutation' | 'read' | 'context';
    verb: string;           // "Created", "Viewed", etc.

    // Entity (Object — Verb format)
    entity: {
      type: string;
      id: string;
      display_name: string;  // "Generator Manual"
    };

    // Attribution
    user: {
      name: string;
      role: string;
      is_self: boolean;
    };

    // Grouping
    domain: string;          // "Documents", "Inventory", etc.
  }>;
}

// UI must render:
// - Day anchors stay visible while scrolling (sticky)
// - Mutations rendered with higher visual weight
// - Reads collapsed by default (expandable)
// - No colors suggesting judgment (green=good, red=bad)
```

---

## PART 7: VALIDATION CHECKLIST

Before deployment, verify:

- [ ] `ledger_events` table created with immutable structure
- [ ] `ledger_day_anchors` table auto-populates on event insert
- [ ] `record_ledger_event()` generates correct proof hashes
- [ ] `get_ledger_view()` returns grouped by day with anchors
- [ ] `get_entity_history()` shows full chain with verification
- [ ] `search_ledger()` works with same grammar as global search
- [ ] All entity triggers record events automatically
- [ ] Read events can be collapsed but not hidden
- [ ] No UPDATE/DELETE policies on ledger_events (immutable)
- [ ] Proof chain integrity can be verified
- [ ] Day anchors show correct counts (mutations/reads/contexts)
- [ ] Department view respects role permissions

---

## RELATED DOCUMENTS

- `05-ledger-and-proof.md` - UX requirements source
- `04-habits-cues-rewards.md` - Reward is evidentiary
- `08-transparency-and-power.md` - Facts over interpretation
- `IMPL_01_search_intelligence.sql.md` - Search integration
- `IMPL_03_handover_continuity.sql.md` - Handover uses ledger events
