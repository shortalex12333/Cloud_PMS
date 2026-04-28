from handlers.compliance_handler import HANDLERS


def test_all_actions_registered():
    # add_item_to_purchase, approve_purchase, upload_invoice, update_purchase_status
    # were removed — those 4 wrote to the legacy purchase_requests table and were
    # shadowed by PO_HANDLERS (purchase_order_handlers). Real implementations there.
    expected = {
        "view_compliance_status", "tag_for_survey", "create_purchase_request",
        "track_delivery", "log_delivery_received",
        "view_fleet_summary", "open_vessel", "export_fleet_summary",
        "request_predictive_insight",
    }
    assert set(HANDLERS.keys()) == expected
