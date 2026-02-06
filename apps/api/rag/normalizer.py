"""
RAG Input Normalizer (Fix 7)
============================

Normalizes chaotic user input before domain/intent detection and retrieval.

Handles:
- Separators: rest_hours|today → rest hours today
- Abbreviations: hrs → hours, w/o → work order
- Unicode normalization
- Collapse whitespace
- Preserve important short tokens
"""

import re
import unicodedata
from typing import Tuple, Optional
from datetime import datetime, timedelta


# =============================================================================
# SYNONYM MAP
# =============================================================================

SYNONYMS = {
    # Hours of rest
    'hrs': 'hours',
    'hr': 'hour',
    'hor': 'hours of rest',
    'rest hrs': 'rest hours',
    'rest-hrs': 'rest hours',
    'rest_hrs': 'rest hours',
    'rest_hours': 'rest hours',
    'rest-hours': 'rest hours',
    'restrecords': 'rest records',
    'rest-records': 'rest records',
    'rest_records': 'rest records',

    # Work orders
    'w/o': 'work order',
    'w.o.': 'work order',
    'wo': 'work order',
    'workorder': 'work order',
    'work-order': 'work order',
    'work_order': 'work order',

    # Parts/inventory
    'inv': 'inventory',
    'invntry': 'inventory',
    'prt': 'part',
    'prts': 'parts',
    'stok': 'stock',
    'stck': 'stock',
    'lvl': 'level',
    'lvls': 'levels',

    # Equipment
    'equip': 'equipment',
    'eqpt': 'equipment',

    # Common typos - crew/names
    'dckhand': 'deckhand',
    'deckand': 'deckhand',
    'enginer': 'engineer',
    'enginr': 'engineer',
    'captian': 'captain',
    'captin': 'captain',
    'stewrd': 'steward',

    # Common typos - parts
    'trbochrgr': 'turbocharger',
    'turbocharger': 'turbocharger',
    'turbochrgr': 'turbocharger',
    'gaskt': 'gasket',
    'filtr': 'filter',
    'filtrs': 'filters',
    'elemnt': 'element',
    'grundfoss': 'grundfos',  # Common misspelling
    'caterpiller': 'caterpillar',
    'caterpillar': 'caterpillar',
    'volv': 'volvo',

    # Common typos - general
    'ours': 'hours',  # "my ours" → "my hours"
    'recordz': 'records',
    'restord': 'rest record',
    'complience': 'compliance',
    'compliace': 'compliance',
    'violaton': 'violation',
    'violatons': 'violations',
    'lst': 'last',

    # Actions
    'veiw': 'view',
    'veiew': 'view',
    'shwo': 'show',
    'updae': 'update',
    'updat': 'update',
    'crete': 'create',
    'creat': 'create',
    'delet': 'delete',
    'remov': 'remove',
}

# =============================================================================
# TIME EXPRESSIONS
# =============================================================================

TIME_EXPRESSIONS = {
    'today': lambda: (datetime.now().date(), datetime.now().date()),
    'yesterday': lambda: (datetime.now().date() - timedelta(days=1), datetime.now().date() - timedelta(days=1)),
    'this week': lambda: (datetime.now().date() - timedelta(days=datetime.now().weekday()), datetime.now().date()),
    'last week': lambda: (datetime.now().date() - timedelta(days=datetime.now().weekday() + 7),
                          datetime.now().date() - timedelta(days=datetime.now().weekday() + 1)),
    'this month': lambda: (datetime.now().date().replace(day=1), datetime.now().date()),
    'last month': lambda: ((datetime.now().date().replace(day=1) - timedelta(days=1)).replace(day=1),
                           datetime.now().date().replace(day=1) - timedelta(days=1)),
    'last 7 days': lambda: (datetime.now().date() - timedelta(days=7), datetime.now().date()),
    'last 30 days': lambda: (datetime.now().date() - timedelta(days=30), datetime.now().date()),
    'last 90 days': lambda: (datetime.now().date() - timedelta(days=90), datetime.now().date()),
}

# Month names for parsing "January", "February 2024", etc.
MONTHS = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12,
}


# =============================================================================
# NORMALIZATION FUNCTIONS
# =============================================================================

def normalize_unicode(text: str) -> str:
    """Normalize unicode characters."""
    # NFKC normalization - canonical decomposition, compatibility decomposition
    return unicodedata.normalize('NFKC', text)


def replace_separators(text: str) -> str:
    """Replace separators with spaces."""
    # Replace _/-/| with space
    text = re.sub(r'[_\-|]', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def expand_synonyms(text: str) -> str:
    """Expand abbreviations and fix typos."""
    text_lower = text.lower()

    # Sort by length descending to match longer phrases first
    for abbrev, expansion in sorted(SYNONYMS.items(), key=lambda x: -len(x[0])):
        # Word boundary matching
        pattern = r'\b' + re.escape(abbrev) + r'\b'
        text_lower = re.sub(pattern, expansion, text_lower, flags=re.IGNORECASE)

    return text_lower


def extract_time_window(text: str) -> Tuple[str, Optional[Tuple[datetime, datetime]]]:
    """
    Extract time window from query and return cleaned query + window.

    Returns:
        (cleaned_query, (from_date, to_date)) or (query, None)
    """
    text_lower = text.lower()

    # Check predefined expressions
    for expr, date_fn in TIME_EXPRESSIONS.items():
        if expr in text_lower:
            from_date, to_date = date_fn()
            # Remove the time expression from query
            cleaned = re.sub(re.escape(expr), '', text_lower, flags=re.IGNORECASE).strip()
            return cleaned, (from_date, to_date)

    # Check for month names (e.g., "January", "February 2024")
    for month_name, month_num in MONTHS.items():
        pattern = rf'\b{month_name}(?:\s+(\d{{4}}))?\b'
        match = re.search(pattern, text_lower)
        if match:
            year = int(match.group(1)) if match.group(1) else datetime.now().year
            from_date = datetime(year, month_num, 1).date()
            # Last day of month
            if month_num == 12:
                to_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                to_date = datetime(year, month_num + 1, 1).date() - timedelta(days=1)

            cleaned = re.sub(pattern, '', text_lower).strip()
            return cleaned, (from_date, to_date)

    return text, None


def normalize_query(query: str) -> Tuple[str, Optional[Tuple[datetime, datetime]]]:
    """
    Full normalization pipeline.

    Returns:
        (normalized_query, time_window)
    """
    # Step 1: Unicode normalization
    query = normalize_unicode(query)

    # Step 2: Replace separators
    query = replace_separators(query)

    # Step 3: Extract time window (before synonym expansion)
    query, time_window = extract_time_window(query)

    # Step 4: Expand synonyms
    query = expand_synonyms(query)

    # Step 5: Final cleanup
    query = re.sub(r'\s+', ' ', query).strip()

    return query, time_window


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    test_queries = [
        "rest_hours|today",
        "show rest hrs",
        "hrs for yesterday",
        "hours-of-rest for engine crew",
        "rest recordz",
        "who didnt log hours today",
        "update_rest_hours",
        "add my ours",
        "w/o for generator",
        "last month's rest records",
        "hours of rest this week",
        "January compliance report",
    ]

    print("=" * 60)
    print(" Normalizer Tests")
    print("=" * 60)

    for query in test_queries:
        normalized, time_window = normalize_query(query)
        print(f"\nInput:  \"{query}\"")
        print(f"Output: \"{normalized}\"")
        if time_window:
            print(f"Time:   {time_window[0]} to {time_window[1]}")
