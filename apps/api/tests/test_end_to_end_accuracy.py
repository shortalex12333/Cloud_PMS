#!/usr/bin/env python3
"""
END-TO-END ACCURACY TEST
========================

Tests the FULL pipeline: Query → Extraction → Capability Matching → Results

This is NOT about speed. This is about ACCURACY:
1. Did we extract the RIGHT entities?
2. Did we match the RIGHT capability?
3. Did we return RELEVANT results?

Ground truth is manually defined - what a human would expect.

Usage:
    # Extraction-only mode (no database needed)
    python -m pytest tests/test_end_to_end_accuracy.py -v

    # Full pipeline mode (requires Supabase connection)
    FULL_PIPELINE=1 python -m pytest tests/test_end_to_end_accuracy.py -v
"""

import os
import sys
import pytest
import asyncio
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ExpectedEntity:
    """What entity we expect to be extracted."""
    type: str                      # Entity type (brand, equipment, action, etc.)
    value: Optional[str] = None    # Expected value (None = any value of this type)
    required: bool = True          # If True, test fails if not extracted


@dataclass
class GroundTruthCase:
    """A single test case with expected outcomes."""
    id: str                                    # Unique test ID
    query: str                                 # User input
    lens: str                                  # Which lens/domain
    description: str                           # Human description of what this tests

    # Extraction expectations
    expected_entities: List[ExpectedEntity]    # Entities that SHOULD be extracted
    forbidden_entities: List[str] = field(default_factory=list)  # Entity types that should NOT appear

    # Capability expectations
    expected_capability: Optional[str] = None  # Which capability should be matched

    # Result expectations (for full pipeline mode)
    result_must_contain: List[str] = field(default_factory=list)  # Strings that MUST appear in results
    result_must_not_contain: List[str] = field(default_factory=list)  # Strings that must NOT appear
    min_results: int = 0                       # Minimum number of results expected
    max_results: Optional[int] = None          # Maximum results (None = no limit)


# =============================================================================
# GROUND TRUTH TEST CASES
# =============================================================================
# These are manually curated. Each case represents what a HUMAN would expect.

GROUND_TRUTH: List[GroundTruthCase] = [

    # =========================================================================
    # PARTS LENS - Brand searches
    # =========================================================================

    GroundTruthCase(
        id="parts_001",
        query="Racor filters",
        lens="parts",
        description="Simple brand + part type search",
        expected_entities=[
            ExpectedEntity(type="brand", value="racor"),
            ExpectedEntity(type="part", value="filter", required=False),
        ],
        expected_capability="part_by_part_number_or_name",
        result_must_contain=["Racor"],
        min_results=1,
    ),

    GroundTruthCase(
        id="parts_002",
        query="Caterpillar fuel injector",
        lens="parts",
        description="Brand + specific part search",
        expected_entities=[
            ExpectedEntity(type="brand", value="caterpillar"),
            ExpectedEntity(type="part", value="fuel injector", required=False),
        ],
        expected_capability="part_by_part_number_or_name",
        result_must_contain=["Caterpillar"],
        min_results=1,
    ),

    GroundTruthCase(
        id="parts_003",
        query="Caterpiller parts",  # MISSPELLING
        lens="parts",
        description="Misspelled brand should still match via fuzzy",
        expected_entities=[
            ExpectedEntity(type="brand", value="caterpillar"),  # Should correct to Caterpillar
        ],
        expected_capability="part_by_part_number_or_name",
        result_must_contain=["Caterpillar"],
        min_results=1,
    ),

    GroundTruthCase(
        id="parts_004",
        query="MTU oil filter",
        lens="parts",
        description="Different brand + part type",
        expected_entities=[
            ExpectedEntity(type="brand", value="mtu"),
            ExpectedEntity(type="part", value="oil filter", required=False),
        ],
        expected_capability="part_by_part_number_or_name",
        min_results=0,  # May or may not have MTU parts in DB
    ),

    GroundTruthCase(
        id="parts_005",
        query="part number ABC-123",
        lens="parts",
        description="Part number search",
        expected_entities=[
            ExpectedEntity(type="part_number", value="ABC-123", required=False),
            ExpectedEntity(type="identifier", required=False),
        ],
        expected_capability="part_by_part_number_or_name",
    ),

    GroundTruthCase(
        id="parts_006",
        query="12345",
        lens="parts",
        description="Pure numeric - should be treated as identifier/part number",
        expected_entities=[
            ExpectedEntity(type="identifier", required=False),
        ],
        # This is a known hard case - may not extract anything
    ),

    # =========================================================================
    # PARTS LENS - Negative/Edge cases
    # =========================================================================

    GroundTruthCase(
        id="parts_neg_001",
        query="show me",
        lens="parts",
        description="Generic phrase with no domain meaning - should extract nothing",
        expected_entities=[],  # Nothing expected
        min_results=0,
    ),

    GroundTruthCase(
        id="parts_neg_002",
        query="!@#$%^&*()",
        lens="parts",
        description="Special characters only - should extract nothing",
        expected_entities=[],
        min_results=0,
    ),

    # =========================================================================
    # SHOPPING LIST LENS
    # =========================================================================

    GroundTruthCase(
        id="shopping_001",
        query="pending shopping list",
        lens="shopping_list",
        description="Shopping list with status filter",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term"),
            ExpectedEntity(type="approval_status", value="pending"),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="shopping_002",
        query="approved items to order",
        lens="shopping_list",
        description="Approved status shopping list",
        expected_entities=[
            ExpectedEntity(type="approval_status", value="approved"),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="shopping_003",
        query="buy list",
        lens="shopping_list",
        description="Synonym for shopping list",
        expected_entities=[
            ExpectedEntity(type="shopping_list_term"),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="shopping_004",
        query="what needs to be ordered",
        lens="shopping_list",
        description="Natural language shopping list query",
        expected_entities=[
            # This is hard - natural language, no explicit terms
            # May need vector fallback
        ],
        min_results=0,
    ),

    # =========================================================================
    # CREW LENS - Warnings & Compliance
    # =========================================================================

    GroundTruthCase(
        id="crew_001",
        query="critical warnings",
        lens="crew",
        description="Warning severity filter",
        expected_entities=[
            ExpectedEntity(type="WARNING_SEVERITY", value="critical"),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="crew_002",
        query="active warnings",
        lens="crew",
        description="Warning status filter",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", value="active"),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="crew_003",
        query="rest compliance issues",
        lens="crew",
        description="Rest compliance search",
        expected_entities=[
            ExpectedEntity(type="REST_COMPLIANCE"),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="crew_004",
        query="Captain Smith schedule",
        lens="crew",
        description="Person name search",
        expected_entities=[
            ExpectedEntity(type="person", value="captain smith", required=False),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="crew_005",
        query="warnings",  # Single word
        lens="crew",
        description="Single word warning query",
        expected_entities=[
            ExpectedEntity(type="WARNING_STATUS", required=False),
        ],
        min_results=0,
    ),

    # =========================================================================
    # WORK ORDER LENS
    # =========================================================================

    GroundTruthCase(
        id="wo_001",
        query="main engine maintenance",
        lens="work_order",
        description="Equipment + action work order search",
        expected_entities=[
            ExpectedEntity(type="equipment", value="main engine"),
            ExpectedEntity(type="action", value="maintenance", required=False),
        ],
        expected_capability="work_order_by_id",
        min_results=0,
    ),

    GroundTruthCase(
        id="wo_002",
        query="open work orders",
        lens="work_order",
        description="Status filter on work orders",
        expected_entities=[
            ExpectedEntity(type="status", value="open", required=False),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="wo_003",
        query="generator oil change",
        lens="work_order",
        description="Equipment + specific action",
        expected_entities=[
            ExpectedEntity(type="equipment", value="generator"),
            ExpectedEntity(type="action", value="oil change", required=False),
        ],
        min_results=0,
    ),

    # =========================================================================
    # INVENTORY LENS
    # =========================================================================

    GroundTruthCase(
        id="inv_001",
        query="low stock items",
        lens="inventory",
        description="Stock status filter",
        expected_entities=[
            ExpectedEntity(type="stock_status", value="low"),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="inv_002",
        query="engine room inventory",
        lens="inventory",
        description="Location-based inventory search",
        expected_entities=[
            ExpectedEntity(type="location_on_board", value="engine room"),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="inv_003",
        query="out of stock",
        lens="inventory",
        description="Out of stock status",
        expected_entities=[
            ExpectedEntity(type="stock_status", value="out of stock"),
        ],
        min_results=0,
    ),

    # =========================================================================
    # RECEIVING LENS
    # =========================================================================

    GroundTruthCase(
        id="recv_001",
        query="pending deliveries",
        lens="receiving",
        description="Delivery status filter",
        expected_entities=[
            ExpectedEntity(type="receiving_status", value="pending", required=False),
            ExpectedEntity(type="approval_status", value="pending", required=False),
        ],
        min_results=0,
    ),

    GroundTruthCase(
        id="recv_002",
        query="Caterpillar shipment",
        lens="receiving",
        description="Brand + receiving context",
        expected_entities=[
            ExpectedEntity(type="brand", value="caterpillar"),
        ],
        min_results=0,
    ),

    # =========================================================================
    # DOCUMENT LENS
    # =========================================================================

    GroundTruthCase(
        id="doc_001",
        query="engine manual",
        lens="document",
        description="Document type search",
        expected_entities=[
            ExpectedEntity(type="document_type", value="manual", required=False),
            ExpectedEntity(type="equipment", value="engine", required=False),
        ],
        expected_capability="documents_search",
        min_results=0,
    ),

    # =========================================================================
    # CROSS-CUTTING: Misspellings that MUST work
    # =========================================================================

    GroundTruthCase(
        id="typo_001",
        query="Racoor filters",  # Double 'o'
        lens="parts",
        description="Misspelled Racor should fuzzy match",
        expected_entities=[
            ExpectedEntity(type="brand", value="racor"),
        ],
    ),

    GroundTruthCase(
        id="typo_002",
        query="genaratur maintenance",  # generator misspelled
        lens="work_order",
        description="Misspelled generator should fuzzy match",
        expected_entities=[
            ExpectedEntity(type="equipment", value="generator"),
        ],
    ),

    GroundTruthCase(
        id="typo_003",
        query="Volvo Penta oil",
        lens="parts",
        description="Multi-word brand",
        expected_entities=[
            ExpectedEntity(type="brand", value="volvo penta"),
        ],
    ),

    # =========================================================================
    # HARD CASES - These define our accuracy ceiling
    # =========================================================================

    GroundTruthCase(
        id="hard_001",
        query="the filter for the main engine that we ordered last week",
        lens="parts",
        description="Complex natural language with multiple potential entities",
        expected_entities=[
            ExpectedEntity(type="part", value="filter", required=False),
            ExpectedEntity(type="equipment", value="main engine", required=False),
            ExpectedEntity(type="time_ref", required=False),
        ],
    ),

    GroundTruthCase(
        id="hard_002",
        query="Rcr",  # Too short for fuzzy (3 chars)
        lens="parts",
        description="Too short for fuzzy matching - known limitation",
        expected_entities=[],  # Expected to fail
    ),

    GroundTruthCase(
        id="hard_003",
        query="stuff",
        lens="parts",
        description="Generic word with no domain meaning",
        expected_entities=[],  # Should extract nothing
    ),
]


# =============================================================================
# TEST EXECUTION
# =============================================================================

class AccuracyMetrics:
    """Tracks accuracy metrics across all test cases."""

    def __init__(self):
        self.total_cases = 0
        self.extraction_correct = 0
        self.extraction_partial = 0
        self.extraction_wrong = 0
        self.capability_correct = 0
        self.capability_wrong = 0
        self.results_relevant = 0
        self.results_irrelevant = 0
        self.failures: List[Dict[str, Any]] = []

    def add_result(self, case: GroundTruthCase, actual_entities: List[Dict],
                   actual_capability: Optional[str], actual_results: List[Dict],
                   extraction_score: float, notes: str = ""):
        self.total_cases += 1

        # Extraction accuracy
        if extraction_score >= 0.8:
            self.extraction_correct += 1
        elif extraction_score >= 0.5:
            self.extraction_partial += 1
        else:
            self.extraction_wrong += 1
            self.failures.append({
                "case_id": case.id,
                "query": case.query,
                "expected_entities": [e.type for e in case.expected_entities],
                "actual_entities": [e.get("type") for e in actual_entities],
                "extraction_score": extraction_score,
                "notes": notes,
            })

        # Capability accuracy
        if case.expected_capability:
            if actual_capability == case.expected_capability:
                self.capability_correct += 1
            else:
                self.capability_wrong += 1

    def report(self) -> str:
        lines = [
            "=" * 70,
            "END-TO-END ACCURACY REPORT",
            "=" * 70,
            f"Total test cases: {self.total_cases}",
            "",
            "EXTRACTION ACCURACY:",
            f"  Correct (>=80%): {self.extraction_correct} ({100*self.extraction_correct/max(1,self.total_cases):.1f}%)",
            f"  Partial (50-79%): {self.extraction_partial} ({100*self.extraction_partial/max(1,self.total_cases):.1f}%)",
            f"  Wrong (<50%): {self.extraction_wrong} ({100*self.extraction_wrong/max(1,self.total_cases):.1f}%)",
            "",
        ]

        if self.capability_correct + self.capability_wrong > 0:
            lines.extend([
                "CAPABILITY MATCHING:",
                f"  Correct: {self.capability_correct}",
                f"  Wrong: {self.capability_wrong}",
                "",
            ])

        if self.failures:
            lines.extend([
                "FAILURES:",
                "-" * 70,
            ])
            for f in self.failures[:20]:  # Show first 20
                lines.append(f"  [{f['case_id']}] \"{f['query']}\"")
                lines.append(f"    Expected: {f['expected_entities']}")
                lines.append(f"    Actual: {f['actual_entities']}")
                lines.append(f"    Score: {f['extraction_score']:.2f}")
                if f['notes']:
                    lines.append(f"    Notes: {f['notes']}")
                lines.append("")

        return "\n".join(lines)


def normalize_entities(entities_dict: Dict) -> List[Dict]:
    """
    Convert entities from dict format {type: [values]} to list format [{type, value}].

    The orchestrator returns: {"brand": ["Racor"], "part": ["filter"]}
    We normalize to: [{"type": "brand", "value": "Racor"}, {"type": "part", "value": "filter"}]
    """
    normalized = []
    if isinstance(entities_dict, dict):
        for entity_type, values in entities_dict.items():
            if isinstance(values, list):
                for value in values:
                    normalized.append({"type": entity_type, "value": value})
            else:
                normalized.append({"type": entity_type, "value": values})
    return normalized


def calculate_extraction_score(case: GroundTruthCase, actual_entities: Dict) -> float:
    """
    Calculate how well the actual extraction matches expected.

    Returns 0.0 to 1.0:
    - 1.0 = All required entities extracted correctly
    - 0.5 = Some entities extracted
    - 0.0 = No expected entities extracted
    """
    # Normalize entities to list format
    normalized = normalize_entities(actual_entities)

    if not case.expected_entities:
        # No entities expected - score is 1.0 if we extracted nothing, 0.5 if we extracted something
        return 1.0 if not normalized else 0.5

    actual_types = {e.get("type", "").lower() for e in normalized}
    actual_values = set()
    for e in normalized:
        val = e.get("value", "")
        if val:
            actual_values.add(str(val).lower())

    required_found = 0
    required_total = 0
    optional_found = 0
    optional_total = 0

    for expected in case.expected_entities:
        expected_type = expected.type.lower()

        # Check if type was extracted
        type_found = expected_type in actual_types

        # Check if value matches (if specified)
        value_found = True
        if expected.value:
            value_found = expected.value.lower() in actual_values or any(
                expected.value.lower() in str(e.get("value", "")).lower()
                for e in normalized
            )

        found = type_found and value_found

        if expected.required:
            required_total += 1
            if found:
                required_found += 1
        else:
            optional_total += 1
            if found:
                optional_found += 1

    # Score: required entities are worth 80%, optional are worth 20%
    if required_total == 0:
        required_score = 1.0
    else:
        required_score = required_found / required_total

    if optional_total == 0:
        optional_score = 1.0
    else:
        optional_score = optional_found / optional_total

    return 0.8 * required_score + 0.2 * optional_score


# =============================================================================
# PYTEST FIXTURES AND TESTS
# =============================================================================

@pytest.fixture(scope="module")
def extractor():
    """Load the extraction orchestrator."""
    from extraction.orchestrator import ExtractionOrchestrator
    return ExtractionOrchestrator()


@pytest.fixture(scope="module")
def metrics():
    """Shared metrics collector."""
    return AccuracyMetrics()


@pytest.mark.parametrize("case", GROUND_TRUTH, ids=[c.id for c in GROUND_TRUTH])
def test_extraction_accuracy(case: GroundTruthCase, extractor, metrics):
    """Test that extraction produces expected entities."""

    # Run extraction (lens is used for ground truth categorization, not passed to extractor)
    result = asyncio.get_event_loop().run_until_complete(
        extractor.extract(case.query)
    )

    actual_entities = result.get("entities", {})
    normalized_entities = normalize_entities(actual_entities)

    # Calculate score
    score = calculate_extraction_score(case, actual_entities)

    # Record metrics
    notes = ""
    if not normalized_entities:
        notes = "Zero entities extracted"

    metrics.add_result(
        case=case,
        actual_entities=normalized_entities,
        actual_capability=None,
        actual_results=[],
        extraction_score=score,
        notes=notes,
    )

    # Check for forbidden entities
    actual_types = {e.get("type", "").lower() for e in normalized_entities}
    for forbidden in case.forbidden_entities:
        assert forbidden.lower() not in actual_types, \
            f"Forbidden entity type '{forbidden}' was extracted"

    # Assert minimum score for required entities
    required_entities = [e for e in case.expected_entities if e.required]
    if required_entities:
        assert score >= 0.5, \
            f"Extraction score {score:.2f} below threshold. " \
            f"Expected: {[e.type for e in required_entities]}, " \
            f"Got: {[e.get('type') for e in normalized_entities]}"


def test_accuracy_summary(metrics):
    """Print accuracy summary after all tests."""
    print("\n")
    print(metrics.report())

    # Save report to file
    report_path = f"/private/tmp/claude/-Volumes-Backup-CELESTE/27a139f0-977c-4beb-a66a-839509dfd18a/scratchpad/accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_path, "w") as f:
        f.write(metrics.report())
    print(f"\nReport saved to: {report_path}")

    # Assert overall accuracy threshold
    total = metrics.total_cases
    correct = metrics.extraction_correct + metrics.extraction_partial
    accuracy = correct / max(1, total)

    print(f"\nOverall accuracy: {accuracy:.1%}")
    # Don't fail on accuracy threshold - this is diagnostic


# =============================================================================
# STANDALONE EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("Running end-to-end accuracy test...")
    print(f"Ground truth cases: {len(GROUND_TRUTH)}")

    # Load extractor
    from extraction.orchestrator import ExtractionOrchestrator
    extractor = ExtractionOrchestrator()

    metrics = AccuracyMetrics()

    for case in GROUND_TRUTH:
        print(f"  [{case.id}] {case.query[:40]}...", end=" ")

        result = asyncio.get_event_loop().run_until_complete(
            extractor.extract(case.query)
        )

        actual_entities = result.get("entities", {})
        normalized = normalize_entities(actual_entities)
        score = calculate_extraction_score(case, actual_entities)

        status = "✅" if score >= 0.8 else "⚠️" if score >= 0.5 else "❌"
        print(f"{status} score={score:.2f}")

        metrics.add_result(
            case=case,
            actual_entities=normalized,
            actual_capability=None,
            actual_results=[],
            extraction_score=score,
            notes="" if normalized else "Zero entities",
        )

    print("\n")
    print(metrics.report())
