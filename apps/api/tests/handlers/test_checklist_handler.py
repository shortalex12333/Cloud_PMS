from routes.handlers.checklist_handler import HANDLERS


def test_all_actions_registered():
    expected = {
        "view_checklist", "mark_checklist_item_complete", "add_checklist_note",
        "add_checklist_item", "add_checklist_photo", "view_smart_summary",
        "upload_photo", "record_voice_note", "show_manual_section",
    }
    assert set(HANDLERS.keys()) == expected
