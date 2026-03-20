# Design Reference: Signatures & Universal Action Popup

> **Status:** Design phase — not production yet. Informs future React component build.
> **Date:** 2026-03-17 (revised)
> **Context:** All 12 lens prototypes approved. These two patterns govern every user action across the PMS.

---

## 0. Architecture Principle

**The frontend is dumb. The backend is the brain.**

```
Frontend does ONLY:          Backend decides:
─────────────────────        ──────────────────────────────
render fields                what fields appear
show preview                 what is editable
collect signature            what can be linked
submit payload               what signature level is required
                             what data-gates block submission
                             what audit record gets created
                             what permissions are needed
```

The frontend is a **shell**. It receives a schema, renders it, collects input, sends it back. No business logic. No giant IF statement. No per-action UI code.

**Why this matters:** Vessel operators can configure action schemas per-vessel (add a field, change a signature level, make something required) without frontend code changes. The schema is the contract.

---

## 1. Two Surfaces — Read vs Mutate

Not all popups are equal. **Viewing should feel lighter than changing.**

### Read Overlay

Lightweight. No friction. Crew glances at things constantly.

```
┌─────────────────────────────────────┐
│  Equipment: E-007 Main Engine       │  ← entity title
│  ─────────────────────────────────  │
│  Running Hours: 12,847              │  ← kv-read rows
│  Location: Engine Room, Deck 2      │
│  Criticality: Safety-Critical       │
│  Last WO: WO-2024-0891 ←(link)     │  ← tappable entity links
│  ─────────────────────────────────  │
│                          [ Close ]  │  ← single dismiss
└─────────────────────────────────────┘
```

**Characteristics:**
- No signature component
- No submit button
- Entity links inside are tappable (navigate to that lens)
- Dismisses on backdrop tap or Close button
- Backend sends `mode: "read"` — frontend renders display-only

### Mutation Popup

Heavier. Schema-driven form. Signature-gated submission.

```
┌─────────────────────────────────────┐
│  Create Work Order                  │  ← title from schema
│  From FLT-0042                      │  ← subtitle (context)
│  ─────────────────────────────────  │
│  Equipment    E-007 Main Engine     │  ← kv-read (locked)
│  Title        [Emergency Valve___]  │  ← kv-edit (editable, prefilled)
│  Assigned To  [Chief Engineer   ▾]  │  ← person-assign
│  Priority     [Urgent           ▾]  │  ← select
│  Due Date     [2026-04-01       📅] │  ← date-pick
│  Photos       [+ Upload         📎] │  ← attachment
│  ─────────────────────────────────  │
│  ┌─ Data Gate ─────────────────┐    │
│  │ ⚠ Complete checklist before │    │  ← blocks submit until satisfied
│  │   sign-off (3/5 done)       │    │
│  └─────────────────────────────┘    │
│  ─────────────────────────────────  │
│  [ Confirm ]                        │  ← signature component (L1)
└─────────────────────────────────────┘
```

**Characteristics:**
- Schema-driven fields rendered in order
- Required fields block submission
- Data gates block signature until conditions met
- Signature component rendered at bottom (level from schema)
- Backend sends `mode: "mutate"` + full field schema

---

## 2. Signature Ladder — Graduated Confirmation Journey

Every action has a "weight." The signature type must match the consequence.

### Signature Levels

| Level | Name | UX Pattern | When Used | Regulatory |
|-------|------|-----------|-----------|-----------|
| **0** | Tap | Single button, no modal | Add note, upload photo, toggle checklist | None — audit log only |
| **1** | Confirm | Modal with summary + "Confirm" button | Submit shopping list, reassign WO, change status | ISM general |
| **2** | Attest | Modal with declaration text + **type full name** | HoR submit to HOD, certificate ack, handover sign-off | MLC 2006, STCW |
| **3** | Verify | Modal + **PIN or TOTP code** entry | Write-off parts, accept receiving (stock), approve PO spend | Financial/inventory |
| **4** | Wet Sign | **Drawn signature pad** (touch/stylus) + printed name + date | Class survey, PSC inspections, ISM audit, handover doc | Port State Control, Classification |
| **5** | Chain | Sequential multi-party — each approver gets own level | PO approval (crew→HOD→Captain), WO deferral (CE→Captain→Class) | ISM §10, SMS |

### Principle

Signature intensity scales with reversibility:
- Level 0 = instantly undoable → no modal at all
- Level 4 = creates legal document for Port State Control → full ceremony

### DB Payload Per Level

| Level | Stored Payload |
|-------|---------------|
| 0 | `{user_id, timestamp}` |
| 1 | `{user_id, timestamp, action_summary}` |
| 2 | `{user_id, timestamp, typed_name, declaration_text}` |
| 3 | `{user_id, timestamp, verification_method, action_summary}` |
| 4 | `{user_id, timestamp, signature_image, printed_name, device_info, declaration_text}` |
| 5 | `{chain_id, steps: [{user_id, level, timestamp, payload}...], status}` |

### Per-Entity Signature Mapping

| Entity | Action | Level |
|--------|--------|-------|
| Work Order | Mark checklist item | 0 |
| Work Order | Mark complete | 2 |
| Work Order | Defer | 5 (CE → Captain) |
| Hours of Rest | Enter hours | 0 |
| Hours of Rest | Submit to HOD | 2 |
| Hours of Rest | HOD approve | 2 |
| Receiving | Confirm receipt | 3 (PIN — affects stock) |
| Purchase Order | Approve spend | 5 (HOD → Purser/Captain) |
| Handover | Sign handover doc | 4 (wet — legal) |
| Certificate | Acknowledge reading | 1 |
| Parts | Write-off stock | 3 (PIN) |
| Fault | Log fault | 0 |
| Fault | Close fault | 1 |
| Shopping List | Submit for approval | 1 |
| Shopping List | Convert to PO | 2 |

---

## 3. Data Gates — No Sign-Off Until Data Is Complete

Some actions cannot be signed until the user has completed prerequisite data. The backend defines these gates. The frontend renders them as blockers above the signature component.

### Gate Types

| Gate | Condition | Example |
|------|-----------|---------|
| `checklist-complete` | All checklist items ticked | WO Mark Complete: "Complete all checklist items before sign-off" |
| `field-required` | Specific fields filled | Create WO: Title + Assigned To required |
| `note-required` | User must add a note/reason | Archive: "Add reason for archiving" |
| `attachment-required` | At least one file uploaded | Write-off: "Photo evidence required" |
| `linked-entity` | Must link at least one entity | Fault Close: "Link to resolving Work Order" |
| `time-logged` | Hours must be logged | WO Complete: "Log time spent" |

### How Gates Work

```
Backend schema includes:   gates: [
                             { type: "checklist-complete", message: "Complete all steps" },
                             { type: "field-required", fields: ["title", "assigned_to"] }
                           ]

Frontend renders:          ┌─ Gate ──────────────────────────┐
                           │ ⚠ Complete all steps (3/5 done) │
                           └────────────────────────────────-┘
                           [ Confirm ]  ← disabled until gates pass

When all gates pass:       ┌─ Gate ──────────────────────────┐
                           │ ✓ All steps complete             │
                           └─────────────────────────────────┘
                           [ Confirm ]  ← enabled
```

**The user never needs to "exit" the popup to complete prerequisites.** Gates update live as the user fills in data within the same popup. The popup loads with fields prefilled and gates evaluated — the user completes what's missing and signs in one flow.

---

## 4. Action Registry — Backend Schema Engine

### Schema Shape

```
ActionSchema {
  action_id:        string              // "create-work-order"
  entity_type:      string              // "work_order"
  mode:             "read" | "mutate"   // surface type
  title:            string              // "Create Work Order"
  subtitle?:        string              // "From Fault FLT-0042"
  signature_level:  0 | 1 | 2 | 3 | 4 | 5
  permissions:      string[]            // ["wo.create", "wo.assign"]
  prefill_from:     string[]            // ["current_entity", "user"]
  fields: [
    {
      key:           string             // "title"
      label:         string             // "Title"
      type:          FieldType          // "kv-edit"
      required?:     boolean            // true
      editable?:     boolean            // true (false = locked display)
      options?:      string[]           // ["Routine","Urgent","Critical"]
      entity_types?: string[]           // ["parts","cert","doc"]
      default?:      string | null      // "{{fault.title}}"
      prefill?:      string | null      // "{{fault.equipment.name}}"
    }
  ]
  gates?: [
    {
      type:          GateType           // "checklist-complete"
      message:       string             // "Complete all steps before sign-off"
      fields?:       string[]           // ["title", "assigned_to"]
    }
  ]
  preview_rules?: {
    show_summary:    boolean            // true = show before signature
    summary_fields:  string[]           // ["title", "assigned_to", "priority"]
  }
  audit: {
    event_type:      string             // "wo.created"
    include_fields:  string[]           // fields to store in audit trail
  }
}
```

### Prefill Pattern

Fields resolve values from context using template syntax:

```
"{{fault.title}}"              → "Starboard engine vibration"
"{{fault.equipment.name}}"     → "E-007 Main Engine"
"{{user.name}}"                → "Chief Engineer"
"{{part.qty}}"                 → "12"
```

Resolution rule: `{{$json.item || null}}` — if the path resolves, prefill. If not, render empty/null. **Never error on missing context.** The user fills in what the system can't prefill.

### Field Type Catalogue

Six functional classes, twelve concrete types:

| Class | Types | Purpose |
|-------|-------|---------|
| **Read** | `kv-read` | Display locked context (equipment name, fault ID) |
| **Edit** | `kv-edit`, `text-area`, `select`, `date-pick` | Collect user input |
| **Link** | `entity-search` | Search + link related entities (WO, fault, parts, cert) |
| **Upload** | `attachment` | File/image evidence |
| **Assign** | `person-assign` | Crew member picker |
| **Lifecycle** | `status-set`, `signature` | Status change + confirmation ceremony |

| Type | Behaviour | Example |
|------|----------|---------|
| `kv-read` | Display only, prefilled, locked | Equipment: "E-007 Main Engine" |
| `kv-edit` | Editable text, prefilled or empty | Title: "Emergency Valve Repair" |
| `text-area` | Multi-line free text | Description, notes, reason |
| `select` | Dropdown from backend-provided options | Priority, Status, Category, Reason |
| `date-pick` | Date selector | Due date, scheduled date |
| `entity-search` | Dropdown search across entity types | Link WO, fault, parts, cert, doc |
| `person-assign` | Crew member picker (from vessel roster) | Assign to Chief Engineer |
| `attachment` | File/image upload zone | Photos, documents, scans |
| `status-set` | Lifecycle transition selector | Complete / Archive / Draft / Delete |
| `signature` | Rendered per level (0-5) | Confirm btn / type name / PIN / wet sign / chain |

---

## 5. Frontend Components — What Gets Built

The frontend builds exactly **three things**:

### Component 1: `<ReadOverlay>`

```
Props:    { schema: ReadSchema, context: EntityContext }
Renders:  kv-read rows + entity links
Dismiss:  backdrop tap, Close button, Escape key
```

No form state. No validation. No signature. Just display.

### Component 2: `<MutationPopup>`

```
Props:    { schema: ActionSchema, context: EntityContext }
Renders:  fields (from schema) → gates (from schema) → signature (from level)
State:    field values, gate satisfaction, signature data
Submit:   payload = { field_values + signature_data + audit_metadata }
```

One component. Reads schema. Renders fields. Collects input. Shows gates. Renders signature. Submits.

**Internal structure:**

```
<MutationPopup>
  <PopupHeader title={schema.title} subtitle={schema.subtitle} />
  <FieldRenderer fields={schema.fields} values={state} onChange={update} />
  <GatePanel gates={schema.gates} satisfied={evaluate(state)} />
  <PreviewSummary rules={schema.preview_rules} values={state} />
  <SignatureBlock level={schema.signature_level} onSign={collect} />
  <SubmitBar disabled={!allGatesSatisfied || !signatureCollected} />
</MutationPopup>
```

### Component 3: Signature Components (one per level)

| Level | Component | Renders |
|-------|-----------|---------|
| 0 | — (no modal, inline tap) | Single button in lens view |
| 1 | `<ConfirmButton>` | Summary + "Confirm" button |
| 2 | `<AttestField>` | Declaration text + type-full-name input |
| 3 | `<PinVerify>` | PIN or TOTP code entry |
| 4 | `<SignaturePad>` | Canvas drawing area + printed name + date |
| 5 | `<ApprovalChain>` | Multi-step: shows chain progress, current approver's component |

### Field Renderers (one per type)

10 small components, each ~20-50 lines:

`KvReadField`, `KvEditField`, `TextAreaField`, `SelectField`, `DatePickField`, `EntitySearchField`, `PersonAssignField`, `AttachmentField`, `StatusSetField`, `SignatureField`

Each receives `{ field, value, onChange }`. That's it.

---

## 6. Request Lifecycle

```
User clicks dropdown action
  → Frontend sends: GET /api/actions/{action_id}?entity_id={id}
  → Backend returns: ActionSchema (with prefilled values resolved)

  IF mode = "read":
    → Render <ReadOverlay> with kv-read rows
    → Done (no submission)

  IF mode = "mutate":
    → Render <MutationPopup>
    → Fields prefilled from schema ({{path}} resolved server-side)
    → User fills remaining fields
    → Gates evaluate live as fields change
    → When all gates satisfied: signature component activates
    → User completes signature (per level)
    → Frontend sends: POST /api/actions/{action_id}
      Body: {
        entity_id,
        field_values: { key: value, ... },
        signature_data: { level, ... },
        client_metadata: { timestamp, device_info }
      }
    → Backend validates (permissions, gates, signature)
    → Backend executes action (DB mutations)
    → Backend creates audit trail record
    → Backend returns: { success, entity_id, next_action? }
    → Frontend closes popup, refreshes lens
```

**Key detail:** Prefill resolution happens **server-side**. The frontend never fetches related entities to build the popup — the backend resolves `{{fault.equipment.name}}` and sends the display value. Frontend just renders what it receives.

---

## 7. Examples

### Example: "Create Work Order from Fault" (L1 Confirm)

```json
{
  "action_id": "create-wo-from-fault",
  "entity_type": "work_order",
  "mode": "mutate",
  "title": "Create Work Order",
  "subtitle": "From FLT-0042",
  "signature_level": 1,
  "permissions": ["wo.create"],
  "prefill_from": ["fault:FLT-0042", "user"],
  "fields": [
    { "key": "equipment",   "label": "Equipment",   "type": "kv-read",       "prefill": "{{fault.equipment.name}}" },
    { "key": "fault",       "label": "Fault",        "type": "kv-read",       "prefill": "{{fault.id}}: {{fault.title}}" },
    { "key": "title",       "label": "Title",        "type": "kv-edit",       "required": true, "default": "{{fault.title}}" },
    { "key": "description", "label": "Description",  "type": "text-area",     "default": "{{fault.description}}" },
    { "key": "assigned_to", "label": "Assigned To",  "type": "person-assign", "required": true },
    { "key": "priority",    "label": "Priority",     "type": "select",        "options": ["Routine","Urgent","Critical"] },
    { "key": "due_date",    "label": "Due Date",     "type": "date-pick" },
    { "key": "related",     "label": "Related",      "type": "entity-search", "entity_types": ["parts","cert","doc"] },
    { "key": "photos",      "label": "Photos",       "type": "attachment" }
  ],
  "gates": [
    { "type": "field-required", "fields": ["title", "assigned_to"], "message": "Title and assignee required" }
  ],
  "preview_rules": { "show_summary": true, "summary_fields": ["title", "assigned_to", "priority"] },
  "audit": { "event_type": "wo.created", "include_fields": ["title", "assigned_to", "priority", "equipment"] }
}
```

### Example: "Write Off Part" (L3 PIN — high security)

```json
{
  "action_id": "write-off-part",
  "entity_type": "part",
  "mode": "mutate",
  "title": "Write Off Stock",
  "signature_level": 3,
  "permissions": ["parts.write_off"],
  "prefill_from": ["part"],
  "fields": [
    { "key": "part_name",     "label": "Part",            "type": "kv-read",    "prefill": "{{part.name}}" },
    { "key": "current_stock", "label": "Current Stock",   "type": "kv-read",    "prefill": "{{part.qty}}" },
    { "key": "qty",           "label": "Qty to Write Off","type": "kv-edit",    "required": true },
    { "key": "reason",        "label": "Reason",          "type": "select",     "options": ["Damaged","Expired","Lost","Used"] },
    { "key": "notes",         "label": "Notes",           "type": "text-area" },
    { "key": "evidence",      "label": "Photo Evidence",  "type": "attachment" }
  ],
  "gates": [
    { "type": "field-required", "fields": ["qty", "reason"], "message": "Quantity and reason required" },
    { "type": "attachment-required", "message": "Photo evidence required for write-off" }
  ],
  "audit": { "event_type": "part.written_off", "include_fields": ["part_name", "qty", "reason", "current_stock"] }
}
```

### Example: "Mark Work Order Complete" (L2 Attest + Data Gate)

```json
{
  "action_id": "complete-work-order",
  "entity_type": "work_order",
  "mode": "mutate",
  "title": "Mark Complete",
  "signature_level": 2,
  "permissions": ["wo.complete"],
  "prefill_from": ["work_order", "user"],
  "fields": [
    { "key": "wo_title",     "label": "Work Order",     "type": "kv-read",   "prefill": "{{wo.id}}: {{wo.title}}" },
    { "key": "equipment",    "label": "Equipment",      "type": "kv-read",   "prefill": "{{wo.equipment.name}}" },
    { "key": "hours_spent",  "label": "Hours Spent",    "type": "kv-edit",   "required": true },
    { "key": "completion_notes", "label": "Notes",      "type": "text-area" },
    { "key": "photos",       "label": "Evidence",       "type": "attachment" }
  ],
  "gates": [
    { "type": "checklist-complete", "message": "Complete all checklist items before sign-off" },
    { "type": "time-logged", "message": "Log time spent" }
  ],
  "audit": { "event_type": "wo.completed", "include_fields": ["wo_title", "hours_spent", "completion_notes"] }
}
```

### Example: "View Equipment" (Read Overlay)

```json
{
  "action_id": "view-equipment",
  "entity_type": "equipment",
  "mode": "read",
  "title": "Equipment Details",
  "fields": [
    { "key": "name",          "label": "Name",           "type": "kv-read",  "prefill": "{{equipment.name}}" },
    { "key": "location",      "label": "Location",       "type": "kv-read",  "prefill": "{{equipment.location}}" },
    { "key": "running_hours", "label": "Running Hours",   "type": "kv-read",  "prefill": "{{equipment.running_hours}}" },
    { "key": "criticality",   "label": "Criticality",     "type": "kv-read",  "prefill": "{{equipment.criticality}}" },
    { "key": "last_wo",       "label": "Last Work Order", "type": "kv-read",  "prefill": "{{equipment.last_wo.id}}: {{equipment.last_wo.title}}" }
  ]
}
```

---

## 8. Action → Entity Matrix

Every dropdown action across all 12 lenses maps to a schema:

| Entity | Dropdown Actions | Mode | Sig Levels |
|--------|-----------------|------|-----------|
| **Work Order** | Edit Details, Add Note, Log Hours, Reassign, Archive | mutate | 1,0,0,1,1 |
| **Equipment** | Create WO, Log Fault, Edit Details, Log Running Hours | mutate | 1,0,1,0 |
| **Fault** | Edit Details, Add Comment, Link to Item, Reassign, Mark Complete, Archive | mutate | 1,0,1,1,1,1 |
| **Certificate** | Upload Renewed, Edit Details, Print | mutate | 2,1,0 |
| **Parts** | Adjust Stock, Raise PO, Write Off, Edit Details | mutate | 1,1,3,1 |
| **Purchase Order** | Edit Details, Add Note, Approve, Receive Goods | mutate | 1,0,5,3 |
| **Receiving** | Confirm Receipt, Flag Discrepancy, Print Labels | mutate | 3,1,0 |
| **Shopping List** | Edit Details, Add Item, Submit for Approval, Convert to PO | mutate | 1,0,1,2 |
| **Document** | Upload Revision, Edit Details, Acknowledge | mutate | 1,1,1 |
| **Warranty** | File Claim, Edit Details, Link Equipment | mutate | 1,1,1 |
| **Hours of Rest** | Save Template, Edit Template, Submit to HOD | mutate | 0,0,2 |
| **Handover** | Sign, View Prior | mutate/read | 4,0 |

**Total: ~40-50 unique action schemas. Two frontend components serve them all (`<ReadOverlay>` + `<MutationPopup>`).**

---

## 9. Storage & Configuration

### Action Registry Table

```sql
CREATE TABLE action_schemas (
  action_id       TEXT PRIMARY KEY,
  entity_type     TEXT NOT NULL,
  mode            TEXT NOT NULL CHECK (mode IN ('read', 'mutate')),
  title           TEXT NOT NULL,
  subtitle_tpl    TEXT,                          -- template with {{}} placeholders
  signature_level SMALLINT NOT NULL DEFAULT 1,
  permissions     JSONB NOT NULL DEFAULT '[]',
  fields          JSONB NOT NULL,                -- array of field definitions
  gates           JSONB DEFAULT '[]',            -- array of gate definitions
  preview_rules   JSONB DEFAULT '{}',
  audit_config    JSONB NOT NULL,
  active          BOOLEAN DEFAULT TRUE,
  vessel_id       UUID REFERENCES vessels(id),   -- NULL = global default
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);
```

**Why DB over JSON config:** Per-vessel overrides. A vessel operator can add a required field or raise a signature level without a code deploy. The `vessel_id` column allows vessel-specific schemas to override the global default.

**Fallback chain:** `vessel-specific schema → global schema → 404`

### Alternative: JSON Config (simpler, version-controlled)

```
/config/action-schemas/
  create-wo-from-fault.json
  write-off-part.json
  complete-work-order.json
  ...
```

Both options work. DB is better for multi-vessel SaaS. JSON is better for single-vessel or early development.

---

## 10. Production Path

When moving to React:

### Frontend (3 components + renderers)

1. `<ReadOverlay>` — display-only surface, entity links, dismiss
2. `<MutationPopup>` — schema-driven form + gates + signature + submit
3. Signature components (5): `<ConfirmButton>`, `<AttestField>`, `<PinVerify>`, `<SignaturePad>`, `<ApprovalChain>`
4. Field renderers (10): one per field type, each ~20-50 lines
5. `<GatePanel>` — renders gate status, disables submit until all pass

### Backend (3 endpoints + registry)

1. `GET /api/actions/{action_id}?entity_id={id}` — returns resolved schema
2. `POST /api/actions/{action_id}` — validates + executes + audits
3. `GET /api/actions?entity_type={type}` — returns available actions for dropdown
4. `action_schemas` table or JSON registry

### Integration

Each lens dropdown item calls: `openAction(action_id, entity_id)`
→ Frontend fetches schema → decides `<ReadOverlay>` or `<MutationPopup>` based on `mode`
→ Done. No per-entity popup code.

---

## 11. Summary

**In one sentence:** Build one popup shell, powered by schema, with backend-controlled logic, and different signature levels based on action risk.

**What the frontend builds:**
- `<ReadOverlay>` for viewing (lightweight, no friction)
- `<MutationPopup>` for changing (heavier, gated, signed)
- 10 field renderers + 5 signature components + 1 gate panel

**What the backend controls:**
- What fields appear and their order
- What's editable vs locked
- What's required vs optional
- What data gates block submission
- What signature level is needed
- What audit trail gets created
- What permissions are checked

**What this eliminates:**
- Per-action popup components (0 needed — was heading toward ~50)
- Frontend business logic (0 — backend decides everything)
- Hardcoded field lists (0 — schema-driven)
- "Exit popup to complete prerequisite" UX (0 — gates resolve in-popup)

The lens prototypes already define which actions exist per entity (the dropdown menus). This document defines HOW those actions execute.
