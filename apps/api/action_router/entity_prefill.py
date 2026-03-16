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
    "purchase_order":  None,      # no registry domain — returns []
    "handover_export": None,      # no registry domain — handover actions have no domain= set
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

    # ── Receiving ─────────────────────────────────────────────────────────────
    ("receiving", "add_receiving_item"):                  {"receiving_id": "id"},
    ("receiving", "adjust_receiving_item"):               {"receiving_id": "id"},
    ("receiving", "accept_receiving"):                    {"receiving_id": "id"},
    ("receiving", "reject_receiving"):                    {"receiving_id": "id"},
    ("receiving", "attach_receiving_image_with_comment"): {"receiving_id": "id"},
    ("receiving", "update_receiving_fields"):             {"receiving_id": "id"},
    ("receiving", "link_invoice_document"):               {"receiving_id": "id"},

    # ── Warranty ──────────────────────────────────────────────────────────────
    ("warranty", "submit_warranty_claim"):  {"warranty_id": "id"},
    ("warranty", "approve_warranty_claim"): {"warranty_id": "id"},
    ("warranty", "reject_warranty_claim"):  {"warranty_id": "id"},
    ("warranty", "compose_warranty_email"): {"warranty_id": "id"},
    ("warranty", "draft_warranty_claim"):   {"warranty_id": "id"},

    # ── Document ──────────────────────────────────────────────────────────────
    ("document", "update_document"):         {"document_id": "id"},
    ("document", "add_document_comment"):    {"document_id": "id"},
    ("document", "add_document_tags"):       {"document_id": "id"},
    ("document", "delete_document"):         {"document_id": "id"},
    ("document", "update_document_comment"): {"document_id": "id"},

    # ── Shopping List ─────────────────────────────────────────────────────────
    # shopping_list prefill intentionally empty for Phase 2 — add as needed
    # ── Hours of Rest ─────────────────────────────────────────────────────────
    # hours_of_rest prefill intentionally empty for Phase 2 — add as needed
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
