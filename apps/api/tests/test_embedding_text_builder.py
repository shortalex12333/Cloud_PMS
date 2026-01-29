"""
Unit Tests for Embedding Text Builder

Tests normalization, synonym injection, secret scrubbing, and entity-specific builders.

Run:
    pytest apps/api/tests/test_embedding_text_builder.py -v
"""

import pytest
from services.embedding_text_builder import (
    normalize_text,
    apply_synonyms,
    deduplicate_tokens,
    scrub_secrets,
    build_work_order_embedding_text,
    build_equipment_embedding_text,
    build_fault_embedding_text,
    build_part_embedding_text,
    build_attachment_embedding_text,
    build_note_embedding_text,
    build_equipment_context,
    validate_embedding_text,
    build_embedding_text,
)


# =============================================================================
# Normalization Tests
# =============================================================================

def test_normalize_text_lowercase():
    """Test lowercase normalization"""
    assert normalize_text("Hydraulic PUMP Maintenance") == "hydraulic pump maintenance"


def test_normalize_text_temperature_symbols():
    """Test temperature symbol conversion"""
    assert normalize_text("Oil temp 85°C") == "oil temp 85c"
    assert normalize_text("Ambient 72°F") == "ambient 72f"
    assert normalize_text("Set to 90° C") == "set to 90c"


def test_normalize_text_whitespace_collapse():
    """Test whitespace collapse"""
    assert normalize_text("Hydraulic   pump    maintenance") == "hydraulic pump maintenance"
    assert normalize_text("Hydraulic\n\npump\tmaintenance") == "hydraulic pump maintenance"


def test_normalize_text_strip():
    """Test leading/trailing whitespace removal"""
    assert normalize_text("  Hydraulic pump  ") == "hydraulic pump"


def test_normalize_empty():
    """Test empty string handling"""
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


# =============================================================================
# Synonym Injection Tests
# =============================================================================

def test_apply_synonyms_me():
    """Test ME → main engine synonym"""
    assert apply_synonyms("me overhaul scheduled") == "main engine overhaul scheduled"


def test_apply_synonyms_ae():
    """Test AE → auxiliary engine synonym"""
    assert apply_synonyms("ae service required") == "auxiliary engine service required"


def test_apply_synonyms_fw_sw():
    """Test FW/SW synonyms"""
    assert apply_synonyms("fw pump and sw cooler") == "fresh water pump and sea water cooler"


def test_apply_synonyms_partial_match_prevention():
    """Test synonyms don't match partial words"""
    # "some" should not match "me"
    text = "some maintenance work"
    assert apply_synonyms(text) == text


def test_apply_synonyms_case_insensitive():
    """Test synonyms work after normalization"""
    text = normalize_text("ME and AE both need service")
    assert apply_synonyms(text) == "main engine and auxiliary engine both need service"


# =============================================================================
# Deduplication Tests
# =============================================================================

def test_deduplicate_tokens_consecutive():
    """Test consecutive duplicate removal"""
    assert deduplicate_tokens("pump pump hydraulic") == "pump hydraulic"
    assert deduplicate_tokens("replace replace replace seal") == "replace seal"


def test_deduplicate_tokens_non_consecutive():
    """Test non-consecutive duplicates kept"""
    # Only consecutive duplicates removed
    assert deduplicate_tokens("pump hydraulic pump") == "pump hydraulic pump"


def test_deduplicate_empty():
    """Test empty string handling"""
    assert deduplicate_tokens("") == ""


# =============================================================================
# Secret Scrubbing Tests
# =============================================================================

def test_scrub_emails():
    """Test email scrubbing"""
    assert scrub_secrets("Contact hod@example.com for info") == "Contact [email] for info"


def test_scrub_uuids():
    """Test UUID scrubbing"""
    text = "WO ID: 123e4567-e89b-12d3-a456-426614174000"
    assert "[id]" in scrub_secrets(text)


def test_scrub_tokens():
    """Test long base64-like token scrubbing"""
    text = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9LongTokenHere"
    assert "[token]" in scrub_secrets(text)


def test_scrub_passwords():
    """Test password scrubbing"""
    assert scrub_secrets("password: secret123") == "[redacted]"
    assert scrub_secrets("Password: ABC123") == "[redacted]"


# =============================================================================
# Work Order Builder Tests
# =============================================================================

def test_build_wo_basic():
    """Test basic WO embedding text"""
    wo = {
        'wo_number': '1234',
        'title': 'Hydraulic pump maintenance',
        'description': 'Replace seals',
    }
    text = build_work_order_embedding_text(wo)

    assert 'wo-1234' in text
    assert 'hydraulic pump maintenance' in text
    assert 'replace seals' in text


def test_build_wo_with_equipment():
    """Test WO with equipment context"""
    wo = {
        'wo_number': '1234',
        'title': 'Hydraulic pump maintenance',
        'equipment': {
            'name': 'Hydraulic Pump',
            'manufacturer': 'Parker',
            'model': 'PV270',
        }
    }
    text = build_work_order_embedding_text(wo)

    assert 'equipment: hydraulic pump - parker - pv270' in text


def test_build_wo_with_completion_notes():
    """Test WO with completion notes"""
    wo = {
        'title': 'Pump service',
        'completion_notes': 'Replaced seals, tested OK',
    }
    text = build_work_order_embedding_text(wo)

    assert 'notes: replaced seals, tested ok' in text


def test_build_wo_synonym_injection():
    """Test WO synonym injection (ME → main engine)"""
    wo = {
        'title': 'ME oil change',
        'description': 'Change ME oil filter',
    }
    text = build_work_order_embedding_text(wo)

    assert 'main engine' in text


def test_build_wo_length_cap():
    """Test WO text capped at 2000 chars"""
    wo = {
        'title': 'Test',
        'description': 'x' * 3000,  # Very long description
    }
    text = build_work_order_embedding_text(wo)

    assert len(text) <= 2000


def test_build_wo_no_query_echo():
    """Test WO builder doesn't echo query patterns"""
    wo = {
        'title': 'Pump maintenance',
        'description': 'Standard service',
    }
    text = build_work_order_embedding_text(wo)

    # Should not contain query patterns
    assert 'search for' not in text.lower()
    assert 'find' not in text.lower()
    assert 'show me' not in text.lower()


# =============================================================================
# Equipment Builder Tests
# =============================================================================

def test_build_equipment_basic():
    """Test basic equipment embedding text"""
    eq = {
        'name': 'Hydraulic Pump',
        'manufacturer': 'Parker',
        'model': 'PV270',
        'location': 'Engine Room',
        'system_type': 'Hydraulic',
    }
    text = build_equipment_embedding_text(eq)

    assert 'hydraulic pump' in text
    assert 'parker' in text
    assert 'model: pv270' in text
    assert 'location: engine room' in text
    assert 'system: hydraulic' in text


def test_build_equipment_length_cap():
    """Test equipment text capped at 1500 chars"""
    eq = {
        'name': 'Test Equipment',
        'description': 'x' * 2000,
    }
    text = build_equipment_embedding_text(eq)

    assert len(text) <= 1500


# =============================================================================
# Fault Builder Tests
# =============================================================================

def test_build_fault_basic():
    """Test basic fault embedding text"""
    fault = {
        'title': 'Hydraulic pressure low',
        'description': 'Pressure dropped to 50 bar',
        'severity': 'high',
        'status': 'open',
    }
    text = build_fault_embedding_text(fault)

    assert 'hydraulic pressure low' in text
    assert 'pressure dropped to 50 bar' in text
    assert 'severity: high' in text
    assert 'status: open' in text


def test_build_fault_with_equipment():
    """Test fault with equipment context"""
    fault = {
        'title': 'Pressure low',
        'equipment': {
            'name': 'Hydraulic Pump',
            'manufacturer': 'Parker',
        }
    }
    text = build_fault_embedding_text(fault)

    assert 'equipment: hydraulic pump - parker' in text


def test_build_fault_length_cap():
    """Test fault text capped at 1500 chars"""
    fault = {
        'title': 'Test Fault',
        'description': 'x' * 2000,
    }
    text = build_fault_embedding_text(fault)

    assert len(text) <= 1500


# =============================================================================
# Part Builder Tests
# =============================================================================

def test_build_part_basic():
    """Test basic part embedding text"""
    part = {
        'name': 'Hydraulic seal',
        'part_number': 'HS-1234',
        'manufacturer': 'Parker',
        'description': 'O-ring seal for hydraulic pump',
        'category': 'Seals',
    }
    text = build_part_embedding_text(part)

    assert 'hydraulic seal' in text
    assert 'p/n: hs-1234' in text
    assert 'parker' in text
    assert 'o-ring seal for hydraulic pump' in text
    assert 'category: seals' in text


def test_build_part_length_cap():
    """Test part text capped at 1000 chars"""
    part = {
        'name': 'Test Part',
        'description': 'x' * 1500,
    }
    text = build_part_embedding_text(part)

    assert len(text) <= 1000


# =============================================================================
# Attachment Builder Tests
# =============================================================================

def test_build_attachment_basic():
    """Test basic attachment embedding text"""
    att = {
        'filename': 'hydraulic_pump_manual.pdf',
        'description': 'Service manual for Parker PV270',
        'mime_type': 'application/pdf',
    }
    text = build_attachment_embedding_text(att)

    assert 'hydraulic_pump_manual.pdf' in text
    assert 'service manual for parker pv270' in text
    assert 'type: application/pdf' in text


def test_build_attachment_length_cap():
    """Test attachment text capped at 500 chars"""
    att = {
        'filename': 'test.pdf',
        'description': 'x' * 1000,
    }
    text = build_attachment_embedding_text(att)

    assert len(text) <= 500


# =============================================================================
# Note Builder Tests
# =============================================================================

def test_build_note_basic():
    """Test basic note embedding text"""
    note = {
        'note_text': 'Replaced hydraulic pump seals. Tested OK. No leaks observed.',
    }
    text = build_note_embedding_text(note)

    assert 'replaced hydraulic pump seals' in text
    assert 'tested ok' in text


def test_build_note_length_cap():
    """Test note text capped at 200 chars"""
    note = {
        'note_text': 'x' * 500,
    }
    text = build_note_embedding_text(note)

    assert len(text) <= 200


# =============================================================================
# Equipment Context Builder Tests
# =============================================================================

def test_build_equipment_context():
    """Test equipment context for joining"""
    eq = {
        'name': 'Hydraulic Pump',
        'manufacturer': 'Parker',
        'model': 'PV270',
        'location': 'Engine Room',
    }
    text = build_equipment_context(eq)

    assert 'hydraulic pump - parker - pv270 - location: engine room' in text


def test_build_equipment_context_length_cap():
    """Test equipment context capped at 300 chars"""
    eq = {
        'name': 'x' * 500,
    }
    text = build_equipment_context(eq)

    assert len(text) <= 300


# =============================================================================
# Validation Tests
# =============================================================================

def test_validate_embedding_text_valid():
    """Test validation passes for valid text"""
    result = validate_embedding_text("hydraulic pump maintenance", "work_order")

    assert result['valid'] is True
    assert result['errors'] == []


def test_validate_embedding_text_empty():
    """Test validation fails for empty text"""
    result = validate_embedding_text("", "work_order")

    assert result['valid'] is False
    assert "Empty embedding text" in result['errors']


def test_validate_embedding_text_too_long():
    """Test validation fails for text exceeding max length"""
    text = "x" * 3000
    result = validate_embedding_text(text, "work_order")

    assert result['valid'] is False
    assert any('exceeds max length' in err for err in result['errors'])


def test_validate_embedding_text_query_echo():
    """Test validation detects query echo patterns"""
    text = "search for hydraulic pump"
    result = validate_embedding_text(text, "work_order")

    assert result['valid'] is False
    assert any('query echo' in err.lower() for err in result['errors'])


# =============================================================================
# Factory Function Tests
# =============================================================================

def test_build_embedding_text_factory_wo():
    """Test factory function for work order"""
    wo = {
        'wo_number': '1234',
        'title': 'Hydraulic pump maintenance',
    }
    text = build_embedding_text('work_order', wo)

    assert 'wo-1234' in text
    assert 'hydraulic pump maintenance' in text


def test_build_embedding_text_factory_equipment():
    """Test factory function for equipment"""
    eq = {
        'name': 'Hydraulic Pump',
        'manufacturer': 'Parker',
    }
    text = build_embedding_text('equipment', eq)

    assert 'hydraulic pump' in text
    assert 'parker' in text


def test_build_embedding_text_factory_invalid_type():
    """Test factory function rejects invalid entity type"""
    with pytest.raises(ValueError, match="Invalid entity_type"):
        build_embedding_text('invalid_type', {})


# =============================================================================
# Integration Tests (Multi-Step Processing)
# =============================================================================

def test_integration_normalize_then_synonyms():
    """Test full pipeline: normalize → synonyms → dedupe"""
    wo = {
        'title': 'ME Oil Change',
        'description': 'Change ME oil filter and FW cooler',
    }
    text = build_work_order_embedding_text(wo)

    # Should be lowercase
    assert text.islower()
    # Should have synonyms applied
    assert 'main engine' in text
    assert 'fresh water' in text
    # Should not have 'me' or 'fw' (replaced by synonyms)
    assert ' me ' not in text
    assert ' fw ' not in text


def test_integration_secret_scrubbing():
    """Test secrets are scrubbed in full pipeline"""
    wo = {
        'title': 'Contact hod@example.com for approval',
        'description': 'Password: secret123',
    }
    text = build_work_order_embedding_text(wo)

    assert '[email]' in text
    assert '[redacted]' in text
    assert 'hod@example.com' not in text
    assert 'secret123' not in text


def test_integration_deduplication():
    """Test deduplication in full pipeline"""
    wo = {
        'title': 'Hydraulic hydraulic pump pump maintenance',
    }
    text = build_work_order_embedding_text(wo)

    # Consecutive duplicates should be removed
    assert 'hydraulic hydraulic' not in text
    assert 'pump pump' not in text


# =============================================================================
# Edge Cases
# =============================================================================

def test_edge_case_all_fields_empty():
    """Test builder handles all empty fields gracefully"""
    wo = {
        'wo_number': '',
        'title': '',
        'description': '',
    }
    text = build_work_order_embedding_text(wo)

    # Should return empty or minimal text, not crash
    assert isinstance(text, str)


def test_edge_case_unicode_normalization():
    """Test unicode characters are handled"""
    wo = {
        'title': 'Café hydraulic pump maintenance',
    }
    text = build_work_order_embedding_text(wo)

    # Should not crash, lowercase applied
    assert 'café' in text.lower()


def test_edge_case_special_chars():
    """Test special characters don't break processing"""
    wo = {
        'title': 'Pump @ 3000 RPM & 85°C',
    }
    text = build_work_order_embedding_text(wo)

    # Should normalize temperature
    assert '85c' in text
    # Should not crash on @ and &
    assert isinstance(text, str)
