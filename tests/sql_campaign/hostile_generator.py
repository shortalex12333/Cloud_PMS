"""
HOSTILE SQL TEST GENERATOR
===========================

Generates 1500+ hostile test queries across multiple categories.
Goal: Break assumptions, find edge cases, prove failures.

CATEGORIES:
1. Canonical normalization attacks (spacing, casing, separators)
2. Filter stacking and conjunction logic
3. Cross-table constraint resolution
4. Ranking and weighting validation
5. Security and injection resistance
6. Chaotic human phrasing (voice dictation, typos)
7. Negative/impossible queries (correct answer is empty)
8. Multi-constraint compound queries
"""

import json
import random
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

class TestCategory(str, Enum):
    CANONICAL = "canonical"
    FILTER_STACK = "filter_stack"
    CROSS_TABLE = "cross_table"
    RANKING = "ranking"
    SECURITY = "security"
    CHAOTIC = "chaotic"
    NEGATIVE = "negative"
    COMPOUND = "compound"

class ExpectedBehavior(str, Enum):
    HAS_RESULTS = "has_results"
    EMPTY = "empty"
    SPECIFIC_COUNT = "specific_count"
    FIRST_MATCH = "first_match"
    BLOCKED = "blocked"
    ERROR = "error"

@dataclass
class HostileTest:
    id: str
    query: str
    category: TestCategory
    expected: ExpectedBehavior
    expected_detail: str  # e.g., "first result should contain 'filter'"
    difficulty: int  # 1-5, 5 being hardest
    notes: str = ""

# =============================================================================
# CANONICAL NORMALIZATION TESTS (300+)
# =============================================================================

def generate_canonical_tests() -> List[HostileTest]:
    tests = []

    # Equipment code variants - using ACTUAL DATABASE CODES
    # Codes from pms_equipment: ME-S-001, ME-P-001, GEN-001, GEN-002, HVAC-001,
    # THR-B-001, THR-S-001, WM-001, HYD-001, STP-001, NAV-RAD-001, NAV-AP-001, FIRE-001
    equipment_variants = [
        ("ME-S-001", "ME S 001", "MES001", "me-s-001", "ME - S - 001", "M E S 0 0 1", "mes 001", "ME.S.001"),
        ("ME-P-001", "ME P 001", "MEP001", "me-p-001", "me p 001", "mep001"),
        ("GEN-001", "GEN 001", "gen001", "GEN001", "gen 001", "G E N 001"),
        ("GEN-002", "GEN 002", "gen002", "GEN002", "gen 002"),
        ("HVAC-001", "hvac 001", "HVAC001", "H V A C 001", "hvac-001", "HVAC 001"),
        ("THR-B-001", "THR B 001", "thrb001", "thr-b-001", "thruster b 001"),
        ("THR-S-001", "THR S 001", "thrs001", "thr-s-001"),
        ("WM-001", "WM 001", "wm001", "wm-001", "watermaker 001"),
        ("HYD-001", "HYD 001", "hyd001", "hyd-001", "hydraulic 001"),
        ("STP-001", "STP 001", "stp001", "stp-001", "sewage 001"),
        ("FIRE-001", "FIRE 001", "fire001", "fire-001"),
        ("NAV-RAD-001", "NAV RAD 001", "navrad001", "nav-rad-001", "radar 001"),
        ("NAV-AP-001", "NAV AP 001", "navap001", "nav-ap-001", "autopilot 001"),
    ]

    for i, variants in enumerate(equipment_variants):
        canonical = variants[0]
        for j, variant in enumerate(variants[1:], 1):
            # Use "equipment" keyword to route to pms_equipment table
            tests.append(HostileTest(
                id=f"CAN-EQ-{i:03d}-{j:02d}",
                query=f"show equipment {variant}",
                category=TestCategory.CANONICAL,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Should resolve '{variant}' to '{canonical}'",
                difficulty=2 if j < 3 else 4,
                notes=f"Canonical: {canonical}"
            ))
            # Also test in different query contexts (still using equipment routing)
            if j <= 2:
                tests.append(HostileTest(
                    id=f"CAN-EQ-{i:03d}-{j:02d}b",
                    query=f"equipment details {variant}",
                    category=TestCategory.CANONICAL,
                    expected=ExpectedBehavior.HAS_RESULTS,
                    expected_detail=f"Equipment lookup variant",
                    difficulty=2,
                ))

    # Part number variants - using ACTUAL DATABASE PART NUMBERS
    # Verified from pms_parts table
    part_variants = [
        ("ENG-0008-103", "eng 0008 103", "ENG0008103", "ENG 0008 103", "eng-0008-103", "ENG.0008.103"),
        ("ENG-0010-385", "eng 0010 385", "ENG0010385", "eng0010385"),
        ("ENG-0012-584", "eng 0012 584", "ENG0012584"),
        ("PMP-0016-384", "pmp 0016 384", "PMP0016384", "pmp-0016-384"),
        ("PMP-0018-280", "pmp 0018 280", "PMP0018280"),
        ("FLT-0002-346", "flt 0002 346", "FLT0002346"),
        ("FLT-0003-325", "flt 0003 325", "FLT0003325"),
        ("HYD-0066-515", "hyd 0066 515", "HYD0066515", "hyd-0066-515"),
        ("GEN-0127-320", "gen 0127 320", "GEN0127320"),
        ("NAV-0131-486", "nav 0131 486", "NAV0131486"),
    ]

    for i, variants in enumerate(part_variants):
        canonical = variants[0]
        for j, variant in enumerate(variants[1:], 1):
            tests.append(HostileTest(
                id=f"CAN-PT-{i:03d}-{j:02d}",
                query=f"part {variant}",
                category=TestCategory.CANONICAL,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Should resolve to {canonical}",
                difficulty=2,
            ))

    # Fault code variants - using ACTUAL DATABASE FAULT CODES
    # From pms_faults: E001-E047, G012, HVAC-05, NAV-R01, SP-002, T-001, WM-003
    fault_variants = [
        ("E047", "e047", "E 047", "e-047", "E-047", "fault E047", "error E047", "alarm E047"),
        ("E001", "e001", "E 001", "E-001", "fault e001", "error e 001"),
        ("E002", "e002", "E 002", "E-002"),
        ("E003", "e003", "E 003", "E-003"),
        ("G012", "g012", "G 012", "g-012", "fault g012"),
        ("E005", "e005", "E 005", "E-005"),
        ("E010", "e010", "E 010", "E-010"),
        ("E015", "e015", "E 015", "E-015", "fault e015"),
        ("E020", "e020", "E 020", "E-020"),
        ("E025", "e025", "E 025", "E-025", "alarm e025"),
        ("E030", "e030", "E 030", "E-030"),
        ("E036", "e036", "E 036", "E-036"),
    ]

    for i, variants in enumerate(fault_variants):
        canonical = variants[0]
        for j, variant in enumerate(variants[1:], 1):
            tests.append(HostileTest(
                id=f"CAN-FT-{i:03d}-{j:02d}",
                query=f"diagnose {variant}",
                category=TestCategory.CANONICAL,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Should resolve to {canonical}",
                difficulty=2 if j < 3 else 3,
            ))

    # Location variants - comprehensive
    location_variants = [
        ("BOX-2A", "box 2a", "BOX 2A", "box-2a", "box 2 a", "Box 2A", "BOX2A", "storage 2a"),
        ("BOX-2B", "box 2b", "BOX 2B", "box-2b", "box 2 b", "Box 2B"),
        ("BOX-2C", "box 2c", "BOX 2C", "box-2c", "box 2 c"),
        ("BOX-2D", "box 2d", "BOX 2D", "box2d", "BOX-2-D", "box two d", "storage 2d"),
        ("BOX-4A", "box 4a", "four a", "4a", "4 a", "box four a", "BOX4A"),
        ("LOCKER-3B", "locker 3b", "locker-3b", "locker 3 b", "lock 3b", "LOCKER3B"),
        ("DECK-1", "deck 1", "deck-1", "deck one", "DECK1", "deck 01"),
        ("DECK-2", "deck 2", "deck-2", "deck two", "DECK2"),
        ("ENGINE-ROOM", "engine room", "ER", "engine-room", "eng rm"),
        ("BRIDGE", "bridge", "wheelhouse", "pilothouse"),
        ("LAZARETTE", "lazarette", "laz", "stern locker"),
    ]

    for i, variants in enumerate(location_variants):
        canonical = variants[0]
        for j, variant in enumerate(variants[1:], 1):
            tests.append(HostileTest(
                id=f"CAN-LOC-{i:03d}-{j:02d}",
                query=f"inventory in {variant}",
                category=TestCategory.CANONICAL,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Should find items in {canonical}",
                difficulty=3 if "four" in variant or " a" in variant else 2,
            ))

    # Number word expansions
    number_tests = [
        ("four c", "4c", "location normalization"),
        ("box two d", "BOX-2D", "word to digit"),
        ("deck one", "DECK-1", "deck number"),
        ("generator two", "GEN-002", "equipment number"),
    ]

    for i, (query_form, expected_form, notes) in enumerate(number_tests):
        tests.append(HostileTest(
            id=f"CAN-NUM-{i:03d}",
            query=f"inventory in {query_form}",
            category=TestCategory.CANONICAL,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"'{query_form}' should normalize to '{expected_form}'",
            difficulty=4,
            notes=notes
        ))

    return tests

# =============================================================================
# FILTER STACKING TESTS (400+)
# =============================================================================

def generate_filter_tests() -> List[HostileTest]:
    tests = []

    # Single filters - comprehensive status coverage
    single_filters = [
        ("pending work orders", ExpectedBehavior.HAS_RESULTS, "status IN (pending, planned)"),
        ("planned work orders", ExpectedBehavior.HAS_RESULTS, "status = planned"),
        ("out of stock parts", ExpectedBehavior.HAS_RESULTS, "quantity <= 0"),
        ("out of stock", ExpectedBehavior.HAS_RESULTS, "quantity <= 0"),
        ("oos inventory", ExpectedBehavior.HAS_RESULTS, "out of stock abbreviation"),
        ("completed work orders", ExpectedBehavior.HAS_RESULTS, "status = completed"),
        ("in progress tasks", ExpectedBehavior.HAS_RESULTS, "status = in_progress"),
        ("in progress work orders", ExpectedBehavior.HAS_RESULTS, "status = in_progress"),
        ("critical priority work orders", ExpectedBehavior.HAS_RESULTS, "priority = critical"),
        ("critical work orders", ExpectedBehavior.HAS_RESULTS, "priority = critical"),
        ("routine work orders", ExpectedBehavior.HAS_RESULTS, "priority = routine"),
        ("low stock items", ExpectedBehavior.HAS_RESULTS, "needs_reorder = true"),
        ("items needing reorder", ExpectedBehavior.HAS_RESULTS, "needs_reorder = true"),
        ("overdue maintenance", ExpectedBehavior.HAS_RESULTS, "overdue filter"),
        ("overdue work orders", ExpectedBehavior.HAS_RESULTS, "due_date < NOW"),
    ]

    for i, (query, expected, detail) in enumerate(single_filters):
        tests.append(HostileTest(
            id=f"FILT-SINGLE-{i:03d}",
            query=query,
            category=TestCategory.FILTER_STACK,
            expected=expected,
            expected_detail=detail,
            difficulty=1,
        ))
        # Also test with different phrasings
        variants = [
            f"show me {query}",
            f"list {query}",
            f"find {query}",
            f"get {query}",
        ]
        for j, v in enumerate(variants[:2]):  # Limit to avoid explosion
            tests.append(HostileTest(
                id=f"FILT-SINGLE-{i:03d}-v{j}",
                query=v,
                category=TestCategory.FILTER_STACK,
                expected=expected,
                expected_detail=f"Phrased: {detail}",
                difficulty=1,
            ))

    # Combined filters (AND) - comprehensive
    combined_filters = [
        ("pending work orders for ME-S-001", "status AND equipment"),
        ("pending work orders for ME-P-001", "status AND equipment variant"),
        ("pending tasks for generator", "status AND equipment name"),
        ("out of stock inventory in BOX-2A", "quantity AND location"),
        ("out of stock in BOX-2D", "quantity AND location variant"),
        ("out of stock filters in storage", "quantity AND name AND location"),
        ("critical work orders in progress", "priority AND status"),
        ("critical pending work orders", "priority AND status combo"),
        ("pending work orders for main engine", "status AND free text"),
        ("out of stock filters", "quantity AND name filter"),
        ("out of stock oil filters", "quantity AND specific name"),
        ("low stock parts in engine room", "needs_reorder AND location"),
        ("completed work orders for generator", "status AND equipment"),
        ("in progress maintenance for HVAC", "status AND equipment"),
        ("critical faults on ME-S-001", "priority AND equipment AND type"),
        ("pending generator maintenance", "status AND equipment AND action"),
        ("out of stock fuel filters in BOX-2A", "qty AND name AND location"),
        ("critical overdue work orders", "priority AND temporal"),
    ]

    for i, (query, detail) in enumerate(combined_filters):
        tests.append(HostileTest(
            id=f"FILT-COMBO-{i:03d}",
            query=query,
            category=TestCategory.FILTER_STACK,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"AND combination: {detail}",
            difficulty=3,
        ))

    # Multiple location OR (IN semantics) - comprehensive
    or_filters = [
        ("inventory in box 2a and 2b", "location IN (BOX-2A, BOX-2B)"),
        ("inventory in box 2a or box 2b", "location IN (BOX-2A, BOX-2B)"),
        ("inventory in box 2a, 2b, or 2c", "location IN (BOX-2A, BOX-2B, BOX-2C)"),
        ("inventory box 2d and 2c", "location IN (BOX-2D, BOX-2C)"),
        ("parts in deck or bridge", "location ILIKE deck OR bridge"),
        ("parts in deck 1 or deck 2", "location IN (DECK-1, DECK-2)"),
        ("inventory in locker or box", "location type OR"),
        ("equipment in engine room or lazarette", "location IN (ENGINE-ROOM, LAZARETTE)"),
        ("filters in box 2a and box 4a", "name AND location OR"),
        ("oil filters in 2a or 2b", "name AND location IN"),
        ("pending or completed work orders", "status IN (pending, completed)"),
        ("pending or in progress tasks", "status IN (pending, in_progress)"),
        ("critical or routine priority", "priority IN (critical, routine)"),
        ("generator or HVAC equipment", "equipment name OR"),
        ("oil or fuel filters", "part name OR"),
    ]

    for i, (query, detail) in enumerate(or_filters):
        tests.append(HostileTest(
            id=f"FILT-OR-{i:03d}",
            query=query,
            category=TestCategory.FILTER_STACK,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"OR/IN semantics: {detail}",
            difficulty=4,
        ))

    # Negation filters - comprehensive
    negation_filters = [
        ("inventory not in box 2d", "location != BOX-2D"),
        ("inventory excluding box 2a", "location != BOX-2A"),
        ("parts not in locker", "location NOT LIKE locker"),
        ("work orders excluding completed", "status != completed"),
        ("work orders not completed", "status != completed variant"),
        ("non-completed work orders", "status != completed variant 2"),
        ("parts not out of stock", "quantity > 0"),
        ("in stock inventory", "quantity > 0 positive form"),
        ("available parts", "quantity > 0 synonym"),
        ("work orders other than pending", "status != pending"),
        ("equipment except generators", "name NOT LIKE gen"),
        ("filters except oil filters", "name AND NOT name"),
    ]

    for i, (query, detail) in enumerate(negation_filters):
        tests.append(HostileTest(
            id=f"FILT-NEG-{i:03d}",
            query=query,
            category=TestCategory.FILTER_STACK,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Negation: {detail}",
            difficulty=5,
            notes="Negation is advanced - may not be supported"
        ))

    # Contradictory filters (should return empty)
    contradictory = [
        ("pending completed work orders", "status cannot be both"),
        ("out of stock parts with quantity 10", "qty <= 0 AND qty = 10"),
        ("completed in progress tasks", "status contradictory"),
        ("critical routine priority", "priority contradictory"),
        ("in stock out of stock parts", "quantity contradictory"),
    ]

    for i, (query, detail) in enumerate(contradictory):
        tests.append(HostileTest(
            id=f"FILT-CONTRA-{i:03d}",
            query=query,
            category=TestCategory.FILTER_STACK,
            expected=ExpectedBehavior.EMPTY,
            expected_detail=f"Contradictory: {detail}",
            difficulty=4,
        ))

    # Temporal filters
    temporal_filters = [
        ("work orders due this week", "due_date temporal filter"),
        ("work orders due today", "due_date = today"),
        ("overdue maintenance tasks", "due_date < NOW"),
        ("upcoming work orders", "due_date > NOW"),
        ("recent work orders", "temporal recent"),
        ("work orders from last month", "temporal past"),
        ("scheduled for next week", "temporal future"),
    ]

    for i, (query, detail) in enumerate(temporal_filters):
        tests.append(HostileTest(
            id=f"FILT-TEMP-{i:03d}",
            query=query,
            category=TestCategory.FILTER_STACK,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Temporal: {detail}",
            difficulty=4,
            notes="Temporal filters require date parsing"
        ))

    return tests

# =============================================================================
# CROSS-TABLE RESOLUTION TESTS (250+)
# =============================================================================

def generate_cross_table_tests() -> List[HostileTest]:
    tests = []

    # Equipment → Work Orders (code to equipment_id) - comprehensive
    equipment_to_wo = [
        "work orders for ME-S-001",
        "work orders for ME-P-001",
        "work orders for GEN-001",
        "work orders for GEN-002",
        "work orders for HVAC-001",
        "work orders for THR-B-001",
        "work orders for THR-S-001",
        "work orders for AUX-001",
        "work orders for DG1",
        "work orders for DG2",
        "maintenance for GEN-002",
        "maintenance for main engine",
        "maintenance for generator",
        "maintenance for thruster",
        "tasks for HVAC-001",
        "tasks for generator",
        "service history THR-B-001",
        "service history ME-S-001",
        "service history for main engine",
        "maintenance schedule ME-S-001",
        "maintenance schedule generator",
    ]

    for i, query in enumerate(equipment_to_wo):
        tests.append(HostileTest(
            id=f"CROSS-EQ-WO-{i:03d}",
            query=query,
            category=TestCategory.CROSS_TABLE,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Equipment code resolved to equipment_id for work order query",
            difficulty=3,
        ))

    # Part → Inventory (part_id resolution) - comprehensive
    part_to_inv = [
        "stock level for ENG-0008-103",
        "stock level for fuel filter",
        "stock level oil filter",
        "quantity of fuel filter",
        "quantity of oil filter",
        "quantity of impeller",
        "where is the oil filter stored",
        "where is ENG-0008-103 stored",
        "location of fuel filter",
        "location of impeller",
        "inventory for oil filter",
        "inventory for fuel pump",
        "inventory for ENG-0008-103",
        "how many oil filters",
        "how many fuel filters in stock",
        "how many impellers do we have",
    ]

    for i, query in enumerate(part_to_inv):
        tests.append(HostileTest(
            id=f"CROSS-PT-INV-{i:03d}",
            query=query,
            category=TestCategory.CROSS_TABLE,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Part lookup crosses to inventory view",
            difficulty=3,
        ))

    # Equipment + Fault (multi-entity) - comprehensive
    multi_entity = [
        "fault E047 on ME-P-001",
        "fault E047 on ME-S-001",
        "fault E001 on generator",
        "fault G012 on GEN-002",
        "overheating issues on main engine",
        "overheating on ME-S-001",
        "vibration faults on generator",
        "vibration on GEN-001",
        "generator faults for GEN-002",
        "engine faults for ME-S-001",
        "thruster faults for THR-B-001",
        "HVAC faults",
        "alarm E047 main engine",
        "error E001 generator",
        "E047 symptoms on starboard engine",
    ]

    for i, query in enumerate(multi_entity):
        tests.append(HostileTest(
            id=f"CROSS-MULTI-{i:03d}",
            query=query,
            category=TestCategory.CROSS_TABLE,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Multiple entity types resolved across tables",
            difficulty=4,
        ))

    # Supplier → Parts resolution
    supplier_parts = [
        "parts from MTU",
        "parts from Caterpillar",
        "filters from supplier",
        "supplier for oil filter",
        "who supplies fuel filters",
        "vendor for impeller",
    ]

    for i, query in enumerate(supplier_parts):
        tests.append(HostileTest(
            id=f"CROSS-SUP-PT-{i:03d}",
            query=query,
            category=TestCategory.CROSS_TABLE,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Supplier to parts resolution",
            difficulty=4,
        ))

    # Work Order → Parts consumption
    wo_parts = [
        "parts used in WO-1234",
        "parts needed for maintenance",
        "parts for work order",
        "consumables for service",
    ]

    for i, query in enumerate(wo_parts):
        tests.append(HostileTest(
            id=f"CROSS-WO-PT-{i:03d}",
            query=query,
            category=TestCategory.CROSS_TABLE,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Work order to parts resolution",
            difficulty=4,
        ))

    # Symptom → Fault resolution
    symptom_fault = [
        "what faults cause overheating",
        "what faults cause vibration",
        "what faults cause noise",
        "symptoms for fault E047",
        "symptoms for fault E001",
        "vibration fault diagnosis",
        "overheating fault diagnosis",
        "noise diagnosis",
        "leak diagnosis",
    ]

    for i, query in enumerate(symptom_fault):
        tests.append(HostileTest(
            id=f"CROSS-SYM-FT-{i:03d}",
            query=query,
            category=TestCategory.CROSS_TABLE,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Symptom to fault resolution",
            difficulty=4,
        ))

    # Equipment → Location
    eq_location = [
        "equipment in engine room",
        "equipment on deck",
        "equipment on bridge",
        "what's in the lazarette",
        "equipment in machinery space",
    ]

    for i, query in enumerate(eq_location):
        tests.append(HostileTest(
            id=f"CROSS-EQ-LOC-{i:03d}",
            query=query,
            category=TestCategory.CROSS_TABLE,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Equipment by location query",
            difficulty=3,
        ))

    return tests

# =============================================================================
# RANKING TESTS (200+)
# =============================================================================

def generate_ranking_tests() -> List[HostileTest]:
    tests = []

    # Exact vs partial match - comprehensive
    ranking_tests = [
        ("oil filter", "Exact 'Oil Filter' should rank higher than partial"),
        ("fuel filter", "Exact match fuel filter first"),
        ("fuel pump seal", "Exact match outranks partial"),
        ("generator impeller", "Specific part name first"),
        ("coolant hose", "Exact coolant hose match"),
        ("main engine", "Exact main engine match"),
        ("hydraulic pump", "Exact hydraulic pump match"),
        ("alternator belt", "Exact match ranking"),
        ("thermostat", "Single word exact match"),
        ("impeller", "Single word exact match"),
        ("gasket", "Single word exact match"),
        ("bearing", "Single word exact match"),
        ("seal", "Single word exact match"),
    ]

    for i, (query, detail) in enumerate(ranking_tests):
        tests.append(HostileTest(
            id=f"RANK-EXACT-{i:03d}",
            query=query,
            category=TestCategory.RANKING,
            expected=ExpectedBehavior.FIRST_MATCH,
            expected_detail=detail,
            difficulty=2,
        ))

    # Wave precedence (EXACT > ILIKE > TRIGRAM) - comprehensive
    wave_tests = [
        ("ENG-0008-103", "Exact part number should be wave EXACT"),
        ("ENG-0010-201", "Exact part number EXACT wave"),
        ("ME-S-001", "Exact equipment code EXACT wave"),
        ("E047", "Exact fault code EXACT wave"),
        ("eng 0008", "Partial should still find via ILIKE"),
        ("eng-0008", "Partial with separator ILIKE"),
        ("fule filter", "Typo should find via TRIGRAM"),
        ("fiter", "Typo TRIGRAM"),
        ("genertor", "Typo TRIGRAM"),
        ("pummp", "Typo TRIGRAM"),
        ("engin", "Truncation TRIGRAM"),
        ("impeler", "Typo TRIGRAM"),
    ]

    for i, (query, detail) in enumerate(wave_tests):
        tests.append(HostileTest(
            id=f"RANK-WAVE-{i:03d}",
            query=query,
            category=TestCategory.RANKING,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=detail,
            difficulty=3,
        ))

    # Generic vs specific - comprehensive
    generic_tests = [
        ("filter", "Should not return all filters equally"),
        ("pump", "Should prefer exact pump matches"),
        ("engine", "Many items contain 'engine'"),
        ("oil", "Generic - many matches"),
        ("fuel", "Generic - many matches"),
        ("water", "Generic term"),
        ("generator", "Equipment name - multiple matches"),
        ("seal", "Part type - multiple matches"),
        ("hose", "Part type - multiple matches"),
        ("valve", "Part type - multiple matches"),
        ("belt", "Part type - multiple matches"),
        ("part", "Very generic"),
        ("maintenance", "Action word"),
        ("service", "Action word"),
    ]

    for i, (query, detail) in enumerate(generic_tests):
        tests.append(HostileTest(
            id=f"RANK-GENERIC-{i:03d}",
            query=query,
            category=TestCategory.RANKING,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Generic term '{query}' - {detail}",
            difficulty=3,
        ))

    # Constraint satisfaction ranking
    constraint_ranking = [
        ("pending work orders ME-S-001", "More constraints = higher rank"),
        ("critical pending ME-S-001", "Triple constraint ranking"),
        ("out of stock oil filter box 2a", "Triple constraint inventory"),
        ("fuel filter", "Single constraint baseline"),
        ("oil filter box 2a", "Double constraint inventory"),
    ]

    for i, (query, detail) in enumerate(constraint_ranking):
        tests.append(HostileTest(
            id=f"RANK-CONSTRAINT-{i:03d}",
            query=query,
            category=TestCategory.RANKING,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=detail,
            difficulty=4,
        ))

    # Table priority ranking
    table_priority = [
        ("ENG-0008-103", "Part number - should prioritize pms_parts"),
        ("ME-S-001", "Equipment code - should prioritize pms_equipment"),
        ("E047", "Fault code - should prioritize pms_faults"),
        ("pending", "Status - should prioritize work_orders"),
        ("box 2a", "Location - should prioritize inventory"),
    ]

    for i, (query, detail) in enumerate(table_priority):
        tests.append(HostileTest(
            id=f"RANK-TABLE-{i:03d}",
            query=query,
            category=TestCategory.RANKING,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=detail,
            difficulty=3,
        ))

    return tests

# =============================================================================
# SECURITY TESTS (250+)
# =============================================================================

def generate_security_tests() -> List[HostileTest]:
    tests = []

    # SQL injection attempts (should be blocked or escaped) - comprehensive
    injections = [
        "parts'; DROP TABLE pms_parts;--",
        "filter OR 1=1",
        "filter OR 1=1--",
        "filter' OR '1'='1",
        "filter' OR '1'='1'--",
        "SELECT * FROM pms_parts",
        "SELECT * FROM users",
        "name UNION SELECT password FROM users",
        "name UNION ALL SELECT * FROM users",
        "'; DELETE FROM pms_parts WHERE '1'='1",
        "1; UPDATE pms_parts SET name='hacked'",
        "'; TRUNCATE TABLE pms_parts;--",
        "1; INSERT INTO users VALUES('hacker', 'pass');--",
        "'; EXEC xp_cmdshell('dir');--",
        "' AND 1=1--",
        "' AND 1=2--",
        "1' AND SLEEP(5)--",
        "1' WAITFOR DELAY '0:0:5'--",
        "1'; SHUTDOWN--",
        "admin'--",
        "' OR ''='",
        "1' ORDER BY 1--",
        "1' ORDER BY 100--",
        "1' UNION SELECT NULL--",
        "1' UNION SELECT NULL, NULL--",
        "1' UNION SELECT table_name FROM information_schema.tables--",
        "'; DROP DATABASE;--",
        "1; GRANT ALL ON *.* TO 'hacker'@'%';--",
        "/**/UNION/**/SELECT/**/password/**/FROM/**/users",
        "UN%49ON SEL%45CT",
        "' OR EXISTS(SELECT * FROM users)--",
        "'; CALL sys.procedures('shell')--",
    ]

    for i, query in enumerate(injections):
        tests.append(HostileTest(
            id=f"SEC-INJ-{i:03d}",
            query=query,
            category=TestCategory.SECURITY,
            expected=ExpectedBehavior.BLOCKED,
            expected_detail="SQL injection attempt should be blocked",
            difficulty=5,
        ))

    # Legitimate queries that look like SQL (false positive risk) - comprehensive
    false_positives = [
        "manual from engine room",           # 'from' is SQL keyword
        "parts from the supplier",           # 'from' is preposition
        "where is the bilge pump",           # 'where' is question word
        "where is box 2a located",           # 'where' question
        "select the right filter size",      # 'select' is verb
        "how to select the correct part",    # 'select' is verb
        "order by part number",              # could be instruction
        "sort order by size",                # 'order by' is instruction
        "update on generator status",        # 'update' is noun
        "latest update from service",        # 'update' is noun
        "delete old work orders",            # 'delete' is action
        "mark for deletion",                 # 'delete' related
        "union coupling replacement",        # 'union' is part name
        "union fitting for hose",            # 'union' is fitting type
        "offset wrench for alignment",       # 'offset' is tool type
        "offset pump alignment",             # 'offset' is adjustment
        "drop in replacement filter",        # 'drop' is adjective
        "drop test results",                 # 'drop' is noun
        "table mount for radar",             # 'table' is furniture
        "mounting table dimensions",         # 'table' is furniture
        "insert new gasket",                 # 'insert' is verb
        "insert for bearing housing",        # 'insert' is noun
        "index the timing",                  # 'index' is verb
        "index pin location",                # 'index' is noun
        "null and void warranty",            # 'null' in phrase
        "grant access to engine room",       # 'grant' is verb
        "execute the maintenance plan",      # 'execute' is verb
        "truncate the hose to fit",          # 'truncate' is verb
        "join the coupling halves",          # 'join' is verb
        "inner bearing seal",                # 'inner' is adjective
        "outer race inspection",             # 'outer' - not SQL
        "left hand thread",                  # 'left' is direction
        "right hand rotation",               # 'right' is direction
        "having trouble with pump",          # 'having' - colloquial
        "having issues with filter",         # 'having' - colloquial
        "between decks storage",             # 'between' is preposition
        "like for like replacement",         # 'like' is adjective
        "and gate valve",                    # 'and' in part name
        "or gate failure",                   # 'or' in part name
    ]

    for i, query in enumerate(false_positives):
        tests.append(HostileTest(
            id=f"SEC-FP-{i:03d}",
            query=query,
            category=TestCategory.SECURITY,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Legitimate query should NOT be blocked",
            difficulty=4,
            notes="False positive detection"
        ))

    # Yacht ID scope attempts - comprehensive
    scope_tests = [
        "all yachts inventory",
        "show inventory yacht_id=*",
        "parts for yacht 00000000-0000-0000-0000-000000000000",
        "inventory for all vessels",
        "show all yacht data",
        "cross-yacht inventory search",
        "global inventory search",
        "fleet-wide parts search",
        "other yacht parts",
        "yacht_id IS NULL",
        "yacht_id = NULL",
        "yacht_id != current",
        "override yacht filter",
        "bypass yacht restriction",
    ]

    for i, query in enumerate(scope_tests):
        tests.append(HostileTest(
            id=f"SEC-SCOPE-{i:03d}",
            query=query,
            category=TestCategory.SECURITY,
            expected=ExpectedBehavior.BLOCKED,
            expected_detail="Cross-yacht access should be prevented",
            difficulty=5,
        ))

    # Path traversal and command injection
    path_injection = [
        "../../../etc/passwd",
        "file:///etc/passwd",
        "; cat /etc/passwd",
        "| ls -la",
        "$(whoami)",
        "`id`",
        "${PATH}",
        "../../../../windows/system32",
    ]

    for i, query in enumerate(path_injection):
        tests.append(HostileTest(
            id=f"SEC-PATH-{i:03d}",
            query=query,
            category=TestCategory.SECURITY,
            expected=ExpectedBehavior.BLOCKED,
            expected_detail="Path/command injection should be blocked",
            difficulty=5,
        ))

    # XSS-style inputs (should be escaped)
    xss_tests = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
        "{{constructor.constructor('return this')()}}",
    ]

    for i, query in enumerate(xss_tests):
        tests.append(HostileTest(
            id=f"SEC-XSS-{i:03d}",
            query=query,
            category=TestCategory.SECURITY,
            expected=ExpectedBehavior.EMPTY,
            expected_detail="XSS attempt should return empty or be escaped",
            difficulty=4,
        ))

    return tests

# =============================================================================
# CHAOTIC HUMAN PHRASING (500+)
# =============================================================================

def generate_chaotic_tests() -> List[HostileTest]:
    tests = []

    # Typos and misspellings - comprehensive
    typos = [
        ("fule fitler", "fuel filter", "double typo"),
        ("fule filter", "fuel filter", "single typo"),
        ("fuel fitler", "fuel filter", "single typo 2"),
        ("genertor", "generator", "missing letter"),
        ("genreator", "generator", "transposition"),
        ("gnerator", "generator", "transposition 2"),
        ("stearing", "steering", "common misspelling"),
        ("steerin", "steering", "truncation"),
        ("exhuast", "exhaust", "transposition"),
        ("exaust", "exhaust", "missing letter"),
        ("exhast", "exhaust", "missing letter 2"),
        ("engin", "engine", "truncation"),
        ("engien", "engine", "transposition"),
        ("oile", "oil", "extra letter"),
        ("oill", "oil", "double letter"),
        ("pummp", "pump", "double letter"),
        ("pmp", "pump", "missing vowels"),
        ("fiter", "filter", "missing letter"),
        ("filtre", "filter", "transposition"),
        ("fliter", "filter", "transposition 2"),
        ("mantenance", "maintenance", "misspelling"),
        ("maintnance", "maintenance", "missing letter"),
        ("maintenace", "maintenance", "missing letter 2"),
        ("hydraulc", "hydraulic", "missing letter"),
        ("hydralic", "hydraulic", "missing letter 2"),
        ("hydrolics", "hydraulic", "wrong vowel"),
        ("elecrical", "electrical", "missing letter"),
        ("eletrical", "electrical", "transposition"),
        ("coolant", "coolant", "correct - baseline"),
        ("coollant", "coolant", "double letter"),
        ("colant", "coolant", "missing letter"),
        ("impeler", "impeller", "missing letter"),
        ("impellor", "impeller", "wrong ending"),
        ("thermastat", "thermostat", "missing letter"),
        ("thermstat", "thermostat", "missing vowel"),
        ("alterntor", "alternator", "missing vowel"),
        ("alternatr", "alternator", "missing vowel 2"),
        ("compresser", "compressor", "wrong ending"),
        ("comprsor", "compressor", "missing letters"),
        ("gaskit", "gasket", "wrong vowel"),
        ("gasekt", "gasket", "transposition"),
        ("seel", "seal", "wrong vowel"),
        ("seall", "seal", "double letter"),
        ("beering", "bearing", "wrong vowel"),
        ("bearng", "bearing", "missing letter"),
    ]

    for i, (typo, correct, notes) in enumerate(typos):
        tests.append(HostileTest(
            id=f"CHAOS-TYPO-{i:03d}",
            query=typo,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Typo '{typo}' should fuzzy match to '{correct}'",
            difficulty=3,
            notes=notes
        ))

    # Voice dictation garbage - comprehensive
    voice_tests = [
        "show me um the oil filter",
        "where's the uh fuel pump",
        "i need the the generator parts",
        "can you find me find the manual",
        "what's the what's the status",
        "ok so basically the engine filter",
        "like, the oil filter thing",
        "you know the uh main engine",
        "so like where is the, the filter",
        "um yeah the generator",
        "hey can you um show me pumps",
        "i guess the fuel pump or whatever",
        "basically i need uh work orders",
        "the thing for the um engine",
        "so yeah pending stuff",
        "what about like maintenance",
        "kinda need the filter",
        "sorta looking for oil",
    ]

    for i, query in enumerate(voice_tests):
        tests.append(HostileTest(
            id=f"CHAOS-VOICE-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Voice dictation artifacts should not break search",
            difficulty=4,
        ))

    # Spacing variants - comprehensive
    spacing = [
        "oilfilter",
        "oil  filter",
        "oil   filter",
        " oil filter ",
        "oil\tfilter",
        "fuel  pump",
        "fuelpump",
        "main  engine",
        "mainengine",
        "work orders",
        "workorders",
        "work  orders",
        "   filter   ",
        "\toil\t",
    ]

    for i, query in enumerate(spacing):
        tests.append(HostileTest(
            id=f"CHAOS-SPACE-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Spacing variants should normalize",
            difficulty=2,
        ))

    # Mixed case - comprehensive
    case_tests = [
        "OIL FILTER",
        "Oil Filter",
        "oIL fILTER",
        "oiL FiLtEr",
        "FUEL PUMP",
        "Fuel Pump",
        "fUEL pUMP",
        "GENERATOR",
        "Generator",
        "geNeRaToR",
        "MAIN ENGINE",
        "Main Engine",
        "mAiN eNgInE",
        "ME-S-001",
        "me-s-001",
        "Me-S-001",
        "mE-s-001",
    ]

    for i, query in enumerate(case_tests):
        tests.append(HostileTest(
            id=f"CHAOS-CASE-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Case should be ignored",
            difficulty=1,
        ))

    # Shorthand and abbreviations - comprehensive
    shorthand = [
        ("oos parts", "out of stock parts"),
        ("oos", "out of stock"),
        ("wo for ME", "work orders for main engine"),
        ("wo ME-S-001", "work orders for ME-S-001"),
        ("wo gen", "work orders for generator"),
        ("inv box 2d", "inventory in box 2d"),
        ("inv 2a", "inventory in 2a"),
        ("gen maint", "generator maintenance"),
        ("eng rm", "engine room"),
        ("e/r", "engine room"),
        ("maint sched", "maintenance schedule"),
        ("pend wo", "pending work orders"),
        ("comp wo", "completed work orders"),
        ("crit wo", "critical work orders"),
        ("hyd pump", "hydraulic pump"),
        ("elec panel", "electrical panel"),
        ("nav equip", "navigation equipment"),
        ("a/c", "air conditioning"),
        ("fw", "fresh water"),
        ("sw", "sea water"),
        ("s/b", "starboard"),
        ("p/s", "port side"),
    ]

    for i, (short, full) in enumerate(shorthand):
        tests.append(HostileTest(
            id=f"CHAOS-SHORT-{i:03d}",
            query=short,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Shorthand '{short}' should find results like '{full}'",
            difficulty=4,
        ))

    # Partial identifiers - comprehensive
    partial = [
        ("ME-S", "partial equipment code"),
        ("ME-P", "partial equipment code variant"),
        ("GEN", "equipment prefix"),
        ("ENG-", "partial part prefix"),
        ("ENG-0008", "partial part number"),
        ("E0", "partial fault code"),
        ("E04", "partial fault code 2"),
        ("BOX-2", "partial location"),
        ("BOX", "location type only"),
        ("LOCKER", "location type only"),
        ("DECK", "location type only"),
        ("0008", "numeric part only"),
        ("001", "short number"),
    ]

    for i, (query, notes) in enumerate(partial):
        tests.append(HostileTest(
            id=f"CHAOS-PARTIAL-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Partial ID should find matches",
            difficulty=3,
            notes=notes
        ))

    # Natural language questions
    questions = [
        "what oil filters do we have",
        "where are the fuel filters stored",
        "how many pumps are in stock",
        "which generators need maintenance",
        "when was the last oil change",
        "who created work order 1234",
        "why is the generator flagged",
        "is there any coolant left",
        "are the filters in stock",
        "do we have spare impellers",
        "can I see the inventory",
        "show me everything in box 2a",
        "list all pending work orders",
        "find the main engine filter",
        "get status of generator",
    ]

    for i, query in enumerate(questions):
        tests.append(HostileTest(
            id=f"CHAOS-QUESTION-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Natural language question should extract entities",
            difficulty=3,
        ))

    # Compound terms - expanded
    compound_terms = [
        "main engine oil filter",
        "port generator fuel pump",
        "starboard thruster impeller",
        "auxiliary generator coolant",
        "fresh water pump seal",
        "sea water strainer",
        "hydraulic steering pump",
        "bow thruster motor",
        "stern tube seal",
        "anchor windlass motor",
        "bilge pump float switch",
        "air conditioning compressor",
        "reverse osmosis membrane",
        "fuel day tank",
        "lube oil cooler",
    ]

    for i, query in enumerate(compound_terms):
        tests.append(HostileTest(
            id=f"CHAOS-COMPOUND-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Multi-word compound term should match",
            difficulty=3,
        ))

    return tests

# =============================================================================
# NEGATIVE TESTS (correct answer is empty) (200+)
# =============================================================================

def generate_negative_tests() -> List[HostileTest]:
    tests = []

    # Non-existent IDs - comprehensive
    nonexistent = [
        "work orders for ME-Z-999",
        "work orders for ME-X-001",
        "work orders for ABC-999",
        "part XYZ-9999-999",
        "part AAA-0000-000",
        "part ZZZ-1111-111",
        "fault code Z999",
        "fault code X000",
        "fault code Q123",
        "inventory in BOX-99Z",
        "inventory in BOX-99",
        "inventory in LOCKER-99",
        "inventory in DECK-99",
        "equipment FAKE-001",
        "equipment NOTREAL-002",
        "serial number SN000000000",
        "serial number SNFAKE123",
    ]

    for i, query in enumerate(nonexistent):
        tests.append(HostileTest(
            id=f"NEG-NOEXIST-{i:03d}",
            query=query,
            category=TestCategory.NEGATIVE,
            expected=ExpectedBehavior.EMPTY,
            expected_detail="Non-existent ID should return empty, not hallucinate",
            difficulty=2,
        ))

    # Impossible combinations
    impossible = [
        "out of stock inventory in BOX-2C",  # BOX-2C has no OOS items
        "completed pending work orders",      # Contradictory status
        "critical routine priority tasks",    # Contradictory priority
        "in progress completed tasks",        # Contradictory
        "pending completed status",           # Contradictory
        "quantity 0 with quantity 10",        # Numeric contradiction
        "stock level above 100 below 5",      # Range contradiction
    ]

    for i, query in enumerate(impossible):
        tests.append(HostileTest(
            id=f"NEG-IMPOSSIBLE-{i:03d}",
            query=query,
            category=TestCategory.NEGATIVE,
            expected=ExpectedBehavior.EMPTY,
            expected_detail="Impossible constraint combination should return empty",
            difficulty=3,
        ))

    # Very specific non-matches - expanded
    specific_nomatch = [
        "purple unicorn generator",
        "quantum flux capacitor filter",
        "warp drive maintenance schedule",
        "dilithium crystal inventory",
        "flux compensator parts",
        "hyperdrive motor",
        "teleporter maintenance",
        "time machine parts",
        "antigravity pump",
        "phaser array filter",
        "tractor beam motor",
        "cloaking device",
        "replicator parts",
        "holodeck maintenance",
    ]

    for i, query in enumerate(specific_nomatch):
        tests.append(HostileTest(
            id=f"NEG-FANTASY-{i:03d}",
            query=query,
            category=TestCategory.NEGATIVE,
            expected=ExpectedBehavior.EMPTY,
            expected_detail="Fantasy items should return empty, not partial matches",
            difficulty=2,
        ))

    # Nonsense queries that should return empty
    nonsense = [
        "asdfasdfasdf",
        "qwerty12345",
        "zzzzzzzzzzz",
        "!@#$%^&*()",
        "///\\\\///",
        "123 456 789",
        "abc xyz 123",
        "   ",
        "\t\t\t",
        "~`~`~`~",
    ]

    for i, query in enumerate(nonsense):
        tests.append(HostileTest(
            id=f"NEG-NONSENSE-{i:03d}",
            query=query,
            category=TestCategory.NEGATIVE,
            expected=ExpectedBehavior.EMPTY,
            expected_detail="Nonsense query should return empty gracefully",
            difficulty=1,
        ))

    # Overly specific queries that won't match
    overspecific = [
        "blue titanium oil filter model 7b revision 3",
        "german-made zinc-plated fuel pump with ceramic bearings",
        "2019 model generator impeller with anti-corrosion coating",
        "marine-grade stainless steel coolant hose 50mm diameter",
        "caterpillar part number CAT-999-XYZ-SPECIAL",
    ]

    for i, query in enumerate(overspecific):
        tests.append(HostileTest(
            id=f"NEG-OVERSPEC-{i:03d}",
            query=query,
            category=TestCategory.NEGATIVE,
            expected=ExpectedBehavior.EMPTY,
            expected_detail="Overly specific query unlikely to match should return empty",
            difficulty=3,
        ))

    return tests

# =============================================================================
# COMPOUND TESTS (multi-constraint) (300+)
# =============================================================================

def generate_compound_tests() -> List[HostileTest]:
    tests = []

    # 3+ constraint combinations - comprehensive
    compounds = [
        ("pending work orders for ME-S-001 due this week", "status + equipment + temporal"),
        ("pending work orders for ME-P-001 this month", "status + equipment + temporal variant"),
        ("out of stock filters in box 2a", "quantity + name + location"),
        ("out of stock oil filters in engine room", "quantity + name + location variant"),
        ("low stock parts in box 2d", "quantity + type + location"),
        ("critical maintenance for generator completed", "priority + object + equipment + status"),
        ("high temperature faults on main engine port", "symptom + equipment + side"),
        ("overheating issues on ME-S-001 starboard", "symptom + equipment + side variant"),
        ("fuel filter stock level box 2a", "part + metric + location"),
        ("pending generator service schedule", "status + equipment + type"),
        ("critical overdue work orders for engine", "priority + temporal + equipment"),
        ("completed tasks for HVAC this week", "status + equipment + temporal"),
        ("in progress maintenance main engine oil", "status + equipment + fluid"),
        ("low stock impellers for water pumps", "quantity + part + equipment type"),
        ("pending fault E047 resolution", "status + fault"),
        ("critical pending tasks generator room", "priority + status + location"),
        ("out of stock fuel filters for generator", "quantity + part + equipment"),
        ("completed in progress pending tasks", "multiple status - should handle gracefully"),
    ]

    for i, (query, detail) in enumerate(compounds):
        tests.append(HostileTest(
            id=f"COMP-3PLUS-{i:03d}",
            query=query,
            category=TestCategory.COMPOUND,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Compound query: {detail}",
            difficulty=4,
        ))

    # Entity soup (multiple entities, ambiguous routing) - expanded
    soup = [
        "E047 ME-S-001 fuel filter",          # fault + equipment + part
        "GEN-002 oil filter BOX-2A",          # equipment + part + location
        "pending E001 generator maintenance", # status + fault + object
        "ME-P-001 ENG-0008-103 BOX-2D",       # equipment + part + location
        "E047 E001 main engine",              # multiple faults + equipment
        "generator HVAC thruster",            # multiple equipment
        "oil filter fuel filter coolant",     # multiple parts
        "BOX-2A BOX-2D LOCKER-3B",            # multiple locations
        "pending completed in progress",      # multiple statuses
        "ME-S-001 GEN-002 THR-B-001",         # multiple equipment codes
        "ENG-0008-103 PMP-0018-280",          # multiple part numbers
        "filter pump impeller seal",          # multiple part types
        "engine generator thruster auxiliary",# multiple systems
    ]

    for i, query in enumerate(soup):
        tests.append(HostileTest(
            id=f"COMP-SOUP-{i:03d}",
            query=query,
            category=TestCategory.COMPOUND,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Entity soup - multiple entity types in one query",
            difficulty=5,
        ))

    # Cross-domain queries
    cross_domain = [
        "work orders with related parts in stock",
        "equipment with open faults",
        "parts needed for pending maintenance",
        "inventory for equipment with overdue service",
        "suppliers for out of stock items",
        "faults related to low stock parts",
        "maintenance history with part consumption",
        "equipment in engine room with pending work",
    ]

    for i, query in enumerate(cross_domain):
        tests.append(HostileTest(
            id=f"COMP-CROSS-{i:03d}",
            query=query,
            category=TestCategory.COMPOUND,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Cross-domain query spanning multiple tables",
            difficulty=5,
        ))

    # Complex natural language compounds
    natural_compound = [
        "show me all the oil filters that are out of stock in box 2a",
        "find pending work orders for the main engine generator system",
        "what critical maintenance tasks are overdue for HVAC",
        "list parts running low in the engine room storage",
        "get all faults reported on the starboard thruster this month",
        "which equipment needs service based on runtime hours",
        "display inventory items that need reordering soon",
        "show maintenance history for all generators last quarter",
    ]

    for i, query in enumerate(natural_compound):
        tests.append(HostileTest(
            id=f"COMP-NATURAL-{i:03d}",
            query=query,
            category=TestCategory.COMPOUND,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail="Natural language compound query",
            difficulty=4,
        ))

    return tests

# =============================================================================
# PROGRAMMATIC EXPANSION (700+)
# =============================================================================

def generate_expansion_tests() -> List[HostileTest]:
    """Programmatically generate additional test variations."""
    tests = []

    # Part names to test
    part_names = [
        "oil filter", "fuel filter", "air filter", "coolant filter",
        "fuel pump", "water pump", "oil pump", "hydraulic pump",
        "impeller", "thermostat", "gasket", "seal", "bearing",
        "belt", "hose", "valve", "alternator", "starter",
    ]

    # Equipment names
    equipment_names = [
        "main engine", "generator", "thruster", "stabilizer",
        "HVAC", "watermaker", "compressor", "radar", "autopilot",
    ]

    # Locations
    locations = [
        "box 2a", "box 2b", "box 2c", "box 2d", "box 4a",
        "locker 3b", "deck 1", "deck 2", "engine room", "bridge",
    ]

    # Statuses
    statuses = ["pending", "in progress", "completed", "planned"]

    # Priorities
    priorities = ["critical", "routine"]

    # Generate part + location combinations
    for i, part in enumerate(part_names):
        for j, loc in enumerate(locations[:5]):  # Limit combinations
            tests.append(HostileTest(
                id=f"EXP-PARTLOC-{i:03d}-{j:02d}",
                query=f"{part} in {loc}",
                category=TestCategory.COMPOUND,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Part + location: {part} in {loc}",
                difficulty=3,
            ))

    # Generate equipment + status combinations
    for i, eq in enumerate(equipment_names):
        for j, status in enumerate(statuses):
            tests.append(HostileTest(
                id=f"EXP-EQSTAT-{i:03d}-{j:02d}",
                query=f"{status} work orders for {eq}",
                category=TestCategory.FILTER_STACK,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Equipment + status filter",
                difficulty=3,
            ))

    # Generate status + priority combinations
    for i, status in enumerate(statuses):
        for j, priority in enumerate(priorities):
            tests.append(HostileTest(
                id=f"EXP-STATPRI-{i:03d}-{j:02d}",
                query=f"{priority} {status} work orders",
                category=TestCategory.FILTER_STACK,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Status + priority combination",
                difficulty=3,
            ))

    # Generate typo variants for common parts
    typo_map = {}
    typo_map["filter"] = ["fitler", "fiter", "filtre", "fliter", "filtter"]
    typo_map["pump"] = ["pummp", "pmp", "pupm", "pumb"]
    typo_map["generator"] = ["genertor", "genreator", "gnerator", "generater"]
    typo_map["engine"] = ["engin", "engien", "engne", "egnine"]
    typo_map["oil"] = ["oile", "oill", "iol"]
    typo_map["fuel"] = ["fule", "feul", "fuell"]
    typo_map["water"] = ["watter", "weter", "watr"]
    typo_map["hydraulic"] = ["hydraulc", "hydralic", "hydrolics", "hydrolic"]

    for correct, typos in typo_map.items():
        for i, typo in enumerate(typos):
            tests.append(HostileTest(
                id=f"EXP-TYPO-{correct[:4].upper()}-{i:02d}",
                query=typo,
                category=TestCategory.CHAOTIC,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Typo '{typo}' should find '{correct}'",
                difficulty=3,
            ))

    # Generate equipment code variants
    eq_codes = ["ME-S-001", "ME-P-001", "GEN-001", "GEN-002", "HVAC-001",
                "THR-B-001", "THR-S-001", "AUX-001", "DG1", "DG2"]

    variant_patterns = [
        lambda c: c.lower(),
        lambda c: c.replace("-", " "),
        lambda c: c.replace("-", ""),
        lambda c: c.lower().replace("-", " "),
        lambda c: c.lower().replace("-", ""),
    ]

    for i, code in enumerate(eq_codes):
        for j, pattern in enumerate(variant_patterns):
            variant = pattern(code)
            if variant != code:
                tests.append(HostileTest(
                    id=f"EXP-EQVAR-{i:03d}-{j:02d}",
                    query=f"work orders for {variant}",
                    category=TestCategory.CANONICAL,
                    expected=ExpectedBehavior.HAS_RESULTS,
                    expected_detail=f"Equipment code variant: {variant} -> {code}",
                    difficulty=2,
                ))

    # Generate fault code variants
    fault_codes = ["E047", "E001", "E002", "E003", "G012", "G001", "F001", "H001"]

    for i, code in enumerate(fault_codes):
        variants = [
            code.lower(),
            code[0] + " " + code[1:],
            code[0] + "-" + code[1:],
            f"fault {code}",
            f"error {code.lower()}",
            f"alarm {code}",
        ]
        for j, variant in enumerate(variants):
            if variant != code:
                tests.append(HostileTest(
                    id=f"EXP-FTVAR-{i:03d}-{j:02d}",
                    query=f"diagnose {variant}",
                    category=TestCategory.CANONICAL,
                    expected=ExpectedBehavior.HAS_RESULTS,
                    expected_detail=f"Fault code variant: {variant} -> {code}",
                    difficulty=2,
                ))

    # Generate natural language query variations
    query_templates = [
        "show me {item}",
        "find {item}",
        "get {item}",
        "list {item}",
        "search for {item}",
        "looking for {item}",
        "need {item}",
        "where is {item}",
        "locate {item}",
        "display {item}",
    ]

    items = ["oil filter", "fuel pump", "generator", "pending work orders",
             "out of stock parts", "main engine", "inventory"]

    for i, template in enumerate(query_templates):
        for j, item in enumerate(items):
            tests.append(HostileTest(
                id=f"EXP-TEMPL-{i:03d}-{j:02d}",
                query=template.format(item=item),
                category=TestCategory.CHAOTIC,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Template query: {template}",
                difficulty=2,
            ))

    # Generate cross-entity queries
    entities_a = ["ME-S-001", "GEN-002", "generator", "main engine"]
    entities_b = ["oil filter", "fuel filter", "pending", "E047"]

    for i, a in enumerate(entities_a):
        for j, b in enumerate(entities_b):
            tests.append(HostileTest(
                id=f"EXP-CROSS-{i:03d}-{j:02d}",
                query=f"{a} {b}",
                category=TestCategory.COMPOUND,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Cross-entity: {a} + {b}",
                difficulty=4,
            ))

    # Additional part name variations with actions
    actions = ["find", "show", "get", "list", "locate", "check", "search"]
    parts = ["filter", "pump", "seal", "gasket", "bearing", "impeller",
             "hose", "belt", "valve", "thermostat"]

    for i, action in enumerate(actions):
        for j, part in enumerate(parts):
            tests.append(HostileTest(
                id=f"EXP-ACT-{i:03d}-{j:02d}",
                query=f"{action} {part}",
                category=TestCategory.CHAOTIC,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Action + part: {action} {part}",
                difficulty=2,
            ))

    # More equipment code variations with different contexts
    contexts = ["maintenance for", "status of", "history of", "parts for", "faults on"]
    eq_names = ["main engine", "generator", "thruster", "HVAC", "watermaker",
                "stabilizer", "compressor", "bow thruster", "stern thruster"]

    for i, ctx in enumerate(contexts):
        for j, eq in enumerate(eq_names):
            tests.append(HostileTest(
                id=f"EXP-CTX-{i:03d}-{j:02d}",
                query=f"{ctx} {eq}",
                category=TestCategory.CROSS_TABLE,
                expected=ExpectedBehavior.HAS_RESULTS,
                expected_detail=f"Context + equipment: {ctx} {eq}",
                difficulty=3,
            ))

    # Quantity-based queries
    qty_queries = [
        "how many oil filters",
        "how many fuel pumps",
        "how many impellers in stock",
        "count of filters",
        "total pumps",
        "quantity of seals",
        "number of gaskets",
        "stock count bearings",
        "inventory count hoses",
        "available belts",
    ]

    for i, query in enumerate(qty_queries):
        tests.append(HostileTest(
            id=f"EXP-QTY-{i:03d}",
            query=query,
            category=TestCategory.FILTER_STACK,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Quantity query",
            difficulty=3,
        ))

    # Question-form variations
    questions = [
        "what filters do we have",
        "what parts are out of stock",
        "what work orders are pending",
        "what equipment needs service",
        "what faults are reported",
        "which pumps need replacement",
        "which items need reorder",
        "which tasks are overdue",
        "when was last service ME-S-001",
        "when is next maintenance generator",
        "who created this work order",
        "why is generator flagged",
        "is oil filter in stock",
        "is there any coolant left",
        "are there pending tasks",
        "are filters available",
        "can I see inventory",
        "can you find fuel pump",
        "could you show me work orders",
        "would you list pending tasks",
    ]

    for i, query in enumerate(questions):
        tests.append(HostileTest(
            id=f"EXP-QUES-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Question form query",
            difficulty=3,
        ))

    # More location combinations
    loc_queries = []
    locs = ["box 2a", "box 2b", "box 2c", "box 2d", "locker 3b", "deck 1", "engine room"]
    for loc in locs:
        loc_queries.extend([
            f"parts in {loc}",
            f"inventory {loc}",
            f"what's in {loc}",
            f"items stored in {loc}",
            f"equipment in {loc}",
        ])

    for i, query in enumerate(loc_queries):
        tests.append(HostileTest(
            id=f"EXP-LOC-{i:03d}",
            query=query,
            category=TestCategory.COMPOUND,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Location query",
            difficulty=2,
        ))

    # More symptom/diagnosis queries
    symptoms = ["overheating", "vibration", "noise", "leak", "smoke", "alarm",
                "warning", "fault", "error", "failure"]

    for i, symptom in enumerate(symptoms):
        tests.append(HostileTest(
            id=f"EXP-SYM-{i:03d}",
            query=f"diagnose {symptom}",
            category=TestCategory.CROSS_TABLE,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Symptom diagnosis: {symptom}",
            difficulty=4,
        ))
        tests.append(HostileTest(
            id=f"EXP-SYM-{i:03d}b",
            query=f"{symptom} on main engine",
            category=TestCategory.COMPOUND,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Symptom + equipment: {symptom}",
            difficulty=4,
        ))

    # Additional work order status combinations
    wo_queries = []
    wo_statuses = ["pending", "planned", "in progress", "completed"]
    wo_priorities = ["critical", "routine"]
    wo_equipment = ["ME-S-001", "GEN-002", "HVAC-001", "main engine", "generator"]

    for status in wo_statuses:
        for eq in wo_equipment:
            wo_queries.append(f"{status} work orders {eq}")

    for priority in wo_priorities:
        for eq in wo_equipment:
            wo_queries.append(f"{priority} maintenance {eq}")

    for i, query in enumerate(wo_queries):
        tests.append(HostileTest(
            id=f"EXP-WO-{i:03d}",
            query=query,
            category=TestCategory.FILTER_STACK,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Work order combination",
            difficulty=3,
        ))

    # Manufacturer variations
    manufacturers = ["MTU", "Caterpillar", "Volvo", "MAN", "Yanmar", "Cummins"]
    for i, mfg in enumerate(manufacturers):
        tests.append(HostileTest(
            id=f"EXP-MFG-{i:03d}",
            query=f"parts from {mfg}",
            category=TestCategory.CROSS_TABLE,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Manufacturer search: {mfg}",
            difficulty=3,
        ))
        tests.append(HostileTest(
            id=f"EXP-MFG-{i:03d}b",
            query=f"{mfg} filters",
            category=TestCategory.COMPOUND,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Manufacturer + part",
            difficulty=3,
        ))

    # System/category searches
    systems = ["propulsion", "electrical", "hydraulic", "HVAC", "navigation",
               "deck", "safety", "communication"]
    for i, sys in enumerate(systems):
        tests.append(HostileTest(
            id=f"EXP-SYS-{i:03d}",
            query=f"{sys} system parts",
            category=TestCategory.COMPOUND,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"System search: {sys}",
            difficulty=3,
        ))
        tests.append(HostileTest(
            id=f"EXP-SYS-{i:03d}b",
            query=f"{sys} equipment",
            category=TestCategory.CROSS_TABLE,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"System equipment",
            difficulty=3,
        ))

    # Date/time based queries
    date_queries = [
        "work orders this week",
        "maintenance this month",
        "overdue tasks",
        "upcoming service",
        "recent completions",
        "work orders today",
        "tasks due tomorrow",
        "last week maintenance",
        "next month scheduled",
        "old work orders",
    ]
    for i, query in enumerate(date_queries):
        tests.append(HostileTest(
            id=f"EXP-DATE-{i:03d}",
            query=query,
            category=TestCategory.FILTER_STACK,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Temporal query",
            difficulty=4,
        ))

    # Plural/singular variations
    plurals = [
        ("filter", "filters"),
        ("pump", "pumps"),
        ("seal", "seals"),
        ("gasket", "gaskets"),
        ("bearing", "bearings"),
        ("impeller", "impellers"),
        ("hose", "hoses"),
        ("belt", "belts"),
        ("generator", "generators"),
        ("engine", "engines"),
    ]
    for i, (singular, plural) in enumerate(plurals):
        tests.append(HostileTest(
            id=f"EXP-PLUR-{i:03d}a",
            query=singular,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Singular form: {singular}",
            difficulty=1,
        ))
        tests.append(HostileTest(
            id=f"EXP-PLUR-{i:03d}b",
            query=plural,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Plural form: {plural}",
            difficulty=1,
        ))

    # Possessive/ownership queries
    ownership = [
        "my work orders",
        "my pending tasks",
        "our inventory",
        "the yacht inventory",
        "vessel parts",
        "ship equipment",
        "boat filters",
        "yacht work orders",
    ]
    for i, query in enumerate(ownership):
        tests.append(HostileTest(
            id=f"EXP-OWN-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Ownership query",
            difficulty=2,
        ))

    # Special characters in queries
    special = [
        "oil/fuel filter",
        "pump & motor",
        "seal - o-ring",
        "filter (oil)",
        "pump #1",
        "filter type: oil",
        "seal; rubber",
        "filter, oil",
    ]
    for i, query in enumerate(special):
        tests.append(HostileTest(
            id=f"EXP-SPEC-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Special character handling",
            difficulty=3,
        ))

    # Common nautical abbreviations
    nautical = [
        "P/S parts",   # port/starboard
        "FWD pump",    # forward
        "AFT seal",    # aft
        "STBD engine", # starboard
        "PT motor",    # port
        "E/R filter",  # engine room
        "M/E parts",   # main engine
        "A/E generator", # auxiliary engine
        "S/W pump",    # sea water
        "F/W system",  # fresh water
    ]
    for i, query in enumerate(nautical):
        tests.append(HostileTest(
            id=f"EXP-NAUT-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Nautical abbreviation: {query}",
            difficulty=4,
        ))

    # Final expansion - common search phrases
    common_phrases = [
        "show all", "list everything", "all parts", "all equipment",
        "everything", "full inventory", "complete list", "all work orders",
        "entire stock", "all items", "all filters", "all pumps",
        "all pending", "all completed", "all in progress", "all overdue",
        "summary", "overview", "status report", "inventory report",
        "all for ME-S-001", "everything for generator", "all maintenance",
        "stock status", "reorder list", "low stock", "needs attention",
        "urgent items", "priority tasks", "immediate action", "critical items",
        "review needed", "attention required", "flagged items", "warnings",
        "alerts", "notifications", "reminders", "scheduled tasks",
        "this yacht", "current vessel", "on board", "installed parts",
    ]
    for i, query in enumerate(common_phrases):
        tests.append(HostileTest(
            id=f"EXP-PHRASE-{i:03d}",
            query=query,
            category=TestCategory.CHAOTIC,
            expected=ExpectedBehavior.HAS_RESULTS,
            expected_detail=f"Common search phrase",
            difficulty=2,
        ))

    return tests


# =============================================================================
# MAIN GENERATOR
# =============================================================================

def generate_all_tests() -> List[HostileTest]:
    """Generate all hostile tests."""
    all_tests = []

    generators = [
        ("canonical", generate_canonical_tests),
        ("filter", generate_filter_tests),
        ("cross_table", generate_cross_table_tests),
        ("ranking", generate_ranking_tests),
        ("security", generate_security_tests),
        ("chaotic", generate_chaotic_tests),
        ("negative", generate_negative_tests),
        ("compound", generate_compound_tests),
        ("expansion", generate_expansion_tests),
    ]

    for name, gen_func in generators:
        tests = gen_func()
        all_tests.extend(tests)
        print(f"Generated {len(tests)} {name} tests")

    print(f"\nTotal tests generated: {len(all_tests)}")
    return all_tests

def save_tests(tests: List[HostileTest], path: str):
    """Save tests to JSONL file."""
    with open(path, 'w') as f:
        for test in tests:
            f.write(json.dumps(asdict(test)) + '\n')
    print(f"Saved to {path}")

if __name__ == "__main__":
    tests = generate_all_tests()
    save_tests(tests, "/Users/celeste7/Documents/Cloud_PMS/tests/sql_campaign/hostile_tests.jsonl")

    # Summary by category
    from collections import Counter
    cats = Counter(t.category for t in tests)
    print("\nBy category:")
    for cat, count in cats.most_common():
        print(f"  {cat.value}: {count}")

    # Summary by difficulty
    diffs = Counter(t.difficulty for t in tests)
    print("\nBy difficulty:")
    for diff in sorted(diffs.keys()):
        print(f"  Level {diff}: {diffs[diff]}")
