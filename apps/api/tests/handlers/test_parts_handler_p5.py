from routes.handlers.parts_handler_p5 import HANDLERS


def test_all_actions_registered():
    expected = {
        "check_stock_level", "log_part_usage", "view_part_details", "consume_part",
        "receive_part", "transfer_part", "adjust_stock_quantity", "write_off_part",
        "generate_part_labels", "request_label_output", "view_part_stock",
        "view_part_location", "view_part_usage", "view_linked_equipment",
        "order_part", "scan_part_barcode", "add_to_shopping_list",
    }
    assert set(HANDLERS.keys()) == expected
