"""
Internal Adapter — bridges INTERNAL_HANDLERS (flat params dict) to Phase 4
calling convention (payload, context, yacht_id, user_id, user_context, db_client).

This is a migration shim. As handlers get rewritten to Phase 4 native, entries
here should be removed and replaced with direct handlers in their domain files.
"""

from typing import Any, Dict, Callable

# IMPORTANT: Do NOT import INTERNAL_HANDLERS at module level.
# It causes a circular import: internal_dispatcher → handlers → routes/handlers/__init__ → this file.
# Instead, import lazily inside each adapter call.


def _make_adapter(action_id: str) -> Callable:
    """
    Create a Phase 4 adapter for an INTERNAL_HANDLERS function.

    Phase 4 signature: (payload, context, yacht_id, user_id, user_context, db_client) -> dict
    INTERNAL_HANDLERS signature: (params: dict) -> dict
    """
    async def _adapted(
        payload: dict,
        context: dict,
        yacht_id: str,
        user_id: str,
        user_context: dict,
        db_client: Any,
    ) -> dict:
        # Lazy import to avoid circular dependency
        from action_router.dispatchers.internal_dispatcher import INTERNAL_HANDLERS
        handler_fn = INTERNAL_HANDLERS[action_id]
        # Merge into flat params dict expected by legacy handlers
        # Context contains resolved entity keys (e.g. entity_id → receiving_id)
        params = {
            "yacht_id": yacht_id,
            "user_id": user_id,
            "user_context": user_context,
            **context,
            **payload,
        }
        return await handler_fn(params)

    _adapted.__name__ = f"adapted_{action_id}"
    _adapted.__doc__ = f"Phase 4 adapter for INTERNAL_HANDLERS['{action_id}']"
    return _adapted


# All actions that exist in INTERNAL_HANDLERS but NOT in Phase 4 routes/handlers/
_ACTIONS_TO_ADAPT = [
    "accept_receiving",
    "add_certificate_note",
    "add_document_comment",
    "add_document_note",
    "add_entity_link",
    "add_list_item",
    "add_note",
    "add_part_note",
    "add_po_note",
    "add_receiving_item",
    "add_warranty_note",
    "add_wo_photo",
    "adjust_receiving_item",
    "apply_template",
    "approve_list",
    "archive_certificate",
    "archive_document",
    "archive_equipment",
    "archive_fault",
    "archive_handover",
    "archive_list",
    "archive_part",
    "archive_warranty",
    "assign_parent_equipment",
    "attach_file_to_equipment",
    "attach_image_with_comment",
    "attach_receiving_image_with_comment",
    "cancel_po",
    "classify_fault",
    "confirm_receiving",
    "convert_to_po",
    "create_equipment",
    "create_receiving",
    "decommission_and_replace_equipment",
    "decommission_equipment",
    "delete_document_comment",
    "delete_fault",
    "delete_list",
    "delete_part",
    "delete_po",
    "delete_work_order",
    "edit_handover_section",
    "extract_receiving_candidates",
    "file_warranty_claim",
    "flag_discrepancy",
    "flag_equipment_attention",
    "get_open_faults_for_equipment",
    "get_related_entities_for_equipment",
    "investigate_fault",
    "link_document_to_equipment",
    "link_invoice_document",
    "link_part_to_equipment",
    "list_document_comments",
    "open_document",
    "record_equipment_hours",
    "reject_receiving",
    "reorder_part",
    "restore_archived_equipment",
    "revoke_certificate",
    "set_equipment_status",
    "sign_handover",
    "submit_list",
    "suspend_certificate",
    "track_po_delivery",
    "update_document_comment",
    "update_part_details",
    "update_receiving_fields",
    "view_document",
    "view_maintenance_history",
    "view_receiving_history",
    "void_warranty",
]

HANDLERS: Dict[str, Callable] = {
    action_id: _make_adapter(action_id)
    for action_id in _ACTIONS_TO_ADAPT
}
