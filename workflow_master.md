⭐ THE CORE PRINCIPLE

Micro-actions ≠ workflows.
Micro-actions are intents.
Workflows are pipelines that serve those intents.

You will NOT build 70 workflows.
You will build a handful of reusable workflow “archetypes” that handle categories of micro-actions.

This avoids:

duplication

insanity

maintenance nightmares

high latency

bot fragility

⭐ THE 6 WORKFLOW ARCHETYPE MODEL

This is the correct, scalable way to handle 70+ micro-actions.

Every micro-action belongs to one of these archetypes:

1. VIEW WORKFLOWS

For all “read-only” micro-actions:

show_manual_section

show_related_documents

show_equipment_history

view_all_linked_documents

show_certificates

show_expiring_certificates

show_hours_of_rest

open_document

open_document_page

search_documents

search_document_pages

trace_related_faults

trace_related_equipment

view_linked_entities

Workflow pattern:

Query DB → retrieve context → build card JSON → return front-end actions.

Roughly 1 workflow with branching.

2. WRITE / UPDATE WORKFLOWS

For micro-actions that mutate a record:

update_hours_of_rest

mark_work_order_complete

add_note

add_note_to_work_order

add_part_to_work_order

update_certificate_metadata

replace_document_version

tag_document

log_part_usage

Workflow pattern:

Validate input → update Supabase → return updated card.

Roughly 1 workflow with multiple branches OR 2 workflows (light vs heavy).

3. CREATE WORKFLOWS

For creating new objects:

create_work_order

create_work_order_from_fault

add_certificate

upload_certificate_document

upload_document

create_purchase_request

add_worklist_item

add_document_to_handover

add_document_section_to_handover

Workflow pattern:

Insert row → link relations → produce card.

Roughly 2 workflows:

create_simple_resource

create_complex_resource (with linking)

4. EXPORT WORKFLOWS

For actions that generate files, PDFs, summaries:

export_handover

export_logs

generate_audit_pack

generate_summary

summarise_document_section

summarise_document_for_handover

Workflow pattern:

Collect data → transform → upload PDF → return signed URL.

Roughly 1 workflow.

5. RAG / AI WORKFLOWS

All actions that need semantic search, vector search, summary or doc analysis:

search_documents

search_document_pages

summarise_document_section

compare_document_sections

extract_procedures_from_document

detect_document_anomalies

show_document_graph

Workflow pattern:

Embed → retrieve vectors → construct RAG prompt → LLM → card output.

Roughly 2 workflows:

RAG_search

RAG_enrichment

6. LINKING WORKFLOWS

The micro-actions that attach things to other things:

link_document_to_equipment

link_document_to_fault

add_document_section_to_handover

attach_document_to_work_order

add_part_to_handover

Workflow pattern:

Insert into link table → return updated card.

Roughly 1 workflow.

⭐ TOTAL WORKFLOWS NEEDED: 12–20

NOT 70.

Here is the practical breakdown:

Pipeline Type	Count	Handles
View / Read	1–2	20+ micro-actions
Update / Mutate	1–2	10+ micro-actions
Create	2	10+ micro-actions
Export	1	PDF/logs/summaries
RAG	2–3	semantic + graph RAG
Linking	1–2	all relational “attach/link”

Expected total:
12–20 workflows
not
70+ workflows.

This is how you scale reliably.

⭐ HOW THE ROUTER USES THESE WORKFLOWS

You already have:

micro-action router

canonical micro-actions

micro-action → card mapping

micro-action → workflow mapping

n8n workflow endpoints

frontend button mapping

The Router’s job is trivial now:

if action_name in VIEW_ACTIONS:
    call viewWorkflow()

if action_name in UPDATE_ACTIONS:
    call updateWorkflow()

if action_name in CREATE_ACTIONS:
    call createWorkflow()

if action_name in RAG_ACTIONS:
    call ragWorkflow()

if action_name in EXPORT_ACTIONS:
    call exportWorkflow()


Each workflow receives:

{
 action_name: "...",
 context: { ... },
 user_input: "...",
 additional_parameters: {...}
}


And returns:

{
 card_type: "...",
 card: {...},
 micro_actions: [...]
}

----

