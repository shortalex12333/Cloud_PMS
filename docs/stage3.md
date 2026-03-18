             
                                                                                                                                         
⏺ Stage 3 — Execution (Actions)                                                            
                                                                                           
  Stage 2 is now complete: all 12 entity endpoints return data, all 12 lenses can display it. A crew member can search, click a result,  
  and see the full entity detail. Stage 3 is what happens next — they do something about it.                                             
                                                                                                                                         
  ---                                                                                                                                    
  What It Is                                   

  From within any open lens, crew members take state-changing actions against the entity they're looking at. These are not navigation
  events. They are mutations that write to the database, trigger side effects, and leave an audit trail.

  Examples of what stage 3 looks like in practice:

  - Chief engineer opens a fault → clicks "Create Work Order" → a work order is generated, linked to the fault, assigned to a department
  - Captain opens a work order → clicks "Mark Complete" → status flips to completed, audit log entry written, handover item optionally
  created
  - Bosun opens a parts lens → clicks "Log Usage" → quantity_on_hand decremented, usage logged against the work order it was consumed for
  - Chief stewardess opens a shopping list item → clicks "Approve" → item promoted to pms_parts, status updated, notification triggered
  - Engineer opens a certificate → clicks "Supersede" → existing cert marked superseded, new cert created in its place

  ---
  The Three-Phase Lifecycle

  Every action follows the same pattern, enforced by p0_actions_routes.py:

  GET  /prefill?{entity_type}_id={id}
         ↓ returns current entity state, pre-populated form fields, available choices
  POST /prepare
         ↓ validates inputs, dry-runs the mutation, returns preview of impact + confirmation token
  POST /execute
         ↓ commits the mutation, writes audit log, returns updated entity state

  This is not accidental — it maps to how maritime operations actually work. An action that changes vessel state (decommissioning
  equipment, closing a fault, signing off hours of rest) needs a preview step so the user can confirm before committing. Some actions
  also require a signature (PIN + timestamp hash), enforced at the prepare phase.

  ---
  What's Already Built

  The scaffolding for stage 3 is largely in place. This is not starting from zero:

  Backend — p0_actions_routes.py (307KB): The unified action router exists. It handles the prefill/prepare/execute lifecycle for work
  orders (create, add note, add part, mark complete, assign, close), faults (report, acknowledge, close, reopen), parts (consume, adjust
  stock), handover (add item, export, sign), receiving (accept, reject), shopping list (approve, reject, promote to part). Most of the DB
   mutations are written.

  Frontend — 12 action hooks (use*Actions.ts): One per lens, each defining what actions are available, what modals they open, what the
  confirmation UI looks like, and which API endpoints they call. Work order has 9. Fault has 5. Certificate has 2. The hooks exist. The
  modals mostly exist.

  Configuration — lens_matrix.json: 87 actions defined with required_fields, optional_fields, role_restricted flags, and
  requires_signature flags. This is the source of truth for what's allowed and under what conditions.

  ---
  What Stage 3 Actually Involves

  The work is wiring and hardening, not building from scratch. The gaps are:

  1. Some actions are defined in lens_matrix.json but have no backend handler — the frontend hook calls an endpoint that doesn't exist
  yet. These will return 404.
  2. Some actions have backend handlers but aren't registered in p0_actions_routes.py — the function exists in a handler class, the route
   decorator is missing.
  3. Role gating needs verification — some actions are marked role_restricted: ["captain", "hod"] in the matrix but the backend may not
  enforce this consistently. The service key bypasses Supabase RLS, so the API must do its own role check. Some endpoints do this, some
  don't.
  4. Signature flow needs end-to-end testing — the frontend generates a confirmation token, the backend validates it. This has been built
   in pieces across several branches. Whether it's coherent end-to-end against all signed actions is unknown.
  5. Audit trail completeness — every mutation is supposed to write to pms_audit_log. Some do. Some don't. Stage 3 is where this gets
  verified action by action.

  ---
  The Shape of Stage 3 Work

  Same discipline as stage 2: test first, fix second, document third. Per-action:

  1. Click the action button in the running frontend
  2. Observe what happens (modal appears? 404? 500? form submits? success?)
  3. Check the DB for the expected mutation
  4. Check pms_audit_log for the audit entry
  5. Check role enforcement (try the same action as a crew role — should be blocked for restricted actions)
  6. Fix whatever is broken
  7. Update the per-lens VERIFY.md in docs/superpowers/agents/

  The engineer left DATA.md and VERIFY.md per lens in docs/superpowers/agents/ — those documents define what each action should do and
  how to verify it. Stage 3 is executing those checklists.

  ★ Insight ─────────────────────────────────────
  Stage 3 is where the product becomes a tool rather than a dashboard. Stages 1 and 2 are read-only — search and display. Stage 3 is
  where crew can close a fault, consume a part, or sign off rest hours without leaving the interface. The three-phase action lifecycle
  (prefill → prepare → execute) is specifically designed for maritime compliance: every mutation is previewed before commit, and every
  commit is audit-logged. This is not UX polish — it's a regulatory requirement for MLC 2006 and ISM Code compliance.
