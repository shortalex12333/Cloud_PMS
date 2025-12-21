"""
Extraction Validator
====================

Tests entity extraction against ground truth to compute:
- Precision: % of extracted entities that are correct
- Recall: % of expected entities that were extracted
- F1 Score: Harmonic mean of precision and recall

Also identifies:
- False Positives: Entities extracted that shouldn't be
- False Negatives: Entities that should be extracted but weren't
- Type Mismatches: Correct text but wrong entity type

This is the core quality assurance tool.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict
import sys

# Import ground truth manager
from ground_truth import GroundTruthManager, GroundTruthQuery, GroundTruthEntity

# Import extraction module
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api"))
try:
    from module_b_entity_extractor import MaritimeEntityExtractor, EntityDetection
    EXTRACTOR_AVAILABLE = True
except ImportError:
    EXTRACTOR_AVAILABLE = False
    print("Warning: Cannot import MaritimeEntityExtractor")


@dataclass
class EntityMatch:
    """Result of matching an extracted entity against ground truth."""
    extracted: Optional[Dict]  # The extracted entity (None if false negative)
    expected: Optional[GroundTruthEntity]  # The expected entity (None if false positive)
    match_type: str  # 'exact', 'partial', 'type_mismatch', 'false_positive', 'false_negative'
    overlap_score: float  # 0.0-1.0 text overlap
    notes: str


@dataclass
class QueryResult:
    """Result of validating extraction for a single query."""
    query_id: str
    query_text: str
    expected_count: int
    extracted_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    type_mismatches: int
    precision: float
    recall: float
    f1: float
    matches: List[EntityMatch]


@dataclass
class ValidationReport:
    """Full validation report across all queries."""
    run_id: str
    run_date: str
    total_queries: int
    total_expected: int
    total_extracted: int
    total_true_positives: int
    total_false_positives: int
    total_false_negatives: int
    total_type_mismatches: int

    # Overall metrics
    overall_precision: float
    overall_recall: float
    overall_f1: float

    # By entity type
    metrics_by_type: Dict[str, Dict]

    # By category
    metrics_by_category: Dict[str, Dict]

    # Detailed results
    query_results: List[QueryResult]

    # Actionable insights
    common_false_positives: List[Dict]
    common_false_negatives: List[Dict]
    pattern_gaps: List[str]


class ExtractionValidator:
    """
    Validates entity extraction against ground truth.

    This is THE critical testing component.
    """

    def __init__(self, ground_truth_db: Optional[str] = None):
        self.gt_manager = GroundTruthManager(ground_truth_db)

        if EXTRACTOR_AVAILABLE:
            self.extractor = MaritimeEntityExtractor()
        else:
            self.extractor = None

    def _calculate_overlap(self, span1: Tuple[int, int], span2: Tuple[int, int]) -> float:
        """Calculate overlap ratio between two spans."""
        start1, end1 = span1
        start2, end2 = span2

        # Calculate intersection
        intersection_start = max(start1, start2)
        intersection_end = min(end1, end2)
        intersection = max(0, intersection_end - intersection_start)

        # Calculate union
        union = (end1 - start1) + (end2 - start2) - intersection

        if union == 0:
            return 0.0

        return intersection / union

    def _normalize_type(self, entity_type: str) -> str:
        """Normalize entity type for comparison."""
        type_mapping = {
            'equipment': 'equipment',
            'system': 'system',
            'part': 'part',
            'brand': 'brand',
            'model': 'model',
            'symptom': 'symptom',
            'fault_code': 'fault_code',
            'measurement': 'measurement',
            'measurement_term': 'measurement',
            'action': 'action',
            'person': 'person',
            'location': 'location',
            'observation': 'observation',
            'diagnostic': 'diagnostic',
        }
        return type_mapping.get(entity_type.lower(), entity_type.lower())

    def _match_entities(
        self,
        extracted: List[Dict],
        expected: List[GroundTruthEntity],
        query_text: str
    ) -> Tuple[List[EntityMatch], int, int, int, int]:
        """
        Match extracted entities against expected entities.

        Returns:
            - List of EntityMatch objects
            - true_positives count
            - false_positives count
            - false_negatives count
            - type_mismatches count
        """
        matches = []
        matched_expected = set()
        matched_extracted = set()

        true_positives = 0
        type_mismatches = 0

        # First pass: find exact and partial matches
        for i, ext in enumerate(extracted):
            ext_span = tuple(ext.get('span', [0, 0]))
            ext_type = self._normalize_type(ext.get('type', ''))
            ext_text = ext.get('value', '')

            best_match = None
            best_score = 0.0

            for j, exp in enumerate(expected):
                if j in matched_expected:
                    continue

                exp_span = (exp.start, exp.end)
                exp_type = self._normalize_type(exp.entity_type)
                types_match = ext_type == exp_type

                overlap = self._calculate_overlap(ext_span, exp_span)

                # Also check text similarity for fuzzy matching
                text_match = 1.0 if ext_text.lower() == exp.text.lower() else 0.0
                if exp.text.lower() in ext_text.lower() or ext_text.lower() in exp.text.lower():
                    text_match = 0.8

                score = max(overlap, text_match)

                # Prefer matches where types align (add small bonus for type match)
                # This breaks ties when multiple expected entities have same text score
                score_with_type_bonus = score + (0.01 if types_match else 0.0)

                if score_with_type_bonus > best_score:
                    best_score = score_with_type_bonus
                    best_match = (j, exp, types_match, score)  # Store original score too

            if best_match and best_score >= 0.5:  # Threshold for match
                j, exp, type_match, original_score = best_match
                matched_expected.add(j)
                matched_extracted.add(i)

                if type_match:
                    match_type = 'exact' if original_score >= 0.9 else 'partial'
                    true_positives += 1
                else:
                    match_type = 'type_mismatch'
                    type_mismatches += 1

                matches.append(EntityMatch(
                    extracted=ext,
                    expected=exp,
                    match_type=match_type,
                    overlap_score=original_score,
                    notes=f"Extracted type: {ext.get('type')}, Expected type: {exp.entity_type}"
                ))

        # Second pass: identify false positives (extracted but not matched)
        for i, ext in enumerate(extracted):
            if i not in matched_extracted:
                matches.append(EntityMatch(
                    extracted=ext,
                    expected=None,
                    match_type='false_positive',
                    overlap_score=0.0,
                    notes=f"No matching expected entity for: {ext.get('value')}"
                ))

        # Third pass: identify false negatives (expected but not extracted)
        for j, exp in enumerate(expected):
            if j not in matched_expected:
                matches.append(EntityMatch(
                    extracted=None,
                    expected=exp,
                    match_type='false_negative',
                    overlap_score=0.0,
                    notes=f"Expected entity not extracted: {exp.text} ({exp.entity_type})"
                ))

        false_positives = len(extracted) - len(matched_extracted)
        false_negatives = len(expected) - len(matched_expected)

        return matches, true_positives, false_positives, false_negatives, type_mismatches

    def validate_query(self, gt_query: GroundTruthQuery) -> QueryResult:
        """Validate extraction for a single ground truth query."""
        if not self.extractor:
            raise RuntimeError("Extractor not available")

        # Extract entities
        extracted_entities = self.extractor.extract_entities(gt_query.query_text)
        extracted_dicts = [e.to_dict() for e in extracted_entities]

        # Match against expected
        matches, tp, fp, fn, tm = self._match_entities(
            extracted_dicts,
            gt_query.expected_entities,
            gt_query.query_text
        )

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return QueryResult(
            query_id=gt_query.query_id,
            query_text=gt_query.query_text,
            expected_count=len(gt_query.expected_entities),
            extracted_count=len(extracted_entities),
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            type_mismatches=tm,
            precision=precision,
            recall=recall,
            f1=f1,
            matches=matches
        )

    def validate_all(self, category: Optional[str] = None) -> ValidationReport:
        """Run validation against all ground truth queries."""
        gt_queries = self.gt_manager.get_all_ground_truth(category)

        if not gt_queries:
            raise ValueError("No ground truth queries found")

        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        query_results = []

        # Aggregate metrics
        total_tp = 0
        total_fp = 0
        total_fn = 0
        total_tm = 0
        total_expected = 0
        total_extracted = 0

        # By type and category
        by_type = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0})
        by_category = defaultdict(lambda: {'tp': 0, 'fp': 0, 'fn': 0})

        # Track common issues
        false_positives_counter = defaultdict(int)
        false_negatives_counter = defaultdict(int)

        for gt_query in gt_queries:
            try:
                result = self.validate_query(gt_query)
                query_results.append(result)

                total_tp += result.true_positives
                total_fp += result.false_positives
                total_fn += result.false_negatives
                total_tm += result.type_mismatches
                total_expected += result.expected_count
                total_extracted += result.extracted_count

                # Track by category
                by_category[gt_query.category]['tp'] += result.true_positives
                by_category[gt_query.category]['fp'] += result.false_positives
                by_category[gt_query.category]['fn'] += result.false_negatives

                # Track common issues
                for match in result.matches:
                    if match.match_type == 'false_positive' and match.extracted:
                        key = f"{match.extracted.get('value')}|{match.extracted.get('type')}"
                        false_positives_counter[key] += 1
                    elif match.match_type == 'false_negative' and match.expected:
                        key = f"{match.expected.text}|{match.expected.entity_type}"
                        false_negatives_counter[key] += 1

                    # Track by type
                    if match.expected:
                        t = self._normalize_type(match.expected.entity_type)
                        if match.match_type in ['exact', 'partial']:
                            by_type[t]['tp'] += 1
                        elif match.match_type == 'false_negative':
                            by_type[t]['fn'] += 1

            except Exception as e:
                print(f"Error validating {gt_query.query_id}: {e}")

        # Calculate overall metrics
        overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0

        # Calculate per-type metrics
        metrics_by_type = {}
        for t, counts in by_type.items():
            tp, fp, fn = counts['tp'], counts['fp'], counts['fn']
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
            metrics_by_type[t] = {'precision': p, 'recall': r, 'f1': f, **counts}

        # Calculate per-category metrics
        metrics_by_category = {}
        for cat, counts in by_category.items():
            tp, fp, fn = counts['tp'], counts['fp'], counts['fn']
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
            metrics_by_category[cat] = {'precision': p, 'recall': r, 'f1': f, **counts}

        # Top false positives
        common_fps = [
            {'pattern': k.split('|')[0], 'type': k.split('|')[1], 'count': v}
            for k, v in sorted(false_positives_counter.items(), key=lambda x: -x[1])[:10]
        ]

        # Top false negatives
        common_fns = [
            {'pattern': k.split('|')[0], 'type': k.split('|')[1], 'count': v}
            for k, v in sorted(false_negatives_counter.items(), key=lambda x: -x[1])[:10]
        ]

        # Identify pattern gaps
        pattern_gaps = []
        for fn in common_fns:
            pattern_gaps.append(f"Missing pattern for: {fn['pattern']} (type: {fn['type']}, missed {fn['count']} times)")

        return ValidationReport(
            run_id=run_id,
            run_date=datetime.now().isoformat(),
            total_queries=len(query_results),
            total_expected=total_expected,
            total_extracted=total_extracted,
            total_true_positives=total_tp,
            total_false_positives=total_fp,
            total_false_negatives=total_fn,
            total_type_mismatches=total_tm,
            overall_precision=overall_precision,
            overall_recall=overall_recall,
            overall_f1=overall_f1,
            metrics_by_type=metrics_by_type,
            metrics_by_category=metrics_by_category,
            query_results=query_results,
            common_false_positives=common_fps,
            common_false_negatives=common_fns,
            pattern_gaps=pattern_gaps
        )

    def print_report(self, report: ValidationReport):
        """Print a human-readable validation report."""
        print("\n" + "=" * 70)
        print("ENTITY EXTRACTION VALIDATION REPORT")
        print("=" * 70)
        print(f"Run ID: {report.run_id}")
        print(f"Date: {report.run_date}")
        print(f"Queries tested: {report.total_queries}")
        print()

        print("OVERALL METRICS")
        print("-" * 40)
        print(f"  Precision: {report.overall_precision:.1%}")
        print(f"  Recall:    {report.overall_recall:.1%}")
        print(f"  F1 Score:  {report.overall_f1:.1%}")
        print()
        print(f"  True Positives:   {report.total_true_positives}")
        print(f"  False Positives:  {report.total_false_positives}")
        print(f"  False Negatives:  {report.total_false_negatives}")
        print(f"  Type Mismatches:  {report.total_type_mismatches}")
        print()

        print("METRICS BY ENTITY TYPE")
        print("-" * 40)
        for t, m in sorted(report.metrics_by_type.items()):
            print(f"  {t:20} P:{m['precision']:.0%} R:{m['recall']:.0%} F1:{m['f1']:.0%}")
        print()

        print("METRICS BY CATEGORY")
        print("-" * 40)
        for cat, m in sorted(report.metrics_by_category.items()):
            print(f"  {cat:20} P:{m['precision']:.0%} R:{m['recall']:.0%} F1:{m['f1']:.0%}")
        print()

        if report.common_false_positives:
            print("TOP FALSE POSITIVES (over-extraction)")
            print("-" * 40)
            for fp in report.common_false_positives[:5]:
                print(f"  '{fp['pattern']}' as {fp['type']} ({fp['count']}x)")
            print()

        if report.common_false_negatives:
            print("TOP FALSE NEGATIVES (missed entities)")
            print("-" * 40)
            for fn in report.common_false_negatives[:5]:
                print(f"  '{fn['pattern']}' ({fn['type']}) - missed {fn['count']}x")
            print()

        if report.pattern_gaps:
            print("PATTERN GAPS (action required)")
            print("-" * 40)
            for gap in report.pattern_gaps[:5]:
                print(f"  - {gap}")
        print()

        # Quality gate
        print("QUALITY GATE")
        print("-" * 40)
        if report.overall_f1 >= 0.85:
            print("  ✅ PASSED - F1 score >= 85%")
        elif report.overall_f1 >= 0.70:
            print("  ⚠️  WARNING - F1 score between 70-85%")
        else:
            print("  ❌ FAILED - F1 score < 70%")
        print("=" * 70)

    def export_report(self, report: ValidationReport, output_path: str):
        """Export validation report to JSON."""
        # Convert dataclasses to dicts
        report_dict = {
            'run_id': report.run_id,
            'run_date': report.run_date,
            'total_queries': report.total_queries,
            'total_expected': report.total_expected,
            'total_extracted': report.total_extracted,
            'total_true_positives': report.total_true_positives,
            'total_false_positives': report.total_false_positives,
            'total_false_negatives': report.total_false_negatives,
            'total_type_mismatches': report.total_type_mismatches,
            'overall_precision': report.overall_precision,
            'overall_recall': report.overall_recall,
            'overall_f1': report.overall_f1,
            'metrics_by_type': report.metrics_by_type,
            'metrics_by_category': report.metrics_by_category,
            'common_false_positives': report.common_false_positives,
            'common_false_negatives': report.common_false_negatives,
            'pattern_gaps': report.pattern_gaps,
            'query_results': [
                {
                    'query_id': r.query_id,
                    'query_text': r.query_text,
                    'precision': r.precision,
                    'recall': r.recall,
                    'f1': r.f1,
                    'expected_count': r.expected_count,
                    'extracted_count': r.extracted_count,
                    'true_positives': r.true_positives,
                    'false_positives': r.false_positives,
                    'false_negatives': r.false_negatives,
                } for r in report.query_results
            ]
        }

        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)

        print(f"Report exported to {output_path}")


# Success thresholds for CI/CD
QUALITY_THRESHOLDS = {
    'minimum_f1': 0.70,         # Minimum F1 to pass
    'target_f1': 0.85,          # Target F1 for production
    'minimum_precision': 0.75,  # Minimum precision (avoid false positives)
    'minimum_recall': 0.65,     # Minimum recall (catch most entities)
    'max_false_positive_rate': 0.30,  # Max 30% false positives
}


def run_quality_gate(report: ValidationReport) -> Tuple[bool, List[str]]:
    """
    Run quality gate checks.

    Returns:
        - passed: True if all checks pass
        - issues: List of issues found
    """
    issues = []
    passed = True

    if report.overall_f1 < QUALITY_THRESHOLDS['minimum_f1']:
        issues.append(f"F1 score {report.overall_f1:.1%} below minimum {QUALITY_THRESHOLDS['minimum_f1']:.0%}")
        passed = False

    if report.overall_precision < QUALITY_THRESHOLDS['minimum_precision']:
        issues.append(f"Precision {report.overall_precision:.1%} below minimum {QUALITY_THRESHOLDS['minimum_precision']:.0%}")
        passed = False

    if report.overall_recall < QUALITY_THRESHOLDS['minimum_recall']:
        issues.append(f"Recall {report.overall_recall:.1%} below minimum {QUALITY_THRESHOLDS['minimum_recall']:.0%}")
        passed = False

    fp_rate = report.total_false_positives / (report.total_extracted or 1)
    if fp_rate > QUALITY_THRESHOLDS['max_false_positive_rate']:
        issues.append(f"False positive rate {fp_rate:.1%} exceeds maximum {QUALITY_THRESHOLDS['max_false_positive_rate']:.0%}")
        passed = False

    return passed, issues


if __name__ == "__main__":
    print("Initializing extraction validator...")

    validator = ExtractionValidator()

    print("Running validation against ground truth...")
    report = validator.validate_all()

    validator.print_report(report)

    # Run quality gate
    passed, issues = run_quality_gate(report)
    if passed:
        print("\n✅ All quality checks passed!")
        exit(0)
    else:
        print("\n❌ Quality gate failed:")
        for issue in issues:
            print(f"  - {issue}")
        exit(1)
