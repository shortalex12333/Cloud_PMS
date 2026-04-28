from handlers.part_handlers import HANDLERS


def test_all_actions_registered():
    # archive_part, delete_part, suggest_parts are served via ADAPTER_HANDLERS
    # (INTERNAL_HANDLERS soft-delete / NYI shim) — not registered here
    expected = {
        "view_part_details", "update_part_details",
        "add_to_shopping_list", "reorder_part",
        "consume_part", "receive_part", "transfer_part",
        "adjust_stock_quantity", "write_off_part",
        "generate_part_labels", "request_label_output",
        "view_part_stock", "view_part_location", "view_part_usage",
        "view_linked_equipment", "order_part", "scan_part_barcode",
        "check_stock_level", "log_part_usage",
        "view_low_stock",
    }
    assert set(HANDLERS.keys()) == expected


def test_update_part_details_is_not_view_alias():
    from handlers.part_handlers import _p4_update_part_details, _p4_view_part_details
    assert _p4_update_part_details is not _p4_view_part_details
