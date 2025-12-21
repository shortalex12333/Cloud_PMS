"""
Gap Analyzer
============

Identifies gaps between:
1. Terms found in documents vs patterns we have
2. Expected entities vs extracted entities
3. Entity types that need more coverage

This provides ACTIONABLE insights for improving extraction.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

# Import our patterns
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api"))

try:
    from regex_production_data import (
        EQUIPMENT_PATTERNS,
        DIAGNOSTIC_PATTERNS,
        get_all_manufacturers,
        get_equipment_terms,
    )
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False
    print("Warning: Pattern data not available")


@dataclass
class GapReport:
    """Report of identified gaps."""
    generated_at: str

    # Terms in documents but not in patterns
    missing_from_patterns: List[Dict]

    # Patterns that never match (potentially obsolete)
    unused_patterns: List[str]

    # Entity types with low coverage
    low_coverage_types: List[Dict]

    # Recommendations
    recommendations: List[str]


class GapAnalyzer:
    """
    Analyzes gaps between actual documents and extraction patterns.
    """

    def __init__(self, mined_terms_db: str, ground_truth_db: str):
        self.mined_db = mined_terms_db
        self.gt_db = ground_truth_db

    def get_mined_terms(self, term_type: str = 'word', min_freq: int = 3) -> Set[str]:
        """Get frequently occurring terms from mined documents."""
        conn = sqlite3.connect(self.mined_db)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT term FROM terms
            WHERE term_type = ?
            AND frequency >= ?
        ''', (term_type, min_freq))

        terms = {row[0].lower() for row in cursor.fetchall()}
        conn.close()
        return terms

    def get_pattern_terms(self) -> Set[str]:
        """Get all terms covered by our extraction patterns."""
        if not PATTERNS_AVAILABLE:
            return set()

        terms = set()

        # Get manufacturers
        terms.update(get_all_manufacturers())

        # Get equipment terms
        terms.update(get_equipment_terms())

        # Get from diagnostic patterns
        for pattern_type, patterns in DIAGNOSTIC_PATTERNS.items():
            for pattern_data in patterns:
                if isinstance(pattern_data, dict):
                    subdomain = pattern_data.get('subdomain', '').lower()
                    canonical = pattern_data.get('canonical_term', '').lower()
                    terms.add(subdomain)
                    terms.add(canonical)

        return terms

    def find_missing_patterns(self, min_freq: int = 5) -> List[Dict]:
        """
        Find terms that appear frequently in documents
        but are not covered by our patterns.

        These are candidates for new patterns.
        """
        mined = self.get_mined_terms(min_freq=min_freq)
        patterns = self.get_pattern_terms()

        missing = mined - patterns

        # Filter out common words and get frequency data
        conn = sqlite3.connect(self.mined_db)
        cursor = conn.cursor()

        missing_with_freq = []
        for term in missing:
            if len(term) < 4:
                continue

            cursor.execute('''
                SELECT frequency, doc_count, categories FROM terms
                WHERE term = ? AND term_type = 'word'
            ''', (term,))

            row = cursor.fetchone()
            if row:
                missing_with_freq.append({
                    'term': term,
                    'frequency': row[0],
                    'doc_count': row[1],
                    'categories': row[2],
                    'needs_review': True
                })

        conn.close()

        # Sort by frequency
        return sorted(missing_with_freq, key=lambda x: -x['frequency'])[:100]

    def analyze_extraction_coverage(self) -> Dict:
        """
        Analyze how well our patterns cover ground truth entities.
        """
        conn = sqlite3.connect(self.gt_db)
        cursor = conn.cursor()

        # Get all expected entity types
        cursor.execute('''
            SELECT entity_type, COUNT(*) FROM entities
            GROUP BY entity_type
        ''')

        type_counts = dict(cursor.fetchall())
        conn.close()

        # TODO: Compare against extraction results to find coverage gaps
        return {
            'entity_types': type_counts,
            'total_entities': sum(type_counts.values()),
        }

    def find_category_gaps(self) -> List[Dict]:
        """
        Find document categories that have poor extraction coverage.
        """
        conn = sqlite3.connect(self.mined_db)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT category, COUNT(*) as doc_count
            FROM documents
            GROUP BY category
        ''')

        categories = cursor.fetchall()
        conn.close()

        # TODO: Cross-reference with ground truth coverage
        return [{'category': c, 'doc_count': n} for c, n in categories]

    def generate_report(self) -> GapReport:
        """Generate comprehensive gap analysis report."""
        missing = self.find_missing_patterns()
        coverage = self.analyze_extraction_coverage()
        categories = self.find_category_gaps()

        # Generate recommendations
        recommendations = []

        if len(missing) > 20:
            recommendations.append(
                f"Add {len(missing)} frequently occurring terms to patterns"
            )

        # Identify low-coverage entity types
        low_coverage = []
        for etype, count in coverage.get('entity_types', {}).items():
            if count < 3:
                low_coverage.append({
                    'type': etype,
                    'count': count,
                    'recommendation': f"Add more ground truth examples for {etype}"
                })
                recommendations.append(
                    f"Need more ground truth for entity type: {etype}"
                )

        return GapReport(
            generated_at=datetime.now().isoformat(),
            missing_from_patterns=missing,
            unused_patterns=[],  # TODO: Track pattern usage
            low_coverage_types=low_coverage,
            recommendations=recommendations
        )

    def export_missing_patterns(self, output_path: str):
        """Export missing patterns for human review."""
        missing = self.find_missing_patterns(min_freq=3)

        export_data = {
            'generated_at': datetime.now().isoformat(),
            'instructions': '''
HUMAN REVIEW REQUIRED
=====================
These terms appear frequently in yacht documents but are NOT
covered by our extraction patterns.

For each term, decide:
1. Is this a valid maritime entity? (yes/no)
2. What entity type is it? (equipment, part, symptom, etc.)
3. What should the canonical form be?
4. What confidence weight should it have?

DO NOT automatically add these - each must be manually validated.
            ''',
            'candidate_count': len(missing),
            'candidates': missing
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"Exported {len(missing)} missing pattern candidates to {output_path}")

    def print_report(self, report: GapReport):
        """Print human-readable gap analysis."""
        print("\n" + "=" * 60)
        print("GAP ANALYSIS REPORT")
        print("=" * 60)
        print(f"Generated: {report.generated_at}")
        print()

        print("TERMS MISSING FROM PATTERNS")
        print("-" * 40)
        print(f"Found {len(report.missing_from_patterns)} terms in documents not in patterns")
        print("Top 10:")
        for item in report.missing_from_patterns[:10]:
            print(f"  '{item['term']}' - freq: {item['frequency']}, docs: {item['doc_count']}")
        print()

        print("LOW COVERAGE ENTITY TYPES")
        print("-" * 40)
        for lc in report.low_coverage_types:
            print(f"  {lc['type']}: only {lc['count']} examples")
        print()

        print("RECOMMENDATIONS")
        print("-" * 40)
        for rec in report.recommendations:
            print(f"  • {rec}")
        print("=" * 60)


if __name__ == "__main__":
    # Paths
    mined_db = str(Path(__file__).parent / "mined_terms.db")
    gt_db = str(Path(__file__).parent / "ground_truth.db")

    analyzer = GapAnalyzer(mined_db, gt_db)

    print("Generating gap analysis report...")
    report = analyzer.generate_report()

    analyzer.print_report(report)

    # Export for review
    analyzer.export_missing_patterns("/tmp/missing_patterns.json")
