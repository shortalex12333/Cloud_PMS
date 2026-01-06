Below are **text-only sequence diagrams** you can paste into docs and use as the contract between backend + frontend. They match your rules:

* universal (mobile + desktop)
* no modals
* real-time status line
* cancel/exit always visible
* entity extraction visible under search bar
* READ is frictionless
* MUTATE requires preview + signature + audit, but still inline

---

# Happy path (READ) — “show me inventory box 2D”

**Goal:** user asks → system orients → loads renderer → row actions available → no mutation.

```
User
  -> Client UI: types query "show me inventory box 2D"

Client UI
  -> API /search: POST { query, user_context, client_fingerprint }

API /search
  -> Interpret: normalize + parse intent + extract entities + map situation
  -> SQL: fetch candidates (inventory lane prioritized)
  -> Ranker: score + order results (do not collapse uncertainty)
  -> Action Attachment: for each row attach:
       - primary READ action (e.g., View / Print)
       - dropdown verbs (optional)
  -> Renderer Selection: choose InventoryTable renderer
  -> Assemble Response: stream chunks

API /search
  -> Client UI (stream):
       [status] "Interpreting..."
       [understood] entities + resolved box=2D
       [lane] Inventory (primary), other lanes collapsed
       [renderer] inventory_table payload (rows)
       [actions] per-row primary + ▼ dropdown

Client UI
  -> Renders:
       SearchBar
       UnderstoodLine (entity extraction output)
       InventoryTable (virtualized list, infinite scroll allowed)
       RowActions (primary + ▼ dropdown)

User
  -> taps row (or primary action "View")

Client UI
  -> API /actions/execute: POST { action_id="view_inventory_item", target_entity_id, request_id }

API /actions/execute (READ)
  -> Gate:
       permission ok
       context ok
       variant=READ => no signature, no diff
  -> Execute handler: read/view
  -> Audit (optional for READ): log minimal event (can be none)
  -> Return: renderer_update payload

API /actions/execute
  -> Client UI:
       [status] "Loading inventory item..."
       [update] renderer_update (inline, no new tab)

Client UI
  -> Updates beneath search:
       row detail drawer OR inline expanded view
       actions remain adjacent
       cancel closes drawer, returns to list
```

**Key alignment points**

* search returns *understood entities + renderer + actions*
* READ execution is immediate, inline, cancellable UI-wise
* no modal confirmation
* no deep reasoning surfaces

---

# Mutation path (MUTATE) — “reduce oil filter qty from 2 to 1”

**Goal:** user initiates a change → system shows exact diff → user signs → commit → audit log created → UI updates inline → undo if supported.

```
User
  -> Client UI: searches or opens inventory row (Box 2D)

Client UI
  -> user taps ▼ dropdown on row
  -> selects "Edit" (mutation action hidden behind ▼)

Client UI
  -> API /actions/prepare: POST {
       action_id="edit_inventory_quantity",
       target_entity_id,
       proposed_input: { qty: 1 },
       request_id
     }

API /actions/prepare (MUTATE)
  -> Gate:
       permission ok?
       context ok?
       variant=MUTATE => require diff preview + signature
  -> Diff Builder:
       compute exact delta (2 -> 1) and impacted fields
  -> Return:
       { stage: "action_staged", diff_preview, signing_required=true }

API /actions/prepare
  -> Client UI:
       [status] "Preparing change..."
       [diff] show one-line delta (no modal)
       [cta] show "Sign to apply" + "Cancel"

User
  -> taps "Sign to apply"

Client UI
  -> Signature capture:
       FaceID / passcode / typed (device-native)
  -> API /signatures: POST { method, device_hash, proof, request_id }

API /signatures
  -> Verify signature (MVP can stub but must exist)
  -> Store signature row
  -> Return { signature_id }

Client UI
  -> API /actions/commit: POST {
       action_id="edit_inventory_quantity",
       target_entity_id,
       diff_preview_hash,
       signature_id,
       request_id
     }

API /actions/commit (MUTATE)
  -> Gate again (never trust client):
       permission ok?
       signature present + valid?
       diff hash matches prepared preview?
  -> Execute handler:
       update inventory qty in SQL transaction
  -> Audit Logger (append-only):
       write action_log row including:
         user_id, action_id, target_entity_id, diff_json, signature_id, fingerprint
  -> Return:
       { stage: "committed", renderer_update, action_log_id, undo_token? }

API /actions/commit
  -> Client UI:
       [status] "Saving change..."
       [update] inventory table row updates inline
       [receipt] "Saved" + small "View log" (optional)
       [undo] show "Undo" ONLY if undoable=true

User
  -> optional taps Undo (if enabled)

Client UI
  -> API /actions/undo: POST { undo_token, request_id }

API /actions/undo
  -> Verify undo token + permissions
  -> Apply reverse mutation (new transaction)
  -> Audit Logger:
       write new action_log row (never delete)
  -> Return renderer_update
```

**Key alignment points**

* MUTATE is a 3-step server-owned ritual: `prepare → sign → commit`
* Diff preview is mandatory and **server-generated**
* Signature is required **before commit**, not before exploration
* Commit re-checks everything (permission, signature, diff hash) to prevent tampering
* Audit is append-only
* UI stays inline; “status line” narrates each stage

---

# Cancellation + failure behavior (must be identical everywhere)

### Cancel rules

* Cancel during `prepare` or `action_staged`:

  * client drops staged state, no server mutation
* Cancel during `commit` in-flight:

  * client can stop waiting, but server may still complete
  * if server completes: UI receives committed update and shows it calmly

### Failure rules

* Signature failed:

  * show “Signature failed. No changes made.”
* Permission denied:

  * action remains in ▼ but disabled next time (gating feedback)
* Network timeout:

  * UI shows “Not sure if saved.” + “Refresh” (do not lie)

---
