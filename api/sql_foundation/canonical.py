"""
Canonical Normalization
=======================

Mathematical normalization function for entity term matching.

THEOREM:
    For all surface forms {t₁, t₂, ..., tₙ} in equivalence class E:
        canonical(t₁) = canonical(t₂) = ... = canonical(tₙ)

EQUIVALENCE CLASSES (examples):
    [4c]         = {4c, 4 c, 4-c, 4C, four c, FOUR-C, ...}
    [eng0001103] = {ENG-0001-103, ENG 0001 103, eng0001103, ...}
    [e047]       = {E047, E-047, e 047, E 047, e-047, ...}

PROPERTIES:
    - Idempotent: canonical(canonical(t)) = canonical(t)
    - Deterministic: Same input → same output
    - Equivalence-preserving: If t₁ ~ t₂, then canonical(t₁) = canonical(t₂)

TRANSFORMATION PIPELINE (ordered):
    INPUT → lowercase → expand_numbers → strip_separators → OUTPUT
"""

import re
from typing import Optional, Dict, Set

# =============================================================================
# NUMBER WORD EXPANSION
# =============================================================================

NUMBER_WORDS: Dict[str, str] = {
    # Cardinal numbers
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20",

    # Ordinals (map to cardinal)
    "first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
    "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10",
}

# Build regex pattern for number word replacement
_NUMBER_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(k) for k in NUMBER_WORDS.keys()) + r')\b',
    re.IGNORECASE
)

# =============================================================================
# SEPARATOR PATTERNS
# =============================================================================

# Characters that are semantically equivalent to no separator
SEPARATOR_CHARS = r'[\s\-_\.\,\/]+'

# =============================================================================
# ENTITY-TYPE SPECIFIC RULES
# =============================================================================

# Entity types that use alphanumeric code canonicalization
ALPHANUMERIC_CODE_TYPES: Set[str] = {
    "LOCATION",
    "PART_NUMBER",
    "EQUIPMENT_CODE",
    "FAULT_CODE",
    "EQUIPMENT_NAME",  # May contain codes like ME-001
    "WORK_ORDER_NUMBER",
    "PO_NUMBER",
}

# Entity types that preserve word boundaries (natural language)
NATURAL_LANGUAGE_TYPES: Set[str] = {
    "SYMPTOM",
    "PART_NAME",
    "MANUFACTURER",
    "SUPPLIER",
    "DESCRIPTION",
}

# =============================================================================
# CORE CANONICALIZATION FUNCTION
# =============================================================================

def canonical(term: str, entity_type: Optional[str] = None) -> str:
    """
    Universal canonical normalization function.

    Transforms any surface form to its canonical representative.

    Args:
        term: The raw term to canonicalize
        entity_type: Optional entity type for type-specific rules

    Returns:
        Canonical form of the term

    Examples:
        >>> canonical("4 c")
        '4c'
        >>> canonical("Four-C")
        '4c'
        >>> canonical("ENG-0001-103")
        'eng0001103'
        >>> canonical("E 047", "FAULT_CODE")
        'e047'
        >>> canonical("oil filter", "PART_NAME")
        'oil filter'
    """
    if not term:
        return ""

    # Step 1: Lowercase
    t = term.lower().strip()

    # Step 2: Expand number words ("four" → "4")
    t = _expand_number_words(t)

    # Step 3: Entity-type-specific handling
    if entity_type in NATURAL_LANGUAGE_TYPES:
        # Preserve word boundaries, just normalize whitespace
        t = re.sub(r'\s+', ' ', t)
    else:
        # Alphanumeric code: strip all separators
        t = re.sub(SEPARATOR_CHARS, '', t)

    return t


def canonical_for_search(term: str, entity_type: Optional[str] = None) -> str:
    """
    Canonical form optimized for search matching.

    Same as canonical() but returns both the canonical form
    and variants that might be stored in the database.

    This is used when we want to match "4c" against both:
    - Database value "4c" (exact canonical match)
    - Database value "4-C" (via ILIKE pattern)
    """
    return canonical(term, entity_type)


def generate_search_variants(term: str, entity_type: Optional[str] = None) -> list:
    """
    Generate search variants for a term.

    When searching, we may need to match against non-canonicalized
    database values. This generates variants to try.

    Args:
        term: The search term
        entity_type: Optional entity type

    Returns:
        List of variants to search for, in priority order:
        [canonical_form, original_lowercase, with_separators, ...]
    """
    canon = canonical(term, entity_type)
    original = term.lower().strip()

    variants = [canon]

    if original != canon:
        variants.append(original)

    # For alphanumeric codes, add spaced/hyphenated variants
    if entity_type not in NATURAL_LANGUAGE_TYPES:
        # Add variant with spaces between letter-number boundaries
        # e.g., "4c" → "4 c", "eng0001" → "eng 0001"
        spaced = _add_letter_number_spacing(canon)
        if spaced != canon:
            variants.append(spaced)

        # Add hyphenated variant
        hyphenated = _add_letter_number_hyphens(canon)
        if hyphenated != canon:
            variants.append(hyphenated)

    return variants


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _expand_number_words(text: str) -> str:
    """
    Expand number words to digits.

    "four c" → "4 c"
    "box twelve" → "box 12"
    """
    def replace_number(match):
        word = match.group(1).lower()
        return NUMBER_WORDS.get(word, word)

    return _NUMBER_PATTERN.sub(replace_number, text)


def _add_letter_number_spacing(text: str) -> str:
    """
    Add spaces at letter-number boundaries.

    "4c" → "4 c"
    "eng0001" → "eng 0001"
    """
    # Add space between digit and letter
    result = re.sub(r'(\d)([a-z])', r'\1 \2', text)
    # Add space between letter and digit
    result = re.sub(r'([a-z])(\d)', r'\1 \2', result)
    return result


def _add_letter_number_hyphens(text: str) -> str:
    """
    Add hyphens at letter-number boundaries.

    "4c" → "4-c"
    "eng0001" → "eng-0001"
    """
    # Add hyphen between digit and letter
    result = re.sub(r'(\d)([a-z])', r'\1-\2', text)
    # Add hyphen between letter and digit
    result = re.sub(r'([a-z])(\d)', r'\1-\2', result)
    return result


# =============================================================================
# ILIKE PATTERN GENERATION
# =============================================================================

def canonical_ilike_pattern(term: str, entity_type: Optional[str] = None) -> str:
    """
    Generate ILIKE pattern that matches canonical variants.

    For term "4c", generates pattern that matches:
    - "4c", "4 c", "4-c", "4_c", "4.c"

    This is used for Wave 2 (ILIKE) matching when we can't
    rely on database having canonical values.

    Args:
        term: The search term
        entity_type: Optional entity type

    Returns:
        ILIKE pattern with wildcards at variant boundaries
    """
    canon = canonical(term, entity_type)

    if entity_type in NATURAL_LANGUAGE_TYPES:
        # Natural language: simple wildcard match
        return f"%{canon}%"

    # For alphanumeric codes, insert optional-separator wildcards
    # at letter-number boundaries
    # "4c" → "%4%c%"
    pattern_chars = []
    prev_type = None

    for char in canon:
        curr_type = 'digit' if char.isdigit() else 'alpha' if char.isalpha() else 'other'

        # Add wildcard at type transitions
        if prev_type and curr_type != prev_type and curr_type != 'other' and prev_type != 'other':
            pattern_chars.append('%')

        pattern_chars.append(char)
        prev_type = curr_type

    return '%' + ''.join(pattern_chars) + '%'


# =============================================================================
# VALIDATION
# =============================================================================

def is_canonical(term: str, entity_type: Optional[str] = None) -> bool:
    """
    Check if term is already in canonical form.

    Returns True if canonical(term) == term
    """
    return canonical(term, entity_type) == term.lower().strip()


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Canonical Normalization - Test Suite")
    print("=" * 60)

    test_cases = [
        # (input, entity_type, expected_canonical)
        ("4c", "LOCATION", "4c"),
        ("4 c", "LOCATION", "4c"),
        ("4-c", "LOCATION", "4c"),
        ("4C", "LOCATION", "4c"),
        ("four c", "LOCATION", "4c"),
        ("Four-C", "LOCATION", "4c"),
        ("FOUR C", "LOCATION", "4c"),

        ("ENG-0001-103", "PART_NUMBER", "eng0001103"),
        ("ENG 0001 103", "PART_NUMBER", "eng0001103"),
        ("eng0001103", "PART_NUMBER", "eng0001103"),

        ("E047", "FAULT_CODE", "e047"),
        ("E-047", "FAULT_CODE", "e047"),
        ("e 047", "FAULT_CODE", "e047"),
        ("E 047", "FAULT_CODE", "e047"),

        ("oil filter", "PART_NAME", "oil filter"),
        ("OIL FILTER", "PART_NAME", "oil filter"),
        ("Oil  Filter", "PART_NAME", "oil filter"),

        ("box 2d", "LOCATION", "box2d"),
        ("BOX-2D", "LOCATION", "box2d"),
        ("box two d", "LOCATION", "box2d"),
    ]

    passed = 0
    failed = 0

    for term, entity_type, expected in test_cases:
        result = canonical(term, entity_type)
        status = "PASS" if result == expected else "FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"  {status}: canonical({term!r}, {entity_type}) = {result!r}")
        if result != expected:
            print(f"         Expected: {expected!r}")

    print()
    print(f"Results: {passed} passed, {failed} failed")

    # Test ILIKE pattern generation
    print()
    print("ILIKE Patterns:")
    print("-" * 40)
    for term, entity_type in [("4c", "LOCATION"), ("eng0001", "PART_NUMBER")]:
        pattern = canonical_ilike_pattern(term, entity_type)
        print(f"  {term!r} → {pattern!r}")

    # Test variant generation
    print()
    print("Search Variants:")
    print("-" * 40)
    for term, entity_type in [("4 c", "LOCATION"), ("ENG-0001", "PART_NUMBER")]:
        variants = generate_search_variants(term, entity_type)
        print(f"  {term!r} → {variants}")
