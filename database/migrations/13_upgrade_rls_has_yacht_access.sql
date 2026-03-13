-- Migration 13: Upgrade remaining PMS tables to has_yacht_access() RLS
-- Date: 2026-03-13
-- Prerequisite: Migration 12 (has_yacht_access + prevent_yacht_id_change functions must exist)
--
-- Preflight: run in Supabase SQL Editor first:
--   SELECT proname FROM pg_proc WHERE proname IN ('has_yacht_access','prevent_yacht_id_change');
-- If prevent_yacht_id_change is missing, remove the trigger lines below or run migration 12 first.

-- ================================================================
-- PART 1: Upgrade existing PMS tables to has_yacht_access() RLS
-- ================================================================

DO $$
DECLARE
  tbl text;
  tbls text[] := ARRAY[
    'pms_work_orders',
    'pms_work_order_notes',
    'pms_work_order_parts',
    'pms_faults',
    'pms_parts',
    'pms_part_usage',
    'pms_handover',
    'pms_shopping_list_items'
  ];
BEGIN
  FOREACH tbl IN ARRAY tbls
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', tbl);

    -- Drop old policies (any name pattern)
    EXECUTE format('DROP POLICY IF EXISTS "%s_select_yacht_scope" ON public.%I', tbl, tbl);
    EXECUTE format('DROP POLICY IF EXISTS "%s_insert_yacht_scope" ON public.%I', tbl, tbl);
    EXECUTE format('DROP POLICY IF EXISTS "%s_update_yacht_scope" ON public.%I', tbl, tbl);
    EXECUTE format('DROP POLICY IF EXISTS "%s_delete_yacht_scope" ON public.%I', tbl, tbl);
    -- Also drop legacy name variants
    EXECUTE format('DROP POLICY IF EXISTS "Users can view %s on their yacht" ON public.%I', tbl, tbl);

    -- Create new policies using has_yacht_access()
    EXECUTE format(
      'CREATE POLICY "%s_select_yacht_scope" ON public.%I FOR SELECT TO authenticated USING (public.has_yacht_access(yacht_id))',
      tbl, tbl
    );
    EXECUTE format(
      'CREATE POLICY "%s_insert_yacht_scope" ON public.%I FOR INSERT TO authenticated WITH CHECK (public.has_yacht_access(yacht_id))',
      tbl, tbl
    );
    EXECUTE format(
      'CREATE POLICY "%s_update_yacht_scope" ON public.%I FOR UPDATE TO authenticated USING (public.has_yacht_access(yacht_id)) WITH CHECK (public.has_yacht_access(yacht_id))',
      tbl, tbl
    );
    EXECUTE format(
      'CREATE POLICY "%s_delete_yacht_scope" ON public.%I FOR DELETE TO authenticated USING (public.has_yacht_access(yacht_id))',
      tbl, tbl
    );

    -- Add immutability trigger (requires prevent_yacht_id_change function from migration 12)
    EXECUTE format('DROP TRIGGER IF EXISTS trg_prevent_yacht_id_change ON public.%I', tbl);
    EXECUTE format(
      'CREATE TRIGGER trg_prevent_yacht_id_change BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.prevent_yacht_id_change()',
      tbl
    );

    RAISE NOTICE 'Upgraded RLS for: %', tbl;
  END LOOP;
END $$;

-- ================================================================
-- PART 2: Tables that need RLS added from scratch
-- ================================================================

-- pms_receiving
ALTER TABLE public.pms_receiving ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_receiving FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "pms_receiving_select_yacht_scope" ON public.pms_receiving;
DROP POLICY IF EXISTS "pms_receiving_insert_yacht_scope" ON public.pms_receiving;
DROP POLICY IF EXISTS "pms_receiving_update_yacht_scope" ON public.pms_receiving;
DROP POLICY IF EXISTS "pms_receiving_delete_yacht_scope" ON public.pms_receiving;

CREATE POLICY "pms_receiving_select_yacht_scope" ON public.pms_receiving
  FOR SELECT TO authenticated USING (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_receiving_insert_yacht_scope" ON public.pms_receiving
  FOR INSERT TO authenticated WITH CHECK (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_receiving_update_yacht_scope" ON public.pms_receiving
  FOR UPDATE TO authenticated USING (public.has_yacht_access(yacht_id)) WITH CHECK (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_receiving_delete_yacht_scope" ON public.pms_receiving
  FOR DELETE TO authenticated USING (public.has_yacht_access(yacht_id));

-- pms_purchase_orders
ALTER TABLE public.pms_purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_purchase_orders FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "pms_purchase_orders_select_yacht_scope" ON public.pms_purchase_orders;
DROP POLICY IF EXISTS "pms_purchase_orders_insert_yacht_scope" ON public.pms_purchase_orders;
DROP POLICY IF EXISTS "pms_purchase_orders_update_yacht_scope" ON public.pms_purchase_orders;
DROP POLICY IF EXISTS "pms_purchase_orders_delete_yacht_scope" ON public.pms_purchase_orders;

CREATE POLICY "pms_purchase_orders_select_yacht_scope" ON public.pms_purchase_orders
  FOR SELECT TO authenticated USING (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_purchase_orders_insert_yacht_scope" ON public.pms_purchase_orders
  FOR INSERT TO authenticated WITH CHECK (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_purchase_orders_update_yacht_scope" ON public.pms_purchase_orders
  FOR UPDATE TO authenticated USING (public.has_yacht_access(yacht_id)) WITH CHECK (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_purchase_orders_delete_yacht_scope" ON public.pms_purchase_orders
  FOR DELETE TO authenticated USING (public.has_yacht_access(yacht_id));

-- ledger_events (read-only for authenticated, inserts via service role only)
ALTER TABLE public.ledger_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ledger_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ledger_events_select_yacht_scope" ON public.ledger_events;
DROP POLICY IF EXISTS "ledger_events_insert_service_only" ON public.ledger_events;

CREATE POLICY "ledger_events_select_yacht_scope" ON public.ledger_events
  FOR SELECT TO authenticated USING (public.has_yacht_access(yacht_id));
-- Inserts only via service_role (API writes, never direct from browser):
CREATE POLICY "ledger_events_insert_service_only" ON public.ledger_events
  FOR INSERT TO service_role WITH CHECK (true);

-- ================================================================
-- PART 3: Expand ledger_events check constraints
-- Adds 'view' to valid_event_type (for future direct use)
-- Adds 'read_beacon' to valid_source_context (for explicit beacon labelling)
-- ================================================================

ALTER TABLE public.ledger_events
  DROP CONSTRAINT IF EXISTS valid_event_type;
ALTER TABLE public.ledger_events
  ADD CONSTRAINT valid_event_type CHECK (event_type IN (
    'create', 'update', 'delete', 'status_change', 'assignment', 'approval',
    'rejection', 'escalation', 'handover', 'import', 'export', 'view'
  ));

ALTER TABLE public.ledger_events
  DROP CONSTRAINT IF EXISTS valid_source_context;
ALTER TABLE public.ledger_events
  ADD CONSTRAINT valid_source_context CHECK (source_context IN (
    'microaction', 'search', 'read_beacon', 'bulk', 'system'
  ));

-- ================================================================
-- PART 4: Indexes for role-scoped timeline queries (idempotent)
-- ================================================================

CREATE INDEX IF NOT EXISTS idx_ledger_self
  ON public.ledger_events (yacht_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_dept
  ON public.ledger_events (yacht_id, department, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_entity
  ON public.ledger_events (yacht_id, entity_type, entity_id, created_at DESC);
