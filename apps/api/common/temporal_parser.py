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

Returns TemporalResult with:
- value: ISO date string (YYYY-MM-DD)
- confidence: float (0.0-1.0)
- assumption: string explaining interpretation
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import logging

logger = logging.getLogger(__name__)


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

    phrase_lower = phrase.strip().lower()

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
            assumption=phrase_lower
        )

    # =========================================================================
    # TOMORROW
    # =========================================================================
    if phrase_lower == "tomorrow":
        tomorrow = now_date + timedelta(days=1)
        return TemporalResult(
            value=tomorrow.isoformat(),
            confidence=0.90,
            assumption="tomorrow"
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
            assumption="interpreted next week as next Monday"
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
                assumption=f"next {weekday_name}"
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
                assumption=f"in {count} {'day' if count == 1 else 'days'}"
            )
        elif unit.startswith("week"):
            future_date = now_date + timedelta(weeks=count)
            return TemporalResult(
                value=future_date.isoformat(),
                confidence=0.90,
                assumption=f"in {count} {'week' if count == 1 else 'weeks'}"
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
            assumption="end of current month"
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
                assumption="explicit ISO date"
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
]
