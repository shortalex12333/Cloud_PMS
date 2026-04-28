# tests/handlers/test_fault_handler.py
import pytest
from handlers.fault_handler import HANDLERS

def test_all_actions_registered():
    expected = {
        "report_fault", "acknowledge_fault", "resolve_fault", "diagnose_fault",
        "investigate_fault", "close_fault", "update_fault", "reopen_fault",
        "mark_fault_false_alarm", "add_fault_photo", "view_fault_detail",
        "view_fault_history", "add_fault_note", "list_faults",
        "archive_fault", "delete_fault", "link_parts_to_fault", "unlink_part_from_fault",
    }
    assert set(HANDLERS.keys()) == expected

def test_handlers_are_callable():
    for name, fn in HANDLERS.items():
        assert callable(fn), f"{name} is not callable"

def test_aliases_point_to_same_function():
    assert HANDLERS["investigate_fault"] is HANDLERS["diagnose_fault"]
    assert HANDLERS["delete_fault"] is HANDLERS["archive_fault"]
