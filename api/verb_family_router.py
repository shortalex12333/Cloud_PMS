"""
Verb Family Router
==================
Two-pass router architecture for action resolution.

Pass 1: Detect verb family from query
Pass 2: Resolve target slots (object, container, destination)

This replaces implicit pattern ordering with explicit slot resolution.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class VerbFamily(str, Enum):
    """Verb families group related action verbs."""
    ADD = "add"           # add, attach, upload, include
    SHOW = "show"         # show, view, display, list
    CREATE = "create"     # create, generate, make, raise
    UPDATE = "update"     # update, edit, modify, set
    DIAGNOSE = "diagnose" # diagnose, troubleshoot, investigate, trace
    EXPORT = "export"     # export, download, share
    CHECK = "check"       # check, scan, search, find
    LOG = "log"           # log, record, enter
    COMPLETE = "complete" # close, complete, finish, mark
    ASSIGN = "assign"     # assign, schedule
    ORDER = "order"       # order, purchase, reserve
    OPEN = "open"         # open (document or equipment card)
    UNKNOWN = "unknown"


@dataclass
class SlotResolution:
    """Result of slot resolution pass."""
    target_object: Optional[str] = None      # note, part, photo, document, certificate
    target_container: Optional[str] = None   # work_order, handover, equipment, checklist
    destination: Optional[str] = None        # compliance, fleet, shipyard
    confidence: float = 0.0
    alternatives: List[str] = None

    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []


@dataclass
class RouterResult:
    """Complete routing result."""
    verb_family: VerbFamily
    primary_action: str
    confidence: float
    slots: SlotResolution
    alternatives: List[Tuple[str, float]]  # (action, confidence) pairs
    suggestion_worthy: bool  # True if should show chips instead of auto-execute


# Verb family detection patterns
VERB_FAMILY_MAP: Dict[str, VerbFamily] = {
    # ADD family
    "add": VerbFamily.ADD,
    "attach": VerbFamily.ADD,
    "upload": VerbFamily.ADD,
    "include": VerbFamily.ADD,
    "put": VerbFamily.ADD,

    # SHOW family
    "show": VerbFamily.SHOW,
    "view": VerbFamily.SHOW,
    "display": VerbFamily.SHOW,
    "list": VerbFamily.SHOW,
    "see": VerbFamily.SHOW,

    # CREATE family
    "create": VerbFamily.CREATE,
    "generate": VerbFamily.CREATE,
    "make": VerbFamily.CREATE,
    "raise": VerbFamily.CREATE,
    "new": VerbFamily.CREATE,

    # UPDATE family
    "update": VerbFamily.UPDATE,
    "edit": VerbFamily.UPDATE,
    "modify": VerbFamily.UPDATE,
    "change": VerbFamily.UPDATE,
    "set": VerbFamily.UPDATE,

    # DIAGNOSE family
    "diagnose": VerbFamily.DIAGNOSE,
    "troubleshoot": VerbFamily.DIAGNOSE,
    "investigate": VerbFamily.DIAGNOSE,
    "trace": VerbFamily.DIAGNOSE,
    "analyze": VerbFamily.DIAGNOSE,
    "analyse": VerbFamily.DIAGNOSE,
    "expand": VerbFamily.DIAGNOSE,
    "detect": VerbFamily.DIAGNOSE,

    # EXPORT family
    "export": VerbFamily.EXPORT,
    "download": VerbFamily.EXPORT,
    "share": VerbFamily.EXPORT,
    "summarise": VerbFamily.EXPORT,
    "summarize": VerbFamily.EXPORT,

    # CHECK family
    "check": VerbFamily.CHECK,
    "scan": VerbFamily.CHECK,
    "search": VerbFamily.CHECK,
    "find": VerbFamily.CHECK,
    "lookup": VerbFamily.CHECK,
    "look": VerbFamily.CHECK,

    # LOG family
    "log": VerbFamily.LOG,
    "record": VerbFamily.LOG,
    "enter": VerbFamily.LOG,

    # COMPLETE family
    "close": VerbFamily.COMPLETE,
    "complete": VerbFamily.COMPLETE,
    "finish": VerbFamily.COMPLETE,
    "mark": VerbFamily.COMPLETE,

    # ASSIGN family
    "assign": VerbFamily.ASSIGN,
    "schedule": VerbFamily.ASSIGN,

    # ORDER family
    "order": VerbFamily.ORDER,
    "purchase": VerbFamily.ORDER,
    "reserve": VerbFamily.ORDER,
    "request": VerbFamily.ORDER,

    # OPEN family
    "open": VerbFamily.OPEN,
}


# Slot detection patterns
OBJECT_PATTERNS = {
    "note": r"\b(?:note|comment|remark|observation)\b",
    "part": r"\b(?:part|gasket|filter|belt|anode|seal|bearing|impeller|injector|o-ring|sensor|relay|fuse|valve)\b",
    "photo": r"\b(?:photo|picture|image|pic)\b",
    "document": r"\b(?:document|doc|manual|pdf|drawing|schematic|report|procedure|spec|invoice)\b",
    "certificate": r"\b(?:certificate|cert|certificat)\b",
    "summary": r"\b(?:summary|report)\b",
    "audit": r"\b(?:audit|compliance)\b",
}

CONTAINER_PATTERNS = {
    "work_order": r"\b(?:work\s*order|wo\b|job|task)\b",
    "handover": r"\b(?:handover|watch|logbook)\b",
    "equipment": r"\b(?:equipment|card|system|unit|pump|generator|engine|thruster|stabilizer|watermaker|chiller|compressor|HVAC|boiler)\b",
    "checklist": r"\b(?:checklist|check\s*list)\b",
}

DESTINATION_PATTERNS = {
    "compliance": r"\b(?:compliance|hor|hours\s*of\s*rest|certificate|certification)\b",
    "fleet": r"\b(?:fleet|shipyard|yard)\b",
    "inventory": r"\b(?:inventory|stock|spare|storage)\b",
}


# Action resolution rules by verb family
ACTION_RULES: Dict[VerbFamily, List[Tuple[Dict[str, str], str, float]]] = {
    VerbFamily.ADD: [
        # (slot requirements, action, base_confidence)
        ({"object": "note", "container": "work_order"}, "add_note_to_work_order", 0.95),
        ({"object": "part", "container": "work_order"}, "add_part_to_work_order", 0.95),
        ({"object": "photo", "container": "work_order"}, "attach_photo_to_work_order", 0.95),
        ({"object": "document", "container": "work_order"}, "attach_document_to_work_order", 0.90),
        ({"object": "document", "container": "handover"}, "attach_document_to_handover", 0.90),
        ({"container": "handover"}, "add_to_handover", 0.85),
        ({"container": "checklist"}, "add_checklist_item", 0.85),
        ({"object": "note"}, "add_note", 0.80),
        ({}, "add_to_handover", 0.60),  # Default fallback
    ],
    VerbFamily.SHOW: [
        ({"object": "certificate"}, "show_certificates", 0.90),
        ({"destination": "compliance"}, "show_hours_of_rest", 0.90),
        ({"destination": "inventory"}, "check_stock_level", 0.90),
        ({"container": "handover"}, "view_handover", 0.90),
        ({"container": "work_order"}, "list_work_orders", 0.85),
        ({"container": "checklist"}, "show_checklist", 0.85),
        ({"object": "document"}, "search_documents", 0.80),
        ({}, "show_equipment_overview", 0.70),  # Default
    ],
    VerbFamily.CREATE: [
        ({"object": "audit"}, "generate_audit_pack", 0.95),
        ({"object": "summary"}, "generate_summary", 0.90),
        ({"container": "work_order"}, "create_work_order", 0.90),
        ({"container": "checklist"}, "add_checklist_item", 0.85),
        ({}, "create_work_order", 0.70),  # Default
    ],
    VerbFamily.UPDATE: [
        ({"container": "work_order"}, "update_work_order", 0.90),
        ({"destination": "inventory"}, "update_stock_level", 0.90),
        ({"object": "certificate"}, "update_certificate_metadata", 0.90),
        ({"container": "handover"}, "edit_handover_section", 0.85),
        ({}, "update_work_order", 0.70),  # Default
    ],
    VerbFamily.DIAGNOSE: [
        ({}, "diagnose_fault", 0.90),  # Almost always diagnose_fault
    ],
    VerbFamily.EXPORT: [
        ({"container": "handover"}, "export_handover", 0.95),
        ({"destination": "compliance"}, "export_compliance_logs", 0.95),
        ({"object": "summary"}, "export_summary", 0.90),
        ({"container": "work_order"}, "export_work_order_history", 0.85),
        ({}, "generate_summary", 0.70),  # Default
    ],
    VerbFamily.CHECK: [
        ({"destination": "inventory"}, "check_stock_level", 0.95),
        ({"object": "certificate"}, "show_certificates", 0.90),
        ({"destination": "compliance"}, "show_hours_of_rest", 0.85),
        ({}, "none_search_only", 0.60),  # Default to search
    ],
    VerbFamily.LOG: [
        ({"destination": "compliance"}, "log_hours_of_rest", 0.95),
        ({}, "log_hours_of_rest", 0.80),  # Default
    ],
    VerbFamily.COMPLETE: [
        ({"container": "work_order"}, "close_work_order", 0.90),
        ({}, "mark_work_order_complete", 0.80),
    ],
    VerbFamily.ASSIGN: [
        ({"container": "work_order"}, "assign_work_order", 0.90),
        ({}, "assign_task", 0.75),
    ],
    VerbFamily.ORDER: [
        ({}, "order_part", 0.90),
    ],
    VerbFamily.OPEN: [
        ({"object": "document"}, "open_document", 0.90),
        ({"object": "certificate"}, "open_document", 0.85),
        ({}, "open_equipment_card", 0.75),  # Default
    ],
}


class VerbFamilyRouter:
    """Two-pass router using verb family + slot resolution."""

    def __init__(self):
        self.typo_corrections = {
            "diagnoes": "diagnose", "diganose": "diagnose", "diaggnose": "diagnose",
            "shwo": "show", "hsow": "show", "shoow": "show", "shoo": "show",
            "cretae": "create", "craete": "create", "creat": "create",
            "upadte": "update", "updte": "update",
            "oepn": "open", "opne": "open", "oppn": "open",
            "chekc": "check", "chrck": "check",
            "attahc": "attach", "atach": "attach",
        }

    def correct_typo(self, word: str) -> str:
        """Correct common typos in verbs."""
        return self.typo_corrections.get(word.lower(), word.lower())

    def detect_verb_family(self, query: str) -> Tuple[VerbFamily, str]:
        """
        Pass 1: Detect verb family from first verb in query.

        Returns:
            (VerbFamily, detected_verb)
        """
        # Normalize and tokenize
        query_lower = query.lower().strip()

        # Remove polite prefixes
        polite_prefixes = [
            r"^(?:can|could|would|will)\s+you\s+",
            r"^please\s+",
            r"^i\s+(?:need|want)\s+(?:to\s+)?",
            r"^help\s+(?:me\s+)?",
        ]
        for prefix in polite_prefixes:
            query_lower = re.sub(prefix, "", query_lower)

        # Get first token
        tokens = query_lower.split()
        if not tokens:
            return VerbFamily.UNKNOWN, ""

        first_token = self.correct_typo(tokens[0])

        # Look up verb family
        if first_token in VERB_FAMILY_MAP:
            return VERB_FAMILY_MAP[first_token], first_token

        return VerbFamily.UNKNOWN, first_token

    def resolve_slots(self, query: str) -> SlotResolution:
        """
        Pass 2: Resolve target slots from query context.

        Returns:
            SlotResolution with detected slots and confidence
        """
        query_lower = query.lower()
        slots = SlotResolution()

        # Detect object
        for obj_type, pattern in OBJECT_PATTERNS.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                slots.target_object = obj_type
                break

        # Detect container
        for container_type, pattern in CONTAINER_PATTERNS.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                slots.target_container = container_type
                break

        # Detect destination
        for dest_type, pattern in DESTINATION_PATTERNS.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                slots.destination = dest_type
                break

        # Calculate confidence based on slot coverage
        slot_count = sum([
            slots.target_object is not None,
            slots.target_container is not None,
            slots.destination is not None,
        ])
        slots.confidence = 0.5 + (slot_count * 0.15)  # 0.5 base + 0.15 per slot

        return slots

    def resolve_action(self, verb_family: VerbFamily, slots: SlotResolution) -> Tuple[str, float, List[Tuple[str, float]]]:
        """
        Resolve final action based on verb family and slots.

        Returns:
            (primary_action, confidence, alternatives)
        """
        if verb_family not in ACTION_RULES:
            return "none_search_only", 0.5, []

        rules = ACTION_RULES[verb_family]
        matches = []

        for requirements, action, base_confidence in rules:
            score = base_confidence
            matched = True

            # Check each requirement
            for slot_name, required_value in requirements.items():
                actual_value = None
                if slot_name == "object":
                    actual_value = slots.target_object
                elif slot_name == "container":
                    actual_value = slots.target_container
                elif slot_name == "destination":
                    actual_value = slots.destination

                if actual_value != required_value:
                    matched = False
                    break

            if matched:
                # Boost confidence if more slots matched
                slot_match_count = len(requirements)
                score = base_confidence + (slot_match_count * 0.02)
                matches.append((action, min(score, 1.0)))

        if not matches:
            # Fallback to last rule (default)
            default_rule = rules[-1]
            return default_rule[1], default_rule[2], []

        # Sort by confidence
        matches.sort(key=lambda x: -x[1])

        primary = matches[0]
        alternatives = matches[1:4]  # Top 3 alternatives

        return primary[0], primary[1], alternatives

    def route(self, query: str) -> RouterResult:
        """
        Full two-pass routing.

        Args:
            query: User query string

        Returns:
            RouterResult with action, confidence, alternatives
        """
        # Pass 1: Verb family
        verb_family, detected_verb = self.detect_verb_family(query)

        if verb_family == VerbFamily.UNKNOWN:
            return RouterResult(
                verb_family=VerbFamily.UNKNOWN,
                primary_action="none_search_only",
                confidence=0.5,
                slots=SlotResolution(),
                alternatives=[],
                suggestion_worthy=True
            )

        # Pass 2: Slot resolution
        slots = self.resolve_slots(query)

        # Resolve action
        primary_action, confidence, alternatives = self.resolve_action(verb_family, slots)

        # Determine if suggestion-worthy
        suggestion_worthy = (
            confidence < 0.85 or
            len(alternatives) > 0 and alternatives[0][1] > confidence - 0.1
        )

        return RouterResult(
            verb_family=verb_family,
            primary_action=primary_action,
            confidence=confidence,
            slots=slots,
            alternatives=alternatives,
            suggestion_worthy=suggestion_worthy
        )


# Singleton instance
_router: Optional[VerbFamilyRouter] = None


def get_verb_family_router() -> VerbFamilyRouter:
    """Get singleton router instance."""
    global _router
    if _router is None:
        _router = VerbFamilyRouter()
    return _router


# Convenience function
def route_query(query: str) -> RouterResult:
    """Route a query using verb family resolution."""
    return get_verb_family_router().route(query)


if __name__ == "__main__":
    # Test cases
    router = VerbFamilyRouter()

    test_queries = [
        "add note to work order filter replaced",
        "show hours of rest",
        "create work order for generator service",
        "diagnose fault E047 on main engine",
        "export handover notes",
        "check stock level for oil filter",
        "attach photo to work order",
        "generate audit pack",
        "open document P&ID",
        "upload certificate",
    ]

    print("=== VERB FAMILY ROUTER TEST ===\n")
    for query in test_queries:
        result = router.route(query)
        print(f"Query: {query}")
        print(f"  Verb Family: {result.verb_family.value}")
        print(f"  Action: {result.primary_action} ({result.confidence:.0%})")
        print(f"  Slots: obj={result.slots.target_object}, cont={result.slots.target_container}, dest={result.slots.destination}")
        if result.alternatives:
            print(f"  Alternatives: {[(a, f'{c:.0%}') for a, c in result.alternatives]}")
        print(f"  Suggestion-worthy: {result.suggestion_worthy}")
        print()
