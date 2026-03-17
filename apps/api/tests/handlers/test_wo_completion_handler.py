# tests/handlers/test_wo_completion_handler.py
import pytest
from routes.handlers.wo_completion_handler import HANDLERS

def test_all_actions_registered():
    expected = {
        "create_work_order_from_fault",
        "add_note_to_work_order",
        "add_part_to_work_order",
        "mark_work_order_complete",
        "reassign_work_order",
        "archive_work_order",
        "add_work_order_note",
    }
    assert set(HANDLERS.keys()) == expected

def test_handlers_are_callable():
    import asyncio
    for name, fn in HANDLERS.items():
        assert callable(fn), f"{name} is not callable"
