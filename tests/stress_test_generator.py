#!/usr/bin/env python3
"""
Stress Test Generator: Matrix-Based Test Payload Creation
==========================================================

Generates comprehensive test payloads covering:
- All lanes (BLOCKED/NO_LLM/RULES_ONLY/GPT)
- All intent strengths (high/medium/low confidence)
- All entity types
- Canonical vs non-canonical values
- Weight variations (0-5)
- Multi-entity conflicts
- Temporal phrases
- Spelling noise, shorthand, casing
- Negative controls
- Adversarial cases
- Concurrency burst tests
"""

import random
import uuid
import itertools
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import json

from stress_test_config import (
    ACTION_REGISTRY, ENTITY_TYPES, LANES, LANE_CAPABILITIES,
    TEST_YACHT_IDS, MIN_TOTAL_CALLS, MIN_PER_LANE
)


# =============================================================================
# TEST CASE CATEGORIES
# =============================================================================

class TestCategory(Enum):
    # Lane-specific
    BLOCKED_PASTE_DUMP = "blocked_paste_dump"
    BLOCKED_TOO_VAGUE = "blocked_too_vague"
    BLOCKED_NON_DOMAIN = "blocked_non_domain"
    NO_LLM_DIRECT_LOOKUP = "no_llm_direct_lookup"
    NO_LLM_BRAND_MODEL = "no_llm_brand_model"
    NO_LLM_CODE_PATTERN = "no_llm_code_pattern"
    RULES_ONLY_COMMAND = "rules_only_command"
    RULES_ONLY_WITH_TARGET = "rules_only_with_target"
    GPT_DIAGNOSTIC = "gpt_diagnostic"
    GPT_TEMPORAL = "gpt_temporal"
    GPT_COMPLEX = "gpt_complex"

    # Entity variations
    MULTI_ENTITY = "multi_entity"
    CONFLICTING_ENTITIES = "conflicting_entities"
    HIGH_WEIGHT_WRONG_TABLE = "high_weight_wrong_table"

    # Noise/variations
    SPELLING_NOISE = "spelling_noise"
    VOICE_DICTATION = "voice_dictation"
    SHORTHAND = "shorthand"
    CASING_VARIATIONS = "casing_variations"

    # Edge cases
    NEGATIVE_CONTROL = "negative_control"
    ADVERSARIAL_BOUNDARY = "adversarial_boundary"
    EMPTY_ENTITIES = "empty_entities"

    # Concurrency
    BURST_TEST = "burst_test"


@dataclass
class TestPayload:
    """A single test payload with expected outcomes."""
    query: str
    category: TestCategory
    expected_lane: str
    expected_intent: Optional[str] = None
    entities: List[Dict] = field(default_factory=list)
    yacht_id: str = TEST_YACHT_IDS[0]
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stream_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Expected validation criteria
    should_have_embedding: bool = False
    forbidden_search_types: List[str] = field(default_factory=list)
    expected_actions: List[str] = field(default_factory=list)

    # Metadata
    description: str = ""

    def to_request_body(self) -> Dict:
        """Convert to HTTP request body."""
        return {
            "query": self.query,
            "session_id": self.session_id,
            "include_embedding": True,
            "include_metadata": True,
        }


# =============================================================================
# QUERY TEMPLATES BY LANE
# =============================================================================

BLOCKED_QUERIES = {
    "paste_dump": [
        # Code pastes (> 50 words or code patterns)
        "SELECT * FROM users WHERE id = 1; DROP TABLE users; -- injection test with lots of words to make it really long and hit the threshold for blocking",
        "import os\nimport sys\ndef main():\n    print('hello')\n    for i in range(100):\n        process(i)\n        handle_errors()\n    return 0",
        "curl -X POST https://api.example.com/data -H 'Content-Type: application/json' -d '{\"key\": \"value\", \"nested\": {\"deep\": \"data\"}}' && echo 'done'",
        "Traceback (most recent call last):\n  File \"test.py\", line 10, in <module>\n    raise ValueError(\"test error\")\nValueError: test error",
        "<?xml version=\"1.0\"?><root><node>data</node><node>more data</node></root>",
    ],
    "too_vague": [
        "help",
        "hi",
        "?",
        "show",
        "what",
        "um",
    ],
    "non_domain": [
        "what is the capital of France",
        "tell me a joke",
        "what's the weather tomorrow",
        "who won the world cup",
        "calculate 2 + 2",
        "translate hello to Spanish",
        "what time is it",
        "how are you today",
    ],
}

NO_LLM_QUERIES = {
    "direct_lookup": [
        ("WO-1234", "find_work_order", [{"type": "work_order", "value": "WO-1234", "weight": 5.0}]),
        ("wo 5678", "find_work_order", [{"type": "work_order", "value": "WO-5678", "weight": 5.0}]),
        ("E047", "diagnose_fault", [{"type": "fault_code", "value": "E047", "weight": 5.0}]),
        ("error E123", "diagnose_fault", [{"type": "fault_code", "value": "E123", "weight": 5.0}]),
        ("SPN 100 FMI 3", "diagnose_fault", [{"type": "fault_code", "value": "SPN100FMI3", "weight": 5.0}]),
        ("ME1", "view_equipment_details", [{"type": "equipment", "value": "ME1", "canonical": "MAIN_ENGINE_1", "weight": 4.0}]),
        ("DG2", "view_equipment_details", [{"type": "equipment", "value": "DG2", "canonical": "DIESEL_GENERATOR_2", "weight": 4.0}]),
        ("port main", "view_equipment_details", [{"type": "equipment", "value": "port main", "canonical": "PORT_MAIN_ENGINE", "weight": 4.0}]),
    ],
    "brand_model": [
        ("Caterpillar C32", "find_equipment", [{"type": "brand", "value": "Caterpillar", "canonical": "CATERPILLAR", "weight": 3.0}, {"type": "model", "value": "C32", "weight": 3.0}]),
        ("MTU 2000", "find_equipment", [{"type": "brand", "value": "MTU", "canonical": "MTU", "weight": 3.0}, {"type": "model", "value": "2000", "weight": 2.5}]),
        ("seakeeper", "find_equipment", [{"type": "brand", "value": "Seakeeper", "canonical": "SEAKEEPER", "weight": 3.5}]),
        ("kohler generator", "find_equipment", [{"type": "brand", "value": "Kohler", "canonical": "KOHLER", "weight": 3.0}, {"type": "equipment", "value": "generator", "weight": 2.0}]),
        ("Furuno radar", "find_equipment", [{"type": "brand", "value": "Furuno", "canonical": "FURUNO", "weight": 3.0}, {"type": "equipment", "value": "radar", "weight": 2.0}]),
    ],
    "code_pattern": [
        ("fault SPN 146", "diagnose_fault", [{"type": "fault_code", "value": "SPN146", "weight": 5.0}]),
        ("J1939 169/3", "diagnose_fault", [{"type": "fault_code", "value": "J1939-169-3", "weight": 5.0}]),
        ("doc-12345", "find_document", [{"type": "document", "value": "doc-12345", "weight": 4.0}]),
        ("MCA certificate", "find_document", [{"type": "certificate", "value": "MCA", "canonical": "MCA", "weight": 3.5}]),
    ],
}

RULES_ONLY_QUERIES = {
    "command_pattern": [
        ("create work order", "create_work_order", []),
        ("open work order", "view_work_order_history", []),
        ("close work order", "mark_work_order_complete", []),
        ("add note", "add_work_order_note", []),
        ("add to handover", "add_to_handover", []),
        ("export handover", "export_handover", []),
        ("show equipment", "view_equipment_details", []),
        ("view history", "view_work_order_history", []),
        ("log entry", "add_work_order_note", []),
    ],
    "command_with_target": [
        ("create work order for generator 1 overheating", "create_work_order", [{"type": "equipment", "value": "generator 1", "canonical": "GENERATOR_1", "weight": 3.0}, {"type": "symptom", "value": "overheating", "weight": 2.5}]),
        ("add note to main engine", "add_work_order_note", [{"type": "equipment", "value": "main engine", "canonical": "MAIN_ENGINE", "weight": 3.5}]),
        ("schedule inspection for watermaker", "assign_work_order", [{"type": "equipment", "value": "watermaker", "canonical": "WATERMAKER", "weight": 3.0}]),
        ("please create wo for bilge pump", "create_work_order", [{"type": "equipment", "value": "bilge pump", "canonical": "BILGE_PUMP", "weight": 3.0}]),
        ("can you add this to handover", "add_to_handover", []),
    ],
    "polite_prefix": [
        ("please create work order", "create_work_order", []),
        ("can you show equipment history", "view_equipment_history", []),
        ("could you add to handover", "add_to_handover", []),
        ("I'd like to create wo", "create_work_order", []),
        ("hey can you show history", "view_work_order_history", []),
    ],
}

GPT_QUERIES = {
    "diagnostic": [
        ("main engine is overheating", "diagnose_issue", [{"type": "equipment", "value": "main engine", "canonical": "MAIN_ENGINE", "weight": 4.0}, {"type": "symptom", "value": "overheating", "weight": 3.5}]),
        ("generator making unusual noise", "diagnose_issue", [{"type": "equipment", "value": "generator", "canonical": "GENERATOR", "weight": 3.5}, {"type": "symptom", "value": "unusual noise", "weight": 3.0}]),
        ("stabilizer vibrating badly", "diagnose_issue", [{"type": "equipment", "value": "stabilizer", "canonical": "STABILIZER", "weight": 3.5}, {"type": "symptom", "value": "vibrating", "weight": 3.0}]),
        ("watermaker not working properly", "diagnose_issue", [{"type": "equipment", "value": "watermaker", "canonical": "WATERMAKER", "weight": 3.5}, {"type": "symptom", "value": "not working", "weight": 2.5}]),
        ("low oil pressure alarm on port engine", "diagnose_issue", [{"type": "symptom", "value": "low oil pressure", "weight": 4.0}, {"type": "equipment", "value": "port engine", "canonical": "PORT_ENGINE", "weight": 3.5}]),
        ("smoke coming from exhaust", "diagnose_issue", [{"type": "symptom", "value": "smoke", "weight": 3.5}, {"type": "part", "value": "exhaust", "weight": 2.5}]),
    ],
    "temporal": [
        ("show me faults from last week", "view_fault_history", [{"type": "temporal", "value": "last week", "weight": 2.0}]),
        ("what maintenance is due this month", "view_work_order_history", [{"type": "temporal", "value": "this month", "weight": 2.0}]),
        ("issues since we left port", "diagnose_issue", [{"type": "temporal", "value": "since port", "weight": 2.0}]),
        ("problems before charter", "diagnose_issue", [{"type": "temporal", "value": "before charter", "weight": 2.5}]),
        ("generator faults this morning", "diagnose_issue", [{"type": "equipment", "value": "generator", "canonical": "GENERATOR", "weight": 3.5}, {"type": "temporal", "value": "this morning", "weight": 2.0}]),
        ("what happened yesterday with the watermaker", "diagnose_issue", [{"type": "temporal", "value": "yesterday", "weight": 2.0}, {"type": "equipment", "value": "watermaker", "canonical": "WATERMAKER", "weight": 3.0}]),
    ],
    "complex": [
        ("why is the main engine running hot and making unusual noise after we refueled", "diagnose_issue", [{"type": "equipment", "value": "main engine", "canonical": "MAIN_ENGINE", "weight": 4.0}, {"type": "symptom", "value": "running hot", "weight": 3.5}, {"type": "symptom", "value": "unusual noise", "weight": 3.0}]),
        ("find me the maintenance manual for the caterpillar generator and show recent service history", "find_document", [{"type": "document", "value": "maintenance manual", "weight": 3.0}, {"type": "brand", "value": "caterpillar", "canonical": "CATERPILLAR", "weight": 2.5}, {"type": "equipment", "value": "generator", "canonical": "GENERATOR", "weight": 3.0}]),
        ("we have recurring issues with the starboard thruster, show me history and suggest parts", "diagnose_issue", [{"type": "equipment", "value": "starboard thruster", "canonical": "STARBOARD_THRUSTER", "weight": 4.0}, {"type": "symptom", "value": "recurring issues", "weight": 3.0}]),
    ],
}

# =============================================================================
# NOISE GENERATORS
# =============================================================================

TYPO_MAP = {
    "create": ["creat", "creaet", "crate"],
    "work": ["wrok", "wrk"],
    "order": ["oder", "oreder"],
    "engine": ["engien", "engin"],
    "generator": ["genertor", "genrator"],
    "filter": ["filtre", "fliter"],
    "manual": ["manaul", "manuel"],
    "maintenance": ["maintenace", "maintanence"],
    "overheating": ["overheting", "over heating"],
    "equipment": ["equpment", "equipement"],
    "show": ["shwo", "sho"],
    "history": ["hisotry", "histroy"],
    "schedule": ["schdeule", "schedul"],
    "assign": ["assing", "asign"],
}

SHORTHAND_MAP = {
    "work order": ["wo", "w/o", "WO"],
    "generator": ["gen", "genny"],
    "main engine": ["ME", "main eng", "m/e"],
    "watermaker": ["wm", "water maker"],
    "hours of rest": ["HOR", "h.o.r.", "rest hours"],
    "purchase order": ["PO", "po", "p.o."],
}

VOICE_DICTATION_PATTERNS = [
    # Common voice recognition errors
    ("engine", "engin"),
    ("fault", "falt"),
    ("oil", "oyle"),
    ("filter", "philter"),
    ("starboard", "star board"),
    ("portside", "port side"),
    ("stabilizer", "stabiliser"),
]


def apply_typo(text: str) -> str:
    """Apply a random typo to text."""
    words = text.split()
    if not words:
        return text

    for i, word in enumerate(words):
        word_lower = word.lower()
        if word_lower in TYPO_MAP and random.random() < 0.5:
            typo = random.choice(TYPO_MAP[word_lower])
            # Preserve original casing pattern
            if word[0].isupper():
                typo = typo.capitalize()
            words[i] = typo
            break

    return " ".join(words)


def apply_shorthand(text: str) -> str:
    """Apply shorthand substitution."""
    result = text
    for full, shorthands in SHORTHAND_MAP.items():
        if full.lower() in result.lower():
            shorthand = random.choice(shorthands)
            result = result.lower().replace(full.lower(), shorthand)
            break
    return result


def apply_casing_variation(text: str) -> str:
    """Apply random casing variation."""
    variations = [
        lambda t: t.upper(),
        lambda t: t.lower(),
        lambda t: t.title(),
        lambda t: "".join(c.upper() if random.random() > 0.5 else c.lower() for c in t),
    ]
    return random.choice(variations)(text)


def apply_voice_dictation(text: str) -> str:
    """Apply voice dictation-like errors."""
    result = text
    for correct, error in VOICE_DICTATION_PATTERNS:
        if correct.lower() in result.lower() and random.random() < 0.3:
            result = result.lower().replace(correct.lower(), error)
            break
    return result


# =============================================================================
# ADVERSARIAL GENERATORS
# =============================================================================

def generate_boundary_paste_dump() -> str:
    """Generate text right at the boundary of paste-dump detection."""
    # 45-55 words - right at the boundary of 50
    words = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog"]
    base = " ".join(random.choices(words, k=random.randint(45, 55)))
    return f"check {base} engine status"


def generate_multi_entity_conflict() -> Tuple[str, List[Dict]]:
    """Generate query with conflicting entity weights."""
    entities = [
        {"type": "part", "value": "oil filter", "canonical": "OIL_FILTER", "weight": 2.0},
        {"type": "equipment", "value": "main engine", "canonical": "MAIN_ENGINE", "weight": 4.5},
        {"type": "location", "value": "engine room", "canonical": "ENGINE_ROOM", "weight": 1.5},
        {"type": "fault_code", "value": "E047", "canonical": "E047", "weight": 5.0},
    ]
    query = "check oil filter location and E047 fault on main engine in engine room"
    return query, entities


def generate_high_weight_wrong_table() -> Tuple[str, List[Dict]]:
    """Generate query where high weight points to unexpected table."""
    entities = [
        {"type": "document", "value": "maintenance manual", "weight": 1.5},
        {"type": "fault_code", "value": "E001", "canonical": "E001", "weight": 5.0},  # High weight
    ]
    query = "find maintenance manual for fault E001"
    return query, entities


# =============================================================================
# NEGATIVE CONTROL GENERATORS
# =============================================================================

NEGATIVE_CONTROLS = [
    # Queries that SHOULD NOT trigger command patterns
    ("I need to understand how work orders work", "should_not_create_wo"),
    ("what is a handover used for", "should_not_add_handover"),
    ("explain the maintenance schedule", "should_not_schedule"),
    ("how do I usually create work orders", "should_not_create_wo"),
    ("tell me about the fault system", "should_not_report_fault"),
]


# =============================================================================
# MAIN GENERATOR CLASS
# =============================================================================

class StressTestGenerator:
    """
    Generates comprehensive stress test payloads.

    Coverage targets:
    - 1000+ total calls
    - 200+ per lane (50+ for BLOCKED)
    - 100+ concurrency calls
    """

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.payloads: List[TestPayload] = []
        self.lane_counts = {lane: 0 for lane in LANES}

    def generate_all(self) -> List[TestPayload]:
        """Generate all test payloads."""
        # BLOCKED lane (50+)
        self._generate_blocked_tests(60)

        # NO_LLM lane (300+)
        self._generate_no_llm_tests(350)

        # RULES_ONLY lane (300+)
        self._generate_rules_only_tests(350)

        # GPT lane (300+)
        self._generate_gpt_tests(350)

        # Multi-entity and conflict tests
        self._generate_multi_entity_tests(50)

        # Noise variation tests
        self._generate_noise_tests(100)

        # Adversarial tests
        self._generate_adversarial_tests(50)

        # Negative controls
        self._generate_negative_control_tests(30)

        # Concurrency burst tests
        self._generate_burst_tests(110)

        return self.payloads

    def _generate_blocked_tests(self, count: int):
        """Generate BLOCKED lane test cases."""
        # Paste dumps
        for query in BLOCKED_QUERIES["paste_dump"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.BLOCKED_PASTE_DUMP,
                expected_lane="BLOCKED",
                description="Code/log paste should be blocked",
            ))
            self.lane_counts["BLOCKED"] += 1

        # Too vague
        for query in BLOCKED_QUERIES["too_vague"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.BLOCKED_TOO_VAGUE,
                expected_lane="BLOCKED",
                description="Vague query should be blocked",
            ))
            self.lane_counts["BLOCKED"] += 1

        # Non-domain
        for query in BLOCKED_QUERIES["non_domain"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.BLOCKED_NON_DOMAIN,
                expected_lane="BLOCKED",
                description="Non-maritime query should be blocked",
            ))
            self.lane_counts["BLOCKED"] += 1

        # Generate boundary cases to hit count
        while self.lane_counts["BLOCKED"] < count:
            query = generate_boundary_paste_dump()
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.ADVERSARIAL_BOUNDARY,
                expected_lane="BLOCKED",
                description="Boundary paste-dump test",
            ))
            self.lane_counts["BLOCKED"] += 1

    def _generate_no_llm_tests(self, count: int):
        """Generate NO_LLM lane test cases."""
        # Direct lookups
        for query, intent, entities in NO_LLM_QUERIES["direct_lookup"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.NO_LLM_DIRECT_LOOKUP,
                expected_lane="NO_LLM",
                expected_intent=intent,
                entities=entities,
                forbidden_search_types=["VECTOR"],
                description="Direct lookup - no LLM needed",
            ))
            self.lane_counts["NO_LLM"] += 1

        # Brand/model lookups
        for query, intent, entities in NO_LLM_QUERIES["brand_model"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.NO_LLM_BRAND_MODEL,
                expected_lane="NO_LLM",
                expected_intent=intent,
                entities=entities,
                forbidden_search_types=["VECTOR"],
                description="Brand/model lookup - no LLM needed",
            ))
            self.lane_counts["NO_LLM"] += 1

        # Code patterns
        for query, intent, entities in NO_LLM_QUERIES["code_pattern"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.NO_LLM_CODE_PATTERN,
                expected_lane="NO_LLM",
                expected_intent=intent,
                entities=entities,
                forbidden_search_types=["VECTOR"],
                description="Code pattern - no LLM needed",
            ))
            self.lane_counts["NO_LLM"] += 1

        # Generate variations with noise to hit count
        base_queries = [q[0] for q in NO_LLM_QUERIES["direct_lookup"] + NO_LLM_QUERIES["brand_model"]]
        while self.lane_counts["NO_LLM"] < count:
            base = random.choice(base_queries)
            # Apply random noise
            noisy = base
            if random.random() < 0.3:
                noisy = apply_typo(noisy)
            if random.random() < 0.3:
                noisy = apply_shorthand(noisy)
            if random.random() < 0.2:
                noisy = apply_casing_variation(noisy)

            self.payloads.append(TestPayload(
                query=noisy,
                category=TestCategory.SPELLING_NOISE,
                expected_lane="NO_LLM",
                forbidden_search_types=["VECTOR"],
                description=f"Noise variation of: {base}",
            ))
            self.lane_counts["NO_LLM"] += 1

    def _generate_rules_only_tests(self, count: int):
        """Generate RULES_ONLY lane test cases."""
        # Command patterns
        for query, intent, entities in RULES_ONLY_QUERIES["command_pattern"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.RULES_ONLY_COMMAND,
                expected_lane="RULES_ONLY",
                expected_intent=intent,
                entities=entities,
                forbidden_search_types=["VECTOR"],
                description="Simple command pattern",
            ))
            self.lane_counts["RULES_ONLY"] += 1

        # Commands with targets
        for query, intent, entities in RULES_ONLY_QUERIES["command_with_target"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.RULES_ONLY_WITH_TARGET,
                expected_lane="RULES_ONLY",
                expected_intent=intent,
                entities=entities,
                forbidden_search_types=["VECTOR"],
                description="Command with entity target",
            ))
            self.lane_counts["RULES_ONLY"] += 1

        # Polite prefixes
        for query, intent, entities in RULES_ONLY_QUERIES["polite_prefix"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.RULES_ONLY_COMMAND,
                expected_lane="RULES_ONLY",
                expected_intent=intent,
                entities=entities,
                forbidden_search_types=["VECTOR"],
                description="Polite prefix command",
            ))
            self.lane_counts["RULES_ONLY"] += 1

        # Generate variations
        base_commands = [q[0] for q in RULES_ONLY_QUERIES["command_pattern"] + RULES_ONLY_QUERIES["command_with_target"]]
        equipment_targets = ["main engine", "generator 1", "watermaker", "stabilizer", "bilge pump"]

        while self.lane_counts["RULES_ONLY"] < count:
            base = random.choice(base_commands)
            target = random.choice(equipment_targets)

            # Add target if not present
            if "for" not in base.lower() and "to" not in base.lower():
                query = f"{base} for {target}"
            else:
                query = base

            # Apply noise
            if random.random() < 0.2:
                query = apply_typo(query)
            if random.random() < 0.2:
                query = apply_shorthand(query)

            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.RULES_ONLY_WITH_TARGET,
                expected_lane="RULES_ONLY",
                forbidden_search_types=["VECTOR"],
                description=f"Generated command variation",
            ))
            self.lane_counts["RULES_ONLY"] += 1

    def _generate_gpt_tests(self, count: int):
        """Generate GPT lane test cases."""
        # Diagnostic queries
        for query, intent, entities in GPT_QUERIES["diagnostic"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.GPT_DIAGNOSTIC,
                expected_lane="GPT",
                expected_intent=intent,
                entities=entities,
                should_have_embedding=True,
                description="Diagnostic query - needs GPT",
            ))
            self.lane_counts["GPT"] += 1

        # Temporal queries
        for query, intent, entities in GPT_QUERIES["temporal"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.GPT_TEMPORAL,
                expected_lane="GPT",
                expected_intent=intent,
                entities=entities,
                should_have_embedding=True,
                description="Temporal query - needs GPT",
            ))
            self.lane_counts["GPT"] += 1

        # Complex queries
        for query, intent, entities in GPT_QUERIES["complex"]:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.GPT_COMPLEX,
                expected_lane="GPT",
                expected_intent=intent,
                entities=entities,
                should_have_embedding=True,
                description="Complex query - needs GPT",
            ))
            self.lane_counts["GPT"] += 1

        # Generate variations
        symptoms = ["overheating", "leaking", "vibrating", "making noise", "not working", "smoking", "failing"]
        equipment = ["main engine", "port engine", "generator", "watermaker", "stabilizer", "thruster", "windlass"]

        while self.lane_counts["GPT"] < count:
            symptom = random.choice(symptoms)
            equip = random.choice(equipment)
            query = f"{equip} is {symptom}"

            # Add temporal context sometimes
            if random.random() < 0.3:
                temporal = random.choice(["since yesterday", "this morning", "after maintenance", "before charter"])
                query = f"{query} {temporal}"

            # Apply noise occasionally
            if random.random() < 0.15:
                query = apply_typo(query)
            if random.random() < 0.15:
                query = apply_voice_dictation(query)

            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.GPT_DIAGNOSTIC,
                expected_lane="GPT",
                expected_intent="diagnose_issue",
                entities=[
                    {"type": "equipment", "value": equip, "weight": 3.5},
                    {"type": "symptom", "value": symptom, "weight": 3.0},
                ],
                should_have_embedding=True,
                description="Generated diagnostic query",
            ))
            self.lane_counts["GPT"] += 1

    def _generate_multi_entity_tests(self, count: int):
        """Generate multi-entity and conflict tests."""
        for _ in range(count):
            query, entities = generate_multi_entity_conflict()
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.CONFLICTING_ENTITIES,
                expected_lane="RULES_ONLY",  # Mixed entities
                entities=entities,
                description="Multi-entity conflict test",
            ))

    def _generate_noise_tests(self, count: int):
        """Generate spelling noise, shorthand, casing tests."""
        base_queries = [
            "create work order for generator",
            "show equipment history",
            "find maintenance manual",
            "check oil filter",
            "add to handover",
        ]

        for _ in range(count):
            base = random.choice(base_queries)
            noise_type = random.choice(["typo", "shorthand", "casing", "voice"])

            if noise_type == "typo":
                query = apply_typo(base)
                category = TestCategory.SPELLING_NOISE
            elif noise_type == "shorthand":
                query = apply_shorthand(base)
                category = TestCategory.SHORTHAND
            elif noise_type == "casing":
                query = apply_casing_variation(base)
                category = TestCategory.CASING_VARIATIONS
            else:
                query = apply_voice_dictation(base)
                category = TestCategory.VOICE_DICTATION

            self.payloads.append(TestPayload(
                query=query,
                category=category,
                expected_lane="RULES_ONLY",  # Commands should still route to RULES_ONLY
                description=f"{noise_type} applied to: {base}",
            ))

    def _generate_adversarial_tests(self, count: int):
        """Generate adversarial boundary tests."""
        for _ in range(count // 2):
            # Boundary paste dumps
            query = generate_boundary_paste_dump()
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.ADVERSARIAL_BOUNDARY,
                expected_lane="BLOCKED",  # Should be blocked
                description="Boundary word count test",
            ))

        for _ in range(count // 2):
            # High weight wrong table
            query, entities = generate_high_weight_wrong_table()
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.HIGH_WEIGHT_WRONG_TABLE,
                expected_lane="NO_LLM",
                entities=entities,
                description="High weight wrong table test",
            ))

    def _generate_negative_control_tests(self, count: int):
        """Generate negative control tests."""
        for query, control_type in NEGATIVE_CONTROLS:
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.NEGATIVE_CONTROL,
                expected_lane="NO_LLM",  # Should be simple lookup, not command
                description=f"Negative control: {control_type}",
            ))

        # Generate more variations
        while len([p for p in self.payloads if p.category == TestCategory.NEGATIVE_CONTROL]) < count:
            base = random.choice(NEGATIVE_CONTROLS)[0]
            self.payloads.append(TestPayload(
                query=base,
                category=TestCategory.NEGATIVE_CONTROL,
                expected_lane="NO_LLM",
                description="Negative control variation",
            ))

    def _generate_burst_tests(self, count: int):
        """Generate burst/concurrency test payloads."""
        # Mix of all lanes for burst testing
        burst_queries = [
            ("WO-1234", "NO_LLM"),
            ("create work order", "RULES_ONLY"),
            ("engine overheating", "GPT"),
            ("ME1 status", "NO_LLM"),
            ("show history", "RULES_ONLY"),
        ]

        for i in range(count):
            query, expected_lane = random.choice(burst_queries)
            self.payloads.append(TestPayload(
                query=query,
                category=TestCategory.BURST_TEST,
                expected_lane=expected_lane,
                yacht_id=random.choice(TEST_YACHT_IDS),
                session_id=str(uuid.uuid4()),
                stream_id=str(uuid.uuid4()),
                description=f"Burst test {i+1}",
            ))

    def get_summary(self) -> Dict:
        """Get summary statistics of generated payloads."""
        category_counts = {}
        for p in self.payloads:
            cat = p.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        lane_counts = {}
        for p in self.payloads:
            lane = p.expected_lane
            lane_counts[lane] = lane_counts.get(lane, 0) + 1

        return {
            "total_payloads": len(self.payloads),
            "by_category": category_counts,
            "by_lane": lane_counts,
            "meets_minimums": {
                "total": len(self.payloads) >= MIN_TOTAL_CALLS,
                "blocked": lane_counts.get("BLOCKED", 0) >= MIN_PER_LANE["BLOCKED"],
                "no_llm": lane_counts.get("NO_LLM", 0) >= MIN_PER_LANE["NO_LLM"],
                "rules_only": lane_counts.get("RULES_ONLY", 0) >= MIN_PER_LANE["RULES_ONLY"],
                "gpt": lane_counts.get("GPT", 0) >= MIN_PER_LANE["GPT"],
                "concurrency": category_counts.get("burst_test", 0) >= 100,
            }
        }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    generator = StressTestGenerator(seed=42)
    payloads = generator.generate_all()

    summary = generator.get_summary()

    print("=" * 70)
    print(" STRESS TEST GENERATOR - Payload Summary")
    print("=" * 70)

    print(f"\nTotal payloads: {summary['total_payloads']}")

    print("\nBy Lane:")
    for lane, count in summary["by_lane"].items():
        min_required = MIN_PER_LANE.get(lane, 0)
        status = "OK" if count >= min_required else "BELOW MIN"
        print(f"  {lane}: {count} ({status}, min: {min_required})")

    print("\nBy Category:")
    for cat, count in sorted(summary["by_category"].items()):
        print(f"  {cat}: {count}")

    print("\nMinimum Requirements:")
    for req, met in summary["meets_minimums"].items():
        status = "PASS" if met else "FAIL"
        print(f"  {req}: {status}")

    # Export sample payloads
    print("\n" + "=" * 70)
    print(" Sample Payloads (first 5)")
    print("=" * 70)
    for p in payloads[:5]:
        print(f"\n  Query: {p.query[:60]}...")
        print(f"  Lane: {p.expected_lane}")
        print(f"  Category: {p.category.value}")
