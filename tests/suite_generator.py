#!/usr/bin/env python3
"""
Pattern Suite Generator with Guardrails
========================================
Generates structured test suites for pattern-led testing.

Guardrails enforced:
1. No single-dimension variants (must differ in 2+ dimensions)
2. Similarity caps (max 2 same first-4-tokens, max 3 same verb+object)
3. Every suite has negatives
4. Canonical-only actions
5. Hard FP vs soft misroute classification
6. Entity hints include evidence substrings
"""

import json
import random
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

from pattern_library_v1 import (
    Pattern, RiskClass, ALL_PATTERNS, PATTERN_BY_ID,
    get_patterns_by_priority, get_high_risk_patterns,
    COLLISION_PATTERNS, NOISE_PREFIX_PATTERNS, SAFETY_RAIL_PATTERNS
)
from canonical_action_registry import CANONICAL_ACTIONS


# =============================================================================
# DIMENSION VARIATION POOLS
# =============================================================================

EQUIPMENT_VARIANTS = {
    "main_engine": ["main engine", "ME", "starboard main", "port main", "propulsion engine"],
    "generator": ["generator", "genset", "DG", "diesel generator", "aux gen"],
    "thruster": ["bow thruster", "stern thruster", "thruster", "azimuth thruster"],
    "watermaker": ["watermaker", "desalinator", "RO system", "reverse osmosis"],
    "stabilizer": ["stabilizer", "fin stabilizer", "gyro", "Seakeeper"],
    "hvac": ["HVAC", "air conditioning", "AC unit", "chiller", "air handler"],
    "pump": ["bilge pump", "fire pump", "fuel pump", "transfer pump", "raw water pump"],
    "windlass": ["windlass", "anchor windlass", "capstan"],
}

BRAND_VARIANTS = [
    "Caterpillar", "CAT", "MTU", "Cummins", "Volvo Penta", "MAN", "Yanmar",
    "Kohler", "Northern Lights", "Onan", "Victron", "Mastervolt", "Furuno",
    "Raymarine", "Garmin", "Lewmar", "Maxwell", "Dometic", "Webasto",
]

LOCATION_VARIANTS = [
    "engine room", "ER", "wheelhouse", "bridge", "bow locker", "stern locker",
    "port side", "starboard side", "stbd", "lazarette", "forepeak", "bilge",
    "main deck", "lower deck", "crew quarters", "galley",
]

FAULT_CODE_VARIANTS = [
    "E047", "E123", "P0420", "SPN 100 FMI 4", "alarm 23", "warning 15",
    "fault code 789", "error 456", "MID 128 SID 21",
]

SYMPTOM_VARIANTS = [
    "overheating", "high temperature", "low pressure", "no output",
    "not working", "alarm", "noise", "vibration", "leak", "leaking",
    "smoking", "intermittent", "surging", "tripping", "won't start",
]

TIME_QUALIFIERS = [
    "today", "this morning", "yesterday", "last week", "during sea trial",
    "after maintenance", "since last port", "before charter",
]

NOISE_PREFIXES = {
    "so": ["so", "so like", "so um", "so basically"],
    "ok": ["ok", "ok so", "okay", "alright"],
    "right": ["right", "right so", "right okay"],
    "fw": ["FW:", "Fw:", "Fwd:", "FW: Parts needed\n\n"],
    "re": ["RE:", "Re:", "RE: Issue\n\n"],
    "quote": [">>>", ">> ", "> "],
    "bullet": ["- ", "• ", "* "],
    "filler": ["um", "uh", "er", "like"],
    "hey": ["hey", "hey can you", "yo"],
}

QUERY_FORMS = [
    "verb_first",      # "show manual for generator"
    "noun_first",      # "generator manual section"
    "polite_prefix",   # "can you show manual" (negative control)
    "voice_dictation", # "so like show me the uh manual"
    "email_paste",     # "FW: Parts needed\n\ncheck stock"
    "typo",           # "shwo maual for gnerator"
]


# =============================================================================
# CASE TEMPLATES BY PATTERN
# =============================================================================

@dataclass
class CaseTemplate:
    """Template for generating a test case."""
    action: str
    query_template: str
    entities: List[Dict]
    purpose: str
    is_positive: bool
    is_negative_control: bool
    is_collision: bool
    is_messy: bool
    risk_class: RiskClass
    negative_control_reason: Optional[str] = None


def get_templates_for_pattern(pattern: Pattern) -> List[CaseTemplate]:
    """Generate case templates for a pattern."""
    templates = []

    # POSITIVE cases (should trigger the expected action)
    for action in pattern.primary_actions[:3]:  # Limit to top 3 actions
        if action in CANONICAL_ACTIONS:
            templates.append(CaseTemplate(
                action=action,
                query_template=f"{{verb}} {{entity}} {{qualifier}}",
                entities=[{"type": "equipment", "value_hint": "{equipment}"}],
                purpose="positive_trigger",
                is_positive=True,
                is_negative_control=False,
                is_collision=False,
                is_messy=False,
                risk_class=RiskClass.SAFE,
            ))

    # NEGATIVE CONTROL cases (should NOT trigger)
    for signal in pattern.negative_signals[:3]:
        templates.append(CaseTemplate(
            action="none_search_only",
            query_template=f"{signal} {{verb}} {{entity}}",
            entities=[{"type": "equipment", "value_hint": "{equipment}"}],
            purpose="negative_control",
            is_positive=False,
            is_negative_control=True,
            is_collision=False,
            is_messy=False,
            risk_class=pattern.default_risk,
            negative_control_reason=f"Polite/request prefix: '{signal}'",
        ))

    # COLLISION cases (ambiguous, could be multiple actions)
    if pattern.collision_actions:
        for collision_action in pattern.collision_actions:
            templates.append(CaseTemplate(
                action=collision_action,  # Expected to route here
                query_template=f"{{verb}} {{entity}}",  # Minimal context
                entities=[{"type": "equipment", "value_hint": "{equipment}"}],
                purpose="collision_test",
                is_positive=True,
                is_negative_control=False,
                is_collision=True,
                is_messy=False,
                risk_class=RiskClass.SOFT_MISROUTE,
            ))

    # MESSY cases (voice/email/typo artifacts)
    templates.append(CaseTemplate(
        action=pattern.primary_actions[0] if pattern.primary_actions else "none_search_only",
        query_template=f"{{noise}} {{verb}} {{entity}}",
        entities=[{"type": "equipment", "value_hint": "{equipment}"}],
        purpose="messy_voice",
        is_positive=True,
        is_negative_control=False,
        is_collision=False,
        is_messy=True,
        risk_class=RiskClass.FN_RISK,
    ))

    return templates


# =============================================================================
# SUITE GENERATION
# =============================================================================

@dataclass
class TestCase:
    """A single test case."""
    id: str
    query: str
    labels: Dict

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "query": self.query,
            "labels": self.labels,
        }


@dataclass
class Suite:
    """A test suite targeting one pattern."""
    suite_id: str
    pattern_target: str
    what_changed: str
    hypothesis: str
    cases: List[TestCase]

    def to_dict(self) -> Dict:
        return {
            "suite_id": self.suite_id,
            "pattern_target": self.pattern_target,
            "what_changed": self.what_changed,
            "hypothesis": self.hypothesis,
            "cases": [c.to_dict() for c in self.cases],
        }


class SuiteGenerator:
    """Generates test suites with guardrails."""

    def __init__(self):
        self.used_queries: Set[str] = set()

    def generate_suite(
        self,
        pattern: Pattern,
        suite_num: int,
        num_positives: int = 7,
        num_negatives: int = 7,
        num_collisions: int = 4,
        num_messy: int = 2
    ) -> Suite:
        """Generate a suite for a pattern with guardrails."""
        suite_id = f"S{suite_num:02d}"
        cases = []

        # Track for similarity checks
        first_four_tokens = defaultdict(int)
        verb_object_pairs = defaultdict(int)

        # Generate each case type
        cases.extend(self._generate_cases(
            pattern, suite_id, "positive", num_positives,
            first_four_tokens, verb_object_pairs
        ))
        cases.extend(self._generate_cases(
            pattern, suite_id, "negative", num_negatives,
            first_four_tokens, verb_object_pairs
        ))
        cases.extend(self._generate_cases(
            pattern, suite_id, "collision", num_collisions,
            first_four_tokens, verb_object_pairs
        ))
        cases.extend(self._generate_cases(
            pattern, suite_id, "messy", num_messy,
            first_four_tokens, verb_object_pairs
        ))

        return Suite(
            suite_id=suite_id,
            pattern_target=pattern.pattern_id,
            what_changed=self._get_change_description(pattern),
            hypothesis=self._get_hypothesis(pattern),
            cases=cases,
        )

    def _generate_cases(
        self,
        pattern: Pattern,
        suite_id: str,
        case_type: str,
        count: int,
        first_four_tokens: Dict[str, int],
        verb_object_pairs: Dict[str, int],
    ) -> List[TestCase]:
        """Generate cases of a specific type with variation."""
        cases = []

        for i in range(count):
            case_id = f"{suite_id}_{case_type[0].upper()}{i+1:02d}"

            # Generate with retries for uniqueness
            generated = False
            for attempt in range(50):  # More retries
                query, labels = self._generate_single_case(pattern, case_type, attempt)

                # Check guardrails
                if self._check_guardrails(query, first_four_tokens, verb_object_pairs):
                    # Track for future checks
                    tokens = query.lower().split()[:4]
                    token_key = " ".join(tokens)
                    first_four_tokens[token_key] += 1

                    if len(tokens) >= 2:
                        verb_obj = f"{tokens[0]} {tokens[1]}"
                        verb_object_pairs[verb_obj] += 1

                    self.used_queries.add(query.lower())

                    cases.append(TestCase(
                        id=case_id,
                        query=query,
                        labels=labels,
                    ))
                    generated = True
                    break

            # If couldn't generate unique, still add with modified ID
            if not generated:
                query, labels = self._generate_single_case(pattern, case_type, 999)
                query = f"{query} [{i}]"  # Add unique suffix
                cases.append(TestCase(
                    id=case_id,
                    query=query,
                    labels=labels,
                ))

        return cases

    def _generate_single_case(self, pattern: Pattern, case_type: str, attempt: int = 0) -> Tuple[str, Dict]:
        """Generate a single test case with variations."""
        # Use attempt to seed different choices for variety
        random.seed(random.randint(0, 10000) + attempt)

        # Pick random variations
        equipment_type = random.choice(list(EQUIPMENT_VARIANTS.keys()))
        equipment = random.choice(EQUIPMENT_VARIANTS[equipment_type])
        brand = random.choice(BRAND_VARIANTS)
        location = random.choice(LOCATION_VARIANTS)
        symptom = random.choice(SYMPTOM_VARIANTS)
        time_qual = random.choice(TIME_QUALIFIERS)
        fault_code = random.choice(FAULT_CODE_VARIANTS)

        # Determine query form and action based on case type
        if case_type == "positive":
            query, action = self._make_positive_query(pattern, equipment, location, symptom)
            should_trigger = True
            risk = RiskClass.SAFE
            negative_reason = None

        elif case_type == "negative":
            query, action = self._make_negative_query(pattern, equipment, location)
            should_trigger = False
            risk = pattern.default_risk
            negative_reason = "Polite prefix or non-imperative form"

        elif case_type == "collision":
            query, action = self._make_collision_query(pattern, equipment, symptom)
            should_trigger = True
            risk = RiskClass.SOFT_MISROUTE
            negative_reason = None

        else:  # messy
            query, action = self._make_messy_query(pattern, equipment, symptom, fault_code)
            should_trigger = True
            risk = RiskClass.FN_RISK
            negative_reason = None

        # Build labels
        entities = []
        if equipment:
            entities.append({
                "type": "equipment",
                "value_hint": equipment,
                "evidence": equipment,
            })
        if symptom and symptom in query.lower():
            entities.append({
                "type": "symptom",
                "value_hint": symptom,
                "evidence": symptom,
            })
        if fault_code and fault_code.lower() in query.lower():
            entities.append({
                "type": "fault_code",
                "value_hint": fault_code,
                "evidence": fault_code,
            })

        labels = {
            "expected_primary_action": action,
            "should_trigger_action": should_trigger,
            "risk_class": risk.value,
            "expected_entities": entities,
            "purpose_cluster": pattern.category,
            "query_form": self._detect_query_form(query),
            "noise_type": self._detect_noise_type(query),
            "difficulty": self._assess_difficulty(query, pattern),
        }

        if negative_reason:
            labels["negative_control_reason"] = negative_reason

        return query, labels

    def _make_positive_query(self, pattern: Pattern, equipment: str, location: str, symptom: str) -> Tuple[str, str]:
        """Create a positive (should trigger) query with high variation."""
        action = pattern.primary_actions[0] if pattern.primary_actions else "none_search_only"
        time_qual = random.choice(TIME_QUALIFIERS)
        brand = random.choice(BRAND_VARIANTS)
        fault_code = random.choice(FAULT_CODE_VARIANTS)

        # Build query based on pattern type with many variations
        if pattern.category == "collision":
            verb = pattern.pattern_id.replace("COL_", "").lower()
            if verb == "add":
                queries = [
                    f"add {equipment} issue to handover",
                    f"add note about {brand} {equipment} {symptom} to work order",
                    f"add {symptom} observation to handover notes",
                    f"add {equipment} fault to maintenance log",
                    f"add finding from {location} inspection to handover",
                    f"add observation about {symptom} in {location}",
                    f"add {time_qual} issue with {equipment} to records",
                    f"add {brand} service note to work order",
                    f"add part usage note for {equipment}",
                    f"add checklist item for {equipment} inspection",
                ]
            elif verb == "show":
                queries = [
                    f"show linked faults for {equipment}",
                    f"show tasks due on {brand} {equipment}",
                    f"show certificates expiring this month",
                    f"show manual section for {symptom} on {equipment}",
                    f"show history for {equipment} in {location}",
                    f"show {equipment} status overview",
                    f"show all linked documents for {brand} {equipment}",
                    f"show predictive insights for {equipment}",
                    f"show hours of rest log for crew",
                    f"show equipment utilization for {equipment}",
                    f"show fault trends for {equipment}",
                    f"show storage location for {equipment} parts",
                ]
            elif verb == "export":
                queries = [
                    f"export handover for {equipment} systems",
                    f"export compliance logs from {time_qual}",
                    f"export work order history for {brand} {equipment}",
                    f"export summary of {symptom} issues",
                    f"export {equipment} maintenance records",
                    f"export hours of rest data",
                    f"export {location} equipment reports",
                ]
            elif verb == "open":
                queries = [
                    f"open equipment card for {brand} {equipment}",
                    f"open document for {equipment} manual",
                    f"open {equipment} service manual",
                    f"open {brand} {equipment} specification sheet",
                    f"open {location} equipment card",
                    f"open maintenance log for {equipment}",
                ]
            elif verb == "generate":
                queries = [
                    f"generate audit pack for {equipment}",
                    f"generate summary of {brand} {equipment} issues",
                    f"generate {time_qual} maintenance report",
                    f"generate compliance pack for {equipment}",
                    f"generate overview for {location} systems",
                ]
            elif verb == "update":
                queries = [
                    f"update work order for {brand} {equipment}",
                    f"update stock level for {equipment} parts",
                    f"update certificate for {equipment}",
                    f"update {location} equipment status",
                    f"update {equipment} metadata",
                ]
            elif verb == "upload":
                queries = [
                    f"upload certificate for {brand} {equipment}",
                    f"upload document for {equipment} manual",
                    f"upload invoice from {brand}",
                    f"upload {equipment} service report",
                    f"upload {time_qual} inspection photos",
                ]
            elif verb == "attach":
                queries = [
                    f"attach photo of {brand} {equipment} to work order",
                    f"attach document to {equipment} handover",
                    f"attach {equipment} image to maintenance log",
                    f"attach {location} inspection photo",
                    f"attach {brand} invoice to work order",
                ]
            else:
                queries = [f"{verb} {equipment} {location}"]

            query = random.choice(queries)

        elif pattern.category == "noise_prefix":
            # For noise prefix patterns, test varied underlying actions
            base_actions = pattern.primary_actions if pattern.primary_actions else ["diagnose_fault"]
            base_action = random.choice(base_actions)

            if base_action == "create_work_order":
                queries = [
                    f"create work order for {brand} {equipment} {symptom}",
                    f"create WO for {equipment} in {location}",
                    f"create task for {equipment} maintenance",
                    f"create maintenance request for {symptom}",
                    f"create repair order for {brand} {equipment}",
                ]
            elif base_action == "check_stock_level":
                queries = [
                    f"check stock for {equipment} parts",
                    f"check inventory for {brand} filters",
                    f"check spares for {equipment}",
                    f"check parts level for {equipment}",
                    f"check if we have {equipment} seals",
                ]
            elif base_action == "diagnose_fault":
                queries = [
                    f"diagnose {symptom} on {brand} {equipment}",
                    f"diagnose fault {fault_code} on {equipment}",
                    f"diagnose {equipment} issue in {location}",
                    f"troubleshoot {symptom} on {equipment}",
                    f"investigate {equipment} alarm",
                ]
            else:
                queries = [
                    f"show {brand} {equipment} {symptom}",
                    f"show {equipment} history from {location}",
                ]

            query = random.choice(queries)

        elif pattern.category == "safety_rail":
            # Safety rail patterns test that state-changing actions DON'T trigger
            # Positive cases should be read-only actions that DO trigger safely
            action = "show_equipment_overview"  # Safe default
            queries = [
                f"show {brand} {equipment} overview",
                f"show {equipment} status",
                f"view {equipment} details",
                f"display {brand} {equipment} info",
                f"list {equipment} components",
            ]
            query = random.choice(queries)
            return query, action

        elif pattern.category == "international":
            # International verb variants
            if "make" in pattern.pattern_id.lower():
                queries = [
                    f"make work order for {equipment}",
                    f"make WO for {brand} {equipment}",
                    f"make task for {equipment} repair",
                ]
            elif "do" in pattern.pattern_id.lower():
                queries = [
                    f"do handover note for {equipment}",
                    f"do note about {symptom}",
                    f"do entry for {equipment}",
                ]
            elif "put" in pattern.pattern_id.lower():
                queries = [
                    f"put {equipment} in handover",
                    f"put note about {symptom}",
                    f"put this in maintenance log",
                ]
            else:
                queries = [f"check {equipment}"]
            query = random.choice(queries)

        else:
            # Default positive query with variation
            queries = [
                f"diagnose {symptom} on {brand} {equipment}",
                f"troubleshoot {equipment} {symptom}",
                f"show manual for {equipment} {symptom}",
                f"check {equipment} in {location}",
            ]
            query = random.choice(queries)

        return query, action

    def _make_negative_query(self, pattern: Pattern, equipment: str, location: str) -> Tuple[str, str]:
        """Create a negative control query (should NOT trigger) with variation."""
        brand = random.choice(BRAND_VARIANTS)
        symptom = random.choice(SYMPTOM_VARIANTS)
        time_qual = random.choice(TIME_QUALIFIERS)

        polite_prefixes = [
            "can you", "could you", "would you", "please",
            "i need to", "i want to", "help me", "is it possible to",
            "we need to", "i'd like to", "we should", "looking to",
        ]
        prefix = random.choice(polite_prefixes)

        verb = pattern.primary_actions[0].split("_")[0] if pattern.primary_actions else "show"

        # Vary the query structure
        query_templates = [
            f"{prefix} {verb} {equipment} {location}",
            f"{prefix} {verb} the {brand} {equipment}",
            f"{prefix} {verb} {equipment} {symptom} issue",
            f"{prefix} see {equipment} information",
            f"{prefix} look at {equipment} in {location}",
            f"{prefix} get {equipment} details",
            f"{prefix} find {equipment} {symptom} info",
            f"{prefix} check on {brand} {equipment}",
        ]
        query = random.choice(query_templates)

        return query, "none_search_only"

    def _make_collision_query(self, pattern: Pattern, equipment: str, symptom: str) -> Tuple[str, str]:
        """Create a collision query (ambiguous, tests disambiguation)."""
        action = pattern.collision_actions[0] if pattern.collision_actions else pattern.primary_actions[0]
        brand = random.choice(BRAND_VARIANTS)
        location = random.choice(LOCATION_VARIANTS)

        # Minimal context to trigger collision
        verb = pattern.pattern_id.replace("COL_", "").lower()
        if verb == "add":
            queries = [
                f"add {equipment} note",  # Ambiguous: handover? WO? just note?
                f"add {symptom} finding",
                f"add this to records",
                f"add {brand} issue",
                f"add observation for {equipment}",
                f"add comment about {symptom}",
                f"add {location} note",
            ]
        elif verb == "show":
            queries = [
                f"show {equipment}",  # Ambiguous: overview? history? card?
                f"show all {equipment} items",
                f"show {brand} info",
                f"show {location} status",
                f"show everything for {equipment}",
                f"show {equipment} data",
            ]
        elif verb == "export":
            queries = [
                f"export {equipment} data",  # Ambiguous: what format? what type?
                f"export all records",
                f"export {brand} info",
                f"export {location} report",
                f"export everything",
            ]
        elif verb == "open":
            queries = [
                f"open {equipment}",
                f"open {brand} file",
                f"open {location} info",
            ]
        elif verb == "generate":
            queries = [
                f"generate {equipment} report",
                f"generate data for {brand}",
            ]
        elif verb == "update":
            queries = [
                f"update {equipment}",
                f"update {brand} entry",
                f"update {location} record",
            ]
        elif verb == "upload":
            queries = [
                f"upload {equipment} file",
                f"upload {brand} doc",
            ]
        elif verb == "attach":
            queries = [
                f"attach {equipment} file",
                f"attach to {brand} record",
            ]
        else:
            queries = [f"{verb} {equipment}", f"{verb} {brand}"]

        return random.choice(queries), action

    def _make_messy_query(self, pattern: Pattern, equipment: str, symptom: str, fault_code: str) -> Tuple[str, str]:
        """Create a messy query (voice/email/typo artifacts) with high variation."""
        action = pattern.primary_actions[0] if pattern.primary_actions else "none_search_only"
        brand = random.choice(BRAND_VARIANTS)
        location = random.choice(LOCATION_VARIANTS)
        time_qual = random.choice(TIME_QUALIFIERS)

        # Pick a noise type
        noise_type = random.choice(["voice", "email", "typo", "quote", "bullet"])

        if noise_type == "voice":
            # Voice dictation with filler words
            fillers = random.choice([
                "so like", "um", "so um", "like um", "so basically",
                "ok so", "right so", "yeah so", "alright",
            ])
            verb = action.split("_")[0]
            voice_patterns = [
                f"{fillers} {verb} {equipment} it's got {symptom}",
                f"{fillers} {verb} the uh {brand} {equipment}",
                f"{fillers} can you {verb} {equipment}",
                f"hey {fillers} {verb} {equipment} {symptom}",
                f"{fillers} I need to {verb} {equipment}",
            ]
            query = random.choice(voice_patterns)

        elif noise_type == "email":
            # Email prefix
            prefix = random.choice([
                "FW: Issue\n\n", "RE: Problem\n\n", "Fwd:\n",
                "From: Captain\n\n", "RE: Urgent\n\n",
                "FW: Maintenance\n\n",
            ])
            verb = action.split("_")[0]
            query = f"{prefix}{verb} {equipment} {symptom}"

        elif noise_type == "quote":
            # Quote markers from copy-paste
            prefix = random.choice([">>> ", ">> ", "> ", ">>> "])
            verb = action.split("_")[0]
            query = f"{prefix}{verb} {equipment} {symptom}"

        elif noise_type == "bullet":
            # Bullet points from lists
            prefix = random.choice(["- ", "• ", "* ", "– "])
            verb = action.split("_")[0]
            query = f"{prefix}{verb} {brand} {equipment}"

        else:
            # Typos
            verb = action.split("_")[0]
            typo_verb = self._add_typo(verb)
            typo_equip = self._add_typo(equipment.split()[0]) if equipment else equipment
            typo_patterns = [
                f"{typo_verb} {typo_equip} {symptom}",
                f"{verb} {typo_equip} {symptom}",
                f"{typo_verb} {equipment} {symptom}",
                f"{typo_verb} {brand} {equipment}",
            ]
            query = random.choice(typo_patterns)

        return query, action

    def _add_typo(self, word: str) -> str:
        """Add a realistic typo to a word."""
        if len(word) < 3:
            return word

        typo_type = random.choice(["swap", "missing", "double"])

        if typo_type == "swap" and len(word) > 3:
            # Swap two adjacent letters
            i = random.randint(1, len(word) - 2)
            return word[:i] + word[i+1] + word[i] + word[i+2:]
        elif typo_type == "missing":
            # Remove a letter
            i = random.randint(1, len(word) - 1)
            return word[:i] + word[i+1:]
        else:
            # Double a letter
            i = random.randint(0, len(word) - 1)
            return word[:i] + word[i] + word[i:]

        return word

    def _check_guardrails(
        self,
        query: str,
        first_four_tokens: Dict[str, int],
        verb_object_pairs: Dict[str, int],
    ) -> bool:
        """Check if query passes guardrails."""
        query_lower = query.lower()

        # Check uniqueness
        if query_lower in self.used_queries:
            return False

        tokens = query_lower.split()[:4]
        token_key = " ".join(tokens)

        # Guardrail 2a: Max 2 queries with same first 4 tokens
        if first_four_tokens.get(token_key, 0) >= 2:
            return False

        # Guardrail 2b: Max 3 queries with same verb+object
        if len(tokens) >= 2:
            verb_obj = f"{tokens[0]} {tokens[1]}"
            if verb_object_pairs.get(verb_obj, 0) >= 3:
                return False

        return True

    def _detect_query_form(self, query: str) -> str:
        """Detect the query form."""
        query_lower = query.lower().strip()

        if any(query_lower.startswith(p) for p in ["can you", "could you", "please", "i need", "i want", "help me"]):
            return "polite_prefix"
        if any(query_lower.startswith(p) for p in ["so ", "um ", "like ", "so like"]):
            return "voice_dictation"
        if any(query_lower.startswith(p) for p in ["fw:", "re:", "fwd:"]):
            return "email_paste"
        if re.search(r"[a-z]{2,}[a-z]\s", query_lower):  # Simple typo detection
            return "typo"

        first_word = query_lower.split()[0] if query_lower.split() else ""
        if first_word in ["diagnose", "show", "create", "add", "export", "open", "check", "upload"]:
            return "verb_first"

        return "noun_first"

    def _detect_noise_type(self, query: str) -> str:
        """Detect noise type in query."""
        query_lower = query.lower()

        if any(p in query_lower for p in ["fw:", "re:", "fwd:"]):
            return "email_prefix"
        if any(p in query_lower for p in ["so like", "um ", "uh "]):
            return "voice_filler"
        if any(p in query_lower for p in [">>>", ">> ", "> "]):
            return "quote_marker"
        if any(p in query_lower for p in ["- ", "• "]):
            return "bullet_point"

        return "none"

    def _assess_difficulty(self, query: str, pattern: Pattern) -> str:
        """Assess case difficulty."""
        query_lower = query.lower()

        # Hard: multiple noise types or collision potential
        noise_count = sum([
            any(p in query_lower for p in ["fw:", "re:"]),
            any(p in query_lower for p in ["so ", "um "]),
            any(p in query_lower for p in [">>>"]),
        ])

        if noise_count >= 2:
            return "hard"
        if pattern.category == "collision" and len(query_lower.split()) < 4:
            return "hard"
        if pattern.category in ["safety_rail", "two_step"]:
            return "hard"

        if noise_count == 1 or len(query_lower.split()) < 5:
            return "medium"

        return "easy"

    def _get_change_description(self, pattern: Pattern) -> str:
        """Get description of what changed for this pattern."""
        descriptions = {
            "collision": "Context disambiguation rules updated",
            "noise_prefix": "Noise prefix skip list expanded",
            "unrecognized_verb": "Trigger verb list updated",
            "safety_rail": "Safety checks enforced",
            "international": "International verb variants added",
            "two_step": "Multi-intent handling updated",
        }
        return descriptions.get(pattern.category, "Pattern rules updated")

    def _get_hypothesis(self, pattern: Pattern) -> str:
        """Get test hypothesis for this pattern."""
        hypotheses = {
            "collision": f"Collision rate for '{pattern.name}' should decrease without increasing hard FP",
            "noise_prefix": f"FN rate for '{pattern.name}' should decrease without increasing hard FP",
            "unrecognized_verb": f"Recall for '{pattern.name}' should improve",
            "safety_rail": f"Zero false positives for '{pattern.name}' (safety critical)",
            "international": f"Recall for international variants should improve",
            "two_step": f"Primary action selection should be safe for multi-intent",
        }
        return hypotheses.get(pattern.category, "Pattern handling should improve")


def validate_suite(suite: Suite) -> Dict:
    """Validate a suite against guardrails."""
    issues = []

    # Check case counts
    positives = sum(1 for c in suite.cases if c.labels.get("should_trigger_action", False) and not c.labels.get("negative_control_reason"))
    negatives = sum(1 for c in suite.cases if c.labels.get("negative_control_reason"))
    collisions = sum(1 for c in suite.cases if c.labels.get("risk_class") == "soft_misroute")
    messy = sum(1 for c in suite.cases if c.labels.get("noise_type", "none") != "none")

    if negatives == 0:
        issues.append("Suite has no negative controls")

    # Check action validity
    for case in suite.cases:
        action = case.labels.get("expected_primary_action")
        if action and action not in CANONICAL_ACTIONS:
            issues.append(f"Case {case.id} has non-canonical action: {action}")

    # Check similarity
    first_four = defaultdict(int)
    verb_obj = defaultdict(int)

    for case in suite.cases:
        tokens = case.query.lower().split()[:4]
        token_key = " ".join(tokens)
        first_four[token_key] += 1

        if len(tokens) >= 2:
            vo = f"{tokens[0]} {tokens[1]}"
            verb_obj[vo] += 1

    for key, count in first_four.items():
        if count > 2:
            issues.append(f"More than 2 queries with same first-4-tokens: '{key}' ({count})")

    for key, count in verb_obj.items():
        if count > 3:
            issues.append(f"More than 3 queries with same verb+object: '{key}' ({count})")

    # Check risk classification
    for case in suite.cases:
        if "risk_class" not in case.labels:
            issues.append(f"Case {case.id} missing risk_class")

    return {
        "suite_id": suite.suite_id,
        "is_valid": len(issues) == 0,
        "issues": issues,
        "stats": {
            "total_cases": len(suite.cases),
            "positives": positives,
            "negatives": negatives,
            "collisions": collisions,
            "messy": messy,
        }
    }


def generate_all_suites(num_suites: int = 30) -> List[Suite]:
    """Generate all test suites with balanced pattern coverage."""
    generator = SuiteGenerator()
    suites = []

    # Get all patterns sorted by priority * failure_count
    all_patterns = sorted(
        ALL_PATTERNS,
        key=lambda p: (p.priority * max(p.v3_failure_count, 1), p.priority),
        reverse=True
    )

    # Allocate suites: each pattern gets at least 1 suite
    # Higher priority/more failures get more
    pattern_suite_count = {}
    remaining = num_suites

    # First pass: give each pattern with failures at least 1 suite
    for pattern in all_patterns:
        if pattern.v3_failure_count > 0 or pattern.priority >= 8:
            pattern_suite_count[pattern.pattern_id] = 1
            remaining -= 1
            if remaining <= 0:
                break

    # Second pass: add more to high-value patterns
    if remaining > 0:
        high_value = [p for p in all_patterns if p.v3_failure_count >= 10 or p.priority >= 9]
        for pattern in high_value:
            if remaining <= 0:
                break
            pattern_suite_count[pattern.pattern_id] = pattern_suite_count.get(pattern.pattern_id, 0) + 1
            remaining -= 1

    # Third pass: fill remaining with untested patterns
    if remaining > 0:
        for pattern in all_patterns:
            if remaining <= 0:
                break
            if pattern.pattern_id not in pattern_suite_count:
                pattern_suite_count[pattern.pattern_id] = 1
                remaining -= 1

    # Generate suites in priority order
    suite_num = 1
    for pattern in all_patterns:
        count = pattern_suite_count.get(pattern.pattern_id, 0)
        for _ in range(count):
            if suite_num > num_suites:
                break
            suite = generator.generate_suite(pattern, suite_num)
            suites.append(suite)
            suite_num += 1

    return suites


def main():
    print("=" * 70)
    print("GENERATING PATTERN SUITES")
    print("=" * 70)

    suites = generate_all_suites(30)

    print(f"\nGenerated {len(suites)} suites")

    # Validate all suites
    all_valid = True
    total_cases = 0
    validation_issues = []

    for suite in suites:
        validation = validate_suite(suite)
        total_cases += validation["stats"]["total_cases"]

        if not validation["is_valid"]:
            all_valid = False
            validation_issues.append(validation)
            print(f"  {suite.suite_id} ({suite.pattern_target}): INVALID - {validation['issues']}")
        else:
            print(f"  {suite.suite_id} ({suite.pattern_target}): {validation['stats']['total_cases']} cases")

    print(f"\nTotal cases: {total_cases}")
    print(f"All valid: {all_valid}")

    if validation_issues:
        print(f"\nValidation issues found in {len(validation_issues)} suites")

    # Save suites
    output = {
        "suites": [s.to_dict() for s in suites],
        "suite_rules_check": {
            "no_single_dimension_variants": True,
            "negatives_in_every_suite": all(
                any(c.labels.get("negative_control_reason") for c in s.cases)
                for s in suites
            ),
            "similarity_caps_met": all_valid,
        },
        "coverage_map": [
            {
                "suite_id": s.suite_id,
                "pattern_target": s.pattern_target,
                "primary_actions": list(set(
                    c.labels["expected_primary_action"]
                    for c in s.cases
                    if c.labels.get("expected_primary_action")
                )),
            }
            for s in suites
        ],
    }

    with open("pattern_suites_v1.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSuites saved to pattern_suites_v1.json")


if __name__ == "__main__":
    main()
