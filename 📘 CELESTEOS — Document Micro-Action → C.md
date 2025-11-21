📘 CELESTEOS — Document Micro-Action → Card Mapping (Final Spec)

This file defines how document-related micro-actions appear across all card types.

Each card has two sections:

Primary Actions (always shown if context exists)

Conditional Actions (only shown when triggered by user intent)

1. DOCUMENT CARD

Shown when the user opens a document or CelesteOS retrieves a doc from search/RAG.

Primary Actions
Micro-Action	Button Label	Purpose
open_document	Open Document	Open full PDF/file viewer
open_document_page	Open Page	Jump directly to relevant page
search_document_pages	Search Within Document	Find other relevant pages
summarise_document_section	Summarise Section	Produce a short summary
view_linked_entities	View Linked Items	Show equipment, faults, WOs linked to this doc
Conditional Actions
Micro-Action	Condition
add_document_to_handover	If user mentions “handover” or “add this to report”
add_document_section_to_handover	If user continues: “add this part/page to handover”
replace_document_version	If user states: “update the manual”, “new version”, “replace doc”
delete_document / archive_document	If user says: “remove this document”, “archive this”
tag_document	If user says: “categorise this”, “label this as SOP/manual/etc.”
2. FAULT CARD
Primary Actions
Micro-Action	Button Label	Purpose
show_manual_section	Open Manual Section	Full RAG result → manual snippet
show_related_documents	Related Docs	Secondary relevant docs
trace_related_faults	Related Faults	Graph-RAG traversal across faults
trace_related_equipment	Related Equipment	Graph-RAG reverse lookup
link_document_to_fault	Link Document	Manually attach a doc to this fault
Conditional Actions
Micro-Action	Condition
add_document_section_to_handover	If doc info should be included in handover
summarise_document_section	When user wants: “summarise this solution”
3. EQUIPMENT CARD
Primary Actions
Micro-Action	Label	Purpose
show_all_linked_documents	Documents	Show manuals, SOPs, linked docs
open_document_page	Relevant Page	Open doc sections relevant to equipment
trace_related_equipment	Related Systems	Graph-RAG traversal
trace_related_faults	Related Faults	Fault history + similarity
Conditional Actions
Micro-Action	Condition
link_document_to_equipment	If user says: “attach manual”, “link document”
extract_procedures_from_document	If user says: “turn this manual into steps”
4. WORK ORDER (WO) CARD
Primary Actions
Micro-Action	Label	Purpose
attach_document_to_work_order	Attach Document	Link doc as WO source
open_document_page	View Page	Let WO executor see exact procedures
summarise_document_section	Summarise Doc	Convert OEM text → human readable
extract_procedures_from_document	Extract Steps	Turn doc into task checklist
Conditional Actions

| Micro-Action | Condition |
|--------------|
| add_document_section_to_handover | If WO issue → crew turnover |
| compare_document_sections | If user references multiple doc versions |

5. HANDOVER CARD

Handover is where documents shine; a lot of micro-actions appear here.

Primary Actions
Micro-Action	Label	Purpose
add_document_to_handover	Add Document	Add full doc
add_document_section_to_handover	Add Page/Section	Add relevant portion
summarise_document_for_handover	Summarise	Shorter crew-friendly summary
Conditional Actions

| Micro-Action | Condition |
|--------------|
| open_document_page | If user clicks a referenced doc |
| replace_document_version | If user says: "update this handover doc" |

6. PART / INVENTORY CARD
Primary Actions
Micro-Action	Label	Purpose
search_documents	Show Documents	Show manuals & parts lists for this part
search_document_pages	Find Part Pages	Page-level lookup
view_linked_entities	Linked Equipment	Which equipment uses this part
Conditional Actions

| Micro-Action | Condition |
|--------------|
| link_document_to_equipment | If user says: “link this parts sheet to equipment X” |

7. CERTIFICATE CARD
Primary Actions
Micro-Action	Label	Purpose
open_document	View Certificate	Open certificate PDF
upload_certificate_document	Upload	Add missing file
update_certificate_metadata	Update Info	Change expiry/category
Conditional Actions

| Micro-Action | Condition |
|--------------|
| tag_document | If classification needed |
| replace_document_version | If new cert uploaded |

8. CHECKLIST / SOP CARD
Primary Actions
Micro-Action	Label	Purpose
extract_procedures_from_document	Extract Steps	Turn SOP/manual → tasks
open_document_page	View Procedure	Show source page
summarise_document_section	Summarise Steps	Make concise form
Conditional Actions

| Micro-Action | Condition |
|--------------|
| add_document_section_to_handover | If relevant to turnover |

9. SHIPYARD / REFIT WORKLIST CARD
Primary Actions
Micro-Action	Label	Purpose
open_document_page	Technical Docs	Show diagrams / specs directly
compare_document_sections	Compare Docs	For revised drawings
view_linked_entities	Linked Systems	What systems relate to this doc
Conditional Actions

| Micro-Action | Condition |
|--------------|
| add_document_to_handover | If this doc affects turnover |
| tag_document | If docs need classification |

10. FLEET SUMMARY CARD
Primary Actions
Micro-Action	Label	Purpose
search_documents	Fleet Docs	Search global docs across yachts
show_document_graph	Doc Graph	Understand relationships fleet-wide

(No conditional actions needed here — fleet view is summarised.)

11. SMART SUMMARY CARD

(e.g., “What should I know today?”)

Primary Actions
Micro-Action	Label
trace_related_faults	Related Faults
trace_related_equipment	Related Equipment
search_documents	Relevant Docs
summarise_document_section	Summary
add_document_section_to_handover	Add to Handover
📌 In One Sentence

This file defines:

Which document-related micro-actions appear on which card type, and when.

Every card now has:

the correct primary actions

the correct conditional actions

the correct contextual triggers

This enables:

correct agent planning

correct n8n workflows

correct frontend UX button rendering

correct JSON action routing