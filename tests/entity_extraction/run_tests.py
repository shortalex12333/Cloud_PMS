#!/usr/bin/env python3
"""
Entity Extraction Test Runner
=============================

Main entry point for running entity extraction tests.

Usage:
    # Initialize ground truth (first time only)
    python run_tests.py --init

    # Run full validation
    python run_tests.py --validate

    # Mine documents for new patterns
    python run_tests.py --mine --limit 100

    # Analyze gaps
    python run_tests.py --gaps

    # Full test suite (mine + validate + gaps)
    python run_tests.py --full

    # CI mode (exit with error code if quality gate fails)
    python run_tests.py --ci

Test Sequence:
1. Mine documents → Extract terms from yacht documents
2. Initialize GT → Create ground truth test cases
3. Validate → Run extraction and compare to ground truth
4. Gap Analysis → Identify missing patterns
5. Quality Gate → Pass/fail based on metrics
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "api"))

from document_miner import DocumentMiner
from ground_truth import GroundTruthManager, create_initial_ground_truth
from extraction_validator import ExtractionValidator, run_quality_gate, QUALITY_THRESHOLDS
from gap_analyzer import GapAnalyzer


# Configuration
ROOT_DIR = "/Users/celeste7/Documents/yacht-nas/ROOT"
TESTS_DIR = Path(__file__).parent
MINED_DB = str(TESTS_DIR / "mined_terms.db")
GT_DB = str(TESTS_DIR / "ground_truth.db")
REPORTS_DIR = TESTS_DIR / "reports"


def ensure_reports_dir():
    """Ensure reports directory exists."""
    REPORTS_DIR.mkdir(exist_ok=True)


def cmd_init(args):
    """Initialize ground truth database with initial test cases."""
    print("=" * 60)
    print("INITIALIZING GROUND TRUTH DATABASE")
    print("=" * 60)

    manager = GroundTruthManager(GT_DB)

    print("\nCreating initial ground truth test cases...")
    initial_gt = create_initial_ground_truth()

    added = 0
    for gt in initial_gt:
        if manager.add_ground_truth(gt):
            added += 1

    print(f"\nAdded {added} ground truth queries")

    stats = manager.get_statistics()
    print("\nGround Truth Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Export for backup
    ensure_reports_dir()
    manager.export_to_json(str(REPORTS_DIR / "ground_truth_backup.json"))


def cmd_mine(args):
    """Mine documents for entity patterns."""
    print("=" * 60)
    print("DOCUMENT TERM MINING")
    print("=" * 60)

    if not Path(ROOT_DIR).exists():
        print(f"Error: Document root not found: {ROOT_DIR}")
        return False

    miner = DocumentMiner(ROOT_DIR, MINED_DB)

    limit = args.limit if hasattr(args, 'limit') and args.limit else None
    print(f"\nMining documents{f' (limit: {limit})' if limit else ''}...")

    stats = miner.mine_all_documents(limit=limit)

    print(f"\nMining Statistics:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Processed: {stats['processed']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Total words: {stats['total_words']}")
    print(f"  Unique terms: {stats['unique_terms']}")

    print("\nTop 20 terms by frequency:")
    for term, freq in miner.get_top_terms(limit=20):
        print(f"  {term}: {freq}")

    # Export candidates for review
    ensure_reports_dir()
    miner.export_for_review(str(REPORTS_DIR / "entity_candidates.json"))
    print(f"\nExported candidates to {REPORTS_DIR / 'entity_candidates.json'}")

    return True


def cmd_validate(args):
    """Run extraction validation against ground truth."""
    print("=" * 60)
    print("EXTRACTION VALIDATION")
    print("=" * 60)

    # Check prerequisites
    if not Path(GT_DB).exists():
        print("Error: Ground truth database not found. Run --init first.")
        return False, None

    validator = ExtractionValidator(GT_DB)

    print("\nRunning validation against ground truth...")
    try:
        report = validator.validate_all()
    except ValueError as e:
        print(f"Error: {e}")
        return False, None

    validator.print_report(report)

    # Export report
    ensure_reports_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"validation_report_{timestamp}.json"
    validator.export_report(report, str(report_path))

    # Run quality gate
    passed, issues = run_quality_gate(report)

    return passed, report


def cmd_gaps(args):
    """Run gap analysis."""
    print("=" * 60)
    print("GAP ANALYSIS")
    print("=" * 60)

    # Check prerequisites
    if not Path(MINED_DB).exists():
        print("Warning: Mined terms database not found. Run --mine first.")

    if not Path(GT_DB).exists():
        print("Warning: Ground truth database not found. Run --init first.")

    analyzer = GapAnalyzer(MINED_DB, GT_DB)

    print("\nAnalyzing gaps between documents and patterns...")
    report = analyzer.generate_report()

    analyzer.print_report(report)

    # Export missing patterns for review
    ensure_reports_dir()
    analyzer.export_missing_patterns(str(REPORTS_DIR / "missing_patterns.json"))


def cmd_full(args):
    """Run full test suite."""
    print("=" * 60)
    print("FULL ENTITY EXTRACTION TEST SUITE")
    print("=" * 60)
    print()

    results = {
        'init': True,
        'mine': True,
        'validate': False,
        'gaps': True,
    }

    # Step 1: Initialize if needed
    if not Path(GT_DB).exists():
        print("Step 1: Initializing ground truth...")
        cmd_init(args)
    else:
        print("Step 1: Ground truth already initialized ✓")

    # Step 2: Mine documents (limited for speed)
    print("\nStep 2: Mining documents...")
    args.limit = 100  # Limit for testing
    results['mine'] = cmd_mine(args)

    # Step 3: Validate
    print("\nStep 3: Running validation...")
    passed, report = cmd_validate(args)
    results['validate'] = passed

    # Step 4: Gap analysis
    print("\nStep 4: Analyzing gaps...")
    cmd_gaps(args)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUITE SUMMARY")
    print("=" * 60)

    for step, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {step}: {status}")

    if all(results.values()):
        print("\n✅ ALL TESTS PASSED")
        return True
    else:
        print("\n❌ SOME TESTS FAILED")
        return False


def cmd_ci(args):
    """CI mode - exit with error code if tests fail."""
    print("Running in CI mode...")

    # Run validation only (assumes ground truth exists)
    passed, report = cmd_validate(args)

    if passed:
        print("\n✅ CI: Quality gate passed")
        sys.exit(0)
    else:
        print("\n❌ CI: Quality gate failed")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Entity Extraction Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py --init          Initialize ground truth database
  python run_tests.py --mine          Mine documents for terms
  python run_tests.py --validate      Run extraction validation
  python run_tests.py --gaps          Analyze pattern gaps
  python run_tests.py --full          Run full test suite
  python run_tests.py --ci            CI mode (exit code on failure)
        """
    )

    parser.add_argument('--init', action='store_true',
                        help='Initialize ground truth database')
    parser.add_argument('--mine', action='store_true',
                        help='Mine documents for terms')
    parser.add_argument('--validate', action='store_true',
                        help='Run extraction validation')
    parser.add_argument('--gaps', action='store_true',
                        help='Analyze pattern gaps')
    parser.add_argument('--full', action='store_true',
                        help='Run full test suite')
    parser.add_argument('--ci', action='store_true',
                        help='CI mode with exit codes')
    parser.add_argument('--limit', type=int,
                        help='Limit number of documents to mine')

    args = parser.parse_args()

    # Default to --validate if no arguments
    if not any([args.init, args.mine, args.validate, args.gaps, args.full, args.ci]):
        parser.print_help()
        return

    if args.init:
        cmd_init(args)

    if args.mine:
        cmd_mine(args)

    if args.validate:
        cmd_validate(args)

    if args.gaps:
        cmd_gaps(args)

    if args.full:
        success = cmd_full(args)
        sys.exit(0 if success else 1)

    if args.ci:
        cmd_ci(args)


if __name__ == "__main__":
    main()
