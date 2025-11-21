🔧 1. PMS / Work Order Micro-Actions
From Work Order Cards

add_note_to_work_order

close_work_order

view_work_order_history

create_work_order (global WO creation)

create_work_order_fault (WO from fault)

General PMS micro-actions (from functionality spec)

autofill WO from search

detect equipment from query

auto-link fault → WO

attach parts to WO

attach documents/photos

⚠️ 2. Fault & Diagnosis Micro-Actions
Fault card actions

diagnose_fault

create_work_order_fault

add_note (context = fault)

related_documents (find associated manuals/docs)

Predictive / fault intelligence actions (from predictive card)

add_predictive_to_handover

view_equipment

📦 3. Inventory / Spare Parts Micro-Actions
Part card actions

view_stock

order_part

add_part_to_handover

From functionality module

scan part (mobile)

check location

link part → equipment → WO

log part usage

📄 4. Document / Manual Micro-Actions
Document-specific micro-actions

view_full_document

From functionality spec

open manual section

show relevant doc snippet

multi-source doc fusion

“view related documents” (fault card inherits)

🧠 5. Handover Micro-Actions
Handover card

edit_handover_section

export_handover

Other handover actions (implicit & explicit)

add_to_handover (global)

add_part_to_handover

add_predictive_to_handover

add_note_to_handover (implied)

add_document_to_handover (from registry example)


🔍 6. Search / Navigation Micro-Actions

(Not mutations — but micro-actions returned with cards)

find_document

find_part

equipment_history

predictive_request

view_equipment

open_document

All mapped in your intent → action table:


🧩 7. System Utility Micro-Actions

These aren’t card-specific but exist in the registry / architecture:

generate_signed_document_url (internal dispatcher)


update status / small field mutations


log action (automatic)


🚢 8. Hours of Rest Micro-Actions (Implied from functionality)

Not in your catalogue explicitly, but required given your module:


You need:

update_hours_of_rest

view_hours_of_rest

correct_hours_of_rest_entry

These will live in the action registry and schema folder.

🚨 9. Predictive / Global Intelligence Micro-Actions
(From predictive module & V2 actions)

predict_spare_consumption

compare_OEM_patterns

auto_diagnose_fault_chain

search_global_fleet_data

These are V2+ but part of the future micro-actions.

🧨 10. Purchase / Supplier Micro-Actions

Not all explicitly defined in the catalogue, but required by functionality:


Should exist as:

create_purchase_request

link_supplier

log_delivery

update_order_status

attach_invoice_document

📱 11. Mobile Capture Micro-Actions (Implied)

From mobile functionality:


upload_photo_to_WO

scan_barcode_to_part

voice_to_note

(Not yet explicitly in catalogue — should be added.)

🔥 THE COMPLETE MICRO-ACTION FAMILY (Flat List)

Here is the flattened “all micro-actions” list you asked for:

PMS / WO

add_note_to_work_order

close_work_order

view_work_order_history

create_work_order

create_work_order_fault

Faults

diagnose_fault

add_note

related_documents

Inventory

view_stock

order_part

add_part_to_handover

Documents

view_full_document

open_document

Handover

add_to_handover

add_document_to_handover

add_predictive_to_handover

edit_handover_section

export_handover

Predictive / Global

predictive_request

view_equipment

Utility

generate_signed_document_url

update_status

Hours of Rest (implied)

update_hours_of_rest

view_hours_of_rest

Purchasing (implied)

create_purchase_request

update_order_status

log_delivery

Mobile (implied)
upload_photo
scan_barcode

