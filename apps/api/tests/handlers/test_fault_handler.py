# tests/handlers/test_fault_handler.py
import pytest
from routes.handlers.fault_handler import HANDLERS

def test_all_actions_registered():
    expected = {
        "report_fault", "acknowledge_fault", "resolve_fault", "diagnose_fault",
        "close_fault", "update_fault", "reopen_fault", "mark_fault_false_alarm",
        "add_fault_photo", "view_fault_detail", "view_fault_history",
        "add_fault_note", "list_faults",
    }
    assert set(HANDLERS.keys()) == expected

def test_handlers_are_callable():
    for name, fn in HANDLERS.items():
        assert callable(fn), f"{name} is not callable"
