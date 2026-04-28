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

| File | Plain English |
|---|---|
| `apps/api/pipeline_service.py` | Starts the backend server. Registers all the URL routes. Like the front door of the building. |
| `apps/api/combined_service.py` | Runs the server plus 5 background workers at the same time on Render. Don't touch unless changing how the server starts. |

---

### BACKEND: `routes/`
*(These files just receive a web request and hand it to the right handler. No logic here.)*

| File | Plain English |
|---|---|
| `action_execution_routes.py` | Receives every button-click action from the frontend. The single entry point for all actions. |
| `entity_routes.py` | Sends back all the data for an entity detail page (e.g. all the work order information when you open a work order). |
| `vessel_surface_routes.py` | Sends back the home page / dashboard data. |
| `document_routes.py` | Document search and CRUD requests. |
| `part_routes.py` | Parts and equipment list requests. |
| `hours_of_rest_routes.py` | Hours of rest data requests. |
| `handover_export_routes.py` | Handover PDF generation requests. |
| `import_routes.py` | File import (CSV/XLSX) requests. |
| `ledger_routes.py` | Audit ledger download requests. |
| `notification_routes.py` | Notification fetch requests. |
| `related_routes.py` | Legacy related-entity requests. (Old, kept for compatibility.) |
| `related_signal_routes.py` | Related-entity discovery using signals. |
| `context_navigation_routes.py` | Related-entity discovery using database relationships. |
| `attachment_upload.py` | File upload requests. Passes the file to Supabase storage. |
| `receiving_upload.py` | Receiving item uploads. |
| `receiving_label_routes.py` | Generates barcode labels for received items. |
| `purchase_order_pdf_route.py` | Generates purchase order PDFs. |
| `shopping_list_pdf_route.py` | Generates shopping list PDFs. |
| `email.py` | Email integration requests (main). |
| `email_inbox_routes.py` | Email inbox data. |
| `email_thread_routes.py` | Email thread data. |
| `email_link_routes.py` | Requests to link an email to an entity. |
| `email_sync_routes.py` | Email sync trigger requests. |
| `auth_routes.py` | Microsoft login token exchange. |
| `attention_routes.py` | "Needs attention" priority data. |
| `decisions_routes.py` | Decision history data. |
| `orchestrated_search_routes.py` | Main search requests. |
| `f1_search_streaming.py` | Live streaming search (results appear as you type). |
| `search_streaming.py` | Old streaming search. Kept but not used. |
| `rag_endpoint.py` | AI question-answering requests. |
| `routes/handlers/__init__.py` | The lookup table. Maps every action name to the function that handles it. If an action returns 404, it's probably missing from here. |
| `routes/handlers/internal_adapter.py` | Temporary bridge for document and parts actions that haven't been updated yet. Will be deleted once those are updated. |

---

### BACKEND: `handlers/`
*(This is where all the real work happens. One file per domain. If a button does the wrong thing, it's in here.)*

| File | Plain English |
|---|---|
| `work_order_handlers.py` | Everything work orders do: create, update, close, assign, checklist, frequency spawn. |
| `equipment_handler.py` | Everything equipment does: status, notes, hours, manuals, archive. |
| `fault_handler.py` | Everything faults do: create, update, resolve, link parts, notes. |
| `warranty_handlers.py` | Everything warranty claims do: draft, file, email, notes, audit. |
| `certificate_handlers.py` | Everything certificates do: register, renew, expire, notes. |
| `inventory_handlers.py` | Inventory/stock management logic. |
| `part_handlers.py` | Individual part lifecycle: create, update, reorder. |
| `purchase_order_handlers.py` | Purchase order creation and status tracking. |
| `receiving_handlers.py` | Goods receiving and acceptance logic. |
| `shopping_list_handlers.py` | Shopping list creation and item management. |
| `hours_of_rest_handlers.py` | Hours of rest recording and compliance checks. |
| `handover_handlers.py` | Handover workflow: draft, sign, countersign, export. |
| `document_handler.py` | Document creation, update, metadata. |
| `document_comment_handlers.py` | Comments on documents. |
| `attachment_comment_handlers.py` | Comments on attachments. |
| `entity_lens_handlers.py` | Builds the full data package sent to any entity detail page. |
| `list_handlers.py` | Generic list queries used by multiple domains. |
| `shared_mutation_handlers.py` | Generic "add note", "update field" logic used across domains. |
| `shared_read_handlers.py` | Generic "view entity", "list items" logic used across domains. |
| `universal_handlers.py` | "Soft delete" and "archive" logic, shared across all domains. |
| `email_handlers.py` | Email reading, thread management, linking to entities. |
| `media_handlers.py` | Photo and image attachment handling. |
| `manual_handlers.py` | Manual task and procedure handling. |
| `delivery_compliance_handlers.py` | Compliance checks on deliveries. |
| `compliance_handler.py` | General compliance status and audit logic. |
| `pm_handler.py` | Preventive maintenance logic. |
| `context_navigation_handlers.py` | Finds related entities using database relationships. |
| `related_signal_handlers.py` | Finds related entities using signals. |
| `related_handlers.py` | Old related-entity logic. Kept for compatibility. |
| `ledger_utils.py` | Writes entries to the audit ledger. Used by handlers after any important action. |
| `schema_mapping.py` | Lookup table: entity type name → database table name. |
| `db_client.py` | Creates a database connection that enforces who can see what data. |
| `stub_handlers.py` | Placeholder functions for actions that aren't built yet. Returns a "not implemented" response. |
| `equipment_utils.py` | Helper calculations for equipment (running hours, status checks). |

---

### BACKEND: `action_router/`
*(Controls which actions appear on screen and what they're called. No database writes here.)*

| File | Plain English |
|---|---|
| `registry.py` | The master list of every action in the system. Defines: action name, what fields it shows, who can use it, what it's called in the UI. **If you want to add a new action, start here.** |
| `entity_actions.py` | Rules for when each action is visible. E.g. "only show Close Work Order if status is open". **If an action isn't appearing when it should, check here.** |
| `entity_prefill.py` | When you open an action form, some fields are pre-filled. This file maps which fields to pre-fill for which action on which entity. |
| `ledger_metadata.py` | Maps each action name to the right audit log entry type. |
| `logger.py` | Records every action execution to the database for analytics. |

#### `action_router/dispatchers/`
*(Thin wrappers that unpack request data and call the right handler. Normally don't need to touch these.)*

| File | Plain English |
|---|---|
| `index.py` | Temporary compatibility layer for old document/parts actions. Will be deleted. |
| `document.py` | Passes document actions to the document handler. |
| `parts.py` | Passes parts actions to the parts handler. |
| `p3.py` | Passes read-only actions (view document etc.) to the right handler. |
| `shared.py` | Shared helper utilities used by the dispatchers above. |

---

### BACKEND: `middleware/`
*(Runs before every request. Security, validation, rate limiting.)*

| File | Plain English |
|---|---|
| `auth.py` | Checks your login token is valid. Looks up which vessel you're on. Checks your role. Every request goes through here first. |
| `action_security.py` | Extra security checks on actions: does this user own this entity? Is the vessel frozen? Has this action already been run (duplicate prevention)? |
| `action_gating.py` | Decides if an action needs a confirmation step (like "are you sure?") or can run automatically. |
| `handover_gating.py` | Controls which roles can add things to a handover, per entity type. |
| `state_machine.py` | Validates status changes. E.g. you can't go from "closed" back to "draft". |
| `validation_middleware.py` | Checks that UUIDs look like UUIDs, strings aren't too long, quantities are positive numbers. |
| `vessel_access.py` | For fleet users who have access to multiple vessels: checks they're allowed to view the vessel they're requesting. |
| `rate_limit.py` | Prevents too many requests per second from flooding the server. |

---

### BACKEND: `validators/`
*(Checks that data is correct before it's used.)*

| File | Plain English |
|---|---|
| `jwt_validator.py` | Validates the login token sent with every request. |
| `yacht_validator.py` | Checks the user has access to the vessel they're requesting. |
| `role_validator.py` | Checks the user's role allows the action they're trying to do. |
| `rls_entity_validator.py` | Prevents one vessel from accessing another vessel's data. Critical security check. |
| `field_validator.py` | Checks individual field values (e.g. email format, date format). |
| `schema_validator.py` | Checks the whole action payload matches the expected shape. |
| `ownership.py` | Checks an entity (e.g. a work order) belongs to the vessel making the request. |
| `validation_result.py` | The standard "pass/fail" wrapper returned by all validators. |

---

### BACKEND: `schemas/`
*(Defines what every API response looks like.)*

| File | Plain English |
|---|---|
| `action_response_schema.py` | The standard wrapper around every response. Every handler uses `ResponseBuilder` from here to format its response. If the response shape is wrong, look here. |

---

### BACKEND: `services/`
*(Complex business features that don't fit in a single handler.)*

| File | Plain English |
|---|---|
| `import_service.py` | The engine that processes CSV/XLSX file imports. Dry-run mode, then commit mode. |
| `hyper_search.py` | Runs the F1 search database call and manages the connection. |
| `decision_engine.py` | Reads the policy config files (E017, E019) and decides which actions to suggest and how confident to be. |
| `action_surfacing.py` | Decides which actions to show as "suggested" based on entity state. |
| `handover_export_service.py` | Builds the handover PDF/HTML with all items, then seals it. |
| `handover_microservice_client.py` | Talks to the separate handover microservice. |
| `file_reference_resolver.py` | When an import file references another file, this resolves the path. |
| `linking_ladder.py` | Tries to automatically link entities to each other based on content similarity. |
| `cache.py` | Stores frequently-used data in memory so the database isn't hit every time. |
| `rate_limit.py` | Rate limiter specifically for the live streaming search (different from middleware rate limiter). |
| `entity_serializer.py` | Converts an entity's data into a text string so it can be indexed for search. |
| `scoring_engine.py` | Scores search results for relevance. |
| `email_sync_service.py` | Pulls emails from Microsoft Outlook into the app. |
| `email_search_service.py` | Searches across stored emails. |
| `email_link_service.py` | Automatically links emails to entities (work orders, equipment etc.) based on content. |
| `email_suggestion_service.py` | Suggests actions based on email content. |

---

### BACKEND: `workers/`
*(Background jobs that run automatically. Not triggered by user clicks.)*

| File | Plain English |
|---|---|
| `projection_worker.py` | Runs in the background indexing entities for search. Keeps the search index up to date. |
| `embedding_worker_1536.py` | Generates AI embeddings (numerical representations) of entity text for semantic search. |
| `extraction_worker.py` | Downloads documents and extracts their text content for search indexing. |
| `email_watcher_worker.py` | Watches for new emails and processes them automatically. |
| `nightly_certificate_expiry.py` | Runs every night. Checks if any certificates are expiring soon and creates alerts. |
| `nightly_feedback_loop.py` | Runs every night. Checks extraction quality and adjusts. |

---

### BACKEND: `evidence/`
*(Production code for the ledger export. Not test files — don't delete.)*

| File | Plain English |
|---|---|
| `sealing.py` | When you export the audit ledger as a PDF, this seals it with a legal timestamp so it can't be tampered with. |
| `fonts/` | Font files used when generating sealed PDFs. |
| `icc/` | Colour profile used when generating sealed PDFs. |

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
*(Visual design. Colours, spacing, sizes. All values come from tokens — never hardcode.)*

| File | Plain English |
|---|---|
| `styles/tokens.css` | The single source of truth for colours, sizes, and spacing. Every visual value in the app comes from here. **If you want to change a colour or size globally, edit here.** |
| `styles/globals.css` | Base styles applied to the whole page (fonts, resets). |
| `styles/lens.css` | Styles specific to entity detail pages. |
| `styles/spotlight.css` | Styles for the search overlay. |

---

### FRONTEND: `contexts/`
*(Shared state available to the whole app.)*

| File | Plain English |
|---|---|
| `AuthContext.tsx` | Stores who is logged in, their role, their vessel. Available everywhere. |
| `VesselContext.tsx` | Stores which vessel is currently active (for fleet users who can switch). |
| `EntityLensContext.tsx` | On a detail page: stores the entity data and handles action execution. |
| `BackdropContext.tsx` | Controls the animated background orb effect on successful saves. |

---

### FRONTEND: `hooks/`
*(Reusable data-fetching logic. These talk to the backend and return data to components.)*

| File | Plain English |
|---|---|
| `useAuth.ts` | Get the current user, their login status, login/logout functions. |
| `useActiveVessel.ts` | Get the current active vessel and the list of all vessels for this user. |
| `useEntityLens.ts` | Fetch all the data for an entity detail page, plus run actions on it. |
| `useActionHandler.ts` | Handle clicking an action button: loading state, error handling, confirmation step. |
| `useCelesteSearch.ts` | Run a search query and get results back. |
| `useEntityLedger.ts` | Fetch the ledger/transaction history for an entity. |
| `useNeedsAttention.ts` | Fetch the list of items flagged as needing attention. |
| `useRelated.ts` | Fetch related entities for the "related" panel. |
| `useRelatedDrawer.ts` | Open/close the related entities side drawer. |
| `useEmailData.ts` | Fetch email inbox and thread data. |
| `useReadBeacon.ts` | Mark an entity as "viewed" when the detail page opens. |

---

### FRONTEND: `lib/`
*(Utilities and client-side logic. Not visual — pure functions and API calls.)*

| File | Plain English |
|---|---|
| `apiClient.ts` | The main HTTP client. Adds your login token and vessel ID to every request. Handles token refresh. **If API calls are failing with auth errors, start here.** |
| `actionClient.ts` | Specifically sends action execution requests to the backend. |
| `authHelpers.ts` | Helper functions: get your token, get your vessel ID, handle a 401 error. |
| `tokenRefresh.ts` | Keeps your login token fresh so you don't get logged out unexpectedly. |
| `apiBase.ts` | Stores the backend URL. Changes based on whether you're in development or production. |
| `supabaseClient.ts` | The Supabase database client for the frontend (auth only). |
| `field-schema.ts` | Defines which form fields should be hidden, shown as read-only, or auto-filled. If a form field is appearing when it shouldn't, or is missing a label, check here. |
| `entityRoutes.ts` | Maps entity types to their URL. E.g. "work_order" → "/work-orders". Used to build links. |
| `utils.ts` | Small helper functions used everywhere: format a date, merge CSS class names, debounce a function. |
| `normalizeWarranty.ts` | Cleans up warranty data into a consistent shape before displaying it. |
| `spotlightGrouping.ts` | Groups search results by category for display in the search overlay. |
| `handoverExportClient.ts` | API calls for handover export actions (acknowledge, countersign, submit). |
| `documentLoader.ts` | Fetches the document list and builds the folder tree structure. |
| `domain/catalog.ts` | Master list of entity types with their display names and metadata. |
| `filters/catalog.ts` | Defines what filters are available for each entity type. |
| `filters/infer.ts` | Automatically suggests filters based on what you've typed. |
| `filters/execute.ts` | Applies active filters to a list of results. |
| `actions/registry.ts` | Frontend copy of the action registry — action names, display labels, icons. |
| `actions/executor.ts` | Sends actions to the backend and handles the response (success/error/confirmation). |
| `actions/handlers/workOrders.ts` | Frontend-side work order action logic (what to do after the backend responds). |
| `actions/handlers/equipment.ts` | Frontend-side equipment action logic. |
| `actions/handlers/inventory.ts` | Frontend-side inventory action logic. |
| `actions/handlers/procurement.ts` | Frontend-side procurement/purchasing action logic. |
| `actions/handlers/handover.ts` | Frontend-side handover action logic. |
| `actions/handlers/compliance.ts` | Frontend-side compliance action logic. |

---

### FRONTEND: `components/shell/`
*(The persistent frame around every page: topbar, sidebar, subbar.)*

| File | Plain English |
|---|---|
| `AppShell.tsx` | The layout grid that places the topbar, sidebar, and body. The skeleton of every page. |
| `Topbar.tsx` | The bar at the top: vessel name dropdown, search icon, notification bell, user avatar. |
| `Sidebar.tsx` | The left navigation bar with links to each domain and their item counts. |
| `Subbar.tsx` | The bar below the topbar: breadcrumb trail, scoped search, active filter chips. |
| `VesselSurface.tsx` | The home page content showing vessel status, vital signs, and overview data. |
| `SearchOverlay.tsx` | The full-screen search that appears when you click the search icon. |
| `NotificationBell.tsx` | The bell icon and the dropdown list of notifications. |
| `SettingsModal.tsx` | The settings panel. |

---

### FRONTEND: `components/lens/`
*(Everything on entity detail pages.)*

| File | Plain English |
|---|---|
| `EntityLensPage.tsx` | The wrapper for every detail page. Coordinates the header, tabs, action button, and content. |
| `LensGlassHeader.tsx` | The top section of a detail page: entity name, status pill, action button. |
| `LensTabBar.tsx` | The row of tabs on a detail page (e.g. "Overview", "Checklist", "History"). |
| `RelatedDrawer.tsx` | The panel that slides in from the right showing related entities. |
| `CollapsibleSection.tsx` | A section that can be expanded/collapsed with a click. Used inside content pages. |
| `ActionPopup/ActionPopup.tsx` | The modal form that appears when you click any action. Handles the title, fields, submit button. |
| `ActionPopup/fields/renderField.tsx` | Looks at the field type and renders the right input component. The dispatcher for form fields. |

#### Per-entity content files (`lens/entity/`)
*(Each entity type has its own file that defines what appears on its detail page and in what order.)*

| File | What it controls |
|---|---|
| `WorkOrderContent/index.tsx` | Work order detail page layout and section order |
| `WorkOrderContent/WOTabBodies.tsx` | Content inside each work order tab |
| `WorkOrderContent/WOModals.tsx` | Modals specific to work order actions (e.g. SetFrequencyModal) |
| `EquipmentContent.tsx` | Equipment detail page layout |
| `FaultContent.tsx` | Fault detail page layout |
| `CertificateContent.tsx` | Certificate detail page layout |
| `WarrantyContent.tsx` | Warranty detail page layout |
| `PurchaseOrderContent.tsx` | Purchase order detail page layout |
| `ReceivingContent.tsx` | Receiving detail page layout |
| `ShoppingListContent.tsx` | Shopping list detail page layout |
| `PartsInventoryContent.tsx` | Parts/inventory detail page layout |
| `DocumentContent.tsx` | Document detail page layout |
| `HandoverContent.tsx` | Handover export detail page layout |
| `HoursOfRestContent.tsx` | Hours of rest detail page layout |
| `HoRSignoffContent.tsx` | Hours of rest signoff detail page layout |

#### Reusable sections (`lens/sections/`)
*(These are building blocks. They render a specific section and can be placed in any entity content file.)*

| File | What it shows |
|---|---|
| `ChecklistSection.tsx` | A list of checklist items with tick/text inputs and a submit button |
| `NotesSection.tsx` | A thread of notes/comments with an "add note" input |
| `AttachmentsSection.tsx` | A grid of uploaded files with an upload button |
| `AuditTrailSection.tsx` | A timeline of every change ever made to this entity (who did what, when) |
| `HistorySection.tsx` | A timeline of key events in the entity's life |
| `LedgerHistorySection.tsx` | The financial/transaction ledger for this entity |
| `PartsSection.tsx` | Parts used in a work order with quantities |
| `RelatedEquipmentSection.tsx` | Equipment linked to this entity |
| `RenewalHistorySection.tsx` | History of certificate or warranty renewals |
| `KVSection.tsx` | Custom key-value data (flexible fields) |
| `LensFileViewer.tsx` | Embedded PDF viewer |
| `LensImageViewer.tsx` | Embedded image viewer |
| `ReceivingDiscrepancies.tsx` | Discrepancies found during goods receiving |
| `ReceivingLabelPrint.tsx` | Print barcode labels for received items |
| `ReceivingLinkedPO.tsx` | The purchase order linked to this receiving record |
| `ReceivingPackingList.tsx` | The packing list from this receiving record |
| `DocRowsSection.tsx` | Line items / rows within a document |
| `EquipmentPickerModal.tsx` | Modal to search and link a piece of equipment |

---

### FRONTEND: `features/`
*(Domain-specific list page logic. Data fetching and column definitions for the list views.)*

| File | Plain English |
|---|---|
| `entity-list/components/FilteredEntityList.tsx` | The list component used on every list page. Handles filtering, pagination, and display. |
| `entity-list/components/EntityTableList.tsx` | Table layout for entity lists. |
| `entity-list/components/EntityRecordRow.tsx` | A single row in any list. Edit here to change how all list rows look. |
| `entity-list/components/FilterBar.tsx` | The filter input bar above a list. |
| `entity-list/hooks/useEntityList.ts` | Fetches entity list data from the backend. |
| `work-orders/columns.tsx` | Which columns appear in the work orders list. |
| `work-orders/api.ts` | API calls for the work orders list. |
| `work-orders/adapter.ts` | Converts raw work order data into the shape the list needs. |
| `work-orders/WorkOrderCalendar.tsx` | The calendar view of work orders. |
| `equipment/columns.tsx` | Which columns appear in the equipment list. |
| `equipment/api.ts` | API calls for the equipment list. |
| `faults/api.ts` | API calls for the faults list. |
| `inventory/api.ts` | API calls for the inventory list. |
| `purchasing/columns.tsx` | Which columns appear in the purchase orders list. |
| `receiving/columns.tsx` | Which columns appear in the receiving list. |

---

## WHAT'S DEFERRED (not yet done — do not touch these without checking)

| Item | Why it's waiting |
|---|---|
| `routes/handlers/internal_adapter.py` | Temporary bridge for documents and parts. Gets deleted once those domains are rewritten. Don't add new things to it. |
| `action_router/registry.py` reorganisation | It's 5,000+ lines and imported everywhere. Moving it requires a full session with sign-off first. |

---

## IMPORT RULES FOR AGENTS
*(If you're writing a prompt for an agent that touches backend code, include these lines.)*

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

## DONE MEANS (include this in every agent brief)

```
Done = full chain verified:
  Button clicked → API returns 200 → correct row in database → correct data shown on screen

NOT done: "compiles", "no TypeScript errors", "tests pass", "looks right"
```
