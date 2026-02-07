#!/usr/bin/env python3
"""
Goldset Relabeling Script

Applies the "no magic booster" philosophy:
1. Vague queries (singleton keywords) → domain=None, mode=explore
2. Fix intents: create/update/sign/approve → correct intent
3. Add filter expectations for status/compliance queries
4. Compound anchors determine domain assignment

Output: tests/search/goldset_v2.jsonl
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

INPUT_PATH = Path("tests/search/goldset.jsonl")
OUTPUT_PATH = Path("tests/search/goldset_v3.jsonl")  # v3 with fixed intents and looser anchors

# =============================================================================
# SINGLETON KEYWORDS (no domain anchor alone)
# =============================================================================

SINGLETON_KEYWORDS = {
    'warning', 'warnings', 'alert', 'alerts',
    'crew', 'staff', 'team',
    'work', 'working',
    'rest', 'hrs', 'hours',  # alone without compound
    'check', 'show', 'view', 'list', 'find',
    'status', 'update', 'log',
}

# =============================================================================
# COMPOUND ANCHORS (determine domain)
# =============================================================================

COMPOUND_ANCHORS = {
    # hours_of_rest compounds - includes abbreviations (hrs, hor)
    'hours_of_rest': [
        # Core patterns
        r'\bcrew\s+rest\b',
        r'\brest\s+hours?\b',
        r'\brest\s+hrs\b',  # abbreviation
        r'\bhours?[\s-]+of[\s-]+rest\b',  # matches "hours of rest" and "hours-of-rest"
        r'\bwork\s+hours?\b',
        r'\bwork\s+hrs\b',  # abbreviation
        r'\brest\s+violations?\b',
        r'\brest\s+records?\b',
        r'\brest\s+compliance\b',
        # Monthly sign-off patterns
        r'\bmonthly\s+sign[- ]?off',
        r'\bmonthly\s+(hours?|hrs|record)',
        r'\bsign[- ]?off.*hours?\b',
        r'\bsign\s+monthly\b',
        r'\bsign\s+(my\s+)?monthly',
        # Log/update patterns with abbreviations
        r'\blog\b.*\b(hours?|hrs|rest)\b',
        r'\b(log|record|enter)\s+(my\s+)?(hours?|hrs|rest)\b',
        r'\bneed\s+to\s+log\b',
        r'\bupdate\s+(my\s+)?(hours?|hrs|rest)\b',
        # Abbreviations with context
        r'\bhor\s+\w+',  # "hor records", "hor violations"
        r'\bhor\b',  # Standalone abbreviation
        r'\bhrs\s+of\s+rest\b',
        # Acknowledge patterns
        r'\back(nowledge)?\s+(rest\s+)?violation',
    ],
    # receiving compounds
    'receiving': [
        r'\baccepted?\s+deliver',
        r'\bapproved?\s+deliver',
        r'\brejected?\s+deliver',
        r'\bdraft\s+deliver',
        r'\bpending\s+deliver',
        r'\breceiving\s+draft\b',
        r'\breceiving\s+accepted\b',
        r'\bdeliveries?\s+(this|last|today)',
        r'\bshipments?\b',
    ],
    # equipment compounds
    'equipment': [
        r'\bmain\s+engine\b',
        r'\bgenerator\s*\d*\b',
        r'\bwatermaker\b',
        r'\bradar\b',
        r'\bflybridge\b',
        r'\bhvac\b',
        r'\bpump\b',
        r'\bboiler\b',
        r'\bcompressor\b',
    ],
    # part/inventory compounds
    'part': [
        r'\b(racor|caterpillar|volvo|mtu|yanmar|northern\s+lights)\b.*\b(filter|part|element)\b',
        r'\b(filter|part|element).*\b(racor|caterpillar|volvo|mtu|yanmar)\b',
        r'\bpart\s+number\b',
        r'\bspare\s+parts?\b',
        r'\b[A-Z]{2,}-\d{3,}',  # Part number patterns
        r'\blow\s+stock\b',
        r'\breorder\b',
    ],
    # work_order compounds
    'work_order': [
        r'\bwork\s+order\b',
        r'\bwo\s*[-#]?\d*\b',
        r'\bmaintenance\s+(task|schedule|order)\b',
        r'\boverdue\s+work\b',
        r'\bopen\s+work\s+orders?\b',
    ],
    # document compounds
    'document': [
        r'\bmanual\b',
        r'\bprocedure\b',
        r'\bdocumentation\b',
        r'\bsafety\s+procedures?\b',
        r'\boperating\s+instructions?\b',
        r'\btechnical\s+doc',
    ],
    # fault compounds
    'fault': [
        r'\bopen\s+faults?\b',
        r'\bcritical\s+faults?\b',
        r'\bfault\s+(code|history|report)\b',
        r'\bequipment\s+fault\b',
        r'\breport\s+fault\b',
        r'\blog\s+fault\b',
    ],
}

# =============================================================================
# INTENT DETECTION
# =============================================================================

INTENT_PATTERNS = {
    'CREATE': [
        r'\bcreate\s+\w+',
        r'\badd\s+(new\s+)?\w+',
        # Hours of rest logging - expanded patterns
        r'\blog\b.*\b(hours?|hrs|rest)\b',  # "log my hours", "log hrs"
        r'\b(log|record|enter)\s+(my\s+)?(hours?|hrs|rest)',
        r'\bneed\s+to\s+log\b',  # "i need to log rest today"
        r'\breport\s+(a\s+)?(fault|issue)',
    ],
    'UPDATE': [
        r'\bupdate\s+(my\s+)?\w+',
        r'\bedit\s+\w+',
        r'\bmodify\s+\w+',
        r'\bchange\s+\w+',
        r'\bcorrect\s+\w+',
    ],
    'APPROVE': [
        r'\bsign[-\s]?off\b',  # "sign off", "sign-off", "signoff"
        r'\bsignoff\b',
        # Sign + monthly/hours/record patterns
        r'\bsign\b.*\b(monthly|hours?|hrs|record)\b',
        r'\bpls\s+sign\b',
        r'\bwho\s+needs?\s+to\s+sign\b',
        r'\bstart\s+(monthly\s+)?sign[-\s]?off',  # "start monthly sign-off"
        r'\bapprove\s+\w+',
        r'\baccept\s+(the\s+)?(delivery|order)',
        r'\back(nowledge)?\s+\w+',  # "acknowledge rest violation"
    ],
    'DELETE': [
        r'\bdelete\s+\w+',
        r'\bremove\s+\w+',
        r'\bcancel\s+\w+',
    ],
    'EXPORT': [
        r'\bexport\s+\w+',
        r'\bdownload\s+\w+',
        r'\bprint\s+\w+',
        r'\bgenerate\s+report',
    ],
}

# Adjective status words that mean READ + filter, not mutation
STATUS_ADJECTIVES = {
    'accepted', 'approved', 'rejected', 'draft', 'pending',
    'compliant', 'non-compliant', 'violation', 'overdue',
    'open', 'closed', 'completed', 'in progress',
}

# =============================================================================
# FILTER EXTRACTION
# =============================================================================

def extract_filters(query: str) -> Optional[Dict[str, Any]]:
    """Extract structured filters from query."""
    query_lower = query.lower()
    filters = {}

    # Status filters for receiving
    if re.search(r'\b(accepted?|approved?)\s+(deliver|receiving)', query_lower):
        filters['status'] = 'accepted'
    elif re.search(r'\bdraft\s+(deliver|receiving)', query_lower):
        filters['status'] = 'draft'
    elif re.search(r'\b(rejected?|declined?)\s+(deliver|receiving)', query_lower):
        filters['status'] = 'rejected'
    elif re.search(r'\bpending\s+(deliver|receiving)', query_lower):
        filters['status'] = 'pending'

    # Compliance filters for HoR
    if re.search(r'\bviolation', query_lower):
        filters['compliance_state'] = 'violation'
    elif re.search(r'\bnon[- ]?compliant', query_lower):
        filters['compliance_state'] = 'violation'
    elif re.search(r'\bcompliant\b', query_lower):
        filters['compliance_state'] = 'compliant'

    return filters if filters else None


# =============================================================================
# DOMAIN DETECTION (with confidence)
# =============================================================================

def detect_domain(query: str) -> Tuple[Optional[str], float]:
    """
    Detect domain using compound anchors.
    Returns (domain, confidence).
    If no compound anchor matches, returns (None, 0.0) for explore mode.
    """
    query_lower = query.lower()

    # Check each domain's compound patterns
    matches = []
    for domain, patterns in COMPOUND_ANCHORS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                matches.append((domain, pattern))
                break  # One match per domain is enough

    if not matches:
        return None, 0.0

    if len(matches) == 1:
        return matches[0][0], 0.9

    # Multiple domains matched - need disambiguation
    # Priority: work_order > receiving > hours_of_rest > equipment > part > fault > document
    priority = ['work_order', 'receiving', 'hours_of_rest', 'equipment', 'part', 'fault', 'document']
    for p in priority:
        for domain, _ in matches:
            if domain == p:
                return domain, 0.7  # Lower confidence due to ambiguity

    return matches[0][0], 0.6


def detect_intent(query: str, domain: Optional[str]) -> Tuple[str, float]:
    """
    Detect intent from query.
    Returns (intent, confidence).

    Key rule: Adjective status words (accepted, draft) → READ + filter, not APPROVE.
    """
    query_lower = query.lower()

    # Priority check: acknowledge/sign-off patterns BEFORE adjective check
    # "acknowledge rest violation" → APPROVE (not READ just because "violation" is present)
    if re.search(r'\back(nowledge)?\s+\w+', query_lower):
        return 'APPROVE', 0.9
    if re.search(r'\bsign[-\s]?off\b', query_lower):
        return 'APPROVE', 0.9
    if re.search(r'\bstart\s+(monthly\s+)?sign[-\s]?off', query_lower):
        return 'APPROVE', 0.9

    # Check for adjective-before-noun patterns (READ + filter)
    for adj in STATUS_ADJECTIVES:
        if re.search(rf'\b{adj}\s+\w+', query_lower):
            # "accepted deliveries", "draft receiving" → READ
            return 'READ', 0.9

    # Check for explicit mutation intents
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return intent, 0.85

    # Default to READ
    return 'READ', 0.8


def is_vague_query(query: str) -> bool:
    """
    Check if query is too vague to assign a domain.
    Vague = only singleton keywords, no compound anchors.
    """
    query_lower = query.lower()

    # Check if any compound anchor matches
    for domain, patterns in COMPOUND_ANCHORS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return False  # Has a compound anchor, not vague

    # Check if it's just singleton words
    words = set(re.findall(r'\b\w+\b', query_lower))
    meaningful_words = words - {'me', 'my', 'the', 'a', 'an', 'for', 'to', 'of', 'and', 'or', 'in', 'on', 'at', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'please', 'all', 'this', 'that', 'these', 'those', 'i'}

    # If most words are singleton keywords or very short, it's vague
    if len(meaningful_words) <= 2:
        return True

    return False


# =============================================================================
# MAIN RELABELING
# =============================================================================

def relabel_query(item: Dict[str, Any]) -> Dict[str, Any]:
    """Relabel a single query with correct domain, intent, filters."""
    query = item.get('query', '')

    # Detect domain with compound anchors
    domain, domain_confidence = detect_domain(query)

    # Check for vague queries - only set to explore if truly vague AND low confidence
    if is_vague_query(query) and domain_confidence < 0.4:
        domain = None
        domain_confidence = 0.0

    # Detect intent
    intent, intent_confidence = detect_intent(query, domain)

    # Extract filters
    filters = extract_filters(query)

    # Determine mode - lowered threshold from 0.6 to 0.4
    mode = 'focused' if domain and domain_confidence >= 0.4 else 'explore'

    # Build updated item
    updated = item.copy()
    updated['expected_domain'] = domain
    updated['expected_intent'] = intent
    updated['expected_mode'] = mode
    updated['domain_confidence'] = domain_confidence
    updated['intent_confidence'] = intent_confidence

    if filters:
        updated['expected_filters'] = filters

    return updated


def main():
    print(f"Loading goldset from {INPUT_PATH}")

    items = []
    with open(INPUT_PATH, 'r') as f:
        for line in f:
            items.append(json.loads(line.strip()))

    print(f"Loaded {len(items)} queries")

    # Relabel each query
    relabeled = []
    stats = {
        'domain_none': 0,
        'intent_create': 0,
        'intent_update': 0,
        'intent_approve': 0,
        'intent_read': 0,
        'has_filters': 0,
        'mode_explore': 0,
        'mode_focused': 0,
    }

    for item in items:
        updated = relabel_query(item)
        relabeled.append(updated)

        # Track stats
        if updated['expected_domain'] is None:
            stats['domain_none'] += 1
        if updated['expected_intent'] == 'CREATE':
            stats['intent_create'] += 1
        elif updated['expected_intent'] == 'UPDATE':
            stats['intent_update'] += 1
        elif updated['expected_intent'] == 'APPROVE':
            stats['intent_approve'] += 1
        else:
            stats['intent_read'] += 1
        if updated.get('expected_filters'):
            stats['has_filters'] += 1
        if updated['expected_mode'] == 'explore':
            stats['mode_explore'] += 1
        else:
            stats['mode_focused'] += 1

    # Write output
    with open(OUTPUT_PATH, 'w') as f:
        for item in relabeled:
            f.write(json.dumps(item) + '\n')

    print(f"\nWrote {len(relabeled)} queries to {OUTPUT_PATH}")
    print(f"\nStats:")
    print(f"  Domain=None (explore): {stats['domain_none']}")
    print(f"  Mode explore: {stats['mode_explore']}")
    print(f"  Mode focused: {stats['mode_focused']}")
    print(f"  Intent CREATE: {stats['intent_create']}")
    print(f"  Intent UPDATE: {stats['intent_update']}")
    print(f"  Intent APPROVE: {stats['intent_approve']}")
    print(f"  Intent READ: {stats['intent_read']}")
    print(f"  Has filters: {stats['has_filters']}")

    # Show some examples
    print("\n\nExample relabeled queries:")
    print("-" * 70)

    # Show first 5 explore mode
    explore_examples = [r for r in relabeled if r['expected_mode'] == 'explore'][:5]
    print("\nExplore mode examples:")
    for ex in explore_examples:
        print(f"  \"{ex['query'][:50]}\" → domain={ex['expected_domain']}, intent={ex['expected_intent']}")

    # Show first 5 with filters
    filter_examples = [r for r in relabeled if r.get('expected_filters')][:5]
    print("\nFilter examples:")
    for ex in filter_examples:
        print(f"  \"{ex['query'][:50]}\" → filters={ex['expected_filters']}")

    # Show first 5 non-READ intents
    mutation_examples = [r for r in relabeled if r['expected_intent'] != 'READ'][:5]
    print("\nMutation intent examples:")
    for ex in mutation_examples:
        print(f"  \"{ex['query'][:50]}\" → intent={ex['expected_intent']}")


if __name__ == '__main__':
    main()
