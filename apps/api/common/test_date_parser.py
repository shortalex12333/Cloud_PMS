"""
CelesteOS - Date Parser Unit Tests
===================================

Unit tests for the natural language date parser.

Run with:
    pytest apps/api/common/test_date_parser.py -v
"""

import pytest
from datetime import date, datetime, timedelta, timezone
import calendar

from common.date_parser import (
    parse_relative_date,
    get_base_date,
    parse_today_tomorrow,
    parse_in_x_days,
    parse_next_week,
    parse_next_weekday,
    parse_end_of_month,
    parse_urgency,
    parse_this_weekday,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def fixed_date():
    """Fixed date for consistent testing: Wednesday, March 15, 2024."""
    return datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fixed_base(fixed_date):
    """Base date derived from fixed_date."""
    return fixed_date.date()


# =============================================================================
# TEST get_base_date
# =============================================================================

def test_get_base_date_with_none():
    """Test get_base_date with None returns today's date."""
    result = get_base_date(None)
    expected = datetime.now(timezone.utc).date()
    assert result == expected


def test_get_base_date_with_datetime():
    """Test get_base_date with datetime returns date portion."""
    dt = datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
    result = get_base_date(dt)
    assert result == date(2024, 6, 15)


def test_get_base_date_with_naive_datetime():
    """Test get_base_date with naive datetime."""
    dt = datetime(2024, 6, 15, 14, 30, 0)
    result = get_base_date(dt)
    assert result == date(2024, 6, 15)


# =============================================================================
# TEST parse_today_tomorrow
# =============================================================================

def test_parse_today(fixed_base):
    """Test parsing 'today'."""
    result = parse_today_tomorrow("today", fixed_base)
    assert result == fixed_base


def test_parse_tomorrow(fixed_base):
    """Test parsing 'tomorrow'."""
    result = parse_today_tomorrow("tomorrow", fixed_base)
    assert result == fixed_base + timedelta(days=1)


def test_parse_yesterday(fixed_base):
    """Test parsing 'yesterday'."""
    result = parse_today_tomorrow("yesterday", fixed_base)
    assert result == fixed_base - timedelta(days=1)


def test_parse_today_tomorrow_no_match(fixed_base):
    """Test non-matching text returns None."""
    result = parse_today_tomorrow("random", fixed_base)
    assert result is None


# =============================================================================
# TEST parse_in_x_days
# =============================================================================

def test_parse_in_x_days_single(fixed_base):
    """Test parsing 'in 1 day'."""
    result = parse_in_x_days("in 1 day", fixed_base)
    assert result == fixed_base + timedelta(days=1)


def test_parse_in_x_days_plural(fixed_base):
    """Test parsing 'in 5 days'."""
    result = parse_in_x_days("in 5 days", fixed_base)
    assert result == fixed_base + timedelta(days=5)


def test_parse_in_x_days_large_number(fixed_base):
    """Test parsing 'in 30 days'."""
    result = parse_in_x_days("in 30 days", fixed_base)
    assert result == fixed_base + timedelta(days=30)


def test_parse_days_from_now(fixed_base):
    """Test parsing '3 days from now'."""
    result = parse_in_x_days("3 days from now", fixed_base)
    assert result == fixed_base + timedelta(days=3)


def test_parse_in_x_days_no_match(fixed_base):
    """Test non-matching text returns None."""
    result = parse_in_x_days("random", fixed_base)
    assert result is None


# =============================================================================
# TEST parse_next_week
# =============================================================================

def test_parse_next_week_from_wednesday(fixed_base):
    """Test 'next week' from Wednesday returns next Monday."""
    # fixed_base is Wednesday, March 15, 2024
    result = parse_next_week("next week", fixed_base)
    # Next Monday should be March 18, 2024
    assert result == date(2024, 3, 18)
    assert result.weekday() == 0  # Monday


def test_parse_next_week_from_monday():
    """Test 'next week' from Monday returns following Monday."""
    # Monday, March 11, 2024
    base = date(2024, 3, 11)
    result = parse_next_week("next week", base)
    # Should be March 18, 2024 (7 days later)
    assert result == date(2024, 3, 18)
    assert result.weekday() == 0  # Monday


def test_parse_next_week_from_sunday():
    """Test 'next week' from Sunday returns next Monday."""
    # Sunday, March 17, 2024
    base = date(2024, 3, 17)
    result = parse_next_week("next week", base)
    # Should be March 18, 2024 (1 day later)
    assert result == date(2024, 3, 18)
    assert result.weekday() == 0  # Monday


def test_parse_next_week_no_match(fixed_base):
    """Test non-matching text returns None."""
    result = parse_next_week("random", fixed_base)
    assert result is None


# =============================================================================
# TEST parse_next_weekday
# =============================================================================

def test_parse_next_monday_from_wednesday(fixed_base):
    """Test 'next monday' from Wednesday returns next Monday."""
    # fixed_base is Wednesday, March 15, 2024
    result = parse_next_weekday("next monday", fixed_base)
    # Next Monday should be March 18, 2024
    assert result == date(2024, 3, 18)


def test_parse_next_friday_from_wednesday(fixed_base):
    """Test 'next friday' from Wednesday returns this Friday."""
    # fixed_base is Wednesday, March 15, 2024
    result = parse_next_weekday("next friday", fixed_base)
    # Next Friday should be March 15 + 2 = March 17... wait, Friday is 2 days ahead
    # Wednesday (2) -> Friday (4), diff = 2
    assert result == date(2024, 3, 22)  # Actually should be next week since day is ahead


def test_parse_next_wednesday_from_wednesday(fixed_base):
    """Test 'next wednesday' from Wednesday returns next Wednesday."""
    # fixed_base is Wednesday, March 15, 2024
    result = parse_next_weekday("next wednesday", fixed_base)
    # Should be exactly 7 days later
    assert result == date(2024, 3, 22)


def test_parse_next_tuesday_from_wednesday(fixed_base):
    """Test 'next tuesday' from Wednesday returns next Tuesday."""
    # fixed_base is Wednesday, March 15, 2024
    # Tuesday has already passed, so next Tuesday is March 19
    result = parse_next_weekday("next tuesday", fixed_base)
    assert result == date(2024, 3, 19)


def test_parse_next_weekday_short_form(fixed_base):
    """Test parsing short weekday form 'next mon'."""
    result = parse_next_weekday("next mon", fixed_base)
    assert result == date(2024, 3, 18)


def test_parse_next_weekday_thurs(fixed_base):
    """Test parsing 'next thurs'."""
    # Wednesday -> Thursday is 1 day ahead
    result = parse_next_weekday("next thurs", fixed_base)
    assert result == date(2024, 3, 21)


def test_parse_next_weekday_no_match(fixed_base):
    """Test non-weekday after 'next' returns None."""
    result = parse_next_weekday("next month", fixed_base)
    assert result is None


# =============================================================================
# TEST parse_this_weekday
# =============================================================================

def test_parse_this_friday_from_wednesday(fixed_base):
    """Test 'this friday' from Wednesday returns this Friday."""
    # fixed_base is Wednesday, March 15, 2024
    result = parse_this_weekday("this friday", fixed_base)
    # This Friday is March 15 + 2 = March 17
    assert result == date(2024, 3, 17)


def test_parse_this_monday_from_wednesday(fixed_base):
    """Test 'this monday' from Wednesday returns Monday (past)."""
    # fixed_base is Wednesday, March 15, 2024
    result = parse_this_weekday("this monday", fixed_base)
    # This Monday was March 11 (2 days before)
    assert result == date(2024, 3, 11)


def test_parse_this_wednesday_from_wednesday(fixed_base):
    """Test 'this wednesday' from Wednesday returns same day."""
    result = parse_this_weekday("this wednesday", fixed_base)
    assert result == fixed_base


# =============================================================================
# TEST parse_end_of_month
# =============================================================================

def test_parse_end_of_month_march(fixed_base):
    """Test 'end of month' in March."""
    result = parse_end_of_month("end of month", fixed_base)
    assert result == date(2024, 3, 31)


def test_parse_end_of_month_february_leap_year():
    """Test 'end of month' in February (leap year 2024)."""
    base = date(2024, 2, 15)
    result = parse_end_of_month("end of month", base)
    assert result == date(2024, 2, 29)


def test_parse_end_of_month_february_non_leap():
    """Test 'end of month' in February (non-leap year)."""
    base = date(2023, 2, 15)
    result = parse_end_of_month("end of month", base)
    assert result == date(2023, 2, 28)


def test_parse_end_of_the_month(fixed_base):
    """Test 'end of the month' variation."""
    result = parse_end_of_month("end of the month", fixed_base)
    assert result == date(2024, 3, 31)


def test_parse_eom(fixed_base):
    """Test 'eom' abbreviation."""
    result = parse_end_of_month("eom", fixed_base)
    assert result == date(2024, 3, 31)


def test_parse_month_end(fixed_base):
    """Test 'month end' variation."""
    result = parse_end_of_month("month end", fixed_base)
    assert result == date(2024, 3, 31)


# =============================================================================
# TEST parse_urgency
# =============================================================================

def test_parse_urgent(fixed_base):
    """Test 'urgent' returns today."""
    result = parse_urgency("urgent", fixed_base)
    assert result == fixed_base


def test_parse_asap(fixed_base):
    """Test 'asap' returns today."""
    result = parse_urgency("asap", fixed_base)
    assert result == fixed_base


def test_parse_immediately(fixed_base):
    """Test 'immediately' returns today."""
    result = parse_urgency("immediately", fixed_base)
    assert result == fixed_base


def test_parse_now(fixed_base):
    """Test 'now' returns today."""
    result = parse_urgency("now", fixed_base)
    assert result == fixed_base


def test_parse_urgency_no_match(fixed_base):
    """Test non-urgency keyword returns None."""
    result = parse_urgency("random", fixed_base)
    assert result is None


# =============================================================================
# TEST parse_relative_date (MAIN FUNCTION)
# =============================================================================

def test_parse_relative_date_tomorrow(fixed_date):
    """Test main function with 'tomorrow'."""
    result = parse_relative_date("tomorrow", fixed_date)
    assert result == date(2024, 3, 16)


def test_parse_relative_date_next_week(fixed_date):
    """Test main function with 'next week'."""
    result = parse_relative_date("next week", fixed_date)
    assert result.weekday() == 0  # Monday


def test_parse_relative_date_in_5_days(fixed_date):
    """Test main function with 'in 5 days'."""
    result = parse_relative_date("in 5 days", fixed_date)
    assert result == date(2024, 3, 20)


def test_parse_relative_date_asap(fixed_date):
    """Test main function with 'asap'."""
    result = parse_relative_date("asap", fixed_date)
    assert result == date(2024, 3, 15)


def test_parse_relative_date_random_text(fixed_date):
    """Test main function with non-date text returns None."""
    result = parse_relative_date("random text", fixed_date)
    assert result is None


def test_parse_relative_date_case_insensitive(fixed_date):
    """Test main function is case-insensitive."""
    result1 = parse_relative_date("TOMORROW", fixed_date)
    result2 = parse_relative_date("Tomorrow", fixed_date)
    result3 = parse_relative_date("tomorrow", fixed_date)
    assert result1 == result2 == result3


def test_parse_relative_date_with_whitespace(fixed_date):
    """Test main function handles leading/trailing whitespace."""
    result = parse_relative_date("  tomorrow  ", fixed_date)
    assert result == date(2024, 3, 16)


def test_parse_relative_date_empty_string(fixed_date):
    """Test empty string returns None."""
    result = parse_relative_date("", fixed_date)
    assert result is None


def test_parse_relative_date_none():
    """Test None input returns None."""
    result = parse_relative_date(None)
    assert result is None


def test_parse_relative_date_next_monday(fixed_date):
    """Test 'next Monday' from Wednesday."""
    result = parse_relative_date("next Monday", fixed_date)
    assert result == date(2024, 3, 18)


def test_parse_relative_date_end_of_month(fixed_date):
    """Test 'end of month' in March."""
    result = parse_relative_date("end of month", fixed_date)
    assert result == date(2024, 3, 31)


# =============================================================================
# TEST INTEGRATION REQUIREMENTS
# =============================================================================

def test_requirement_tomorrow():
    """Test requirement: parse_relative_date('tomorrow') == date.today() + timedelta(days=1)."""
    result = parse_relative_date("tomorrow")
    expected = date.today() + timedelta(days=1)
    assert result == expected


def test_requirement_next_week_is_monday():
    """Test requirement: parse_relative_date('next week').weekday() == 0 (Monday)."""
    result = parse_relative_date("next week")
    assert result.weekday() == 0


def test_requirement_in_5_days():
    """Test requirement: parse_relative_date('in 5 days') == date.today() + timedelta(days=5)."""
    result = parse_relative_date("in 5 days")
    expected = date.today() + timedelta(days=5)
    assert result == expected


def test_requirement_asap():
    """Test requirement: parse_relative_date('asap') == date.today()."""
    result = parse_relative_date("asap")
    expected = date.today()
    assert result == expected


def test_requirement_random_text_none():
    """Test requirement: parse_relative_date('random text') is None."""
    result = parse_relative_date("random text")
    assert result is None


# =============================================================================
# EDGE CASES
# =============================================================================

def test_next_week_at_year_boundary():
    """Test 'next week' at year boundary."""
    # Sunday, December 31, 2023
    base = datetime(2023, 12, 31, tzinfo=timezone.utc)
    result = parse_relative_date("next week", base)
    # Should be January 1, 2024 (Monday)
    assert result == date(2024, 1, 1)


def test_end_of_month_december():
    """Test 'end of month' in December."""
    base = datetime(2024, 12, 15, tzinfo=timezone.utc)
    result = parse_relative_date("end of month", base)
    assert result == date(2024, 12, 31)


def test_in_zero_days(fixed_date):
    """Test 'in 0 days' returns today."""
    result = parse_relative_date("in 0 days", fixed_date)
    assert result == date(2024, 3, 15)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
