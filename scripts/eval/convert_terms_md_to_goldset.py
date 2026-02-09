#!/usr/bin/env python3
"""
Convert test_terms.md to evaluation goldset JSONL.

Since the MD focuses on entity extraction/actions (not search ranking positives),
this creates a "terms-only" goldset suitable for:
1. Testing that queries return results
2. Measuring consistency across roles
3. Bootstrap for manual annotation of positives

Output format (JSONL):
{
    "query": "show me hours of rest",
    "lens": "hours_of_rest",
    "role": "crew",
    "expected_object_types": ["hours_of_rest"],
    "difficulty": 1,
    "category": "View Hours of Rest Records",
    "positives": [],  // Empty for now - to be annotated
    "negatives": [],
    "limit": 20,
    "notes": "Basic query for HOR viewing"
}
"""

import json
import re
from pathlib import Path

INPUT_MD = Path("/Users/celeste7/Desktop/entity_failures/query_terms_examples/test_terms.md")
OUTPUT_JSONL = Path("/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/tests/search/goldset.jsonl")

# Lens mapping based on domain/button patterns
BUTTON_TO_LENS = {
    "get_hours_of_rest": "hours_of_rest",
    "upsert_hours_of_rest": "hours_of_rest",
    "list_crew_warnings": "hours_of_rest",
    "acknowledge_warning": "hours_of_rest",
    "dismiss_warning": "hours_of_rest",
    "get_signoff": "hours_of_rest",
    "create_signoff": "hours_of_rest",
    "get_template": "hours_of_rest",
    "create_template": "hours_of_rest",
    "get_compliance_stats": "hours_of_rest",
}

def parse_difficulty(stars):
    """Convert ★☆☆☆☆ to numeric difficulty."""
    if not stars:
        return 1
    filled = stars.count('★')
    return max(1, filled)

def normalize_role(role_str):
    """Normalize role string."""
    role_str = role_str.lower()
    if 'hod' in role_str or 'chief' in role_str:
        return 'hod'
    if 'captain' in role_str:
        return 'captain'
    if 'engineer' in role_str:
        return 'engineer'
    if 'deckhand' in role_str:
        return 'deckhand'
    if 'crew' in role_str:
        return 'crew'
    return 'crew'

def extract_queries(md_path):
    """Extract queries from MD file."""
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    queries = []
    current_category = None
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Category header
        if line.startswith('Category '):
            match = re.search(r'Category \d+: (.+?) \((\d+) tests\)', line)
            if match:
                current_category = match.group(1)

        # Query pattern: number. "query text"
        query_match = re.match(r'^\d+\.\s+"(.+)"', line)
        if query_match:
            query_text = query_match.group(1)

            # Extract metadata from next few lines
            entity = None
            button = None
            role = 'crew'
            difficulty = 1
            notes = []

            for j in range(i+1, min(i+10, len(lines))):
                meta_line = lines[j].strip()
                if not meta_line or meta_line.startswith(('---', 'Category', r'\d+\.')):
                    break

                if '- Entity:' in meta_line:
                    entity = meta_line.split('- Entity:')[1].strip()
                    notes.append(f"Entity: {entity}")
                elif '- Button:' in meta_line:
                    button = meta_line.split('- Button:')[1].strip()
                elif '- Role:' in meta_line:
                    role = normalize_role(meta_line.split('- Role:')[1].strip())
                elif '- Difficulty:' in meta_line:
                    stars = meta_line.split('- Difficulty:')[1].strip()
                    difficulty = parse_difficulty(stars)

            # Determine lens from button
            lens = BUTTON_TO_LENS.get(button, 'hours_of_rest')

            # Expected object types
            expected_types = []
            if lens == 'hours_of_rest':
                expected_types = ['hours_of_rest']

            queries.append({
                'query': query_text,
                'lens': lens,
                'role': role,
                'expected_object_types': expected_types,
                'difficulty': difficulty,
                'category': current_category or 'Unknown',
                'button': button,
                'positives': [],  # To be annotated
                'negatives': [],
                'limit': 20,
                'notes': ' | '.join(notes) if notes else None
            })

        i += 1

    return queries

def main():
    print(f"Converting {INPUT_MD}")
    print("=" * 70)

    queries = extract_queries(INPUT_MD)

    # Stats
    categories = {}
    roles = {}
    for q in queries:
        cat = q['category']
        categories[cat] = categories.get(cat, 0) + 1
        roles[q['role']] = roles.get(q['role'], 0) + 1

    print(f"\nExtracted {len(queries)} queries")
    print(f"\nCategories:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    print(f"\nRoles:")
    for role, count in sorted(roles.items()):
        print(f"  {role}: {count}")

    # Write JSONL
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, 'w') as f:
        for q in queries:
            f.write(json.dumps(q) + '\n')

    print(f"\n✓ Wrote {OUTPUT_JSONL}")
    print(f"  Format: JSONL with {len(queries)} records")
    print(f"  Note: positives[] are empty - bootstrap with manual annotation")

if __name__ == '__main__':
    main()
