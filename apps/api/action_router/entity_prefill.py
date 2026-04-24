# apps/api/action_router/entity_prefill.py
"""
CelesteOS — Entity Context Prefill
====================================
Static VLOOKUP table mapping (entity_type, action_id) to field dot-paths.
Dot-paths resolve against entity data already fetched by the route handler.

No DB calls. No side effects. Pure functions only.

To extend: add entries to CONTEXT_PREFILL_MAP. Missing entries return {}
and never block an action from appearing.
"""
from typing import Any, Dict, Optional, Tuple
# Module-level imports required so patch() can reach these names in tests.
# Lazy import inside get_field_schema() would make them invisible to patch().
from action_router.registry import ACTION_REGISTRY, FieldClassification


ENTITY_TYPE_TO_DOMAIN: Dict[str, Optional[str]] = {
    "work_order":      "work_orders",
    "equipment":       "equipment",
    "fault":           "faults",
    "part":            "parts",
    "document":        "documents",
    "certificate":     "certificates",
    "receiving":       "receiving",
    "shopping_list":   "shopping_list",
    "warranty":        "warranty",
    "hours_of_rest":   "hours_of_rest",
    "purchase_order":  "purchase_orders",
    "handover_export": "handover",
}


CONTEXT_PREFILL_MAP: Dict[Tuple[str, str], Dict[str, str]] = {
    # ── Equipment ─────────────────────────────────────────────────────────────
    ("equipment", "create_work_order_for_equipment"): {
        "equipment_id": "id",
        "title":        "canonical_label",
    },
    ("equipment", "report_fault"): {
        "equipment_id":   "id",
        "equipment_name": "canonical_label",
    },
    ("equipment", "link_part_to_equipment"):        {"equipment_id": "id"},
    ("equipment", "add_equipment_note"):            {"equipment_id": "id"},
    ("equipment", "attach_file_to_equipment"):      {"equipment_id": "id"},
    ("equipment", "flag_equipment_attention"):      {"equipment_id": "id"},
    ("equipment", "record_equipment_hours"):        {"equipment_id": "id"},
    ("equipment", "decommission_equipment"):        {"equipment_id": "id"},
    ("equipment", "set_equipment_status"):          {"equipment_id": "id"},

    # ── Fault ─────────────────────────────────────────────────────────────────
    ("fault", "create_work_order_from_fault"): {
        "fault_id":     "id",
        "equipment_id": "equipment_id",
        "title":        "description",
    },
    ("fault", "add_fault_note"):        {"fault_id": "id"},
    ("fault", "add_fault_photo"):       {"fault_id": "id"},
    ("fault", "acknowledge_fault"):     {"fault_id": "id"},
    ("fault", "diagnose_fault"):        {"fault_id": "id"},
    ("fault", "close_fault"):           {"fault_id": "id"},
    ("fault", "reopen_fault"):          {"fault_id": "id"},
    ("fault", "mark_fault_false_alarm"): {"fault_id": "id"},
    ("fault", "update_fault"):          {"fault_id": "id"},

    # ── Work Order ────────────────────────────────────────────────────────────
    ("work_order", "add_wo_note"):          {"work_order_id": "id"},
    ("work_order", "add_wo_part"):          {"work_order_id": "id"},
    ("work_order", "add_wo_hours"):         {"work_order_id": "id"},
    ("work_order", "add_work_order_photo"): {"work_order_id": "id"},
    ("work_order", "start_work_order"):     {"work_order_id": "id"},
    ("work_order", "cancel_work_order"):    {"work_order_id": "id"},
    ("work_order", "close_work_order"):     {"work_order_id": "id"},
    ("work_order", "assign_work_order"):    {"work_order_id": "id"},
    ("work_order", "reassign_work_order"):  {"work_order_id": "id"},
    ("work_order", "archive_work_order"):   {"work_order_id": "id"},
    ("work_order", "update_work_order"):    {"work_order_id": "id"},

    # ── Part ──────────────────────────────────────────────────────────────────
    ("part", "log_part_usage"):        {"part_id": "id"},
    ("part", "transfer_part"):         {"part_id": "id"},
    ("part", "adjust_stock_quantity"): {"part_id": "id"},
    ("part", "write_off_part"):        {"part_id": "id"},
    ("part", "receive_part"):          {"part_id": "id"},
    ("part", "consume_part"):          {"part_id": "id"},
    ("part", "check_stock_level"):     {"part_id": "id"},
    ("part", "request_label_output"):  {"part_id": "id"},

    # ── Certificate ───────────────────────────────────────────────────────────
    ("certificate", "update_certificate"):          {"certificate_id": "id"},
    ("certificate", "link_document_to_certificate"):{"certificate_id": "id"},
    ("certificate", "supersede_certificate"):       {"certificate_id": "id"},
    ("certificate", "add_certificate_note"):        {"certificate_id": "id"},
    ("certificate", "renew_certificate"):           {"certificate_id": "id"},
    ("certificate", "link_equipment_to_certificate"):   {"certificate_id": "id"},
    ("certificate", "unlink_equipment_from_certificate"):{"certificate_id": "id"},
    # Archive / suspend / revoke registry rows declare `entity_id` (not
    # `certificate_id`) as the required key, matching the generic
    # archive/suspend/revoke pattern other domains use. Without these prefill
    # rows the router's required-fields gate rejected every dropdown click
    # with 400 before the handler ever ran (Issue 6 pattern in
    # /Users/celeste7/Desktop/list_of_faults.md — "every button gives 400").
    # Handler bodies already accept either key (certificate_handlers.py:1528,
    # 1600) so this is a wiring fix only — no behavioural change.
    ("certificate", "archive_certificate"):         {"entity_id": "id"},
    ("certificate", "suspend_certificate"):         {"entity_id": "id"},
    ("certificate", "revoke_certificate"):          {"entity_id": "id"},
    ("certificate", "assign_certificate"):          {"certificate_id": "id"},

    # ── Receiving ─────────────────────────────────────────────────────────────
    ("receiving", "add_receiving_item"):                  {"receiving_id": "id"},
    ("receiving", "adjust_receiving_item"):               {"receiving_id": "id"},
    ("receiving", "accept_receiving"):                    {"receiving_id": "id"},
    ("receiving", "reject_receiving"):                    {"receiving_id": "id"},
    ("receiving", "attach_receiving_image_with_comment"): {"receiving_id": "id"},
    ("receiving", "update_receiving_fields"):             {"receiving_id": "id"},
    ("receiving", "link_invoice_document"):               {"receiving_id": "id"},

    # ── Warranty ──────────────────────────────────────────────────────────────
    # submit/approve/reject/compose/close use claim_id (matches required_fields in registry)
    # draft uses warranty_id (its handler resolves by warranty_id)
    # add_warranty_note uses warranty_id (its handler stores warranty_id FK on pms_notes)
    ("warranty", "submit_warranty_claim"):  {"claim_id": "id"},
    ("warranty", "approve_warranty_claim"): {"claim_id": "id"},
    ("warranty", "reject_warranty_claim"):  {"claim_id": "id"},
    ("warranty", "compose_warranty_email"): {"claim_id": "id"},
    ("warranty", "draft_warranty_claim"):   {"warranty_id": "id"},
    ("warranty", "close_warranty_claim"):   {"claim_id": "id"},
    ("warranty", "add_warranty_note"):      {"warranty_id": "id"},
    ("warranty", "add_to_handover"):        {"entity_id": "id", "title": "title"},

    # ── Document ──────────────────────────────────────────────────────────────
    ("document", "update_document"):              {"document_id": "id"},
    # FIX 2026-04-23: add_document_note was missing a prefill entry — the
    # AddNoteModal on the documents lens submits {note_text} and relies on
    # this map to inject document_id. Without it the action validator 400'd.
    # Paired with the registry.py required_fields correction (equipment_id
    # → document_id on add_document_note).
    ("document", "add_document_note"):            {"document_id": "id"},
    ("document", "add_document_comment"):         {"document_id": "id"},
    ("document", "add_document_tags"):            {"document_id": "id"},
    ("document", "delete_document"):              {"document_id": "id"},
    # archive_document uses entity_id per its required_fields declaration.
    ("document", "archive_document"):             {"entity_id": "id"},
    ("document", "update_document_comment"):      {"document_id": "id"},
    ("document", "link_document_to_equipment"):   {"document_id": "id"},
    ("document", "get_document_url"):             {"document_id": "id"},
    ("document", "list_document_comments"):       {"document_id": "id"},
    # upload_document intentionally omitted — upload creates a NEW doc, so
    # there is no source document context to prefill from.
    # delete_document_comment intentionally omitted — it keys on comment_id,
    # not document_id; prefill happens from the comment row, not the doc.
    # add_document_to_handover: prefill document provenance fields so the
    # handover item records WHAT document is being handed over. `section` and
    # `summary` stay empty and editable — the HOD fills them in the popup.
    ("document", "add_document_to_handover"): {
        "document_id":   "id",
        "entity_id":     "id",
        "title":         "filename",
        "doc_type":      "doc_type",
        "source_doc_id": "id",
        "link":          "storage_path",
    },

    # ── Shopping List ─────────────────────────────────────────────────────────
    # Mutation actions: prefill item_id from entity "id" so required-field
    # validation in p0_actions_routes passes when called from EntityLensPage.
    ("shopping_list", "approve_shopping_list_item"): {"item_id": "id"},
    ("shopping_list", "reject_shopping_list_item"):  {"item_id": "id"},
    ("shopping_list", "promote_candidate_to_part"):  {"item_id": "id"},
    ("shopping_list", "view_shopping_list_history"): {"item_id": "id"},
    ("shopping_list", "delete_shopping_item"):       {"item_id": "id"},
    ("shopping_list", "mark_shopping_list_ordered"): {"item_id": "id"},
    # ── Hours of Rest ─────────────────────────────────────────────────────────
    # hours_of_rest prefill intentionally empty for Phase 2 — add as needed

    # ══════════════════════════════════════════════════════════════════════════
    # CROSS-DOMAIN CANONICAL ACTIONS — prefill from source entity context
    # ══════════════════════════════════════════════════════════════════════════

    # add_to_handover: pre-populates entity reference from ANY source entity.
    #
    # HANDOVER08 task B6 (2026-04-23): extended the equipment/fault/work_order
    # rows with read-only context fields so ActionPopup can surface the
    # identifying attributes of the source entity (manufacturer, model, WO#,
    # severity, etc.) in the "Add to Handover" modal. See
    # /Users/celeste7/Desktop/list_of_faults.md and the EQUIPMENT05 request
    # relayed through claude-peers channel.
    #
    # All extras are BACKEND_AUTO-style passthroughs — ActionPopup MAY render
    # them as a read-only context block. Fields missing from entity_data are
    # dropped silently by resolve_prefill(), so any lens that does not expose
    # a given key is a no-op (no 400, no crash).
    #
    # TODO (ActionPopup consumer): wire a read-only "Source entity" block that
    # renders these prefill keys above the editable summary/notes inputs.
    # EQUIPMENT05 owns the frontend side; do NOT edit ActionPopup here.
    ("work_order", "add_to_handover"): {
        "entity_id":      "id",
        "title":          "title",
        "wo_number":      "wo_number",
        "priority":       "priority",
        "status":         "status",
        "equipment_id":   "equipment_id",
        "equipment_name": "equipment_name",
    },
    ("fault", "add_to_handover"): {
        "entity_id":      "id",
        "title":          "title",
        "fault_code":     "title",            # pms_faults surfaces fault_code via title fallback — entity_routes.py:1280
        "severity":       "severity",
        "status":         "status",
        "equipment_id":   "equipment_id",
        "equipment_name": "equipment_name",
    },
    ("equipment", "add_to_handover"): {
        "entity_id":      "id",
        "title":          "name",
        # CEO context fields (EQUIPMENT05 request):
        # code is not surfaced on the lens response today — intentionally
        # omitted; resolve_prefill drops missing keys. Add here when the
        # equipment route starts emitting it.
        "name":           "name",
        "manufacturer":   "manufacturer",
        "model":          "model",
        "serial_number":  "serial_number",
        "criticality":    "criticality",
        "status":         "status",
        "location":       "location",
        "system_type":    "equipment_type",   # entity_routes.py:1473 maps system_type → equipment_type
        # running_hours not on the equipment lens response yet (see
        # pms_equipment.running_hours column usage in equipment_handlers.py:1374).
        # Left out so we don't ship a key that resolves to None; add when the
        # equipment route starts surfacing it.
    },
    ("part", "add_to_handover"):         {"entity_id": "id", "title": "name"},
    ("certificate", "add_to_handover"):  {"entity_id": "id", "title": "name"},
    ("document", "add_to_handover"):     {"entity_id": "id", "title": "name"},
    ("receiving", "add_to_handover"):    {"entity_id": "id", "title": "vendor_name"},
    ("shopping_list", "add_to_handover"):{"entity_id": "id", "title": "item_name"},
    ("warranty", "add_to_handover"):     {"entity_id": "id", "title": "vendor_name"},
    ("hours_of_rest", "add_to_handover"):{"entity_id": "id", "title": "crew_member_name"},
    ("purchase_order", "add_to_handover"): {
        "entity_id":  "id",
        "title":      "po_number",
        "status":     "status",
        "department": "department",
    },

    # ── Purchase Order action prefill (Issue #14 — 400 fix, 2026-04-23) ──
    # Without these entries the action popup has no purchase_order_id and the
    # router's required-fields gate rejects every PO button. Same pattern
    # CERT04 used to unbreak the cert dropdown in PR #681.
    ("purchase_order", "submit_po"):              {"purchase_order_id": "id"},
    ("purchase_order", "submit_purchase_order"):  {"purchase_order_id": "id"},
    ("purchase_order", "approve_po"):             {"purchase_order_id": "id"},
    ("purchase_order", "approve_purchase_order"): {"purchase_order_id": "id"},
    ("purchase_order", "approve_purchase"):       {"purchase_order_id": "id"},
    ("purchase_order", "receive_po"):             {"purchase_order_id": "id"},
    ("purchase_order", "mark_po_received"):       {"purchase_order_id": "id"},
    ("purchase_order", "cancel_po"):              {"purchase_order_id": "id"},
    ("purchase_order", "cancel_purchase_order"):  {"purchase_order_id": "id"},
    ("purchase_order", "delete_po"):              {"purchase_order_id": "id"},
    ("purchase_order", "delete_purchase_order"):  {"purchase_order_id": "id"},
    ("purchase_order", "add_po_note"):            {"purchase_order_id": "id"},
    ("purchase_order", "update_purchase_status"): {"purchase_order_id": "id"},
    ("purchase_order", "add_item_to_purchase"):   {"purchase_order_id": "id"},
    ("purchase_order", "upload_invoice"):         {"purchase_order_id": "id"},

    # add_to_shopping_list from parts: pre-populates part reference
    ("part", "add_to_shopping_list"):    {"part_id": "id", "part_name": "name", "part_number": "part_number"},

    # file_warranty_claim from parts + equipment
    ("part", "file_warranty_claim"):     {"part_id": "id", "part_name": "name"},
    ("equipment", "file_warranty_claim"):{"equipment_id": "id", "equipment_name": "name"},
}


def resolve_prefill(entity_type: str, action_id: str, entity_data: dict) -> dict:
    """
    Resolve prefill values for an (entity_type, action_id) pair.
    Returns a dict of {field_name: resolved_value} from entity_data.
    Returns {} if no mapping exists — safe, never blocks an action.
    """
    mapping = CONTEXT_PREFILL_MAP.get((entity_type, action_id), {})
    result = {}
    for field_name, dot_path in mapping.items():
        value = _resolve_dot_path(entity_data, dot_path)
        if value is not None:
            result[field_name] = value
    return result


def get_field_schema(action_id: str) -> tuple[list[str], list[str]]:
    """
    Return (required_fields, optional_fields) for an action.

    Reads ActionDefinition.field_metadata from ACTION_REGISTRY.
    Uses ACTION_REGISTRY.get() — never get_action() — to safely handle
    missing action_ids without raising KeyError.

    BACKEND_AUTO and CONTEXT fields (yacht_id, user_id, etc.) are excluded
    — they are server-injected and must not appear in the frontend form.

    Returns ([], []) if action not found or has no field_metadata.
    """
    # ACTION_REGISTRY and FieldClassification are module-level imports (top of file).
    action_def = ACTION_REGISTRY.get(action_id)
    if not action_def or not action_def.field_metadata:
        return [], []
    required = [
        f.name for f in action_def.field_metadata
        if f.classification in ("REQUIRED", FieldClassification.REQUIRED)
    ]
    optional = [
        f.name for f in action_def.field_metadata
        if f.classification in ("OPTIONAL", FieldClassification.OPTIONAL)
    ]
    return required, optional


def _resolve_dot_path(data: dict, path: str) -> Any:
    """
    Resolve a dot-notation path against a dict.
    Returns None if any key in the path is missing or the value is None.
    Example: _resolve_dot_path({"a": {"b": "x"}}, "a.b") -> "x"
    """
    parts = path.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current
