⭐ CELESTEOS CANONICAL MICRO-ACTION LIST (V2 — FINAL)

Everything the OS does emerges from these atoms.

This version includes:
✔ existing actions
✔ required actions for RAG/Graph-RAG
✔ required actions for document ingestion
✔ required actions for compliance/certificates
✔ required linking actions
✔ required advanced document actions

No duplicates.
No confusion.
No backend schemas.
Pure functional surface layer.

1. FIX SOMETHING (FAULT / DIAGNOSTIC)

These actions help the user understand a technical issue and take next steps.

Core

diagnose_fault

show_manual_section

show_related_documents

show_equipment_overview

show_equipment_history

show_recent_state

show_predictive_insight

suggest_likely_parts

show_similar_past_events

NEW (Graph-RAG)

trace_related_faults

trace_related_equipment

view_linked_entities

show_document_graph

2. DO MAINTENANCE (TASKS / WORK ORDERS)

Tasks for creating, updating, closing, and adding detail to work orders.

create_work_order

create_work_order_from_fault

add_note_to_work_order

attach_photo_to_work_order

attach_document_to_work_order

add_part_to_work_order

mark_work_order_complete

show_tasks_due

show_tasks_overdue

3. MANAGE EQUIPMENT

Understanding equipment context.

open_equipment_card

show_all_linked_parts

show_all_linked_faults

show_all_linked_documents

show_all_linked_work_orders

NEW (Document Linking / Graph-RAG)

link_document_to_equipment

4. INVENTORY & PARTS

For checking stock, ordering, linking parts.

check_stock_level

show_storage_location

order_part

add_part_to_handover

log_part_usage

scan_barcode

5. HANDOVER & COMMUNICATION

Human-to-human continuity.

add_to_handover

add_note

add_predictive_insight_to_handover

add_document_to_handover

edit_handover_section

export_handover

generate_summary

NEW (Docs → Handover)

add_document_section_to_handover

summarise_document_for_handover

6. COMPLIANCE & HOURS OF REST

Logging, correcting, exporting compliance data.

update_hours_of_rest

show_hours_of_rest

show_certificates

show_expiring_certificates

export_logs

generate_audit_pack

NEW (Certificates)

add_certificate

upload_certificate_document

update_certificate_metadata

7. DOCUMENTS (MANUALS, SOPs, DRAWINGS, BULLETINS)

This is where your missing RAG actions go.

Document Search & Interaction

open_document

open_document_page

search_documents

search_document_pages

summarise_document_section

Document Administration (NEW)

upload_document

delete_document / archive_document

replace_document_version

tag_document

Document Linking (NEW)

link_document_to_fault

link_document_to_equipment

Advanced RAG (NEW)

compare_document_sections

extract_procedures_from_document

detect_document_anomalies

8. PURCHASING & SUPPLIERS

Basic procurement flows.

create_purchase_request

add_part_to_purchase_request

approve_purchase

track_delivery

attach_invoice

9. CHECKLISTS & OPERATIONS

Operational workflows like arrival, departure, guest prep.

open_checklist

mark_checklist_item_complete

add_note_to_checklist_item

attach_photo_to_checklist_item

10. SHIPYARD / REFIT WORK

For heavy project periods.

open_worklist

add_worklist_item

update_worklist_progress

export_worklist

tag_worklist_item

11. FLEET / MANAGEMENT

High-level oversight.

open_fleet_summary

open_vessel_from_fleet

export_fleet_report

12. GENERAL / SYSTEM UTILITY

Always-available actions.

undo_last_action

open_location_on_map

view_file

open_media

show_linked_context

⭐ THE 22 NEW MICRO-ACTIONS YOU WERE MISSING

For clarity, here they are isolated:

Document Search & RAG

search_documents

search_document_pages

open_document_page

summarise_document_section

Graph-RAG

view_linked_entities

trace_related_faults

trace_related_equipment

show_document_graph

Document Admin

upload_document

delete_document / archive_document

replace_document_version

tag_document

Document Linking

link_document_to_fault

link_document_to_equipment

Certificates

add_certificate

upload_certificate_document

update_certificate_metadata

Advanced RAG

compare_document_sections

extract_procedures_from_document

detect_document_anomalies

Docs → Handover

add_document_section_to_handover

summarise_document_for_handover

This is the required expansion to support:

full yacht-manual ingestion

chunked semantic search

Graph-RAG relations

manual section linking

certificate compliance

document→fault→equipment graph navigation

SOP extraction

document-enhanced handovers

It is now complete.