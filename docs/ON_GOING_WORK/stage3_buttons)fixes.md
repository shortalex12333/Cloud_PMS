───────────────────────────────────────

  ---
  Shard-33 Review

  REAL BUG — callAction sends yacht_id in the wrong field

  shard-33 helpers.ts:
  JSON.stringify({ action, payload: { ...payload, yacht_id: yachtId } })

  shard-34 callActionDirect:
  JSON.stringify({ action, context: { yacht_id: RBAC_CONFIG.yachtId, ...contextOverrides }, payload })

  The API contract is { action, context: { yacht_id }, payload }. Shard-33 puts yacht_id inside payload, not context. The
  engineer noticed this when building shard-34 and fixed it — but never went back to fix shard-33.

  This means every shard-33 action call is sending the tenant identifier to the wrong field. If the handlers are returning 200,
  one of three things is true:
  - (a) handlers fall back to payload.yacht_id silently, OR
  - (b) yacht_id is derived from the JWT, not the body, OR
  - (c) the actions are succeeding without proper tenant scoping

  Option (c) is a silent security gap. This needs to be verified and shard-33's callAction fixed to match the contract.

  ---
  Stale test description — acknowledge_fault

  fault-actions.spec.ts test title: acknowledge-fault → 200 + status=acknowledged

  But the expect.poll asserts .toBe('investigating') — because acknowledge_fault transitions to 'investigating', not
  'acknowledged'. The assertion is correct; the test name is wrong. Same type of stale comment issue as the shard-34 docstring.

  ---
  Shared state mutation — equipment notes accumulate

  Every equipment note test (HOD + Captain) adds notes to the same shared equipment record via getExistingEquipment(). It
  reads-once, then mutations pile up across runs. Not a functional failure, but after 50 test runs the metadata.notes array will
   have 100 entries on the one shared equipment. The before-count pattern handles this correctly (comparing relative growth),
  but it's worth noting the shared equipment record is never cleaned up.

  ---
  No audit trail coverage at all

  Shard-33 has zero ledger verification. That's fine because it's a smoke layer. But it means the complete audit trail guarantee
   rests entirely on shard-34 running. The two shards need to be run together for full coverage.

  ---
  Summary Comparison

  ┌───────────────────────┬─────────────────────────────────┬─────────────────────────┐
  │                       │            Shard-33             │        Shard-34         │
  ├───────────────────────┼─────────────────────────────────┼─────────────────────────┤
  │ Purpose               │ Render smoke + basic action 200 │ 3-layer hard proof      │
  ├───────────────────────┼─────────────────────────────────┼─────────────────────────┤
  │ yacht_id placement    │ Wrong field (payload)           │ Correct (context)       │
  ├───────────────────────┼─────────────────────────────────┼─────────────────────────┤
  │ Ledger verification   │ None                            │ ✓                       │
  ├───────────────────────┼─────────────────────────────────┼─────────────────────────┤
  │ DB state verification │ Shallow (row count)             │ ✓ Specific field values │
  ├───────────────────────┼─────────────────────────────────┼─────────────────────────┤
  │ JWT strategy          │ Browser localStorage            │ Node.js minted          │
  ├───────────────────────┼─────────────────────────────────┼─────────────────────────┤
  │ Cleanup               │ ✓ (seed fixtures)               │ ✓ (seed fixtures)       │
  ├───────────────────────┼─────────────────────────────────┼─────────────────────────┤
  │ Stale descriptions    │ acknowledge-fault title         │ close_fault docstring   │
  ├───────────────────────┼─────────────────────────────────┼─────────────────────────┤
  │ RBAC advisory issue   │ Same (shared captain JWT)       │ Same                    │
  └───────────────────────┴─────────────────────────────────┴─────────────────────────┘

  ---
  What needs fixing before shipping

  1. Rotate credentials (both shards depend on rbac-fixtures.ts) — JWT secret + service key out of source
  2. Fix shard-33 callAction — move yacht_id from payload to context, match the API contract
  3. Fix update_document — either make it actually write to the DB, or rename the action to signal it's an intent-only log
  4. Fix stale test descriptions — acknowledge_fault in shard-33, close_fault docstring in shard-34
  5. Add _ACTION_ENTITY_MAP entry for transfer_part — otherwise the ledger records a nil UUID for every stock transfer
  6. Add reopen_fault ledger write — right now internal_dispatcher skips it entirely







### shard 34
  ---
  Verdict: Conditional Pass with Blockers

  Good architecture. Has real bugs, one security breach, and one fabricated claim in the handoff doc.

  ---
  BLOCKER 1 — Double credential leak in source

  helpers.ts:25 — Raw tenant JWT signing secret hardcoded:
  ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su109d2wBz8WjSNX6wc3MiEFg==

  rbac-fixtures.ts:30 — Supabase service role key hardcoded. The engineer even left a TODO SECURITY: move to env var comment and
   then left it there anyway. Both secrets are now in git history.

  These must be rotated and moved to env vars (SUPABASE_JWT_SECRET, SUPABASE_SERVICE_KEY). Not a test quality issue — a
  credential exposure issue.

  ---
  BLOCKER 2 — Stale file comment contradicts the code

  fault-actions-full.spec.ts line 7:
  *   close_fault      — requires status='acknowledged' pre-condition

  The code sets status: 'investigating' (line 75). The inline comment explains 'acknowledged' fails the CHECK constraint. The
  top-level docstring was never updated. Proof the engineer corrected the handoff doc but not the actual file. Minor but it's
  exactly the kind of thing that confuses the next person.

  ---
  BLOCKER 3 — update_document doesn't update anything

  document-actions-full.spec.ts:132 comment:
  "update_document handler intentionally does NOT write to doc_metadata"

  The test then asserts only data.status === 'success' and Array.isArray(data.updated_fields). There is no DB state check —
  because there's nothing to check.

  This is described as "by design" but it means: a user calls update_document, gets a 200, and nothing in the database changes.
  This is broken behavior. The test passes by asserting a JSON response shape, not an actual outcome. That's the exact failure
  mode the 3-layer verification pattern was designed to prevent.

  If this is truly "by design" (avoids PostgREST schema cache issues), the handler needs to either: (a) fix the schema cache
  issue so it actually writes, or (b) be explicitly called log_document_update_intent and removed from any UI that implies a
  real update.

  ---
  BLOCKER 4 — RBAC is not tested, it's advisory theater

  All three auth files (hod.json, captain.json, crew.json) use the same captain JWT. Every "crew 403" test accepts [200, 403] as
   valid. This means the RBAC enforcement guarantee is never actually tested.

  The engineer documented this honestly in the gotchas table — but accepted it as a known gap and shipped. The crew RBAC tests
  should be marked test.skip() with a clear reason until separate auth fixtures exist, not run as advisory tests that always
  pass regardless of what the API returns.

  ---
  REAL BUG — transfer_part ledger entity_id is nil

  inventory-actions-full.spec.ts:215:
  "transfer_part is NOT in _ACTION_ENTITY_MAP — the centralized ledger write fires but uses entity_id='00000000-...000'
  (fallback)"

  This isn't a test gap — the ledger row for every part transfer records a nil UUID as the entity. The audit trail for transfers
   is broken in production. The engineer noted it and skipped the ledger poll. This needs a backend fix (_ACTION_ENTITY_MAP
  entry for transfer_part), not just a test accommodation.

  ---
  REAL BUG — reopen_fault writes nothing to ledger

  reopen_fault routes through internal_dispatcher and writes no ledger_events row. An action that mutates entity status but
  leaves no audit trail is an audit completeness failure. Same as transfer_part — documented and skipped rather than fixed.

  ---
  Smaller Issues (not blockers)

  - pollLedger is copy-pasted 4 times across spec files. Should live in helpers.ts. One edit to update it, four places that
  diverge.
  - supersede_certificate advisory accepts 200 (line 195). If the signed action gate is broken and returns 200 without a
  signature, this test passes. The test should reject 200 explicitly — that's a security bypass, not a benign advisory case.
  - getPartWithLocation structural confusion: the column is named location (string), aliased as location_id in the fixture
  return. Works if the handler accepts a string location name, but the naming is confusing and could break silently if the
  schema changes.
  - pms_vessel_certificates vs pms_certificates: Entity endpoint reads from pms_certificates (fixed in Stage 2). Certificate
  actions write to pms_vessel_certificates. These should be verified to be different tables by design, not an inconsistency.

  ---
  Summary

  ┌────────────────────────────────────┬──────────┬──────────────────────────────────┐
  │              Finding               │ Severity │              Status              │
  ├────────────────────────────────────┼──────────┼──────────────────────────────────┤
  │ JWT secret + service key in source │ CRITICAL │ Must rotate + move to env        │
  ├────────────────────────────────────┼──────────┼──────────────────────────────────┤
  │ Stale docstring in fault spec      │ Low      │ Fix the comment                  │
  ├────────────────────────────────────┼──────────┼──────────────────────────────────┤
  │ update_document no-ops silently    │ HIGH     │ Backend fix needed               │
  ├────────────────────────────────────┼──────────┼──────────────────────────────────┤
  │ RBAC crew tests are advisory       │ HIGH     │ Skip or fix auth fixtures        │
  ├────────────────────────────────────┼──────────┼──────────────────────────────────┤
  │ transfer_part ledger nil UUID      │ MEDIUM   │ Backend fix (_ACTION_ENTITY_MAP) │
  ├────────────────────────────────────┼──────────┼──────────────────────────────────┤
  │ reopen_fault no ledger row         │ MEDIUM   │ Backend fix                      │
  ├────────────────────────────────────┼──────────┼──────────────────────────────────┤
  │ pollLedger copy-pasted 4x          │ Low      │ Extract to helpers.ts            │
  ├────────────────────────────────────┼──────────┼──────────────────────────────────┤
  │ supersede_certificate accepts 200  │ MEDIUM   │ Change to expect([400, 403])     │
  └────────────────────────────────────┴──────────┴──────────────────────────────────┘
