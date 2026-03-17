from routes.handlers.equipment_handler import HANDLERS


def test_all_actions_registered():
    expected = {
        "update_equipment_status", "view_equipment", "view_equipment_detail",
        "view_equipment_details", "view_equipment_history", "view_equipment_parts",
        "view_linked_faults", "view_equipment_manual", "add_equipment_note",
        "suggest_parts",
    }
    assert set(HANDLERS.keys()) == expected


def test_view_equipment_details_is_alias():
    assert HANDLERS["view_equipment_details"] is HANDLERS["view_equipment_detail"]
