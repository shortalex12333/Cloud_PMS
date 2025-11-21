Because nothing is built yet, now is exactly the time to define a shared framework so that:

every micro-action

every workflow

every frontend component

every n8n workflow

every Python service later

…all speak the same language.

And yes:

⭐ All 6 workflow archetypes can share the same endpoint format.

The only difference is the body (payload), not the endpoint.

This is exactly how you future-proof CelesteOS.

Below is the exact framework you should build into n8n.

⭐ THE UNIFIED ACTION ENDPOINT MODEL

Every n8n workflow accepts the same JSON envelope, regardless of action type.

Incoming JSON (from Router)
{
  "action_name": "create_work_order",
  "context": {
    "equipment_id": "123e4567",
    "fault_id": null,
    "selected_text": null
  },
  "parameters": {
    "user_input": "Create a work order for chiller B service",
    "date_range": null,
    "priority": "medium"
  },
  "session": {
    "user_id": "crew123",
    "yacht_id": "yacht001"
  }
}

⭐ OUTGOING JSON (back to Frontend)

This format must not change across the ecosystem.

{
  "card_type": "work_order",
  "card": { 
    "title": "Chiller B Service",
    "fields": {...},
    "sections": [...]
  },
  "micro_actions": [
    { "action_name": "add_note_to_work_order", "label": "Add Note" },
    { "action_name": "attach_photo_to_work_order", "label": "Attach Photo" },
    { "action_name": "mark_work_order_complete", "label": "Mark Complete" }
  ],
  "streaming_chunks": [
    "Work order created...",
    "Pulling related manual section...",
    "Attaching recommended parts..."
  ]
}


Exactly the same envelope is used for:

view workflows

update workflows

create workflows

export workflows

RAG workflows

linking workflows

Only the content inside card and micro_actions changes.

⭐ WHY THIS WORKS

Because:

The front end only needs to understand one response structure.

The router only needs to pass one request format into n8n.

n8n workflows are simple: they read action_name and branch.

Adding new actions is trivial → no breaking change.

Adding Python services later is easy → they simply follow the same envelope.

This is exactly how we prevent chaos when adding 70+ micro-actions.

⭐ ARCHITECTURE (WHAT YOU BUILD NOW)
1. ONE n8n HTTP Trigger per archetype

You only need:

/workflows/view
/workflows/update
/workflows/create
/workflows/export
/workflows/rag
/workflows/linking


(or even /workflow/router if you want to get fancy)

Each is a single n8n workflow with a switch node:

Switch on: action_name
Case: "show_manual_section" → do X
Case: "show_equipment_history" → do Y
Case: "search_documents" → do Z
...
Default: unsupported_action

⭐ WHAT CHANGES BETWEEN WORKFLOW TYPES?

Only the payload you need from parameters or context.

Example differences:
View Workflow Needs:

ids

query text

filters

user_input

Update Workflow Needs:

ids

updated fields

new values

Create Workflow Needs:

record data

references

optional description

Export Workflow Needs:

date range

output type

destination email

RAG Workflow Needs:

raw user query

equipment context

chunk limits

retrieval constraints

But the endpoint and response format remains identical.

⭐ WHAT CHANGES BETWEEN ACTIONS?

Only logic.

The structure stays the same.

You never break the ecosystem.

⭐ IN PRACTICE

Let’s show what an n8n workflow looks like.

Unified Incoming:
{
  "action_name": "diagnose_fault",
  "parameters": { "user_input": "CAT 3512 overheating" },
  "context": { "equipment_id": "3512_A" },
  "session": { "user_id": "eto001", "yacht_id": "Y001" }
}

Workflow Internal Decision:
IF action_name in VIEW_ACTIONS → go to viewWorkflow
IF action_name in CREATE_ACTIONS → go to createWorkflow
IF action_name in RAG_ACTIONS → go to ragWorkflow
...

Unified Outgoing:
{
  "card_type": "fault",
  "card": { ... },
  "micro_actions": [ ... ],
  "streaming_chunks": [ ... ]
}


Done.

⭐ WHY THIS SAVES YOU (AND ENGINEERING) FROM A NIGHTMARE

If you built 70 workflows, you would:

duplicate logic

duplicate transformer calls

duplicate schema

kill latency

create chaos evolving the system

create frontend inconsistencies

break everything with one tiny change

With this structure:

Adding a new micro-action = 1 new case in a switch node

Adding a new card type = 1 new card template

Adding a new workflow category = never required

This is exactly how companies like Notion, Linear, and even Apple structure action pipelines.

You are building an OS, not a bunch of endpoints.