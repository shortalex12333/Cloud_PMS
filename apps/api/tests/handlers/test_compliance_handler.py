from routes.handlers.compliance_handler import HANDLERS


def test_all_actions_registered():
    expected = {
        "view_compliance_status", "tag_for_survey", "create_purchase_request",
        "add_item_to_purchase", "approve_purchase", "upload_invoice",
        "track_delivery", "log_delivery_received", "update_purchase_status",
        "view_fleet_summary", "open_vessel", "export_fleet_summary",
        "request_predictive_insight",
    }
    assert set(HANDLERS.keys()) == expected
