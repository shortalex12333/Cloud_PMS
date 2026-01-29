# Receiving Lens v1 - Zero→Gold Plan

**Lens ID**: `receiving`
**Domain**: `receiving`
**Priority**: #1 (after Shopping List canary stabilization)
**Status**: Planning Phase
**Date**: 2026-01-28

**Rationale**: Receiving Lens ties directly to Shopping List ("request → order → receive" loop) and accelerates procurement workflow.

---

## Zero→Gold Phases

### Phase 0: Spec & DB Truth

**Goal**: Extract schema, define actions, document scenarios

**Tasks**:
1. **Database Schema Extraction**:
   ```sql
   -- Query Supabase for receiving-related tables
   SELECT table_name, column_name, data_type, is_nullable
   FROM information_schema.columns
   WHERE table_schema = 'public'
     AND table_name LIKE '%receiving%' OR table_name LIKE '%delivery%'
   ORDER BY table_name, ordinal_position;
   ```

2. **Define Core Actions**:
   - `create_receiving_record` (MUTATE) - Log incoming shipment
   - `mark_items_received` (MUTATE) - Update received quantities
   - `reject_items` (MUTATE) - Record damaged/incorrect items
   - `match_to_purchase_order` (MUTATE) - Link receiving to PO
   - `view_receiving_history` (READ) - Audit trail

3. **Required Fields Mapping**:
   | Action | Required Fields | Optional Fields | Variant |
   |--------|----------------|----------------|---------|
   | create_receiving_record | yacht_id, shipment_date, supplier | tracking_number, notes | MUTATE |
   | mark_items_received | receiving_id, item_id, quantity_received | condition | MUTATE |
   | reject_items | receiving_id, item_id, rejection_reason | quantity_rejected | MUTATE |
   | match_to_purchase_order | receiving_id, purchase_order_id | | MUTATE |
   | view_receiving_history | receiving_id | | READ |

4. **Scenarios & Edge Cases**:
   - Partial receipt (ordered 10, received 7)
   - Damaged goods (reject and update inventory)
   - Wrong items delivered (reject and re-order)
   - Advance shipment (received before PO finalized)
   - Backorder handling (multiple partial receipts)

5. **Error Mapping** (4xx/5xx):
   - 400 `invalid_quantity` - quantity_received > quantity_ordered
   - 400 `missing_purchase_order` - Cannot match to non-existent PO
   - 403 `permission_denied` - Only HOD/Manager can approve receipts
   - 404 `receiving_record_not_found` - Invalid receiving_id
   - 500 `database_error` - DB write failed

**Deliverables**:
- [ ] `docs/architecture/30_RECEIVING_LENS/RECEIVING_LENS_V1_SPEC.md`
- [ ] Database schema documented (tables, columns, FKs)
- [ ] Action catalog draft (5 actions with fields)
- [ ] Scenarios spreadsheet (10+ test cases)

**Duration**: 2-3 hours

---

### Phase 1: Registry & Suggestions

**Goal**: Add actions to registry, implement `/list` and `/suggestions` endpoints

**Tasks**:
1. **Action Registry** (`apps/api/main.py`):
   ```python
   ActionDefinition(
       action_id="create_receiving_record",
       domain="receiving",
       variant=ActionVariant.MUTATE,
       allowed_roles=["crew", "deckhand", "steward", "engineer", "eto",
                     "chief_officer", "chief_engineer", "purser", "captain", "manager"],
       keywords=["receiving", "shipment", "delivery", "goods"],
       required_fields=["yacht_id", "shipment_date", "supplier"],
       storage_options={"photos": True, "documents": True}
   ),
   # ... add other actions ...
   ```

2. **Suggestions Logic** (`apps/api/handlers/receiving_handlers.py`):
   ```python
   def get_receiving_suggestions(yacht_id: str) -> List[ActionCandidate]:
       # Query for:
       # - Purchase orders awaiting receipt
       # - Partial receipts needing completion
       # - Recent shopping list items (approved → ordered → receiving)
       pass
   ```

3. **Role Gating**:
   - All authenticated users can create receiving records
   - HOD/Manager required to approve receipts
   - Engineers can match to purchase orders

4. **Context Gating**:
   - `yacht_id` required in all actions
   - Suggestions scoped to user's yacht

**Deliverables**:
- [ ] 5 actions added to registry
- [ ] Suggestions handler implemented
- [ ] Role gating enforced (Router layer)
- [ ] Test: `GET /v1/actions/list?domain=receiving` returns 5 actions
- [ ] Test: `POST /v1/actions/suggestions` returns candidates

**Duration**: 3-4 hours

---

### Phase 2: Handlers & Execute

**Goal**: Implement action handlers with strict 4xx mapping, tenant-scoped role resolution

**Tasks**:
1. **Handler Implementations**:
   - `create_receiving_record_handler()` - Insert into `pms_receiving_records`
   - `mark_items_received_handler()` - Update `pms_receiving_items` + inventory
   - `reject_items_handler()` - Insert into `pms_rejected_items`
   - `match_to_purchase_order_handler()` - Link receiving_id ↔ po_id
   - `view_receiving_history_handler()` - Query state_history table

2. **Strict 4xx Mapping**:
   ```python
   # Example: mark_items_received
   if quantity_received > quantity_ordered:
       return 400, {"error_code": "invalid_quantity",
                    "message": "Cannot receive more than ordered"}

   if not is_hod(user_id, yacht_id):
       return 403, {"error_code": "permission_denied",
                    "message": "Only HOD can approve receipts"}
   ```

3. **Tenant-Scoped Role Resolution**:
   ```python
   def is_receiver(user_id: str, yacht_id: str) -> bool:
       """Check if user can create receiving records."""
       # All authenticated users in yacht can receive
       return get_user_yacht_id(user_id) == yacht_id

   def is_receiving_approver(user_id: str, yacht_id: str) -> bool:
       """Check if user can approve receipts (HOD/Manager)."""
       return is_hod(user_id, yacht_id)
   ```

4. **Audit Invariant**:
   - All MUTATE actions write to `pms_receiving_state_history`
   - No SIGNED actions (no signature validation needed)

**Deliverables**:
- [ ] 5 handlers implemented in `apps/api/handlers/receiving_handlers.py`
- [ ] Strict 4xx error mapping (400/403/404)
- [ ] Role checks in handlers (defense-in-depth Layer 2)
- [ ] Audit logs to state_history table
- [ ] Test: `POST /v1/actions/execute` with valid payload → 200
- [ ] Test: Invalid payload → 400 with error_code
- [ ] Test: CREW approval attempt → 403

**Duration**: 6-8 hours

---

### Phase 3: RLS & Storage Migrations

**Goal**: Apply RLS policies, add storage prefixes, create helper functions

**Tasks**:
1. **Helper Functions** (`supabase/migrations/...`):
   ```sql
   CREATE OR REPLACE FUNCTION is_receiving_approver(p_user_id uuid, p_yacht_id uuid)
   RETURNS boolean
   LANGUAGE plpgsql
   SECURITY DEFINER
   AS $$
   BEGIN
       -- Check if user is HOD/Manager for yacht
       RETURN is_hod(p_user_id, p_yacht_id);
   END;
   $$;
   ```

2. **RLS Policies**:
   ```sql
   -- Allow all yacht members to SELECT receiving records
   CREATE POLICY yacht_scoped_receiving_select
   ON pms_receiving_records FOR SELECT
   USING (yacht_id = get_user_yacht_id(auth.uid()));

   -- Allow all yacht members to INSERT receiving records
   CREATE POLICY yacht_scoped_receiving_insert
   ON pms_receiving_records FOR INSERT
   WITH CHECK (yacht_id = get_user_yacht_id(auth.uid()));

   -- Only HOD can UPDATE receiving records (approve)
   CREATE POLICY hod_receiving_update
   ON pms_receiving_records FOR UPDATE
   USING (
       yacht_id = get_user_yacht_id(auth.uid())
       AND is_receiving_approver(auth.uid(), yacht_id)
   );

   -- Deny DELETE (audit requirement)
   CREATE POLICY deny_receiving_delete
   ON pms_receiving_records FOR DELETE
   USING (false);
   ```

3. **Storage Prefixes**:
   ```sql
   -- Photo uploads: /receiving/{yacht_id}/{receiving_id}/photos/
   -- Documents: /receiving/{yacht_id}/{receiving_id}/documents/
   CREATE POLICY yacht_scoped_receiving_storage
   ON storage.objects FOR INSERT
   WITH CHECK (
       bucket_id = 'pms-attachments'
       AND name LIKE 'receiving/' || get_user_yacht_id(auth.uid())::text || '/%'
   );
   ```

4. **DELETE Restrictions**:
   - No DELETE policy (audit trail must be preserved)
   - Soft delete via `deleted_at` column if needed

**Deliverables**:
- [ ] RLS policies migration file (`20260129_receiving_rls.sql`)
- [ ] Helper functions: `is_receiving_approver()`
- [ ] Storage policies for photo/document uploads
- [ ] Applied to staging DB
- [ ] Test: Direct SQL INSERT bypasses role check (service_role)
- [ ] Test: Authenticated user INSERT respects yacht_id
- [ ] Test: CREW UPDATE fails (0 rows updated)

**Duration**: 4-5 hours

---

### Phase 4: Docker RLS Tests

**Goal**: Validate RLS policies in isolated Docker environment

**Tasks**:
1. **Test Coverage** (18+ tests):
   - **Role & CRUD** (8 tests):
     - CREW create → success
     - CREW approve → denied (0 rows updated)
     - HOD approve → success
     - HOD reject → success
     - Cross-yacht denial
   - **Isolation** (4 tests):
     - Anonymous access denied
     - Cross-yacht filtering
     - Yacht-scoped SELECT
   - **Edge** (6 tests):
     - Invalid quantity validation
     - Double approval prevention
     - Missing PO rejection

2. **0×500 Enforcement**:
   - All tests must return 2xx/4xx (no 5xx)
   - Citation: `testing_success_ci:cd.md:249`

3. **Evidence Artifacts**:
   - Full DDL snippets
   - Before/after DB state
   - HTTP transcripts (if via API)
   - Citation: `testing_success_ci:cd.md:815`

**Deliverables**:
- [ ] `tests/docker/run_receiving_rls_tests.py`
- [ ] 18/18 tests passing
- [ ] Evidence: `docs/pipeline/receiving_lens/PHASE3_DOCKER_RLS_RESULTS.md`
- [ ] 0×500 requirement met

**Duration**: 4-6 hours

---

### Phase 5: Staging Acceptance

**Goal**: Validate against live staging API

**Tasks**:
1. **Test Coverage** (9+ tests):
   - Action list filtering (CREW vs HOD)
   - CREW operations (create=200, approve=403)
   - HOD operations (approve=200, reject=200)
   - Storage denial tests (if applicable)

2. **MUTATE Role Gating** (not SIGNED):
   - Receiving Lens has no SIGNED actions
   - Focus on role-based permissions (CREW vs HOD)

**Deliverables**:
- [ ] `tests/ci/staging_receiving_acceptance.py`
- [ ] 9/9 tests passing
- [ ] Evidence: `docs/pipeline/receiving_lens/PHASE4_STAGING_ACCEPTANCE_RESULTS.md`
- [ ] 0×500 requirement met

**Duration**: 3-4 hours

---

### Phase 6: Stress Tests

**Goal**: Validate performance under load

**Tasks**:
1. **Concurrent Requests**:
   - 50× `/list` + 30× `/execute` (create_receiving_record)
   - Measure P50/P95/P99 latencies

2. **0×500 Enforcement**:
   - Zero 5xx errors required
   - Status breakdown (200/403/404 counts)

**Deliverables**:
- [ ] `tests/stress/receiving_actions_endpoints.py`
- [ ] Performance report (P50/P95/P99)
- [ ] 0×500 requirement met
- [ ] PASS verdict

**Duration**: 2-3 hours

---

### Phase 7: Feature Flags + Docs

**Goal**: Add feature flags, document toggle procedures

**Tasks**:
1. **Feature Flag** (`apps/api/integrations/feature_flags.py`):
   ```python
   RECEIVING_LENS_V1_ENABLED = os.getenv('RECEIVING_LENS_V1_ENABLED', 'false').lower() == 'true'

   def check_receiving_lens_feature() -> tuple[bool, str]:
       if not RECEIVING_LENS_V1_ENABLED:
           return False, "Receiving Lens v1 is disabled (canary flag off)"
       return True, ""
   ```

2. **503 FEATURE_DISABLED**:
   - When flag OFF: `/v1/actions/list?domain=receiving` → 503
   - When flag ON: `/v1/actions/list?domain=receiving` → 200

3. **Toggle/Rollback Docs**:
   - Enable: `RECEIVING_LENS_V1_ENABLED=true` in Render
   - Disable: `RECEIVING_LENS_V1_ENABLED=false` (rollback)

**Deliverables**:
- [ ] Feature flag added to code (default OFF)
- [ ] `docs/pipeline/RECEIVING_FEATURE_FLAGS.md`
- [ ] Toggle procedures documented
- [ ] Rollback tested (503 response)

**Duration**: 2 hours

---

### Phase 8: Ops Health

**Goal**: Add health monitoring infrastructure

**Tasks**:
1. **Ops Tables Migration**:
   - Use existing `pms_health_checks` and `pms_health_events` tables
   - Add `lens_id='receiving'` rows

2. **Health Worker**:
   - Copy template: `tools/ops/monitors/receiving_health_worker.py`
   - Configure: `LENS_ID="receiving"`, `DOMAIN="receiving"`
   - Checks: service health, feature flags, list, suggestions, create

3. **Add to `render.yaml`**:
   ```yaml
   - type: worker
     name: receiving-health-worker
     runtime: python
     plan: starter
     region: oregon
     branch: main
     buildCommand: pip install requests PyJWT
     startCommand: python tools/ops/monitors/receiving_health_worker.py
     autoDeploy: true
   ```

4. **Optional `/v1/ops/health` Endpoint**:
   - Query latest health check from DB
   - Return status/latency/error_rate

**Deliverables**:
- [ ] Health worker created
- [ ] Added to `render.yaml`
- [ ] Test: Worker writes to `pms_health_checks`
- [ ] Evidence: First health check row in DB

**Duration**: 2-3 hours

---

### Phase 9: Canary Rollout

**Goal**: Enable canary flag, monitor 24h, gradual rollout

**Tasks**:
1. **Enable Canary Flag** (Staging):
   ```yaml
   # render.yaml
   - key: RECEIVING_LENS_V1_ENABLED
     value: "true"
   ```

2. **24h Observation**:
   - Monitor health checks every 15 minutes
   - Alert on 5xx errors (0×500 requirement)
   - Check P99 latency < 10s
   - Check error rate < 1%

3. **Expand Rollout**:
   - Production canary (1 yacht) → 7 days
   - 10% → 50% → 100% with monitoring

**Deliverables**:
- [ ] Canary flag enabled
- [ ] 24h monitoring logs
- [ ] Smoke test passed (8/8)
- [ ] MUTATE role acceptance passed (7/7)
- [ ] Health worker stable
- [ ] 0×500 requirement met

**Duration**: 24 hours + monitoring

---

### Phase 10: Final Sign-Off

**Goal**: Consolidate evidence, archive drafts, canary summary

**Tasks**:
1. **Evidence v2 Document**:
   - `docs/architecture/30_RECEIVING_LENS/RECEIVING_LENS_V1.md`
   - Consolidate: spec, actions, schema, RLS, tests, deployment

2. **Archived Drafts**:
   - Move v1 drafts to `archived/`
   - Keep only final v2 docs

3. **Flags OFF in Main**:
   - Verify: `RECEIVING_LENS_V1_ENABLED` default is `false` in code
   - Only enabled via env var

4. **Canary Summary**:
   - `docs/pipeline/receiving_lens/PHASE5_STAGING_CANARY_SUMMARY.md`
   - Include: flags ON proof, smoke transcripts, health check results

**Deliverables**:
- [ ] Final documentation (architecture, catalog, flowcharts, handoff)
- [ ] Evidence consolidated
- [ ] Drafts archived
- [ ] Canary summary complete
- [ ] Ready for production rollout

**Duration**: 3-4 hours

---

## Integration with Shopping List Lens

### Workflow Connection

**Request → Order → Receive Loop**:
1. Shopping List: `create_shopping_list_item` (CREW)
2. Shopping List: `approve_shopping_list_item` (HOD)
3. **Purchase Order**: Create PO from approved items (external system or future lens)
4. **Receiving**: `create_receiving_record` (link to PO)
5. **Receiving**: `mark_items_received` (update inventory)
6. **Inventory**: Update stock levels (Inventory Lens integration)

### Data Dependencies

**Tables**:
- `pms_shopping_list_items` (Shopping List Lens)
  - `approved_at` → triggers PO creation
- `pms_purchase_orders` (future or external)
  - `po_id` → linked to receiving record
- `pms_receiving_records` (Receiving Lens)
  - `purchase_order_id` FK to PO
  - `received_at` → triggers inventory update
- `pms_inventory` (Inventory Lens)
  - `quantity_on_hand` updated via receiving

### Suggestions Integration

**Receiving Suggestions**:
```python
def get_receiving_suggestions(yacht_id: str) -> List[ActionCandidate]:
    # Query approved shopping list items
    approved_items = query_approved_shopping_list_items(yacht_id)

    # Query pending purchase orders
    pending_pos = query_pending_purchase_orders(yacht_id)

    # Generate candidates
    candidates = []
    for po in pending_pos:
        candidates.append({
            "action": "create_receiving_record",
            "context": {"purchase_order_id": po.id},
            "suggested_fields": {
                "supplier": po.supplier,
                "shipment_date": "today",
                "items": po.items
            }
        })

    return candidates
```

---

## Estimated Timeline

**Total Duration**: ~35-45 hours (5-6 business days)

**Week 1**: Phases 0-3 (Spec, Registry, Handlers, RLS)
**Week 2**: Phases 4-7 (Tests, Flags, Docs)
**Week 3**: Phases 8-10 (Ops Health, Canary, Sign-Off)

**Parallelization Opportunities**:
- Phase 1 + Phase 0 (registry while finalizing spec)
- Phase 4 + Phase 5 (Docker tests + Staging tests)
- Phase 7 + Phase 8 (Flags + Health worker)

---

## Risk Mitigation

**Risk 1: Purchase Order Schema Unknown**
- Mitigation: Research PO table schema in Phase 0
- Fallback: Soft FK (store PO number as string, not uuid FK)

**Risk 2: Inventory Lens Not Yet Implemented**
- Mitigation: Stub inventory updates (log only, no actual stock changes)
- Fallback: Manual inventory reconciliation

**Risk 3: Complex Receiving Scenarios**
- Mitigation: Start with simple scenarios (full receipt, single supplier)
- Expand later: Partial receipts, backorders, multi-supplier

---

## Success Criteria

- [ ] 5 actions registered and functional
- [ ] 100% test pass rate (Docker + Staging + Stress)
- [ ] 0×500 requirement met (zero 5xx errors)
- [ ] Defense-in-depth security (Router + Handler + RLS)
- [ ] Feature flag working (OFF → 503, ON → 200)
- [ ] Health monitoring active (15-minute checks)
- [ ] 24h canary stable (0 errors, P99 < 10s, error_rate < 1%)
- [ ] Documentation complete (architecture, catalog, flowcharts, handoff)

---

**Next**: After Shopping List canary stabilizes (7 days), begin Receiving Lens Phase 0

**Priority**: #1 (accelerates "request → order → receive" loop)
