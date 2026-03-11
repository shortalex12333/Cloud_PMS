"""
CelesteOS - Temporal Parser
============================

Parses natural language temporal phrases to ISO dates with timezone awareness.

Supports patterns:
- "tomorrow" -> now + 1 day
- "next week" -> start of next Monday
- "next tuesday" -> next occurrence of Tuesday
- "in 3 days" -> now + 3 days
- "urgent" / "asap" -> today
- "next month" -> first day of next month
- "end of Q1/Q2/Q3/Q4" -> last day of quarter
- "until YYYY" -> December 31 of that year
- "charter season" -> May 1 to October 31 range

Prefix handling:
- Strips "due", "by", "expiring", "valid until" before parsing

Returns TemporalResult with:
- value: ISO date string (YYYY-MM-DD)
- confidence: float (0.0-1.0)
- assumption: string explaining interpretation
"""

from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import re
import logging

logger = logging.getLogger(__name__)


# =========================================================================
# PREFIX PATTERNS TO STRIP
# =========================================================================
PREFIX_PATTERNS = [
    r"^due\s+",
    r"^by\s+",
    r"^expiring\s+",
    r"^valid\s+until\s+",
    r"^expires\s+",
    r"^deadline\s+",
]


def strip_prefix(phrase: str) -> Tuple[str, Optional[str]]:
    """
    Strip common prefix words from temporal phrases.

    Args:
        phrase: The original phrase

    Returns:
        Tuple of (stripped_phrase, prefix_found or None)

    Examples:
        >>> strip_prefix("due next month")
        ("next month", "due")
        >>> strip_prefix("expiring next week")
        ("next week", "expiring")
        >>> strip_prefix("tomorrow")
        ("tomorrow", None)
    """
    phrase_lower = phrase.strip().lower()

    for pattern in PREFIX_PATTERNS:
        match = re.match(pattern, phrase_lower)
        if match:
            prefix = match.group(0).strip()
            stripped = phrase_lower[match.end():].strip()
            return stripped, prefix

    return phrase_lower, None


def get_quarter_end(year: int, quarter: int) -> date:
    """
    Get the last day of a given quarter.

    Args:
        year: The year
        quarter: Quarter number (1-4)

    Returns:
        date: Last day of the quarter
    """
    quarter_end_months = {1: 3, 2: 6, 3: 9, 4: 12}
    quarter_end_days = {1: 31, 2: 30, 3: 30, 4: 31}

    month = quarter_end_months[quarter]
    day = quarter_end_days[quarter]

    return date(year, month, day)


def get_current_quarter(d: date) -> int:
    """Get the quarter number (1-4) for a given date."""
    return (d.month - 1) // 3 + 1


@dataclass
class TemporalResult:
    """
    Result of temporal phrase parsing.

    Attributes:
        value: ISO date string (YYYY-MM-DD) or None if unparseable
        confidence: Confidence score (0.0-1.0)
        assumption: Human-readable explanation of interpretation
    """
    value: Optional[str]
    confidence: float
    assumption: str = ""


def parse_temporal_phrase(
    phrase: str,
    client_timezone: str,
    now_iso: str
) -> TemporalResult:
    """
    Parse natural language temporal phrase to ISO date.

    Args:
        phrase: Natural language temporal phrase
        client_timezone: IANA timezone string (e.g., "America/New_York")
        now_iso: Current datetime in ISO format with timezone

    Returns:
        TemporalResult with value, confidence, and assumption

    Examples:
        >>> parse_temporal_phrase("tomorrow", "America/New_York", "2026-03-01T16:00:00-05:00")
        TemporalResult(value="2026-03-02", confidence=0.90, assumption="tomorrow")

        >>> parse_temporal_phrase("next week", "America/New_York", "2026-03-01T16:00:00-05:00")
        TemporalResult(value="2026-03-09", confidence=0.85, assumption="interpreted next week as next Monday")
    """
    if not phrase:
        return TemporalResult(value=None, confidence=0.0, assumption="empty phrase")

    # Strip common prefixes before parsing
    phrase_lower, prefix_stripped = strip_prefix(phrase)
    prefix_note = f" (prefix '{prefix_stripped}' stripped)" if prefix_stripped else ""

    # Parse now_iso to datetime
    try:
        # Handle ISO format with timezone info
        if now_iso.endswith('Z'):
            now = datetime.fromisoformat(now_iso.replace('Z', '+00:00'))
        elif '+' in now_iso or now_iso.count('-') > 2:
            # Already has timezone offset
            now = datetime.fromisoformat(now_iso)
        else:
            # No timezone - assume UTC
            now = datetime.fromisoformat(now_iso).replace(tzinfo=None)

        # Remove timezone info for date calculations (we work in local time)
        now_date = now.date()
    except (ValueError, AttributeError) as e:
        logger.error(f"[Temporal] Failed to parse now_iso: {now_iso} - {e}")
        return TemporalResult(value=None, confidence=0.0, assumption="invalid base date")

    # =========================================================================
    # TODAY / NOW / URGENT / ASAP
    # =========================================================================
    if phrase_lower in ["today", "now", "urgent", "asap"]:
        return TemporalResult(
            value=now_date.isoformat(),
            confidence=0.95,
            assumption=f"{phrase_lower}{prefix_note}"
        )

    # =========================================================================
    # TOMORROW
    # =========================================================================
    if phrase_lower == "tomorrow":
        tomorrow = now_date + timedelta(days=1)
        return TemporalResult(
            value=tomorrow.isoformat(),
            confidence=0.90,
            assumption=f"tomorrow{prefix_note}"
        )

    # =========================================================================
    # NEXT WEEK (Monday of next week per CONTEXT decision)
    # =========================================================================
    if phrase_lower in ["next week", "nextweek"]:
        # Calculate Monday of NEXT week (not just next Monday occurrence)
        # Strategy: Find this coming Monday, then add 7 days if needed
        current_weekday = now_date.weekday()  # 0=Monday, 6=Sunday

        if current_weekday == 6:
            # Today is Sunday - this coming Monday is tomorrow, next week's Monday is 8 days away
            days_to_next_week_monday = 8
        else:
            # Mon-Sat: days until this coming Monday, then +7 for next week
            days_to_this_monday = (7 - current_weekday) % 7
            if days_to_this_monday == 0:
                # Today is Monday - next week's Monday is 7 days away
                days_to_next_week_monday = 7
            else:
                # Add 7 to get to NEXT week's Monday
                days_to_next_week_monday = days_to_this_monday + 7

        next_week_monday = now_date + timedelta(days=days_to_next_week_monday)

        return TemporalResult(
            value=next_week_monday.isoformat(),
            confidence=0.85,
            assumption=f"interpreted next week as next Monday{prefix_note}"
        )

    # =========================================================================
    # NEXT <WEEKDAY> (next tuesday, next friday, etc.)
    # =========================================================================
    weekday_map = {
        "monday": 0, "mon": 0,
        "tuesday": 1, "tue": 1, "tues": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3, "thurs": 3,
        "friday": 4, "fri": 4,
        "saturday": 5, "sat": 5,
        "sunday": 6, "sun": 6,
    }

    # Try "next <weekday>" pattern
    match = re.match(r"next\s+(\w+)", phrase_lower)
    if match:
        weekday_name = match.group(1)
        if weekday_name in weekday_map:
            target_weekday = weekday_map[weekday_name]
            current_weekday = now_date.weekday()

            # Calculate days until next occurrence
            days_ahead = (target_weekday - current_weekday) % 7
            if days_ahead == 0:
                # Today is the target weekday - next occurrence is 7 days away
                days_ahead = 7

            next_occurrence = now_date + timedelta(days=days_ahead)

            return TemporalResult(
                value=next_occurrence.isoformat(),
                confidence=0.95,
                assumption=f"next {weekday_name}{prefix_note}"
            )

    # =========================================================================
    # IN <N> DAYS/WEEKS (in 3 days, in 2 weeks)
    # =========================================================================
    match = re.match(r"in\s+(\d+)\s+(day|days|week|weeks)", phrase_lower)
    if match:
        count = int(match.group(1))
        unit = match.group(2)

        if unit.startswith("day"):
            future_date = now_date + timedelta(days=count)
            return TemporalResult(
                value=future_date.isoformat(),
                confidence=0.90,
                assumption=f"in {count} {'day' if count == 1 else 'days'}{prefix_note}"
            )
        elif unit.startswith("week"):
            future_date = now_date + timedelta(weeks=count)
            return TemporalResult(
                value=future_date.isoformat(),
                confidence=0.90,
                assumption=f"in {count} {'week' if count == 1 else 'weeks'}{prefix_note}"
            )

    # =========================================================================
    # END OF MONTH
    # =========================================================================
    if phrase_lower in ["end of month", "month end", "eom"]:
        # Last day of current month
        next_month = now_date.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)

        return TemporalResult(
            value=last_day.isoformat(),
            confidence=0.88,
            assumption=f"end of current month{prefix_note}"
        )

    # =========================================================================
    # NEXT MONTH (first day of next month)
    # =========================================================================
    if phrase_lower in ["next month", "nextmonth"]:
        next_month_date = now_date + relativedelta(months=1)
        first_day = next_month_date.replace(day=1)

        return TemporalResult(
            value=first_day.isoformat(),
            confidence=0.85,
            assumption=f"first day of next month{prefix_note}"
        )

    # =========================================================================
    # END OF QUARTER (end of Q1, Q2, Q3, Q4)
    # =========================================================================
    quarter_match = re.match(r"end\s+of\s+q([1-4])", phrase_lower)
    if quarter_match:
        quarter = int(quarter_match.group(1))
        current_quarter = get_current_quarter(now_date)

        # Determine the year for this quarter
        if quarter < current_quarter:
            # Quarter already passed this year, assume next year
            target_year = now_date.year + 1
        else:
            target_year = now_date.year

        quarter_end = get_quarter_end(target_year, quarter)

        return TemporalResult(
            value=quarter_end.isoformat(),
            confidence=0.85,
            assumption=f"end of Q{quarter} {target_year}{prefix_note}"
        )

    # =========================================================================
    # UNTIL/BY YEAR (until 2027 -> Dec 31 of that year)
    # =========================================================================
    year_match = re.match(r"(?:until\s+)?(\d{4})$", phrase_lower)
    if year_match:
        year = int(year_match.group(1))
        # Validate reasonable year range (not too far past or future)
        if 2020 <= year <= 2100:
            year_end = date(year, 12, 31)

            return TemporalResult(
                value=year_end.isoformat(),
                confidence=0.85,
                assumption=f"December 31, {year}{prefix_note}"
            )

    # =========================================================================
    # CHARTER SEASON (May 1 to October 31 - returns May 1 as start)
    # =========================================================================
    if phrase_lower in ["charter season", "charterseason", "season"]:
        # Charter season is typically May-October
        # Return May 1 of current or next year depending on current date
        current_year = now_date.year

        # If we're past October, charter season refers to next year
        if now_date.month > 10:
            season_start = date(current_year + 1, 5, 1)
            season_year = current_year + 1
        else:
            season_start = date(current_year, 5, 1)
            season_year = current_year

        return TemporalResult(
            value=season_start.isoformat(),
            confidence=0.70,
            assumption=f"charter season (May 1 - Oct 31, {season_year}){prefix_note}"
        )

    # =========================================================================
    # THIS WEEK (this coming <weekday> if not passed, otherwise today)
    # =========================================================================
    this_week_match = re.match(r"this\s+(\w+)", phrase_lower)
    if this_week_match:
        weekday_name = this_week_match.group(1)
        if weekday_name in weekday_map:
            target_weekday = weekday_map[weekday_name]
            current_weekday = now_date.weekday()

            if target_weekday >= current_weekday:
                # This weekday is still coming this week
                days_ahead = target_weekday - current_weekday
            else:
                # This weekday already passed, still return it (earlier this week)
                days_ahead = target_weekday - current_weekday

            target_date = now_date + timedelta(days=days_ahead)

            return TemporalResult(
                value=target_date.isoformat(),
                confidence=0.85,
                assumption=f"this {weekday_name}{prefix_note}"
            )

    # =========================================================================
    # ALREADY ISO DATE (YYYY-MM-DD)
    # =========================================================================
    if len(phrase_lower) == 10 and phrase_lower[4] == '-' and phrase_lower[7] == '-':
        try:
            datetime.strptime(phrase_lower, "%Y-%m-%d")
            return TemporalResult(
                value=phrase_lower,
                confidence=1.0,
                assumption=f"explicit ISO date{prefix_note}"
            )
        except ValueError:
            pass

    # =========================================================================
    # UNPARSEABLE
    # =========================================================================
    logger.warning(f"[Temporal] Could not parse phrase: '{phrase}'")
    return TemporalResult(
        value=None,
        confidence=0.0,
        assumption=f"unparseable phrase: '{phrase}'"
    )


__all__ = [
    "parse_temporal_phrase",
    "TemporalResult",
    "strip_prefix",
    "get_quarter_end",
    "get_current_quarter",
]
