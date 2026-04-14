"""
Ledger Metadata — Phase B safety net.

Maps action names that go through internal_adapter to their ledger attributes.
Used by the POST /execute dispatcher to write a generic audit entry when the
handler did not already write one (i.e. result["_ledger_written"] is falsy).

Read-only actions (get_*, list_*, view_*, extract_*) are intentionally absent —
no safety-net write for reads.

Schema per entry:
    event_type      — one of the enum values accepted by build_ledger_event:
                      create | update | delete | status_change | assignment |
                      approval | rejection | escalation | handover | import | export
    entity_type     — snake_case noun (free text stored in ledger_events)
    entity_id_field — key to look up in the action payload; falls back to
                      yacht_id if not present.
"""

# ---------------------------------------------------------------------------
# Adapter actions (72 total in internal_adapter.py) — mutations only
# ---------------------------------------------------------------------------
ACTION_METADATA: dict = {
    # ── Receiving ────────────────────────────────────────────────────────────
    "accept_receiving":                  {"event_type": "status_change", "entity_type": "receiving",     "entity_id_field": "receiving_id"},
    "add_receiving_item":                {"event_type": "update",        "entity_type": "receiving",     "entity_id_field": "receiving_id"},
    "adjust_receiving_item":             {"event_type": "update",        "entity_type": "receiving",     "entity_id_field": "receiving_id"},
    "attach_receiving_image_with_comment": {"event_type": "update",      "entity_type": "receiving",     "entity_id_field": "receiving_id"},
    "confirm_receiving":                 {"event_type": "status_change", "entity_type": "receiving",     "entity_id_field": "receiving_id"},
    "create_receiving":                  {"event_type": "create",        "entity_type": "receiving",     "entity_id_field": "receiving_id"},
    "flag_discrepancy":                  {"event_type": "update",        "entity_type": "receiving",     "entity_id_field": "receiving_id"},
    "reject_receiving":                  {"event_type": "rejection",     "entity_type": "receiving",     "entity_id_field": "receiving_id"},
    "update_receiving_fields":           {"event_type": "update",        "entity_type": "receiving",     "entity_id_field": "receiving_id"},

    # ── Equipment ────────────────────────────────────────────────────────────
    "archive_equipment":                 {"event_type": "update",        "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "assign_parent_equipment":           {"event_type": "update",        "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "attach_file_to_equipment":          {"event_type": "update",        "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "attach_image_with_comment":         {"event_type": "update",        "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "create_equipment":                  {"event_type": "create",        "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "decommission_and_replace_equipment": {"event_type": "status_change","entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "decommission_equipment":            {"event_type": "status_change", "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "flag_equipment_attention":          {"event_type": "update",        "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "link_document_to_equipment":        {"event_type": "update",        "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "link_part_to_equipment":            {"event_type": "update",        "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "record_equipment_hours":            {"event_type": "update",        "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "restore_archived_equipment":        {"event_type": "status_change", "entity_type": "equipment",     "entity_id_field": "equipment_id"},
    "set_equipment_status":              {"event_type": "status_change", "entity_type": "equipment",     "entity_id_field": "equipment_id"},

    # ── Faults ───────────────────────────────────────────────────────────────
    "archive_fault":                     {"event_type": "update",        "entity_type": "fault",         "entity_id_field": "fault_id"},
    "classify_fault":                    {"event_type": "update",        "entity_type": "fault",         "entity_id_field": "fault_id"},
    "delete_fault":                      {"event_type": "delete",        "entity_type": "fault",         "entity_id_field": "fault_id"},
    "investigate_fault":                 {"event_type": "update",        "entity_type": "fault",         "entity_id_field": "fault_id"},

    # ── Documents ────────────────────────────────────────────────────────────
    "add_document_comment":              {"event_type": "update",        "entity_type": "document",      "entity_id_field": "document_id"},
    "add_document_note":                 {"event_type": "update",        "entity_type": "document",      "entity_id_field": "document_id"},
    "add_entity_link":                   {"event_type": "update",        "entity_type": "document",      "entity_id_field": "document_id"},
    "archive_document":                  {"event_type": "update",        "entity_type": "document",      "entity_id_field": "document_id"},
    "delete_document_comment":           {"event_type": "update",        "entity_type": "document",      "entity_id_field": "document_id"},
    "link_invoice_document":             {"event_type": "update",        "entity_type": "document",      "entity_id_field": "document_id"},
    "update_document_comment":           {"event_type": "update",        "entity_type": "document",      "entity_id_field": "document_id"},

    # ── Certificates ─────────────────────────────────────────────────────────
    "add_certificate_note":              {"event_type": "update",        "entity_type": "certificate",   "entity_id_field": "certificate_id"},
    "archive_certificate":               {"event_type": "update",        "entity_type": "certificate",   "entity_id_field": "entity_id"},
    "create_vessel_certificate":         {"event_type": "create",        "entity_type": "certificate",   "entity_id_field": "certificate_id"},
    "create_crew_certificate":           {"event_type": "create",        "entity_type": "certificate",   "entity_id_field": "certificate_id"},
    "link_document_to_certificate":      {"event_type": "update",        "entity_type": "certificate",   "entity_id_field": "certificate_id"},
    "renew_certificate":                 {"event_type": "create",        "entity_type": "certificate",   "entity_id_field": "certificate_id"},
    "revoke_certificate":                {"event_type": "status_change", "entity_type": "certificate",   "entity_id_field": "entity_id"},
    "supersede_certificate":             {"event_type": "status_change", "entity_type": "certificate",   "entity_id_field": "certificate_id"},
    "suspend_certificate":               {"event_type": "status_change", "entity_type": "certificate",   "entity_id_field": "entity_id"},
    "update_certificate":                {"event_type": "update",        "entity_type": "certificate",   "entity_id_field": "certificate_id"},

    # ── Parts / Inventory ────────────────────────────────────────────────────
    "add_part_note":                     {"event_type": "update",        "entity_type": "part",          "entity_id_field": "part_id"},
    "archive_part":                      {"event_type": "update",        "entity_type": "part",          "entity_id_field": "part_id"},
    "delete_part":                       {"event_type": "delete",        "entity_type": "part",          "entity_id_field": "part_id"},
    "reorder_part":                      {"event_type": "update",        "entity_type": "part",          "entity_id_field": "part_id"},
    "update_part_details":               {"event_type": "update",        "entity_type": "part",          "entity_id_field": "part_id"},

    # ── Purchase Orders ──────────────────────────────────────────────────────
    "add_po_note":                       {"event_type": "update",        "entity_type": "purchase_order","entity_id_field": "purchase_order_id"},
    "cancel_po":                         {"event_type": "status_change", "entity_type": "purchase_order","entity_id_field": "purchase_order_id"},
    "convert_to_po":                     {"event_type": "create",        "entity_type": "purchase_order","entity_id_field": "purchase_order_id"},
    "delete_po":                         {"event_type": "delete",        "entity_type": "purchase_order","entity_id_field": "purchase_order_id"},
    "track_po_delivery":                 {"event_type": "update",        "entity_type": "purchase_order","entity_id_field": "purchase_order_id"},

    # ── Work Orders ──────────────────────────────────────────────────────────
    "add_wo_photo":                      {"event_type": "update",        "entity_type": "work_order",    "entity_id_field": "work_order_id"},
    "delete_work_order":                 {"event_type": "delete",        "entity_type": "work_order",    "entity_id_field": "work_order_id"},

    # ── Warranties ───────────────────────────────────────────────────────────
    "add_warranty_note":                 {"event_type": "update",        "entity_type": "warranty",      "entity_id_field": "warranty_id"},
    "archive_warranty":                  {"event_type": "update",        "entity_type": "warranty",      "entity_id_field": "warranty_id"},
    "file_warranty_claim":               {"event_type": "create",        "entity_type": "warranty",      "entity_id_field": "warranty_id"},
    "void_warranty":                     {"event_type": "status_change", "entity_type": "warranty",      "entity_id_field": "warranty_id"},
    "submit_warranty_claim":             {"event_type": "status_change", "entity_type": "warranty",      "entity_id_field": "warranty_id"},
    "approve_warranty_claim":            {"event_type": "approval",      "entity_type": "warranty",      "entity_id_field": "warranty_id"},
    "reject_warranty_claim":             {"event_type": "rejection",     "entity_type": "warranty",      "entity_id_field": "warranty_id"},
    "close_warranty_claim":              {"event_type": "status_change", "entity_type": "warranty",      "entity_id_field": "warranty_id"},
    "compose_warranty_email":            {"event_type": "update",        "entity_type": "warranty",      "entity_id_field": "warranty_id"},

    # ── Handover ─────────────────────────────────────────────────────────────
    "archive_handover":                  {"event_type": "update",        "entity_type": "handover",      "entity_id_field": "handover_id"},
    "edit_handover_section":             {"event_type": "update",        "entity_type": "handover",      "entity_id_field": "handover_id"},
    "sign_handover":                     {"event_type": "handover",      "entity_type": "handover",      "entity_id_field": "handover_id"},

    # ── Shopping Lists ───────────────────────────────────────────────────────
    "add_list_item":                     {"event_type": "update",        "entity_type": "shopping_list", "entity_id_field": "list_id"},
    "approve_list":                      {"event_type": "approval",      "entity_type": "shopping_list", "entity_id_field": "list_id"},
    "archive_list":                      {"event_type": "update",        "entity_type": "shopping_list", "entity_id_field": "list_id"},
    "delete_list":                       {"event_type": "delete",        "entity_type": "shopping_list", "entity_id_field": "list_id"},
    "submit_list":                       {"event_type": "update",        "entity_type": "shopping_list", "entity_id_field": "list_id"},

    # ── Hours of Rest ────────────────────────────────────────────────────────
    "upsert_hours_of_rest":              {"event_type": "update",        "entity_type": "hours_of_rest", "entity_id_field": "user_id"},

    # ── Misc ─────────────────────────────────────────────────────────────────
    "add_note":                          {"event_type": "update",        "entity_type": "entity",        "entity_id_field": "entity_id"},
    "apply_template":                    {"event_type": "update",        "entity_type": "entity",        "entity_id_field": "entity_id"},
}
