# Cloud PMS — Codebase Map

Plain English. Every file. Exact locations. Use this to task agents without guessing.

Last updated: 2026-04-28

---

## UNDERSTAND THE APP IN ONE MINUTE

The app has two halves:

**Backend** (`apps/api/`) — the server. It talks to the database and does the real work.
**Frontend** (`apps/web/`) — the website. It shows things on screen and sends requests to the backend.

When you click a button on screen, this is what happens:
```
You click button
  → frontend sends a request to the backend
    → backend runs the logic (handler)
      → backend reads/writes the database
        → backend sends data back
          → frontend shows the result
```

Every bug lives somewhere in that chain. This map tells you exactly where.

---

## THE GOLDEN RULE: EDIT OR CREATE NEW FILE?

**Almost always: edit an existing file.**

Only create a new file when:
1. You are adding a **completely new domain** — a new type of thing the app tracks (like a new module "insurance" that doesn't exist at all)
2. You are adding a **brand new reusable section** that will appear on multiple entity pages AND nothing like it exists yet
3. An agent explicitly tells you the file doesn't exist and explains where it would live

**If the thing already exists on screen, the file already exists. Edit it.**

Examples:
- "Change how the checklist looks" → edit existing checklist files, do NOT create new ones
- "Add upload button to warranty page" → edit `WarrantyContent.tsx`, do NOT create a new component
- "Make the notes section show differently" → edit `NotesSection.tsx`, do NOT create a new notes component
- "Add a new action button to equipment" → edit `equipment_handler.py` + `registry.py`, do NOT create a new handler

---

## SCENARIO GUIDE — "I WANT TO..."

### Change something on the WORK ORDER detail page

The work order detail page is split across 3 files. Here's which one to touch:

| What you want to change | File |
|---|---|
| The **checklist tab** — how items look, tick behaviour, submit button | `apps/web/src/components/lens/sections/ChecklistSection.tsx` |
| The **checklist tab** — which tab it's on, what order tabs appear | `apps/web/src/components/lens/entity/WorkOrderContent/WOTabBodies.tsx` |
| A **modal/popup** that appears when you click a work order action | `apps/web/src/components/lens/entity/WorkOrderContent/WOModals.tsx` |
| What **actions show** in the action dropdown on a work order | `apps/api/action_router/entity_actions.py` + `apps/api/action_router/registry.py` |
| What happens **when an action is executed** (the logic) | `apps/api/handlers/work_order_handlers.py` |
| The **overall layout** — which sections appear, in what order | `apps/web/src/components/lens/entity/WorkOrderContent/index.tsx` |
| The **frequency / auto-spawn** logic | `apps/api/handlers/work_order_handlers.py` |

---

### Change something on ANY entity detail page (certificates, faults, equipment, etc.)

Every entity detail page ("lens") follows the same pattern. When you open `/equipment/abc123`, three layers are involved:

**Layer 1 — The page shell** (same for all entities)
- `apps/web/src/components/lens/EntityLensPage.tsx` — the overall wrapper (header, tabs, action bar)
- `apps/web/src/components/lens/LensGlassHeader.tsx` — the top strip with the entity name and action button
- `apps/web/src/components/lens/LensTabBar.tsx` — the row of tabs

**Layer 2 — The content for that specific entity** (one file per domain)
This is where you control what sections appear and in what order on each entity type:
- Equipment page content → `apps/web/src/components/lens/entity/EquipmentContent.tsx`
- Fault page content → `apps/web/src/components/lens/entity/FaultContent.tsx`
- Certificate page content → `apps/web/src/components/lens/entity/CertificateContent.tsx`
- Work order page content → `apps/web/src/components/lens/entity/WorkOrderContent/index.tsx`
- Purchase order content → `apps/web/src/components/lens/entity/PurchaseOrderContent.tsx`
- Warranty content → `apps/web/src/components/lens/entity/WarrantyContent.tsx`
- Inventory/parts content → `apps/web/src/components/lens/entity/PartsInventoryContent.tsx`
- Receiving content → `apps/web/src/components/lens/entity/ReceivingContent.tsx`
- Shopping list content → `apps/web/src/components/lens/entity/ShoppingListContent.tsx`
- Document content → `apps/web/src/components/lens/entity/DocumentContent.tsx`
- Handover content → `apps/web/src/components/lens/entity/HandoverContent.tsx`
- Hours of rest content → `apps/web/src/components/lens/entity/HoursOfRestContent.tsx`

**Layer 3 — Reusable sections** (shared across multiple entities)
These are building blocks that plug into any entity page above. Edit these when the section itself is broken, not which entity it appears on:
- Notes section (comments) → `apps/web/src/components/lens/sections/NotesSection.tsx`
- Attachments/files section → `apps/web/src/components/lens/sections/AttachmentsSection.tsx`
- Checklist section → `apps/web/src/components/lens/sections/ChecklistSection.tsx`
- Audit trail (who changed what) → `apps/web/src/components/lens/sections/AuditTrailSection.tsx`
- History timeline → `apps/web/src/components/lens/sections/HistorySection.tsx`
- Ledger/transaction history → `apps/web/src/components/lens/sections/LedgerHistorySection.tsx`
- Related equipment → `apps/web/src/components/lens/sections/RelatedEquipmentSection.tsx`
- Parts used → `apps/web/src/components/lens/sections/PartsSection.tsx`
- Renewal history (certs/warranties) → `apps/web/src/components/lens/sections/RenewalHistorySection.tsx`
- Key-value data → `apps/web/src/components/lens/sections/KVSection.tsx`
- File viewer (PDFs) → `apps/web/src/components/lens/sections/LensFileViewer.tsx`
- Image viewer (photos) → `apps/web/src/components/lens/sections/LensImageViewer.tsx`

---

### Add the document upload / attachment button to an entity page

The upload button and section live in two places:

1. **The section that shows files** → `apps/web/src/components/lens/sections/AttachmentsSection.tsx`
   (this already shows an "upload" button — if it's broken or needs changing, edit here)

2. **Where on the entity page it appears** → the `*Content.tsx` file for that entity
   (if attachments section isn't showing on a particular entity page, add `<AttachmentsSection />` to that entity's Content file)

3. **The backend that receives the upload** → `apps/api/routes/attachment_upload.py`
   (if uploads are failing or going to wrong storage, edit here)

You do NOT need a new file. The section already exists. You're just plugging it into the right content page.

---

### Add a new ACTION button to an entity (something the user can do)

Actions are buttons like "Add Note", "Close Work Order", "File Warranty Claim". They follow a fixed chain. ALL of these files need touching:

1. **Define the action** — `apps/api/action_router/registry.py`
   (add the action name, what fields it needs, what role can use it)

2. **Make it appear on the right entity** — `apps/api/action_router/entity_actions.py`
   (add a rule: "show this action when entity is in X state")

3. **Write what it does** — `apps/api/handlers/{domain}_handlers.py`
   (e.g. for a work order action → `work_order_handlers.py`)

4. **Wire the backend dispatch** — `apps/api/routes/handlers/__init__.py`
   (make sure the action name maps to the handler function)

5. **If the action has a custom popup/form** — add a modal to the entity's `WOModals.tsx` equivalent, or use the standard `ActionPopup` which handles it automatically

If the action uses the standard form popup (most do), steps 1-4 are enough. The ActionPopup renders the form automatically based on the registry definition.

---

### Change what shows in the LIST view (before clicking into an entity)

The list pages (`/equipment`, `/work-orders`, etc.) are separate from the detail pages.

| What you want to change | File |
|---|---|
| Columns in the work order list table | `apps/web/src/features/work-orders/columns.tsx` |
| Columns in the equipment list table | `apps/web/src/features/equipment/columns.tsx` |
| How work order data is fetched for the list | `apps/web/src/features/work-orders/api.ts` |
| How equipment data is fetched for the list | `apps/web/src/features/equipment/api.ts` |
| The filter bar (filter chips, search input) | `apps/web/src/features/entity-list/components/FilterBar.tsx` |
| A single row in any list | `apps/web/src/features/entity-list/components/EntityRecordRow.tsx` |
| The work order calendar view | `apps/web/src/features/work-orders/WorkOrderCalendar.tsx` |

---

### Change the action POPUP FORM (the modal that appears when you click an action)

The popup is shared across all actions. It has field types:

| Field type | File |
|---|---|
| A text box | `apps/web/src/components/lens/ActionPopup/fields/FieldTextArea.tsx` |
| A date picker | `apps/web/src/components/lens/ActionPopup/fields/FieldDatePick.tsx` |
| A dropdown (select one option) | `apps/web/src/components/lens/ActionPopup/fields/FieldSelect.tsx` |
| A file/attachment upload | `apps/web/src/components/lens/ActionPopup/fields/FieldAttachment.tsx` |
| Assign a person | `apps/web/src/components/lens/ActionPopup/fields/FieldPersonAssign.tsx` |
| Search and link another entity | `apps/web/src/components/lens/ActionPopup/fields/FieldEntitySearch.tsx` |
| The popup shell itself (title, submit button) | `apps/web/src/components/lens/ActionPopup/ActionPopup.tsx` |
| Which field renders for which type | `apps/web/src/components/lens/ActionPopup/fields/renderField.tsx` |

To add a new field TYPE (e.g. a colour picker that doesn't exist yet), add a new file in `ActionPopup/fields/` and register it in `renderField.tsx`. To change an existing field, just edit the field's file directly.

---

### Change what the backend DOES when an action is clicked

Every domain has one handler file. Find the domain, find the function:

| Domain | Handler file |
|---|---|
| Work orders | `apps/api/handlers/work_order_handlers.py` |
| Equipment | `apps/api/handlers/equipment_handler.py` |
| Faults | `apps/api/handlers/fault_handler.py` |
| Warranty | `apps/api/handlers/warranty_handlers.py` |
| Certificates | `apps/api/handlers/certificate_handlers.py` |
| Inventory / parts | `apps/api/handlers/inventory_handlers.py` + `part_handlers.py` |
| Purchase orders | `apps/api/handlers/purchase_order_handlers.py` |
| Receiving | `apps/api/handlers/receiving_handlers.py` |
| Shopping list | `apps/api/handlers/shopping_list_handlers.py` |
| Hours of rest | `apps/api/handlers/hours_of_rest_handlers.py` |
| Handover | `apps/api/handlers/handover_handlers.py` |
| Documents | `apps/api/handlers/document_handler.py` |

**Rule: one domain = one handler file. Never split logic across two handler files for the same domain.**

---

### Change the TOP BAR, SIDEBAR, or overall layout

| What | File |
|---|---|
| The top bar (vessel dropdown, search icon, user menu) | `apps/web/src/components/shell/Topbar.tsx` |
| The left sidebar (navigation links, counts) | `apps/web/src/components/shell/Sidebar.tsx` |
| The bar below the topbar (breadcrumb, filter chips) | `apps/web/src/components/shell/Subbar.tsx` |
| The overall grid layout (how topbar/sidebar/body fit together) | `apps/web/src/components/shell/AppShell.tsx` |
| The home page (vessel overview) | `apps/web/src/components/shell/VesselSurface.tsx` |
| The notification bell | `apps/web/src/components/shell/NotificationBell.tsx` |
| The vessel switcher (multi-vessel dropdown) | `apps/web/src/contexts/VesselContext.tsx` |

---

### Change search behaviour

| What | File |
|---|---|
| The search overlay that appears when you press the search icon | `apps/web/src/components/spotlight/SpotlightSearch.tsx` |
| How search results are grouped/ordered | `apps/web/src/lib/spotlightGrouping.ts` |
| The backend search logic (what gets returned) | `apps/api/orchestration/search_orchestrator.py` |
| Search result ranking | `apps/api/orchestration/ranking_recipes.py` |

---

### Change who can see/use something (permissions)

| What | File |
|---|---|
| Which actions are visible to which roles | `apps/api/action_router/registry.py` (each action has a `roles` field) |
| Which actions appear based on entity state | `apps/api/action_router/entity_actions.py` |
| Whether a user can access a vessel at all | `apps/api/middleware/vessel_access.py` |
| Whether an action requires confirmation | `apps/api/middleware/action_gating.py` |

---

## FILE DIRECTORY

This section lists every file. Use the scenario guide above first — only come here if you need a file not covered above.

---

### BACKEND ENTRY POINTS
*(These start the server. You almost never touch these.)*

| File | What it does + when you'd touch it |
|---|---|
| `apps/api/pipeline_service.py` | Starts the backend server and registers all URL routes. Like the front door of the building. *Touch this if you're adding a brand new route file that isn't being picked up by the server.* |
| `apps/api/combined_service.py` | Runs the server plus 5 background workers together on Render. *Only touch this if you're changing how the server starts up or adding a new background worker process.* |

---

### BACKEND: `routes/`
*(These files just receive a web request and hand it to the right handler. No logic here.)*

| File | What it does + when you'd touch it |
|---|---|
| `action_execution_routes.py` | Receives every button-click action from the frontend. The single entry point for all actions. *Touch this if an action is returning 404 or 500 before even reaching the handler — the routing itself is broken.* |
| `entity_routes.py` | Sends back all the data when you open an entity detail page. *e.g. you open a work order and the page is blank or missing fields → the data fetch starts here.* |
| `vessel_surface_routes.py` | Sends back the home dashboard data. *Touch this if the home page isn't loading or is showing stale vessel info.* |
| `document_routes.py` | Document search and CRUD. *e.g. document search returns no results or the wrong ones → start here.* |
| `part_routes.py` | Parts and equipment list requests. *Touch this if the parts list endpoint returns an error.* |
| `hours_of_rest_routes.py` | Hours of rest data. *If HoR data isn't loading at all, check this before the handler.* |
| `handover_export_routes.py` | Handover PDF generation. *If the export button triggers a 500, the route is the first place to check.* |
| `import_routes.py` | File import pipeline. *Touch this if the import dry-run or commit endpoint returns the wrong response shape.* |
| `ledger_routes.py` | Audit ledger downloads. *e.g. the "Export Ledger" button returns a broken PDF → check here first.* |
| `notification_routes.py` | Notification fetch. *If the notification bell never loads or always shows 0, this is where the request comes in.* |
| `related_signal_routes.py` | Related-entity discovery. *Touch this if the "Related" panel on an entity never populates.* |
| `context_navigation_routes.py` | Related-entity discovery using DB relationships. *Alternative to signal routes — touch if related items are wrong or missing.* |
| `attachment_upload.py` | Receives uploaded files and stores them. *If an upload button silently fails or the file goes to the wrong bucket, start here.* |
| `receiving_upload.py` | Receiving item uploads. *Touch this if a receiving upload returns an error the frontend doesn't explain.* |
| `receiving_label_routes.py` | Generates barcode labels. *e.g. "Print Label" button produces a blank page → the label generation starts here.* |
| `purchase_order_pdf_route.py` | Generates PO PDFs. *Touch this if "Download PO" returns an error or a corrupt file.* |
| `shopping_list_pdf_route.py` | Generates shopping list PDFs. *Same as above but for shopping lists.* |
| `email_inbox_routes.py` | Email inbox data. *If the inbox doesn't load, this is where that request lands.* |
| `email_thread_routes.py` | Email thread data. *Touch this if opening an email thread returns blank content.* |
| `email_link_routes.py` | Linking emails to entities. *e.g. "Link to Work Order" button returns 500 → start here.* |
| `email_sync_routes.py` | Triggers an email sync. *Touch this if the "Sync" button does nothing.* |
| `auth_routes.py` | Microsoft login token exchange. *Touch this if Outlook auth redirects to an error page.* |
| `attention_routes.py` | "Needs attention" data. *If the attention dashboard is empty when it shouldn't be, check here.* |
| `orchestrated_search_routes.py` | Main search requests. *Touch this if search returns a 500 rather than results.* |
| `f1_search_streaming.py` | Live streaming search (results appear as you type). *Touch this if the streaming search hangs or stops mid-result.* |
| `search_streaming.py` | Old streaming search. Not actively used. *Don't touch unless debugging legacy search behaviour.* |
| `rag_endpoint.py` | AI question-answering. *Touch this if the AI assistant returns an error instead of an answer.* |
| `routes/handlers/__init__.py` | Maps every action name to its handler function. *If any action returns 404 "action not found", it's missing from this lookup table.* |
| `routes/handlers/internal_adapter.py` | Temporary bridge for document and parts actions. *Don't add new things here. Touch only if a document or parts action is broken and you've confirmed the handler exists.* |

---

### BACKEND: `handlers/`
*(This is where all the real work happens. One file per domain. If a button does the wrong thing, it's in here.)*

| File | What it does + when you'd touch it |
|---|---|
| `work_order_handlers.py` | Everything work orders do: create, update, close, assign, checklist, frequency spawn, `link_fault_to_work_order`, `link_equipment_to_work_order`, `add_parts_to_work_order` (writes to `pms_work_order_parts`). *If "Close Work Order" doesn't update the status, or checklist items aren't saving, the bug is in here.* |
| `equipment_handler.py` | Everything equipment does: status, notes, running hours, manuals, archive. *e.g. "Record Hours" action saves but the hours don't update on screen → the logic is here.* |
| `fault_handler.py` | Everything faults do: create, update, resolve, link parts, notes. *Touch this if resolving a fault doesn't change its status or the audit trail entry is wrong.* |
| `warranty_handlers.py` | Everything warranty claims do: draft, file, compose email, notes, audit. *If filing a warranty claim returns 500, or the draft isn't saved, start here.* |
| `certificate_handlers.py` | Everything certificates do: register, renew, expiry, notes. *e.g. renewing a certificate doesn't update the expiry date → this is where that logic runs.* |
| `inventory_handlers.py` | Inventory and stock management. *Touch this if stock levels aren't updating after a transaction.* |
| `part_handlers.py` | Individual part lifecycle: create, update, reorder. *If creating a new part fails or reorder logic is wrong, start here.* |
| `purchase_order_handlers.py` | Purchase order creation and status. *e.g. a PO is stuck in "draft" even after sending → the status transition logic is here.* |
| `receiving_handlers.py` | Goods receiving and acceptance. *Touch this if received items aren't being recorded correctly against a PO.* |
| `shopping_list_handlers.py` | Shopping list creation and item management. *If adding an item to a shopping list silently fails, the handler is here.* |
| `hours_of_rest_handlers.py` | HoR recording and compliance checks. *Touch this if rest periods aren't being calculated correctly or compliance flags are wrong.* |
| `handover_handlers.py` | Handover workflow: draft, sign, countersign, export. *e.g. a handover is stuck and can't be countersigned → the state machine logic is here.* |
| `document_handler.py` | Document creation, update, metadata. *If uploading a document saves the file but doesn't create the metadata record, start here.* |
| `document_comment_handlers.py` | Comments on documents. *Touch this if adding a comment to a document returns an error.* |
| `attachment_comment_handlers.py` | Comments on attachments (files). *Same but for attachment comments specifically.* |
| `entity_lens_handlers.py` | Builds the full data package sent to any entity detail page. WO handler: enriches fault_id → `faults[]`, resolves note `created_by` UUIDs → `author_name`/`author_role`, resolves audit `user_id` → `actor`, flattens `pms_work_order_parts` to parts array, filters read-prefix audit noise. Interlink chain (all bidirectional): **Part** card shows related WOs (via `pms_work_order_parts`), shopping list items (via `pms_shopping_list_items.part_id`), and POs (via `pms_purchase_order_items.part_id`). **PO** card shows source shopping list + line-item parts + receiving records (via `pms_receiving.po_id`). **Certificate** (vessel) card shows equipment it covers (via `properties.equipment_ids`). *If an entity page loads but fields are missing or showing wrong data, the data assembly is here.* |
| `list_handlers.py` | Generic list queries used across domains. *Touch this if a list endpoint returns the wrong set of items.* |
| `shared_mutation_handlers.py` | Generic "add note", "update field" logic shared across domains. *e.g. notes are saving but not appearing on screen → check here if it's not a domain-specific handler issue.* |
| `shared_read_handlers.py` | Generic "view entity" and "list items" logic. *Touch this if a read-only view action returns incorrect data.* |
| `universal_handlers.py` | Soft delete and archive logic used across all domains. *If "Archive" on any entity type doesn't work, the shared archive logic is here.* |
| `email_handlers.py` | Email reading, thread management, linking to entities. *Touch this if an email thread isn't displaying correctly or linking to the wrong entity.* |
| `media_handlers.py` | Photo and image attachment handling. *If photo uploads save but thumbnails don't generate, start here.* |
| `manual_handlers.py` | Manual task and procedure handling. *Touch this if manual task creation or assignment is broken.* |
| `delivery_compliance_handlers.py` | Compliance checks on deliveries. *e.g. a delivery passes compliance it shouldn't → the check logic is here.* |
| `compliance_handler.py` | General compliance status and audit logic. *Touch this if compliance status badges are showing the wrong state.* |
| `pm_handler.py` | Preventive maintenance logic. *If PM schedules aren't generating work orders correctly, start here.* |
| `context_navigation_handlers.py` | Finds related entities using database FK relationships. *Touch this if the related panel shows wrong or missing items.* |
| `related_signal_handlers.py` | Finds related entities using signals. *Alternative to context_nav — touch if related panel is empty when it shouldn't be.* |
| `ledger_utils.py` | Writes to the audit ledger after every important action. *If an action completes but leaves no audit trail entry, this is where that write should happen.* |
| `schema_mapping.py` | Maps entity type names to database table names. *Touch this if a new entity type is returning "table not found" errors.* |
| `db_client.py` | Creates a database connection that enforces data access rules. *Touch this only if all DB queries are failing with permission errors.* |
| `stub_handlers.py` | Placeholder for actions not yet built. Returns "not implemented". *Touch this if an action exists in the registry but has no real handler yet — add the stub here temporarily.* |
| `equipment_utils.py` | Helper calculations for equipment (running hours, status checks). *Touch this if running hour totals are calculated wrong.* |

---

### BACKEND: `action_router/`
*(Controls which actions appear on screen and what they're called. No database writes here.)*

| File | What it does + when you'd touch it |
|---|---|
| `registry.py` | The master list of every action. Defines the name, fields, roles, and UI label for each one. *If you want to add a new action anywhere in the app, this is always the first file to touch. If an action shows the wrong name or wrong fields, it's here.* |
| `entity_actions.py` | Rules for when each action is visible. *If an action isn't appearing when it should — or is appearing when it shouldn't — the visibility rule is here.* |
| `entity_prefill.py` | Maps which fields to pre-fill when an action form opens. *e.g. you open "Add Note" on a work order and the work order ID field is blank instead of pre-filled → this file is missing that mapping.* |
| `ledger_metadata.py` | Maps action names to their audit log event types. *Touch this if an action runs but creates the wrong type of ledger entry.* |
| `logger.py` | Records every action execution for analytics. *Touch this if action analytics are missing or logging the wrong data.* |

#### `action_router/dispatchers/`
*(Thin wrappers. Normally don't touch these.)*

| File | What it does + when you'd touch it |
|---|---|
| `index.py` | Temporary bridge for old document/parts actions. *Only touch if a document or parts action is returning "handler not found" and you've confirmed the real handler exists.* |
| `document.py` | Passes document actions to the document handler. *Touch this if a document action gets through routing but the wrong function is called.* |
| `parts.py` | Passes parts actions to the parts handler. *Same as above for parts actions.* |
| `p3.py` | Passes read-only view actions to the right handler. *Touch this if "View Document" or similar read-only actions are breaking.* |
| `shared.py` | Shared utilities used by the dispatchers. *Touch this only if multiple dispatchers are all failing in the same way.* |

---

### BACKEND: `middleware/`
*(Runs before every request. Security, validation, rate limiting.)*

| File | What it does + when you'd touch it |
|---|---|
| `auth.py` | Checks login token, looks up which vessel you're on, checks your role. *If every request returns 401 or 403, or users are landing on the wrong vessel, start here.* |
| `action_security.py` | Extra checks: does this user own this entity? Is the vessel frozen? Has this exact action already been run? *Touch this if users are getting "not authorised" on actions they should be able to do, or if duplicate actions are slipping through.* |
| `action_gating.py` | Decides if an action needs a confirmation dialog or can run automatically. *e.g. "Archive Equipment" fires immediately without asking "are you sure?" → add it to the gated list here.* |
| `handover_gating.py` | Controls which roles can add things to a handover. *Touch this if a crew member can add items they shouldn't, or can't add items they should.* |
| `state_machine.py` | Validates status changes — prevents going backwards through statuses. *e.g. a shopping list is being moved back to "draft" from "approved" and it shouldn't be → the rule is here.* |
| `validation_middleware.py` | Checks field formats before they reach the handler. *If an action returns a 400 error about "invalid UUID" or "field too long", the check that triggered it is here.* |
| `vessel_access.py` | Checks fleet users are allowed to view the vessel they're requesting. *Touch this if fleet managers can see vessels they shouldn't, or can't see vessels they should.* |
| `rate_limit.py` | Prevents too many requests per second. *Touch this if legitimate users are getting "too many requests" errors.* |

---

### BACKEND: `validators/`
*(Checks data is correct before it's used. If something returns "invalid" before reaching the handler, it's here.)*

| File | What it does + when you'd touch it |
|---|---|
| `jwt_validator.py` | Validates the login token on every request. *If users are being rejected despite being logged in, the token check is here.* |
| `yacht_validator.py` | Checks the user has access to the vessel they're requesting. *Touch this if cross-vessel access is wrongly allowed or blocked.* |
| `role_validator.py` | Checks the user's role allows what they're trying to do. *e.g. a chief engineer can't run an action that should be open to all officers → the role check is here.* |
| `rls_entity_validator.py` | Prevents one vessel's data from being seen by another vessel. *Critical. Touch this only if data isolation is broken — one vessel can see another's records.* |
| `field_validator.py` | Validates individual field values before they're used. *Touch this if a valid value is being rejected as invalid.* |
| `schema_validator.py` | Checks the whole action payload has the right shape. *If an action returns "invalid payload" with no other explanation, the payload schema check is here.* |
| `ownership.py` | Checks an entity belongs to the vessel making the request. *Touch this if ownership checks are wrongly blocking a user from their own data.* |
| `validation_result.py` | The standard pass/fail wrapper used by all validators. *Only touch if you're changing how validation results are returned system-wide.* |

---

### BACKEND: `schemas/`
*(Defines what every API response looks like.)*

| File | What it does + when you'd touch it |
|---|---|
| `action_response_schema.py` | The standard wrapper every handler uses when sending back a response. *If the frontend receives a response in an unexpected shape — fields missing or in the wrong place — check here. Every handler uses `ResponseBuilder` from this file.* |

---

### BACKEND: `services/`
*(Complex features that don't fit neatly in a single handler.)*

| File | What it does + when you'd touch it |
|---|---|
| `import_service.py` | Processes CSV/XLSX imports. Dry-run shows what would happen; commit makes it real. *If imported data is landing in the wrong columns or rows are being skipped, the transformation logic is here.* |
| `hyper_search.py` | Runs the F1 search database call and manages the connection pool. *Touch this if search is timing out or returning connection errors.* |
| `indexing_trigger.py` | Fire-and-forget sync hook that upserts a `pending` row into `search_index` after any entity change or file upload. Called by `action_execution_routes.py` and `attachment_upload.py`. *Touch this if newly created or updated entities never appear in search at all — this is the first link in the indexing chain.* |
| `decision_engine.py` | Reads the E017/E019 policy files and decides which actions to suggest with what confidence. *e.g. the wrong action is being suggested for a fault → the policy evaluation is here.* |
| `action_surfacing.py` | Decides which actions appear as "suggested" based on entity state. *Touch this if the suggested action strip is showing irrelevant actions.* |
| `handover_export_service.py` | Builds the handover PDF/HTML with all items and seals it. *If a handover export generates but is missing items or has broken formatting, start here.* |
| `handover_microservice_client.py` | Talks to the separate handover microservice. *Touch this if the handover microservice is returning errors that the main app isn't handling correctly.* |
| `file_reference_resolver.py` | Resolves file references in import data to actual paths. *Touch this if imported records reference files that can't be found.* |
| `linking_ladder.py` | Automatically links entities to each other based on content similarity. *Touch this if auto-linking is connecting the wrong entities.* |
| `cache.py` | Stores frequently-used data in memory to reduce database load. *Touch this if cached data is going stale and not refreshing.* |
| `rate_limit.py` | Rate limiter for live streaming search only (per-user, in-memory). *Different from the middleware rate limiter. Touch this if streaming search is cutting users off too aggressively.* |
| `entity_serializer.py` | Converts entity data into a text string for search indexing. *Touch this if entities are appearing in search with wrong or missing text.* |
| `scoring_engine.py` | Scores search results for relevance. *Touch this if relevant results are ranking below irrelevant ones.* |
| `email_sync_service.py` | Pulls emails from Microsoft Outlook. *Touch this if emails stop syncing or sync is missing certain mailboxes.* |
| `email_search_service.py` | Searches stored emails. *Touch this if email search returns the wrong results.* |
| `email_link_service.py` | Auto-links emails to entities based on content. *e.g. an email about "WO-4521" isn't being linked to that work order → the linking logic is here.* |
| `email_suggestion_service.py` | Suggests actions based on email content. *Touch this if email-triggered action suggestions are wrong or irrelevant.* |

---

### BACKEND: `workers/`
*(Background jobs. Not triggered by user clicks — they run on their own schedule.)*

| File | What it does + when you'd touch it |
|---|---|
| `projection_worker.py` | Continuously indexes entities so they appear in search. *If newly created work orders or equipment aren't showing up in search after a few minutes, this worker may be failing.* |
| `embedding_worker_1536.py` | Generates AI embeddings for semantic search. *Touch this if semantic search (finding things by meaning, not just keywords) is broken.* |
| `extraction_worker.py` | Downloads documents and extracts text for indexing. *Touch this if documents are visible in the app but their content never appears in search results.* |
| `email_watcher_worker.py` | Watches for new emails and processes them. *Touch this if the email module stops receiving new emails without any user action.* |
| `nightly_certificate_expiry.py` | Runs every night checking for expiring certificates. *Touch this if expiry alerts aren't appearing, or are appearing for the wrong certificates.* |
| `nightly_feedback_loop.py` | Runs every night adjusting extraction quality. *Touch this only if extraction accuracy is degrading over time.* |

---

### BACKEND: `tests/`
*(Integration test suites that hit the live TENANT DB. Not unit tests — these require a real DB connection and prove the full chain.)*

| File | What it does + when you'd touch it |
|---|---|
| `tests/pridx_integration_test.py` | 6-test suite proving the full indexing + visibility chain: `search_projection_map` config, `enqueue_for_projection` trigger, `allowed_roles` on HoR rows, role-gated `f1_search_cards` RPC, and `trg_propagate_visibility_change`. *Run after any change to the indexing pipeline, search routes, or visibility config.* Run: `cd apps/api && python3 tests/pridx_integration_test.py` |

---

### BACKEND: `evidence/`
*(Production code for the ledger export. Not test files — don't delete.)*

| File | What it does + when you'd touch it |
|---|---|
| `sealing.py` | Seals the audit ledger PDF with a legal timestamp so it can't be altered. *Touch this if ledger exports generate but fail the tamper-check, or if the PDF sealing step errors.* |
| `fonts/` | Font files used when generating sealed PDFs. *Don't touch. If PDF fonts are broken, replace the files here.* |
| `icc/` | Colour profile for sealed PDFs. *Don't touch unless PDF colour rendering is wrong.* |

---

### BACKEND: `lib/`
*(Shared helpers used by handlers and routes. Not domain-specific logic — pure utility.)*

| File | What it does + when you'd touch it |
|---|---|
| `entity_helpers.py` | Maps entity types to their storage buckets and attachment configs. *Touch this if uploads are going to the wrong bucket, or a new entity type needs its own document storage configured.* |
| `user_resolver.py` | Resolves a JWT token to a user record (name, role, yacht). *Touch this if the wrong user name is appearing in audit trails or notifications.* |

---

### FRONTEND: HOW THE SCREEN IS BUILT

Every page on screen is built from these layers, from outside in:

```
AppShell (the frame: topbar + sidebar + body area)
  └── RouteLayout (padding, max-width for the page body)
       └── Page file (e.g. work-orders/[id]/page.tsx — just loads the lens)
            └── EntityLensPage (the detail page wrapper)
                 └── {Domain}Content (e.g. WorkOrderContent — what sections appear)
                      └── Sections (ChecklistSection, NotesSection, etc.)
```

---

### FRONTEND: `styles/`
*(Visual design. All values come from tokens — never hardcode colours or sizes.)*

| File | What it does + when you'd touch it |
|---|---|
| `styles/tokens.css` | The single source of truth for every colour, size, and spacing value. *If you want to change the primary colour, a font size, or a border radius globally — edit here, not in individual components.* |
| `styles/globals.css` | Base styles for the whole page: fonts, resets, body background. *Touch this if a base-level style (like the default font) needs changing everywhere.* |
| `styles/lens.css` | Styles specific to entity detail pages and modal dialogs. *Touch this if the overall spacing or layout of any detail page looks wrong.* |
| `styles/spotlight.css` | Styles for the search overlay. *Touch this if the search dropdown looks broken or is positioned incorrectly.* |

---

### FRONTEND: `contexts/`
*(Shared state available to the whole app. Think of these as global variables the whole app can read.)*

| File | What it does + when you'd touch it |
|---|---|
| `AuthContext.tsx` | Stores who is logged in, their role, their vessel. *If the app shows the wrong user, wrong vessel, or can't read the current role anywhere, start here.* |
| `VesselContext.tsx` | Stores which vessel is active and handles switching between vessels. *Touch this if the vessel switcher doesn't update the rest of the app, or the wrong vessel stays selected after a switch.* |
| `EntityLensContext.tsx` | On a detail page, holds the entity data and runs actions. *If actions on a detail page aren't triggering a reload of the page data after completion, look here.* |
| `BackdropContext.tsx` | Triggers the animated orb effect after a successful save. *Touch this only if the animation is firing at the wrong times or not at all.* |

---

### FRONTEND: `hooks/`
*(Reusable data-fetching. These are what components use to load data from the backend.)*

| File | What it does + when you'd touch it |
|---|---|
| `useAuth.ts` | Returns the current user, login status, and login/logout functions. *Touch this if login state isn't persisting across page navigation.* |
| `useActiveVessel.ts` | Returns the active vessel and the full list of vessels for this user. *e.g. the vessel name in the topbar doesn't update after switching → check here.* |
| `useEntityLens.ts` | Fetches all data for an entity detail page and handles running actions. *If a detail page loads but is missing fields, or actions run but the page doesn't refresh, start here.* |
| `useActionHandler.ts` | Manages the lifecycle of clicking an action: loading state, errors, confirmation dialogs. *Touch this if the action button doesn't show a loading spinner, or errors aren't displayed to the user.* |
| `useCelesteSearch.ts` | Runs search queries with debouncing (waits until you stop typing). *Touch this if search fires too eagerly or too slowly while typing.* |
| `useEntityLedger.ts` | Fetches the ledger history for an entity. *e.g. the History tab on a work order is empty even though entries exist → check here.* |
| `useNeedsAttention.ts` | Fetches the list of items flagged as needing attention. *Touch this if the attention dashboard is blank or shows stale data.* |
| `useRelated.ts` | Fetches related entities for the related panel. *If the related panel loads forever or shows nothing, start here.* |
| `useRelatedDrawer.ts` | Manages whether the related entities drawer is open or closed. *Touch this if the drawer doesn't open when clicking the related button.* |
| `useEmailData.ts` | Fetches email inbox and thread data. *Touch this if the inbox loads but threads won't open.* |
| `useReadBeacon.ts` | Marks an entity as viewed when its detail page opens. *Touch this if read/unread status isn't updating when you view an entity.* |

---

### FRONTEND: `lib/`
*(Client-side logic and utilities. Not visual — pure functions and API calls.)*

| File | What it does + when you'd touch it |
|---|---|
| `apiClient.ts` | The main HTTP client. Adds your login token and vessel ID to every request. *If API calls are failing with 401 (not authorised) or the wrong vessel's data is being fetched, start here.* |
| `actionClient.ts` | Specifically sends action execution requests. *Touch this if actions reach the frontend handler but the network request never fires.* |
| `authHelpers.ts` | Helper functions: get your token, get your vessel ID, handle a 401 error. *e.g. after a 401, the user isn't being redirected to login → the 401 handler is here.* |
| `tokenRefresh.ts` | Keeps the login token fresh automatically. *Touch this if users are getting logged out unexpectedly mid-session.* |
| `apiBase.ts` | Stores the backend URL, switching between dev and production. *Touch this if API calls are hitting the wrong server in a given environment.* |
| `supabaseClient.ts` | The Supabase client used for auth on the frontend. *Touch this only if the Supabase auth connection itself is broken.* |
| `field-schema.ts` | Defines which form fields are hidden, read-only, or auto-filled. *If a field is showing in a form that shouldn't be there, or a field is missing a label, check here first.* |
| `entityRoutes.ts` | Maps entity types to URLs. *e.g. clicking an equipment link goes to the wrong page → the route mapping is here.* |
| `utils.ts` | Small helpers: format a date, merge CSS classes, debounce a function. *Touch this if dates are formatted inconsistently across the app.* |
| `normalizeWarranty.ts` | Cleans up raw warranty data before it's displayed. *Touch this if warranty fields are showing raw database values instead of formatted ones.* |
| `spotlightGrouping.ts` | Groups search results by category for the search overlay. *Touch this if search results appear in the wrong groups or order.* |
| `handoverExportClient.ts` | API calls for handover export actions. *Touch this if acknowledge/countersign/submit buttons on handover aren't sending the right request.* |
| `documentLoader.ts` | Fetches the document list and builds the folder tree. *Touch this if the document tree is showing the wrong structure or missing folders.* |
| `domain/catalog.ts` | Master list of entity types with their display names. *Touch this if a new entity type needs to be added to the domain catalog.* |
| `filters/catalog.ts` | Defines what filters are available per entity type. *Touch this if a filter option is missing from a list page.* |
| `filters/infer.ts` | Automatically suggests filters as you type. *Touch this if filter suggestions are wrong or not appearing.* |
| `filters/execute.ts` | Applies active filters to results. *Touch this if filtering is returning the wrong set of items.* |
| `actions/registry.ts` | Frontend copy of the action registry with display labels and icons. *Touch this if an action button shows the wrong label or icon.* |
| `actions/executor.ts` | Sends actions to the backend and handles the response. *Touch this if actions return success from the backend but the frontend shows an error anyway.* |
| `actions/handlers/workOrders.ts` | What the frontend does after a work order action completes. *e.g. closing a work order succeeds but the status pill on screen doesn't update → check here.* |
| `actions/handlers/equipment.ts` | Frontend response to equipment actions. *Same pattern — if equipment actions succeed server-side but the UI doesn't update, check here.* |
| `actions/handlers/inventory.ts` | Frontend response to inventory actions. |
| `actions/handlers/procurement.ts` | Frontend response to purchasing/PO actions. |
| `actions/handlers/handover.ts` | Frontend response to handover actions. |
| `actions/handlers/compliance.ts` | Frontend response to compliance/HoR actions. |

---

### FRONTEND: `components/shell/`
*(The persistent chrome around every page.)*

| File | What it does + when you'd touch it |
|---|---|
| `AppShell.tsx` | The grid that places topbar, sidebar, and body. The frame everything lives inside. *Touch this if the overall page layout is broken — content overflowing, sidebar covering the body, etc.* |
| `Topbar.tsx` | The top bar: vessel name, search icon, notification bell, user avatar. *Touch this if the vessel name is wrong, the avatar is missing, or the search icon doesn't open the search overlay.* |
| `Sidebar.tsx` | Left navigation with links and item counts. *Touch this if a navigation link goes to the wrong page, a domain is missing, or counts are wrong.* |
| `Subbar.tsx` | The bar below the topbar: breadcrumb, scoped search, active filter chips. *Touch this if the breadcrumb shows the wrong path or filter chips aren't appearing.* |
| `VesselSurface.tsx` | The home page content: vessel status, vital signs, overview. *Touch this to change what's shown on the dashboard when you first log in.* |
| `SearchOverlay.tsx` | The full-screen search triggered by the search icon. *Touch this if the search overlay is opening at the wrong size or results aren't showing correctly inside it.* |
| `NotificationBell.tsx` | The bell icon and notification dropdown. *Touch this if notifications aren't showing in the dropdown even when they exist in the database.* |
| `SettingsModal.tsx` | The settings panel. *Touch this to add settings options or change the layout of the settings screen.* |

---

### FRONTEND: `components/lens/`
*(Everything on entity detail pages.)*

| File | What it does + when you'd touch it |
|---|---|
| `EntityLensPage.tsx` | The wrapper that coordinates the header, tabs, action button, and content for every detail page. *Touch this if the overall structure of every entity page is wrong — not just one domain.* |
| `LensGlassHeader.tsx` | Top strip showing entity name, status badge, and the main action button. *Touch this if the entity title is wrong, the status pill is in the wrong position, or the action button doesn't appear.* |
| `LensTabBar.tsx` | The row of tabs on a detail page. *Touch this if tabs are in the wrong order, the wrong tab is active by default, or a tab label is wrong — across all entities.* |
| `RelatedDrawer.tsx` | The side panel that slides in showing related entities. *Touch this if the panel won't open, won't close, or the related items inside it aren't rendering.* |
| `CollapsibleSection.tsx` | A section with a header you can click to expand or collapse. *Touch this if collapse/expand behaviour is broken on any section.* |
| `ActionPopup/ActionPopup.tsx` | The modal that appears for every action. Renders the title, fields, and submit button. *Touch this if the action popup opens but is blank, or the submit button is missing.* |
| `ActionPopup/fields/renderField.tsx` | Dispatches to the right field component based on field type. *Touch this if a specific field type isn't rendering — add it to the dispatch map here.* |

#### Action modals (`lens/actions/`)
*(Pop-up dialogs tied to specific actions — used when the standard ActionPopup isn't enough.)*

| File | What it shows + when you'd touch it |
|---|---|
| `AddNoteModal.tsx` | The "Add Note" popup. *Touch this if the note form is showing the wrong fields or the wrong note types.* |
| `AttachmentUploadModal.tsx` | The file upload popup. *Touch this to add new accepted file types (SVG, PowerPoint, CAD/DWG are already in), change the upload bucket target, or fix upload failures.* |
| `FileWarrantyClaimModal.tsx` | The popup for filing a warranty claim. *Touch this if the warranty claim form fields are wrong or the submit is broken.* |

#### Per-entity content files (`lens/entity/`)
*(Each entity type has one file controlling what appears on that entity's detail page and in what order.)*

| File | What it controls + when you'd touch it |
|---|---|
| `WorkOrderContent/index.tsx` | Work order detail page: which sections appear and where. Faults tab opens `WOFaultLinkModal`, Equipment tab opens `EquipmentPickerModal`. Tab label "Images" = key "uploads". `handleFaultLink`/`handleEquipmentLink` use `runAction` (toast feedback). Both link actions are `HIDDEN_FROM_DROPDOWN` (tab-inline only). |
| `WorkOrderContent/WOTabBodies.tsx` | Tab body components: `FaultsTabBody` (with `onLinkFault` dashed button), `EquipmentTabBody` (with `onAssignEquipment` dashed button), `SafetyTabBody`, `EmptyTab`. *Touch this if a tab shows the wrong content.* |
| `WorkOrderContent/WOModals.tsx` | ALL WO-specific modal components: `AddPartModal`, `AssignModal`, `AddChecklistItemModal`, `EditSOPModal`, `ArchiveWorkOrderModal`, `SetFrequencyModal`, `WOFaultLinkModal`. *Add new WO modals here — never create a separate file for a single WO modal.* |
| `EquipmentContent.tsx` | Equipment detail page layout. *Add a section here if you want it to appear on every equipment detail page.* |
| `FaultContent.tsx` | Fault detail page layout. *Touch this if a section is missing from the fault page that exists on other pages.* |
| `CertificateContent.tsx` | Certificate detail page layout. *Touch this to add the renewal history section, or reorder how certificate details are shown.* |
| `WarrantyContent.tsx` | Warranty detail page layout. *Touch this to add attachments to the warranty page or change section order.* |
| `PurchaseOrderContent.tsx` | Purchase order detail page layout. *Touch this if the PO detail page is missing a section.* |
| `ReceivingContent.tsx` | Receiving detail page layout. *Touch this if the packing list or discrepancy section isn't appearing.* |
| `ShoppingListContent.tsx` | Shopping list detail page layout. |
| `PartsInventoryContent.tsx` | Parts/inventory detail page layout. |
| `DocumentContent.tsx` | Document detail page layout. |
| `HandoverContent.tsx` | Handover export detail page layout. |
| `HoursOfRestContent.tsx` | Hours of rest detail page layout. |
| `HoRSignoffContent.tsx` | HoR signoff detail page layout. |

#### Reusable sections (`lens/sections/`)
*(Building blocks. Each one renders a specific section and can be dropped into any entity content file.)*

| File | What it shows + when you'd touch it |
|---|---|
| `ChecklistSection.tsx` | Checklist items with tick/text inputs and a batch submit button. *Touch this if the tick behaviour is wrong, items aren't saving, or the submit button is missing — across any entity that has a checklist.* |
| `NotesSection.tsx` | A thread of notes and comments with an "add note" input at the bottom. *Touch this if notes aren't appearing, the input field is missing, or new notes don't show without a refresh.* |
| `AttachmentsSection.tsx` | A grid of uploaded files with an upload button. *Touch this if the upload button is missing, files aren't displaying as thumbnails, or the download link is broken.* |
| `AuditTrailSection.tsx` | A timeline of every change ever made to the entity (who, what, when). *Touch this if the audit trail is empty when it shouldn't be, or entries are showing the wrong user or timestamp.* |
| `HistorySection.tsx` | A timeline of key events in the entity's life (status changes etc.). *Touch this if the history timeline is in the wrong order or showing duplicate events.* |
| `LedgerHistorySection.tsx` | The financial/transaction ledger for this entity. *Touch this if ledger entries aren't appearing or are showing the wrong amounts.* |
| `PartsSection.tsx` | Parts used in a work order with quantities and part numbers. *Touch this if parts aren't appearing in the work order, or quantities are wrong.* |
| `RelatedEquipmentSection.tsx` | Equipment linked to this entity. *Touch this if the related equipment list is empty or shows equipment from a different entity.* |
| `RenewalHistorySection.tsx` | History of certificate or warranty renewals. *Touch this if past renewals aren't showing on the certificate or warranty page.* |
| `KVSection.tsx` | Custom key-value data (flexible, custom fields). *Touch this if custom field values aren't displaying or the layout looks wrong.* |
| `LensFileViewer.tsx` | Embedded PDF viewer. *Touch this if PDFs aren't rendering inline or the viewer is the wrong size.* |
| `LensImageViewer.tsx` | Embedded image viewer. *Touch this if photos aren't showing or the image is broken.* |
| `ReceivingDiscrepancies.tsx` | Discrepancies found during goods receiving. *Touch this if discrepancy items aren't showing or the discrepancy flags are wrong.* |
| `ReceivingLabelPrint.tsx` | Barcode label printing for received items. *Touch this if the print button isn't generating labels.* |
| `ReceivingLinkedPO.tsx` | The purchase order linked to this receiving record. *Touch this if the linked PO isn't showing or links to the wrong PO.* |
| `ReceivingPackingList.tsx` | The packing list from this receiving record. *Touch this if packing list items aren't appearing correctly.* |
| `DocRowsSection.tsx` | Line items / rows within a document. *Touch this if document line items aren't rendering or are in the wrong order.* |
| `EquipmentPickerModal.tsx` | The modal you use to search for and link a piece of equipment. *Touch this if the equipment search inside the modal returns no results or links the wrong item.* |

---

### FRONTEND: `features/`
*(Domain-specific list page logic. Data fetching and column definitions for the list views.)*

| File | What it does + when you'd touch it |
|---|---|
| `entity-list/components/FilteredEntityList.tsx` | The list component on every list page — handles filtering, pagination, layout. *Touch this if something is broken across ALL list pages at once.* |
| `entity-list/components/EntityTableList.tsx` | Table layout for entity lists. *Touch this if the table structure itself is broken.* |
| `entity-list/components/EntityRecordRow.tsx` | A single row in any list. *Touch this to change how all list rows look — status pill position, what fields show per row, etc.* |
| `entity-list/components/FilterBar.tsx` | The filter input bar above every list. *Touch this if filter chips aren't appearing or the search input inside the list isn't working.* |
| `entity-list/hooks/useEntityList.ts` | Fetches list data from the backend. *Touch this if a list page loads but is empty, or isn't calling the right endpoint.* |
| `work-orders/columns.tsx` | Column definitions for the work orders list table. *Touch this to add, remove, or rename a column on the work orders list page.* |
| `work-orders/api.ts` | API calls for the work orders list. *Touch this if the work orders list endpoint is returning the wrong data.* |
| `work-orders/adapter.ts` | Converts raw API data to the shape the list component needs. *Touch this if work order data is loading but displaying with wrong field names.* |
| `work-orders/WorkOrderCalendar.tsx` | The calendar view showing work orders by date. *Touch this if the calendar is showing work orders on wrong dates or not rendering.* |
| `equipment/columns.tsx` | Column definitions for the equipment list. *Touch this to add a column to the equipment list page.* |
| `equipment/api.ts` | API calls for the equipment list. *Touch this if the equipment list is returning an error.* |
| `faults/api.ts` | API calls for the faults list. *Touch this if the faults list is returning an error or wrong data.* |
| `inventory/api.ts` | API calls for the inventory list. *Touch this if the inventory list isn't loading.* |
| `purchasing/columns.tsx` | Columns for the purchase orders list. *Touch this to change what columns appear on the PO list page.* |
| `receiving/columns.tsx` | Columns for the receiving list. *Touch this to add or change columns on the receiving list page.* |

---

## WHAT'S DEFERRED (do not touch without checking first)

| Item | Why it's waiting |
|---|---|
| `routes/handlers/internal_adapter.py` | Temporary bridge for documents and parts. Gets deleted once those domains are fully updated. Don't add anything new here. |
| `action_router/registry.py` reorganisation | 5,000+ lines, imported by ~40 files. Moving it safely requires a dedicated session with sign-off. |

---

## IMPORT RULES FOR AGENTS
*(Paste into any agent brief that touches backend code.)*

```
Canonical import paths (use these — not the old paths):
- from middleware.X import ...          (NOT action_router.middleware)
- from validators.X import ...          (NOT action_router.validators)
- from schemas.action_response_schema import ResponseBuilder
- from handlers.{domain}_handlers import ...

NEVER use git add -A. Stage only the exact files you changed.
Every claim must cite file:line. No guessing.
```

---

## DONE MEANS (paste into every agent brief)

```
Done = full chain verified:
  Button clicked → API returns 200 → correct row in database → correct data shown on screen

NOT done: "compiles", "no TypeScript errors", "tests pass", "looks right"
```
