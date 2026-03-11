"""
CelesteOS - Natural Language Date Parser
=========================================

Parses natural language date expressions into Python date objects.

Supported patterns:
- "tomorrow" -> current date + 1 day
- "today" -> current date
- "in X days" -> current date + X days
- "next week" -> Monday of next week
- "next Monday/Tuesday/etc." -> next occurrence of weekday
- "end of month" -> last day of current month
- "urgent" / "asap" -> current date (today)

Usage:
    from common.date_parser import parse_relative_date
    from datetime import date, datetime

    # Basic usage (uses current date as base)
    result = parse_relative_date("tomorrow")
    # Returns: date.today() + timedelta(days=1)

    # With specific base date
    base = datetime(2024, 3, 15, tzinfo=timezone.utc)
    result = parse_relative_date("next week", base_date=base)
    # Returns: date(2024, 3, 18)  # Monday of next week

    # Non-date text returns None
    result = parse_relative_date("random text")
    # Returns: None
"""

import re
import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Optional


# =============================================================================
# WEEKDAY CONSTANTS
# =============================================================================

WEEKDAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

# Short forms of weekday names
WEEKDAY_SHORT_NAMES = {
    "mon": 0,
    "tue": 1,
    "tues": 1,
    "wed": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


# =============================================================================
# URGENCY KEYWORDS
# =============================================================================

URGENCY_KEYWORDS = frozenset({
    "urgent",
    "asap",
    "immediately",
    "now",
    "right away",
    "straight away",
})


# =============================================================================
# DATE PARSING FUNCTIONS
# =============================================================================

def get_base_date(base_date: Optional[datetime] = None) -> date:
    """
    Get the base date for relative calculations.

    Args:
        base_date: Optional datetime to use as base. If None, uses current UTC date.

    Returns:
        date object to use as base for calculations.
    """
    if base_date is not None:
        # If datetime is timezone-aware, convert to UTC first
        if base_date.tzinfo is not None:
            base_date = base_date.astimezone(timezone.utc)
        return base_date.date()
    else:
        # Use current UTC date
        return datetime.now(timezone.utc).date()


def parse_today_tomorrow(text: str, base: date) -> Optional[date]:
    """
    Parse 'today' or 'tomorrow' patterns.

    Args:
        text: Normalized text to parse
        base: Base date for calculations

    Returns:
        Parsed date or None if not a match
    """
    if text == "today":
        return base
    elif text == "tomorrow":
        return base + timedelta(days=1)
    elif text == "yesterday":
        return base - timedelta(days=1)
    return None


def parse_in_x_days(text: str, base: date) -> Optional[date]:
    """
    Parse 'in X days' patterns.

    Supports:
    - "in 3 days"
    - "in 1 day"
    - "3 days from now"

    Args:
        text: Normalized text to parse
        base: Base date for calculations

    Returns:
        Parsed date or None if not a match
    """
    # Pattern: "in X days" or "in X day"
    match = re.match(r"in\s+(\d+)\s+days?", text)
    if match:
        days = int(match.group(1))
        return base + timedelta(days=days)

    # Pattern: "X days from now"
    match = re.match(r"(\d+)\s+days?\s+from\s+now", text)
    if match:
        days = int(match.group(1))
        return base + timedelta(days=days)

    return None


def parse_next_week(text: str, base: date) -> Optional[date]:
    """
    Parse 'next week' pattern.

    Returns Monday of the next week.

    Args:
        text: Normalized text to parse
        base: Base date for calculations

    Returns:
        Monday of next week or None if not a match
    """
    if text == "next week":
        # Calculate days until next Monday
        # weekday() returns 0 for Monday, 6 for Sunday
        days_until_next_monday = (7 - base.weekday()) % 7
        if days_until_next_monday == 0:
            # If today is Monday, "next week" means the following Monday
            days_until_next_monday = 7
        return base + timedelta(days=days_until_next_monday)

    return None


def parse_next_weekday(text: str, base: date) -> Optional[date]:
    """
    Parse 'next Monday/Tuesday/etc.' patterns.

    Args:
        text: Normalized text to parse
        base: Base date for calculations

    Returns:
        Next occurrence of the weekday or None if not a match
    """
    # Pattern: "next monday", "next tuesday", etc.
    match = re.match(r"next\s+(\w+)", text)
    if match:
        weekday_text = match.group(1).lower()

        # Check full weekday names
        if weekday_text in WEEKDAY_NAMES:
            target_weekday = WEEKDAY_NAMES[weekday_text]
        # Check short weekday names
        elif weekday_text in WEEKDAY_SHORT_NAMES:
            target_weekday = WEEKDAY_SHORT_NAMES[weekday_text]
        else:
            return None

        # Calculate days until target weekday
        current_weekday = base.weekday()
        days_ahead = target_weekday - current_weekday

        # If the target day has already passed this week, go to next week
        if days_ahead <= 0:
            days_ahead += 7

        return base + timedelta(days=days_ahead)

    return None


def parse_end_of_month(text: str, base: date) -> Optional[date]:
    """
    Parse 'end of month' pattern.

    Args:
        text: Normalized text to parse
        base: Base date for calculations

    Returns:
        Last day of current month or None if not a match
    """
    if text in ("end of month", "end of the month", "eom", "month end"):
        # Get the last day of the current month
        _, last_day = calendar.monthrange(base.year, base.month)
        return date(base.year, base.month, last_day)

    return None


def parse_urgency(text: str, base: date) -> Optional[date]:
    """
    Parse urgency keywords that map to today.

    Args:
        text: Normalized text to parse
        base: Base date for calculations

    Returns:
        Today's date if urgency keyword, None otherwise
    """
    if text in URGENCY_KEYWORDS:
        return base

    return None


def parse_this_weekday(text: str, base: date) -> Optional[date]:
    """
    Parse 'this Monday/Tuesday/etc.' patterns.

    Returns the specified weekday of the current week.
    If the day has passed, returns that day (in the past).

    Args:
        text: Normalized text to parse
        base: Base date for calculations

    Returns:
        The weekday in current week or None if not a match
    """
    # Pattern: "this monday", "this tuesday", etc.
    match = re.match(r"this\s+(\w+)", text)
    if match:
        weekday_text = match.group(1).lower()

        # Check full weekday names
        if weekday_text in WEEKDAY_NAMES:
            target_weekday = WEEKDAY_NAMES[weekday_text]
        # Check short weekday names
        elif weekday_text in WEEKDAY_SHORT_NAMES:
            target_weekday = WEEKDAY_SHORT_NAMES[weekday_text]
        else:
            return None

        # Calculate days difference (can be negative if day passed)
        current_weekday = base.weekday()
        days_diff = target_weekday - current_weekday

        return base + timedelta(days=days_diff)

    return None


def parse_relative_date(
    text: str,
    base_date: Optional[datetime] = None
) -> Optional[date]:
    """
    Parse natural language date expressions into date objects.

    Supported patterns:
    - "today" -> current date
    - "tomorrow" -> current date + 1 day
    - "yesterday" -> current date - 1 day
    - "in X days" -> current date + X days
    - "X days from now" -> current date + X days
    - "next week" -> Monday of next week
    - "next Monday/Tuesday/etc." -> next occurrence of weekday
    - "this Monday/Tuesday/etc." -> weekday of current week
    - "end of month" / "eom" -> last day of current month
    - "urgent" / "asap" / "immediately" / "now" -> current date

    Args:
        text: Natural language date expression
        base_date: Optional datetime to use as base for calculations.
                   If None, uses current UTC date.
                   If timezone-aware, will be converted to UTC.

    Returns:
        date object if text is a recognized date expression, None otherwise.

    Examples:
        >>> parse_relative_date("tomorrow")  # Returns date.today() + timedelta(days=1)
        >>> parse_relative_date("next week")  # Returns Monday of next week
        >>> parse_relative_date("in 5 days")  # Returns date.today() + timedelta(days=5)
        >>> parse_relative_date("asap")  # Returns date.today()
        >>> parse_relative_date("random text")  # Returns None
    """
    if not text:
        return None

    # Normalize text: lowercase and strip whitespace
    normalized = text.lower().strip()

    # Skip empty strings
    if not normalized:
        return None

    # Get base date for calculations
    base = get_base_date(base_date)

    # Try each parser in order of specificity
    parsers = [
        parse_today_tomorrow,
        parse_in_x_days,
        parse_next_weekday,  # Check before parse_next_week (more specific)
        parse_next_week,
        parse_this_weekday,
        parse_end_of_month,
        parse_urgency,
    ]

    for parser in parsers:
        result = parser(normalized, base)
        if result is not None:
            return result

    # No pattern matched
    return None


__all__ = [
    "parse_relative_date",
    "get_base_date",
    "WEEKDAY_NAMES",
    "WEEKDAY_SHORT_NAMES",
    "URGENCY_KEYWORDS",
]
