"""
Tests for temporal_parser.py

Verifies natural language date parsing with timezone awareness.
"""

from common.temporal_parser import parse_temporal_phrase


def test_tomorrow():
    """Test 'tomorrow' parsing."""
    result = parse_temporal_phrase("tomorrow", "America/New_York", "2026-03-01T16:00:00-05:00")
    assert result.value == "2026-03-02"
    assert result.confidence >= 0.90
    assert "tomorrow" in result.assumption


def test_next_week():
    """Test 'next week' parsing - should return next Monday."""
    result = parse_temporal_phrase("next week", "America/New_York", "2026-03-01T16:00:00-05:00")
    # March 1, 2026 is a Sunday, so next Monday is March 2
    # Wait, let me calculate: Sunday March 1 -> next Monday is March 2
    # But the plan says March 9, so let me check the logic
    # Actually March 1, 2026 needs calculation:
    # If today is Sunday (weekday 6), next Monday (weekday 0) is: (0 - 6) % 7 = 1 day ahead? No.
    # Days until Monday: (7 - 6) % 7 = 1. But we want "next" Monday, so if today is Sunday,
    # next Monday is 1 day away (March 2). But the plan expects March 9 (next week's Monday).

    # Per plan expectation and CONTEXT.md "next week as next Monday":
    # This should be the start of NEXT week, not just "next Monday occurrence"
    assert result.value == "2026-03-09"  # Monday of next week
    assert result.confidence >= 0.85
    assert "interpreted next week as next Monday" == result.assumption


def test_next_tuesday():
    """Test 'next tuesday' parsing."""
    result = parse_temporal_phrase("next tuesday", "America/New_York", "2026-03-01T16:00:00-05:00")
    # March 1, 2026 is Sunday, next Tuesday is March 3
    assert result.value == "2026-03-03"
    assert result.confidence >= 0.95


def test_in_3_days():
    """Test 'in 3 days' parsing."""
    result = parse_temporal_phrase("in 3 days", "America/New_York", "2026-03-01T16:00:00-05:00")
    assert result.value == "2026-03-04"
    assert result.confidence >= 0.90


def test_today():
    """Test 'today' parsing."""
    result = parse_temporal_phrase("today", "America/New_York", "2026-03-01T16:00:00-05:00")
    assert result.value == "2026-03-01"
    assert result.confidence >= 0.95


def test_urgent():
    """Test 'urgent' maps to today."""
    result = parse_temporal_phrase("urgent", "America/New_York", "2026-03-01T16:00:00-05:00")
    assert result.value == "2026-03-01"
    assert result.confidence >= 0.95


def test_explicit_iso_date():
    """Test explicit ISO date passes through."""
    result = parse_temporal_phrase("2026-05-15", "America/New_York", "2026-03-01T16:00:00-05:00")
    assert result.value == "2026-05-15"
    assert result.confidence == 1.0


def test_unparseable():
    """Test unparseable phrase returns None."""
    result = parse_temporal_phrase("random text", "America/New_York", "2026-03-01T16:00:00-05:00")
    assert result.value is None
    assert result.confidence == 0.0


def test_empty_phrase():
    """Test empty phrase returns None."""
    result = parse_temporal_phrase("", "America/New_York", "2026-03-01T16:00:00-05:00")
    assert result.value is None
    assert result.confidence == 0.0
