"""
Tests for intent detection module
"""
import pytest
from services.entity_extraction import extract_entities
from services.intent_detection import detect_intent
from models.responses import IntentType


def test_diagnose_fault_intent():
    """Test fault diagnosis intent"""
    query = "fault code E047 on main engine"
    entities = extract_entities(query)

    result = detect_intent(query, entities)

    assert result.intent == IntentType.DIAGNOSE_FAULT
    assert result.confidence >= 0.8


def test_find_document_intent():
    """Test document finding intent"""
    query = "find CAT 3516 coolant manual"
    entities = extract_entities(query)

    result = detect_intent(query, entities)

    assert result.intent == IntentType.FIND_DOCUMENT
    assert result.confidence >= 0.6


def test_create_work_order_intent():
    """Test work order creation intent"""
    query = "create work order for stabiliser pump leak"
    entities = extract_entities(query)

    result = detect_intent(query, entities)

    assert result.intent == IntentType.CREATE_WORK_ORDER
    assert result.confidence >= 0.7


def test_add_to_handover_intent():
    """Test handover addition intent"""
    query = "add this to handover"
    entities = extract_entities(query)

    result = detect_intent(query, entities)

    assert result.intent == IntentType.ADD_TO_HANDOVER
    assert result.confidence >= 0.8


def test_find_part_intent():
    """Test part finding intent"""
    query = "racor 2040 filter for generator"
    entities = extract_entities(query)

    result = detect_intent(query, entities)

    assert result.intent in [IntentType.FIND_PART, IntentType.GENERAL_SEARCH]


def test_predictive_intent():
    """Test predictive maintenance intent"""
    query = "is anything likely to fail soon in HVAC?"
    entities = extract_entities(query)

    result = detect_intent(query, entities)

    assert result.intent == IntentType.PREDICTIVE_REQUEST
    assert result.confidence >= 0.7


def test_general_search_fallback():
    """Test general search as fallback"""
    query = "something vague"
    entities = extract_entities(query)

    result = detect_intent(query, entities)

    assert result.intent == IntentType.GENERAL_SEARCH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
