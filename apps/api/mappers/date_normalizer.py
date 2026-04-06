"""
Date Normalizer
===============
Converts dates from various PMS formats to ISO 8601 (YYYY-MM-DD).
Handles: DD-MMM-YYYY, DD/MM/YYYY, MM/DD/YYYY, Excel serial numbers, ISO passthrough.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("import.date_normalizer")

# Month abbreviation map (case-insensitive)
MONTH_ABBREV = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

# Excel epoch (with Lotus 1-2-3 bug adjustment)
EXCEL_EPOCH = datetime(1899, 12, 30)


def normalize_date(value: str, detected_format: Optional[str] = None) -> Optional[str]:
    """
    Convert a date string to ISO 8601 (YYYY-MM-DD).
    Returns None if the value cannot be parsed.

    Args:
        value: Raw date string from source file
        detected_format: Hint from parser ('ISO', 'DD-MMM-YYYY', 'DD/MM/YYYY', 'MM/DD/YYYY', 'ambiguous')
    """
    if not value or not value.strip():
        return None

    value = value.strip()

    # Already ISO
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value

    # ISO with time component
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}.*", value):
        return value[:10]

    # DD-MMM-YYYY (IDEA Yacht format: 15-JAN-2025)
    match = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", value)
    if match:
        day, month_str, year = match.groups()
        month = MONTH_ABBREV.get(month_str.upper())
        if month:
            try:
                dt = datetime(int(year), month, int(day))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return None

    # DD/MM/YYYY or MM/DD/YYYY
    match = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", value)
    if match:
        a, b, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if detected_format == "DD/MM/YYYY" or (detected_format is None and a > 12):
            day, month = a, b
        elif detected_format == "MM/DD/YYYY" or (detected_format is None and b > 12):
            month, day = a, b
        else:
            # Default to DD/MM/YYYY (European maritime convention)
            day, month = a, b

        try:
            dt = datetime(year, month, day)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            # Try the other interpretation
            try:
                dt = datetime(year, a, b) if day == a else datetime(year, b, a)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return None

    # Excel serial number (float or int)
    try:
        serial = float(value)
        if 1 < serial < 200000:  # reasonable range for dates
            if serial >= 60:
                serial -= 1  # Lotus 1-2-3 bug
            dt = EXCEL_EPOCH + timedelta(days=serial)
            return dt.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        pass

    return None


def normalize_dates_in_row(row: dict, date_columns: list[str], detected_format: Optional[str] = None) -> dict:
    """
    Normalize all date fields in a row dict.
    Returns a new dict with date values converted to ISO 8601.
    """
    result = dict(row)
    for col in date_columns:
        if col in result and result[col]:
            normalized = normalize_date(result[col], detected_format)
            if normalized:
                result[col] = normalized
    return result
