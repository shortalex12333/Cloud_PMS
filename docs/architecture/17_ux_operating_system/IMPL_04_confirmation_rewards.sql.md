# IMPLEMENTATION SPEC: Confirmation & Evidentiary Rewards

> **Document**: `IMPL_04_confirmation_rewards.sql.md`
> **UX Source**: `04-habits-cues-rewards.md`, `03-interlocutor-model.md`
> **Priority**: P1 (User Trust)
> **Target DB**: Tenant Database

---

## Overview

This specification implements the **Evidentiary Reward System** defined in `04-habits-cues-rewards.md`. The reward is **certainty**, not celebration.

Key UX requirements:
- Every mutation produces immediate confirmation
- Confirmation shows: what changed, when, who, where recorded
- No celebration, no color explosion, no disappearance
- Closure is mandatory - empty screen after completion is unacceptable
- Users must be able to trust outcomes without double-checking

---

## PART 1: NEW TABLES

### 1.1 `action_confirmations` - Immediate feedback records

```sql
-- ============================================================================
-- TABLE: action_confirmations
-- Purpose: Store confirmation data for every mutation
-- UX Requirement: "Every committed action must produce immediate confirmation"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.action_confirmations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    -- User who performed the action
    user_id UUID NOT NULL REFERENCES auth.users(id),

    -- What was done
    action_type TEXT NOT NULL,
    -- Values: 'create', 'update', 'complete', 'log', 'sign', 'acknowledge'

    action_verb TEXT NOT NULL,
    -- Human-readable verb: "Created", "Updated", "Logged", etc.

    -- What was affected
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    entity_display_name TEXT NOT NULL,

    -- Domain for grouping
    domain TEXT NOT NULL,

    -- Confirmation message components
    confirmation_headline TEXT NOT NULL,
    -- e.g., "Work Order Created"

    confirmation_details JSONB NOT NULL,
    -- Structured details for UI rendering
    -- Format: {
    --   "what_changed": "Work Order #WO-2024-001",
    --   "when": "2025-01-14T10:30:00Z",
    --   "who": "John Smith",
    --   "where_recorded": "Ledger, Work Orders",
    --   "handover_status": "Added to handover draft"
    -- }

    -- Proof references
    ledger_event_id UUID REFERENCES public.ledger_events(id),
    audit_log_id UUID,

    -- Follow-up actions available
    available_actions JSONB DEFAULT '[]'::jsonb,
    -- e.g., [{"id": "add_to_handover", "label": "Add to handover"}, {"id": "view_details", "label": "View details"}]

    -- Display metadata
    display_duration_ms INTEGER DEFAULT 5000,
    -- How long to show confirmation (0 = until dismissed)

    auto_dismiss BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dismissed_at TIMESTAMPTZ,
    follow_up_action_taken TEXT,

    CONSTRAINT valid_action_type CHECK (action_type IN (
        'create', 'update', 'complete', 'log', 'sign', 'acknowledge', 'delete', 'cancel'
    ))
);

-- Indexes
CREATE INDEX idx_confirmations_user ON public.action_confirmations(user_id, created_at DESC);
CREATE INDEX idx_confirmations_entity ON public.action_confirmations(entity_type, entity_id);
CREATE INDEX idx_confirmations_recent ON public.action_confirmations(user_id, created_at DESC)
    WHERE dismissed_at IS NULL;

-- RLS Policy
ALTER TABLE public.action_confirmations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "confirmations_own_only" ON public.action_confirmations
    FOR ALL USING (user_id = auth.uid());
```

### 1.2 `confirmation_templates` - Standardized confirmation formats

```sql
-- ============================================================================
-- TABLE: confirmation_templates
-- Purpose: Consistent confirmation messaging per action type
-- UX Requirement: "predictable confirmation rituals"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.confirmation_templates (
    id TEXT PRIMARY KEY,
    -- e.g., 'work_order_created', 'fault_resolved', 'part_logged'

    -- Action context
    entity_type TEXT NOT NULL,
    action_type TEXT NOT NULL,

    -- Template content
    headline_template TEXT NOT NULL,
    -- e.g., "Work Order Created" or "{entity_name} Updated"

    detail_template JSONB NOT NULL,
    -- Template for confirmation_details
    -- Uses {placeholders} for dynamic values

    -- Proof statement
    proof_statement TEXT NOT NULL DEFAULT 'Logged • Attributed • Retrievable',
    -- What appears at bottom of confirmation

    -- Follow-up actions
    default_actions JSONB DEFAULT '[]'::jsonb,
    -- Actions to offer after this confirmation

    -- Display settings
    display_duration_ms INTEGER DEFAULT 5000,
    auto_dismiss BOOLEAN DEFAULT TRUE,
    show_proof_hash BOOLEAN DEFAULT FALSE,

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed confirmation templates
INSERT INTO public.confirmation_templates (id, entity_type, action_type, headline_template, detail_template, proof_statement, default_actions) VALUES

-- Work Orders
('work_order_created', 'work_order', 'create',
 'Work Order Created',
 '{"what_changed": "Work Order #{number}", "status": "Created as {status}", "assigned": "{assigned_to}"}',
 'Logged • Attributed • Added to ledger',
 '[{"id": "add_to_handover", "label": "Add to handover"}, {"id": "view_details", "label": "View details"}]'
),
('work_order_updated', 'work_order', 'update',
 'Work Order Updated',
 '{"what_changed": "{changes_summary}", "work_order": "#{number}"}',
 'Logged • Attributed • Retrievable',
 '[{"id": "view_history", "label": "View history"}]'
),
('work_order_completed', 'work_order', 'complete',
 'Work Order Closed',
 '{"what_changed": "Work Order #{number} marked complete", "outcome": "{outcome}", "time_spent": "{time_spent_hours} hours"}',
 'Logged • Attributed • Included in handover',
 '[{"id": "add_to_handover", "label": "Add to handover"}, {"id": "view_summary", "label": "View summary"}]'
),

-- Faults
('fault_created', 'fault', 'create',
 'Fault Reported',
 '{"what_changed": "{title}", "severity": "{severity}", "equipment": "{equipment_name}"}',
 'Logged • Attributed • Tracked',
 '[{"id": "create_work_order", "label": "Create work order"}, {"id": "add_to_handover", "label": "Add to handover"}]'
),
('fault_acknowledged', 'fault', 'acknowledge',
 'Fault Acknowledged',
 '{"what_changed": "{title}", "acknowledged_by": "{user_name}"}',
 'Logged • Attributed',
 '[{"id": "create_work_order", "label": "Create work order"}]'
),
('fault_resolved', 'fault', 'complete',
 'Fault Resolved',
 '{"what_changed": "{title}", "resolution": "{resolution_notes}"}',
 'Logged • Attributed • Closed',
 '[{"id": "view_history", "label": "View history"}]'
),

-- Inventory
('part_logged', 'inventory_transaction', 'log',
 'Part Usage Logged',
 '{"what_changed": "{part_name}", "quantity": "{quantity} {unit}", "work_order": "#{work_order_number}"}',
 'Logged • Inventory updated • Retrievable',
 '[{"id": "view_stock", "label": "View stock level"}]'
),
('part_received', 'inventory_transaction', 'create',
 'Parts Received',
 '{"what_changed": "{part_name}", "quantity": "{quantity} received", "location": "{location}"}',
 'Logged • Inventory updated',
 '[{"id": "view_inventory", "label": "View inventory"}]'
),

-- Documents
('document_viewed', 'document', 'read',
 'Document Accessed',
 '{"what_changed": "{title}", "page": "Page {page_number}"}',
 'Logged',
 '[{"id": "add_note", "label": "Add note"}, {"id": "add_to_handover", "label": "Add to handover"}]'
),

-- Handover
('handover_item_added', 'handover_item', 'create',
 'Added to Handover',
 '{"what_changed": "{title}", "handover": "{shift_date} {shift_period}"}',
 'Logged • Will appear in handover document',
 '[{"id": "view_handover", "label": "View handover"}]'
),
('handover_signed', 'handover', 'sign',
 'Handover Signed',
 '{"what_changed": "{department} Handover", "items_count": "{items_count} items", "signature": "{signature_hash}"}',
 'Signed • Immutable • Awaiting countersign',
 '[{"id": "view_handover", "label": "View handover"}, {"id": "export_pdf", "label": "Export PDF"}]'
)

ON CONFLICT (id) DO UPDATE SET
    headline_template = EXCLUDED.headline_template,
    detail_template = EXCLUDED.detail_template,
    default_actions = EXCLUDED.default_actions;
```

### 1.3 `user_action_history` - Recent actions for "Did I do that?"

```sql
-- ============================================================================
-- TABLE: user_action_history
-- Purpose: Quick access to user's recent actions
-- UX Requirement: "users stop asking 'Did I log that?'"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.user_action_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id),

    -- Action summary
    action_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action_date DATE NOT NULL DEFAULT CURRENT_DATE,

    action_summary TEXT NOT NULL,
    -- e.g., "Created Work Order #WO-2024-001"

    action_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    entity_display_name TEXT NOT NULL,

    -- Quick verification fields
    proof_available BOOLEAN DEFAULT TRUE,
    ledger_event_id UUID,
    confirmation_id UUID REFERENCES public.action_confirmations(id),

    -- For "what did I do today" queries
    session_id TEXT,

    CONSTRAINT valid_action_type CHECK (action_type IN (
        'create', 'update', 'complete', 'log', 'sign', 'acknowledge', 'view', 'delete', 'cancel'
    ))
);

-- Indexes for fast "my recent actions" queries
CREATE INDEX idx_action_history_user_date ON public.user_action_history(user_id, action_date DESC);
CREATE INDEX idx_action_history_user_recent ON public.user_action_history(user_id, action_timestamp DESC);
CREATE INDEX idx_action_history_entity ON public.user_action_history(entity_type, entity_id);

-- Partition by month for performance (optional)
-- Consider if user_action_history grows large

-- RLS Policy
ALTER TABLE public.user_action_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "action_history_own_only" ON public.user_action_history
    FOR SELECT USING (user_id = auth.uid());
```

---

## PART 2: RPC FUNCTIONS

### 2.1 `generate_confirmation()` - Create confirmation after action

```sql
-- ============================================================================
-- FUNCTION: generate_confirmation
-- Purpose: Generate and store confirmation for any mutation
-- UX Requirement: "immediate confirmation, durable trace, later retrievability"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.generate_confirmation(
    p_yacht_id UUID,
    p_action_type TEXT,
    p_entity_type TEXT,
    p_entity_id UUID,
    p_entity_display_name TEXT,
    p_domain TEXT,
    p_context JSONB DEFAULT '{}',
    p_ledger_event_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_user_name TEXT;
    v_template RECORD;
    v_confirmation_id UUID;
    v_headline TEXT;
    v_details JSONB;
    v_action_verb TEXT;
    v_proof_statement TEXT;
    v_available_actions JSONB;
BEGIN
    v_user_id := auth.uid();

    -- Get user name
    SELECT COALESCE(name, email) INTO v_user_name
    FROM user_profiles WHERE id = v_user_id;

    -- Get template
    SELECT * INTO v_template
    FROM confirmation_templates
    WHERE entity_type = p_entity_type
    AND action_type = p_action_type
    AND active = TRUE
    LIMIT 1;

    -- Generate action verb
    v_action_verb := CASE p_action_type
        WHEN 'create' THEN 'Created'
        WHEN 'update' THEN 'Updated'
        WHEN 'complete' THEN 'Completed'
        WHEN 'log' THEN 'Logged'
        WHEN 'sign' THEN 'Signed'
        WHEN 'acknowledge' THEN 'Acknowledged'
        WHEN 'delete' THEN 'Removed'
        WHEN 'cancel' THEN 'Cancelled'
        ELSE 'Modified'
    END;

    -- Build confirmation content
    IF v_template IS NOT NULL THEN
        v_headline := v_template.headline_template;
        v_proof_statement := v_template.proof_statement;
        v_available_actions := v_template.default_actions;
    ELSE
        v_headline := p_entity_type || ' ' || v_action_verb;
        v_proof_statement := 'Logged • Attributed • Retrievable';
        v_available_actions := '[]'::jsonb;
    END IF;

    -- Build confirmation details
    v_details := jsonb_build_object(
        'what_changed', p_entity_display_name,
        'when', NOW(),
        'who', v_user_name,
        'where_recorded', 'Ledger, ' || p_domain,
        'action_type', p_action_type,
        'context', p_context
    );

    -- Insert confirmation
    INSERT INTO action_confirmations (
        yacht_id,
        user_id,
        action_type,
        action_verb,
        entity_type,
        entity_id,
        entity_display_name,
        domain,
        confirmation_headline,
        confirmation_details,
        ledger_event_id,
        available_actions,
        display_duration_ms,
        auto_dismiss
    ) VALUES (
        p_yacht_id,
        v_user_id,
        p_action_type,
        v_action_verb,
        p_entity_type,
        p_entity_id,
        p_entity_display_name,
        p_domain,
        v_headline,
        v_details,
        p_ledger_event_id,
        v_available_actions,
        COALESCE(v_template.display_duration_ms, 5000),
        COALESCE(v_template.auto_dismiss, TRUE)
    )
    RETURNING id INTO v_confirmation_id;

    -- Record to action history
    INSERT INTO user_action_history (
        yacht_id,
        user_id,
        action_summary,
        action_type,
        entity_type,
        entity_id,
        entity_display_name,
        ledger_event_id,
        confirmation_id
    ) VALUES (
        p_yacht_id,
        v_user_id,
        v_action_verb || ' ' || p_entity_display_name,
        p_action_type,
        p_entity_type,
        p_entity_id,
        p_entity_display_name,
        p_ledger_event_id,
        v_confirmation_id
    );

    -- Return confirmation payload for UI
    RETURN jsonb_build_object(
        'confirmation_id', v_confirmation_id,
        'headline', v_headline,
        'details', v_details,
        'proof_statement', v_proof_statement,
        'available_actions', v_available_actions,
        'display_duration_ms', COALESCE(v_template.display_duration_ms, 5000),
        'auto_dismiss', COALESCE(v_template.auto_dismiss, TRUE),
        'ledger_event_id', p_ledger_event_id
    );
END;
$$;

GRANT EXECUTE ON FUNCTION public.generate_confirmation TO authenticated;
```

### 2.2 `get_my_recent_actions()` - "What did I do today?"

```sql
-- ============================================================================
-- FUNCTION: get_my_recent_actions
-- Purpose: Quick answer to "Did I log that?" / "What did I do?"
-- UX Requirement: "users stop double-checking themselves"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_my_recent_actions(
    p_date DATE DEFAULT CURRENT_DATE,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    action_timestamp TIMESTAMPTZ,
    action_summary TEXT,
    action_type TEXT,
    entity_type TEXT,
    entity_id UUID,
    entity_display_name TEXT,
    proof_available BOOLEAN,
    confirmation_id UUID
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        uah.action_timestamp,
        uah.action_summary,
        uah.action_type,
        uah.entity_type,
        uah.entity_id,
        uah.entity_display_name,
        uah.proof_available,
        uah.confirmation_id
    FROM user_action_history uah
    WHERE uah.user_id = auth.uid()
    AND uah.action_date = p_date
    ORDER BY uah.action_timestamp DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_my_recent_actions TO authenticated;
```

### 2.3 `verify_action_proof()` - Verify action was recorded

```sql
-- ============================================================================
-- FUNCTION: verify_action_proof
-- Purpose: Allow user to verify their action was properly recorded
-- UX Requirement: "trust that work is remembered"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.verify_action_proof(
    p_entity_type TEXT,
    p_entity_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_ledger_event RECORD;
    v_confirmation RECORD;
    v_action_history RECORD;
BEGIN
    -- Get latest ledger event for this entity
    SELECT * INTO v_ledger_event
    FROM ledger_events
    WHERE entity_type = p_entity_type
    AND entity_id = p_entity_id
    AND yacht_id = (SELECT yacht_id FROM user_profiles WHERE id = auth.uid())
    ORDER BY event_timestamp DESC
    LIMIT 1;

    -- Get corresponding confirmation
    SELECT * INTO v_confirmation
    FROM action_confirmations
    WHERE entity_type = p_entity_type
    AND entity_id = p_entity_id
    ORDER BY created_at DESC
    LIMIT 1;

    -- Get action history entry
    SELECT * INTO v_action_history
    FROM user_action_history
    WHERE entity_type = p_entity_type
    AND entity_id = p_entity_id
    ORDER BY action_timestamp DESC
    LIMIT 1;

    RETURN jsonb_build_object(
        'verified', v_ledger_event IS NOT NULL,
        'ledger_event', CASE WHEN v_ledger_event IS NOT NULL THEN
            jsonb_build_object(
                'id', v_ledger_event.id,
                'timestamp', v_ledger_event.event_timestamp,
                'verb', v_ledger_event.event_verb,
                'user', v_ledger_event.user_name,
                'proof_hash', v_ledger_event.proof_hash
            )
            ELSE NULL END,
        'confirmation', CASE WHEN v_confirmation IS NOT NULL THEN
            jsonb_build_object(
                'id', v_confirmation.id,
                'headline', v_confirmation.confirmation_headline,
                'timestamp', v_confirmation.created_at
            )
            ELSE NULL END,
        'action_history', CASE WHEN v_action_history IS NOT NULL THEN
            jsonb_build_object(
                'summary', v_action_history.action_summary,
                'timestamp', v_action_history.action_timestamp
            )
            ELSE NULL END,
        'message', CASE
            WHEN v_ledger_event IS NOT NULL THEN 'Action verified in ledger'
            ELSE 'No record found'
        END
    );
END;
$$;

GRANT EXECUTE ON FUNCTION public.verify_action_proof TO authenticated;
```

---

## PART 3: TRIGGERS

### 3.1 Auto-generate confirmation on mutations

```sql
-- ============================================================================
-- TRIGGER: Auto-generate confirmation for work orders
-- ============================================================================

CREATE OR REPLACE FUNCTION public.trigger_work_order_confirmation()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_action_type TEXT;
    v_context JSONB;
BEGIN
    -- Determine action type
    IF TG_OP = 'INSERT' THEN
        v_action_type := 'create';
        v_context := jsonb_build_object(
            'number', NEW.number,
            'status', NEW.status,
            'priority', NEW.priority
        );
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
            v_action_type := 'complete';
        ELSE
            v_action_type := 'update';
        END IF;
        v_context := jsonb_build_object(
            'number', NEW.number,
            'status_change', jsonb_build_object('from', OLD.status, 'to', NEW.status)
        );
    END IF;

    -- Generate confirmation (async or inline based on performance needs)
    PERFORM generate_confirmation(
        p_yacht_id := NEW.yacht_id,
        p_action_type := v_action_type,
        p_entity_type := 'work_order',
        p_entity_id := NEW.id,
        p_entity_display_name := 'Work Order #' || NEW.number,
        p_domain := 'Work Orders',
        p_context := v_context,
        p_ledger_event_id := NEW.last_ledger_event_id
    );

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_work_order_confirmation ON public.pms_work_orders;
CREATE TRIGGER trg_work_order_confirmation
    AFTER INSERT OR UPDATE ON public.pms_work_orders
    FOR EACH ROW
    EXECUTE FUNCTION trigger_work_order_confirmation();
```

---

## PART 4: API CONTRACT

### 4.1 Confirmation Response Format

```typescript
// Every mutation API response must include confirmation

interface MutationResponse<T> {
  success: boolean;
  data: T;

  // REQUIRED: Confirmation for UI display
  confirmation: {
    confirmation_id: string;
    headline: string;           // "Work Order Created"
    details: {
      what_changed: string;     // "Work Order #WO-2024-001"
      when: string;             // ISO timestamp
      who: string;              // "John Smith"
      where_recorded: string;   // "Ledger, Work Orders"
    };
    proof_statement: string;    // "Logged • Attributed • Retrievable"
    available_actions: Array<{
      id: string;
      label: string;
    }>;
    display_duration_ms: number;
    auto_dismiss: boolean;
    ledger_event_id?: string;
  };
}

// UI must render confirmation showing:
// ✓ {headline}
// {what_changed}
// {proof_statement}
//
// [Action Button 1] [Action Button 2]
```

### 4.2 Frontend Confirmation Component Requirements

```typescript
// Frontend confirmation component MUST:

interface ConfirmationRequirements {
  // 1. Display immediately after mutation (< 100ms)
  immediateDisplay: true;

  // 2. Show proof statement prominently
  proofStatementVisible: true;

  // 3. Never disappear without trace
  // (always accessible via "recent actions" even after dismiss)
  persistInHistory: true;

  // 4. Offer follow-up actions
  showAvailableActions: true;

  // 5. No celebration/animation (professional, calm)
  noAnimations: true;

  // 6. Calm color scheme (not red/green success/failure)
  neutralColors: true;
}
```

---

## PART 5: VALIDATION CHECKLIST

Before deployment, verify:

- [ ] `action_confirmations` table created
- [ ] `confirmation_templates` seeded with all action types
- [ ] `user_action_history` captures all mutations
- [ ] `generate_confirmation()` returns proper structure
- [ ] `get_my_recent_actions()` returns today's actions
- [ ] `verify_action_proof()` links to ledger event
- [ ] Triggers auto-generate confirmations for work orders
- [ ] Triggers auto-generate confirmations for faults
- [ ] Triggers auto-generate confirmations for inventory
- [ ] UI displays confirmation within 100ms of mutation
- [ ] Confirmation shows proof statement
- [ ] "What did I do today" query returns accurate results
- [ ] No celebratory animations or color explosions

---

## RELATED DOCUMENTS

- `04-habits-cues-rewards.md` - UX requirements source
- `03-interlocutor-model.md` - Behavioral model
- `IMPL_02_ledger_proof.sql.md` - Ledger integration
